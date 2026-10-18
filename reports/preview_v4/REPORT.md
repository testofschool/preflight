# Preflight preview v4 — evidence report (release work pending)

Snapshot: **2026-10-18T11:22:23+09:00**. This document records completed measurements and leaves unfinished release work as **PENDING**. Native promotion, production self-QA and the v4 demo are complete. Final evidence publication, history scanning and anonymous-access checks remain PENDING.

Production serves **preflight-00025-lij at 100%** in **samples-only** mode. All 60 preregistered probe calls are complete: P1 returned 8/20 successful images, P2 6/20 and P3 6/20. No arm reaches 19/20, so no live arm is selected. All applicable candidate gates are PASS; V-C is not applicable because no arm qualifies. The bound gate decision and native promotion are recorded. Source commit `d638c0690cb17d60316922eb30a14f150fe7c23c` and the new lightweight `aibc-2026-submission-v3` tag have been pushed. Production self-QA passed 28/28 recorded steps. The one-take demo is complete; final evidence publication, history scanning and anonymous-publication verification remain PENDING.

The required message is: **Image preview — Active for sample prompts (saved stills); live generation limited**. Five sample decisions are saved: four lower-risk rewrites and one honest unchanged result for “indoor gymnasium”. Saved images are labeled with their generation date, 0 model calls and $0.00. Typed prompts retain the live Gemini rewrite. An uncached still in samples-only mode says: “Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works.”

## V-A through V-F

| Gate | Status at this snapshot | Measured evidence | Remaining work |
| --- | --- | --- | --- |
| V-A | PASS — final full suite | 144 tests and 11 subtests passed; 0 failures/errors/skips, 3 warnings, 46.72 s. Python 3.12.14 in an isolated task environment outside iCloud; 113/113 exact pins matched, 0 version mismatches. Includes 12 promotion guards, 12 offline probe tests and 5 offline warm tests. Separate mocked browser contracts: 28/28. | No remaining test gate; production self-QA also passed 28/28. |
| V-B | PASS — candidate and production | Final candidate: 10/10 visible saved stills, cache hits, model_calls=0 and exact saved labels; 0 page errors, 22 screenshots. Fresh production self-QA: 28/28 steps/screenshots, including 10/10 visible saved stills with hits, 0 model calls and exact labels; 0 page errors. | None; the demo also records two HTTP 200 cache hits with 0 model calls. |
| V-C | N/A — samples-only | All 60 probe calls are complete; every arm fails 19/20. No live UI calls are required for the samples-only release. | No live path will be promoted. |
| V-D | PASS — candidate and production previews | Candidate: 10/10 HTTP 200, 0.3464–0.7948 s. Production: 10/10 saved previews HTTP 200, 0.3708–0.5743 s; two expected typed HTTP 503 responses, 0.1838–0.1866 s. 0 HTTP 504. All 10 warm responses also <45 s; warm maximum 13.662 s. | None; demo preview response-header times are 0.404 s and 0.245 s, both HTTP 200 hits. |
| V-E | PASS — final candidate | Typed prompts: 6/6 HTTP 200, 6/6 live rewrites, 6/6 verified workflows, 6/6 <45 s and two different rewrites for the repeated prompt. Postcheck smoke: HTTP 200, 17.896 s. Final candidate viewport: 18 objects, 7 colors, CTA bottom 837.4375 px. Native source/image provenance: PASS, 25/25 files. | Production self-QA passed: two further typed HTTP 200 live rewrites, 5.4072/6.3758 s; canonical architecture and public README match. Retain postcheck smoke-test limitations. |
| V-F | PASS — final caps/spend | 69 image-model attempts and 71 conservative reservations are below the amended v4 cap of 85; 0 unknown dispatches, 0 unpriced rows; image-model request list price $1.172306350. Native final app counter is 50/60, leaving 10 admissions; 0 new model calls after probe completion, including the two demo cache hits. | None; actual billed spend remains UNMEASURED. |

