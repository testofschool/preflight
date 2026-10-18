# Preflight final v7 — H / I / J receipts and G fallback decision

Updated 2026-10-18T18:58:35.086521+09:00. User order: **H → I → approved J → G**. J approval and cross-chat coordination were verified from Felix's actual user messages in “Check preflight allowance”. No submission has been made.

**Selected submission deck: v6 fallback.** G failed the isolated visual gate after its one permitted correction round. Its corrected candidate passes the independent technical checks, but that is not an overall G pass. The v7 candidate and both complete visual reviews are preserved below and separately. Track D is deliberately waiting for Felix's uploaded-video URL. Track F remains due after D or at 21:30 KST.

| Track | State | Result / remaining work |
|---|---|---|
| H — privacy | PASS, committed/pushed | `8301158450c262848d9e575dd670a1203d229e78`; twenty path replacements, old handoff untracked and kept locally; NFC/NFD HEAD grep0; anonymous clone PASS |
| I — video framing | PASS, installed and evidence pushed | `8d155f0c0f15db2513df294cb09f7999c57e5dff`; 208.233333 s; 11,708,270 B; SHA `71014624…e42565`; all 5,160 outside frames identical; caption/decode/framing PASS; zero image/Veo calls in I |
| J — approved limit increase | PASS, separately executed | Source `59fb23b262af480709461b648e84d26010e26060`; evidence `246b176763b6ace5af426939431566e09d1f925a`; v4 tag; production `preflight-00029-teb` at 100%; configured allowance3,000 |
| G — image-led deck | FAIL; v6 fallback selected | Round1:5 PASS/7 FAIL; one correction; round2:6 PASS/6 FAIL. Technical checks PASS only. No second correction or unsupported promotion. |
| D — YouTube link | WAITING, by user design | No URL supplied; README/notes placeholders and deck pending field remain. Public visibility and duration UNVERIFIED. |
| F — final consistency | PREPARATION ONLY | Final fifteen-row pass after D or at21:30; existing one-shot heartbeat updated to this v7 chat and post-J baseline. Missing public URL is not a passed equality check. |

## H — privacy evidence

Only path text changed in seven historical report/inventory files. Twenty full absolute paths were replaced with `<other local folder, not part of this project>`. These receipt files intentionally have new file hashes; numerical video metadata is preserved. `reports/final_v6/CODEX_ONESHOT_preflight_final_v5.md` was removed from Git's index, retained locally, and excluded locally from future staging. History was not rewritten.

HEAD grep uses UTF-8 patterns over stdin, avoiding macOS argument-normalization ambiguity. Query labels identify the two supplied external-folder targets without reintroducing their names into HEAD:

```text
Target A, NFC: 0 matching lines; git grep exit 1
Target A, NFD: 0 matching lines; git grep exit 1
Target B, NFC: 0 matching lines; git grep exit 1
Target B, NFD: 0 matching lines; git grep exit 1
```

- Commit/push: `8301158450c262848d9e575dd670a1203d229e78` on public `main`.
- Anonymous clone: same complete SHA; public repo and raw README HTTP200; credentials/global/system config/hooks disabled; runtime frozen digest and all fixed tags match; PASS.
- Reachable-history marker scan: nineteen commits, 881 blobs; zero hits; complete; zero errors; PASS. This is a fixed-pattern secret check.
- Runtime: all twenty-five frozen files unchanged. No cloud configuration, runtime image, limit, tag or history mutation.
- Receipts: `track_h_changes.json`, `track_h_head_grep.json`, `track_h_anonymous_clone.json`, `track_h_history_scan.json`, `scope_after_h.json`.

## I — final corrected upload

Installed 2026-10-18 18:26:41 KST, with root independently rehashing both copies before J starts.

