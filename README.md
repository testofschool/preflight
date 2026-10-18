# Preflight — check an AI-video prompt before you pay to generate it.

[Live prototype](https://preflight-jcgro45veq-as.a.run.app) · Demo video: `https://youtu.be/1A8I-9NZ3Kc` · [Pitch deck PDF](docs/Preflight_pitch_deck.pdf).

Public source: https://github.com/testofschool/preflight. Demo duration: 3:28. The demonstrated spoon/laptop risk estimate changes from 46.8% → 15.8%; this is not measured video-quality improvement.

## The problem, in users' words

> “you still burn credits on the failed attempt”
>
> — [Ed McDowell, Runway review on Trustpilot, September 2026](https://www.trustpilot.com/reviews/6a9f952dc2a80e997c67354a)

> “I recommend a lo-res preview render before having to spend actual credits”
>
> — [David306816550282, Adobe Community](https://community.adobe.com/questions-404/wasted-generative-credits-on-bad-results-1479378)

> “Credits are only automatically returned when a generation ends in a generation error.”
>
> — [Runway Help: Can I have credits refunded?](https://help.runwayml.com/hc/en-us/articles/34266159290003-Can-I-have-credits-refunded)

These are individual user reports and a provider policy, not measured savings from Preflight.

## What Preflight does

Historical risk (free to try) → reason → rewrite kept only if estimated risk drops → saved sample still → clip review as a second pair of eyes.

Paste a prompt to see a historical risk signal and five nearby prompts from 1,911 human pairwise votes in GenAI-Bench. Gemini proposes a rewrite; Preflight presents it only when its estimated risk is strictly lower. Upload a clip you already have for a separate Gemini review with inspectable timecodes. Original human votes stay separate from machine feedback.

Image preview — Active for sample prompts (saved stills); live generation limited

The five sample prompts use saved rewrite decisions, visibly labeled “Sample rewrite (saved)”, so their stills can be reused without model calls. Four saved decisions contain lower-risk rewrites. “Indoor gymnasium” keeps the original because no lower-risk rewrite passed; its saved-sample preview explicitly says “unchanged”. A saved still displays its generation date and “0 model calls · $0.00”. Typed prompts retain the live Gemini rewrite. On an uncached still, the samples-only mode explains: “Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works.” A still comes from an image model and cannot judge motion, flicker or timing. All three preregistered live-image probes fell below the 19/20 reliability gate: P1 returned 8/20 valid images, P2 6/20 and P3 6/20. Live generation remains limited. [v4 results](reports/preview_v4/REPORT.md). The [v3 report](reports/preview_v3/REPORT.md) retains the previous reliability failure; earlier dated measurements remain separate.

## Google Cloud services

| Service | Role | Status |
| --- | --- | --- |
| Cloud Run | Hosts FastAPI and the English browser interface in `asia-southeast1` | live |
| Cloud Firestore | Stores historical vote aggregates, fitted item parameters, separate machine feedback and cached preview images | live |
| Vertex AI Gemini 3.5 Flash | Proposes prompt rewrites through Application Default Credentials | live |
| Google ADK 2.12 | Runs the tool workflow and checks rewrite candidates against the risk estimate | live |
| Agent Platform Sessions | Persists anonymous rewrite-session history | live |
| Gemini video understanding | Reviews uploaded clips and sampled frames with timecodes | live |
| Gemini image models + Firestore cache | Saved original/rewrite stills for the five sample prompts | active for sample prompts; live generation limited |
| Secret Manager | Holds a key from an earlier API-key setup; production requests use Vertex ADC instead | not used by live requests |

**Not used:** Veo (0 calls), Agent Engine runtime hosting, BigQuery. Managed Agent Platform Sessions is used for sessions; the agent itself runs in the Cloud Run application. [Runtime status receipt](reports/track_cd_primary_status.json), [implementation and deployment receipts](COMPLETION_REPORT.md).

## Architecture

```text
Browser
  |
  v
Cloud Run / FastAPI
  |-- Firestore: history, item parameters, feedback
  |-- Google ADK rewrite agent
  |     |-- Vertex AI: Gemini 3.5 Flash
  |     |-- Agent Platform Sessions
  |     `-- Keep only a lower estimated-risk rewrite
  |-- Gemini video understanding: uploaded clip
  `-- Firestore: saved sample stills (live generation limited)
```

The [live architecture page](https://preflight-jcgro45veq-as.a.run.app/architecture) reads current service flags from `/api/status`.

## What it can't do (measured)

- The held-out risk AUC is **0.67** (five-seed mean 0.668329, below the 0.68 target). This is a historical signal, not a calibrated probability for today's video models. [Evaluation](artifacts/evaluation.json).
- Clip-review accuracy is **unmeasured**. No confirmed-defect reference set was established; a working review endpoint and a machine verdict do not establish accuracy. [Reference limits](COMPLETION_REPORT.md).
- Retrieval covers the dataset's **English vocabulary only**. No vocabulary overlap produces unavailable risk rather than an invented score. [Predictor](preflight_core/engine.py).
- The preview uses **saved sample stills**. All three live-image probes failed the 19/20 reliability gate (8/20, 6/20 and 6/20), so live generation remains limited. A still cannot establish video quality. [Current gates](reports/preview_v4/REPORT.md). Earlier provider measurements describe their dated runs: [2026-10-17 receipts](reports/preview_live.json), [v3 gate failure](reports/preview_v3/REPORT.md).
- A lower rewrite estimate does not establish better generated-video quality, money saved, or current-model routing performance. Machine feedback can make the displayed risk a mixed, unvalidated heuristic proxy.

## Try it in 30 seconds

Open the [live prototype](https://preflight-jcgro45veq-as.a.run.app), choose a sample chip, and press **Check this prompt**. First request after idle may take about 20 seconds because minimum instances is zero.

| Sample chip | Expected historical-only risk range |
| --- | --- |
| a cat and a dog | 25–35% |
| a spoon and a laptop | 45–60% |
| a bicycle and a car | 35–50% |
| indoor gymnasium | 0–15% |
| a purple clock | 0–15% |

These ranges describe the frozen historical predictor (recorded values: 30.7%, 53.5%, 43.3%, 6.5%, 5.7%). The displayed mixed proxy can change with separately counted machine feedback; a rewrite can safely abstain. [Sample receipt](reports/local_latency.json).

**Max 20 checks/min shared** across the service, with a cumulative allowance currently configured to 3,000 admitted checks. No video generation is requested. For clip review, upload an MP4 you already have (up to 30 MiB and 30 seconds) and enter what should happen.

## Run the local fallback

Use Python 3.12 for parity with the cloud container. The historical local G0 receipts used Python 3.10.11 on macOS ARM64; those receipts do not establish the current cloud environment.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8080 --no-access-log
```

Open [the local app](http://127.0.0.1:8080). The default local mode makes no external model calls. Bundled artifacts load at startup; missing artifacts fail startup rather than silently substituting sample results. The interface calls the real local predictor and labels Gemini rewriting unavailable in local mode.

The cloud dependency set is recorded separately in `requirements-cloud.txt` and `requirements-cloud.lock`: Google ADK 2.12.0 and FastAPI 0.133.0 are pinned. `Dockerfile` uses Python 3.12 slim pinned by SHA-256 digest and runs as an unprivileged user. Installing dependencies or building that image does not constitute a cloud deployment.

## Deploy

Deployment requires the owner's configured Google Cloud project, authenticated `gcloud`, Vertex ADC, the dedicated Firestore database and a managed-session resource. Keep project identifiers and credentials in runtime configuration.

```sh
python scripts/check_secrets.py --include-index
python scripts/release_cloud.py --candidate
```

The candidate is created without primary traffic. Validate its real `/preflight`, cached sample stills and upload-review responses before promotion; a failed risk-check battery or saved-sample UI gate must not be promoted. The build script records the runtime input digest in `reports/cloud_build.json`. Live preview generation defaults to limited; enabling it requires the recorded probe and UI gates. [Release script](scripts/release_cloud.py), [release evidence](COMPLETION_REPORT.md).

## Tests

```sh
python -m pip install -r requirements-cloud.lock -r requirements-dev.txt
python -m pytest -q
python scripts/check_secrets.py --include-index
```

The 2026-10-17 local regression passed **99 tests, 0 failed**, including nine preview tests; those tests use fakes and do not establish provider reliability. Genuine cloud, image and clip-review receipts are recorded separately. [Current test receipt](reports/submission_closeout/tests.json), [retained test output](reports/track_cd_tests.txt), [preview tests](tests/test_preview.py).

## Release evidence and technical details

The 2026-10-17 native audit verified live revision `preflight-00016-tuk`, with preview disabled and upload review enabled. Its recovered build inputs match runtime digest `f080be0c815cbe460b0036b0a6a597201d6460dece9c73c8049af66f54a05d7c`. Current native verification is recorded separately from the older measurements below. [Completion report](COMPLETION_REPORT.md), [disabled-preview receipt](reports/track_cd_primary_status.json).

The latest live replay returned **6/6 HTTP 200** responses. One warm request took **9.716 seconds**, above the six-second target; the latency condition failed. No deployment or retry followed that result. [Current live checks](reports/submission_closeout/live_battery_gate.json).

The following sections retain the original technical documentation, including historical receipts and their numerical limitations. Counts, timings and revision names in dated receipts describe those measurements. They are not fresh measurements of the current revision.

## Historical component evidence (2026-10-16)

These retained receipts describe earlier revisions, not the current live revision. Observed on 2026-10-16:

| Component | Observed result | Limit |
| --- | --- | --- |
| Firestore | Storage check PASS: `preflight-aibc` in `asia-southeast1` contains 510 prompt documents (508 historical plus two feedback-only), 508 item documents, and two real verdicts; all 1,016 historical documents match the retained integrity comparison with zero differences | Machine feedback is separate from the original human pairwise counts; a new feedback-only prompt has no fitted item |
| Agent Platform Sessions | Genuine managed-session create/read health check passed | Minimum supported TTL is 24 hours; this does not prove the full rewrite workflow |
| Vertex Gemini | Gemini 3.5 Flash runs through Vertex Application Default Credentials in Singapore; real ADK requests succeeded | Statistical improvement does not establish generated-video quality |
| ADK workflow | Rewrite check PASS: 9/10 strict improvements, above the required 6/10; cat/dog returned `no_safe_rewrite`; zero higher-risk returns. Tool/session check verified six tools and genuine managed sessions for all ten cases, with ten attempts and zero retries | A lower proxy score does not establish generated-video quality or better future predictions |
| Cloud Run | Historical primary revision `preflight-00008-g92` served both workflows. The historical cloud-latency release-validation report passed: one cold request and five warm sample requests all returned HTTP 200 with six tools and verified sessions | Measured cold 19.738130s; warm 4.862889, 4.586187, 4.378278, 4.620390 and 4.329699s. The report records validation revision `preflight-00006-d4s`; final configuration is reported separately below |
| Clip review | Feature-baseline optimized revision seven completed a fresh cached02 review in 10.346132s with two model calls, flagging a machine-reported physics issue at 4.5s. The earlier cached01 native Pass took 18.950459s on the two-pass image; its stored-review checks took 0.937997s initially and 1.560978s on the primary | The cached02 flag is not independently confirmed. One fresh optimized measurement is not a latency guarantee or Clip-accuracy check evidence; see the clip-accuracy measurement limit below |

The separate AI Studio API-key planner attempt returned HTTP 402 because prepaid credit was depleted. Production explicitly selects Vertex ADC. It does not silently fall back between credential backends. No credential value or actual cloud project identifier belongs in this repository.

## Detailed measurement limits

The numerical limits below preserve the detailed evaluation record. Internal acceptance identifiers and their canonical statuses are kept in [COMPLETION_REPORT.md](COMPLETION_REPORT.md).

| Check | Status | Evidence and limits |
| --- | --- | --- |
| Risk evaluation | **FAIL; exact 0.72 UNVERIFIABLE** | Five-seed held-out vote both-bad AUC **0.668329 < 0.68**. Cold-start IRT **0.714796 ≥ 0.696622** baseline; strict train-only TF-IDF **0.715403**. The composite fails its first condition. [Evaluation](artifacts/evaluation.json), [stdout](logs/evaluation.txt). |
| Clip-accuracy check | **NOT RUN** | **0/3 known-defect clips** validated. One owner clip was inspected and reviewed as a negative control, with no independently confirmed intrinsic defect; it does not count toward Clip-accuracy check. All nine owner shots are resident and independently screened; **0** clips have a confirmed intrinsic defect in the sampled references. Accuracy is **UNVERIFIABLE** from these fixtures. [Availability](reports/owner_clip_availability.json), [frozen negative-control reference](reports/postcheck_canary_reference.json). |

## Detailed architecture and session handling

The deployed cloud path is verified by actual requests:

```text
Browser prompt
  -> Cloud Run primary service
     -> Google ADK agent
        |-- Gemini 3.5 Flash via Vertex ADC
        |-- Firestore: historical evidence and separate feedback
        |-- Managed Agent Platform Sessions
        `-- Strict estimated-risk reduction guard
            -> Risk and approved rewrite, or safe abstention

Browser: existing owner MP4 and its prompt
  -> Cloud Run primary service
     -> Bounded one-decode video and 2-fps frame preparation
        -> Gemini visual review
           -> Machine verdict and timecoded defects
              -> Firestore
                 -> Mixed heuristic risk; human history stays separate
```

The backend uses bundled lexical retrieval and reads the corresponding historical rates and item parameters from Firestore in cloud mode. The local fallback uses the bundled aggregates directly. The [architecture screen](static/architecture.html) reads `/api/status` and labels each connection from the actual runtime flags. It shows an active session badge only when managed-session readiness is confirmed.

The interface retains a returned opaque `session_id` in JavaScript memory and sends it on subsequent checks. Reloading clears that memory. The server maintains anonymous ownership using a random HttpOnly `pf_user` cookie; requests do not accept a public `user_id` field. No API credentials are sent by the browser.

## Runtime configuration

Supply configuration through the runtime environment or the deployment’s credential mechanism. The table lists variable names without secret assignments or real project identifiers.

| Variable | Purpose |
| --- | --- |
| `PREFLIGHT_MODE` | Select `cloud` for the connected workflow; `local-g0` keeps the local fallback |
| `PREFLIGHT_GEMINI_BACKEND` | Production explicitly selects `vertex`; there is no automatic backend fallback |
| `GOOGLE_CLOUD_PROJECT` | Runtime-only cloud project selection |
| `GOOGLE_CLOUD_LOCATION` | Managed-session region; current verified component region is `asia-southeast1` |
| `PREFLIGHT_GEMINI_LOCATION` | Optional explicit Vertex model region; otherwise uses the configured cloud location |
| `PREFLIGHT_GEMINI_MODEL` | Gemini model selection; current target is `gemini-3.5-flash` |
| `PREFLIGHT_SESSION_ENGINE_ID` | Runtime-only managed-session application resource |
| `PREFLIGHT_FIRESTORE_DATABASE` | Dedicated named database; current database is `preflight-aibc`; the default database is rejected |
| `PREFLIGHT_TOTAL_REQUEST_LIMIT` | Cumulative admitted-check allowance; default 1,000, maximum 3,000; production configured to 3,000 |
| `GEMINI_API_KEY` | Only for an explicitly selected API-key backend; unused by the production Vertex path |

Application Default Credentials are required for the production Vertex and Firestore path. Keep credentials and resource identifiers out of source, screenshots, command transcripts, and committed logs. The pre-commit guard scans worktree files and staged blobs for forbidden credential markers without printing values.

Historical primary revision `preflight-00008-g92` used region `asia-southeast1`, minimum instances zero, concurrency 80, and timeout 40 seconds. The [Cloud latency check release-validation report](reports/cloud_latency_postcheck_release.json) measured a 19.738130-second cold request and warm requests of 4.862889, 4.586187, 4.378278, 4.620390 and 4.329699 seconds. That report records validation revision `preflight-00006-d4s` and timeout 38 seconds; those timings were not remeasured on the copy-fix revision. The feature runtime is unchanged; see the [freeze follow-up](reports/freeze_followup/REPORT.md). Runtime configuration, cached request timing, local decode timing and uncached inference timing are separate evidence.

## Data source and licence

The unchanged supplied parquet comes from [TIGER-Lab/GenAI-Bench](https://huggingface.co/datasets/TIGER-Lab/GenAI-Bench), video generation **test** split, not the smaller filtered test_v1. Credit: Jiang et al., *GenAI Arena: An Open Evaluation Platform for Generative Models* (2024). The dataset card declares [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See [NOTICE.md](NOTICE.md) for attribution and derived-data changes.

The supplied file’s SHA-256 is `c58ba145070415d084950fe8a80c517fd14e05d3285e371338a66791cee5de94`; the build verifies this value. There are 1,911 human pairwise votes, 508 prompts, 10 models and 2,080 observed prompt/model cells. The 407 both-bad votes are 21.30% of votes. They do not establish the share of money wasted or the probability a single clip is usable.

Each left/right win contributes 1/0, loss 0/1, tie 0.5/0.5, and both-bad 0/0. A prompt/model cell is the mean of its observations; an unobserved cell remains missing. `prompts_v1.jsonl` and `items_v1.jsonl` preserve the derived outcomes and fitted item parameters used for the verified Firestore import. There is no fabricated verdict log.

## Methods and limits

The historical risk estimate is the **unweighted mean of five nearest prompt both-bad vote rates**, using word TF-IDF with 1–2 grams and cosine similarity. A query may include the exact historical prompt itself. Zero-similarity neighbours are disclosed. An input with no vocabulary overlap receives null risk, null budget and no IRT estimates. Lexical similarity is evidence coverage, not semantic understanding. If a response supplies additional risk semantics, the interface displays them and separately identifies the historical vote estimate when supplied.

The 2PL fit uses fractional cell outcomes and one likelihood contribution per observed cell. The audited reference objective adds squared ability with coefficient 1, squared difficulty with coefficient 0.1, and squared deviation of discrimination from one with coefficient 1. Positive discrimination is bounded to [0.3, 4]. The fresh solver uses direct bounds and an analytic gradient; the supplied reference used clipping inside an unconstrained solver. Fit settings and optimizer diagnostics are saved with the artifact. Cold-start difficulty and discrimination are the arithmetic mean over the same five text neighbours. Model scores are historical relative cell-response estimates, not calibrated usable-video probabilities.

Gemini proposes candidates; the statistical guard decides whether one may be presented. An `improved` status requires a strict decrease from `p_fail_before` to `p_fail_after`. The interface also checks this inequality before exposing the candidate or its copy control. Otherwise it shows no safe rewrite or an unavailable rewrite. A lower score does not establish better generated-video quality or better future predictions.

**Machine-feedback semantic limit:** the original human `both_bad_votes`, `vote_count` and `both_bad_rate` remain unchanged. Separate machine single-clip pass/fail counts can update `p_fail` as a mixed heuristic proxy; a machine failure on one clip is not a human judgment that both compared videos are bad. `historical_p_fail` preserves the human-only statistic. The mixed proxy is unvalidated and does not prove improved future prediction accuracy.

**Limits:** the evidence comes from 2024-era public votes. Preflight does not route between video models, validate current Veo performance, establish money saved, or inspect videos during a prompt check. Positive discrimination gives the same model ordering for every item. No novel published research result is claimed.

The supplied preregistration defines Q1–Q4 but no both-bad AUC target or evaluation. The supplied results file has a diagnostic prefix before its JSON and does not contain the claimed exact 0.72 both-bad AUC. Risk evaluation’s canonical status and numerical evidence are reproduced in Detailed measurement limits. Preregistered cell tests and declared both-bad diagnostics remain separate; thresholds and seeds are not changed to turn a failure into a pass.

## Cost assumptions

The illustrative scenario uses Veo 3.1 Standard, audio, 720p/1080p, eight seconds at USD 0.40/second, checked on 2026-10-16 against [Google’s Gemini API price page](https://ai.google.dev/gemini-api/docs/pricing#veo-3.1). One attempt is USD 3.20. The budget illustration is `3.20 × min(1 / (1 − p_fail), 5)`; a risk of one uses the cap. Prices can change.

This is a hypothetical budget, not a forecast or a measured saving. Treating either the historical both-bad rate or the mixed machine-feedback proxy as a current Veo failure probability is unvalidated. Gemini rewrite and clip-review requests, cloud hosting, taxes and discounts are excluded from the displayed video-generation budget. The local fallback incurs no generation fee; the connected workflow can incur Gemini and cloud charges. No Veo generation is called.

## Sample prompts

Paste any of these into the input, or use its sample buttons:

1. a cat and a dog
2. a spoon and a laptop
3. a bicycle and a car
4. indoor gymnasium
5. a purple clock

## Upload-only clip review

The clip-review workflow reviews a clip that the owner already has and is enabled on the primary public URL. Its [native canary receipt](reports/postcheck_canary_live.json) records one genuine review of resident cached01, followed by stored-review reuse. The historical [optimized smoke receipt](reports/postcheck_optimized_smoke.json) records a second fresh review, cached02, on revision `preflight-00008-g92`: 10.346132 seconds and two model calls. Stored review is reused without a new model call. The review control is enabled only when `/api/status` explicitly reports `postcheck` ready. It never requests a Veo generation.

Choose an MP4 video up to 30 MiB and 30 seconds, inspect it with the local preview controls, and enter its intended prompt. A preflight is not required: the clip has its own required prompt field, with an optional shortcut to reuse the prompt above. The optional model label defaults to `owner-upload` and is displayed as owner-provided information. The file is sent only when Review is pressed, using multipart `POST /postcheck` fields `video`, `prompt`, and `model`.

The result area separates the machine verdict and timecoded defects from historical human pairwise votes. Before/after values are a feedback-adjusted proxy; they do not mean the public historical both-bad vote rate changed. Null risk is shown as unavailable. A successful response can confirm that machine feedback was recorded; a reused stored review is labeled explicitly and does not claim a new review or feedback record. Errors and abstentions must not appear as a pass.

The requested review sampling rate is 2 fps, compared with the default video sampling rate of 1 fps. The interface uses the sampling rate actually reported in the response. Sampling may miss flicker shorter than 0.5 seconds at 2 fps; a pass does not establish that every frame is defect-free.

For cached01, the initial native review took 18.950459 seconds on the earlier two-pass preprocessing image. Its machine Pass changed the feedback-adjusted proxy from 21.6667% to 20.7639%; the human-only estimate stayed at 21.6667%. The initial cached request took 0.937997 seconds. The UI later showed Pass and explicit reuse, with risk unchanged at `0.20763888888888885` before and after reuse and one feedback record retained. Desktop and mobile had no overflow, page errors or console errors. The owner clip preview decoded successfully; two local blob-range failure events during loading are recorded in the browser receipt, with no API/static-resource failure. No defect timestamp was invented for this passing clip.

The recorded optimized image prepares video and frame evidence in one decode. Local preprocessing measured 5.154 seconds versus the earlier 10.215 seconds. **This is a local decode measurement, not a 5.154-second cloud review.** The fresh optimized cloud review measured 10.346132 seconds for cached02; latency on the remaining clips is still UNMEASURED.

Cached02’s fresh machine review flagged a physics issue at 4.5 seconds and changed the mixed proxy from `0.2909090909090909` to `0.32636363636363636`; its human-only estimate stayed at `0.2909090909090909`. This machine flag has not been independently confirmed and does not establish a known-defect positive. A separate [primary browser check](reports/browser_postcheck_flagged_qa.json) uploaded cached02 exactly once and reused the stored flag with zero new model calls. It displayed Flagged, the actual reason at `00:04`, and the separate historical 29.1% versus updated 32.6% values. Clicking the timecode sought to 4.5 seconds. Both desktop and mobile rendered without overflow or application errors; local aborted preview-range requests are recorded in the receipt. The original Pass receipt and frozen independent annotations remain unchanged.

Clip-accuracy check’s canonical status and evidence are reproduced in Detailed measurement limits. All nine owner shots were hydrated and cached by 2026-10-16 05:09:55 KST; they are available for local inspection. The earlier manual-unlock/download request is resolved as an access blocker, with no user action pending for clip access. Independent local reference annotation is complete, but it did not establish the required set of confirmed intrinsic defects. Cached01 remains a negative control with no confirmed defects. Clips08 and09 were independently frozen as no-confirmed-defect references after timestamped contact-sheet and targeted-frame inspection. A functional pipeline, machine Pass, or unconfirmed visual suspicion does not satisfy Clip-accuracy check defect-detection acceptance.

## Operational limits

Prompts are limited to 4,000 characters. Cloud mode uses a shared Firestore transaction to admit at most 20 checks per rolling minute across instances, with a cumulative allowance currently configured to 3,000 admitted checks. Admission can count a request even if a later external step fails. The local fallback retains a process-local 20-per-minute limiter. These are service-wide budgets, not per-user allowances.

Invalid input receives HTTP 422, exhausted budgets HTTP 429, and an unavailable connected service HTTP 503. Clip uploads are capped at 30 MiB to stay below Cloud Run’s HTTP/1 request limit; the server must also verify the 30-second duration limit. There is no login and no public video-generation endpoint. A shared budget is not an authentication system.

## Verification and continuation

See [COMPLETION_REPORT.md](COMPLETION_REPORT.md) for the acceptance ledger, commands, receipts, failures and pending checks. [`reports/`](reports/) contains machine-readable receipts and [`logs/`](logs/) contains redacted command output. Earlier local browser and latency receipts prove their recorded local scope only; they must not be relabeled as cloud evidence. Freshness checks compare against the external attachment and do not prove authorship or creation date.

The cloud-latency check passed in the [historical release-validation report](reports/cloud_latency_postcheck_release.json). The earlier [cloud browser receipt](reports/browser_cloud_qa.json) records spoon/laptop’s approved reduction from 53.5% to 36.7% and purple clock’s safe abstention at 5.7%, with managed-session reuse. It remains a scoped browser receipt rather than a fresh timing measurement of the final revision. The copy handler was checked using an instrumented clipboard write; the user’s clipboard was neither read nor overwritten.

The [historical rewrite receipt](reports/rewrites_postcheck_release.json) records a passing rewrite check: nine of ten strict improvements against a minimum of six, with cat/dog returning `no_safe_rewrite`. All ten tool workflows and managed sessions passed the tool/session check; there were ten HTTP attempts, zero retries and zero higher-risk returns. The [postcheck integrity receipt](reports/firestore_integrity_postcheck.json) matches all 1,016 expected historical documents to the exported content with zero differences. The [Firestore counts receipt](reports/firestore_postcheck_counts.json) records the then-current 510 prompts, 508 items and two real verdicts for a passing storage check.

The risk-evaluation and clip-accuracy numerical limits are retained in Detailed measurement limits. Prompt checking and upload-only clip review are live on the primary URL, with the recorded storage/feedback checks passed. One fresh optimized cloud review is measured, while performance on other clips remains UNMEASURED. Component readiness, browser checks, deployment, prediction validity and defect-detection acceptance remain separate claims.

The [freeze follow-up](reports/freeze_followup/REPORT.md) records the missing billing-console observation, this copy-only deployment and the human-confirmation requirement for clip-accuracy readiness.

## Team

Felix — build, direction · Sidhant Sushil — QA, product feedback.
