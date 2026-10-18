# Preflight final package v6

Report date: 2026-10-18, Asia/Seoul. **Tracks E, B authoring and C extension are complete. Track D awaits a human URL; final Track F remains scheduled. Repository publication receipts follow below after the content commit.** Track D waits for Felix's public YouTube URL and does not block other tracks. No submission form has been submitted.

| Track | State | Result |
| --- | --- | --- |
| E — unique upload file / inventory | DONE | New 3:28 upload copy + untouched 2:52 backup;12 files measured;9 original entries unchanged |
| B — official-template pitch deck | DONE for authoring/export/QA; public video link pending | 11-page PDF, 660,305 B; official template; every-page 50-dpi render; independent content/fidelity checks |
| C extension — official 3–4-minute submission video | DONE / INDEPENDENT QA PASS | 3:28.233;11,869,949 B;1920×1080/30fps/H.264; silent;2:52 backup unchanged |
| D — public YouTube link | WAITING FOR INPUT | No public URL; README/notes placeholders and deck pending field remain |
| F — last consistency pass | PRELIMINARY; final scheduled | 15 canonical rows, no conflicting value in the post-video snapshot; final after B+D or at 21:30KST |

## E — copy, original identity and inventory

The originally requested copy is now a **backup**, after Felix explicitly selected a new 3–4-minute submission video:

- Absolute path: `/Users/felix/Desktop/UPLOAD_THIS_Preflight_AIBC2026_2m52s.mp4`
- Duration: **172.000000 seconds / 2:52.000**
- Bytes: **8,109,690**
- SHA-256: `4bbe0168a40156c06718c53df736ecd90e2314b0539629bed0cc3fa947bdda03`
- Identical to `demo/preflight_demo_final.mp4`. Neither was changed, renamed or deleted.

The new selected submission copy is `/Users/felix/Desktop/UPLOAD_THIS_Preflight_AIBC2026_3m28s.mp4`: **208.233333 seconds**, **11,869,949 bytes**, SHA-256 `6ebd825cbe8cbc1810c81d9592ac4e21028340a4ed92dbafb840cd5d684703a2`. It matches `demo/preflight_demo_submission_3m.mp4` exactly.

The original recursive Desktop inventory found eight matching `*demo*.mp4` files plus the 2:52 upload copy. That dated inventory remains byte-identical. After new capture/export, a fresh full Desktop search exited0 with **10 matches**; the two uniquely named upload copies bring the final table to **12 files**. All 12 stat/ffprobe/streaming SHA checks passed. All 9 initial entries retain the same hashes and sizes. One 60-second search attempt timed out without publishing partial results; the subsequent complete search succeeded. Full hashes and measurements: `track_e_submission_inventory.md` / `.json`.

