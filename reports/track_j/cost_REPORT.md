# Track J read-only cost and billing audit

Baseline `preflight-00027-pit` was read through the native revision API: `gemini-3.5-flash`, Vertex backend, model endpoint `asia-southeast1`. Therefore the applicable list-price row is standard **non-global**, not global. No checks or image/model calls were run by this audit.

The official [Vertex/Gemini pricing page](https://cloud.google.com/vertex-ai/generative-ai/pricing) (redirects to the Gemini Enterprise Agent Platform pricing URL) quotes `Price (/1M tokens)` and the Gemini 3.5 Flash non-global input subrow, “Non-global* | $1.65 | $1.65 | $0.165 | $0.165”; for “Text output (response and reasoning)”, “Non-global* | $9.90 | $9.90 | N/A | N/A”. These are standard on-demand USD prices; no cached-input discount, credits or promotion is applied here.

Across 126 saved Gemini 3.5 Flash complete-usage receipt entries (including duplicate snapshots), the most expensive recorded check is `reports/cloud_latency.json`, `/validation/5/response/agent_trace`: **15,206 input +443 response/output tokens** over **4 model requests** (3 planner +1 rewrite). Its check token sum and receipt SHA-256 are in `cost_receipt_projection.json`.

`2,000 × (15,206 × $1.65 +443 × $9.90) /1,000,000 = $58.9512`.

Taking input and output maxima independently is more conservative: 15,206 input and 486 output tokens, giving **$59.8026** for 2,000 checks at that envelope. The maxima come from different checks.

**A guaranteed future worst-case is UNVERIFIABLE from these receipts.** The API permits longer prompts, reuse of session history, and up to 6 planner requests plus 1 rewrite request; failed requests can incur work absent from completed response receipts. The figures above are a maximum-recorded-check projection and a recorded-maxima envelope, respectively. They are not a spending cap. The shared allowance can also be consumed by `/postcheck`, which this text-inference projection does not price. Explicit thinking counts were not retained; each saved call's `total_token_count - prompt_token_count` equals its `candidates_token_count`, and all output residual is conservatively priced at the output rate. Infrastructure, managed-session costs, video processing, taxes and future price changes are excluded.

Project billing link is readable and billing is enabled. **Budget alert existence: UNVERIFIABLE.** Native read-only `gcloud billing budgets list` returned `SERVICE_DISABLED` for the Cloud Billing Budget API on the consumer project. The API was not enabled, no billing settings were changed, and a failed list is not evidence of no budget. Sanitized native evidence is saved in `cost_billing_budgets_read_only.json`.

## Supplement: all allowed calls at recorded per-call maxima

The existing receipt snapshot contains 378 planner calls and 126 candidate-generation calls. Maximum recorded planner usage is **5,058 input +169 output tokens per model call** (`reports/cloud_latency.json`, `/validation/5/response/agent_trace/token_usage/3`). Candidate-generation maxima are **911 input tokens** (`reports/postcheck_canary_live.json`, `/rows/2/attempt/response/agent_trace/token_usage/2`) and **151 output tokens** (`reports/cloud_latency.json`, `/validation/5/response/agent_trace/token_usage/2`); these input and output maxima come from different calls.

Reopened source at `cloud/rewrite_agent.py:273` rejects a seventh planner request. Lines 237–241 create the candidate-generation task only once per check and reuse it. Thus use **6 planner +1 candidate-generation calls**. The separate ADK runner setting `max_llm_calls=8` at line 317 is looser than the six-planner scheduler limit. No runtime code was changed by this audit.

At all allowed calls priced at their recorded per-call maxima:

`input/check = 6 ×5,058 +911 = 31,259 tokens`

`output/check = 6 ×169 +151 = 1,165 tokens`

`2,000 ×[(31,259 ×$1.65 +1,165 ×$9.90)/1,000,000] = $126.2217`

**$126.22 is the stronger receipt-based call-limit envelope.** It accounts for the maximum number of model calls the code permits, unlike the earlier $58.95 maximum-recorded-check projection and $59.80 separate-check-maxima envelope, which each retain the four calls observed in completed checks. It remains conditional on future per-call token usage staying within recorded maxima. Session growth, larger inputs and outputs, or incomplete failure receipts mean a guaranteed future hard upper bound remains **UNVERIFIABLE** from these records. The code allows up to 2,000 output tokens per planner request and 1,000 for candidate generation; the 169/151 output maxima used here are observed values. Exact receipts, source excerpts, hashes and formula are in `cost_call_limit_envelope.json`.
