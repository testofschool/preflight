# Track C content production contract — v5

Readiness: DRAFT_WITH_ASSUMPTIONS (local export; human acceptance pending)
Decision: SELECTED
Primary medium: video

## Production contract

- Selected concept: Preflight explains the paid AI-video failure problem, demonstrates the pre-pay risk check/rewrite/saved still and post-generation clip review, then discloses architecture and measurement limits.
- Audience/use moment: AI Builder Cup judges viewing the required public demo link, including muted playback. This audience is explicitly supplied by the user's submission brief.
- Promise/payoff: show the complete workflow before asking judges to use the live app. Natural stop: live and code links, “know before you pay.”
- Channel/extent/language: local MP4 intended for Felix's later upload, English, 1920×1080, 30 fps, 172.000 seconds, H.264, burned-in captions. No voiceover supplied; silent fallback authorized.
- User completion line verbatim: “Output `demo/preflight_demo_final.mp4`, 1920×1080, 30 fps, H.264 + AAC, **total 2:45–2:58**.” The user's explicit exception is: “if not, ship silent with captions and say so.”
- Normalized target: VERIFIED_EXPORT. Publication is a separate Track D input after Felix uploads the final file.
- LOCKED: raw source bytes; all source frames in sequence; ten C.2 script sections verbatim; four full slide-2 quotes; title and closing link copy; specified facts and numbers; raw interval at 0:22–2:10; no live/still or machine/human confusion.
- ADAPTABLE: card composition using the app palette and Helvetica Neue; caption phrase boundaries and wrapping; minor raw speed adjustment; additional outro holds needed to fill the stated window.
- REFERENCE_ONLY: app CSS establishes palette/type; source frames establish workflow visuals.
- MISSING: optional `demo/voiceover.*`; public YouTube URL. These do not block the authorized silent local export.
- [observed] raw video is 108.366667 s, H.264, 1920×1080, 30 fps, no audio, SHA-256 `d1f3772d1187ee7ce1aeed1e0efe3f432c09337e90cc0b7113b6ca37aa94ab78`.
- [reported] product, benchmark, image capacity and biographical claims are the exact user-supplied claims; this render does not independently remeasure them.
- [assumption] Use the exact C.2 opening sentences for0–4 s, then four3 s quote cards at4–16 s, then title for6 s. Caption quotations align with the corresponding source cards; the unspoken third quote at10–13 s has no overlaid C.2 caption. This preserves the title at the supplied0:16 script boundary.
- Timing conflict: the brief specifies a 42 s outro window but its three nominal durations total 30 s. Preserve the 2:10–2:52 window and script starts; use architecture 12 s, limits 16 s, closing 14 s. This choice was reported before render completion.
- Supplied C.2 is 290 whitespace-separated words despite its “≈ 380 words” label. Preserve all supplied text; do not add narration.

## Complete draft / edit map

All audio cells are silent because no optional voiceover was supplied. Caption text below is verbatim C.2; it is divided into readable phrase cues in `demo/final_assets/captions.json`.

