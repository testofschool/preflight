# Preflight — Track A deployment report

Snapshot: 2026-10-16 KST, before the G1 notice and Track B. **Track A is deployed. Overall acceptance is partial: V4 FAIL; V7 partial; V8 not run.**

Live app: **https://preflight-jcgro45veq-as.a.run.app** — the default Cloud Run `run.app` URL, with no login or custom domain. Private source repository: https://github.com/testofschool/preflight.

## Scope, authorization and gates

The attached handoff supplied the proposed work contract and expected results; its statements were not treated as evidence of credentials, observed results or billing readiness. The ZIP passed CRC/path checks, its handoff equals the standalone document, and all six originals remain preserved outside the repository. The public dataset bytes remain frozen and hash-checked before fitting or evaluation.

The owner subsequently filled section 0 directly, supplied the authorized project and private repository, confirmed runtime key setup and GCP billing linkage, selected Singapore first, and authorized continuation without another G0 question. Dedicated app resources were created; legacy Gemini 2.5 / Agent Platform resources were not repurposed. No project identifier or credential value is committed. The first API-key model request returned HTTP 402 for depleted prepaid credit. Production then explicitly selected Vertex AI with GCP Application Default Credentials and linked billing, as disclosed during execution; it does not silently alternate credential backends, and the AI Studio cap was not raised. The runtime key was transferred through stdin to Secret Manager, never printed, and is not injected into the production Vertex container.

**G1:** share the URL and stop for the owner's next message or two hours from that notice, then continue Track B. The owner can forward the link to SIDHANT; no teammate message was sent by the executor. **G2 remains closed:** Veo billing is unconfirmed; total Veo calls **0**. Track B will use the supplied individual owner MP4 shots, excluding the edited compilation.

## V1–V10 acceptance ledger

| ID | Result | Actual number and native evidence |
| --- | --- | --- |
| V1 | PASS within supplied overlap test | **0** files sharing an exact 20-token shingle with the reference; Python lexical tokens and other UTF-8 whitespace tokens, with four binary artifacts excluded. [Receipt](reports/freshness-final.json). This is not proof of authorship or creation date. |
| V2 | PASS within marker/exact-value scan scope | **0** forbidden-marker hits in repository/README/logs and staged blobs; exact current key and actual project identifiers also absent. Captured native Cloud Run text logs: **0** marker hits after identifier redaction. [Guard receipt](reports/secrets-final.json), [cloud log receipt](reports/cloud_log_scan.json). |
| V3 | PASS | Cold **12.598004s**; five warm requests **4.647478, 4.363051, 4.714395, 5.209227, 5.097970s**; all HTTP 200 with genuine tools and verified sessions. [Timed curl receipt](reports/cloud_latency.json), [stdout](logs/cloud_latency.txt). |
| V4 | **FAIL; exact 0.72 UNVERIFIABLE** | Five-seed held-out both-bad vote AUC **0.668329 < 0.68**. Cold-start IRT **0.714796 ≥ 0.696622** baseline; strict train-only TF-IDF **0.715403**. The composite fails its first condition. [Final evaluation](artifacts/evaluation.json), [stdout](logs/evaluation.txt). |
| V5 | PASS | **10/10** hardest fitted items yielded strictly lower estimated risk (required ≥6); **0** higher-risk returns, **10** HTTP attempts, **0** retries. [Full safe responses](reports/rewrites_live.json), [stdout](logs/rewrites_live.txt). No generated-video quality improvement is established. |
| V6 | PASS | **6 completed ADK tool calls on every one of the 10 V5 requests**; genuine Gemini-emitted function calls, Agent Platform managed-session readback verified. One trace below. Same-session continuation separately passed native/browser checks. |
| V7 | PARTIAL | Native Firestore counts: **508 prompts / 508 items / 0 verdicts**. All **1,016** historical documents and **10** model abilities match local exports, **0** differences. Verdict population waits for real Track B output. [Import stdout](logs/firestore_import.txt), [content integrity](reports/firestore_integrity.json). |
| V8 | NOT RUN | **0/3** owner clips inspected. Track B has not started before G1. Available clips are not claimed as known-defect validation. |
| V9 | PASS | README has architecture diagram, source/licence, limits, five samples, cannot-do statement and Agent Platform Sessions named. [Header stdout](logs/readme_headers.txt). |
| V10 | PASS | Current native config: **asia-southeast1, min 0, timeout 36s, default concurrency 80**, revision `preflight-00003-7k9`. [Configuration](reports/cloud_run.json), [stdout](logs/cloud_run_config.txt). |