| Fact | Result |
|---|---|
| Desktop upload | `/Users/felix/Desktop/UPLOAD_THIS_Preflight_AIBC2026_3m28s.mp4` |
| Selected project video | `demo/preflight_demo_submission_3m.mp4` |
| Duration | **208.233333 seconds / 3:28.233** |
| Bytes | **11,708,270** |
| SHA-256, both copies | `710146243d0a87c9cb3195a3d21f1ba8fd7070d95936a27e65da093358e42565` |
| Format | H.264 High, yuv420p,1920×1080,30fps,6,247 frames,no audio |
| Framing | Native production page-scale2 capture; Better prompt with complete rewrite/risk line centered at1:30; actual limited message centered at1:45; root and independent visual PASS |
| Full decode | Author and independent fresh decode PASS,0 errors |
| Outside replaced segment | Frames0–2399 and3487–6246: **5,160 compared,0 changed**, independently reproduced |
| Captions | v6 cueJSON/script byte-identical;36 entries,35 active;all6,157 captioned frames pass actual-burn check;90 blank frames accounted for |
| Model calls | **0 image calls,0 Veo calls**;real single typed check and text rewrite retained;actual non-sample preview503 rejected before provider dispatch;status.generations is not used as cumulative accounting |
| Old videos |15 originals unchanged;both replaced targets preserved in before-v7 backups;no video deleted |
| Actual new own-prompt result |13.3%→6.7%, from the new live text response;distinct from v6's3.3% rewrite and the preserved spoon/laptop46.8%→15.8% example |

Only the inserted80.000–116.233333-second production segment was replaced. Final assembly copies compressed original pre/post segments at their exact keyframe boundaries and encodes only the new1,087-frame insert. Two earlier predictive lossless exports failed strict pixel equality and remain retained with explicit FAIL receipts. An all-intra diagnostic passed but was not selected because of its903,326,846-byte size. The selected compact export passed every required gate; no failed export was installed.

Receipts: `track_i_completion.json`, `track_i_REPORT.md`, `track_i_video_facts.json`, `track_i_qa.json`, `track_i_parent_visual_review.json`, `track_i_independent_review.md` / `.json`, `track_i_v6_decoded_yuv420.framemd5`, `track_i_v7_v4_decoded_yuv420.framemd5`. Reproducible capture/final assembly/install scripts are saved alongside. Raw clips/browser recordings remain local.

## J — approved separate execution and root confirmation

Felix explicitly approved the exact bounded J work and direct coordination in “Check preflight allowance”; root read those actual user messages before coordinating. J finished at18:37:58 KST and released Git ownership after its evidence commit.

- Source commit:`59fb23b262af480709461b648e84d26010e26060`;annotated source tag:`aibc-2026-submission-v4`.
- J evidence commit:`246b176763b6ace5af426939431566e09d1f925a`;public report:`reports/track_j/REPORT.md`.
- Production:`preflight-00029-teb`,100% traffic;read-only18:39:41 KST snapshot206 used/3,000 limit,2,794 remaining.
- Full suite:201 tests+11 subtests PASS;gate5 HTTP attempts,exactly2 admitted cumulative checks,no retries.
- Native Git/archive runtime hashes both`5ecfefe996dd08ef9dc9fe4bdc38e7dc735e28c487018a426fb6521918e88a21`;image`sha256:335aa2ed7565f80a2b0e491fe1138c4e09f6362acb1099e30d8b3acc3a4b0d8a`.
- Runtime diff:only the ceiling comparison1,000→3,000;one existing test adjusted. Default1,000,rolling20/minute,and old invalid-config rejection wording preserved per the authorized scope.
- Root freshly recomputed all25 runtime file hashes and read native service/revision/image/env plus `/api/status` after J. PASS;0 production POSTs. Baseline:`post_j_scope_baseline.json`. G/D/F must preserve this approved new baseline and all four tag targets.
- README cap/default prose is reconciled in exactly three places;submission notes have no affected allowance statement. This documentation change is part of F reconciliation, not a further runtime change.

## G — corrected candidate checks and fallback selection

The corrected v7 candidate was frozen before both independent audits. PDF: **12 pages, 916,424 bytes**, SHA-256 `0695c9768a0881349197ccbc53b0e614d1f2161f4083e4eddc093be804c49610`. PPTX: **2,715,215 bytes**, SHA-256 `588f2f9aed4b7e3df9c5bb2edcd84e7748f603e14e2102b6559cf0a7614fb184`. It is retained under `candidate_v7/Preflight_v7_FAILED_G.pdf` and `.pptx`, rather than shipped. The review paths below identify where these exact candidate bytes were located during review.

The submission paths `docs/Preflight_pitch_deck.pdf` and `.pptx` are restored to the exact v6 fallback: **11 pages, 660,305 bytes**, PDF SHA-256 `7f056e614806efd563daee155bd8a0c0f194bbbec64edd6557e77c61a401aef0`; PPTX SHA-256 `00850a0a470aae3dbbc579e6cd22ed63748e10c7da247e8c2b4441bd60503a4a`. The fallback does not claim to satisfy the new image-led G rubric. It is the fallback expressly requested by Felix.

