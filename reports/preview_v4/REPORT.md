# Preflight preview v4 — evidence report (release work pending)

Snapshot: **2026-10-18T11:07:29+09:00**. This document records completed measurements and leaves unfinished release work as **PENDING**. Production promotion, production self-QA, the v4 demo and final repository receipts are not claimed complete.

The selected release plan is **samples-only** on candidate `preflight-00025-lij`. All 60 preregistered probe calls are complete: P1 returned 8/20 successful images, P2 6/20 and P3 6/20. No arm reaches 19/20, so no live arm is selected. The final decision is recorded; candidate gates and promotion remain PENDING.

The required message is: **Image preview — Active for sample prompts (saved stills); live generation limited**. Five sample decisions are saved: four lower-risk rewrites and one honest unchanged result for “indoor gymnasium”. Saved images are labeled with their generation date, 0 model calls and $0.00. Typed prompts retain the live Gemini rewrite. An uncached still in samples-only mode says: “Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works.”

## V-A through V-F

| Gate | Status at this snapshot | Measured evidence | Remaining work |
| --- | --- | --- | --- |
| V-A | PENDING final receipt | Frozen-runtime suite: 129 passed, 11 subtests, 2 warnings in 4.52 s. Separate promotion-guard battery: 12/12 passed. Mocked browser contracts: 28/28 passed. Offline probe runner: 12/12; warm runner: 5/5. | Record final complete test run and bind it to the final source. |
| V-B | PENDING | Warm API preparation: 10/10 usable sample actions, 9 unique stored texts; this is not the real-browser gate. | Click all 5 samples × original/rewrite through a fresh real browser on the no-traffic candidate; require 10/10 hit, model_calls=0 and exact labels. |
| V-C | N/A — samples-only | All 60 probe calls are complete; every arm fails 19/20. No live UI calls are required for the samples-only release. | No live path will be promoted. |
| V-D | PENDING final preview battery | All 10 warm API responses HTTP 200; maximum 13.662 s; 0 HTTP 504 in warm rows. | Verify every candidate and production preview response remains <45 s with no 504. |
| V-E | PASS measured components; final gate binding PENDING | Final candidate typed prompts: 6/6 HTTP 200, 6/6 live rewrites, 6/6 verified workflows, 6/6 <45 s; repeated prompt produced two different rewrites. Postcheck smoke: HTTP 200, 17.896 s. First viewport: 18 objects, 7 colors, CTA bottom 837.4375 px. | Bind final candidate revision/image to these receipts; retain the smoke-test limitations. |
| V-F | PENDING final accounting | 71 durable v4 reservations; 71 recorded results; 69 known model attempts; 2 known zero-call responses; 0 reserved outcome(s) pending at snapshot. V4 model budget 85. | Confirm the final unchanged model ledger/list-price total and read the daily admission counter after QA/demo. |

Test receipts: [runtime tests](tests_runtime_frozen.txt), [prior full test output](tests_final.txt), [mocked UI contracts](ui_contract.json), [offline probe tests](offline_probe_tests.log), [offline warm tests](offline_warm_tests.log), [scope and promotion-guard audit](release_scope_audit.json). Mocked tests do not establish provider reliability.

## Probe registration and selection

The original preregistration contains 60 distinct prompt files, 20 per arm, a minimum 15-second start interval, one provider attempt per row, and the pass rule of at least 19/20 HTTP-200 images larger than 10,240 bytes. P1 runs with the Priority header, P2 uses its separately verified Vertex global location, and P3 uses the corrected `512` wire value. Different models may overlap; the P1 model has no other image-producing path during its arm. See [preregistration](preregistration.json), [official sources](official_sources.json) and [raw ledger](call_ledger.jsonl).

The human budget amendment sets **85 image attempts for v4**, excluding the preserved 44 v3 attempts. It retains the 10 warm / 60 probe / 15 QA maxima and all runtime caps. The sealed original plan and existing results remain unchanged. [Budget amendment](budget_amendment_001.json).

