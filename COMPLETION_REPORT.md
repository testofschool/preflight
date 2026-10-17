# Preflight — deployed A+B, partial acceptance report

Snapshot: 2026-10-16 KST, after G1 expired and the upload path was deployed. **A+B are live; overall acceptance remains PARTIAL. V4 FAIL, V8 NOT RUN, and the feedback interpretation in A3/B2 is a documented semantic extension.**

Live app: **https://preflight-jcgro45veq-as.a.run.app** — the default Cloud Run `run.app` URL, no login or custom domain. Private source: https://github.com/testofschool/preflight.

## Authority, scope and gates

The attached handoff is the proposed implementation contract, not evidence that its numerical claims, credentials or billing prerequisites are true. The owner directly filled section 0 and authorized A1–A6, then V1–V7/V9/V10, G1 and upload-only B1–B2/V8. The ZIP passed CRC/path checks; its handoff equals the standalone file; all six originals remain preserved outside the repository. Dataset bytes are checked before fitting/evaluation.

The URL notice was prepared at **02:24:09 KST**; G1 expired at **04:24:09** and this continuation began after **04:25**. Automatic goal/heartbeat messages were not treated as human replies. The one-time G1 continuation was deleted after firing. No teammate message was sent. [G1 receipt](../evidence/preflight-20261016/g1_notice.json).

Dedicated Singapore resources use the authorized configured project; unrelated legacy resources were not repurposed. Actual project identifiers and credential values are excluded from saved source/logs. An initial AI Studio key request returned HTTP402 for depleted prepaid credit; production explicitly uses Vertex AI with Application Default Credentials and linked GCP billing. The AI Studio cap was not raised. The key was transferred through stdin to Secret Manager and is not injected into this production Vertex container. **G2 holds: Veo calls 0; no generation endpoint.**

## V1–V10 acceptance ledger

| ID | Result | Actual number and native evidence |
| --- | --- | --- |
| V1 | PASS within supplied overlap test | **0** repository files with an exact 20-token shingle shared with the reference; four binary artifacts excluded. [Receipt](reports/freshness-final.json), [stdout](logs/freshness-final.txt). This does not prove authorship or creation date. |
| V2 | PASS within scan scope | **0** forbidden-marker hits, including repository/README/logs/index; exact current credential and project identifier byte scan also zero. Current revision native log scan **0** forbidden markers after identifier redaction. [Guard](reports/secrets-final.json), [log scan](reports/cloud_log_scan_postcheck.json). |
| V3 | PASS | Cold **19.738130s**; five warm requests **4.862889, 4.586187, 4.378278, 4.620390, 4.329699s**; all HTTP200, genuine tools and verified sessions. Timed on revision `preflight-00006-d4s`, same image as current revision. [Receipt](reports/cloud_latency_postcheck_release.json), [stdout](logs/cloud_latency_postcheck_release.txt). |
| V4 | **FAIL; exact 0.72 UNVERIFIABLE** | Five-seed held-out vote both-bad AUC **0.668329 < 0.68**. Cold-start IRT **0.714796 ≥ 0.696622** baseline; strict train-only TF-IDF **0.715403**. The composite fails its first condition. [Evaluation](artifacts/evaluation.json), [stdout](logs/evaluation.txt). |
| V5 | PASS | Current release **9/10** strict estimated-risk reductions (required ≥6), **0** higher-risk returns, all **10/10** non-higher; **10** attempts, **0** retries. Cat/dog safely returned unchanged. [Responses](reports/rewrites_postcheck_release.json), [stdout](logs/rewrites_postcheck_release.txt). No video-quality gain established. |
| V6 | PASS | All **10/10** V5 requests completed **6** real ADK tools and readback-verified Agent Platform managed sessions. Native signed Gemini function calls; trace below. |
| V7 | PASS | Native Firestore counts **510 prompts / 508 items / 2 verdicts**. All **1,016** historical documents and **10** abilities match local exports, **0** differences; the two extra prompts hold separately counted real clip feedback. [Counts](reports/firestore_postcheck_counts.json), [integrity](reports/firestore_integrity_postcheck_final.json), [stdout](logs/firestore_integrity_postcheck_final.txt). |
| V8 | **NOT RUN** | **0/3 known-defect clips** validated. One owner clip was inspected and reviewed as a negative control, with no independently confirmed intrinsic defect; it does not count toward V8. All nine owner shots are resident and independently screened; **0** clips have a confirmed intrinsic defect in the sampled references. Accuracy is **UNVERIFIABLE** from these fixtures. [Availability](reports/owner_clip_availability.json), [frozen negative-control reference](reports/postcheck_canary_reference.json). |
| V9 | PASS | README includes architecture, data/licence, limits, five samples, cannot-do statements, Agent Platform Sessions and actual B limitations. [Headers](logs/readme_headers.txt). |
| V10 | PASS | Current native config **asia-southeast1, min0, timeout40s, default concurrency80**, revision `preflight-00007-q2d`; 100% primary traffic. [Config](reports/cloud_run.json), [stdout](logs/cloud_run_config.txt). |

