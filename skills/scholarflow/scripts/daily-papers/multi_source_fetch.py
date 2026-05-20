#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parent.parent / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from paper_models import Paper, SearchPlan
from paper_pipeline import deduplicate_papers, rank_papers, resolve_code_links
from paper_sources import SOURCE_REGISTRY, search_all_with_diagnostics


def main(argv: list[str] | None = None, *, registry=None) -> int:
    parser = argparse.ArgumentParser(description="Multi-source paper fetch with normalized output.")
    parser.add_argument("--topic", required=True, help="Research topic understood by Codex.")
    parser.add_argument("--queries-json", required=True, help="JSON list of diversified search queries.")
    parser.add_argument("--since-year", type=int, default=None, help="Lower publication year bound.")
    parser.add_argument("--max-results", type=int, default=100, help="Maximum deduplicated candidates to write.")
    parser.add_argument("--sources", default="auto", help="auto or comma-separated source names.")
    parser.add_argument("--output", required=True, help="Path to candidates JSON output.")
    args = parser.parse_args(argv)

    try:
        queries = json.loads(args.queries_json)
    except json.JSONDecodeError as exc:
        print(f"Error: --queries-json must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if isinstance(queries, str):
        queries = [queries]
    queries = [str(query).strip() for query in queries if str(query).strip()]
    if not queries:
        print("Error: --queries-json must contain at least one query", file=sys.stderr)
        return 2

    sources = _parse_sources(args.sources)
    plan = SearchPlan(
        topic=args.topic,
        queries=queries,
        since_year=args.since_year,
        max_results=args.max_results,
        sources=sources,
    )
    per_query_limit = _per_query_limit(args.max_results, len(queries), len(sources) if sources != ["auto"] else 4)
    raw_papers, diagnostics = search_all_with_diagnostics(
        plan,
        per_query_limit=per_query_limit,
        sources=sources,
        registry=registry or SOURCE_REGISTRY,
    )
    resolved = resolve_code_links(raw_papers)
    deduped, dedup_stats = deduplicate_papers(resolved)
    ranked = rank_papers(deduped, args.topic, args.since_year)[: args.max_results]

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output_path, [paper.to_dict() for paper in ranked])
    _write_json(output_path.parent / "plan.json", plan.to_dict())
    _write_json(output_path.parent / "source_diagnostics.json", diagnostics)
    _write_json(output_path.parent / "dedup_stats.json", dedup_stats)
    return 0


def _parse_sources(value: str) -> list[str]:
    if not value or value.strip().lower() == "auto":
        return ["auto"]
    return [source.strip().lower().replace("-", "_") for source in value.split(",") if source.strip()]


def _per_query_limit(max_results: int, query_count: int, source_count: int) -> int:
    denominator = max(1, query_count * max(1, source_count))
    return max(5, min(50, (max_results // denominator) + 5))


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