| Arm | Model | Rows completed | Images >10 KiB | HTTP counts | Minimum start spacing (s) | Known list-price total | Reliability result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | gemini-3.1-flash-lite-image | 20/20 | 8/20 | {'200': 8, '429': 12} | 15.101 | $0.32265655 | FAIL |
| P2 | gemini-2.5-flash-image | 20/20 | 6/20 | {'200': 6, '429': 14} | 15.101 | $0.2322747 | FAIL |
| P3 | gemini-3.1-flash-image | 20/20 | 6/20 | {'200': 6, '429': 14} | 15.100 | $0.2690385 | FAIL |

Selection rule: highest successful-image count among passing arms, then lowest response-based list price. All three arms fail the reliability rule, so the selected release plan is samples-only. All 60 raw rows, response-based pricing and the no-live decision are complete. [Final decision](probe_decision.json), [final probe/spend summary](final_probe_spend_summary.json), [per-row cost supplement](PROBE_RESULTS.md).

Raw per-arm rows follow. “Not returned” means the traffic field was absent, usually on a non-200 response. Local receipt errors remain visible separately from the provider status; they are not counted as provider retries.

### P1 — `gemini-3.1-flash-lite-image`

| Attempt | Provider HTTP | Model | Latency (s) | Image bytes | Traffic type | Receipt note |
| --- | --- | --- | --- | --- | --- | --- |
| P1-01 | 200 | gemini-3.1-flash-lite-image | 4.198 | 224371 | ON_DEMAND_PRIORITY | ValueError; cost/image path derived from preserved bytes |
| P1-02 | 200 | gemini-3.1-flash-lite-image | 4.134 | 127960 | ON_DEMAND_PRIORITY | ValueError; cost/image path derived from preserved bytes |
| P1-03 | 200 | gemini-3.1-flash-lite-image | 3.760 | 142361 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P1-04 | 200 | gemini-3.1-flash-lite-image | 3.567 | 238192 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P1-05 | 429 | gemini-3.1-flash-lite-image | 0.292 | 0 | Not returned | ProviderHTTPError |
| P1-06 | 429 | gemini-3.1-flash-lite-image | 0.329 | 0 | Not returned | ProviderHTTPError |
| P1-07 | 200 | gemini-3.1-flash-lite-image | 3.699 | 193767 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P1-08 | 429 | gemini-3.1-flash-lite-image | 0.309 | 0 | Not returned | ProviderHTTPError |
| P1-09 | 429 | gemini-3.1-flash-lite-image | 0.313 | 0 | Not returned | ProviderHTTPError |
| P1-10 | 429 | gemini-3.1-flash-lite-image | 0.312 | 0 | Not returned | ProviderHTTPError |
| P1-11 | 200 | gemini-3.1-flash-lite-image | 3.882 | 233404 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P1-12 | 429 | gemini-3.1-flash-lite-image | 0.292 | 0 | Not returned | ProviderHTTPError |
| P1-13 | 429 | gemini-3.1-flash-lite-image | 0.308 | 0 | Not returned | ProviderHTTPError |
| P1-14 | 429 | gemini-3.1-flash-lite-image | 0.326 | 0 | Not returned | ProviderHTTPError |
| P1-15 | 200 | gemini-3.1-flash-lite-image | 3.622 | 156926 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P1-16 | 429 | gemini-3.1-flash-lite-image | 0.302 | 0 | Not returned | ProviderHTTPError |
| P1-17 | 429 | gemini-3.1-flash-lite-image | 0.306 | 0 | Not returned | ProviderHTTPError |
| P1-18 | 429 | gemini-3.1-flash-lite-image | 0.305 | 0 | Not returned | ProviderHTTPError |
| P1-19 | 200 | gemini-3.1-flash-lite-image | 3.455 | 114487 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P1-20 | 429 | gemini-3.1-flash-lite-image | 0.308 | 0 | Not returned | ProviderHTTPError |

### P2 — `gemini-2.5-flash-image`

