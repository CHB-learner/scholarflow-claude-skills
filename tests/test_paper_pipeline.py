import importlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


SKILLS_ROOT = Path(__file__).resolve().parents[1]
SHARED_DIR = SKILLS_ROOT / "_shared"
DAILY_PAPERS_DIR = SKILLS_ROOT / "daily-papers"
DAILY_PAPERS_NOTES_DIR = SKILLS_ROOT / "daily-papers-notes"
PAPER_READER_DIR = SKILLS_ROOT / "paper-reader"

for path in (SHARED_DIR, DAILY_PAPERS_DIR, DAILY_PAPERS_NOTES_DIR, PAPER_READER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


class ConfigCompatibilityTests(unittest.TestCase):
    def test_legacy_daily_paper_keywords_populate_daily_papers_keywords(self):
        import user_config

        with TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            (config_dir / "user-config.json").write_text(
                json.dumps(
                    {
                        "paths": {
                            "obsidian_vault": str(config_dir / "vault"),
                            "daily_papers_folder": "Dailypaper",
                            "research_fields_folder": "Research_Fields",
                        },
                        "daily_paper_keywords": ["大模型评测", "扩散模型"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                self.assertEqual(user_config.daily_papers_config()["keywords"], ["大模型评测", "扩散模型"])
                self.assertEqual(user_config.daily_papers_dir(), config_dir / "vault" / "Dailypaper")
                self.assertEqual(user_config.research_fields_dir(), config_dir / "vault" / "Research_Fields")
                self.assertEqual(user_config.paper_notes_dir(), config_dir / "vault" / "Research_Fields")
                self.assertEqual(user_config.concepts_dir(), config_dir / "vault" / "Concepts")


class PaperPipelineTests(unittest.TestCase):
    def test_deduplicate_merges_identifiers_and_title_similarity(self):
        from paper_models import Paper
        from paper_pipeline import deduplicate_papers

        papers = [
            Paper(
                title="RNA Inverse Folding with Graph Neural Networks",
                authors=["Ada Lovelace"],
                year=2024,
                doi="10.1000/example",
                source="crossref",
                sources=["crossref"],
            ),
            Paper(
                title="RNA inverse folding with graph neural networks",
                authors=["Ada Lovelace", "Grace Hopper"],
                year=2024,
                doi="10.1000/EXAMPLE",
                pdf_url="https://example.org/paper.pdf",
                source="openalex",
                sources=["openalex"],
            ),
            Paper(
                title="A Survey of RNA Design",
                authors=["Alan Turing"],
                year=2023,
                arxiv_id="2401.12345",
                source="arxiv",
                sources=["arxiv"],
            ),
            Paper(
                title="A Survey of RNA Design.",
                authors=["Alan Turing"],
                year=2023,
                raw={"identifiers": {"pmid": "123"}},
                source="pubmed",
                sources=["pubmed"],
            ),
        ]

        merged, stats = deduplicate_papers(papers)

        self.assertEqual(len(merged), 2)
        first = next(p for p in merged if p.doi)
        self.assertEqual(first.pdf_url, "https://example.org/paper.pdf")
        self.assertEqual(set(first.sources), {"crossref", "openalex"})
        survey = next(p for p in merged if "Survey" in p.title)
        self.assertEqual(set(survey.sources), {"arxiv", "pubmed"})
        self.assertEqual(stats["raw_count"], 4)
        self.assertEqual(stats["after_title_similarity_dedup"], 2)

    def test_source_registry_records_failures_without_stopping(self):
        from paper_models import SearchPlan
        from paper_sources import search_all_with_diagnostics

        def ok_searcher(query, limit, since_year):
            from paper_models import Paper

            return [Paper(title=f"{query} result", source="ok_source", sources=["ok_source"])]

        def bad_searcher(query, limit, since_year):
            raise RuntimeError("boom")

        plan = SearchPlan(
            topic="RNA design",
            queries=["RNA inverse folding"],
            since_year=2021,
            max_results=10,
        )
        papers, diagnostics = search_all_with_diagnostics(
            plan,
            per_query_limit=5,
            sources=["ok_source", "bad_source"],
            registry={
                "ok_source": ok_searcher,
                "bad_source": bad_searcher,
            },
        )

        self.assertEqual(len(papers), 1)
        self.assertEqual(diagnostics["sources"]["ok_source"]["status"], "ok")
        self.assertEqual(diagnostics["sources"]["bad_source"]["status"], "error")
        self.assertIn("RuntimeError: boom", diagnostics["sources"]["bad_source"]["errors"][0])


class ScriptEntrypointTests(unittest.TestCase):
    def test_help_entrypoints_import_cleanly(self):
        import backfill_links
        import paper_daemon

        self.assertTrue(hasattr(backfill_links, "main"))
        self.assertTrue(hasattr(paper_daemon, "process_collection"))

    def test_multi_source_fetch_writes_expected_artifacts_with_mock_registry(self):
        multi_source_fetch = importlib.import_module("multi_source_fetch")

        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "candidates.json"
            rc = multi_source_fetch.main(
                [
                    "--topic",
                    "RNA inverse folding",
                    "--queries-json",
                    '["RNA inverse folding"]',
                    "--since-year",
                    "2021",
                    "--max-results",
                    "5",
                    "--sources",
                    "mock",
                    "--output",
                    str(output),
                ],
                registry={
                    "mock": lambda query, limit, since_year: [
                        multi_source_fetch.Paper(
                            title="RNA inverse folding benchmark",
                            authors=["Ada Lovelace"],
                            year=2024,
                            arxiv_id="2401.12345",
                            source="mock",
                            sources=["mock"],
                        )
                    ]
                },
            )

            self.assertEqual(rc, 0)
            self.assertTrue(output.exists())
            self.assertTrue((output.parent / "source_diagnostics.json").exists())
            self.assertTrue((output.parent / "dedup_stats.json").exists())
            papers = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(papers[0]["title"], "RNA inverse folding benchmark")
            self.assertIn("rank_score", papers[0])


if __name__ == "__main__":
    unittest.main()