[acceptance.json](reports/acceptance.json) is the machine-readable ledger. Historical Track A receipts are preserved in [track_a_before_postcheck](reports/track_a_before_postcheck/). Its former 10/10 rewrite result and 508/508/0 counts are historical, not the current release's result.

### Commands and recorded stdout

Run from this repository with the sibling Python3.12 `.preflight-cloud-venv`. Project configuration is read from the authorized runtime configuration, never literal identifiers in saved command lines. Shell initialization is sourced silently before credentialed operations; environment and credentials are not printed.

| Check | Executed command / method | Recorded stdout / receipt |
| --- | --- | --- |
| V1 | `python scripts/check_freshness.py --reference ../evidence/preflight-20261016/inputs/pregen_irt.py` | [freshness-final.txt](logs/freshness-final.txt) |
| V2 | `python scripts/check_secrets.py --include-index`; exact-value scan in memory; selected native Cloud Run logs | [secrets-final.txt](logs/secrets-final.txt), [log scan](reports/cloud_log_scan_postcheck.json) |
| V3 | `python scripts/measure_cloud.py --url https://preflight-jcgro45veq-as.a.run.app --validation-only --report reports/cloud_latency_postcheck_release.json --log logs/cloud_latency_postcheck_release.txt` | [timed curl stdout](logs/cloud_latency_postcheck_release.txt) |
| V4 | `python scripts/evaluate.py`, frozen data, five fixed prompt holdouts | [evaluation.txt](logs/evaluation.txt) |
| V5/V6 | `python scripts/verify_rewrites.py --url https://preflight-jcgro45veq-as.a.run.app --report reports/rewrites_postcheck_release.json --log logs/rewrites_postcheck_release.txt` | [rewrites_postcheck_release.txt](logs/rewrites_postcheck_release.txt) |
| V7 | `python scripts/verify_store_live.py` with distinct output paths; native Firestore count aggregations | [integrity stdout](logs/firestore_integrity_postcheck_final.txt), [count receipt](reports/firestore_postcheck_counts.json) |
| B native canary | `python scripts/verify_postcheck_canary.py --url` with the candidate URL and `--reference reports/postcheck_canary_reference.json` | [postcheck_canary_live.txt](logs/postcheck_canary_live.txt) |
| B primary cache | Native status/OpenAPI read, then one exact cached multipart upload | [postcheck_primary_cache.json](reports/postcheck_primary_cache.json) |
| B current-image fresh smoke | `python scripts/verify_postcheck_smoke.py --url https://preflight-jcgro45veq-as.a.run.app --reference reports/postcheck_smoke_reference.json --report reports/postcheck_optimized_smoke.json --log logs/postcheck_optimized_smoke.txt` | [one-upload stdout](logs/postcheck_optimized_smoke.txt) |
| V8 | **Not run**; `scripts/verify_postcheck.py` is prepared for three frozen known-defect references | No fabricated success or stdout |
| V9 | `rg '^#' README.md` | [readme_headers.txt](logs/readme_headers.txt) |
| V10 | `gcloud run services describe preflight --region asia-southeast1 --format=json`, safe fields selected before writing | [cloud_run_config.txt](logs/cloud_run_config.txt) |
| Tests | `python -m pytest -q tests` | **71 passed, 2 warnings, 11 subtests**; [tests_postcheck.txt](logs/tests_postcheck.txt) |
| B browser | One cached Pass and one separately cached Flagged upload; desktop1440/mobile390; preview/4.5s seek succeeded | [Pass receipt](reports/browser_postcheck_qa.json), [Flagged stdout](logs/browser_postcheck_flagged_qa.txt), [Flagged receipt](reports/browser_postcheck_flagged_qa.json) |

[commands.json](reports/commands.json) retains earlier executions and identifies the added current-release checks. The paid rewrite/clip verifiers refuse to overwrite existing result files. These are executed results, not instructions to repeat paid checks. Unit fakes are distinct from native cloud inference. Pytest warnings concern Starlette HTTPX deprecation and ADK experimental function schemas. Browser inspection recorded two local blob range failure events; partial-content responses still decoded the actual preview successfully. No external API/static request failed. Two local integrity CLI attempts failed before remote access because the shell lacked the required project runtime setting; a different output filename did not fix that setting. Loading the already authorized gcloud project into process memory allowed the final read-only comparison to pass. [Literal attempt record](reports/verification_attempts.json).