| Attempt | Provider HTTP | Model | Latency (s) | Image bytes | Traffic type | Receipt note |
| --- | --- | --- | --- | --- | --- | --- |
| P2-01 | 200 | gemini-2.5-flash-image | 15.329 | 1172955 | ON_DEMAND | — |
| P2-02 | 200 | gemini-2.5-flash-image | 6.598 | 947000 | ON_DEMAND | — |
| P2-03 | 429 | gemini-2.5-flash-image | 4.597 | 0 | Not returned | ProviderHTTPError |
| P2-04 | 429 | gemini-2.5-flash-image | 4.741 | 0 | Not returned | ProviderHTTPError |
| P2-05 | 200 | gemini-2.5-flash-image | 11.867 | 1191444 | ON_DEMAND | — |
| P2-06 | 429 | gemini-2.5-flash-image | 5.217 | 0 | Not returned | ProviderHTTPError |
| P2-07 | 429 | gemini-2.5-flash-image | 5.564 | 0 | Not returned | ProviderHTTPError |
| P2-08 | 429 | gemini-2.5-flash-image | 5.044 | 0 | Not returned | ProviderHTTPError |
| P2-09 | 200 | gemini-2.5-flash-image | 8.626 | 1223785 | ON_DEMAND | — |
| P2-10 | 429 | gemini-2.5-flash-image | 5.536 | 0 | Not returned | ProviderHTTPError |
| P2-11 | 429 | gemini-2.5-flash-image | 5.059 | 0 | Not returned | ProviderHTTPError |
| P2-12 | 429 | gemini-2.5-flash-image | 4.720 | 0 | Not returned | ProviderHTTPError |
| P2-13 | 200 | gemini-2.5-flash-image | 8.756 | 1049747 | ON_DEMAND | — |
| P2-14 | 429 | gemini-2.5-flash-image | 5.234 | 0 | Not returned | ProviderHTTPError |
| P2-15 | 429 | gemini-2.5-flash-image | 5.201 | 0 | Not returned | ProviderHTTPError |
| P2-16 | 429 | gemini-2.5-flash-image | 4.676 | 0 | Not returned | ProviderHTTPError |
| P2-17 | 200 | gemini-2.5-flash-image | 9.016 | 1068512 | ON_DEMAND | — |
| P2-18 | 429 | gemini-2.5-flash-image | 4.904 | 0 | Not returned | ProviderHTTPError |
| P2-19 | 429 | gemini-2.5-flash-image | 5.339 | 0 | Not returned | ProviderHTTPError |
| P2-20 | 429 | gemini-2.5-flash-image | 4.886 | 0 | Not returned | ProviderHTTPError |

### P3 — `gemini-3.1-flash-image`

| Attempt | Provider HTTP | Model | Latency (s) | Image bytes | Traffic type | Receipt note |
| --- | --- | --- | --- | --- | --- | --- |
| P3-01 | 200 | gemini-3.1-flash-image | 7.359 | 483483 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P3-02 | 200 | gemini-3.1-flash-image | 7.257 | 383237 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P3-03 | 429 | gemini-3.1-flash-image | 0.298 | 0 | Not returned | ProviderHTTPError |
| P3-04 | 429 | gemini-3.1-flash-image | 0.317 | 0 | Not returned | ProviderHTTPError |
| P3-05 | 200 | gemini-3.1-flash-image | 6.947 | 396915 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P3-06 | 429 | gemini-3.1-flash-image | 0.329 | 0 | Not returned | ProviderHTTPError |
| P3-07 | 429 | gemini-3.1-flash-image | 0.317 | 0 | Not returned | ProviderHTTPError |
| P3-08 | 429 | gemini-3.1-flash-image | 0.308 | 0 | Not returned | ProviderHTTPError |
| P3-09 | 200 | gemini-3.1-flash-image | 7.044 | 489785 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P3-10 | 429 | gemini-3.1-flash-image | 0.302 | 0 | Not returned | ProviderHTTPError |
| P3-11 | 429 | gemini-3.1-flash-image | 0.320 | 0 | Not returned | ProviderHTTPError |
| P3-12 | 429 | gemini-3.1-flash-image | 0.296 | 0 | Not returned | ProviderHTTPError |
| P3-13 | 200 | gemini-3.1-flash-image | 6.697 | 352592 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P3-14 | 429 | gemini-3.1-flash-image | 0.300 | 0 | Not returned | ProviderHTTPError |
| P3-15 | 429 | gemini-3.1-flash-image | 0.311 | 0 | Not returned | ProviderHTTPError |
| P3-16 | 429 | gemini-3.1-flash-image | 0.306 | 0 | Not returned | ProviderHTTPError |
| P3-17 | 200 | gemini-3.1-flash-image | 6.955 | 423238 | ON_DEMAND | ValueError; cost/image path derived from preserved bytes |
| P3-18 | 429 | gemini-3.1-flash-image | 0.292 | 0 | Not returned | ProviderHTTPError |
| P3-19 | 429 | gemini-3.1-flash-image | 0.359 | 0 | Not returned | ProviderHTTPError |
| P3-20 | 429 | gemini-3.1-flash-image | 0.291 | 0 | Not returned | ProviderHTTPError |