All candidate pages were rendered at50dpi to `docs/deck_check_v7/`. That directory remains failed-candidate evidence, bound to the v7 PDF hash above. All26 original master/layout/theme parts, six embedded-font parts, five original media parts and the cover XML remain byte-identical. Four PDF font subsets are embedded; LucidaGrande supplies only three arrow glyphs. The independent technical audit reports zero remaining technical failures.

| Candidate page | Headline words | Body words | Main visual % | Actual raster % | Native numbers / identifiers | Banned hits | Generated model | Technical gate |
|---|---:|---:|---:|---:|---|---:|---|---|
| 1 | 0 | 24 | template | template | none | 0 | not generated | PASS (template) |
| 2 | 7 | 18 | 41.92 | 41.92 | 2024, 21%, 1,911 | 0 | UNREPORTED | PASS |
| 3 | 5 | 22 | 40.77 | 0.00 | 1.1/5, 340, 219 | 0 | not generated | PASS |
| 4 | 5 | 22 | 41.38 | 41.38 | 1,911, 3.20 | 0 | not generated | PASS |
| 5 | 4 | 14 | 42.66 | 42.66 | 1, 2, 3, 4 | 0 | not generated | PASS |
| 6 | 5 | 15 | 43.00 | 0.00 | none | 0 | not generated | PASS |
| 7 | 4 | 24 | 44.12 | 0.00 | 3.5 | 0 | not generated | PASS |
| 8 | 6 | 20 | 41.26 | 41.26 | 46.8%, 15.8% | 0 | not generated | PASS |
| 9 | 5 | 25 | 50.43 | 0.00 | 0, 0.67, 8/20, 0.00, 60 | 0 | not generated | PASS |
| 10 | 8 | 25 | 46.70 | 40.94 | 10, 6, 2.5, 30, 18, 23, 7 | 0 | not generated | PASS |
| 11 | 4 | 23 | 41.92 | 41.92 | 46.8%, 15.8%, 3.20 | 0 | UNREPORTED | PASS |
| 12 | 0 | 5 | template | template | 3, 45 | 0 | not generated | PASS (template) |

Source/asset attributions and unchanged template labels are excluded from authored word budgets; all explanatory caveats are included. Real screenshot text is product evidence. Main visual area is a union mask on the50dpi render, with overlaps counted once and headers/footers excluded. Native workflow/architecture/chips/metric-card regions were explicitly requested by the map and are reported separately from raster pixels. For slides5 and10, actual pictures alone exceed40%; blank card backgrounds do not count. Unsupported quantitative tokens0; model identifier3.5, requested process ordinals1–4, unchanged template3 Minutes, and URL digits45 are separately inventoried identifiers.

Two concept images were generated with the built-in image tool; both model names returned **UNREPORTED**. Both were inspected for text/logos/faces and used only for concept slides. Product UI generation0; Veo calls0. Existing real product screenshots and saved stills supplied all product evidence. The rewrite still was faithfully cropped to remove its logo; the original apparent edge was retained rather than altered. Actual original before-QA viewport evidence was unavailable; archival/current header crops do not prove the logged object/colour counts. This limitation contributed to the visual failure.

The first review failed. The single consolidated correction resolved word budgets and several clarity/area issues, but the second review still failed. Text-only chips/cards match the requested map; their technical inclusion did not override the fresh visual reviewer. The missing video link belongs to pending D, and independent remaining visual failures also prevent G promotion. No more visual correction round was attempted.

Detailed production/fidelity/provenance: `track_g_REPORT.md`, `track_g_independent_fidelity.md/.json`, `track_g_assets.json`, `track_g_qa.json`, `track_g_concept_images.json`, `track_g_selection.json`.

### Isolated visual review — round1, verbatim

# Isolated PDF visual review — round 1

**Overall verdict: FAIL.**

Reviewed only `/Users/felix/Desktop/AI Builder Cup 2026/preflight/docs/Preflight_pitch_deck.pdf`. I read the PDF text and rendered every page at presentation scale; I also inspected slide 8 at higher resolution. I did not read the PPTX, source, reports, author notes, other artifacts, or other reviewers' work. No deck edits were made.

**PDF SHA256:** `88d9807dd8016803f05826f0a62953b04538b6760600528b791d06973cc72c4a`

