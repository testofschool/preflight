# Preflight preview v3 — 2026-10-18 KST

Production serves **preflight-00021-sus at 100%**, with **preview disabled**. The preview candidate failed its registered gate; only the requested busy-copy change was deployed. The demo was re-recorded as one continuous take without still-preview beats. Source and tag are pushed; final receipts and eight frames accompany this report.

| Gate | Numerical result | Decision |
|---|---|---|
| V11a | Preview candidate: 129 passed, 0 failed, 11 subtests; final copy-only source: 99 passed, 0 failed, 11 subtests; 2 warnings each | Unit tests pass; provider contract defect described below |
| V11b | 0/10 cache checks run; 0 sample-preview warming calls; rewrite selection stopped after 2 HTTP 200 and 1 HTTP 503 | UNRUN; cache hits not established |
| V11c | 18/20 prompts dispatched: 5 HTTP 200 images >10 KiB, 13 HTTP 503; prompts 19–20 UNRUN | FAIL; required 19/20 not reached |
| V11d | Observed 18-request p95/max 3.733115 s; 18/18 returned before 60 s; 0 HTTP 504; 2 requests UNRUN | Full 20-request gate not established |
| V11e | Copy release: preflight 6/6 HTTP 200 and valid workflows; postcheck HTTP 200; preview=false; 18 objects, 7 colors, CTA bottom 837.4375 px; overflow checks 6/6 | PASS for the registered preview-off fallback |
| V11f | 44/45 allowed image-model calls: 31 primary, 13 fallback; unknown call counts 0; successful image-output list price $0.168 | Call cap respected |

Receipts: [candidate tests](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/tests.txt), [copy-only tests](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/tests_copy_only.txt), [candidate results](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/candidate_results.json), [six-request battery](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/preflight_copy_candidate.json), [synthetic smoke](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/postcheck_copy_candidate.json), [viewport and copy checks](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/ui_copy_candidate/summary.json).

**Fresh-prompt log.** Prompts were written before the run; SHA-256 `703c365b0e87f69d912e234f5e1fe1789f06607aba7a45b17217599c17d909a5`. All 40 primary/fallback cache keys were absent before execution. Minimum request-start spacing was 13.000367 s. Row numbers correspond to lines in [the fixed prompt file](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/fresh_prompts.txt); full prompt text and attempt receipts are in [the complete log](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/candidate_results.json).

P = `gemini-3.1-flash-lite-image` (1K); F = `gemini-3.1-flash-image` (0.5K requested). The model column identifies the last attempted model. A failed response contains no image.

| # | HTTP | Attempts | Fallback | Model | Seconds | Image bytes |
|---|---:|---:|---|---|---:|---:|
| 1 | 200 | 1 | false | P | 3.733115 | 191,413 |
| 2 | 200 | 1 | false | P | 3.161213 | 156,123 |
| 3 | 503 | 3 | true | F | 3.314822 | 0 |
| 4 | 503 | 3 | true | F | 2.537088 | 0 |
| 5 | 503 | 3 | true | F | 3.023913 | 0 |
| 6 | 200 | 1 | false | P | 3.364628 | 198,695 |
| 7 | 503 | 3 | true | F | 2.678610 | 0 |
| 8 | 503 | 3 | true | F | 1.416774 | 0 |
| 9 | 503 | 3 | true | F | 2.057424 | 0 |
| 10 | 503 | 3 | true | F | 2.893309 | 0 |
| 11 | 200 | 1 | false | P | 3.465277 | 199,528 |
| 12 | 503 | 3 | true | F | 2.156369 | 0 |
| 13 | 503 | 3 | true | F | 3.079768 | 0 |
| 14 | 503 | 3 | true | F | 2.117242 | 0 |
| 15 | 200 | 1 | false | P | 3.350497 | 139,028 |
| 16 | 503 | 3 | true | F | 1.874506 | 0 |
| 17 | 503 | 3 | true | F | 3.603483 | 0 |
| 18 | 503 | 3 | true | F | 3.133909 | 0 |
| 19 | UNRUN | — | — | — | — | — |
| 20 | UNRUN | — | — | — | — | — |