Test receipts: [final isolated full suite](tests_final_isolated.txt), [JUnit](tests_final_isolated.junit.xml), [verified test scope](tests_final_scope.json), [113 exact pins and isolated environment](test_environment_fallback.json), [retained earlier runtime tests](tests_runtime_frozen.txt), [retained earlier full output](tests_final.txt), [mocked UI contracts](ui_contract.json), [offline probe tests](offline_probe_tests.log), [offline warm tests](offline_warm_tests.log), [scope and promotion-guard audit](release_scope_audit.json). Mocked tests do not establish provider reliability.

The [bound gate decision](gate_decision.json) records V-A/V-B/V-D/V-E/V-F as true and V-C as not applicable. It names source commit `d638c0690cb17d60316922eb30a14f150fe7c23c`, candidate `preflight-00025-lij`, build `095a35c2-74ad-49cb-8ae8-507a6216ee74` and runtime SHA-256 `a3f7c0a10ebec2e00ff7bc7bfc01676c712405aff0a8dad55f8c82eef2364fa7`. The matching revision has been promoted, and production self-QA passed 28/28 steps. [Native 100% traffic receipt](promotion.json).

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

The final no-traffic candidate `preflight-00025-lij` passed the real Chromium sample gate in a fresh profile with HTTP cache disabled and service workers blocked. All **10/10 original/rewrite actions** displayed an image, returned **X-Preview-Cache: hit**, reported **model_calls=0** and displayed the exact saved-still metadata. Preview response times were **0.3464–0.7948 s**, with **0 HTTP 504**, **0 page errors** and **22 saved step screenshots**. The architecture displayed the exact limited-mode canonical message. The final candidate itself measured **18 objects**, **7 colors** and a CTA bottom of **837.4375 px**. [Real candidate gate and screenshots](ui_candidate/summary.json).

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
| preflight-00021-sus | 100% baseline → 0% after promotion | Preserved fallback revision | Preview disabled |
| preflight-00023-wad | 0% | Superseded no-traffic candidate; 0 preview calls | Preview enabled, typed live disabled; replaced before gates |
| preflight-00024-poq | 0% | Bounded app warming and viewport checks | Sample warming enabled; typed live disabled |
| preflight-00025-lij | 0% candidate → 100% production | All applicable gates passed; promoted | Preview enabled; warming false; typed live false |

Final candidate build: `095a35c2-74ad-49cb-8ae8-507a6216ee74`. Release source: `d638c0690cb17d60316922eb30a14f150fe7c23c`, committed locally and pushed to main. Native provenance passed **25/25 Git/archive runtime files**, verified the exact candidate revision and matched the build/revision image digest. Git runtime SHA-256: `a3f7c0a10ebec2e00ff7bc7bfc01676c712405aff0a8dad55f8c82eef2364fa7`. Cloud Build archive runtime SHA-256: `a3f7c0a10ebec2e00ff7bc7bfc01676c712405aff0a8dad55f8c82eef2364fa7`. Candidate image digest: `sha256:4bf0668ae549f7ab924f17e36105b621f1f25676aefb6e53e06154db4384e932`. The `preview-v4-candidate` service tag remains attached to the accepted revision. Native post-promotion traffic confirms **100% on `preflight-00025-lij`**, with warming and typed live generation both disabled. [Build](build.json), [candidate](candidate.json), [native provenance](source_match.json), [100% production traffic](promotion.json), [superseded revision](candidate_superseded.json).

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

Measured against source baseline `9f77cbeb9da1b89cc993cc5c70a1c7dd9a9cc1af`. This table covers changed source, scripts, tests and submitted prose at this snapshot. Generated report/image/demo artifacts are accounted for in their dedicated receipts; the final demo is verified below. A zero baseline size identifies a new file.

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