### Native timing and ADK evidence

A new revision, minimum instances0 and deployment health check disabled, was invoked first through timed curl to measure cold startup. V3 was measured on revision6 at timeout38s; the subsequent revision7 changed timeout to40s and kept the exact source image. Current timeout is `ceil(2 × max(17.707208 original calibration, 18.950459 B canary, 19.738130 current A cold)) = 40s`. [Derivation](reports/postcheck_timeout_calibration.json). No acceptance threshold was relaxed. The current primary cache request also passed; a separate fresh current-image upload later measured10.346132s, below the existing slowest sample, so the40s derivation remains unchanged.

The ten hardest prompts were selected before requests by descending frozen fitted difficulty, with stable artifact-order ties. Every row completed six tools and a verified managed session; ten requests, zero retries.

| Rank | Prompt | Before | After | Tools / session |
| --- | --- | --- | --- | --- |
| 1 | A person is wrestling | 0.500000 | 0.058333 | 6 / verified |
| 2 | a spoon and a laptop | 0.534545 | 0.300000 | 6 / verified |
| 3 | A person is shooting basketball | 0.300000 | 0.133333 | 6 / verified |
| 4 | a cat and a dog | 0.306667 | 0.306667 | 6 / verified |
| 5 | A person is hugging | 0.500000 | 0.250000 | 6 / verified |
| 6 | an orange bird | 0.340000 | 0.303529 | 6 / verified |
| 7 | A person is squat | 0.500000 | 0.290000 | 6 / verified |
| 8 | A person is shaking head | 0.500000 | 0.450000 | 6 / verified |
| 9 | a tv and a laptop | 0.534545 | 0.275000 | 6 / verified |
| 10 | a bicycle and a car | 0.433333 | 0.233333 | 6 / verified |

One current native trace: `nearest_prompts → difficulty(original=0.500000) → rewrite → difficulty(candidate1=0.058333) → difficulty(candidate2=0.375000) → difficulty(candidate3=0.273333)`. Gemini emits signed function calls in three planner steps; a fourth model call generates candidates. The strict guard returns only a lower-risk candidate. Cat/dog returned the original with no safe rewrite; the UI hides candidate/copy controls in that case. Session IDs retained in receipts are opaque resource IDs; authentication cookies/headers are excluded.

## Track B behavior, observations and limits

`POST /postcheck` accepts an owner MP4 upload plus its scene prompt and model label. It validates the actual MP4 container, limits30MiB/30s/12million pixels, and supports the owner's4398×1886 clips. A single bounded ffmpeg decode creates a silent512-side/15fps review video and explicit2fps JPEG batches; Gemini reviews both routes with at most three parallel calls and no retry. Defects have typed categories, MM:SS/seconds and a reason. Unreviewable or failed evidence returns an error, not a clean verdict. Default video sampling1fps, missed events shorter than0.5s, downscaled detail and excluded audio are disclosed in the UI/README. Temporary media is bounded and removed; no generation call is made.

The independently inspected `01_wake.mp4` (4,107,887bytes,5.041667s,HEVC4398×1886) has SHA-256 `4eada38585ce26dda3d1936e2996d18e4c5487ec6c4230f7e25440b956890c9e`. The negative-control reference was frozen before inference. Initial candidate revision4 used the earlier two-pass decoder: actual multipart review **18.950459s**, HTTP200, **2** real Gemini calls,10 frames, no defects returned. Exact repeat **0.937997s**, zero new model calls, same stored review and no duplicate feedback. The following real `/preflight` call took **6.852915s** and used the updated score with six tools and a verified session. These three requests used six model calls total and zero retries. [Full receipt](reports/postcheck_canary_live.json).

The optimized image is now primary revision7. A primary cached request returned HTTP200 in **1.560978s** (the recorded interval includes status/OpenAPI reads), **0** new model calls and no new feedback. The optimized local decoder measured **5.153659s**, with all10JPEGs independently decoded, as recorded in [postcheck_decode_optimized.json](reports/postcheck_decode_optimized.json) / [stdout](logs/postcheck_decode_optimized.txt); that local measurement is separate from cloud inference. A new02 upload on current revision7 measured **10.346132s**, HTTP200, **2** real model calls,10frames and a new durable verdict. [Fresh optimized smoke](reports/postcheck_optimized_smoke.json). The model flagged physics at4.5s and changed the proxy29.0909%→32.6364%; a cached browser check displayed the stored flag and sought to4.5s with **0** new model calls and no duplicate feedback. This proves operational behavior, not detection accuracy.

