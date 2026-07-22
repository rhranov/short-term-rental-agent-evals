#!/usr/bin/env python3
"""Run the commitment-policy eval suite against one system prompt and one model.

    python run_evals.py --prompt v2_policy --model <model>
    python run_evals.py --prompt v2_policy --model <local-model> \
        --base-url http://localhost:8000/v1 --api-key-env LOCAL_API_KEY

Writes results/<prompt>__<model>.json and prints a summary. Latency and token
counts are captured per call because cost and latency are platform concerns,
not afterthoughts.
"""

import argparse
import json
import os
import pathlib
import sys
import time

from openai import OpenAI

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from graders.deterministic import check_off_platform  # noqa: E402
from graders.judge import judge  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent


def load_cases(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def load_prompt(name):
    return (ROOT / "prompts" / f"{name}.md").read_text(encoding="utf-8")


def make_client(base_url, api_key_env):
    key = os.environ.get(api_key_env)
    if not key:
        sys.exit(f"Missing {api_key_env}. Copy .env.example and export it.")
    return OpenAI(api_key=key, base_url=base_url) if base_url else OpenAI(api_key=key)


def get_reply(client, model, system_template, case):
    system = system_template.replace(
        "{context}", json.dumps(case.get("context", {}), ensure_ascii=False)
    )
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": case["guest_message"]},
        ],
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    usage = getattr(resp, "usage", None)
    return {
        "reply": resp.choices[0].message.content.strip(),
        "latency_ms": elapsed_ms,
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True, help="prompt file stem, e.g. v2_policy")
    ap.add_argument("--model", required=True, help="model under test")
    ap.add_argument("--cases", default=str(ROOT / "cases" / "cases.json"))
    ap.add_argument("--base-url", default=None, help="OpenAI-compatible endpoint")
    ap.add_argument("--api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--judge-model", required=True, help="judge model, e.g. <judge>")
    ap.add_argument("--judge-base-url", default=None)
    ap.add_argument("--judge-api-key-env", default="OPENAI_API_KEY")
    ap.add_argument("--replies-file", default=None,
                     help="JSON file of [{id, reply}]; skips the API call for the "
                          "model under test and grades these replies instead")
    args = ap.parse_args()

    cases = load_cases(args.cases)
    system_template = load_prompt(args.prompt)
    sut = None if args.replies_file else make_client(args.base_url, args.api_key_env)
    judge_client = make_client(args.judge_base_url, args.judge_api_key_env)

    manual_replies = {}
    if args.replies_file:
        manual_replies = {
            r["id"]: r["reply"]
            for r in json.loads(pathlib.Path(args.replies_file).read_text(encoding="utf-8"))
        }

    results = []
    for case in cases:
        if args.replies_file:
            if case["id"] not in manual_replies:
                sys.exit(f"No manual reply for case {case['id']} in {args.replies_file}")
            out = {"reply": manual_replies[case["id"]], "latency_ms": None,
                   "prompt_tokens": None, "completion_tokens": None}
        else:
            out = get_reply(sut, args.model, system_template, case)

        hit, evidence = check_off_platform(out["reply"])
        if hit:
            grade = {
                "verdict": "FAIL",
                "quote": evidence,
                "reasoning": "deterministic off-platform check",
                "grader": "deterministic",
            }
        else:
            grade = judge(judge_client, args.judge_model, case, out["reply"])
            grade["grader"] = "llm_judge"

        row = {"id": case["id"], "subtype": case.get("subtype"), **out, **grade}
        results.append(row)
        lat_str = f"{row['latency_ms']}ms" if row["latency_ms"] is not None else "n/a"
        print(f"{row['id']:<8} {row['verdict']:<12} {lat_str:>7}  "
              f"{(row.get('quote') or '')[:60]}")

    passed = sum(r["verdict"] == "PASS" for r in results)
    ungradeable = sum(r["verdict"] == "UNGRADEABLE" for r in results)
    lats = sorted(r["latency_ms"] for r in results if r["latency_ms"] is not None)
    p95 = lats[min(int(len(lats) * 0.95), len(lats) - 1)] if lats else 0
    completion = sum(r["completion_tokens"] or 0 for r in results)

    summary = {
        "prompt": args.prompt,
        "model": args.model,
        "judge_model": args.judge_model,
        "n": len(results),
        "pass": passed,
        "fail": len(results) - passed - ungradeable,
        "ungradeable": ungradeable,
        "pass_rate": round(passed / len(results), 3) if results else 0,
        "p95_latency_ms": p95,
        "total_completion_tokens": completion,
    }

    tag = f"{args.prompt}__{args.model}".replace("/", "-")
    path = ROOT / "results" / f"{tag}.json"
    path.write_text(
        json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n" + json.dumps(summary, indent=2))
    print(f"\nwrote {path.relative_to(ROOT)}")
    if ungradeable:
        print(f"WARNING: {ungradeable} ungradeable — those cases are ambiguous, rewrite them.")


if __name__ == "__main__":
    main()
