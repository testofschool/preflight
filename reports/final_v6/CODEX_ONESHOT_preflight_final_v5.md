# CODEX ONE-SHOT — Preflight final package: admission cap, pitch deck PDF, narrated demo video, links (v5)
Written 2026-10-18 17:00 KST by Claude for Felix. Repo `testofschool/preflight` (public), production `preflight-00025-lij` (samples-only preview), tag `aibc-2026-submission-v3` = `d638c06`, main `de0d563`.
Local copy: `~/Desktop/AI Builder Cup 2026/preflight` (iCloud — confirm 0 dataless files before starting).
Deadline 2026-10-19 03:29 KST. **Report by 21:00 KST. Felix submits at 22:30 KST.** Hard stop 22:00 KST: whatever is not done is reported as not done.

## Inputs Felix places in the repo folder before you start (check each; a missing input blocks only its own track)
| Input | Path | Needed by |
|---|---|---|
| Organizer deck template (dashboard → Submissions → Template), exported as .pptx | `docs/template/aibc_template.pptx` | Track B |
| Felix's voiceover recording of §C.2 (optional) | `demo/voiceover.m4a` (or .wav) | Track C |
| Public YouTube URL of the final video (after Felix uploads Track C's output) | Felix pastes it to you | Track D |

## Track A — admission cap: let free cache hits through (config only)
Fact (Claude verified 12:50 KST): in production the only admitted `/preview` requests are saved sample stills (0 model calls, $0.00); typed prompts return 503 before admission. The 60/day cap therefore throttles only free responses — 52/60 were used on 10/18 by QA alone. A judging day with several judges can exhaust it.
1. Prove with a unit test that in `preview_mode: samples` with warm=false and live=false, **every** admitted path makes 0 model calls, including a sample whose cache document is missing (must return the limited message, not generate).
2. Then set `PREFLIGHT_PREVIEW_DAILY_LIMIT=500` (the existing code ceiling) on a no-traffic candidate revision with the **same image digest** `sha256:4bf0668a…`. No code or image change. Keep 5/min.
3. Gate: candidate `/api/status.preview_mode == "samples"`; 2 sample previews → hit, 0 calls; 1 typed preview → 503 limited copy; `/preflight` 2/2 200. Promote, record revision + traffic. If any step fails, leave `preflight-00025-lij` at 100%.

## Track B — pitch deck PDF on the organizer template
Rules (official): prescribed template; slide 1 = Team name / Team leader name / Problem Statement; must explain solution architecture and business case; English; exported PDF ≤ 5 MB.
- Open `docs/template/aibc_template.pptx`. Keep its masters, fonts and slide 1 layout. If the template has fixed section slides, map the content below onto them in order; otherwise use the slide list below. **If the template file is missing, stop Track B and report — do not build a deck on another template.**
- Images: use `demo/frames/*.png` (1920×1080) and the two saved stills for "a spoon and a laptop" (fetch through `/preview` only if the cap allows; otherwise export from Firestore read-only). Crop browser chrome if any appears. Every number below is fixed — do not add numbers.

| # | Title | Content (exact facts; shorten wording only) |
|---|---|---|
| 1 | (template fields) | Team: testofschool · Team leader: Jung Min Kang · Problem statement: "People who pay per generation for AI video only learn a clip is unusable after they have paid for it." |
| 2 | Paying to find out | Four user quotes (source in small type): "you still burn credits on the failed attempt" (Trustpilot, Runway review, Sept 2026) · "Only one of the generations was usable for my purposes" (Trustpilot, Sept 2026) · "I'm tired of wasting valuable credits on bad footage, I simply can't use" (Adobe Community) · "I recommend a lo-res preview render before having to spend actual credits" (Adobe Community). Footer: "In a 2024 public benchmark (GenAI-Bench), 21% of 1,911 human pairwise votes rejected both videos." |
| 3 | The gap | Every generator's loop: prompt → pay → generate → judge → re-prompt. Refunds cover generation errors, not finished clips that are unusable. Nothing sits before "pay". |
| 4 | Preflight: three rungs before you pay | ① Risk check (free): failure-risk estimate from 1,911 human votes + nearest historical prompts as evidence. ② Gemini rewrite, kept only if estimated risk drops. ③ A still image of the scene before a $3.20 Veo attempt (Veo 3.1, 8 s at $0.40/s, Google pricing page). After generation: upload a clip for a Gemini second look; its verdict is stored separately as feedback. |
| 5 | Demo | Frames 02 (risk + why), 04 (better prompt), 05 (saved still). Caption: "a spoon and a laptop: 46.8% → 15.8% estimated risk after the Gemini rewrite." |
| 6 | Architecture | Diagram: Browser → Cloud Run (FastAPI, asia-southeast1) → Google ADK rewrite agent on Gemini 3.5 Flash (Vertex AI) with Agent Platform Sessions → tools: nearest prompts + IRT difficulty → Cloud Firestore (1,911 votes, IRT parameters, feedback, saved stills). Clip review: Gemini video understanding. Still preview: Gemini image model. |
| 7 | What we measured, and the limits | Held-out AUC 0.67 for the risk score (historical signal, not a calibrated probability for today's models). Live image generation: 60 test calls across three Gemini image models, best 8/20 under shared capacity → judges see saved stills for the 5 samples, labelled "0 model calls · $0.00". Clip-review accuracy: not measured. |
| 8 | Business case | Who pays today: per-generation buyers (Runway TrustScore 1.1/5 from 340 reviews, Sept 2026; Adobe feature request "I lose too many credits doing trial and error", 219 votes). Who would buy a pre-pay step: studios and agencies running generation pipelines; generator platforms as an embedded step. Built by a Seoul producer who ran generative-video pipelines for 2.5 years; tested by a teammate in India. No revenue or market-size figure is claimed. |
| 9 | Next | Live stills with dedicated image capacity; separate tabs for check and clip review; non-English vote data before scoring non-English prompts; on-page emphasis of the risk drop. |
- Export PDF; report page count, byte size (must be ≤ 5,000,000), and render every page to PNG at 50 dpi into `docs/deck_check/` for Claude to inspect. Run a text extraction and confirm every number in the PDF appears in the table above (list any that do not). Commit `docs/Preflight_pitch_deck.pdf` and replace the README "pending" note with the file link.

## Track C — final demo video (≤ 3:00, public-ready)
### C.1 Assembly
Source: `demo/preflight_demo_raw.mp4` (108.37 s, SHA-256 `d1f3772d…`). Output `demo/preflight_demo_final.mp4`, 1920×1080, 30 fps, H.264 + AAC, **total 2:45–2:58**.
- 0:00–0:22 intro cards (plain background from the app's palette, large type): card 1 the four quotes from slide 2 (≈ 3 s each, one per screen); card 2 "Preflight — check an AI-video prompt before you pay to generate it."
- 0:22–2:10 the raw demo, unedited except speed: do not cut the risk result, the rewrite, the saved still or the clip review.
- 2:10–2:52 outro: slide-6 architecture diagram (10 s), slide-7 limits (12 s), closing card "Live: preflight-jcgro45veq-as.a.run.app · Code: github.com/testofschool/preflight" (8 s).
- Burn in captions of §C.2 (bottom, ≤ 2 lines, ≥ 36 px) so the video works muted.
- Audio: if `demo/voiceover.*` exists, align it to the section times (time-stretch ≤ 5% only; otherwise extend card durations) and mix at −16 LUFS; if not, ship silent with captions and say so.
- Report: duration, resolution, fps, audio stream yes/no, loudness, SHA-256, byte size, and 6 frames at 0:05, 0:30, 1:10, 1:40, 2:15, 2:45 as PNG in `demo/final_check/`.
### C.2 Narration / caption script (English, ≈ 380 words — Felix reads this; captions use the same text)
[0:00] People who generate AI video pay per attempt. Here is what they say. "You still burn credits on the failed attempt." "Only one of the generations was usable." "I recommend a lo-res preview before having to spend actual credits."
[0:16] Preflight is that step before you pay.
[0:22] Paste a prompt. Preflight compares it with 1,911 human votes on earlier AI videos and returns a risk estimate, with the closest past prompts as evidence. For "a spoon and a laptop", the estimate is 46.8 percent.
[0:50] Then a Google ADK agent on Gemini rewrites the prompt and keeps the rewrite only if the estimated risk drops. Here it drops to 15.8 percent. Copy it and go.
[1:00] Before paying about three dollars for an eight-second video, you can look at a still of the scene. For judging, the five sample prompts use saved stills: zero model calls, zero cost, and the label says so. In our tests, live image generation failed too often under shared capacity, so we did not put it in front of you.
[1:20] After you generate, upload the clip. Gemini takes a second look at sampled frames, and its verdict is stored as separate feedback next to the human votes. It is a second pair of eyes, not a verdict.
[1:55] Everything runs on Google Cloud: Cloud Run, Firestore, Gemini on Vertex AI, an ADK agent with Agent Platform Sessions.
[2:10] The architecture: one prompt, a traceable check, tools for evidence and difficulty, Firestore as memory.
[2:22] The limits are on the page. The risk score is a historical signal, held-out AUC 0.67, not a promise about today's models. Clip-review accuracy is not measured yet.
[2:36] Built in Seoul by a producer who paid for these failures, tested from India. Preflight: know before you pay.

## Track D — links (after Felix sends the YouTube URL)
Replace `<VIDEO_URL>` in `README.md` and `docs/submission-notes.md`; open the URL anonymously and confirm HTTP 200 and that it is not "private" or "unlisted" (the organizer asks for a public link). Push; re-run the anonymous clone and the history secret scan (0 hits). Print the Brief description character count (≤ 1,024).

## Do not
Change runtime code or the image (Track A is configuration only); raise the 5/min limit; enable live or warm generation; call Veo; add any number not listed above; move or delete tags; rewrite history; present a saved still as a live generation.

## Report
`reports/final_v5/REPORT.md` + paste: per track done / blocked / not done with numbers; revision and traffic; deck PDF size, pages, number check; video facts and the 6 frames; commit SHAs; description count; anything not done.