The pre-inference02 reference had no confirmed defect. A separate, explicitly post-inference [visual adjudication](../evidence/preflight-20261016/v8-reference-engine/02_door/post_inference_adjudication/adjudication.json) **DISAGREED** with the model's narrow claim of an instantaneous camera-side flip: denser frames show continuous door movement and stable corridor geometry. Its prior reference remains unchanged. The automated verdict was retained as observed; it was not silently corrected or credited as a pre-known V8 match. This disagreement illustrates why the machine-feedback proxy is unvalidated. No measured false-positive rate or exhaustive clean-video claim follows from this case.

**A3/B2 literal contract deviation — PARTIAL:** a machine verdict on one clip is not a human pairwise both-bad vote. Historical `both_bad_rate` and all human evidence remain unchanged. The app separately counts clip pass/failure feedback and applies a labelled **MIXED heuristic proxy** to subsequent `p_fail`; `historical_p_fail` retains the original 5-NN estimate. The canary showed21.6667% historical →20.7639% mixed score, feedbackcount1/failures0. Exact unseen prompts use a labelled neighbour prior, not a refitted vectorizer/item model. This demonstrates durable feedback wiring; it does **not** literally recompute human both-bad rates, preserve A3's pure 5-NN definition after feedback, calibrate risk, or establish that future prediction is better. Therefore A3/B2 are not claimed fully compliant with their literal definitions.

**V8 remains NOT RUN,0/3.** OS download requests were issued for the nine individual shots. Finder access initially returned a locked-Mac error and the owner was asked to unlock/Download Now. All nine later became resident at approximately05:09:55 KST without a new human reply; verified local copies/hashes are now available. Independent sampled reference screening of all nine is complete, including targeted denser/native frames where uncertainty arose. No eligible confirmed-positive clip was established. The edited compilation was excluded. No synthetic defects, cuts or ordinary motion blur were labelled as intrinsic defects to force a pass. The [reference availability receipt](reports/postcheck_reference_availability.json) records **9 screened,0 confirmed-positive clips** and hashes of frozen observations. The three-positive-clip accuracy run was therefore not executed. A future valid accuracy test requires three independently confirmed defect references frozen before inference; At least two one-to-one category/time matches within±2s are required; compatible reasons also need inspection. The negative control cannot satisfy that criterion.

## Statistical reproduction and limits

The supplied data reproduces **1,911 votes, 508 prompts, 10 models, 2,080 observed cells**, and **407/1,911 = 21.29775%** both-bad votes. The latter is a human pairwise rejection share, not evidence that one fifth of current generations wastes money. Outcome coding is win1/loss0/tie0.5/both-bad0, aggregated by prompt/model. Unsupported vocabulary abstains instead of returning invented numerical risk.

The fresh implementation uses sorted reference ordering, matching split/initialization seeds and L2 coefficients, analytic gradients and discrimination bounded to [0.3,4]. The reference clips discrimination inside an unconstrained optimizer; byte-identical fit parameters are not claimed. All **11/11** fitted optimizations reported convergence; the full fit's projected gradient was approximately **0.001218**, with termination by relative objective reduction.

The reference fits TF-IDF on all prompt text; this transductive path is labelled separately from the strict train-only path. The supplied preregistration and result payload do not define or contain the handoff's 0.72 both-bad AUC claim. The declared diagnostic here labels each held-out human vote both-bad/not-both-bad and assigns its prompt the mean training-neighbour rate, using five fixed 20% prompt holdouts. Its mean is **0.668329**; the separate any-both-bad-prompt diagnostic is **0.630676**. Targets, seeds and thresholds were not changed to rescue a failing result.

Other preregistered findings remain visible: Q1 IRT **0.642161** vs baseline **0.714971**, FAIL; Q3 model-routing share **0**; Q4 observed outcome **0.573003** for both choices, difference **0**, FAIL. Positive discrimination fixes model ordering. No routing, current-Veo calibration, measured savings, novelty literature priority, or generated-video quality claim follows from these results. Historical `initial_diagnostic` artifacts retain the superseded pre-audit settings; canonical final outputs are `artifacts/evaluation.json` and `logs/evaluation.txt`.


## Delivered and not done, per track