The app can be reviewed and used despite the failed statistical acceptance criterion. This report does not round partial acceptance up to completion.

## Commands and stdout

Run from the repository with the sibling `.preflight-cloud-venv` Python 3.12 environment. Runtime project/service configuration is supplied through the environment or captured gcloud output, never literal identifiers in saved command lines. Source the owner's shell configuration silently before the first credentialed call; never print the environment or key.

| Check | Executed command / method | Recorded stdout |
| --- | --- | --- |
| V1 | `python scripts/check_freshness.py --reference ../evidence/preflight-20261016/inputs/pregen_irt.py` | [freshness-final.txt](logs/freshness-final.txt) |
| V2 | `python scripts/check_secrets.py --include-index` plus exact-value byte scan and captured native log scan | [secrets-final.txt](logs/secrets-final.txt), [cloud log receipt](reports/cloud_log_scan.json) |
| V3 + V10 | `python scripts/measure_cloud.py --url https://preflight-jcgro45veq-as.a.run.app` | [cloud_latency.txt](logs/cloud_latency.txt) |
| V4 | `python scripts/evaluate.py` on frozen bytes | [evaluation.txt](logs/evaluation.txt) |
| V5 + V6 | `python scripts/verify_rewrites.py --url https://preflight-jcgro45veq-as.a.run.app` | [rewrites_live.txt](logs/rewrites_live.txt) |
| V7 | `python scripts/import_firestore.py`; `python scripts/verify_store_live.py` | [import](logs/firestore_import.txt), [integrity](logs/firestore_integrity.txt) |
| V8 | Not run | No fabricated command or stdout |
| V9 | `rg '^#' README.md` | [readme_headers.txt](logs/readme_headers.txt) |
| V10 | `gcloud run services describe preflight --region asia-southeast1 --format=json`, selecting safe fields before writing | [cloud_run_config.txt](logs/cloud_run_config.txt) |
| Unit/integration | `python -m pytest -q tests` | **50 passed, 2 warnings, 5 subtests passed**; [tests_cloud.txt](logs/tests_cloud.txt) |
| Browser | Actual desktop/mobile UI, exactly two live POSTs, instrumented copy write | [browser_cloud_qa.json](reports/browser_cloud_qa.json), [stdout](logs/browser_cloud_qa.txt) |

[commands.json](reports/commands.json) also preserves the historical G0 execution entries. These commands report the completed runs; do not rerun paid checks merely to read their stdout. The ten-request verifier refuses to overwrite existing receipts. The pytest warnings concern Starlette's HTTPX deprecation and an ADK experimental function-schema feature; neither failed the checks. Fake clients in unit tests are separate from native cloud acceptance receipts.

### Native latency and timeout derivation

The cold measurement deployed a new revision with minimum instances zero and deployment health checking disabled, then made its first invocation before any UI/GET access. The [gcloud deploy documentation](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy) states this mode starts the instance on first invocation. Calibration's slowest sample, including cold startup, was **17.707208s**; the integer timeout was set to `ceil(2 × 17.707208) = 36s`. A new revision at that timeout produced the final V3 results above. No time limit or threshold was relaxed after observing results.

### V5 per-prompt stdout summary

Items were selected before requests, by descending difficulty in the frozen engine artifact, with stable artifact-order ties. Every response had six completed tools and a readback-verified managed session. Exactly ten requests were made, without retries.