## Saved samples and exact risk numbers

The committed fixture was captured from the real production rewrite agent on 2026-10-18. Its source acquisition SHA-256 is `2c2d8ca8f644ddfad559dfb1c4bd3c25725f12f8a36d098fefa6e8f808153c76`; all five sanitized payloads match the acquisition. The fixture SHA-256 is `01459f9113276e7de4fa0ca9022b642b945aa0784fe57431d74491b0e1b54cf8`.

“Indoor gymnasium” returned `no_safe_rewrite` in four bounded real requests. Its original text and risk are retained; the UI labels the saved sample as unchanged and does not expose a lower-risk rewrite or copy control. The two requested preview actions share the same saved still for that sample. Ten requested sample actions therefore require nine unique stored images. [Acquisition](sample_rewrites_acquisition.json), [fixed risk values](pinned_risk_numbers.json), [fixture audit](release_scope_audit.json).

| Sample | Saved decision | Exact before | Exact after | Displayed comparison |
| --- | --- | --- | --- | --- |
| a cat and a dog | improved | 0.30666666666666664 | 0.05714285714285714 | 30.7% → 5.7% |
| a spoon and a laptop | improved | 0.4678787878787878 | 0.15833333333333333 | 46.8% → 15.8% |
| a bicycle and a car | improved | 0.4333333333333333 | 0.2 | 43.3% → 20.0% |
| indoor gymnasium | no_safe_rewrite | 0.065 | 0.065 | 6.5% → 6.5% |
| a purple clock | improved | 0.05714285714285714 | 0.025 | 5.7% → 2.5% |

The values above are pinned fixture values, not a claim that the pending demo has already shown them. A lower historical/mixed estimate does not establish better video quality. Original human evidence remains separate from machine feedback.

| Warm action | Variant | HTTP | Cache | Model calls | Image bytes | HTTP latency (s) | Generation date |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WARM-01 | original | 200 | hit | 0 | 170352 | 13.662 | 2026-10-18 |
| WARM-02 | rewrite | 200 | miss | 1 | 144167 | 6.805 | 2026-10-18 |
| WARM-03 | original | 200 | miss | 1 | 76625 | 6.220 | 2026-10-18 |
| WARM-04 | rewrite | 200 | miss | 1 | 65720 | 6.189 | 2026-10-18 |
| WARM-05 | original | 200 | miss | 1 | 139700 | 6.982 | 2026-10-18 |
| WARM-06 | rewrite | 200 | miss | 1 | 335231 | 6.418 | 2026-10-18 |
| WARM-07 | original | 200 | miss | 1 | 199569 | 8.012 | 2026-10-18 |
| WARM-08 | rewrite | 200 | hit | 0 | 199569 | 0.666 | 2026-10-18 |
| WARM-09 | original | 200 | miss | 1 | 118892 | 6.686 | 2026-10-18 |
| WARM-10 | rewrite | 200 | miss | 1 | 54464 | 6.735 | 2026-10-18 |

Warm API result: **10/10 usable saved actions**, **9 unique texts**, **8 new model calls during the ten app actions**, **2 cache hits**. One earlier direct warm call supplied the first original image, so all warming generated **9 model calls in total**. Minimum spacing between recorded nonzero warm-call starts: **66.294 s**. Warm API image byte range: **54,464–335,231**. [Warm receipt](warm.json), [preserved direct warm receipt](warm_direct_before_steering.json).

## No-regression evidence

The final candidate returned 6/6 HTTP 200 on typed prompts, with 6/6 live rewrite sources and verified tool workflows. The repeated prompt was “a spoon and a laptop on a quiet desk with an ivory notebook”. Its two real rewrites were:

