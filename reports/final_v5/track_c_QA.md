# Track C QA — VERIFIED_EXPORT

Track C: DONE as the expressly authorized silent captioned fallback. The final MP4 is a local export; Felix's upload, public URL verification, and human acceptance have not been performed by this track.

## Observed export

| Check | Observed result |
|---|---|
| File | `demo/preflight_demo_final.mp4` |
| Duration |172.000 seconds (2:52), inside2:45–2:58 |
| Video |1920×1080,30/1 fps,H.264,yuv420p,5160 frames |
| Audio stream |No; no `demo/voiceover.*` supplied |
| Loudness |N/A — no audio stream; no0 LUFS measurement claimed |
| Byte size |8,109,690 |
| SHA-256 |`4bbe0168a40156c06718c53df736ecd90e2314b0539629bed0cc3fa947bdda03` |
| Source SHA before/after |`d1f3772d1187ee7ce1aeed1e0efe3f432c09337e90cc0b7113b6ca37aa94ab78`; unchanged |
| Source continuity |Entire chronological108.366667-second source is mapped to22–130 s at1.0033950648×; no segment cuts |
| C.2 text |All ten sections exactly match the attachment, including punctuation;290 supplied whitespace words |
| Captions |33 timeline cues:32 nonblank cues plus the intentional10–13 s transparent gap;43 px; actual maximum1 line |
| Actual caption presence |All32 nonblank midpoint frames passed both dark-pill presence and>95% expected bright glyph pixel checks; intentional gap passed |
| Complete bitstream |Full ffmpeg decode exit0, empty stderr |
| Six requested PNGs |All1920×1080, nonempty, Pillow-decodable, hashes/sizes match metadata |

## Actual visual inspection

Viewed the actual final export's required six-frame contact sheet and full-size frames, then refreshed00:30 after the overlay correction. Read the intro quote/source and matching caption, risk workflow, saved-still label, clip review/feedback, architecture nodes and captions, limits card, closing links and captions. No caption overflow was observed. The risk score/clip-review distinction and saved-still cost label remain visible in the source. Intro11 s shows the third full quote with no conflicting caption.

Required frames are `00m05s.png`, `00m30s.png`, `01m10s.png`, `01m40s.png`, `02m15s.png`, `02m45s.png` under `demo/final_check/`. `contact_sheet.png` shows these six together. Extra full-size checks cover the opening, other quotes, title, and limits card.

## Timing decisions and correction

- Opening card0–4 s uses the exact two C.2 opening sentences. Four exact slide-2 quotes hold3 s each at4–16 s. Title16–22 s. C.2 quotations align to their source cards; the unspoken third quote at10–13 s has an explicit transparent caption cue.
- The supplied outro window is42 s, while its stated10+12+8 s holds total30 s. Preserve the2:10–2:52 window and extend the three holds to12+16+14 s.
- A previous render lost three captions at22–41.67 s. Native PNG concat PTS and raster contents were correct. A/B36 s exports isolated filter-graph reinitialization when main-video SAR/colorspace/chroma metadata changed at the intro/raw boundary. Disabling base-input filter reinitialization preserved buffered caption frames. The final renderer includes `-reinit_filter 0`; the fresh final video passed every actual cue check. The earlier failed diagnosis receipt is explicitly marked invalidated and is not a final PASS receipt.
- No optional voiceover means no AAC stream. This uses the user's explicit instruction to ship silent with captions; no TTS or synthetic narration was introduced.

## Receipts and reproduction

- `track_c_ffprobe.json`: native video metadata.
- `track_c_video_facts.json`: final hash, byte size, input hash, timing, required-frame hashes.
- `track_c_caption_text_check.json`: direct comparison to supplied C.2 text.
- `track_c_captions.json` and `track_c_caption_script.txt`: editable exact caption text/timing.
- `track_c_overlay_check.json`: every actual caption midpoint/background/glyph check and requested PNG validation.
- `track_c_full_decode.json`: complete bitstream decode receipt.
- `track_c_production_contract.md` and `track_c_asset_manifest.csv`: production/asset contract.
- Reproduce: `python3 reports/final_v5/track_c_render.py`; then `python3 reports/final_v5/track_c_verify_export.py`. The renderer generates all local `demo/final_assets/` images/intermediates and refuses changed raw bytes or a newly supplied voiceover. No network, model, TTS, upload, or application runtime mutation occurs.

## Canonical state ledger

DRAFT=READY; ASSETS=READY; ASSEMBLY=COMPLETE; GENERATION=NOT_STARTED; RENDER=COMPLETE; HUMAN_ACCEPTANCE=PENDING; QA=PASS; EXPORT=VERIFIED; PUBLISH=NOT_REQUESTED.
