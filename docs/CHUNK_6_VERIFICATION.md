# Chunk 6: delivery verification

October 17, 2026: repository metadata reports `fridaytaev001/repro` as public. A clickable GitHub repository resource was added and visibly verified in the Linear project's Overview. This is a project resource link, not a claim about installing additional webhooks/integrations.

## Delivered locally

- `.local/delivery/repro-demo.webm`: captioned, silent recorded walkthrough of the real target and actual saved Crusoe proof; final duration **60.00 seconds**, 1360×900, VP9, 6,063,287 bytes. Extra closing frames were trimmed with FFmpeg. A frame showing actual repair proof and the contribution caption was visually inspected.
- `.local/delivery/repro-evidence.zip`: actual fixed-verified case export, 39 members, 12,056,441 bytes at final packaging. Includes frozen replay, opposite tests, actual screenshots/traces, proposed diff, process receipts, proof archives and its file manifest.
- `.local/delivery/repro-report.md` and `.json`: engineer reports scoped to the isolated repair.
- `.local/delivery/delivery-manifest.json`: actual hashes and sizes. These artifacts stay ignored; they do not exist automatically on a fresh clone.

The recorder starts no inference or repair and verifies the baseline defect and saved repaired-case heading before recording success labels. Encoding may add closing padding on regeneration; trim it if a strict duration is required. The delivered recording was independently checked as 60.00 seconds.

## Setup and documentation

`Start_Repro.cmd` starts the prepared Windows virtual environment and opens the store. `python -m scripts.run_local` works cross-platform, sets the workspace browser cache when present, and safely reuses a running local Repro server. Help and existing-server startup were exercised.

`python -m scripts.configure` offers a masked local prompt and writes only ignored `.env`; no editor is required. No credential was entered or displayed during packaging. Repair uses Playwright's bundled Node when PATH lacks Node; the rejection-path test exercised that fallback.

Architecture, demo scripts, source attribution, dependency license metadata, copy-ready description and submission checklist are in `docs/ARCHITECTURE.md`, `DEMO_RUNBOOK.md`, `DEPENDENCIES.md`, and `SUBMISSION.md`. No project-wide license grant was invented. The original FIELD target remains deliberately buggy; verified repair applies to its isolated copy.

## Checks and limits

- Repair implementation: 59 full-suite checks and GitHub CI passed.
- Final delivery changes: 45 non-browser checks passed (14 browser checks deselected), including bundled-Node fallback. Script compilation, startup and media inspection passed. The delivery PR runs the complete suite in CI too.
- Hygiene: 58 tracked/planned source files and Git patch history contained no match for the configured credential. `.env` is ignored. The key itself was never printed by that check.
- Public visibility and the Linear repository link were verified.

The organizer's form, teammate information and public video hosting are **not completed**. The supplied participant guide's deadline/URLs are recorded as supplied; event details/form were not readable through the web tool. This is review/submission-ready source and local media, not a claim of event entry. Upload the video to an accepted destination, check access and submit the form separately.
