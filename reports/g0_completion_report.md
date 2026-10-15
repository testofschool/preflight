> Historical G0 snapshot. Superseded by the root COMPLETION_REPORT.md after direct user setup.

# Preflight — G0 completion report

Date: 2026-10-16 KST. **Overall submission: HOLD. G0 local work: completed.**

Local preview: **http://127.0.0.1:8080**. There is **no live Cloud Run URL**, and this localhost address is not a `run.app` URL.

## Scope and gates

The request was `/goal proceed` with two named handoff files. The handoff was treated as the proposed work contract, not as evidence that credentials, spend permission, cloud services or external results already existed. The ZIP passed CRC and path checks; its handoff and the standalone document are byte-identical. All six source attachments were preserved outside the new repository. See [intake receipt](../evidence/preflight-20261016/intake.json).

Section 0 has no GCP project ID, no completed billing/key fields, no owner-clip path and no private repository URL. The current executor environment had no Gemini key. G0 therefore limits this run to local ingest, fit, prediction, UI and V1/V2/V4 checks. No credentials were recovered from other locations. G1 was not reached; G2 was not opened. No video generation calls or third-party messages were sent.

## V1–V10

| ID | Result | Actual number / evidence |
| --- | --- | --- |
| V1 | PASS, limited to supplied overlap criterion | **0** files with an identical 20-token shingle against the attached reference. Python uses lexical tokens; other UTF-8 text uses whitespace tokens. Four binary data/model artifacts are explicitly outside token comparison. This does not prove creation date or authorship. |
| V2 | PASS, supplied marker scan | **0** forbidden-marker hits. Raw-byte scan includes README, logs and binaries; the final Git hook also scans staged blobs. Arbitrary unknown secrets or project identifiers cannot be ruled out by a finite marker list. |
| V3 | NOT RUN on Cloud Run | **0/5 cloud samples measured**; no URL. The five real local curl requests all returned HTTP 200 in **0.002–0.005s**. Local startup/first-request timings are saved separately and do not count as cloud cold-start evidence. |
| V4 | **FAIL on declared metric; exact 0.72 claim UNVERIFIABLE** | Five-seed mean both-bad vote AUC **0.668329 < 0.68**. Cold-start IRT AUC **0.714796 ≥ 0.696622** baseline; strict train-only TF-IDF IRT **0.715403**. The first condition fails, so the composite does not pass. |
| V5 | NOT RUN | **0/10** Gemini rewrites tested. No rewrite agent is active under G0. |
| V6 | NOT RUN | **0** ADK/Gemini tool calls; Agent Platform Session service inactive. No agent trace is fabricated. |
| V7 | NOT RUN remotely | Firestore collection counts **UNMEASURED**. Local exports contain **508 prompts and 508 items**; there is no fabricated verdict collection. Local files are not remote population evidence. |
| V8 | NOT RUN | **0/3** owner clips evaluated; no clip path supplied, Track B not started. |
| V9 | PASS for documentation | README includes architecture, data source/licence, limits, five samples and the cannot-do line. Its cloud path is explicitly future work. |
| V10 | NOT RUN | No Cloud Run service/configuration query was made. Min instances, deployed timeout and actual deployment region are **UNMEASURED**. |

## Commands and stdout

Run from this repository. The tested virtual environment is its sibling `.preflight-venv`; a portable setup is documented in README.

```sh
../.preflight-venv/bin/python scripts/verify_local.py --reference ../evidence/preflight-20261016/inputs/pregen_irt.py
../.preflight-venv/bin/python scripts/preview_local.py
../.preflight-venv/bin/python scripts/check_secrets.py --include-index
```

The preview command starts its own local server and refuses to replace an existing listener. [Command receipts](reports/commands.json) retain the exact executable paths and exit codes. Full stdout: [build](logs/build.txt), [evaluation](logs/evaluation.txt), [30 tests](logs/tests.txt), [freshness](logs/freshness.txt), [secret scan](logs/secrets.txt), [local timed curl](logs/local_latency.txt). Final browser receipts are in [browser QA](reports/browser_qa.json). The [final full-tree and staged-blob guard receipt](../evidence/preflight-20261016/final_guards.json) includes the generated inventory and reports.

All 30 tests passed. This includes changed-input rejection by both the build and evaluation commands, before any output is changed. One third-party deprecation warning concerns the AnyIO BlockingPortal alias in Starlette's test client. It did not fail the checks. All 11 recorded IRT fits returned optimizer convergence; the full-fit projected gradient was approximately **0.001218**, with convergence by relative objective reduction. Raw gradient is not zero at active discrimination bounds.

Evaluation stdout:

