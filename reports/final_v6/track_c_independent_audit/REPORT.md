# Independent new-submission video audit

PASS within this local artifact, source and recorded-network scope. This audit does not claim a YouTube upload or public-link verification. It read the new video and capture receipts; it did not edit any video, README, parent report, runtime code, setting, tag or Git history, and made no application/model/network request.

| Check | Independently observed result |
| --- | --- |
| New submission file | `demo/preflight_demo_submission_3m.mp4` |
| Desktop upload copy | `/Users/felix/Desktop/UPLOAD_THIS_Preflight_AIBC2026_3m28s.mp4` |
| SHA-256, both copies | `6ebd825cbe8cbc1810c81d9592ac4e21028340a4ed92dbafb840cd5d684703a2` |
| Bytes, both copies | 11,869,949 |
| Native duration | 208.233333 s / 3:28.233, within the human-approved 190-215 s range |
| Native video | 1920 x 1080, H.264, yuv420p, 30/1 fps, 6,247 frames |
| Audio / loudness | No audio stream; LUFS N/A. Captions support silent viewing. |
| Full bitstream decode | `ffmpeg -v error -i ... -f null -` exit 0, empty stderr |
| Assembly | Original 80 s + entire actual 36.233333 s production capture + original remaining 92 s. Existing frame order retained. |
| Original 2:52 backup | `demo/preflight_demo_final.mp4` and its old Desktop 2m52s copy both retain SHA-256 `4bbe0168a40156c06718c53df736ecd90e2314b0539629bed0cc3fa947bdda03`, 8,109,690 bytes |
| Preserved original beats | Nine independent full-frame comparisons, before and after insertion, all PASS; maximum mean absolute RGB-channel difference 0.297 on a 0-255 scale, consistent with re-encoding |
| Caption text | All 33 v5 cues, including its intentional blank cue, retain exact text/order. Reconstructed v5 caption text equals `reports/final_v5/track_c_caption_script.txt`. Three added captions, no digits. |
| Actual burned captions | All 35 nonempty cue midpoints decoded from the new MP4 and compared to expected glyph/pill pixels: 35/35 PASS, minimum expected bright-glyph fraction 1.0 |
| Caption size | 43 px minimum, maximum one line, across original and new cues |
| Timing | Original post-80s cues shifted exactly 1,087 frames. Cue timeline contiguous from frame 0 through exclusive frame 6,247. No original cue split by insertion. |

The three new captions are:

- “Your own prompt gets a live Gemini rewrite too.”
- “Live stills are limited to the samples during judging, and the page says so.”
- “Every number comes with what it is and what it is not.”

The first midpoint falls during the real request's loading state; the accepted live rewrite is visibly shown later within the same caption span at 1:35. The new own-prompt UI displays 13.3% original and 3.3% rewrite. These are observations for “a dog catching a frisbee on a beach at sunset”, separate from the unchanged v5 spoon sample's 46.8% to 15.8%. The new captions make no added numerical claim.

## Actual-frame visual inspection

All five requested times and three action-detail frames were independently decoded from the delivered MP4, then viewed at native resolution. All three new-caption midpoint frames were also viewed. Large captions are legible and fit. No new image, UI mock, replaced response, cropped-away verdict or introduced number-claim fabrication was observed.

| Time | Observed frame |
| --- | --- |
| 0:05 | Original first quote and readable burned caption |
| 1:10 | Saved rewrite still, zero-call/cost label and original caption |
| 1:35 | Actual typed-prompt live rewrite with 13.3% to 3.3% risk line |
| 1:40 | New segment, transition toward preview action; own-prompt caption readable. The limited error is not yet shown at this exact frame. |
| 1:42 | Real red limited-preview message and matching new caption visibly present; no generated still |
| 1:50 | “What this score is” expanded, historical-source/AUC explanation and limitation visible, readable new caption |
| 2:20 | Original clip-review result with separate feedback and truthful synthetic-clip/source label, as approved by the human |
| 3:00 | Original limits card: AUC 0.67, best 8/20, saved samples' zero calls/cost, clip-review accuracy unmeasured |

Frames are `check_005s.png`, `check_070s.png`, `check_095s.png`, `check_100s.png`, `check_102s.png`, `check_110s.png`, `check_140s.png`, `check_180s.png` in this audit directory. `new_caption_midpoint_1.png` through `_3.png` are actual decoded final-video pixels, not source caption assets.

## Image-call evidence and counter boundary

Visible in-app cumulative generation counter: **NOT SHOWN**, before and after. `/api/status.generations` is 0 before and after, but `app.py:194` hardcodes that field. It is not a cumulative meter and does not independently establish image usage.

The zero-image-call conclusion for the new preview interaction instead has this inspectable basis:

- The recorded network contains one real `POST /preflight` HTTP 200 with `rewrite_source=live`, followed by one `POST /preview` HTTP 503 with the exact limited message. No other preview/postcheck request appears in this new capture.
- Recorded before/after status has `preview_mode=samples`. The original typed prompt and its accepted rewrite are independently outside the complete saved original-and-rewrite whitelist in `cloud/sample_rewrites.json`.
- `static/app.js:241-243` selects the accepted rewrite for the clicked “Preview a still” action. Request bodies are not logged in the capture receipt; this selection is established from the frozen UI source and observed interaction.
- `app.py:259-260` rejects a non-sample preview while live mode is false, before admission/cache/provider work and before `provider.generate` at line 285. The exact observed 503 text agrees with this path.
- The base recording script is unchanged: its current SHA agrees with the capture's before/after SHA. The capture uses real production UI requests, with a visible cursor; no mocks or response/DOM replacement were added. Live Gemini text rewrite was authorized by the human.

Thus this is request-path/source evidence of **0 image-model calls for this recorded preview interaction**, not a claim of cumulative image accounting or provider-billing telemetry. There is no Veo call in this capture.

Machine-readable evidence: `audit.json`, `native_and_identity.json`, `caption_burned_checks.json`, `preserved_beat_comparisons.json`, `production_request_evidence.json`, `supplement_source_crosscheck.json`. The audit scripts write only sanitized evidence inside this directory.
