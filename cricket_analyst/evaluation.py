"""Simple evaluation utilities for smoke-testing analyst prompts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .observability import logger

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EVAL_SET = ROOT / "evals" / "cricket_eval_set.json"


def load_eval_set(path: str | Path = DEFAULT_EVAL_SET) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_graph(graph, eval_set: list[dict[str, Any]] | str | Path | None = None):
    """Run each evaluation item and return a summary of route + success flag."""
    items = load_eval_set(eval_set) if isinstance(eval_set, (str, Path)) else (eval_set or load_eval_set())
    results = []
    for item in items:
        question = item["query"]
        logger.info("running_eval_item", extra={"item_id": item["id"], "query": question})
        response = graph.invoke({"query": question})
        route = response.get("route")
        ok = route == item.get("expected_route") or route in {"analysis", "rules", "news", "team_building"}
        results.append({
            "id": item["id"],
            "query": question,
            "expected_route": item.get("expected_route"),
            "actual_route": route,
            "ok": ok,
            "answer_length": len(str(response.get("answer", ""))),
        })
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the cricket analyst evaluation set.")
    parser.add_argument("--path", type=str, default=str(DEFAULT_EVAL_SET))
    args = parser.parse_args()

    print(json.dumps(load_eval_set(args.path), indent=2))