1. “A laptop sits open on a quiet wooden desk next to an ivory notebook, with a metal spoon resting nearby on a small ceramic coaster, static shot.”
2. “A closed laptop sits on a wooden desk next to an ivory notebook, with a metal spoon resting quietly on a ceramic saucer nearby, captured in a steady, still-life shot.”

These differing outputs establish that typed prompts still use the live rewrite path. They do not establish image/video quality. [Final candidate preflight receipt](preflight_candidate.json).

The final candidate postcheck smoke returned HTTP 200 in **17.896 s** on the existing 119,721-byte, five-second synthetic clip. It reused a stored review and made **0 model calls in this request**; the retained original analysis records two model calls. The frozen reference clip was unavailable on this machine, so the frozen reference smoke is **NOT RUN** and clip-review accuracy remains unmeasured. [Postcheck smoke](postcheck_candidate.json).

The fresh Chromium 145.0.7632.6 viewport pass used a 1440×900 desktop viewport, the preserved counting function, fonts ready, a 2,500-ms settling wait and the documented WebGL flags. It measured **18 objects**, **7 colors**, and a CTA bottom at **837.4375 px**. Desktop and 390×844 mobile home/architecture screens had **0 horizontal overflow**. The exact limited-mode architecture message was visible on both sizes. This pass issued **0 `/preflight` and 0 `/preview` requests** on warm revision `preflight-00024-poq`, using the same runtime image as the final cache-only configuration. [Viewport receipt and four screenshots](viewport_warm_candidate/summary.json).

Scope audit: **13/13 frozen inputs match original Git blobs**. All five risk-core files, the rewrite agent, store, postcheck service/UI/route AST, first-screen HTML/CSS and status script remain unchanged. Runtime inventory is **25 files: 19 unchanged and 6 authorized new/changed files**. The local runtime SHA-256 matches the submitted build input digest. The fresh audit scanned **841 regular files, 0 dataless**, with **0 files reconstructed**. [Scope audit](release_scope_audit.json).

## Revisions, traffic and settings

| Revision | Traffic in saved receipt | Purpose | Preview configuration |
| --- | --- | --- | --- |
| preflight-00021-sus | 100% production | Preserved fallback and current production before promotion | Preview disabled |
| preflight-00023-wad | 0% | Superseded no-traffic candidate; 0 preview calls | Preview enabled, typed live disabled; replaced before gates |
| preflight-00024-poq | 0% | Bounded app warming and viewport checks | Sample warming enabled; typed live disabled |
| preflight-00025-lij | 0% | Selected final candidate; promotion PENDING | Preview enabled; warming false; typed live false |

Final candidate build: `095a35c2-74ad-49cb-8ae8-507a6216ee74`. Runtime input SHA-256: `a3f7c0a10ebec2e00ff7bc7bfc01676c712405aff0a8dad55f8c82eef2364fa7`. The selected candidate remains tagged `preview-v4-candidate`; saved traffic still places **100% on `preflight-00021-sus`**. Final primary traffic confirmation after promotion is **PENDING**. [Build](build.json), [candidate](candidate.json), [superseded revision](candidate_superseded.json).

| Setting | Baseline | Final candidate / invariant |
| --- | --- | --- |
| PREFLIGHT_PREVIEW_ENABLED | false | true |
| PREFLIGHT_PREVIEW_LIVE_ENABLED | not set | false |
| PREFLIGHT_PREVIEW_WARM_ENABLED | not set | true only for warm revision; false on final candidate |
| PREFLIGHT_IMAGE_LIVE_ARM | not set | P2 configured for the image service; no live arm selected |
| PREFLIGHT_IMAGE_LOCATION | global | global |
| Cloud Run timeout | 40 s | 40 s; app preview deadline 38 s |
| Preview per-minute cap | 5 | 5 |
| Preview daily admission cap | 60 | 60 |
| Code daily ceiling | 500 | 500 |
| Cumulative check allowance | 1,000 | 1,000 |
| Cloud Run concurrency / CPU / memory | 80 / 1 CPU / 1 GiB | unchanged |
| Veo calls | 0 | 0 |
## File-by-file byte deltas

