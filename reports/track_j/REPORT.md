# Track J — cumulative allowance 3,000

PASS. Completed and promoted at 2026-10-18T18:37:58.256200+09:00, before the 20:30 KST hard stop. H and I completed and their receipt commit was pushed before J's runtime work began. G/D/F were released to resume immediately after J passed; the video and deck were not modified by J.

Production: `preflight-00029-teb` at 100% traffic. Read-only Firestore count after promotion: **206 / 3,000**, **2,794 remaining**. Before J the count was **204 / 1,000**. Candidate admission increased it by exactly **2**; there were **5 HTTP gate attempts, 0 retries**, and no extra smoke checks.

## Exact scope and full suite

Source commit `59fb23b262af480709461b648e84d26010e26060` changes only `cloud/store.py`'s cumulative ceiling comparison from 1,000 to 3,000 and adjusts one existing unit test. The test accepts 3,000, checks the persisted limit and remaining allowance, and rejects 3,001 without changing stored state. The cumulative default stays 1,000 and the rolling shared limit stays 20/minute. The existing rejected-config exception wording still says one to 1000; it was deliberately preserved under the one-line runtime scope.

Full suite: **201 tests + 11 subtests passed**, 0 failures/errors/skips, 3 warnings. JUnit reports 212 including subtests and 201 testcase rows. Initial local release preparation stopped before mutation because it expected the JUnit total to equal the testcase count; the parser was corrected, the original passing suite receipt was reused, and no tests or live gates were rerun. See `preparation_count_correction.json` and `parser_preparation_discrepancy.json`.

## Build, candidate and native provenance

Exactly one build was submitted: `f991c8fe-38aa-4776-8b1c-9634a7c4114d`; native status SUCCESS. Build input was an isolated snapshot of the exact committed 25 runtime files plus the unchanged build configuration. No previous build receipt was overwritten.

The no-traffic candidate kept `preflight-00027-pit` at 100% during validation. Immutable revision spec and operational annotations matched the baseline, allowing only the new image and `PREFLIGHT_TOTAL_REQUEST_LIMIT=3000`.

- Git runtime SHA-256: `5ecfefe996dd08ef9dc9fe4bdc38e7dc735e28c487018a426fb6521918e88a21`
- Native Cloud Build source runtime SHA-256: `5ecfefe996dd08ef9dc9fe4bdc38e7dc735e28c487018a426fb6521918e88a21`
- Native image digest: `sha256:335aa2ed7565f80a2b0e491fe1138c4e09f6362acb1099e30d8b3acc3a4b0d8a`
- Generation-pinned native archive SHA-256: `63cb7d3047b6b0a59aedb101bc9a9c81c04eb0fbb84d3f5488fded08fc0aff7d`
- All 25 runtime files match; both runtime hashes match; native Build and Run image digests match.

## Required candidate gate

| Probe | HTTP | Observation |
|---|---:|---|
| `/api/status` | 200 | `preview_mode=samples`, preview enabled |
| One sample `/preflight` | 200 | Saved sample rewrite; 0 live rewrite calls |
| One typed `/preflight` | 200 | `rewrite_source=live` |
| One sample `/preview` | 200 | `cache=hit`, header hit, 0 model calls, $0.00, 76,625 image bytes |
| One typed `/preview` | 503 | Exact limited copy; non-sample request rejected before image provider |

Typed preview copy: “Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works.”

Gate allowance reads: 204 before and 206 after. The candidate's effective env limit was 3,000 before admission, while Firestore's last-admitting-revision limit remained 1,000; after admission the stored limit became 3,000. The post-promotion read remained 206 / 3,000. No Firestore counter was reset or manually changed. No image generation or Veo call was made.

## Source publication

Annotated tag `aibc-2026-submission-v4` points to source commit `59fb23b262af480709461b648e84d26010e26060`. Source and tag were atomically pushed after all candidate HTTP gates and provenance passed, and before promotion. A credential-free anonymous clone verified the exact source commit, annotated tag, and runtime digest. All three previous submission tags are unchanged.

Source history scan: 21 commits, 937 blobs, **0 hits**, complete with 0 errors. Evidence: `history_scan.json`, `publication.json`, `anonymous_clone.json`. Final evidence publication is recorded separately so the source tag remains immutable.

## List-price cost of 2,000 additional checks

The deployed text endpoint is regional `asia-southeast1`, so Gemini 3.5 Flash standard **non-global** prices apply. The official [Gemini / Vertex pricing page](https://cloud.google.com/vertex-ai/generative-ai/pricing) labels the rates per million tokens and quotes the input row “Non-global* | $1.65 | $1.65 | $0.165 | $0.165” and the text-output row “Non-global* | $9.90 | $9.90 | N/A | N/A”. Output covers response and reasoning.

Using already recorded per-call maxima and every call permitted by code (6 planner calls + 1 rewrite call):

- Input/check: `6 × 5,058 + 911 = 31,259 tokens`
- Output/check: `6 × 169 + 151 = 1,165 tokens`
- `2,000 × (31,259 × $1.65 + 1,165 × $9.90) / 1,000,000 = $126.2217`, or **$126.22**.

This is a **receipt-based call-limit projection**, conditional on future per-call usage staying within recorded maxima. A guaranteed future worst-case is **UNVERIFIABLE from the receipts** because prompts and reused session history can be larger, and unsuccessful work may be absent from successful-response receipts. It is not an actual-billing figure or spending cap. Infrastructure, managed sessions and video postcheck are excluded. The same cumulative allowance is also consumed by `/postcheck`; the text-inference calculation does not price those requests.

For comparison, repeating the single most expensive recorded 4-call check costs $58.9512; independent recorded per-check input/output maxima yield $59.8026. The more conservative 6+1-call projection above is the primary J estimate. Exact receipt paths, hashes, source excerpts and formulas are retained in `cost_call_limit_envelope.json`, `cost_receipt_projection.json`, and `cost_REPORT.md`.

Budget-alert existence: **UNVERIFIABLE**. Project billing was readable and enabled, but the read-only budgets list returned `SERVICE_DISABLED` for the Cloud Billing Budget API. No API, budget, alert or billing setting was created or changed. This does not establish that no budget exists.
