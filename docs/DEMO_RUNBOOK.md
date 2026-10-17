# Demo runbooks and backup

## One-minute recorded walkthrough

The generated video is explicitly captioned **recorded walkthrough of saved real Crusoe evidence**, not a new live model execution. It shows real browser behavior and actual persisted results.

- 0–8 seconds: Repro and the synthetic FIELD store. Explain that customers rarely remember exact steps.
- 8–22 seconds: apply SAVE10, show $90, edit from review, show actual $100 discount loss.
- 22–35 seconds: saved live case, frozen rules, failed remembered steps, changed hypothesis and independent confirmation.
- 35–48 seconds: isolated repair, baseline failure, candidate pass and passing controls. Original demo remains buggy.
- 48–60 seconds: downloadable engineer handoff and clear scope/new-contribution statement.

Run `python -m scripts.record_demo --case <fixed-verified-case-id>` against the running local app to create `.local/delivery/repro-demo.webm`. The script verifies the displayed baseline defect and saved repair heading before recording success captions. It starts no model calls and submits no new reports. An existing `fixed_verified` case is required.

## Three-minute live presentation

1. **0:00–0:25 — Problem:** vague complaint → costly manual reproduction. Open the original store and show the real seeded defect, with review coupon entry hidden.
2. **0:25–1:10 — Investigation:** submit a synthetic vague complaint if provider/network budget allows. While it runs, show the saved genuine recovery case with actual events; distinguish the new live attempt from saved evidence.
3. **1:10–1:45 — Verification:** explain that the model proposes and the host proves. Show fresh-session observed values and the versioned criteria hash. VIP20 guest rejection is an expected control, not a bug.
4. **1:45–2:25 — Repair:** show actual saved live patch and protected baseline-fail/candidate-pass receipts. Repair writes only the isolated copy; originals/tests/fixtures are not model-writable.
5. **2:25–3:00 — Handoff and limits:** download report/replay/tests/patch/evidence, explain opposite reproduction/regression assertions. State small sample size, loopback-only scope, labelled seeded fixture, and new hackathon implementation.

## Backup when Wi-Fi or provider access fails

Use `.local/delivery/repro-demo.webm` and `.local/delivery/repro-evidence.zip`. The latter is an actual exported case bundle with hashes and proof, not staged activity. Browser replay requires no API key or inference; run the exported reproduction test against the original target. A failing regression test on that target is intentional. Do not present the recording or saved timeline as a new live request.

For the current build, the independently confirmed and repaired recovery case is `1f9a01f6-33eb-495a-8f45-fedbb3b045b6`. The earlier confirmed case is `36847863-3e9a-4fe9-8868-99dedeb50bce`; the correct-behavior control is `1029c2e0-85f0-4847-b818-6476064a2c06`. These local IDs do not exist automatically on a fresh clone; submit a new report there.
