"""LLM judge for the commitment policy.

Design choices that matter more than the wording:

1. Criterion-referenced. The per-case `violation_if` / `pass_if` clauses are
   passed into the prompt, so the judge compares a reply against a stated
   criterion instead of exercising its own view of the policy. This is the
   single biggest accuracy lever in the harness.

2. Quote and reasoning are emitted before the verdict. A model that writes its
   verdict first will rationalise it afterwards. Quote-first also makes human
   review fast — you scan quotes, not full replies.

3. The judge never sees which prompt version produced the reply. Otherwise part
   of what you measure is the label.
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUBRIC = (ROOT / "prompts" / "judge_rubric.md").read_text(encoding="utf-8")


def build_prompt(case: dict, reply: str) -> str:
    """Fill the rubric. Uses replace, not str.format — the rubric contains JSON
    braces and format() would choke on them."""
    out = RUBRIC
    out = out.replace("<<GUEST_MESSAGE>>", case["guest_message"])
    out = out.replace("<<CONTEXT>>", json.dumps(case.get("context", {})))
    out = out.replace("<<VIOLATION_IF>>", case["violation_if"])
    out = out.replace("<<PASS_IF>>", case["pass_if"])
    out = out.replace("<<REPLY>>", reply)
    return out


def parse_verdict(raw: str) -> dict:
    """Tolerate fenced JSON and leading prose."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {"quote": None, "reasoning": "unparseable judge output",
                "verdict": "UNGRADEABLE", "raw": raw}
    try:
        parsed = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {"quote": None, "reasoning": "invalid JSON from judge",
                "verdict": "UNGRADEABLE", "raw": raw}

    verdict = str(parsed.get("verdict", "")).upper()
    if verdict not in ("PASS", "FAIL", "UNGRADEABLE"):
        verdict = "UNGRADEABLE"
    return {
        "quote": parsed.get("quote"),
        "reasoning": parsed.get("reasoning", ""),
        "verdict": verdict,
    }


def judge(client, model: str, case: dict, reply: str) -> dict:
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[{"role": "user", "content": build_prompt(case, reply)}],
    )
    return parse_verdict(resp.choices[0].message.content)
