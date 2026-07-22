#!/usr/bin/env python3
"""Generate draft eval cases against a local OpenAI-compatible endpoint.

    python tools/generate_cases.py --model <local-model> \
        --base-url http://localhost:8000/v1 --n 15

Writes cases/cases_draft.json. Review by hand, keep the unambiguous ones, merge
into cases/cases.json. The review step is the point — do not skip it.

Generation runs locally rather than on a hosted API for cost and because no
guest data of any kind, real or paraphrased, should leave the machine.
"""

import argparse
import itertools
import json
import pathlib
import random
import sys

from openai import OpenAI

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROMPT = (ROOT / "tools" / "generation_prompt.md").read_text(encoding="utf-8")
TEMPLATE = PROMPT.split("```")[1]

GRID = {
    "PERSONA": ["first_time_guest", "seasoned_traveller", "pressure_escalator",
                "non_native_speaker", "group_organiser"],
    "TRIP_STAGE": ["pre_booking", "pre_arrival", "mid_stay", "checkout", "post_stay"],
    "PROPERTY": ["city_apartment", "rural_cottage", "multi_unit_building"],
    "REGISTER": ["polite", "terse", "angry", "manipulative", "confused"],
    "LANGUAGE": ["en", "en", "de", "fr", "es"],
    "SUBTYPE": ["late_checkout", "early_checkin", "refund", "discount",
                "extra_guests", "pets", "parking", "off_platform"],
}


def cells(n, seed=0):
    rng = random.Random(seed)
    keys = list(GRID)
    seen, out = set(), []
    while len(out) < n:
        cell = tuple(rng.choice(GRID[k]) for k in keys)
        if cell in seen:
            continue
        seen.add(cell)
        out.append(dict(zip(keys, cell)))
    return out


def extract_json(raw):
    """The judge module's parser already tolerates fences and stray prose."""
    text = raw.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--api-key-env", default="LOCAL_API_KEY")
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    import os
    client = OpenAI(api_key=os.environ.get(args.api_key_env, "not-needed"),
                    base_url=args.base_url)

    drafts = []
    for i, cell in enumerate(cells(args.n, args.seed), start=1):
        prompt = TEMPLATE
        for k, v in cell.items():
            prompt = prompt.replace(f"<<{k}>>", v)

        resp = client.chat.completions.create(
            model=args.model,
            temperature=1.0,
            messages=[{"role": "user", "content": prompt}],
        )
        obj = extract_json(resp.choices[0].message.content)
        if not obj or "guest_message" not in obj:
            print(f"  skipped cell {i}: unparseable")
            continue

        obj.update({
            "id": f"gen-{i:03d}",
            "category": "unauthorised_commitment",
            "subtype": cell["SUBTYPE"],
            "language": cell["LANGUAGE"],
            "persona": cell["PERSONA"],
            "trip_stage": cell["TRIP_STAGE"],
        })
        drafts.append(obj)
        print(f"[{i:>3}] {cell['SUBTYPE']:<14} {cell['LANGUAGE']}  "
              f"{obj['guest_message'][:70]}")

    out = ROOT / "cases" / "cases_draft.json"
    out.write_text(json.dumps(drafts, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(drafts)} drafts to {out.relative_to(ROOT)}")
    print("Review by hand. Expect to discard roughly a third.")


if __name__ == "__main__":
    main()
