"""Tokens per worker and per phase from `claude -p --output-format stream-json --verbose` logs.

Usage: python3 -I tests/tokens.py <log.jsonl> [<log.jsonl> ...]
Per worker: each Agent tool result's agentType, resolvedModel (the model it really ran on),
totalTokens (the worker's context at completion = what it read + wrote), tool uses, duration.
Per model: the session result's modelUsage (cumulative, billed, all agents) and costUSD.
Standard library only.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

PHASE = {"project-reader": "0", "strategic-designer": "1", "tactical-designer": "2", "db-designer": "3",
         "diagram-writer": "4-5", "api-designer": "6", "design-reviewer": "7", "doc-librarian": "8"}


def main(paths: list[str]) -> int:
    workers, models = [], defaultdict(lambda: defaultdict(float))
    desc = {}
    for path in paths:
        for line in open(path, encoding="utf-8"):
            e = json.loads(line)
            if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
                for c in e["message"].get("content", []):
                    if c.get("type") == "tool_use" and c.get("name") == "Agent":
                        desc[c["id"]] = c["input"].get("description", "")
            tur = e.get("tool_use_result")
            if e.get("type") == "user" and isinstance(tur, dict) and tur.get("agentType"):
                tid = next((c.get("tool_use_id") for c in e["message"]["content"] if isinstance(c, dict)), "")
                workers.append((tur["agentType"], desc.get(tid, ""), tur.get("resolvedModel", "?"),
                                tur.get("totalTokens", 0), tur.get("totalToolUseCount", 0),
                                tur.get("totalDurationMs", 0) / 1000, tur.get("status", "")))
            if e.get("type") == "result":
                for m, u in (e.get("modelUsage") or {}).items():
                    for k in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "costUSD"):
                        models[m][k] += u.get(k, 0) or 0
    print("| Phase | Worker | Description | Ran on | Context tokens at end | Tool uses | Seconds | Status |")
    print("|---|---|---|---|---|---|---|---|")
    per_phase = defaultdict(int)
    for w in sorted(workers, key=lambda w: PHASE.get(w[0], "z")):
        ph = PHASE.get(w[0], "?")
        per_phase[ph] += w[3]
        print(f"| {ph} | {w[0]} | {w[1]} | {w[2]} | {w[3]:,} | {w[4]} | {w[5]:.0f} | {w[6]} |")
    print("\n| Phase | Worker context tokens (sum) |\n|---|---|")
    for ph, n in sorted(per_phase.items()):
        print(f"| {ph} | {n:,} |")
    print("\n| Model | Input | Cache read | Cache write | Output | Cost USD (list) |\n|---|---|---|---|---|---|")
    for m, u in models.items():
        print(f"| {m} | {u['inputTokens']:,.0f} | {u['cacheReadInputTokens']:,.0f} | {u['cacheCreationInputTokens']:,.0f} "
              f"| {u['outputTokens']:,.0f} | {u['costUSD']:.2f} |")
    print(f"\nTotal cost USD (list): {sum(u['costUSD'] for u in models.values()):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