Snapshot ledger: **71 reservations**, **71 results**, **69 known model attempts**, **2 known zero-call responses**, and **0 reservation(s) awaiting a result**. The known result-based list-price subtotal is **$1.17230635**. The completed warm/probe phase has **0 unknown dispatches and 0 unpriced result rows**, and the pre-promotion V-F cap/spend gate is **PASS**. Final post-demo native verification confirms **50/60 app admissions**, **10 remaining** and **0 new model calls after probe completion**; the measured attempts and list-price subtotal are unchanged. [Final native budget receipt](firestore_daily_budget_final.json).

Completed model totals, including warm calls:

| Model | Attempts | Generated images | Known list-price spend |
| --- | --- | --- | --- |
| gemini-2.5-flash-image | 29 | 15 | $0.580611300 |
| gemini-3.1-flash-lite-image | 20 | 8 | $0.322656550 |
| gemini-3.1-flash-image | 20 | 6 | $0.269038500 |
| Total | 69 | 29 | $1.172306350 |

The **$1.172306350 subtotal covers image-model requests only**, including text tokens billed within those image requests. It **excludes Gemini text-rewrite and clip-review model charges**, as well as infrastructure/storage charges. It is not an all-service billing total.

Forty provider HTTP-429 calls have zero list-price token cost under the retained official policy. Actual billing remains UNMEASURED. [Final spend summary](final_probe_spend_summary.json).

HTTP-200 costs use recorded token usage and the returned traffic class. P1 Priority rates are 1.8× standard rates; observed `ON_DEMAND` downgrades use standard prices. Official pricing states that non-200 provider requests are not charged; known non-200 rows use zero list-price token cost. Unknown transport outcomes remain unpriced. Actual billed spend is **UNMEASURED**. [Pricing evidence](official_sources.json), [non-200 pricing amendment](pricing_amendment_003.json), [derived annotations](derived_probe_annotations.json), [Google pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing).

The independent app admission cap remains **60/day and 5/min**, including cache hits. Native counters were **28/60 after warming**, **28/60 after all P2 probes**, **38/60 after the 10 candidate sample previews**, **48/60 after the 10 production self-QA sample previews**, and **50/60 after the two demo sample previews**, leaving **10 admissions**. The direct probe arm did not consume app preview admissions. The two typed samples-only misses returned before preview admission. V-C was not run because no arm qualified. The final native snapshot at **2026-10-18T11:21:39.080629+09:00** confirms **0 new model calls after probe completion** and the unchanged 69 measured attempts / 71 conservative reservations. The counter resets at **2026-10-19 00:00 UTC / 09:00 KST**. [Native post-warm counter](firestore_daily_budget_after_warm.json), [after-P2 counter](firestore_daily_budget_after_P2.json), [after-V-B counter](firestore_daily_budget_after_VB.json), [post-self-QA / before-demo counter](firestore_daily_budget_before_demo.json), [final post-demo counter](firestore_daily_budget_final.json), [pre-warm cap check](firestore_daily_budget_before_warm.json).

## Preserved incidents and corrections