**Track A delivered:** fresh frozen-data ingest/IRT/retrieval; Firestore import and integrity verification; real preflight predictions; genuine ADK/Gemini tools and Agent Platform Sessions; strict rewrite guard; English responsive interface/architecture; default public Cloud Run URL; current latency/rewrite/config evidence; private source packaging. The original deployed A receipts are retained. **Not achieved:** V4risk-AUC threshold, calibrated current-video probabilities, measured savings, prospective rewrite video-quality improvement, or actual invoice cost. The A3 semantic extension above is partial compliance.

**Track B delivered:** upload-only actual video plus2fps frame review, bounded decoding/calls, typed verdicts, real Firestore write, exact-cache deduplication, durable updated-score wiring, separated historical/machine evidence, UI preview/results/errors, unit/integration tests, native negative-control/cache/preflight evidence, a fresh optimized-image upload, and actual Pass/Flagged browser checks. **Not achieved:** V8known-defect accuracy; proof that feedback improves predictions; literal B2both-bad recomputation. The asset hydration dependency is resolved; the supplied sampled fixtures do not establish three known-positive references, so V8accuracy remains unverified. The feature remains available while validation is honestly incomplete. Track A was not withheld. G2still holds, totalVeo calls0.

## Files, sizes and build-input changes

[FILE_INVENTORY.json](reports/FILE_INVENTORY.json) lists every repository file with byte size and SHA-256, excluding Git/caches/virtual environments. It includes a local ignored server log as an explicitly local artifact; Git inclusion is recorded. Its own hash is null to avoid recursion and its byte size is included. The [external evidence inventory](../evidence/preflight-20261016/FILES.json) covers preserved inputs, intake/G1/final guard/Git receipts, frozen references and actual desktop/mobile screenshots. Runtime venvs are installed siblings. Owner MP4 bytes are outside the repository; [availability](reports/owner_clip_availability.json) records names, sizes and all nine verified hashes. Original G0 records remain historical in `reports/g0_*`; original A records remain in `reports/track_a_before_postcheck/`.

Build inputs, file by file (all current hashes/sizes are in the inventory):

| File | Change / reason |
| --- | --- |
| `requirements.txt` | Fresh direct requirements; FastAPI0.119.1→**0.133.0** to satisfy ADK/telemetry constraints. Rejected0.143.2 attempt was not deployed. |
| `requirements-cloud.txt` | Pinned ADK[gcp]**2.12.0**, Firestore**2.34.1**, GenAI**2.31.0**; B adds direct **python-multipart0.0.32**, already present transitively in the production lock. |
| `requirements-cloud.lock` | Exact106-package production resolution; unchanged by B. Docker installs this lock, consistency check passed. |
| `requirements.lock` | Historical33-package G0/local environment; not production. |
| `requirements-dev.txt` | Local tests; actual cloud venv used pytest9.0.3. |
| `Dockerfile` | Python3.12-slim base stays pinned to `sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`; B adds **ffmpeg7:7.1.5-0+deb13u1**. NonrootUID10001, productionlock/artifacts, access logs disabled. |
| `cloudbuild.yaml` | Runtime image substitution and dedicated build service account. |
| `.dockerignore` | Excludes Git/caches/tests/evidence/unused artifacts from image context. |
| `.gcloudignore` | Restricts upload to runtime build inputs; owner media/data evidence not uploaded. |
| `app.py` | Cloud readiness, shared20/min and1000cumulative admission; B bounded multipart/tempfiles, per-instance video semaphore1, deterministic cached verdicts and error handling. |
| `cloud/postcheck.py` | New real Vertex visual review, one-pass ffmpeg video+2fps frames, bounded schema/timeout/concurrency and limitations. |
| `cloud/store.py` | Separately counted provenance-bearing feedback, idempotent durable review, unchanged historical documents and labelled mixed proxy. |
| `cloud/rewrite_agent.py` | Signed Gemini/ADK tools with managed sessions; explanation wording reflects separately counted feedback. |
| `preflight_core/*.py`, `scripts/build_data.py` | Fresh bounded IRT/retrieval/provenance; source mismatch stops before writes. |
| `data/genai_video_test.parquet` | Frozen SHA-256 `c58ba145070415d084950fe8a80c517fd14e05d3285e371338a66791cee5de94`; unchanged. |
| `artifacts/engine.json`, `vectorizer.joblib`, `prompt_vectors.npz` | Fresh fit/retrieval runtime inputs; unchanged by B. Engine hash `86c4d83e322f245e49a6955fbf5ff9ec1c42878496df2569d0026fbb3862db4c`. |
| `static/index.html`, `app.js`, `postcheck.js`, `styles.css` | Upload/preview/defect timecodes/updatedscore UI; historical-vs-mixed evidence labels, strict rewrite/copy guard. |
| `static/architecture.html`, `architecture.js` | Actual upload/frame/feedback path and disclosed limitations. |
| `scripts/cloud_ops.py`, `release_cloud.py`, `measure_cloud.py` | Dedicated identifier-safe provisioning/release, candidate deployment and separate validation output files. |
| `scripts/verify_postcheck.py`, `verify_postcheck_canary.py`, `verify_postcheck_smoke.py`, `verify_decode_local.py` | Frozen-reference no-retry native evidence helpers; V8 script not executed. |