| Rank | Prompt | Before | After | Tools / session |
| --- | --- | --- | --- | --- |
| 1 | A person is wrestling | 0.500000 | 0.098529 | 6 / verified |
| 2 | a spoon and a laptop | 0.534545 | 0.340000 | 6 / verified |
| 3 | A person is shooting basketball | 0.300000 | 0.063529 | 6 / verified |
| 4 | a cat and a dog | 0.306667 | 0.097143 | 6 / verified |
| 5 | A person is hugging | 0.500000 | 0.000000 | 6 / verified |
| 6 | an orange bird | 0.340000 | 0.297143 | 6 / verified |
| 7 | A person is squat | 0.500000 | 0.383333 | 6 / verified |
| 8 | A person is shaking head | 0.500000 | 0.440000 | 6 / verified |
| 9 | a tv and a laptop | 0.534545 | 0.090000 | 6 / verified |
| 10 | a bicycle and a car | 0.433333 | 0.224242 | 6 / verified |

One actual trace: `nearest_prompts → difficulty(original=0.500000) → rewrite → difficulty(candidate1=0.290909) → difficulty(candidate2=0.232143) → difficulty(candidate3=0.098529)`. Three Gemini planner calls emit the real signed function calls; one additional Gemini call generates candidates. The strict reduction guard chooses only an approved candidate. The purple-clock browser request independently exercised the unchanged-risk path, which correctly hid the alternative and copy control. Opaque session IDs in native API receipts are resource IDs, not credentials; authentication cookies and headers were not retained.

## Statistical reproduction and limits

The supplied data reproduces **1,911 votes, 508 prompts, 10 models, 2,080 observed cells**, and **407/1,911 = 21.29775%** both-bad votes. The latter is a human pairwise rejection share, not evidence that one fifth of current generations wastes money. Outcome coding is win1/loss0/tie0.5/both-bad0, aggregated by prompt/model. Unsupported vocabulary abstains instead of returning invented numerical risk.

The fresh implementation uses sorted reference ordering, matching split/initialization seeds and L2 coefficients, analytic gradients and discrimination bounded to [0.3,4]. The reference clips discrimination inside an unconstrained optimizer; byte-identical fit parameters are not claimed. All **11/11** fitted optimizations reported convergence; the full fit's projected gradient was approximately **0.001218**, with termination by relative objective reduction.

The reference fits TF-IDF on all prompt text; this transductive path is labelled separately from the strict train-only path. The supplied preregistration and result payload do not define or contain the handoff's 0.72 both-bad AUC claim. The declared diagnostic here labels each held-out human vote both-bad/not-both-bad and assigns its prompt the mean training-neighbour rate, using five fixed 20% prompt holdouts. Its mean is **0.668329**; the separate any-both-bad-prompt diagnostic is **0.630676**. Targets, seeds and thresholds were not changed to rescue a failing result.

Other preregistered findings remain visible: Q1 IRT **0.642161** vs baseline **0.714971**, FAIL; Q3 model-routing share **0**; Q4 observed outcome **0.573003** for both choices, difference **0**, FAIL. Positive discrimination fixes model ordering. No routing, current-Veo calibration, measured savings, novelty literature priority, or generated-video quality claim follows from these results. Historical `initial_diagnostic` artifacts retain the superseded pre-audit settings; canonical final outputs are `artifacts/evaluation.json` and `logs/evaluation.txt`.

## Delivered and not done, per track

**Track A delivered:** fresh data/IRT/retrieval code; frozen source verification; Firestore import with canonical-content comparison; real `/preflight` predictions; Gemini through Vertex AI; Google ADK 2.12 multi-step tool execution; Agent Platform Sessions create/read/reuse; strict rewrite guard; responsive English interface and architecture screen; illustrative price formula; no login; Cloud Run deployment; native latency, rewrite, session and browser receipts; private source packaging. Cloud Build completed successfully with its input hash recorded in [cloud_build.json](reports/cloud_build.json).

**Track A not achieved:** the risk-AUC criterion V4 fails. Predictions are historical retrieval estimates, not calibrated current-model failure probabilities. No prospective generated-video experiment establishes rewrite quality. Actual invoice cost is unmeasured; illustrative Veo budgets exclude Gemini, hosting, tax and discounts.