| Time | Picture/action | Caption text | State change / audience payoff |
|---|---|---|---|
| 00:00–00:16 | Opening exact C.2 sentences at0–4 s; four full user quotes, one per card,3 s each at4–16 s; exact slide-2 text and named sources. | People who generate AI video pay per attempt. Here is what they say. "You still burn credits on the failed attempt." "Only one of the generations was usable." "I recommend a lo-res preview before having to spend actual credits." | Recognize that failed usable clips can still cost credits. |
| 00:16–00:22 | Title: Preflight — check an AI-video prompt before you pay to generate it. | Preflight is that step before you pay. | Name the step before paying. |
| 00:22–00:50 | Entire raw recording begins, no cuts; prompt/risk result and nearest evidence. | Paste a prompt. Preflight compares it with 1,911 human votes on earlier AI videos and returns a risk estimate, with the closest past prompts as evidence. For "a spoon and a laptop", the estimate is 46.8 percent. | See the estimate and evidence. |
| 00:50–01:00 | Raw recording continues through the Gemini rewrite. | Then a Google ADK agent on Gemini rewrites the prompt and keeps the rewrite only if the estimated risk drops. Here it drops to 15.8 percent. Copy it and go. | See that only a lower estimated risk rewrite is kept. |
| 01:00–01:20 | Raw recording continues through the saved still and sample labels. | Before paying about three dollars for an eight-second video, you can look at a still of the scene. For judging, the five sample prompts use saved stills: zero model calls, zero cost, and the label says so. In our tests, live image generation failed too often under shared capacity, so we did not put it in front of you. | Inspect the scene and understand the capacity limitation. |
| 01:20–01:55 | Raw recording continues through upload, review, and feedback. | After you generate, upload the clip. Gemini takes a second look at sampled frames, and its verdict is stored as separate feedback next to the human votes. It is a second pair of eyes, not a verdict. | See separate machine review feedback. |
| 01:55–02:10 | Raw recording continues to its final source frame. | Everything runs on Google Cloud: Cloud Run, Firestore, Gemini on Vertex AI, an ADK agent with Agent Platform Sessions. | See the full cloud workflow without cutting evidence. |
| 02:10–02:22 | Architecture card: Browser → Cloud Run → ADK → tools → Firestore; image/video model branches. | The architecture: one prompt, a traceable check, tools for evidence and difficulty, Firestore as memory. | Trace the evidence, rewrite, and storage path. |
| 02:22–02:36 | Limits card; holds until02:38. | The limits are on the page. The risk score is a historical signal, held-out AUC 0.67, not a promise about today's models. Clip-review accuracy is not measured yet. | Keep AUC, capacity and unmeasured review accuracy visible. |
| 02:36–02:52 | Limits card through02:38, closing links from02:38. | Built in Seoul by a producer who paid for these failures, tested from India. Preflight: know before you pay. | End with provenance and a voluntary visit to live/code links. |

## Asset and rights manifest

`track_c_asset_manifest.csv` is the asset ledger. Source footage and the existing still visible inside it are reused under the explicit user instruction. The brief supplies and instructs use of the four short public quotes with named sources. Their text/source attribution is preserved; their original pages were not re-fetched by this video track. No real-person likeness, cloned voice, TTS, new generative image, paid call, or external upload is used. Installed system fonts are rasterized; no font binaries are redistributed. This ledger records the basis of this local export and does not assert independently verified ownership of third-party quotations.

## Build and edit map

- Run `python3 reports/final_v5/track_c_render.py` with Pillow, ffmpeg, ffprobe and the macOS system Helvetica Neue/Menlo fonts available.
- The script refuses a source SHA mismatch or a newly present voiceover; it never modifies the raw source or performs network requests.
- PNG cards and transparent caption PNGs are generated at1920×1080. Captions use43 px Helvetica Neue, dark opaque backing, bottom safe margin, and at most2 lines (actual current cues all fit1 line).
- Raw speed multiplier:108.366667/108 =1.0033950648. All source time is mapped in order to22–130 s. Only required caption overlays are added to the full-frame source visual; no raw segments are cut.
- Intro, raw and outro are assembled, then caption PNGs are burned into an H.264/yuv420p MP4 with faststart.
- No voiceover means no AAC stream. Loudness is N/A, not a measured0 LUFS.

## QA and falsification

- Source mismatch, incorrect text reconstruction, caption line overflow, wrong dimensions/fps/duration, unexpected audio, missing requested frame, or failed full decode invalidates the export.
- Preserve counterevidence: the risk is historical, clip-review accuracy remains unmeasured, and judging uses saved stills labelled0 model calls/$0.00. The video does not turn a still into a live video generation claim.
- Exact C.2 section-text and phrase reconstruction checks are in `track_c_caption_text_check.json`.
- Native stream facts and hashes are in `track_c_ffprobe.json` and `track_c_video_facts.json`.
- Human-facing release acceptance remains Felix's; upload is not part of this local assembly.

## State ledger / next gate

The canonical state ledger is in `track_c_QA.md`; this contract does not maintain a second status ledger.

The immutable contract above predates final export inspection. Final observed state and validation receipts are recorded separately in `track_c_QA.md`; they do not relax these requirements.
