# Track I independent review

**PASS — reviewed compact v4 candidate.**

`demo/submission_supplement_v7/submission_candidate_v4.mp4`  
SHA-256: `710146243d0a87c9cb3195a3d21f1ba8fd7070d95936a27e65da093358e42565`  
11,708,270 bytes; 1920×1080; silent H.264 High / yuv420p; 30 fps; 3:28.233; 6,247 frames.

| Gate | Independent evidence | Result |
|---|---|---|
| Full decode | Fresh strict FFmpeg decode of both candidate and v6 baseline: 6,247 frames each; exit 0; no errors | PASS |
| Outside the replacement interval | All 5,160 decoded YUV frames outside frames 2400–3486 compared; **0 changed** | PASS |
| 1:30 Better prompt | Fresh v4 frame: full rewrite and 13.3% → 6.7% risk line clearly visible in the horizontally centered card | PASS |
| 1:45 limited message | Fresh v4 frame: complete real message readable in the centered card, without clipping or caption overlap | PASS |
| Frozen captions | Cue JSON and script byte-identical; all 35 active cues checked across 6,157 captioned frames, including every first/last frame | PASS |
| Zero image calls for the new preview request | Captured real `/preview` HTTP 503 in samples mode, plus verified pre-provider source guard | SUPPORTED |

The fixed replacement is frames 2400–3486: 80.000–116.233333 s. All 1,087 inserted frames differ from v6 as expected. The original baseline SHA is `6ebd825cbe8cbc1810c81d9592ac4e21028340a4ed92dbafb840cd5d684703a2`. Fresh hashes were generated independently; author hash manifests were not reused.

Caption verification compared the expected frozen PNG's opaque white text cores to each actual decoded caption frame. The minimum recall was 99.9325%, with zero frames below the 98% gate. This includes exact insertion transitions at frames 2400, 3042, 3264 and 3487. The remaining 90 frames are the frozen blank cue. Target frames were also read manually. This checks glyph presence and timing; it is not a general OCR or semantic-fact audit.

The actual new production rewrite is “A golden retriever jumps to catch a red plastic disc on a sandy beach during a vibrant sunset, wide shot, slow motion.” Its 13.3% → 6.7% result is separately identified from the prior v6 stochastic response; inserted captions contain no risk numbers.

The capture's real non-sample `/preview` request returned 503 with “Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works.” Samples mode was recorded before and after. The matching `app.py` source rejects that request at lines 259–260 before `provider.generate` at line 285. `/api/status.generations` is hard-coded 0 at line 194 and was excluded as accounting evidence. No provider billing audit or replay request was performed.

The two earlier candidates remain recorded as **FAIL**: SHA `d75431b6…` (45,315,486 bytes) and SHA `d9f54b09…` (45,305,584 bytes) each changed 2,749 of 5,160 outside frames. Fresh independent decodes confirmed both failures. Those results were retained, not waived; compact v4 resolved the exact-frame gate.

This reviewer wrote only this Markdown/JSON report pair and did not modify capture, video, source, runtime or Git state. Final-path and Desktop-copy installation were not checked at report time; their hashes must match the reviewed candidate above.