| Absolute path | Bytes | Native duration (s) | SHA-256 prefix (12) | Role |
|---|---:|---:|---|---|
| /Users/felix/Desktop/SK하이닉스 AI 해커톤 2026/preflight_demo_final.mp4 | 8109690 | 172.000000 | 4bbe0168a401 | 2:52 BACKUP — identical bytes to verified final |
| /Users/felix/Desktop/AI Builder Cup 2026/evidence/preview_v3_demo_before_v4_20261018_1121/preflight_demo_raw.mp4 | 8772303 | 108.533333 | 075c5e0b94ce | other demo — no verified version identity assigned |
| /Users/felix/Desktop/AI Builder Cup 2026/preflight/demo/preflight_demo_raw_before_v3_20261018_095707.mp4 | 10008012 | 114.366667 | a771a4690359 | old demo — measured duration and SHA prefix match supplied 10/17 identity |
| /Users/felix/Desktop/AI Builder Cup 2026/preflight/demo/preflight_demo_submission_3m.mp4 | 11869949 | 208.233333 | 6ebd825cbe8c | NEW SUBMISSION — 3:28.233 final |
| /Users/felix/Desktop/AI Builder Cup 2026/preflight/demo/preflight_demo_take_2.mp4 | 10008012 | 114.366667 | a771a4690359 | old demo — measured duration and SHA prefix match supplied 10/17 identity |
| /Users/felix/Desktop/AI Builder Cup 2026/preflight/demo/submission_supplement_v6/preflight_demo_own_prompt_raw.mp4 | 4579484 | 36.233333 | f58ce7ac0375 | New own-prompt production capture — source segment only |
| /Users/felix/Desktop/AI Builder Cup 2026/preflight/demo/preflight_demo_take_1.mp4 | 10085001 | 114.400000 | a5afe4ef56cf | other demo — no verified version identity assigned |
| /Users/felix/Desktop/AI Builder Cup 2026/preflight/demo/preflight_demo_raw.mp4 | 9300697 | 108.366667 | d1f3772d1187 | v4 raw — measured duration and SHA prefix match supplied identity |
| /Users/felix/Desktop/AI Builder Cup 2026/preflight/demo/preflight_demo_final.mp4 | 8109690 | 172.000000 | 4bbe0168a401 | 2:52 BACKUP — identical bytes to verified final |
| /Users/felix/Desktop/E/MAWD Challenge program overview/mawd-contract-total-cost/build/demo.mp4 | 176209 | 5.650000 | 47f7286c77f1 | other project — MAWD path; not a Preflight upload candidate |
| /Users/felix/Desktop/UPLOAD_THIS_Preflight_AIBC2026_2m52s.mp4 | 8109690 | 172.000000 | 4bbe0168a401 | 2:52 BACKUP — upload copy |
| /Users/felix/Desktop/UPLOAD_THIS_Preflight_AIBC2026_3m28s.mp4 | 11869949 | 208.233333 | 6ebd825cbe8c | NEW SUBMISSION — 3:28.233; explicit upload copy |


## B — organizer-template deck

