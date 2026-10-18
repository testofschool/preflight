# Track F preparation — not the final pass

Observed 2026-10-18T18:14:48.861671+09:00 at HEAD `2a631fec9fda2dd7d0d107c270a9034f53193fd4`.

The final pass must inspect the selected new deck PDF, new video, caption file, actual video frames, README, notes and a fresh read-only status GET. It is due at 21:30 KST or after Track D; this preparation does not satisfy that timing.

Brief description: **952/1,024 characters**; SHA-256 `3bac4ff63ca67bf51c54d329abad0c3cb16da13f697bd35e3041e40959f6ef23`.

GET `https://preflight-jcgro45veq-as.a.run.app/api/status` returned **200**, with `preview_mode=samples` and the exact message “Image preview — Active for sample prompts (saved stills); live generation limited”. Cloud Run, Gemini, ADK, Agent Platform Sessions, Firestore and postcheck flags are true. `generations=0` is not cumulative usage evidence.

Public YouTube URL: **WAITING**. README and notes still contain `<VIDEO_URL>`. Placeholder equality is not a passed public-URL equality check.

| # | Canonical row | Final evidence requirement |
| --- | --- | --- |
| 1 | Live URL | README, notes, deck links and closing video frame target the same production origin. |
| 2 | Repo URL | Notes, deck and closing video frame identify testofschool/preflight. |
| 3 | Video URL | Actual public YouTube URL is equal across README, notes and new deck; verify public visibility and shown duration separately in D. |
| 4 | 1,911 | Human-vote count remains 1,911; preserve historical-source qualification. |
| 5 | 0.67 | Held-out AUC is 0.67, labeled historical; exact 0.668329 and target 0.68 may appear with separate roles. |
| 6 | 46.8% | Spoon/laptop mixed-proxy original example is 46.8%; other sample contexts are separate. |
| 7 | 15.8% | Spoon/laptop rewrite example is 15.8%; other sample contexts are separate. |
| 8 | $3.20 / three dollars | Per-attempt illustrative price is USD 3.20 for eight seconds at USD 0.40/s; total-budget examples are separate. |
| 9 | 8/20 | Best live-image probe is 8/20; no reliable live-image claim. |
| 10 | Gemini 3.5 Flash | Rewrite role remains Gemini 3.5 Flash; status gemini=true does not prove its model version. |
| 11 | Google ADK | ADK rewrite-agent references agree with status readiness flag. |
| 12 | Agent Platform Sessions | Session references agree; do not conflate with Agent Engine runtime hosting. |
| 13 | Cloud Run | Application hosting references agree with status readiness flag. |
| 14 | Firestore | Storage references agree with status readiness flag. |
| 15 | samples: Active for sample prompts (saved stills); live generation limited | Saved-still and limited-live-generation scope is consistent; zero calls and zero dollars refer to saved still delivery. |

Potential conflict to avoid: product pictures and the “before pay” claim must retain the saved-sample-still / limited-live-generation scope. An image preview cannot establish motion quality, measured savings, or clip-review accuracy.

No production POST, image-model call, Veo call, runtime edit, cloud mutation, commit or push was made. TLS verification used the installed certifi CA bundle after the host default trust failed.

Primary preparation receipt: `track_f_preparation.json`. Prior v6 audits informed row selection only; their frame conclusions will not be promoted to evidence for replaced v7 material.

## Preparation refresh after Track I, while Track J is in progress

Observed 2026-10-18T18:33:27.805601+09:00; HEAD `59fb23b262af480709461b648e84d26010e26060`. This remains preparation only. The final pass awaits the root trigger after D or at 21:30 KST, and must use the post-J source/runtime baseline.

Selected actual Track I MP4: `demo/preflight_demo_submission_3m.mp4`, **208.233333 seconds**, **11,708,270 bytes**, SHA-256 `710146243d0a87c9cb3195a3d21f1ba8fd7070d95936a27e65da093358e42565`. Actual bytes match the Track I facts; ffprobe confirms 1920×1080, 30 fps and 6,247 frames. Caption-script SHA-256 `8565d8809ff60cc3297db1d2eb1c17e62b8d74ae678e938f84c59dd10e191f08`; manifest SHA-256 `8b6ac612d21ab3bf1eccef76a16589f8ec2c84f82499775ed076faac9b1c3c4c`.

The 1:30 frame visibly shows the own dog/frisbee prompt result **13.3% → 6.7%**, the full rewrite text and the saved-still mode label. The 1:45 frame visibly shows the limited-live-still message. These are separate from the canonical spoon/laptop **46.8% → 15.8%** example. The selected v7 video supersedes the v6 own-prompt **13.3% → 3.3%** recording; the different live rewrite is not a conflicting value for the spoon/laptop example.

J leaves the source default at 1,000 (`cloud/store.py:89`) and raises the validated cumulative maximum to 3,000 (`cloud/store.py:92`). Three README claims require reconciliation after successful J; notes have no such cap/default claim.

| Surface | Exact current claim | Truth after successful J |
| --- | --- | --- |
| `README.md:86` | **Max 20 checks/min shared** across the service, with a cumulative allowance of at most 1,000 admitted checks. | FALSE: cumulative maximum becomes 3,000, while the rolling 20/minute limit remains unchanged. |
| `README.md:196` |  /  `PREFLIGHT_TOTAL_REQUEST_LIMIT`  /  Cumulative admitted-check allowance; default and maximum are 1,000  /  | PARTIALLY FALSE: default remains 1,000; maximum becomes 3,000. |
| `README.md:261` | Cloud mode uses a shared Firestore transaction to admit at most 20 checks per rolling minute across instances, with a cumulative allowance of at most 1,000 admitted checks. | FALSE: cumulative maximum becomes 3,000, while the rolling 20/minute limit remains unchanged. |

Additional observation for the J owner: `cloud/store.py:93` still says “between one and 1000” in the invalid-configuration error text while the adjacent validation ceiling is 3,000. No edits were made. The final audit must not claim zero conflicts while the stale maximum prose remains. The prior status GET remains a pre-J snapshot; no current-runtime conclusion is drawn from it.

## Post-J reconciliation by root

The three README allowance statements identified above are now corrected in the working tree: default 1,000, maximum 3,000, production configured to 3,000. Their earlier FALSE/PARTIALLY FALSE labels describe the historical preparation snapshot, not the corrected current text. Root independently read the native post-J service/revision/image/environment and recomputed all 25 runtime file hashes; `post_j_scope_baseline.json` records that PASS.

The old invalid-configuration error wording remains under J's expressly bounded one-line runtime scope. It is recorded as a known implementation limitation, separate from the requested fifteen presentation-consistency rows. No further runtime edit is authorized here. This section still does not constitute the final timed Track F pass.