Current Cloud Build **SUCCESS**, ID `35497462-13c9-4601-bbda-9f0f980d573f`; source digest `7b649f3f6d72564510289f58afa482419c052296c24ee4fab0924f2cfde999aa` matches current runtime inputs. [Build receipt](reports/cloud_build.json). One earlier build was explicitly cancelled and superseded to fix ultrawide decode/concurrent cache handling; that attempt is retained in `reports/build_attempts/`. The final build, current Track A checks, current-primary cache check and runtime digest refer to the optimized image; the uncached B canary remains evidence from the earlier two-pass image. Documentation/receipt changes do not alter it. Shared admission may count requests whose later external step fails. Min0 reduces idle compute; no claim that all cloud resources are free.

## Factual three-sentence submission description

Preflight runs on Google Cloud Run and retrieves historical prompt outcomes and IRT parameters from Cloud Firestore, the document database shared with Firebase. A Google ADK 2.12 agent uses Gemini 3.5 Flash through Vertex AI for tool-checked prompt rewrites, while Agent Platform Sessions persists anonymous conversation history. Uploaded MP4s are reviewed through Gemini video understanding and explicit 2 fps frame batches; timestamped machine verdicts are saved in Firestore and separately counted feedback changes a labelled, uncalibrated risk proxy without overwriting historical human votes.


## Track C/D (2026-10-17)

**Outcome: PARTIAL overall. Track D is live and verified on `preflight-00016-tuk` at 100%; Track C code and tests are present, but the production image feature is disabled (`preview: false`) because V11 did not pass.** G3 dissolved on real image bytes from the primary model in `global`. Later provider `ClientError` responses prevented all ten sample cases from succeeding. Track C did not block the independent D rollout.

Recorded at 2026-10-17T13:39:47.403247+09:00. Git base matched the requested `266b556`. The actual pre-change test baseline was **90 passed**, rather than the handoff's 71; nine new fake-only preview tests bring the final total to **99 passed, 0 failed**. SDK/CLI and ADC were installed/authenticated on this Mac; the original copied virtual environments pointed at another user's home, so checks used `/tmp/preflight-cd-venv/bin/python`. Project identifiers and credential values are excluded from these receipts; the requested model, location, cap values and required configuration names are recorded.