- **One direct warm call preceded the app-route clarification.** Its result is preserved. All ten subsequent warm actions used `/preview`, including the cached first original. No direct result is relabeled as an app call. [Execution notes](execution_notes.json), [direct warm receipt](warm_direct_before_steering.json).
- **P1/P3 local receipt serialization errors followed successful provider responses.** The relative-path error occurred after decoding, validating, hashing and saving the real bytes. Original raw `ValueError` fields remain intact. Derived annotations verify existing image SHA-256 and calculate price from already recorded usage/traffic. They add **0 provider calls** and do not rewrite the raw rows. [Receipt amendment](receipt_amendment_002.json), [annotations](derived_probe_annotations.json).
- **iCloud offloaded 48 files during the run.** Reads of a frozen model artifact, Git objects and the sealed official-source receipt blocked. P2 held until original bytes were readable. Native `brctl` plus Foundation coordinated reads restored originals; final dataless count was **0**. The official receipt remained **3,001 bytes** with SHA-256 `44f3d0c18d137862abea4d695aa3f04a4ea143401839023eb1ea12698be993a0`, matching the seal. **0 files were reconstructed** and flags were not cleared artificially. Earlier HOLD and fresh PASS_SCOPE audits are both retained. [Offload incident](icloud_regression.json), [source-receipt incident](icloud_offload_regression.json), [revalidation](revalidated_after_hydration.json), [prior scope HOLD](release_scope_audit_before_hydration.json).
- **The initial read-only browser auditor used a CSP-incompatible predicate.** The failure happened before any preview/check call. The corrected arrow predicate passed the viewport audit; the initial failure remains saved. The real UI runner was corrected before V-B execution. [Initial audit failure](viewport_warm_candidate/attempt_01_csp_wait_failure.json), [passing viewport receipt](viewport_warm_candidate/summary.json).
- **An initial real-UI process stopped before browser execution because its interpreter lacked Playwright.** It made **0 preview HTTP requests and 0 provider calls**. The runner then used the existing `python3` Playwright installation and passed the 10/10 candidate gate. No package installation, provider retry or application change was used for this correction. [Initial import failure](ui_candidate_stdout.txt), [passing rerun](ui_candidate_stdout_retry_environment.txt), [execution notes](execution_notes.json).
- **The original external test environment remained partly offloaded.** Native hydration reduced its dataless count from **1,944 to 1,931** after about **3 minutes**; test collection still blocked on installed package bytes. The partial and interrupted attempts are preserved and are not presented as passed validation. Final validation used an isolated **Python 3.12.14** environment outside iCloud, with **113/113 existing exact package pins matched and 0 version mismatches**. The complete suite passed **144 tests plus 11 subtests, with 3 warnings in 46.72 s**, and JUnit records **144 testcase entries, 0 failures, 0 errors and 0 skips**. Original package bytes and repository runtime/lock files were not replaced or changed. [Original test incident](test_environment_incident.json), [native hydration counts](test_environment_hydration.json), [isolated exact-pin setup](test_environment_fallback.json), [final test output](tests_final_isolated.txt), [JUnit](tests_final_isolated.junit.xml), [test scope](tests_final_scope.json).
- **Pre-deployment integration review found harness and promotion defects.** The demo architecture selector was updated to the canonical message; V-C counts fresh one-call misses; the 38-second app deadline fits beneath the unchanged 40-second Cloud Run timeout. Promotion now requires warm=false in saved and native revision flags and binds gate revision/build/commit/runtime hashes and native image digest. The independent promotion battery passed **12/12**. **0 failed candidate revisions were promoted.** [Execution notes](execution_notes.json), [promotion audit](release_scope_audit.json).

## Production self-QA — PASS 28/28

A fresh Chromium profile opened the promoted production URL, with HTTP cache disabled and service workers blocked, from **2026-10-18T02:15:14.559473+00:00** to **2026-10-18T02:17:51.264994+00:00**. All **28 recorded steps and screenshots passed**, with **0 page errors**. Production status reported `preview=true`, `preview_mode=samples` and `postcheck=true`. [Full action/observation/expectation receipt](self_qa/summary.json).

The ten sample preview actions returned **10 HTTP 200 cache hits, 10 visible images and 0 model calls**, each with the exact label **“Saved still · generated 2026-10-18 · 0 model calls · $0.00”**. Their measured latency was **0.3708–0.5743 s**. Two typed checks returned live Gemini rewrites; their two preview attempts returned the expected HTTP 503 with **“Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works.”** and no image. Those error payloads omit model-call metadata (`null` in the runner receipt); no zero value is inferred from the absent field. The unchanged native model-attempt ledger and samples-only configuration are recorded separately in the budget evidence above.

