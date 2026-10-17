# Preflight submission closeout — 2026-10-17 KST

Scope: repository publication, judge README, form text, a silent live demo, and verification. Felix chose preview decision 1: keep disabled and expose no preview control on the resting first screen. Dashboard submission, narrated public video, pitch PDF, teammate retest and prize agreement remain with Felix/Claude.

## Track E — source publication

The 127 changed/untracked paths were committed as `dd12f279e364cbd217a4178b51c1d270cacebbdd` and pushed to main with the exact requested message and attribution. [Full hydrated path inventory](hydrated_git_status.txt). The initial read encountered 111 iCloud placeholders; explicit download requests materialized every file before scanning/staging. No placeholder was committed as empty data and no original was discarded.

The two history searches produced empty output before and after that commit. The indexed pre-commit scan was complete with zero hits; a separate token/project-identifier scan checked 277 files with zero hits. No .env, virtualenv, owner clip or sibling evidence file was staged. The one committed synthetic MP4 is 119,721 bytes. [History scans](history_scan_after_cd.json), [additional scan](additional_scan.json).

Tag `aibc-2026-submission` points to the C/D source commit above and was pushed before the subsequent documentation/demo-receipt commit. It freezes the source matching production; the later material commit does not change runtime inputs. No history rewrite or tag move was used.

Runtime remains `preflight-00016-tuk` at 100% traffic. Native Cloud Build `dbd67cc4-3e2e-4998-9df7-17ecf40e0b1e` succeeded. All 23 runtime inputs in that committed source match the native build archive byte-for-byte: input SHA256 `f080be0c815cbe460b0036b0a6a597201d6460dece9c73c8049af66f54a05d7c`; immutable image digest `sha256:2bf08f18e6576cda4c1698ea46f47f31aa9201f4ce52179e79a507c63cd58a3c`. No rebuild, candidate promotion or runtime setting change was necessary. [Native provenance](runtime_source_provenance.json), [commit-to-runtime mapping](track_e_source_match.json).

## Track F — public access

The repository is public. Anonymous HEAD returned HTTP 200 and a shallow clone succeeded with global/system config, credential helpers, askpass and terminal prompts disabled. [Receipt](public_access.json). No LICENSE was added because Felix did not select one; existing dataset attribution/NOTICE remains.

## Track G — judge-facing text

The README now starts with the product, source-linked exact user quotes, honest service statuses, architecture, measured limitations, five sample ranges and shared rate limit. The original technical sections remain below with historical receipts labelled. Internal acceptance identifiers stay in COMPLETION_REPORT; the README gate exits 0, all relative links resolve, and its prose is English. [Document checks](document_checks.json), [claim/source ledger](../submission_claims.json).

The brief description is 1,010 characters after replacing the preview clause with the disabled wording and removing only the unverified sentence “All code is hackathon-fresh.” The public-video placeholder and pitch-PDF placeholder deliberately remain. The deck file does not exist yet. [Paste fields](../../docs/submission-notes.md).

## Track H — recording

Both complete real takes passed all recorded interactions and full decode: take 1 **114.400 s**, take 2 **114.366667 s**. The shorter clean take 2 is `demo/preflight_demo_raw.mp4` (**1:54.367**, H.264, 30 fps, 1920×1080, silent, 10008012 bytes). Eight PNG key frames are exported to `demo/frames/`. Both takes, source WebM and the chosen MP4 remain local and ignored by Git; the reproducible script, record log and eight PNGs are committed. [Video verification](demo.json), [step-by-step record](../../demo/record_log.json).

The two fixed prompts showed different real bands: spoon/laptop 46.8%, wrestling 50.0%. The chosen rewrite dropped the estimate 46.8%→41.3% and Copy visibly succeeded. Clip review is explicitly a stored review reused, with 46.8%→46.8% risk; it is a genuine cached response, not a new quality measurement. All eight screenshots in both takes were visually inspected with no blocking issue.

The initial diagnostic capture encountered a recorder-side CSP evaluation error after one successful real prompt check; it was stopped, preserved under local ignored `demo_diagnostics/csp_probe`, and the recorder was repaired to use DOM locator waits. Site CSP and product source were unchanged. Two full takes then used the corrected script; their real results and errors are preserved. No step was retried inside a take, and no score, response, video time or page text was fabricated. Only a visible cursor overlay was injected.

## Preview and runtime checks

Preview stays disabled. `/api/status.preview` is false and `/preview` returns 503 before quota admission, cache access or model generation (0 image calls). Desktop and mobile resting first screens contain no preview button/link/control, so no UI edit was required. Disabled preview controls may appear after a prompt result; their tooltip is retained. [Status and code proof](status_preview_disabled.json), [first-screen checks](first_viewport_disabled.json).

The live battery ran once: 6/6 `/preflight` responses were HTTP 200 with verified tool/session workflows. **Warm ≤6.0 seconds FAIL:** maximum 9.715764 seconds; the other warm samples were 5.521130, 5.219659, 5.514284 and 5.227676 seconds. The script's older <10-second gate is not the requested ≤6-second gate. No retry or promotion followed the failure. `/postcheck` synthetic replay returned 200 in 0.617 seconds, used its exact original cached identity, made 0 model calls and created no new feedback. This operational smoke establishes no clip-review accuracy. [Battery gate](live_battery_gate.json), [responses](cloud_latency.json), [synthetic smoke](postcheck_synthetic.json).

Current local regression: **99 passed, 2 warnings, 11 subtests passed** on Python 3.12.14. The existing sibling cloud environment needed the already pinned Pillow 13.0.0 installed; source and dependency pins did not change. [Test receipt](tests.json).

## Spend

Authenticated Cloud Billing was refreshed for the console-selected date 2026-10-17, grouped by SKU. It shows posted total ₩0, approximately ₩1.9 of live Cloud Run estimates, and no image SKU row. This is **not zero incurred image cost**. A broader 2026-10-03–17 window now shows ₩457 posted for Gemini 3.1 Flash Lite Image Global Image Output; the view does not allocate it to KST today. Earlier ten observed successful image outputs have $0.336 output-only list price, excluding text input. This closeout made 0 new image-generation calls. [Spend receipt](spend.json).

## Remaining work / readiness

- Required warm latency bound failed; overall closeout battery is PARTIAL.
- Felix/Claude: export the organizer-template pitch PDF, add voice/edit, upload a public three-minute video, replace VIDEO_URL and the pitch placeholder, and submit the dashboard fields.
- Evaluation-period continued availability is a future operational requirement (2026-10-19–11-06), not proven by today's checks. The existing cumulative service cap remains 1,000; no budget/cap was raised.
- Preview activation/retry/fallback work was skipped under decision 1. Clip-review accuracy, calibrated present-model probabilities, savings and routing remain unmeasured or unsupported.
- LICENSE not added (no owner-selected license). No teammate message or dashboard submission was sent.