| Check | Final result / receipt |
| --- | --- |
| Initial service | `preflight-00009-n9b` at 100%, min 0, timeout 40; [baseline](reports/track_cd_baseline_service.json). |
| G3 | Regional primary returned 404 in 1,429 ms; `global` primary returned image bytes / 200 in 4,430 ms. No alternate image model or Veo call. [Probe](reports/preview_probe.json). |
| Compile / unit regression | `py_compile app.py cloud/*.py`: 0 errors. **99 passed**; all seven requested preview cases plus local-disabled and UTC/ceiling checks. Existing postcheck tests remained unchanged: **38 passed**. [Tests](reports/track_cd_tests.txt), [postcheck subset](reports/postcheck_cd_tests.txt). |
| Secrets / identifiers | 0 credential-marker hits, complete indexed scan; 0 project-identifier hits. [Secrets](reports/track_cd_secrets.json), [identifier scan](reports/track_cd_identifier_scan.json). Final report is included in the last scan. |
| Candidate risk regression | All six requests 200. Final isolated warm maximum **5.323689 s**. A preceding run had a **6.812296 s** warm outlier; it was not promoted on that result, and the raw run is retained. Cause of the outlier was not established. [Isolated battery](reports/cloud_latency_d_candidate_isolated.json), [outlier run](reports/cloud_latency_d_candidate.json). |
| Primary risk regression | All six requests 200; warm **4.646156–5.127007 s**. First request in this primary replay was 5.883486 s. Validation-only now reads the supplied URL without creating another revision or changing traffic; the legacy first-request label is not a certified cold-start measurement. [Primary battery](reports/cloud_latency_d_primary.json). |
| Postcheck / user path B | Frozen smoke **NOT RUN — required frozen reference path not on this machine**. Both original reference JSON files are byte-for-byte unchanged. Two `testsrc` attempts returned 503 and are retained. A 5-second FFmpeg loop of the generated spoon/laptop still then returned **200 in 2.811 s**, with two actual model calls and a valid inspection response. Final candidate replay: **200 / 0.743 s**; final primary replay: **200 / 0.545 s**, cached / zero new model calls. This is **operational smoke, synthetic clip, not the frozen reference**, and establishes no V8 accuracy claim. [Fresh synthetic](reports/postcheck_cd_synthetic_candidate.json), [failed testsrc 1](reports/postcheck_cd_synthetic_attempt_1.json), [failed testsrc 2](reports/postcheck_cd_synthetic_attempt_2.json), [candidate](reports/postcheck_d_candidate.json), [primary](reports/postcheck_d_primary.json), [reproducible synthetic MP4](reports/track_cd_synthetic_smoke.mp4). |
| Firestore integrity | **1,016 / 1,016** original historical documents match, 0 field/hash/document differences. Current totals **511 prompts / 508 items / 4 verdicts**. The attempted identity reuse did not avoid one new feedback-only prompt document from the authorized synthetic smoke; original human-vote fields were not changed. No records were deleted to restore the old 510 total. [Integrity](reports/firestore_integrity_cd_primary.json), [counts](reports/track_cd_store_counts.json). |
| V11 | **PARTIAL: 9 / 10 unique original/rewrite fixtures succeeded**, every successful image >10 KiB. Three preview 503 responses were observed across attempts; the last remained a `ClientError` even with 35-second spacing. The cause/status behind that provider class was not inferred from the generic public error. All sample latencies and image sizes are recorded. No quota was raised, no automatic fallback was added, and production remains disabled. [Main receipt](reports/preview_live.json), [initial failure](reports/preview_live_attempt_1.json), [diagnostic recovery](reports/preview_diagnostic.json), [spaced cases](reports/preview_spaced_samples.json). |
| V12 | **PASS:** sixth admitted-attempt request in the minute returned 429 with **Retry-After: 48**. Daily exhaustion and maximum ceiling are covered in fake-only tests. Deployed cap is 60/day UTC, code ceiling 500, minute cap 5; none was raised for verification. [Live cap](reports/preview_live.json), [tests](tests/test_preview.py). |
| V13 | **PASS:** primary `gemini-3.1-flash-lite-image`, `1K`, **$0.0336** image-output list price, computed from **1,120 × $30 / 1,000,000**. Vertex's prose rounds this to $0.034. Source opened on 2026-10-17: [Vertex pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing). The public API exposes this source/date. Text input is outside that per-image-output figure. [Primary status](reports/track_cd_primary_status.json). |
| V14 | **PASS:** repeated identical request returned `X-Preview-Cache: hit`, `model_calls: 0`; **9** durable cached previews correspond to the **9** distinct successful fixtures. Cache hits still consume admission budget, as specified. [Cache receipt](reports/preview_live.json), [counts](reports/track_cd_store_counts.json). |
| V15 | **PASS:** actual primary at 1440×900: **18 objects / 7 colours / CTA bottom 837.4375 px**. Textarea remains six rows. [Acceptance receipt](reports/first_viewport_after.json), [raw probe](reports/first_viewport_d_primary/summary.json). Optional script axes V3/V4 have no declared budgets and remain UNMEASURED; no comprehension test is claimed. |
| V16 | Enabled-preview candidate states: **12 PNGs** from revision `preflight-00012-rag`. Final D candidate and primary each add **6 PNGs**, plus 6 local preservation screenshots (**30 total**), in both requested dimensions. Primary checks confirm no horizontal overflow, no page script errors, the original home session node preserved but hidden in the footer, the mode pill relocated, and the image button disabled with the exact tooltip. Full production preview states were **NOT RUN because C is disabled**. [Manifest](reports/track_cd_screenshot_manifest.json), [candidate UI](reports/d_candidate_ui.json), [primary UI](reports/d_primary_ui.json). |
| Copy / scope | 0 banned-string hits in `static/`. Score and clip disclaimer paragraphs are byte-for-byte unchanged; architecture rounding and the declared D7 replacement are applied. Home session status was restored as a hidden footer node rather than deleted; architecture's session node stays in its intro. `preflight_core`, `cloud/postcheck.py`, and the existing postcheck tests have no changes. [Gate](reports/track_d_promotion_gate.json), [node preservation](reports/track_d_status_preservation.json). |
| G4 / promotion / primary | **preflight-00016-tuk at 100%**, min **0**, timeout **40**, both required image-model and daily-limit environment names present, daily cap **60**, `preview: false`, `/postcheck` enabled. The diagnostic preview tag was removed. The primary `/preview` correctly returns disabled-service 503 without a model call. [Promotion](reports/track_cd_promotion.json), [primary release](reports/cloud_run.json), [status](reports/track_cd_primary_status.json). |
| Spend | [Numeric receipt](reports/spend_after_preview.json) is **0**: the authenticated 2026-10-17 actual-cost report, grouped by SKU, shows no posted rows / ₩0. This is delayed posted spend, **not zero incurred cost**. Ten observed successful image outputs, including G3, have **$0.336 output-only list price**, excluding text input and unobserved billing adjustments. [Context](reports/spend_after_preview_context.json). |