“Canonical message” below means **“Image preview — Active for sample prompts (saved stills); live generation limited”**. “Saved label” means the exact generation-date/zero-call/$0.00 label quoted above. Each row records the actual action → observed result → expected behavior, with its screenshot.

| # | Action | Observed | Expected | Screenshot |
| --- | --- | --- | --- | --- |
| 1 | Open fresh browser | 18 objects; 7 colors; CTA bottom 837.4375 px | objects <=18; colors <=12; CTA <=900px | [Step 01](self_qa/01_first_viewport.png) |
| 2 | a cat and a dog: Click sample a cat and a dog | Input is “a cat and a dog” | a cat and a dog | [Step 02](self_qa/02_sample_1_sample.png) |
| 3 | a cat and a dog: Click Check | HTTP 200; pinned-sample; improved; p_fail 0.30666666666666664 → 0.05714285714285714; 0.4363 s | 200; saved sample rewrite | [Step 03](self_qa/03_sample_1_check.png) |
| 4 | a cat and a dog: Click Preview original | HTTP 200; hit; 0 model calls; visible image; exact saved label; 0.5743 s | Saved image, hit, 0 calls and exact label | [Step 04](self_qa/04_sample_1_original.png) |
| 5 | a cat and a dog: Click Preview rewrite | HTTP 200; hit; 0 model calls; visible image; exact saved label; 0.5403 s | Saved image, hit, 0 calls and exact label | [Step 05](self_qa/05_sample_1_rewrite.png) |
| 6 | a spoon and a laptop: Click sample a spoon and a laptop | Input is “a spoon and a laptop” | a spoon and a laptop | [Step 06](self_qa/06_sample_2_sample.png) |
| 7 | a spoon and a laptop: Click Check | HTTP 200; pinned-sample; improved; p_fail 0.4678787878787878 → 0.15833333333333333; 0.2891 s | 200; saved sample rewrite | [Step 07](self_qa/07_sample_2_check.png) |
| 8 | a spoon and a laptop: Click Preview original | HTTP 200; hit; 0 model calls; visible image; exact saved label; 0.4111 s | Saved image, hit, 0 calls and exact label | [Step 08](self_qa/08_sample_2_original.png) |
| 9 | a spoon and a laptop: Click Preview rewrite | HTTP 200; hit; 0 model calls; visible image; exact saved label; 0.3708 s | Saved image, hit, 0 calls and exact label | [Step 09](self_qa/09_sample_2_rewrite.png) |
| 10 | a bicycle and a car: Click sample a bicycle and a car | Input is “a bicycle and a car” | a bicycle and a car | [Step 10](self_qa/10_sample_3_sample.png) |
| 11 | a bicycle and a car: Click Check | HTTP 200; pinned-sample; improved; p_fail 0.4333333333333333 → 0.2; 0.2505 s | 200; saved sample rewrite | [Step 11](self_qa/11_sample_3_check.png) |
| 12 | a bicycle and a car: Click Preview original | HTTP 200; hit; 0 model calls; visible image; exact saved label; 0.4275 s | Saved image, hit, 0 calls and exact label | [Step 12](self_qa/12_sample_3_original.png) |
| 13 | a bicycle and a car: Click Preview rewrite | HTTP 200; hit; 0 model calls; visible image; exact saved label; 0.5601 s | Saved image, hit, 0 calls and exact label | [Step 13](self_qa/13_sample_3_rewrite.png) |
| 14 | indoor gymnasium: Click sample indoor gymnasium | Input is “indoor gymnasium” | indoor gymnasium | [Step 14](self_qa/14_sample_4_sample.png) |
| 15 | indoor gymnasium: Click Check | HTTP 200; pinned-sample; no_safe_rewrite; p_fail 0.065 → 0.065; 0.2350 s | HTTP 200; saved no_safe_rewrite decision; original remains unchanged | [Step 15](self_qa/15_sample_4_check.png) |
| 16 | indoor gymnasium: Click Preview original | HTTP 200; hit; 0 model calls; visible image; exact saved label; 0.4747 s | Saved image, hit, 0 calls and exact label | [Step 16](self_qa/16_sample_4_original.png) |
| 17 | indoor gymnasium: Click Preview rewrite | HTTP 200; hit; 0 model calls; visible image; exact saved label; 0.5048 s; unchanged original, 199,569 bytes | Saved unchanged original, hit, 0 calls and exact label | [Step 17](self_qa/17_sample_4_rewrite.png) |
| 18 | a purple clock: Click sample a purple clock | Input is “a purple clock” | a purple clock | [Step 18](self_qa/18_sample_5_sample.png) |
| 19 | a purple clock: Click Check | HTTP 200; pinned-sample; improved; p_fail 0.05714285714285714 → 0.025; 0.2561 s | 200; saved sample rewrite | [Step 19](self_qa/19_sample_5_check.png) |
| 20 | a purple clock: Click Preview original | HTTP 200; hit; 0 model calls; visible image; exact saved label; 0.4261 s | Saved image, hit, 0 calls and exact label | [Step 20](self_qa/20_sample_5_original.png) |
| 21 | a purple clock: Click Preview rewrite | HTTP 200; hit; 0 model calls; visible image; exact saved label; 0.4939 s | Saved image, hit, 0 calls and exact label | [Step 21](self_qa/21_sample_5_rewrite.png) |
| 22 | Typed prompt 1: Click Check | HTTP 200; live rewrite; improved; p_fail 0.4704761904761904 → 0.29047619047619044; 5.4072 s | 200; live rewrite | [Step 22](self_qa/22_typed_1_check.png) |
| 23 | Typed prompt 1: Click Preview original | HTTP 503; exact limited message; no image; 0.1838 s | Exact limited message; no still in samples-only mode | [Step 23](self_qa/23_typed_1_preview.png) |
| 24 | Typed prompt 2: Click Check | HTTP 200; live rewrite; improved; p_fail 0.64 → 0.47333333333333333; 6.3758 s | 200; live rewrite | [Step 24](self_qa/24_typed_2_check.png) |
| 25 | Typed prompt 2: Click Preview original | HTTP 503; exact limited message; no image; 0.1866 s | Exact limited message; no still in samples-only mode | [Step 25](self_qa/25_typed_2_preview.png) |
| 26 | Open architecture page | Canonical message visible in service connections | Exact canonical message | [Step 26](self_qa/26_architecture.png) |
| 27 | Read public README top section | Public top section has canonical message, four improved/one unchanged decisions and probe counts 8/6/6 | Exact canonical message in public README | [Step 27](self_qa/27_readme_top.png) |
| 28 | Read README preview clause | Public preview clause exactly matches the canonical message | Exact canonical message | [Step 28](self_qa/28_readme_preview_clause.png) |

