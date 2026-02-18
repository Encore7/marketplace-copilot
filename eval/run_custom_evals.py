from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from backend.app.agents.graph import create_copilot_graph
from backend.app.agents.state import SellerState
from backend.app.rag.store import async_retrieve_chunks


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            rows.append(json.loads(text))
    return rows


def _contains_all(text: str, required: List[str]) -> Tuple[bool, List[str]]:
    missing = [item for item in required if item.lower() not in text.lower()]
    return len(missing) == 0, missing


def _contains_none(text: str, forbidden: List[str]) -> Tuple[bool, List[str]]:
    present = [item for item in forbidden if item.lower() in text.lower()]
    return len(present) == 0, present


def _action_coverage_score(state: SellerState, required_actions: List[str]) -> Tuple[bool, List[str]]:
    action_text = " ".join(
        f"{a.title} {a.description} {a.category.value}" for a in (state.action_plan.actions if state.action_plan else [])
    ).lower()

    mapping = {
        "adjust_price": ["price", "pricing", "adjust"],
        "rewrite_listing": ["listing", "seo", "title", "bullet", "description"],
        "inventory_replenish": ["inventory", "stock", "reorder", "replenish"],
        "compliance_check": ["compliance", "policy", "restricted", "guideline"],
    }

    missing: List[str] = []
    for expected in required_actions:
        keywords = mapping.get(expected, [expected])
        if not any(k in action_text for k in keywords):
            missing.append(expected)
    return len(missing) == 0, missing


async def _run_golden_scenarios(path: Path) -> Dict[str, Any]:
    graph = create_copilot_graph()
    rows = _read_jsonl(path)
    results: List[Dict[str, Any]] = []

    for row in rows:
        query = row["query"]
        marketplace = row.get("profile", {}).get("marketplaces", [])
        initial_state = {
            "query": {
                "raw_query": query,
                "mode": "general_qa",
                "marketplaces": marketplace,
                "language": "en",
            }
        }
        final_state_dict = await graph.ainvoke(initial_state)
        state = SellerState.model_validate(final_state_dict)
        answer = (state.final_answer.answer_markdown if state.final_answer else "") or ""

        expected = row.get("expected_points", {})
        must_mention = expected.get("must_mention", [])
        must_not_mention = expected.get("must_not_mention", [])
        required_actions = expected.get("required_actions", [])

        mention_ok, missing_mentions = _contains_all(answer, must_mention)
        not_mention_ok, present_forbidden = _contains_none(answer, must_not_mention)
        actions_ok, missing_actions = _action_coverage_score(state, required_actions)
        passed = mention_ok and not_mention_ok and actions_ok

        results.append(
            {
                "id": row.get("id"),
                "passed": passed,
                "missing_mentions": missing_mentions,
                "present_forbidden": present_forbidden,
                "missing_actions": missing_actions,
            }
        )

    passed = sum(1 for r in results if r["passed"])
    return {"suite": "golden_scenarios", "passed": passed, "total": len(results), "results": results}


async def _run_rag_golden(path: Path) -> Dict[str, Any]:
    rows = _read_jsonl(path)
    results: List[Dict[str, Any]] = []

    for row in rows:
        chunks = await async_retrieve_chunks(
            query=row["query"],
            marketplace=row.get("marketplace"),
            section=None,
            top_k=8,
            mode="hybrid",
        )
        chunk_text = " ".join(c.text for c in chunks).lower()
        chunk_sources = [c.source or "" for c in chunks]

        expected_doc_ids = row.get("expected_doc_ids", [])
        expected_key_phrases = row.get("key_phrases", [])

        # Relaxed source matching: any expected basename appears in retrieved source.
        source_ok = True
        missing_sources: List[str] = []
        for expected in expected_doc_ids:
            expected_base = Path(expected).name
            if not any(expected_base in s for s in chunk_sources):
                source_ok = False
                missing_sources.append(expected)

        phrase_ok, missing_phrases = _contains_all(chunk_text, expected_key_phrases)
        passed = source_ok and phrase_ok
        results.append(
            {
                "id": row.get("id"),
                "passed": passed,
                "missing_sources": missing_sources,
                "missing_phrases": missing_phrases,
                "num_chunks": len(chunks),
            }
        )

    passed = sum(1 for r in results if r["passed"])
    return {"suite": "rag_golden", "passed": passed, "total": len(results), "results": results}


async def main() -> None:
    eval_root = Path("eval")
    scenario_report = await _run_golden_scenarios(eval_root / "golden_scenarios.jsonl")
    rag_report = await _run_rag_golden(eval_root / "rag_golden.jsonl")
    report = {
        "summary": {
            "golden_scenarios": f"{scenario_report['passed']}/{scenario_report['total']}",
            "rag_golden": f"{rag_report['passed']}/{rag_report['total']}",
        },
        "details": [scenario_report, rag_report],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
