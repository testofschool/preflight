# Track I — video framing fix

**DONE.** The selected video and Desktop upload copy now contain the verified v7 framing fix.

| Fact | Final value |
|---|---|
| Upload file | `/Users/felix/Desktop/UPLOAD_THIS_Preflight_AIBC2026_3m28s.mp4` |
| Selected project video | `demo/preflight_demo_submission_3m.mp4` |
| Duration | **3:28.233** /208.233333 seconds |
| Bytes | **11,708,270** |
| SHA-256, both copies | `710146243d0a87c9cb3195a3d21f1ba8fd7070d95936a27e65da093358e42565` |
| Native media | 1920×1080 /30fps /H.264 High /yuv420p /silent |
| Replaced interval | frames2400–3486,80.000–116.233333s; exactly1087frames |
| Outside interval | **5,160 frames compared;0 changed**, independently confirmed |
| Captions | Same36 cues,35 active; JSON/script byte identical to v6;35/35 own midpoint checks and6,157/6,157 independent captioned-frame checks PASS |
| Required visual checks | 1:30 full Better prompt rewrite/risk and1:45 actual limited message centered/readable; own, parent and independent review PASS |
| Image-model calls /Veo calls | **0 /0** |

The segment is an actual production capture at1920×1080 with Chromium page scale2 and page scrolling; no post-capture upscale, crop, response replacement or product-text replacement. It shows the actual live rewrite for the dog/frisbee prompt,13.3% original→6.7% rewrite, followed by the actual503 limited-preview message. The canonical spoon/laptop example and all noninserted footage remain exactly unchanged. A fresh text rewrite is stochastic, so this own-prompt result differs from v6's3.3% rewrite.

The production status remained `samples` before and after. The only POSTs were one successful live-text `/preflight` and one non-sample `/preview` returning the exact503 limited message. The inspected frozen guard rejects that request before admission, cache or image provider work. Zero image calls is request-path evidence; `status.generations` is hard-coded0 and is not a cumulative meter. No Veo or postcheck request occurred.

Only the new1087-frame insert was encoded as ordinary High/CRF18. The original compressed pre/post segments were copied at the exact80.000s and116.233333s IDRs. Full decode passed. Local Chromium decoded and sought5,90,105,140 and200 seconds without errors.

| Preserved prior selected copy | Duration | Bytes | SHA-256 |
|---|---:|---:|---|
| `demo/preflight_demo_submission_3m_before_v7_20261018.mp4` |208.233333s|11,869,949|`6ebd825cbe8cbc1810c81d9592ac4e21028340a4ed92dbafb840cd5d684703a2`|
| `/Users/felix/Desktop/Preflight_AIBC2026_3m28s_backup_before_v7_20261018.mp4` |208.233333s|11,869,949|`6ebd825cbe8cbc1810c81d9592ac4e21028340a4ed92dbafb840cd5d684703a2`|

The inventory contains17 pre-existing demo/Desktop video files:15 unreplaced originals were verified unchanged, and the two replaced targets were backed up before overwrite. No video file was deleted. Earlier predictive-lossless diagnostic exports failed strict identity by sparse±1 YUV rounding; they were retained and never promoted. The all-intra diagnostic passed, and is retained. The compact final above is the selected export.

Evidence: `track_i_completion.json`, `track_i_video_facts.json`, `track_i_qa.json`, `track_i_independent_review.json`/`.md`, `track_i_parent_visual_review.json`, `track_i_capture.json`, `track_i_browser_playback.json`, and the decoded-frame manifests. Required frames are `demo/submission_check_v7/01m30s.png` and `01m45s.png`.

Felix's full-video acceptance and YouTube upload remain pending. No commit or push was performed by the Track I worker.