**Track B not started:** the G1 notice/reply-or-two-hour interval comes first. No clip has been inspected, no video defect/timecode accuracy is claimed, no verdict document exists, and no updated-risk UI flow has shipped. The store contains an idempotent feedback transaction for later use, with tests only; this is not an executed feedback loop. Machine single-clip verdicts must remain separately labelled from human pairwise both-bad votes rather than rewriting historical evidence. Veo generation is prohibited while G2 holds and no `/generate` endpoint exists.

## Files, sizes and build-input changes

[FILE_INVENTORY.json](reports/FILE_INVENTORY.json) is the full file-level deliverable list, with byte sizes and SHA-256 for every repository file except generated caches and Git metadata. Its own hash is null to avoid recursion; its byte size is included. The [external evidence inventory](../evidence/preflight-20261016/FILES.json) covers preserved inputs, intake/guard receipts and desktop/mobile screenshots. Runtime virtual environments are installed siblings, not repository deliverables. The original G0 report/ledger remain explicitly historical at [g0_completion_report.md](reports/g0_completion_report.md) and [g0_acceptance.json](reports/g0_acceptance.json).

Build inputs created or changed, file by file:

| File | Change / reason |
| --- | --- |
| `requirements.txt` | Fresh direct requirements; FastAPI changed from 0.119.1 to **0.133.0** to resolve cloud ADK/telemetry constraints. A rejected 0.143.2 dependency attempt was not deployed. |
| `requirements-cloud.txt` | Adds pinned **google-adk[gcp]2.12.0**, **google-cloud-firestore2.34.1**, **google-genai2.31.0**. |
| `requirements-cloud.lock` | Exact resolved production dependency snapshot; dependency consistency check passed. Used by Docker. |
| `requirements.lock` | Retained 33-package historical G0/local environment, not the production lock. |
| `requirements-dev.txt` | Local test dependencies; cloud tests used pytest9.0.3 in the separate cloud venv. |
| `Dockerfile` | New Python3.12 slim container pinned to `sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`; production lock, bundled engine artifacts, nonroot UID10001, uvicorn with access logging disabled. |
| `cloudbuild.yaml` | New reproducible Docker build with runtime image substitution and dedicated build service account. |
| `.dockerignore` | Excludes Git, caches, tests, evidence and unused artifacts from image context. |
| `.gcloudignore` | Restricts Cloud Build uploads to runtime build inputs; source data/evidence are not uploaded. |
| `app.py`, `cloud/*.py` | Cloud startup/readiness, Firestore-backed predictions, shared rolling/cumulative limits, signed Gemini/ADK tool workflow and managed-session persistence; no synthetic fallback. |
| `preflight_core/*.py`, `scripts/build_data.py` | Fresh bounded IRT/retrieval/provenance implementation; frozen-data mismatch stops before writes. |
| `data/genai_video_test.parquet` | Supplied frozen bytes, SHA-256 `c58ba145070415d084950fe8a80c517fd14e05d3285e371338a66791cee5de94`. |
| `artifacts/engine.json`, `vectorizer.joblib`, `prompt_vectors.npz` | Fresh generated fit/retrieval inputs copied into the runtime image. |
| `static/*.html`, `static/*.js`, `static/styles.css` | English interface with actual connection flags, anonymous session continuity and strict candidate/copy guard. |
| `scripts/cloud_ops.py`, `release_cloud.py`, `measure_cloud.py` | Dedicated-resource provisioning, identifier-safe build/deploy and native timeout calibration; configuration remains runtime-only. |

The build input digest and the current runtime-source digest match. Documentation/receipt additions do not change the deployed runtime image. Request admission is shared across instances: at most20 checks per rolling minute and at most1,000 cumulative admitted checks; it can count requests whose later external step fails. Minimum instances0 reduces idle compute but does not make all cloud resources free.

## Factual three-sentence submission description

Preflight runs on Google Cloud Run and retrieves historical prompt outcomes and IRT item parameters from Cloud Firestore, the document database shared with Firebase. A Google ADK 2.12 agent uses Gemini 3.5 Flash through Vertex AI to propose rewrites and calls the difficulty tools to reject candidates whose historical risk score does not fall. Agent Platform Sessions persists anonymous conversation history across checks; video generation and postcheck are not enabled in this Track A build.
