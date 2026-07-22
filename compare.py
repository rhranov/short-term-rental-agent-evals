#!/usr/bin/env python3
"""Diff two eval runs and print a markdown flip table.

    python compare.py results/v1_baseline__gpt-4.1-mini.json \
                      results/v2_policy__gpt-4.1-mini.json

Output pastes straight into the README. The flips are the point of the
exercise: an aggregate pass rate that improves while an individual case
silently regresses is exactly what an eval suite exists to catch.
"""

import json
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load(path):
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return data["summary"], {r["id"]: r for r in data["results"]}


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)

    s_a, a = load(sys.argv[1])
    s_b, b = load(sys.argv[2])

    fixed, broken, unchanged = [], [], 0
    for cid in sorted(set(a) | set(b)):
        va = a.get(cid, {}).get("verdict", "-")
        vb = b.get(cid, {}).get("verdict", "-")
        if va == vb:
            unchanged += 1
        elif va == "FAIL" and vb == "PASS":
            fixed.append(cid)
        elif va == "PASS" and vb == "FAIL":
            broken.append(cid)

    print(f"### {s_a['prompt']} → {s_b['prompt']}  ({s_b['model']})\n")
    print(f"Pass rate {s_a['pass_rate']:.0%} → {s_b['pass_rate']:.0%}  ·  "
          f"fixed {len(fixed)}  ·  **broken {len(broken)}**  ·  unchanged {unchanged}\n")

    print("| case | subtype | " + s_a["prompt"] + " | " + s_b["prompt"] + " | |")
    print("|---|---|---|---|---|")
    for cid in sorted(set(a) | set(b)):
        ra, rb = a.get(cid, {}), b.get(cid, {})
        va, vb = ra.get("verdict", "-"), rb.get("verdict", "-")
        mark = "✅ fixed" if cid in fixed else "🔴 broken" if cid in broken else ""
        print(f"| {cid} | {rb.get('subtype') or ra.get('subtype') or ''} | {va} | {vb} | {mark} |")

    if broken:
        print("\n**Regressions — read these, do not just re-run:**\n")
        for cid in broken:
            r = b[cid]
            print(f"- `{cid}` — {r.get('reasoning', '')}")
            if r.get("quote"):
                print(f"  > {r['quote']}")


if __name__ == "__main__":
    main()