Measured against source baseline `9f77cbeb9da1b89cc993cc5c70a1c7dd9a9cc1af`. This table covers changed source, scripts, tests and submitted prose at this snapshot. Generated report/image/demo artifacts are accounted for in their dedicated receipts; the final demo is PENDING. A zero baseline size identifies a new file.

| File | Baseline bytes | Current bytes | Delta bytes |
| --- | --- | --- | --- |
| `.gitignore` | 181 | 329 | +148 |
| `README.md` | 30188 | 30902 | +714 |
| `app.py` | 21744 | 26134 | +4390 |
| `cloud/preview.py` | 3022 | 8119 | +5097 |
| `cloud/sample_rewrites.json` | 0 | 34494 | +34494 |
| `cloud/sample_rewrites.py` | 0 | 2628 | +2628 |
| `docs/submission-notes.md` | 1365 | 1524 | +159 |
| `scripts/probe_preview_v4.py` | 0 | 26134 | +26134 |
| `scripts/record_demo.py` | 37496 | 41100 | +3604 |
| `scripts/release_preview_v4.py` | 0 | 8678 | +8678 |
| `scripts/verify_preflight_v4.py` | 0 | 7870 | +7870 |
| `scripts/verify_preview_contract_v4.py` | 0 | 10335 | +10335 |
| `scripts/verify_preview_source_v4.py` | 0 | 10258 | +10258 |
| `scripts/verify_preview_ui_v4.py` | 0 | 14817 | +14817 |
| `scripts/warm_preview_v4.py` | 0 | 24979 | +24979 |
| `static/app.js` | 21553 | 23382 | +1829 |
| `static/architecture.js` | 5079 | 5586 | +507 |
| `tests/test_cloud_api.py` | 4141 | 4149 | +8 |
| `tests/test_preview.py` | 4573 | 4812 | +239 |
| `tests/test_preview_release_v4.py` | 0 | 3221 | +3221 |
| `tests/test_preview_v4.py` | 0 | 14123 | +14123 |

No risk-core, rewrite-agent, postcheck, store, first-screen HTML/CSS, dependency lock, Dockerfile or Cloud Build configuration change was made. These protected inputs are byte-checked in [the scope audit](release_scope_audit.json).

## Model calls, list-price spend and unchanged admission budget

The human amendment sets the v4 model-attempt budget to 85; the previous 44 v3 attempts remain separately reported and are excluded from that v4 cap. A durable reservation precedes dispatch; failed and unknown outcomes remain accounted for. No probe call is retried. Cache-hit responses report zero model calls and $0.00.

| Category | Recorded result rows | Known model attempts | Known list-price total | Unpriced result rows |
| --- | --- | --- | --- | --- |
| Warm (direct + app) | 11 | 9 | $0.3483366 | 0 |
| P1 | 20 | 20 | $0.32265655 | 0 |
| P2 | 20 | 20 | $0.2322747 | 0 |
| P3 | 20 | 20 | $0.2690385 | 0 |

Snapshot ledger: **71 reservations**, **71 results**, **69 known model attempts**, **2 known zero-call responses**, and **0 reservation(s) awaiting a result**. The known result-based list-price subtotal is **$1.17230635**. The completed warm/probe phase has **0 unknown dispatches and 0 unpriced result rows**. Final post-QA/demo ledger and admission-counter confirmation remain **PENDING**.

Completed model totals, including warm calls:

| Model | Attempts | Generated images | Known list-price spend |
| --- | --- | --- | --- |
| gemini-2.5-flash-image | 29 | 15 | $0.580611300 |
| gemini-3.1-flash-lite-image | 20 | 8 | $0.322656550 |
| gemini-3.1-flash-image | 20 | 6 | $0.269038500 |
| Total | 69 | 29 | $1.172306350 |

Forty provider HTTP-429 calls have zero list-price token cost under the retained official policy. Actual billing remains UNMEASURED. [Final spend summary](final_probe_spend_summary.json).

HTTP-200 costs use recorded token usage and the returned traffic class. P1 Priority rates are 1.8× standard rates; observed `ON_DEMAND` downgrades use standard prices. Official pricing states that non-200 provider requests are not charged; known non-200 rows use zero list-price token cost. Unknown transport outcomes remain unpriced. Actual billed spend is **UNMEASURED**. [Pricing evidence](official_sources.json), [non-200 pricing amendment](pricing_amendment_003.json), [derived annotations](derived_probe_annotations.json), [Google pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing).

