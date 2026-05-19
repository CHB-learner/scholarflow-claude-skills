import importlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
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


class ResearchFieldMocTests(unittest.TestCase):
    def setUp(self):
        import user_config

        user_config.load_user_config.cache_clear()

    def tearDown(self):
        import user_config

        user_config.load_user_config.cache_clear()

    def test_new_summary_uses_managed_paper_list_markers_and_second_run_is_stable(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            self._write_note(vault, "RNA", "BeeRNA")

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                result = generate_research_field_mocs.build_research_field_mocs(vault)

                summary_path = vault / "Research_Fields" / "RNA" / "summary.md"
                content = summary_path.read_text(encoding="utf-8")

                self.assertEqual(result["created_files"], 1)
                self.assertIn("<!-- scholarflow:paper-list:start -->", content)
                self.assertIn("<!-- scholarflow:paper-list:end -->", content)
                self.assertIn("该研究方向下共有 **1** 篇论文。", content)
                self.assertIn("| 2026.05.01 | [BeeRNA]", content)

                second = generate_research_field_mocs.build_research_field_mocs(vault)
                self.assertEqual(second["created_files"], 0)
                self.assertEqual(second["updated_files"], 0)

    def test_existing_marked_summary_preserves_handwritten_sections(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            field_dir = vault / "Research_Fields" / "RNA"
            self._write_note(vault, "RNA", "BeeRNA")
            (field_dir / "summary.md").write_text(
                "\n".join(
                    [
                        "# RNA",
                        "",
                        "这是一段人工维护的研究方向说明。",
                        "",
                        "<!-- scholarflow:paper-list:start -->",
                        "该研究方向下共有 **0** 篇论文。",
                        "",
                        "## 论文列表",
                        "",
                        "- 旧内容",
                        "<!-- scholarflow:paper-list:end -->",
                        "",
                        "## 手写备注",
                        "",
                        "保留这段判断。",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                result = generate_research_field_mocs.build_research_field_mocs(vault)

            content = (field_dir / "summary.md").read_text(encoding="utf-8")
            self.assertEqual(result["updated_files"], 1)
            self.assertIn("这是一段人工维护的研究方向说明。", content)
            self.assertIn("## 手写备注", content)
            self.assertIn("保留这段判断。", content)
            self.assertNotIn("- 旧内容", content)
            self.assertIn("该研究方向下共有 **1** 篇论文。", content)
            self.assertIn("| 2026.05.01 | [BeeRNA]", content)

    def test_legacy_summary_without_markers_replaces_only_paper_list_section(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            field_dir = vault / "Research_Fields" / "RNA"
            self._write_note(vault, "RNA", "BeeRNA")
            (field_dir / "summary.md").write_text(
                "\n".join(
                    [
                        "---",
                        "tags: [custom]",
                        "---",
                        "",
                        "# RNA",
                        "",
                        "人工 intro 不能丢。",
                        "",
                        "## 论文列表",
                        "",
                        "- 旧论文行",
                        "",
                        "## 手写章节",
                        "",
                        "这里是用户自己的研究判断。",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                generate_research_field_mocs.build_research_field_mocs(vault)

            content = (field_dir / "summary.md").read_text(encoding="utf-8")
            self.assertIn("tags: [custom]", content)
            self.assertIn("人工 intro 不能丢。", content)
            self.assertIn("## 手写章节", content)
            self.assertIn("这里是用户自己的研究判断。", content)
            self.assertNotIn("- 旧论文行", content)
            self.assertIn("<!-- scholarflow:paper-list:start -->", content)
            self.assertIn("该研究方向下共有 **1** 篇论文。", content)

    def test_summary_without_paper_list_appends_managed_block(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            field_dir = vault / "Research_Fields" / "RNA"
            self._write_note(vault, "RNA", "BeeRNA")
            (field_dir / "summary.md").write_text(
                "# RNA\n\n人工维护的概述。\n\n## Open Questions\n\n- 还要补实验。\n",
                encoding="utf-8",
            )

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                generate_research_field_mocs.build_research_field_mocs(vault)

            content = (field_dir / "summary.md").read_text(encoding="utf-8")
            self.assertIn("人工维护的概述。", content)
            self.assertIn("## Open Questions", content)
            self.assertIn("- 还要补实验。", content)
            self.assertIn("<!-- scholarflow:paper-list:start -->", content)
            self.assertIn("| 2026.05.01 | [BeeRNA]", content)

    def test_topic_candidate_index_adds_pending_papers_to_summary(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            self._write_topic_papers(
                vault,
                "RNA",
                [
                    {
                        "title": "RiboSphere: Learning Unified RNA Representations",
                        "method_name": "RiboSphere",
                        "date": "2026-03-20",
                        "url": "https://arxiv.org/abs/2603.19636",
                        "code_url": "https://github.com/example/ribosphere",
                        "label": "core",
                        "reason": "统一 RNA 结构表示，适合后续精读",
                        "note_status": "pending",
                    }
                ],
            )

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                result = generate_research_field_mocs.build_research_field_mocs(vault)

            content = (vault / "Research_Fields" / "RNA" / "summary.md").read_text(encoding="utf-8")
            self.assertEqual(result["papers_found"], 1)
            self.assertIn("该研究方向下共有 **1** 篇论文。", content)
            self.assertIn("| 2026.03.20 | [RiboSphere](https://arxiv.org/abs/2603.19636) | 待精读 | [GitHub](https://github.com/example/ribosphere) | [arXiv](https://arxiv.org/abs/2603.19636) |  |", content)
            self.assertNotIn("统一 RNA 结构表示，适合后续精读", content)

    def test_topic_candidate_and_existing_note_deduplicate_to_done_status(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            self._write_note(vault, "RNA", "BeeRNA")
            self._write_topic_papers(
                vault,
                "RNA",
                [
                    {
                        "title": "BeeRNA: Benchmarking RNA design",
                        "method_name": "BeeRNA",
                        "date": "2025-11-26",
                        "url": "https://arxiv.org/abs/2511.21781",
                        "label": "core",
                        "reason": "已有笔记时保留调研理由",
                        "note_status": "pending",
                    }
                ],
            )

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                generate_research_field_mocs.build_research_field_mocs(vault)

            content = (vault / "Research_Fields" / "RNA" / "summary.md").read_text(encoding="utf-8")
            self.assertEqual(content.count("| 2026.05.01 | [BeeRNA]"), 1)
            self.assertIn("[EN](obsidian://open?", content)
            self.assertIn("[ZH](obsidian://open?", content)
            self.assertNotIn("已有笔记时保留调研理由", content)
            self.assertNotIn("| 待精读 |", content)

    def test_candidate_code_url_is_extracted_from_abstract(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            self._write_topic_papers(
                vault,
                "RNA",
                [
                    {
                        "title": "CodeRNA Agentic RNA Design",
                        "date": "2026-05-18",
                        "url": "https://arxiv.org/abs/2605.12345v1",
                        "abstract": "Code is available at https://github.com/example/coderna.",
                        "note_status": "pending",
                    }
                ],
            )

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                generate_research_field_mocs.build_research_field_mocs(vault)

            content = (vault / "Research_Fields" / "RNA" / "summary.md").read_text(encoding="utf-8")
            self.assertIn("[CodeRNA Agentic RNA Design](https://arxiv.org/abs/2605.12345)", content)
            self.assertIn("[GitHub](https://github.com/example/coderna)", content)

    def test_excluded_topic_candidates_do_not_enter_summary(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            self._write_topic_papers(
                vault,
                "RNA",
                [
                    {
                        "title": "Relevant Agentic RL",
                        "method_name": "RelevantAgent",
                        "date": "2026-05-18",
                        "url": "https://arxiv.org/abs/2605.22222",
                        "label": "core",
                        "note_status": "pending",
                    },
                    {
                        "title": "Excluded Clickbait",
                        "method_name": "Clickbait",
                        "date": "2026-05-18",
                        "url": "https://arxiv.org/abs/2605.33333",
                        "label": "exclude",
                        "note_status": "pending",
                    },
                ],
            )

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                result = generate_research_field_mocs.build_research_field_mocs(vault)

            content = (vault / "Research_Fields" / "RNA" / "summary.md").read_text(encoding="utf-8")
            self.assertEqual(result["papers_found"], 1)
            self.assertIn("RelevantAgent", content)
            self.assertNotIn("Clickbait", content)

    def test_legacy_root_topic_papers_json_is_supported(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            field_dir = vault / "Research_Fields" / "RNA"
            (field_dir / "topic_papers.json").write_text(
                json.dumps(
                    [
                        {
                            "title": "RootIndex: Legacy Candidate",
                            "method_name": "RootIndex",
                            "date": "2026-05-18",
                            "url": "https://arxiv.org/abs/2605.11111",
                            "note_status": "pending",
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                result = generate_research_field_mocs.build_research_field_mocs(vault)

            content = (field_dir / "summary.md").read_text(encoding="utf-8")
            self.assertEqual(result["papers_found"], 1)
            self.assertIn("[RootIndex](https://arxiv.org/abs/2605.11111)", content)

    def test_arxiv_versioned_candidates_are_deduplicated(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            self._write_topic_papers(
                vault,
                "RNA",
                [
                    {
                        "title": "Versioned Agent Paper",
                        "method_name": "Versioned",
                        "date": "2026-05-18",
                        "url": "https://arxiv.org/abs/2605.18747v1",
                        "note_status": "pending",
                    },
                    {
                        "title": "Versioned Agent Paper",
                        "method_name": "Versioned",
                        "date": "2026-05-18",
                        "url": "https://arxiv.org/abs/2605.18747",
                        "note_status": "pending",
                    },
                ],
            )

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                result = generate_research_field_mocs.build_research_field_mocs(vault)

            content = (vault / "Research_Fields" / "RNA" / "summary.md").read_text(encoding="utf-8")
            self.assertEqual(result["papers_found"], 1)
            self.assertEqual(content.count("Versioned"), 1)

    def test_summary_limits_topic_candidates_to_fifty_rows(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            self._write_topic_papers(
                vault,
                "RNA",
                [
                    {
                        "title": f"Candidate {i}",
                        "method_name": f"Candidate{i:02d}",
                        "date": f"2026-05-{(i % 28) + 1:02d}",
                        "url": f"https://arxiv.org/abs/2605.{i:05d}",
                        "note_status": "pending",
                    }
                    for i in range(60)
                ],
            )

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                result = generate_research_field_mocs.build_research_field_mocs(vault)
                second = generate_research_field_mocs.build_research_field_mocs(vault)

            content = (vault / "Research_Fields" / "RNA" / "summary.md").read_text(encoding="utf-8")
            data_rows = [
                line
                for line in content.splitlines()
                if line.startswith("| 2026.") and "Candidate" in line
            ]
            self.assertEqual(result["papers_found"], 50)
            self.assertEqual(len(data_rows), 50)
            self.assertEqual(second["updated_files"], 0)

    def test_legacy_root_note_directories_are_included(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            self._write_note(vault, "RNA", "RiboSphere", legacy_root=True)

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                generate_research_field_mocs.build_research_field_mocs(vault)

            content = (vault / "Research_Fields" / "RNA" / "summary.md").read_text(encoding="utf-8")
            self.assertIn("| 2026.05.01 | [RiboSphere]", content)
            self.assertIn("file=RiboSphere/RiboSphere.pdf", content)
            self.assertIn("file=RiboSphere/RiboSphere_en", content)

    def test_root_uncategorized_notes_are_indexed_like_other_fields(self):
        import generate_research_field_mocs
        import user_config

        with TemporaryDirectory() as tmp:
            vault, config_dir = self._make_vault(tmp)
            self._write_uncategorized_note(vault, "ColdStartPaper")

            with patch.object(user_config, "_config_dir", return_value=config_dir):
                user_config.load_user_config.cache_clear()
                result = generate_research_field_mocs.build_research_field_mocs(vault)

            summary_path = vault / "未分类" / "summary.md"
            content = summary_path.read_text(encoding="utf-8")
            self.assertEqual(result["created_files"], 2)
            self.assertIn("# 未分类", content)
            self.assertIn("| 2026.05.01 | [ColdStartPaper]", content)
            self.assertIn("file=papers/ColdStartPaper/ColdStartPaper.pdf", content)
            self.assertIn("file=papers/ColdStartPaper/ColdStartPaper_en", content)

    def test_skill_docs_make_topic_research_lightweight_and_require_named_read(self):
        topic_skill = (SKILLS_ROOT / "topic-research" / "SKILL.md").read_text(encoding="utf-8")
        paper_reader_skill = (SKILLS_ROOT / "paper-reader" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("不调用 paper-reader", topic_skill)
        self.assertIn("topic_papers.json", topic_skill)
        self.assertIn("最多 50 篇", topic_skill)
        self.assertIn("备注列永远留空", topic_skill)
        self.assertIn("不要写临时全量抓取脚本直接刷新 summary", topic_skill)
        self.assertNotIn("## Step 7: 生成笔记", topic_skill)
        self.assertIn("`读一下` 不带论文名", paper_reader_skill)
        self.assertIn("不启动深读", paper_reader_skill)
        self.assertIn("未分类", paper_reader_skill)
        self.assertIn("{VAULT_PATH}/未分类/papers/{MethodName}/", paper_reader_skill)
        self.assertIn("不要创建 `Dailypaper/{月份}`", topic_skill)
        self.assertNotIn("research-{主题}.md", topic_skill)

    def _make_vault(self, tmp: str) -> tuple[Path, Path]:
        root = Path(tmp)
        vault = root / "vault"
        config_dir = root / "config"
        (vault / "Research_Fields" / "RNA" / "papers").mkdir(parents=True)
        config_dir.mkdir()
        (config_dir / "user-config.json").write_text(
            json.dumps(
                {
                    "paths": {
                        "obsidian_vault": str(vault),
                        "research_fields_folder": "Research_Fields",
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return vault, config_dir

    def _write_note(self, vault: Path, field_name: str, method_name: str, legacy_root: bool = False) -> None:
        field_dir = vault / "Research_Fields" / field_name
        paper_dir = field_dir / method_name if legacy_root else field_dir / "papers" / method_name
        paper_dir.mkdir(parents=True, exist_ok=True)
        (paper_dir / f"{method_name}_en.md").write_text(
            "\n".join(
                [
                    "---",
                    "date: 2026-05-01",
                    "---",
                    "",
                    f"# {method_name}",
                    "",
                    "| arXiv ID | 2605.07608 |",
                    "[GitHub](https://github.com/example/repo)",
                ]
            ),
            encoding="utf-8",
        )
        (paper_dir / f"{method_name}_zh.md").write_text(f"# {method_name}\n", encoding="utf-8")
        (paper_dir / f"{method_name}.pdf").write_bytes(b"%PDF-1.4\n")

    def _write_uncategorized_note(self, vault: Path, method_name: str) -> None:
        paper_dir = vault / "未分类" / "papers" / method_name
        paper_dir.mkdir(parents=True, exist_ok=True)
        (paper_dir / f"{method_name}_en.md").write_text(
            "\n".join(
                [
                    "---",
                    "date: 2026-05-01",
                    "---",
                    "",
                    f"# {method_name}",
                    "",
                    "| arXiv ID | 2605.07608 |",
                ]
            ),
            encoding="utf-8",
        )
        (paper_dir / f"{method_name}_zh.md").write_text(f"# {method_name}\n", encoding="utf-8")
        (paper_dir / f"{method_name}.pdf").write_bytes(b"%PDF-1.4\n")

    def _write_topic_papers(self, vault: Path, field_name: str, papers: list[dict]) -> None:
        meta_dir = vault / "Research_Fields" / field_name / "_meta"
        meta_dir.mkdir(parents=True, exist_ok=True)
        (meta_dir / "topic_papers.json").write_text(
            json.dumps(papers, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


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
