# short-term-rental-agent-evals

An evaluation harness for AI assistants that reply to guests on behalf of
short-term rental property managers.

It tests one thing: **does the assistant commit to things it has no authority to
commit to?** Late check-out, refunds, discounts, off-platform contact — the
answers that cost the host money or breach channel rules.

**An explicit commitment policy took all 5 models tested — from Claude Opus
to a local open-weight model — to 100% pass, up from a 74–100% baseline,
with zero regressions.**

---

## Why this exists

Guest messaging is the highest-volume AI surface in property management, and the
failure that matters is not a clumsy sentence — it is an assistant that agrees
to a 1pm check-out on a same-day turnaround, or issues a refund nobody
authorised. Those failures are invisible to a fluency check and expensive in
aggregate.

A property manager cannot inspect every message. What they need is a way to say
"this class of mistake happens less than X% of the time, and we would notice if
that changed." That is an evaluation problem, not a prompting problem, and it is
the kind of capability a platform team builds once for every product team to
consume.

`policy.md` is the behavioural contract. Everything else in this repo exists to
measure adherence to it.

## Results

19 cases, 5 models (Claude Sonnet 5, Opus 4.8, Haiku 4.5, Fable 5, and a
locally-hosted Qwen3.6-35B-A3B), each run against both prompt versions and
graded by the same judge.

| model | v1_baseline pass rate | v2_policy pass rate | fixed | broken |
|---|---|---|---|---|
| Sonnet 5 | 84.2% | 100.0% | 3 | 0 |
| Opus 4.8 | 100.0% | 100.0% | 0 | 0 |
| Haiku 4.5 | 84.2% | 100.0% | 3 | 0 |
| Fable 5 | 89.5% | 100.0% | 2 | 0 |
| Qwen3.6-35B-A3B (local) | 73.7% | 100.0% | 5 | 0 |

*fixed = failed under v1, passed under v2 · broken = the reverse (a real
regression)*

Every model reaches 100% under the hardened prompt — the weaker the
baseline, the bigger the gain. Two extra cases confirm the hardened prompt
doesn't over-refuse facts it's allowed to state (checkout time, wifi
password) — all 5 models answered directly.

*Claude-family rows: blind isolated-agent replies, no API key used. Qwen
row: a real timed API call.*

### The regression

None found — the flip table is zero broken across all 5 models. One case
looked like a regression during development but turned out to be a broken
test criterion, not real model behavior, and was deleted rather than kept.
Multi-turn pressure and borderline over-refusal phrasing are untested (see
Roadmap).

## What this deliberately does not do

- **One failure category.** Unauthorised commitments only — hallucinated
  facts, escalation, tone, and language are roadmap items, not implemented.
- **Synthetic data.** No real guest messages, ever. Absolute scores aren't
  meaningful, only deltas between prompt versions. Cases were grid-generated
  locally (persona × stage × register × language) and reviewed by hand.
- **Judge not validated against human labels.** `check_judge.py`'s 3-case
  sanity check is a smoke test, not an agreement study — that's on the roadmap.
- **Small n.** 19 cases. Enough to demonstrate the mechanism, not enough to
  make a confident claim about any model.
- **No production concerns.** No retries, no tests, no cost ceiling, no
  concurrency.

## Design notes

- **Criterion-referenced judging.** Each case carries its own `violation_if`/
  `pass_if`, graded against that stated criterion — not the judge's own view
  of the policy. The single biggest accuracy lever in the harness.
- **Quote before verdict.** The judge writes the deciding quote and reasoning
  before the verdict, so it can't rationalise a verdict it already picked.
- **Separation of families.** Case generator, model under test, and judge are
  three different model families, by design — one family grading itself
  measures self-preference, not policy adherence. The Qwen row is the
  exception: the same local model generated the cases, answered as the
  model under test, and judged itself. Disclosed here rather than hidden;
  treat that row's result as the weakest-evidenced one in the table.
- **Not everything needs a model.** Off-platform contact (messenger name,
  email, phone number) is caught by regex before any judge call — cheaper,
  just as reliable.
- **Latency and tokens are captured per call** — for real API calls. That's
  true for the Qwen row; the four Claude-family rows have no latency data,
  for the same reason they have no API key (see Methodology above).

## Configuration

No endpoint, key, or model is hardcoded anywhere in this repo. Set
`OPENAI_API_KEY` (hosted) or `LOCAL_API_KEY` (self-hosted, per
`.env.example`), then pass `--model` / `--base-url` for whichever provider
you're using — bring your own inference.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env && export $(cat .env | xargs)

# 1. validate the judge before trusting it
python check_judge.py --judge-model <judge>

# 2. run both prompt versions
python run_evals.py --prompt v1_baseline --model <model>
python run_evals.py --prompt v2_policy   --model <model>

# 3. diff them
python compare.py results/v1_baseline__<model>.json \
                  results/v2_policy__<model>.json
```

Against a local OpenAI-compatible endpoint:

```bash
python run_evals.py --prompt v2_policy --model <local-model> \
    --base-url http://localhost:8000/v1 --api-key-env LOCAL_API_KEY
```

Case generation, which runs locally:

```bash
python tools/generate_cases.py --model <local-model> --n 15
# review cases/cases_draft.json by hand, merge the keepers into cases/cases.json
```

## Layout

```
policy.md                  the behavioural contract under test
cases/cases.json           eval cases, one criterion each
cases/judge_sanity.json    three hand-written replies to validate the judge
cases/manual_replies_*.json  raw blind-agent replies behind the Claude-family results
prompts/                   v1 baseline, v2 policy-hardened, judge rubric
graders/deterministic.py   regex checks that need no model
graders/judge.py           criterion-referenced LLM judge
tools/generate_cases.py    grid-sampled generation against a local model
run_evals.py               runner — writes results/ and a summary
compare.py                 flip table between two runs
```

## Possible next steps for improvement

- Judge agreement study — multiple judge models, divergences checked against
  human labels.
- Hallucinated property facts, failure to escalate a maintenance emergency —
  two more failure categories.
- Cost-per-conversation pricing for the open-weight model now that its pass
  rate is measured.
- Per-language slicing — non-English pass rates are the ones nobody checks.
- Multi-turn pressure and messier over-refusal phrasing — only single-turn
  asks and two clean probes were tested here.

## Licence

MIT.
