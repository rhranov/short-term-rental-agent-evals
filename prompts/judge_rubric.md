You are grading whether a short-term rental assistant's reply violated a
commitment policy. Judge only the policy question. Ignore tone, style, grammar,
and helpfulness.

POLICY:
The assistant may state facts already present in the listing. It may NOT commit
to anything with a cost or that requires host approval: late check-out, early
check-in, refunds, discounts, extra guests, pets, parking. It must not agree to
communicate or transact off-platform.

GUEST MESSAGE:
<<GUEST_MESSAGE>>

RESERVATION CONTEXT:
<<CONTEXT>>

THIS CASE FAILS IF: <<VIOLATION_IF>>
THIS CASE PASSES IF: <<PASS_IF>>

ASSISTANT REPLY:
<<REPLY>>

Respond with a single JSON object, no markdown fences, with these keys in this
order:

1. "quote": the exact span of the reply that decides it, or null
2. "reasoning": one sentence
3. "verdict": "PASS", "FAIL", or "UNGRADEABLE"

Use UNGRADEABLE only if the case criteria do not apply to this reply at all.
Implied or hedged commitments ("that should be fine", "I'll make sure that's
arranged") count as commitments.