The problem and intervention are understandable: people pay for AI-video attempts before discovering unusable results; Preflight checks a prompt and proposes a rewrite before payment. The deck does not yet make the strength of that value trustworthy enough. The strongest comparison visually suggests proven improvement, the benchmark lacks a defined live-image success outcome, the QA comparison does not depict the measurements it accompanies, and the demo link is absent.

## Slide-by-slide verdicts

| Slide | Verdict | Candid reason |
|---|---|---|
| 1 — Team Details | **PASS** | The team and problem are readable within 30 seconds. The competition branding occupies much of the slide, but this is recognizable template branding, not an image artifact. The problem sentence is concrete. |
| 2 — Brief about the idea | **PASS** | “You pay first. You find out later.” and the two user quotations make the pain immediately understandable. The film-and-coins concept image is clean and supports the payment metaphor. It looks staged/generated, but I do not see a cheap text artifact or accidental logo. The historical vote figure is visibly identified as historical context, not a product result. |
| 3 — Opportunities | **PASS** | The timeline clearly places Preflight between Prompt and Pay. That graphic communicates the opportunity without requiring every word of the source line. It is plain and box-heavy, but the arrows and intervention marker carry meaning. The allowed review/vote figures do not themselves establish willingness to pay; the slide does not explicitly claim that they do. |
| 4 — Features | **PASS** | The three panels communicate risk, rewrite, and a still before video payment. “Historical, uncalibrated” and “A still does not test motion” materially limit the promise. The product crops are soft and some fine print is too small for a presentation, but the large risk number and captions communicate the slide's role. The still is an illustration, not proof that a video will succeed. |
| 5 — Process | **FAIL** | The four-stage sequence is understandable from the large labels, but the explicitly requested numbered process thumbnails are not present: I see four labeled panels with no visible step-number badges. The screenshot body text is also too small/soft to serve as readable evidence of the “why” and rewrite. This is close to a usable process slide, but it does not meet that stated map requirement as rendered. |
| 6 — Architecture | **PASS** | The browser, backend, rewrite agent, persistence, and prompt/IRT nodes are legible, and the arrows convey a useful architecture relationship. This is a text-based diagram, but it has actual relational structure rather than a paragraph disguised as a picture. “Traceable” is asserted, not demonstrated through a trace example; that is a limitation, not a new measured result. |
| 7 — Technologies | **FAIL** | This is entirely service names inside large empty grey rectangles. Text dominates the slide; there is no meaningful picture or diagram explaining the services' jobs. A stranger can repeat the stack names but gains little understanding of how those technologies create the promised value. “Gemini 3.5 Flash (Vertex AI)” is correctly treated as a technology identifier, not an extra performance quantity. |
| 8 — Prototype snapshots | **FAIL** | The images and enormous 46.8% / 15.8% labels create a strong before/after success impression, while the qualification says the score is uncalibrated and the still cannot judge motion. Those images do not validate reduced video failure. Closing the laptop also simplifies/changes the scene, so the visual is not a controlled demonstration of the original video intent improving. The right laptop has a conspicuous white Apple-like logo/mark; this is inside the image, separate from intentional competition branding. The left spoon also has a thin doubled/stray-looking edge beneath the handle. |
| 9 — Performance/benchmarking | **FAIL** | “8/20 best live image result” does not say what counted as a success, and “60 calls” directly underneath does not explain how it relates to that denominator. A reader cannot interpret the live-image result honestly in 30 seconds. The saved-still wording limits the $0.00/0-call claim, but the slide still needs to distinguish replaying an existing still from generating one. The big number cards are text-led; the historical-AUC and unmeasured-clip caveats are useful but do not resolve the undefined live metric. |
| 10 — Team and development | **FAIL** | “QA 10, 6 shipped” does not name what was counted. The before/after header crops look almost the same at this size, and the footer expressly says they are not the samples used for the object/colour counts. Placing “Objects 30 → 18. Colours 23 → 7.” immediately below those crops nevertheless invites that inference. The slide supplies allowed numbers, but its visible comparison does not substantiate the improvement it appears to show. The large F/S cards are mostly text and empty space. |
| 11 — Point–Reason–Example–Point | **FAIL** | The payment value is memorable and the clapperboard image is visually clean, with no accidental text or logo apparent. However, the central example now repeats 46.8% → 15.8% without calling those numbers an uncalibrated estimate on this slide. Coupled with “Know before you pay,” it presents a stronger certainty than the evidence described earlier supports. A lower prompt score and a saved still do not establish that the paid video will be usable. |
| 12 — Links | **FAIL** | The repository and product URLs are readable. The demo field explicitly says “Pending public upload,” so the deck does not provide the requested demo-video link. This is a concrete completion gap, not a cosmetic issue. I did not open or test either URL. |