The independent app admission cap remains **60/day and 5/min**, including cache hits. The native counter was **28/60 after warming and 28/60 after all P2 probes**, leaving 32 admissions. The direct probe arm did not consume app preview admissions. Samples-only planning allocates 10 candidate sample previews, 10 production sample previews and 2 demo sample previews: **projected final counter 50/60**. The two typed samples-only misses return before preview admission. V-C is not run because no arm qualifies. The actual final counter is **PENDING**. [Native post-warm counter](firestore_daily_budget_after_warm.json), [after-P2 counter](firestore_daily_budget_after_P2.json), [pre-warm cap check](firestore_daily_budget_before_warm.json).

## Preserved incidents and corrections

- **One direct warm call preceded the app-route clarification.** Its result is preserved. All ten subsequent warm actions used `/preview`, including the cached first original. No direct result is relabeled as an app call. [Execution notes](execution_notes.json), [direct warm receipt](warm_direct_before_steering.json).
- **P1/P3 local receipt serialization errors followed successful provider responses.** The relative-path error occurred after decoding, validating, hashing and saving the real bytes. Original raw `ValueError` fields remain intact. Derived annotations verify existing image SHA-256 and calculate price from already recorded usage/traffic. They add **0 provider calls** and do not rewrite the raw rows. [Receipt amendment](receipt_amendment_002.json), [annotations](derived_probe_annotations.json).
- **iCloud offloaded 48 files during the run.** Reads of a frozen model artifact, Git objects and the sealed official-source receipt blocked. P2 held until original bytes were readable. Native `brctl` plus Foundation coordinated reads restored originals; final dataless count was **0**. The official receipt remained **3,001 bytes** with SHA-256 `44f3d0c18d137862abea4d695aa3f04a4ea143401839023eb1ea12698be993a0`, matching the seal. **0 files were reconstructed** and flags were not cleared artificially. Earlier HOLD and fresh PASS_SCOPE audits are both retained. [Offload incident](icloud_regression.json), [source-receipt incident](icloud_offload_regression.json), [revalidation](revalidated_after_hydration.json), [prior scope HOLD](release_scope_audit_before_hydration.json).
- **The initial read-only browser auditor used a CSP-incompatible predicate.** The failure happened before any preview/check call. The corrected arrow predicate passed the viewport audit; the initial failure remains saved. The real UI runner was corrected before V-B execution. [Initial audit failure](viewport_warm_candidate/attempt_01_csp_wait_failure.json), [passing viewport receipt](viewport_warm_candidate/summary.json).
- **Pre-deployment integration review found harness and promotion defects.** The demo architecture selector was updated to the canonical message; V-C counts fresh one-call misses; the 38-second app deadline fits beneath the unchanged 40-second Cloud Run timeout. Promotion now requires warm=false in saved and native revision flags and binds gate revision/build/commit/runtime hashes and native image digest. The independent promotion battery passed **12/12**. **0 failed candidate revisions were promoted.** [Execution notes](execution_notes.json), [promotion audit](release_scope_audit.json).

## Production self-QA — PENDING

A fresh browser profile must open the promoted production URL with browser cache disabled. The table below is a checklist, not an execution receipt. Save every step screenshot and the actual action → observation → expectation to `self_qa/` after promotion.