### Build-input changes and self-verification repairs

| File | Byte delta | Reason |
| --- | ---: | --- |
| `Dockerfile` | +23 | Normalize copied runtime files with `a+rX` so the existing nonroot user can read them. The first candidate failed on copied mode-0600 `app.py`; the failed candidate was never sent primary traffic. Base image, ffmpeg pin and nonroot user stay unchanged. |
| `requirements-cloud.txt` | +15 | Pin Pillow 13.0.0 for exact JPEG quality 82 conversion. |
| `requirements-cloud.lock` | +15 | Include the same pinned Pillow runtime dependency. |
| `scripts/release_cloud.py` | +623 | Required preview settings, disabled default and 40-second default service timeout. |
| `scripts/measure_cloud.py` | +513 | Make `--validation-only` read-only so candidate verification cannot silently create or route a new revision. |

[Byte-delta receipt](reports/track_cd_build_input_changes.json). Runtime build digest matches the working tree. One preliminary build was superseded/cancelled; the unreadable-source candidate and all failure receipts are retained. An initial D rollout to `preflight-00013-kil` passed runtime checks but still deleted the home session node; that constraint mistake was corrected and final `preflight-00016-tuk` now preserves it hidden in the footer. The zero-fix-round target was not met; the permission and status-preservation repairs, transient/provider failures and repeated latency measurements are explicitly recorded, not presented as a clean first attempt.

No Veo/video-generation provider calls, provider-model substitution for quota errors, cap increase, new UI library, font or page section. The synthetic video was generated locally with FFmpeg under the user's explicit path-B allowance. The final outcome is not a claim that every original handoff battery item passed: C activation remains blocked; the 510 total-prompt baseline changed by one authorized operational feedback record; full preview production states and frozen-reference smoke were not executed for the reasons above.

### Session block

```text
Revision live: preflight-00016-tuk · Candidate URL: https://postcheck-candidate---preflight-jcgro45veq-as.a.run.app · Track C: BLOCKED(ClientError) · Track D: PASS
G3 probe: gemini-3.1-flash-lite-image@global 200 4430 ms (regional 404 / 1429 ms; alternate model not called)
V11: PARTIAL — 9/10 unique cases succeeded; final rewrite still 503 ClientError after 35 s spacing · reports/preview_live.json + reports/preview_spaced_samples.json
V12: PASS — sixth call 429, Retry-After 48 s; daily cap and ceiling covered by unit tests · reports/preview_live.json + tests/test_preview.py
V13: PASS — $0.0336 / 1K; Vertex $30/M output tokens × 1120; checked 2026-10-17 · reports/track_cd_primary_status.json
V14: PASS — cache hit / model_calls 0; 9 cached documents for 9 successful distinct previews · reports/preview_live.json + reports/track_cd_store_counts.json
V15: PASS — 18 objects / 7 colours / CTA bottom 837.44px · reports/first_viewport_after.json
V16: PARTIAL — 12 enabled-C candidate states + 6 final-D candidate + 6 primary + 6 local PNGs; production preview states NOT RUN because C is disabled · reports/track_cd_screenshot_manifest.json
Baselines re-checked: tests 99 · secrets 0 · /preflight warm 4.65–5.13 s · Firestore 511/508/4 (all 1,016 historical documents unchanged)
Build-input changes: Dockerfile +23 B; requirements-cloud.txt +15 B; requirements-cloud.lock +15 B; scripts/release_cloud.py +623 B; scripts/measure_cloud.py +513 B
Spend observed today: $0 posted (billing delayed; 10 observed image outputs have $0.336 output-only list price) · Daily cap: 60 UTC; 16 admissions observed
Not done / deferred: Track C activation; frozen smoke NOT RUN — required frozen reference path not on this machine (authorized B substitute passed). Original 510 total prompts became 511 through synthetic feedback. Earlier 6.81 s warm outlier retained.
```