The next request could require three attempts: 44 + 3 would exceed 45. It was not dispatched, and no prompt was retried as a new test. The failed candidate's public tag was removed. Sample warming/cache verification was not resumed after the preview gate failed.

The primary returned 26 provider HTTP 429 responses. The fallback returned 5 provider HTTP 400 and 8 provider HTTP 429 responses. Our candidate also contained a confirmed API parameter error: it sent the display label `0.5K` as `image_size`; the documented wire value is `512`. The original fake test repeated that wrong value. A corrected archive passes 29 isolated tests and exposes 3 failures against the original implementation; it made 0 provider calls and was not deployed. Parameter-specific provider error text was not retained, so the exact cause of each 400 is not independently established. [Correction and test-gap receipt](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/candidate_corrected/report.json), [Google image-size documentation](https://ai.google.dev/gemini-api/docs/generate-content/image-generation?hl=en#generate_images_up_to_4k_resolution).

The first preview-on preflight battery returned 2 HTTP 200 then 1 HTTP 503, with 3 cases UNRUN; that failure is preserved. One bounded serial repeat returned 6/6 HTTP 200. The copy-only candidate then passed its own six-request battery: 4.991, 4.705, 5.051, 4.645, 4.891, 4.782 s. Postcheck reused the stored synthetic review with 0 model calls and created 0 new feedback records. These checks establish no clip-review accuracy. [Initial failure](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/preflight_candidate.json), [Bounded repeat](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/preflight_candidate_attempt2.json).

**Revisions and settings.**

| Revision | Traffic before → after | Preview | Timeout |
|---|---|---|---|
| preflight-00016-tuk | 100% → 0% | false | 40 s |
| preflight-00019-kow | 0% → 0%; failed tag removed | true on rejected candidate only | 60 s |
| preflight-00021-sus | 0% → 100% after V11e passed | false | 40 s |

`PREFLIGHT_PREVIEW_ENABLED`: false → true on the no-traffic candidate → false in production. Cloud Run timeout: 40 → 60 → 40 s. All final service-spec fields except the image are identical to baseline. Concurrency 80, CPU 1, memory 1 GiB, minimum instances 0, maximum 2, service region asia-southeast1 and image location global remain unchanged. Limits remain 5 previews/min, 60/day, code ceiling 500 and cumulative service allowance 1,000. Veo calls in this run: 0. [Promotion/configuration](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/promotion.json), [Disabled path and unchanged budget](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/disabled_preview_copy.json).

Only two runtime files changed. The final source restores the original preview implementation and changes its disabled/error copy. The UI also renders that exact copy below the disabled result control; the resting first screen is unchanged.

| File | Before bytes | After bytes | Delta |
|---|---:|---:|---:|
| `app.py` | 21,662 | 21,744 | +82 |
| `static/app.js` | 21,272 | 21,553 | +281 |
| `cloud/preview.py` | 3,022 | 3,022 | +0 |
| `Dockerfile` | 787 | 787 | +0 |
| `cloudbuild.yaml` | 145 | 145 | +0 |
| `scripts/release_cloud.py` | 6,645 | 6,645 | +0 |
| `requirements-cloud.lock` | 2,553 | 2,553 | +0 |
| `requirements-cloud.txt` | 136 | 136 | +0 |
| `requirements-dev.txt` | 48 | 48 | +0 |
| `requirements.lock` | 557 | 557 | +0 |
| `requirements.txt` | 141 | 141 | +0 |

All code/docs/verification-script byte deltas are recorded in [file_changes.json](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/file_changes.json). The remaining 21 runtime inputs are byte-identical, including risk, rewrite, postcheck, store, index and styles. A tooltip-only copy build was superseded before deployment when the visible result copy was added; both build receipts are retained. Before candidate building, hydration recorded 428 original files read and a final scan of 441 files with 0 dataless placeholders.

**Demo.** One take; 108.533333 s / 150 s maximum, 1920×1080, 30 fps, H.264, 0 audio streams, 8,772,303 bytes. Full decode passed. Exactly 8 PNGs replaced `demo/frames/`; timestamps replaced `demo/record_log.json`. All eight extracted frames were visually inspected.

MP4 path: `/Users/felix/Desktop/AI Builder Cup 2026/preflight/demo/preflight_demo_raw.mp4`

MP4 SHA-256: `075c5e0b94cea3aedf5f9e4b1021b389344354bfa045e45c368be0826c2f08f3`

| Beat | Start–end seconds |
|---|---|
| Home | 0.045–5.106 |
| Sample prompt → risk + why | 5.107–28.029 |
| Better prompt → risk drops → copy | 29.002–34.482 |
| Preview busy copy; no image requests | 36.002–42.423 |
| Clip upload → review → feedback-adjusted risk | 56.001–85.148 |
| Architecture image preview connection | 90.001–98.403 |

The rewrite shows 46.8% → 23.3% and Copy succeeded without reading the clipboard. The disabled-preview copy is visible; preview requests in the take: 0. Stored clip-review feedback remains 46.8% → 46.8%, with 0 new feedback records. Architecture correctly shows image preview **Not active**. The MP4 and previous backup remain local and ignored by Git; the source take is retained outside the repository. [MP4/ffprobe and visual verification](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/demo.json), [timestamp log](https://github.com/testofschool/preflight/blob/main/demo/record_log.json).

**Source, publication and spend.**

Production source commit and new tag target: `bdcdecdf6db6b0c2bebea8a35ed350de5f005940` (`aibc-2026-submission-v2`). Rejected candidate source: `110d608f1671834c39895c96b6aa4a477e1528b2`. Original tag `aibc-2026-submission` remains `dd12f279e364cbd217a4178b51c1d270cacebbdd`; no tag or history was rewritten. Later receipt/frame commits contain no runtime changes.

Native Cloud Build: `11f07900-29a9-4f6e-b819-da857f0144ee`; 23/23 runtime inputs match the production source commit. Post-promotion native traffic confirms 100% on the same revision.

Git runtime-source SHA-256: `ecb14dc207c9ba78d360f6b72f77dfa41c08011387c40180327d8a795743c793`

Cloud Build runtime-source SHA-256: `ecb14dc207c9ba78d360f6b72f77dfa41c08011387c40180327d8a795743c793`

Build/revision image digest: `sha256:1df156c771fff10e1a73f8f1b69194a16293985dcf2e2f1ec896a23dd5868444`

[Native provenance with both source hashes](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/source_match.json). Git-history secret scan before source push: 9 commits, 383 blobs, 0 hits, 0 errors; scans are repeated for final receipt publication. Anonymous HEAD returned HTTP 200; anonymous shallow clone exited 0 and matched the production commit; anonymous tag lookup confirmed both tag targets. [History scan](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/history_scan_source_release.json), [Anonymous access](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/public_access.json).

Brief description: **915 / 1,024 characters**. README and submission notes say preview is temporarily disabled; `<VIDEO_URL>` remains in both. Final description/link checks are in [document_checks.json](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/document_checks.json).

Five returned images have an output-only list price of **$0.168**, excluding text input. Pricing all 44 attempts as images at their respective models' prices would total $1.6266; the maximum-price bound is $1.98. Those two bounds are not incurred billing. Actual billed total is **UNMEASURED**. [Attempt ledger](https://github.com/testofschool/preflight/blob/main/reports/preview_v3/image_budget.json), [Google pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing).

**Not completed / limitations.** Preview-on activation failed; 10 sample cache checks and fresh prompts 19–20 were not run. The corrected `512` fallback has no live-provider validation. Preview-on still-image demo beats were omitted under the fail rule. Narration/public-video upload remain with Felix; `<VIDEO_URL>` is unchanged. An additional `/healthz` probe returned 404 on both old and new tagged revisions; it is outside V11e, and no health-route change was made. `/api/status` and the served JS returned 200, with JS bytes matching local source.