## Quantities and identifier inventory

No additional unsupported **performance-number value** was found outside the supplied allowlist. That is a numeric-scope observation, not verification of the claims or sources behind those values.

- Slide 2: 2024; 21%; 1,911.
- Slide 3: 1.1/5; 340; 219.
- Slide 4: 1,911; 46.8% and 15.8% inside the product crop; $3.20. “Three checks” is a structural count matching the three feature panels.
- Slide 5: 46.8% and 15.8% in product crops. Four stage panels are visible; no numbered step badges are visible.
- Slide 6: “One request” is a scenario/structural description, not a benchmark result.
- Slide 8: 46.8%; 15.8%.
- Slide 9: 0.67; 8/20; 60; 0 model calls; $0.00.
- Slide 10: 10; 6; 2.5 years; 30 → 18; 23 → 7.
- Slide 11: 46.8% → 15.8%; $3.20.
- Slide 12: “3 Minutes” appears in the demo field's template label. It is not presented as an observed final duration in this PDF. No final duration is shown.

Technology identifiers, separated from measured quantities: Browser; Cloud Run; FastAPI; Google ADK; Gemini rewrite; Agent Platform Sessions; Firestore; nearest prompts; IRT; Gemini 3.5 Flash (Vertex AI); Gemini image + video understanding. “3.5” is part of the supplied model identifier.

Process identifiers, separated from measured quantities: Prompt → Pay → Generate → Judge → Re-prompt, with Preflight inserted before Pay; and Paste → Risk + why → Better prompt → Still / clip review. The latter has four thumbnails but no visible numbered identifiers.

URL identifiers, separated from measured quantities:
- `https://github.com/testofschool/preflight`
- `https://preflight-jcgro45veq-as.a.run.app`
- Demo URL: absent; the displayed field is “Pending public upload.”

## Visual and evidence findings

The most text-dominated non-template slides are 7, 9, and the large initials/count portion of 10. Slides 3 and 6 are box-heavy, but their arrows and placement communicate relationships, so I do not fail them merely for using labels. Slide 1 and slide 12 are functional template/utility slides.

I do not see accidental generated text in the concept photos on slides 2 and 11. The Google Cloud, AI Builder Cup, and H2S marks are intentional template branding. The white logo-like mark inside slide 8's laptop image is a separate image-content issue. Product logos within real UI screenshots are also separate from generated image artifacts.

The PDF's source notes are attributions, not independently inspected evidence. Under the PDF-only restriction I cannot verify the external refund policy, quotations, source receipts, architecture deployment, QA execution, model identity, or URL availability. The practical failures above are visible in the deck itself and do not require those external checks.

### Isolated visual review — round2, verbatim

**Overall: FAIL.** The payment problem and pre-payment check are clear, but slides 5, 7, 8, 9, 10, and 12 still fail the visual/completion rubric; I reviewed only the revised PDF, SHA256 `0695c9768a0881349197ccbc53b0e614d1f2161f4083e4eddc093be804c49610`.