The gym’s two saved preview actions intentionally use the same original prompt after `no_safe_rewrite`; the unchanged result is not counted as a lower-risk rewrite. Architecture and public README checks confirm the same final samples-only message. This self-QA does not measure clip-review accuracy or actual billed spend.

## Demo re-record — PASS

The published demo is **one clean, continuous take**, selected from **one requested take**. All **11 recorded steps passed**, with **0 page errors, 0 unexpected request failures and the expected request sequence**. Its **108.366667-second** H.264 video is **1920×1080 at 30 fps**, has **no audio stream**, and passed full decode. The two sample stills remained visible for **3.318 s** and **3.251 s**, each exceeding the 3-second requirement. Both `/preview` requests returned HTTP 200 cache hits with **0 image-model calls** and the exact saved metadata label. [Artifact and frame hashes](demo_artifact.json), [selected one-take log](../../demo/record_log.json), [published video](../../demo/preflight_demo_raw.mp4).

| Demo fact | Recorded value |
| --- | --- |
| Final file | `demo/preflight_demo_raw.mp4` |
| File bytes | 9,300,697 |
| SHA-256 | `d1f3772d1187ee7ce1aeed1e0efe3f432c09337e90cc0b7113b6ca37aa94ab78` |
| Duration | 108.366667 s; below 150 s |
| Video stream | H.264; 1920×1080; 30/1 fps |
| Audio streams | 0; silent |
| Full decode | PASS |
| Take / step counts | 1 requested; take 1 selected; 11/11 steps PASS |
| Still holds | Original 3.318 s; rewrite 3.251 s |
| Image previews | 2 HTTP 200 cache hits; 0 image-model calls; $0.00 response cost |
| Eight frames | 8/8 replaced and local bytes/SHA-256 verified against the artifact receipt |
| Original new take retained | `/private/tmp/preflight-v4-demo-20261018-1118` |
| Previous movie and frames | Backed up outside Git at `/Users/felix/Desktop/AI Builder Cup 2026/evidence/preview_v3_demo_before_v4_20261018_1121` |