```text
seed  Q1_IRT  Q1_B1  Q2_IRT_transductive  Q2_IRT_strict  Q2_B1  risk_vote_AUC_strict  length_AUC
0  0.647171  0.729580  0.701495  0.701311  0.674508  0.705971  0.472321
1  0.631960  0.703950  0.725478  0.718499  0.689307  0.707779  0.545356
2  0.645276  0.714930  0.720598  0.723247  0.686368  0.700754  0.534386
3  0.639401  0.720487  0.695059  0.697790  0.691383  0.611137  0.554600
4  0.646995  0.705910  0.731351  0.736167  0.741543  0.616004  0.535079
```

Additional preregistered results: Q1 IRT **0.642161** versus baseline **0.714971**, FAIL. Q3 share with a different best model **0.000000**. Source-compatible Q4 actual outcome **0.573003** for both choices, difference **0.000000**, FAIL. The paired-observed-outcome extension also has difference zero. This run provides no model-routing or measured savings claim.

## What was reproduced, and what was not

The supplied parquet hash, 1,911 votes, 508 prompts, 10 models and 2,080 observed cells were reproduced. Both-bad votes are **407/1,911 = 21.29775%**. Cell coding and the reference's sorted ordering, split seeds, initialization and penalty coefficients were audited independently before the final run.

The reference's TF-IDF is fitted on all prompt text, including held-out text. The report labels that path transductive and separately reports training-only TF-IDF on the same holdouts. The fresh implementation uses direct discrimination bounds and an analytic likelihood gradient; the reference clips discrimination inside an unconstrained optimizer. These methods need not produce byte-identical parameters or identical AUCs.

The claimed both-bad AUC 0.72 is absent from both the supplied preregistration and result payload, and its binary target/aggregation is unspecified. The natural declared diagnostic here scores each held-out human vote as both-bad or not, with all votes from one held-out prompt receiving that prompt's training-neighbour risk score. Prompt holdouts, seeds and metric definitions are retained without threshold selection. Its mean AUC is **0.668329**; a separate predeclared any-both-bad-prompt diagnostic is **0.630676**. Neither is silently substituted to claim replication.

Initial diagnostic outputs remain under filenames containing `initial_diagnostic` or `initial_stdout`. They used different initial method settings and were superseded after the independent reference audit; final results are `artifacts/evaluation.json` and `logs/evaluation.txt`.

## Delivered by track

**Track A, local G0:** new source code, verified public data, bounded 2PL fit, persisted vectorizer/model artifacts, local prompt/item exports, real prediction endpoint, responsive English UI, illustrative price formula, source/licence documentation, credential hook and reproducible verification commands. Unsupported vocabulary receives no numerical risk or budget.

**Track A, pending:** Firestore import, Gemini/ADK multi-step rewrite and self-check, actual Agent Platform Session service, Cloud Run deployment, cloud latency, rewrite success measurement, distributed request limits and a live repository. These are its own G0 dependencies, independent of Track B.

**Track B, pending:** owner clips, Gemini video inspection, flicker frame extraction, defect/timecode evaluation, durable verdict feedback, and optional Veo generation. No Track B code or synthetic success receipts were added under G0.

## Files and build inputs

The new repository is `preflight/`. [FILE_INVENTORY.json](reports/FILE_INVENTORY.json) lists every deliverable file with its byte size and SHA-256; generated caches and Git metadata are excluded. Each inventory records its own size but omits its own hash to avoid recursion. The [external evidence inventory](../evidence/preflight-20261016/FILES.json) covers preserved inputs, intake receipts, final screenshots and final guard output. Runtime dependencies were installed into the separate local virtual environment.

Build inputs created file by file:

- `requirements.txt`: nine pinned direct runtime dependencies.
- `requirements-dev.txt`: runtime requirements plus pinned pytest and HTTPX.
- `requirements.lock`: the exact resolved 33-package environment from the tested isolated venv.
- `data/genai_video_test.parquet`: unchanged supplied bytes, hash enforced by the build script.
- `scripts/build_data.py` and model artifacts: fresh local preprocessing/fit and serialized outputs, with fit settings and source manifest.
- `preflight_core/provenance.py`: enforces the frozen source hash for both build and evaluation, and parses the same checked bytes. A mismatch stops before fitting or writing artifacts.

No Dockerfile or container base was created or changed. No cloud SDK/configuration or remote Git repository was modified. Git was initialized locally and its credential hook configured; no remote push occurred.

## Factual three-sentence status text

Preflight currently runs a local statistical prompt check using public GenAI-Bench votes. Cloud Run, Gemini and Agent Platform Session service have not been connected in this G0 build. Prompt and item records are exported locally for future Firestore use; Firebase/Firestore has not been populated and no live submission URL exists.

These sentences describe current evidence. A completed-cloud submission description cannot yet be written truthfully.

## Continuation inputs

G0 remains open until the user supplies the GCP project ID, confirms runtime Gemini key availability without pasting a key, states Veo billing status, and supplies owner MP4 paths plus an empty private repository URL. The handoff's requested region/fallback remains a configuration requirement, not an observed deployment. No additional product decision is needed to continue the requested cloud track once these inputs exist. V4's failed risk metric will remain visible; resolving credentials does not turn it into a PASS.