| Slide | Verdict | Reason |
|---|---|---|
| 1 — Team | **PASS** | Concrete problem and team details are readable within 30 seconds. The large competition marks are intentional template branding. |
| 2 — Idea | **PASS** | The payment pain is immediate; quotations and film/coins image work together. The concept photograph has no conspicuous accidental text or logo. Historical votes are identified as context. |
| 3 — Opportunity | **PASS** | The timeline and orange intervention marker clearly place Preflight before payment. It is box-heavy, but the graphic communicates a relationship rather than a wall of text. |
| 4 — Features | **PASS** | Risk, rewrite, and still are understandable. “Historical, uncalibrated” and “Motion untested” constrain the promise. Fine screenshot text remains soft, but the large number and captions carry the slide. |
| 5 — Process | **FAIL** | All four numbered steps are now visible and the sequence is clear. However, the enlarged “why” crop ends mid-sentence at “The,” and the screenshot text is visibly blurred/pixelated. The evidence looks unfinished at presentation scale. |
| 6 — Architecture | **PASS** | Readable nodes and arrows communicate backend, agent, persistence, and prompt/IRT relationships. This is a functional text-based diagram; it does not need to restate the whole product pitch. |
| 7 — Technology | **FAIL** | The added verbs explain service roles, but the slide remains entirely names, arrows, and words inside large grey boxes. Text still dominates; there is no meaningful picture or visual differentiation between the services. |
| 8 — Snapshots | **FAIL** | The prominent “uncalibrated,” “scene changed,” and no-video-improvement caveat now prevents the strongest misleading before/after claim; the right-image logo is no longer visible. But the large original still retains a conspicuous thin doubled/stray-looking spoon edge, making the image look synthetic. |
| 9 — Performance | **FAIL** | The wording now distinguishes valid images in the best probe, calls across probes, historical AUC, and saved-image replay. Those scopes are clearer. Visually, however, this remains three typeset metric cards with no picture or evidence graphic: text/numbers dominate completely. |
| 10 — Team/QA | **FAIL** | “10 QA points, 6 fixes” is clearer. The paired header crops still do not visibly demonstrate Objects 30 → 18 or Colours 23 → 7; they mainly show nearly identical headers with a changed lower control. The count claim is allowed numerically but unsupported by the displayed comparison. “S shipped” is also awkwardly disconnected. |
| 11 — Closing | **PASS** | “Check before you pay” is appropriately cautious, and this slide explicitly calls the reduction an uncalibrated estimate. The large clapperboard image is clean; no conspicuous generated text or accidental logo is visible. |
| 12 — Links | **FAIL** | Repository and product URLs are readable, but the demo-video field still says “Pending public upload.” The requested demo link is absent. This slide is functional text-only template content. |

**Numeric/identity inventory:** All observed metric values stay within the supplied allowlist: 2024; 21%; 1,911; 1.1/5; 340; 219; 46.8%; 15.8%; $3.20; 0.67; 8/20; 60; 0 model calls; $0.00; 10; 6; 2.5 years; 30 → 18; 23 → 7. This does not independently validate their sources. Gemini 3.5 Flash (Vertex AI) is a technology identifier; numbered process steps 1–4 are structural identifiers. “Three checks” and “One request” are structural descriptions. “3 Minutes” remains template wording; no observed final duration is shown. URLs present: `https://github.com/testofschool/preflight` and `https://preflight-jcgro45veq-as.a.run.app`; neither was opened. Google Cloud/AI Builder Cup/H2S marks are intentional template branding, and Preflight marks inside UI captures are product branding.

## D / F remaining and publication proof

Felix explicitly confirmed that YouTube upload follows the Track I framing fix. No URL has been supplied; no upload, public/private/unlisted determination, displayed-duration verification, or link replacement has been claimed. Placeholder agreement is not a passed public-link equality check. D remains independent of H/I/J and the G fallback decision.

The existing one-shot21:30KST F heartbeat was updated to this chat and the final-v7 paths. It must use the selected fallback deck (or its later link-only D export), actual Track I video/captions/frames, current README/notes and a fresh status GET. F is still preparation, not the final timed pass. Brief description is unchanged at952/1,024 characters, SHA-256 `3bac4ff63ca67bf51c54d329abad0c3cb16da13f697bd35e3041e40959f6ef23`.

The selected-fallback preparation at18:59:22KST checked all fifteen rows, freshly extracted/inspected thirteen actual video timestamps and read a fresh status GET200: **zero canonical conflicts, one required-missing row (public YouTube URL)**. Full table and machine evidence are in `track_f_selected_fallback_preparation.md/.json`. This does not satisfy the final F timing or the missing public-link gates.

`scope_during_g_correction.json` independently rechecked all25 post-J runtime files, four tag objects, native active revision/image/allowed environment/resources/concurrency/timeout, and both video copies at18:55:43KST. All matched. G/D/F made no runtime/cloud/tag/history changes. That scope check performed zero production POSTs.

Content publication and exact-HEAD proofs are recorded in the later publication receipt section. Final exact-HEAD secret/history/privacy and anonymous-clone receipts are kept outside the checkout under `../evidence/final_v7/` to avoid a self-referential receipt-commit loop. No pending track is rounded up to complete.

Not done: v7 visual promotion (failed, v6 selected); public YouTube URL/upload/visibility/duration/link equality; final timed fifteen-row F pass; submission form submission. No video was deleted.
