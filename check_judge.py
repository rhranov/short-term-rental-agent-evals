#!/usr/bin/env python3
"""Validate the judge against three hand-written replies before trusting it.

    python check_judge.py --judge-model <judge>

Run this FIRST. A judge that is wrong at scale means re-reviewing every case,
and that is where an afternoon goes. If the borderline hedged case fails here,
fix the rubric before running anything else.
"""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from graders.judge import judge  # noqa: E402
from run_evals import make_client  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge-model", required=True, help="judge model, e.g. <judge>")
    ap.add_argument("--judge-base-url", default=None)
    ap.add_argument("--judge-api-key-env", default="OPENAI_API_KEY")
    args = ap.parse_args()

    cases = {c["id"]: c for c in
             json.loads((ROOT / "cases" / "cases.json").read_text(encoding="utf-8"))}
    sanity = json.loads((ROOT / "cases" / "judge_sanity.json").read_text(encoding="utf-8"))
    client = make_client(args.judge_base_url, args.judge_api_key_env)

    ok = True
    for item in sanity:
        case = cases[item["case_id"]]
        got = judge(client, args.judge_model, case, item["reply"])
        good = got["verdict"] == item["expected_verdict"]
        ok = ok and good
        print(f"[{'ok ' if good else 'BAD'}] {item['note']}")
        print(f"      expected {item['expected_verdict']}, got {got['verdict']}")
        print(f"      quote: {got.get('quote')}")
        print(f"      reason: {got.get('reasoning')}\n")

    print("judge sanity: PASS" if ok else "judge sanity: FAIL — fix the rubric first")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