Recorded beats, using the recorder's monotonic offsets in seconds:

| Beat | Start–end (s) | Observed sequence | Result |
| --- | --- | --- | --- |
| 1 | 0.045–5.158 | Home | PASS |
| 2 | 5.159–28.036 | Sample prompt → risk + why | PASS |
| 3 | 29.001–34.487 | Better prompt → risk drops → copy | PASS |
| 4 | 36.002–42.248 | Cached sample still + caption | PASS |
| 5 | 44.002–49.986 | Cached saved-rewrite still | PASS |
| 6 | 56.001–85.154 | Clip upload → reused review → unchanged feedback risk | PASS |
| 7 | 90.002–98.525 | Architecture image preview connection | PASS |

The final home-rest step runs **104.002–108.519 s** in the UI log; its wall-clock offset extends beyond the encoded duration by recorder timing, while the media duration above comes from `ffprobe`. The seven beat rows group 10 UI steps; final home rest is the eleventh.

Eight replacement frames, with exact artifact paths and offsets:

| Frame | Offset (s) | Path |
| --- | --- | --- |
| 1 | 1.083 | [demo/frames/01_home.png](../../demo/frames/01_home.png) |
| 2 | 19.522 | [demo/frames/02_risk_and_score_details.png](../../demo/frames/02_risk_and_score_details.png) |
| 3 | 24.963 | [demo/frames/03_historical_neighbours.png](../../demo/frames/03_historical_neighbours.png) |
| 4 | 30.399 | [demo/frames/04_better_prompt_copied.png](../../demo/frames/04_better_prompt_copied.png) |
| 5 | 42.182 | [demo/frames/05_cached_original_preview.png](../../demo/frames/05_cached_original_preview.png) |
| 6 | 58.172 | [demo/frames/06_clip_uploaded.png](../../demo/frames/06_clip_uploaded.png) |
| 7 | 79.065 | [demo/frames/07_clip_verdict_and_feedback.png](../../demo/frames/07_clip_verdict_and_feedback.png) |
| 8 | 91.479 | [demo/frames/08_architecture_connections.png](../../demo/frames/08_architecture_connections.png) |

The sample actually recorded is **“a spoon and a laptop”**, using the saved `pinned-sample` decision. The selected log and published-copy receipt both record `p_fail_before=0.4678787878787878` and `p_fail_after=0.15833333333333333`, displayed as **46.8% original → 15.8% rewrite**. These are the fixed deck values for this demo. The separate historical-only value is `historical_p_fail=0.5345454545454545`; it is not substituted for the displayed mixed risk proxy.