Acquisition step **3** succeeded: existing signed-in Chrome → Hack2skill dashboard → Submissions → Template Download → public Google Slides → PPTX export. No new sign-in, password handling, clipboard read or form submission occurred. The first two acquisition routes were unavailable. Source: [official template](https://docs.google.com/presentation/d/13rg7vW43mEH6DkpuusAE6fdoEylSFz8waNpE4RLzoUg/edit).

| Artifact / check | Result |
| --- | --- |
| Original `docs/template/aibc_template.pptx` | 960,223 B; SHA-256 `29923ab726aa1382946c70ff527c769f0b9e95a55e889f2e01e7ad62641ea629`; unchanged |
| `docs/Preflight_pitch_deck.pdf` | **660,305 B; 11 pages; ≤5,000,000 B PASS** |
| PDF SHA-256 | `7f056e614806efd563daee155bd8a0c0f194bbbec64edd6557e77c61a401aef0` |
| Editable `docs/Preflight_pitch_deck.pptx` | 1,979,965 B; SHA-256 `00850a0a470aae3dbbc579e6cd22ed63748e10c7da247e8c2b4441bd60503a4a` |
| Page renders / text | 11/11 at 50 dpi,500×282px in `docs/deck_check/`; contact sheet and extracted text included |
| Visual review | Author + independent auditor inspected every page at 120 dpi; parent inspected all 11 final 50 dpi pages; no observed clipping, missing field, tofu or unintended overlap |
| Template fidelity | 2/2 master, 22/22 layout, 2/2 theme, 6/6 font parts unchanged; slide 1 non-text XML/geometry unchanged; all 5 original image resources unchanged |
| Architecture | Six native editable boxes, five native connectors; no new slide added |
| Number check | Author parser 22 unique tokens; independent broad parser 33 occurrences / 24 unique tokens; **0 unsupported newly authored Preflight quantities**, with exceptions below |
| Full user quotes | All 4 exact full quotes preserved; source labels retained |
| Saved stills | Two actual cached spoon/laptop stills; 2/2 HTTP200 hits; 0 image calls, $0.00; input bytes match prior saved stills |
| Finalizer | PASS; import 11 slides; 0 package/layout findings; 20 existing template-boundary warnings disclosed |
| Speaker-note provenance | Only 11 existing notes parts changed; no visible slide/resource change; inspected PDF byte-identical |
| README | Pending-export note replaced with actual PDF link |

All nine v5 content rows are mapped in order across the template's11 fixed content sections. The source template had16 slides. Download instructions, optional wireframe, optional implementation-cost, blank and non-content thank-you pages were omitted. No unauthorized estimate or slide was added. The exact v5 source is preserved in `CODEX_ONESHOT_preflight_final_v5.md`.

Numeric exceptions are explicit: native template page 11 retains **“3 Minutes”**; the live URL contains identifier digits **45**; the unchanged H2S brand image contains **2**. These are not new Preflight performance claims. The native duration label is retained template wording; actual submission duration comes from the new video measurement. The live form's3–4-minute requirement governs the selected new submission video.

Fonts in the original PPTX remain intact. The PDF embeds Google Sans Flex, Medium and SemiBold; Lucida Grande supplies only five right-arrow glyphs (four on page 5, one on page 8), with no body letters/digits in fallback. Fonts were registered only for the export session and then unregistered; no persistent font installation. The optional final-check screenshot was not added because required saved stills/diagram fill the available areas.

Detailed mapping, reproducible build/export, number exceptions and fidelity differences: `track_b_report.md`, `track_b_qa.json`, `track_b_independent_audit/REPORT.md`. Deck link field remains **Pending public upload** and does not establish submission readiness.

## C extension — submission video and rule resolution

The live [Hack2skill submission form](https://hack2skill.com/event/aibuildercup2026/dashboard/submissions/6a5da99a444e4f43e5657a85) says “3 to 4 minute” and labels the video link3–4minutes. Felix reported an explicit Oct16 written support answer confirming3–4minutes; that support email itself was not read in this turn. Felix explicitly selected the new3–4-minute version as the submission video. The previous2:52 file remains a backup. Target3:20; acceptable3:10–3:35.

One new production segment was recorded: own prompt → Check → actual Gemini rewrite/risk line → Preview limited message → What this score is. No added padding cards. The supplemental recording uses `scripts/record_demo.py`'s recording/interaction methods without editing that script or runtime. The segment goes immediately after the saved-still beat near 1:20. Felix confirmed 1:40 as the extra new-segment check; 2:20 remains an extra clip-review check. Required new frame times: 0:05, 1:10, 1:40, 2:20, 3:00.

The new submission export and independent visual/automated QA are complete. Felix will inspect the local video before uploading.

| Metric / check | Result |
| --- | --- |
| Final MP4 | `demo/preflight_demo_submission_3m.mp4` |
| Upload this Desktop copy | `/Users/felix/Desktop/UPLOAD_THIS_Preflight_AIBC2026_3m28s.mp4` |
| Duration | **208.233333s /3:28.233**; approved190–215s range PASS |
| Bytes | **11,869,949**, identical Desktop copy |
| SHA-256 | `6ebd825cbe8cbc1810c81d9592ac4e21028340a4ed92dbafb840cd5d684703a2` |
| Native video | 1920×1080;30fps;H.264/yuv420p;6,247frames |
| Audio | None; no voiceover supplied; silent fallback; loudness N/A |
| Added production footage | Full36.233333s, inserted80.000–116.233333s, no trimming; existing cards not extended |
| Existing 2:52 video / copy | Both remain SHA-256`4bbe0168a40156c06718c53df736ecd90e2314b0539629bed0cc3fa947bdda03` |
| Own typed prompt | `a dog catching a frisbee on a beach at sunset` |
| Actual rewrite | `rewrite_source=live`;13.3%original→3.3%rewrite readable in footage; distinct from spoon/laptop example |
| Recorded requests | One `/preflight` HTTP200; one `/preview` HTTP503 with exact limited message;0pageerrors/0requestfailures |
| Text model calls | Response trace reports3planner+1rewrite=4; not provider billing verification |
| Image / Veo calls | 0/0; typed-preview source guard + actual network response; billed spend remains UNMEASURED |
| In-app counter before / after | **NOT SHOWN / NOT SHOWN**; no such visible usage counter |
| Status field before / after | `generations:0`→`0`, hardcoded in source; **not metering evidence** |
| Captions | Original33cues (32active+1blank) retained exactly;3new number-free cues;36total/35active;43 px, max 1 line |
| Independent automated + visual checks | Full decode PASS;35/35 actual burned-caption midpoints PASS ; 9 preserved-beat sample comparisons PASS; all 8 action/check frames and 3 new caption midpoints visually inspected PASS |
| Parent visual review | All8 exported check frames inspected, including live rewrite, limited message, score explanation, clip review and limits |

Frame checks: `demo/submission_check_v6/00m05s.png`, `01m10s.png`, **`01m40s.png`** (new segment), `02m20s.png` (clip review), `03m00s.png`; extra `01m35s.png` (full live rewrite), `01m42s.png` (limited preview), `01m50s.png` (expanded explanation). The contact sheet is in the same folder. The original six 2:52 check frames remain unchanged in `demo/final_check/`.

The three new captions are exactly:

- “Your own prompt gets a live Gemini rewrite too.”
- “Live stills are limited to the samples during judging, and the page says so.”
- “Every number comes with what it is and what it is not.”

No new caption states a number. UI numbers are captured from the actual production response. The status field is explicitly not a cumulative counter; 0 image calls is a request-path finding, not a claimed counter or measured billing total. Source capture, reproducible assembly, native identity and independent checks are in `track_c_supplement_capture.json`, `track_c_render_submission.py`, `track_c_submission_video_facts.json` and `track_c_independent_audit/`. Felix's full-video acceptance remains pending.

## D — public links

**WAITING FOR FELIX'S PUBLIC YOUTUBE URL.** No upload was performed. `<VIDEO_URL>` remains in README and `docs/submission-notes.md`; deck page 11 explicitly awaits the URL. When supplied, use the new submission-video duration, not the 2:52 backup, for the anonymous public/private/unlisted and duration check. Update the deck pending link before 21:00 if a URL arrives, using the preserved editable deck and the same render/font checks.

Brief description is **952/1,024 characters**, unchanged. Exact supplied YouTube title/description plus the selected 3:28 upload path/hash are in `youtube-upload-handoff.txt`; the original supplied copy remains in `reports/final_v5/youtube-upload-copy.txt`.

## F — shared-value table (post-video preliminary snapshot)

Observed **17:55:41 KST** after the completed deck/new submission video and independent video QA. **This is preliminary, not the required final pass.** The initial 17:35 and post-deck 17:45 receipts remain unchanged. A one-time final check in this chat is scheduled for **21:30 KST**, or can run earlier after B+D. It uses the selected 3:28 video metadata/captions, reads the latest human messages, and stops by 22:00. Track D is still pending.

| Value | Surfaces where it appears | Required but missing | Expected absence / scope caveat | Conflicting canonical value |
| --- | --- | --- | --- | --- |
| Live URL: https://preflight-jcgro45veq-as.a.run.app | README (3,62,74): full URL; architecture link appends /architecture [literal]; notes (3): full URL [literal]; deck (pages 11): Live URL: https://preflight-jcgro45veq-as.a.run.app [literal / whitespace normalized]; actual selected MP4 (3:20 closing card): preflight-jcgro45veq-as.a.run.app; destination matches full URL [semantic destination] | None | caption scripts: URLs appear in closing visual, not frozen C.2 narration; status response: endpoint does not echo its own origin | None found |
| Repo URL: https://github.com/testofschool/preflight | notes (5): full URL [literal]; deck (pages 11): Repo URL: https://github.com/testofschool/preflight [literal / whitespace normalized]; actual selected MP4 (3:20 closing card): github.com/testofschool/preflight; destination matches full URL [semantic destination] | None | README: no self-link required by v5; caption scripts: URLs appear in closing visual, not frozen C.2 narration; status: no repository metadata field | None found |
| Video URL | README (3): <VIDEO_URL> placeholder [literal]; notes (7): <VIDEO_URL> placeholder [literal]; deck (page 11): Pending public upload [waiting placeholder] | README, notes and deck page 11: actual public YouTube URL of the 208.233333-second submission file pending Felix / Track D | v5 and v6 caption scripts, actual MP4 and status: no self-referential public-video URL field required | None found |
| 1,911 | README (25,207): 1,911 human pairwise votes [literal]; notes (9): 1,911 human pairwise votes [literal]; v5 caption script (3): 1,911 human votes [literal]; deck (pages 2,4,6,7): 1,911 [literal / whitespace normalized]; v6 full caption script (7): Preflight compares it with 1,911 human votes on earlier AI videos [literal / semantic]; actual selected MP4 (0:29 caption; 1:50 captured explanation; 2:50 architecture): 1,911 [literal] | None | status: no dataset-count field | None found |
| 0.67 | README (66): held-out risk AUC 0.67 [literal]; notes (9): held-out AUC 0.67 [literal]; v5 caption script (9): held-out AUC 0.67 [literal]; deck (pages 9): 0.67 [literal / whitespace normalized]; v6 full caption script (31): The risk score is a historical signal, held-out AUC 0.67, [literal / semantic]; actual selected MP4 (1:50 captured explanation; 3:04 limits card and caption): 0.67 [literal] | None | status: no evaluation-metric field; README also preserves precise five-seed 0.668329 and target 0.68. They are labeled distinct values; 0.67 is rounded, not conflicting. | None found |
| 46.8% | v5 caption script (3): 46.8 percent [semantic]; deck (pages 8): 46.8% [literal / whitespace normalized]; v6 full caption script (9): For "a spoon and a laptop", the estimate is 46.8 percent. [literal / semantic]; actual selected MP4 (0:45 spoon/laptop UI and caption): 46.8%; 46.8 percent [literal / semantic] | None | README and notes: demo-specific risk pair not mandated by v5; status: no risk-example field; The preserved spoon/laptop example is the mixed proxy 46.8% -> 15.8%; original historical-only 53.5% remains labeled separately. New own prompt dog/frisbee is 13.3% -> 3.3%, so it is not a conflicting value for the spoon example. | None found |
| 15.8% | v5 caption script (4): 15.8 percent [semantic]; deck (pages 8): 15.8% [literal / whitespace normalized]; v6 full caption script (12): Here it drops to 15.8 percent. Copy it and go. [literal / semantic]; actual selected MP4 (0:58 spoon/laptop rewrite UI and caption): 15.8%; 15.8 percent [literal / semantic] | None | README and notes: demo-specific risk pair not mandated by v5; status: no risk-example field; New own-prompt rewrite 3.3% belongs to a different dog/frisbee prompt, not the canonical spoon/laptop rewrite. | None found |
| $3.20 / three dollars | README (227): USD 3.20; eight seconds at USD 0.40/second [currency-format semantic]; v5 caption script (5): about three dollars [approximate semantic]; status (/pricing/single_attempt_usd): 3.2 [numeric semantic]; deck (pages 4): $3.20 / three dollars [literal / whitespace normalized]; v6 full caption script (13): Before paying about three dollars for an eight-second video, [literal / semantic]; actual selected MP4 (1:02 caption; 1:35 captured UI price basis): about three dollars; illustration using $3.20 per 8s attempt [approximate / literal] | None | notes: example Veo-attempt price not mandated by v5; Single-attempt price is $3.20 / status numeric 3.2. Frozen about-three-dollars caption is an approximation. New UI $3.69 is a separately labeled illustrative total budget at the own-prompt 13.3% risk; old sample UI $6.01 is also a total-budget illustration, not the per-attempt price. | None found |
| 8/20 | README (29,69): best probe P1 8/20; P2/P3 6/20 [literal]; notes (13): P1 8/20; P2/P3 6/20 [literal]; deck (pages 9): 8/20 [literal / whitespace normalized]; actual selected MP4 (3:00 and 3:04 limits card): Best 8/20 [literal visual card; not narration] | None | caption scripts: frozen v5 C.2 says live generation failed too often without counts; status: no probe-result field | None found |
| Gemini 3.5 Flash | README (37,55,139,163): Gemini 3.5 Flash [literal]; notes (9): Gemini 3.5 Flash [literal]; deck (pages 6,7): Gemini 3.5 Flash [literal / whitespace normalized]; actual selected MP4 (2:50 architecture card): Gemini 3.5 Flash [literal visual card; not narration]; new capture receipt (preflight_response.agent_trace.model): gemini-3.5-flash [model-code semantic] | None | caption scripts: frozen v5 C.2 says Gemini without version; status: gemini=true flag; rewrite model name not exposed; Fresh /api/status does not expose the rewrite model. The authorized captured request trace identifies gemini-3.5-flash. pricing_image.model=gemini-2.5-flash-image and pricing.model=Veo 3.1 describe different roles. | None found |
| Google ADK | README (38,54,162): Google ADK [literal]; notes (9): Google ADK [literal]; v5 caption script (4): Google ADK agent [literal]; status (/adk): true [service-flag semantic]; deck (pages 6,7): Google ADK [literal / whitespace normalized]; v6 full caption script (10): Then a Google ADK agent on Gemini rewrites the prompt [literal / semantic]; actual selected MP4 (0:50 original caption; 2:35 live architecture; 2:50 card): Google ADK [literal] | None | None | None found |
| Agent Platform Sessions | README (39,44,56,138,165): Agent Platform Sessions [literal]; notes (9): Agent Platform Sessions [literal]; v5 caption script (7): Agent Platform Sessions [literal]; status (/agent_platform_session): true [service-flag semantic]; deck (pages 6,7): Agent Platform Sessions [literal / whitespace normalized]; v6 full caption script (27): Gemini on Vertex AI, an ADK agent with Agent Platform Sessions. [literal / semantic]; actual selected MP4 (2:42 caption; 2:50 architecture card): Agent Platform Sessions [literal] | None | None | None found |
| Cloud Run | README (35,44,52,141,161,170,263): Cloud Run [literal]; notes (9): Cloud Run [literal]; v5 caption script (7): Cloud Run [literal]; status (/cloud_run): true [service-flag semantic]; deck (pages 6,7): Cloud Run [literal / whitespace normalized]; v6 full caption script (26): Everything runs on Google Cloud: Cloud Run, Firestore, [literal / semantic]; actual selected MP4 (2:35 caption and live architecture; 2:50 card): Cloud Run [literal] | None | None | None found |
| Firestore | README (36,41,53,59,137,164,174,178,199,207,261,271): Cloud Firestore / Firestore [literal]; notes (9): Cloud Firestore [literal]; v5 caption script (7,8): Firestore [literal]; status (/firestore): true [service-flag semantic]; deck (pages 6,7): Firestore [literal / whitespace normalized]; v6 full caption script (26,29): Everything runs on Google Cloud: Cloud Run, Firestore,; tools for evidence and difficulty, Firestore as memory. [literal / semantic]; actual selected MP4 (2:35 caption and live architecture; 2:50 card): Firestore / Cloud Firestore [literal] | None | None | None found |
| samples: Active for sample prompts (saved stills); live generation limited | README (27): exact wording [literal]; notes (11): exact wording [literal]; v5 caption script (5): five sample prompts use saved stills; zero model calls; live generation failed too often [semantic]; status (/preview_mode and /preview_mode_message): samples; exact wording [literal]; deck (pages 7): samples: Active for sample prompts (saved stills); live generation limited [literal / whitespace normalized]; v6 full caption script (15,20): For judging, the five sample prompts use saved stills:; Live stills are limited to the samples during judging, and the page says so. [literal / semantic]; actual selected MP4 (1:35 captured mode label; 1:42 limitation message and added caption): Active for sample prompts (saved stills); live generation limited; own-prompt 503 limited copy [literal UI / semantic caption] | None | Zero model calls refers to saved sample stills. The new own-prompt rewrite is live Gemini text work; its still-preview request is rejected with real HTTP503. No visible usage counter exists, and status.generations is hard-coded zero, so 0->0 is not cumulative accounting. | None found |

Current README contains the PDF link and its target exists. Brief description: **952/1,024 characters**. Deck remains 11 pages / 660,305 bytes, SHA-256 `7f056e614806efd563daee155bd8a0c0f194bbbec64edd6557e77c61a401aef0`.

The new own-prompt 13.3% → 3.3% result, the preserved spoon/laptop mixed 46.8% → 15.8% result, and the spoon historical-only 53.5% estimate are separately labeled contexts. Likewise $3.69 is the new illustrative total budget; $3.20 is its disclosed per-attempt input. Neither is a canonical conflict.

No runtime, production documents, cloud settings, tags or history were changed by this audit; no production POST or model request was made. Only a GET of `/api/status` was performed. Previous 17:35 and 17:45 F snapshots remain unchanged.

## Scope, prior completed tracks and anything not done

- Prior Track A evidence remains in `reports/final_v5/REPORT.md`: revision `preflight-00027-pit`, 100% traffic, 500/day, 5/min, 94 offline tests, unchanged image; no fresh runtime test or deployment is implied by this docs/media package.
- Runtime source, image, Cloud Run settings, all three Git tags and existing history are frozen. New recording may call the explicitly authorized Gemini text rewrite, but image generation and Veo are prohibited. The captured response reports 3 planner + 1 text rewrite calls, with 0 image and 0 Veo calls; no billed-spend estimate is invented.
- Submission-video export, independent QA, parent selected-frame review and refreshed 12-file inventory complete. Full-video acceptance by Felix is pending.
- Public YouTube upload, URL replacement, public visibility/duration validation: NOT DONE, human URL pending.
- Final Track F: NOT DONE yet; scheduled 21:30 or after B+D.
- No voiceover is present; the selected submission video is silent with burned captions. Felix has not yet confirmed full-video acceptance.
- Clip-review accuracy and actual billed spend remain unmeasured.

## Commits and public verification

Baseline public main: `a993aa5c4986b564cb9d379d657112d5ad7494a0`. V6 content/receipt commits and exact-head secret/history/anonymous-clone checks will be appended after the content commit. No future commit is claimed as already scanned.

Prepublication scope check: **25/25 runtime files unchanged**, record_demo script unchanged, **3/3 fixed tags unchanged**, original raw and 2:52 backup hashes unchanged, new submission/copy identity matches, **0 dataless files** (`runtime_scope_final.json`). Native read-only production receipt at 17:51 KST confirms revision `preflight-00027-pit` 100%, same image, daily 500, live=false, warm=false (`production_read_only.json`). No runtime tests were rerun for this docs/media-only change.

Prepublication worktree/index guard: **0 marker hits, 0 errors**, complete (1,020 working-tree files;840 then-indexed files). The first attempt flagged one public Git commit verification signature in ignored font-download metadata. It was classified without printing the signature and preserved outside the repository; original guard rules and all font/deck/runtime inputs were unchanged. Both the initial result and successful recheck are recorded in `secrets_prepublication_initial.json`, `secrets_public_metadata_classification.json` and `secrets_prepublication.json`. This was not a discovered private credential. The commit hook will inspect the final staged set again.
