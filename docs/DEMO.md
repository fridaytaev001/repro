# Chunk 1 operator guide

This is evaluator material, not input to the future investigator.

## Real seeded defect

1. Open the store and click **Your bag**.
2. Apply **SAVE10**. Subtotal is $100; discount is $10; total is $90.
3. Continue to review. The total remains $90. This ordinary path is correct.
4. Click **Edit address**, change the street, then **Save address**.
5. The discount disappears and the total becomes $100. This violates store rule v1.
6. Place the synthetic order to verify checkout completes. Nothing is charged.

The intentional fault is in the demo store's address-save state transition. It is a real application state change, not a simulated event feed. Keep it until the isolated repair milestone; do not fix the target during the scaffold PR.

## Correct behavior control

Reset the session and try VIP20. It is member-only, so this guest cart correctly rejects it. If SAVE10 is already active, a rejected VIP20 attempt preserves SAVE10.

## Report a problem

Use the report button in checkout or the bottom dock. Submit a complaint and expected behavior. The case page reads a saved JSON receipt. Restarting the service preserves it. No Crusoe model, investigator, verifier, or repairer runs in Chunk 1.

## Verification

Run the documented pytest commands. Browser assertions confirm the actual $90 → $100 change, the correct control, session isolation/reset, checkout completion, and report persistence. These are developer/evaluator tests, not evidence that an autonomous agent has discovered the bug.