The clip-review beat uses the labeled **“synthetic FFmpeg loop of a Gemini still”**. It reuses a stored review (`feedback_created=false`, `reused_stored_review=true`), retains the existing machine-feedback record and shows **46.8% → 46.8%**. It does not demonstrate a newly created review, a further risk reduction, or motion-review accuracy. The copy step reports “Copied ✓”; the recorder performs **0 clipboard reads**. The exact canonical samples-only message is visible in the architecture beat. Original new-take files and the prior movie/frame backup are retained at the paths above.

## Repository, tags and provenance — PENDING final release

| Item | Snapshot / completion status |
| --- | --- |
| Source baseline | `9f77cbeb9da1b89cc993cc5c70a1c7dd9a9cc1af` |
| Final production source commit | `d638c0690cb17d60316922eb30a14f150fe7c23c`; pushed to main; native provenance PASS |
| Native build | `095a35c2-74ad-49cb-8ae8-507a6216ee74` |
| Current local/build-input runtime hash | `a3f7c0a10ebec2e00ff7bc7bfc01676c712405aff0a8dad55f8c82eef2364fa7` |
| Native archive runtime hash and both-hash comparison | PASS: 25/25 files; Git and native archive both `a3f7c0a10ebec2e00ff7bc7bfc01676c712405aff0a8dad55f8c82eef2364fa7` |
| Production image digest | `sha256:4bf0668ae549f7ab924f17e36105b621f1f25676aefb6e53e06154db4384e932`; accepted revision serves 100% traffic |
| Push to main | Source commit `d638c0690cb17d60316922eb30a14f150fe7c23c` pushed; later receipt publication PENDING |
| New aibc-2026-submission-v3 tag | Lightweight tag created and pushed at `d638c0690cb17d60316922eb30a14f150fe7c23c`; final anonymous verification PENDING |
| Older aibc-2026-submission tag | `dd12f279e364cbd217a4178b51c1d270cacebbdd`; local and anonymous remote match |
| Older aibc-2026-submission-v2 tag | `bdcdecdf6db6b0c2bebea8a35ed350de5f005940`; local and anonymous remote match |
| Worktree secret scan | 522 files, 96 binary files, 0 hits, 0 errors; retained snapshot |
| Final indexed/history secret scan | Source history PASS: 12 commits, 597 blobs, 74 binary payloads, 0 hits, 0 errors. Final receipt/tag history repeat remains PENDING. |
| Anonymous final clone / source tag / runtime agreement | PENDING; production source tag and later evidence-only main commits have separate roles |
| README + submission preview clause | PASS — pushed final samples-only wording; production architecture and public README top/preview clause exactly match in self-QA steps 26–28 |
| Brief description | 952 characters, unchanged in the source commit |
| Demo link / pitch deck export | Existing placeholders remain pending user publication/export |

The lightweight **`aibc-2026-submission-v3` tag pins production SOURCE commit `d638c0690cb17d60316922eb30a14f150fe7c23c`**. Later `main` commits publish post-promotion QA, demo and evidence; they retain the same 25-file runtime hash `a3f7c0a10ebec2e00ff7bc7bfc01676c712405aff0a8dad55f8c82eef2364fa7`. Final public verification must confirm the source tag and runtime agreement without requiring the later evidence-commit HEAD to equal the production source tag. Evidence publication and that final anonymous check remain PENDING.

[Scope/tag checks](release_scope_audit.json), [worktree secret scan](secrets_worktree.json), [source history scan](history_scan_source_release.json), [native 25-file/source/image provenance](source_match.json). Native provenance is complete for the pushed source and exact promoted revision; final anonymous publication checks remain PENDING.

## Not done at this snapshot

PENDING: final report/demo receipt commits and publication; final receipt/tag history scan and anonymous clone verification. All applicable candidate gates, native 25-file provenance, 100% production promotion, 28/28 production self-QA steps/screenshots, one clean demo take with eight replacement frames, final native budget confirmation, source push and the new v3 source tag are complete. No live generation is selected. No Veo calls were made. Clip-review accuracy and actual billed spend remain unmeasured.
