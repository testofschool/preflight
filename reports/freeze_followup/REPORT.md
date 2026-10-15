# Feature freeze follow-up — 2026-10-16

The owner froze features and requested billing-console spend, the cold-start notice, unchanged V4/V8 wording, and readiness for human-confirmed V8 clips. The product feature code, JavaScript, dependencies, model/backend and non-image Cloud Run settings are unchanged from `c64a3619c96e45ef67354e76472479163839e7e6`. The only deployed source change is `static/architecture.html`; README and local verification-helper corrections are also packaged.

## Billing-console spend

Observed **2026-10-16 08:48:26 Asia/Seoul** in authenticated Cloud Billing, Live costs, grouped by service. The console/account linkage matches the configured project and that account has exactly one linked project. Project and billing-account identifiers are redacted.

Displayed period: **2026-10-01 through 2026-10-15**, currency KRW.

| Service | Posted actual cost | Live estimate |
| --- | --- | --- |
| Vertex AI | ₩0 | ~₩884 |
| Cloud Run | ₩0 | ~₩26 |

The console headline is **~₩910.4**; its independently rounded table subtotal is **~₩910**. The posted ₩0 is not zero incurred cost. Google labels live costs directional estimates for eligible SKUs, excludes credits and says amounts may change when fully monetized. Actual invoice spend remains unfinalized. The normal posted-cost report showed no service rows; the live-cost view supplied the nonzero amounts. These are project-wide service amounts, not a full GCP bill or a claim of exclusive attribution to Preflight. The copy deployment occurred after this cost snapshot.

[Redacted machine receipt](spend.json). Native console text, linkage proof, screenshots and the detailed owner report are preserved at `../../../evidence/preflight-20261016/billing-console/`. No billing cap/payment setting was changed.

## Copy correction and deployment

README and the live `/architecture` page contain:

> First request after idle may take ~20 s (cold start, min-instances 0).

Their V4 and V8 status/evidence clauses are copied verbatim from `COMPLETION_REPORT.md`. The canonical completion report was not edited; SHA-256 remains `a75d3b29cf6f41eeee13b46dcf30dbfb78f7c6df3f065ed8df3b14051ac831ef`. V4 remains FAIL and V8 remains NOT RUN/UNVERIFIABLE. No acceptance threshold or failed/unverified claim was relaxed.

Build `f9b93571-500e-422a-872e-f406b111ed0b` succeeded with runtime input hash `e61204928c81c3906e0be94705d9158dc4b1eb5917f8d179c6db6aba56c2b3a8`. The existing primary URL now serves copy-fix revision **preflight-00008-g92**, Singapore, min0, timeout40s, concurrency80. Native before/after comparison confirms runtime settings unchanged except the image. No environment, model, dependency, budget, IAM or public-access setting was changed. The baseline feature deployment receipts in `reports/cloud_build.json` and `reports/cloud_run.json` are retained as historical; current copy-fix receipts are in this directory.

The real rendered page showed the exact notice and canonical V4/V8 paragraphs, cloud mode, active session and no horizontal overflow. Only navigation/GET verification was used; no application inference POST was sent. V3 timing evidence remains the existing revision6 measurement, not a new revision8 measurement. [Live text](live_copy.json), [literal checks](copy_checks.json), [feature freeze](feature_freeze.json), [build](cloud_build.json), [native configuration](cloud_run.json), [deployment stdout](../../logs/freeze_copy_deploy.txt).

## V8 standby

No new human-confirmed clips have been supplied, so no new V8 inference or acceptance result exists. The owner can supply1–3original clips and confirmed category/time/reason today; originals, hashes and human provenance will be frozen before inference. [Readiness procedure](V8_READINESS.md).

The local verification helper now supports explicitly partial1–2clip batches without changing the three-clip/at-least-two-matches/±2s criterion. It rejects cached or concurrent-discarded reviews for fresh V8 credit, validates timezone/nonfuture freezes, and durably records a source-keyed attempt before POST so renaming outputs cannot retry an unknown/completed source. Human confirmation must be explicit. Mechanical matching alone cannot establish accuracy; compatible visual reasons require manual adjudication before final acceptance. Prior01/02 receipts and labels remain unchanged.

[Helper changes and offline test evidence](../verification_helper_fix.json), [stdout](../../logs/verification_helper_tests.txt). Nineteen offline regression tests passed; fake HTTP/temporary test sources are distinct from real owner fixtures. These corrections affect only the local verifier/tests and are excluded from the deployed image. No product features, actual owner fixtures, new application model calls or Veo calls were added by this follow-up.