| Subject | Action | Observed | Expected | Screenshot |
| --- | --- | --- | --- | --- |
| a cat and a dog | Select sample | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a cat and a dog | Check | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a cat and a dog | Preview original | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a cat and a dog | Preview saved rewrite / unchanged sample | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a spoon and a laptop | Select sample | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a spoon and a laptop | Check | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a spoon and a laptop | Preview original | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a spoon and a laptop | Preview saved rewrite / unchanged sample | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a bicycle and a car | Select sample | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a bicycle and a car | Check | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a bicycle and a car | Preview original | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a bicycle and a car | Preview saved rewrite / unchanged sample | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| indoor gymnasium | Select sample | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| indoor gymnasium | Check | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| indoor gymnasium | Preview original | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| indoor gymnasium | Preview saved rewrite / unchanged sample | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a purple clock | Select sample | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a purple clock | Check | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a purple clock | Preview original | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| a purple clock | Preview saved rewrite / unchanged sample | PENDING | Saved sample decision / hit image and exact saved label, as applicable | PENDING |
| Typed prompt 1 | Check and Preview | PENDING | Live rewrite; exact limited-stills message; 0 image-model calls | PENDING |
| Typed prompt 2 | Check and Preview | PENDING | Live rewrite; exact limited-stills message; 0 image-model calls | PENDING |
| Architecture | Open service connections | PENDING | Exact samples-only canonical message | PENDING |
| README top | Read public top section | PENDING | Exact canonical message and no candidate/promotion-pending publication wording | PENDING |

## Demo re-record — PENDING

The v4 demo must be one continuous, silent take at **1920×1080, 30 fps, ≤150 seconds**, with a saved sample still and its metadata readable for at least **3 seconds**. The recorder enforces a 3.25-second still hold and exports eight frames. The samples-only plan has no typed live-image beat.

| Demo fact | Value |
| --- | --- |
| Final file path | PENDING |
| File bytes | PENDING |
| SHA-256 | PENDING |
| Duration | PENDING |
| Resolution verified | PENDING |
| FPS verified | PENDING |
| Silent audio-stream check | PENDING |
| Full decode | PENDING |
| Eight replacement frame paths | PENDING |
| Beat timestamps | PENDING |
| Exact sample risk numbers actually shown | PENDING |
| Selected one-take record log | PENDING |

The planned sample is “a spoon and a laptop”: fixture values `p_fail_before=0.4678787878787878`, `p_fail_after=0.15833333333333333`; UI comparison **46.8% → 15.8%**. These values must be read back from `demo/record_log.json` after recording before Felix uses them in the deck. The video facts above remain PENDING until that receipt exists.

## Repository, tags and provenance — PENDING final release

| Item | Snapshot / completion status |
| --- | --- |
| Source baseline | `9f77cbeb9da1b89cc993cc5c70a1c7dd9a9cc1af` |
| Final production source commit | PENDING |
| Native build | `095a35c2-74ad-49cb-8ae8-507a6216ee74` |
| Current local/build-input runtime hash | `a3f7c0a10ebec2e00ff7bc7bfc01676c712405aff0a8dad55f8c82eef2364fa7` |
| Native archive runtime hash and both-hash comparison | PENDING final source/commit provenance receipt; 25 expected runtime inputs |
| Production image digest | PENDING native source/image provenance receipt |
| Push to main | PENDING |
| New aibc-2026-submission-v3 tag | PENDING; older tags must not move |
| Older aibc-2026-submission tag | `dd12f279e364cbd217a4178b51c1d270cacebbdd`; local and anonymous remote match |
| Older aibc-2026-submission-v2 tag | `bdcdecdf6db6b0c2bebea8a35ed350de5f005940`; local and anonymous remote match |
| Worktree secret scan | 522 files, 96 binary files, 0 hits, 0 errors; retained snapshot |
| Final indexed/history secret scan | PENDING final source and final receipt commits; require 0 hits |
| Anonymous final clone / main / tag agreement | PENDING |
| README + submission preview clause | Current candidate wording matches limited mode; remove pending qualifiers only after actual promotion |
| Brief description | 952 characters now; final publication count PENDING if text changes |
| Demo link / pitch deck export | Existing placeholders remain pending user publication/export |

[Scope/tag checks](release_scope_audit.json), [worktree secret scan](secrets_worktree.json). A matching local build input digest is separate from the final native archive/image and anonymous-publication checks.

## Not done at this snapshot

PENDING: final post-QA/demo ledger and counter; final bound V-A/V-B/V-D/V-F gate decision; candidate promotion and native traffic verification; production self-QA with all screenshots; one-take demo and eight replacement frames; final README/submission release wording; source and receipt commits/push; v3 tag; final native 25-file provenance, all-history secret scans and anonymous clone verification. No live generation is selected. No Veo calls were made. Clip-review accuracy and actual billed spend remain unmeasured.
