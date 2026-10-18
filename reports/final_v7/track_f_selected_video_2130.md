# Selected narrated v7 — 21:30 final F support

**Verified the selected local bytes, full decode, all caption midpoints and eight product/architecture/limits frames.** This report is separate from the earlier silent Track I review.

The selected source is `/Users/felix/Desktop/AI Builder Cup 2026/preflight/evidence/final_run_v8_20261018/v/preflight_v7_candidate.mp4`. Its SHA-256 is **`b5ede0341395b1a5f17616ff718454926e7fc3936273761bd93ad158ba6057ad`**, 26,823,790 bytes. Both Downloads copies named `UPLOAD_CANDIDATE_Preflight_AIBC2026_v7_narrated_3m28s.mp4` and `… (1).mp4` match exactly. FFprobe confirms 1920×1080 H.264 High, 30 fps, 6,247 frames, 208.233333 s, plus AAC-LC stereo / 48 kHz. A fresh strict full video/audio decode returned 0 with no errors.

The selected URL is `https://youtu.be/1A8I-9NZ3Kc`, retained in the supplied parent instruction and current local v11 report/READY records. No new public network playback was performed in this review.

| Actual source | SHA-256 |
|---|---|
| `preflight/evidence/final_run_v8_20261018/v/captions_v7.json` and the actual Remotion `public/captions.json` copy | `9ae38c1871ea19208f1e44ff55f3cfa7ff973b8654d78d973e5954e00274c17b` |
| `…/v/caption_script_verbatim.txt` and sibling-project `evidence/final_run_v11_20261018/v2/frozen_script_35_cues.txt` | `8565d8809ff60cc3297db1d2eb1c17e62b8d74ae678e938f84c59dd10e191f08` |
| `…/v/remotion/src/index.tsx` | `474a0764fb2b3f26df321f03d5093c97e42e33824d270d49f8202abba3499223` |

All 35 nonempty caption strings match the old I script, but ten cue timing entries changed. For example, quote cue 4 begins at 10 s rather than 13 s; rewrite-caption boundaries are 53.133333 and 56.966667 s. The selected manifest governs. Fresh OCR of all 35 actual caption midpoints gave 31 exact raw matches and four uppercase-I/l/vertical-bar ambiguities; the four fresh crops were read visually and matched. All numerical captions were exact raw matches. This is a midpoint content check, not a new every-frame or acoustic-onset audit.

Freshly decoded frames were read at 45, 56, 58, 77, 90, 105, 170 and 184 s:

- The canonical spoon/laptop sample shows **46.8% → 15.8%**, with “Sample rewrite (saved).” At 45 s, 46.8% is explicitly a mixed heuristic risk estimate; historical vote estimate 53.5% is separate. At 58 s the line is partly clipped at the top, while the full line is clear at 56 s and the 15.8% caption is clear at 58 s.
- The own-prompt scene at 90 s shows the full golden-retriever rewrite and **13.3% → 6.7%**. At 105 s the complete real live-stills-limited message is legible and agrees with the caption.
- The saved-still metadata at 77 s says 0 model calls / $0.00 and labels it as an image-model still, not a Veo frame. This is sample-cache retrieval accounting, not a zero-call claim for the whole project or later probes.
- The architecture at 170 s names Cloud Run/FastAPI, Google ADK, Gemini 3.5 Flash on Vertex AI, Agent Platform Sessions, nearest-prompt/IRT tools and Cloud Firestore with 1,911 votes, parameters, feedback and saved stills.
- The limits panel at 184 s says **Best 8/20** with **60 test calls across three Gemini image models under shared capacity**, AUC 0.67, five saved samples, and clip-review accuracy not measured. The 8/20 figure is shown in that historical experiment context; it is not the later v11 P primary/fallback tally.

The original silent Track I canonical and candidate files both still hash to `710146243d0a87c9cb3195a3d21f1ba8fd7070d95936a27e65da093358e42565`, 11,708,270 bytes. Those bytes remain unchanged. Their earlier silence, exact outside-frame and caption-timing passes are lineage evidence and do not apply to the later selected narrated render.

Only this Markdown/JSON report pair was written. No video, source, UI, network/model, Git or publication state was changed. No fresh ASR, loudness/pacing measurement, provider audit or full manual/public playback is claimed. Full absolute paths, hashes, timing differences, frame hashes and check limits are in the JSON.
