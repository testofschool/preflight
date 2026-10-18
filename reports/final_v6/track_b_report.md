# Track B - organizer-template pitch deck

Deck authoring/export/QA: DONE. Submission link completion: WAITING for Felix's public YouTube URL. No video URL was invented. Parent agent owns README change, commit/push and final Track D verification.

- Official template obtained through the existing signed-in Hack2skill Submissions Template link, then Google Slides .pptx export. Original `docs/template/aibc_template.pptx` remains unchanged: 960,223 bytes, SHA-256 `29923ab726aa1382946c70ff527c769f0b9e95a55e889f2e01e7ad62641ea629`.
- PDF: `docs/Preflight_pitch_deck.pdf`, 11 pages, 660,305 bytes (limit 5,000,000), SHA-256 `7f056e614806efd563daee155bd8a0c0f194bbbec64edd6557e77c61a401aef0`.
- Editable PPTX: `docs/Preflight_pitch_deck.pptx`, 1,979,965 bytes, SHA-256 `00850a0a470aae3dbbc579e6cd22ed63748e10c7da247e8c2b4441bd60503a4a`.
- Every PDF page rendered at 50 dpi: `docs/deck_check/page-01.png` through `page-11.png`, each 500 x 282 px. `contact_sheet.png` refreshed from final pages. Full PDF text: `docs/deck_check/deck_text.txt`.
- All 11 pages visually inspected at 120 dpi. Final snapshot crop repairs re-inspected. No text cutoff/overflow or broken architecture connector remains observed. Existing template border/header images preserved.
- Numeric check: the author's word-boundary parser found 22 unique native-text tokens matching the exact v5 table. The broader independent audit found 33 native digit-sequence occurrences / 24 unique tokens. Its explicit exception classes are the original-template `3 Minutes` field label, URL identifier `45`, and the unchanged raster H2S brand-logo digit `2` (separate visual/OCR inspection). Thus this is not a claim that every visible numeric token is a v5 Preflight quantity. After classifying these exceptions, unsupported newly authored Preflight quantities found: 0. Four full user quotes remain verbatim. No new market, revenue, savings, accuracy or implementation-cost estimate was added.
- Speaker notes now cite the supplied v5 row(s) and only actually known quote/source URLs copied from README and live/repo links copied from docs/submission-notes.md. A notes-only delta changed 11 existing notes parts and no visible slide/resource part; the PDF remains byte-identical (`track_b_notes_delta.json`).
- Links page honestly says `Pending public upload`. Its original `Demo Video Link (3 Minutes)` field label is retained as template text, not an assertion that the existing 172-second video is exactly 3:00. The subsequent user duration direction is handled by the parent video track; the deck does not assert the duration of the final selected upload.

## Template section mapping

The template has fixed sections. The v5 instruction permits mapping its nine content items to these sections instead of forcing a nine-page deck. No slides were added.

| PDF page | Source template slide / retained heading | v5 content mapped here |
| --- | --- | --- |
| 1 | 1 / Team Details | Team testofschool; Jung Min Kang; exact problem statement. Only field text appended in place. |
| 2 | 3 / Brief about the idea | Preflight summary, all four full user quotes and small source labels, 2024 GenAI-Bench 21% / 1,911 context. |
| 3 | 4 / Opportunities | Gap/refund distinction, exact business-case buyer hypotheses, 1.1/5 / 340 / 219, 2.5 years, Seoul/India, no revenue/market-size claim. |
| 4 | 5 / List of features offered by the solution | Three pre-pay rungs, 1,911 votes, conditional rewrite, $3.20 / Veo 3.1 / 8 s / $0.40/s, separate clip feedback. |
| 5 | 6 / Process flow diagram or Use-case diagram | Original generator loop, Preflight before-pay placement, actual original/rewritten saved spoon/laptop stills. |
| 6 | 8 / Architecture diagram of the proposed solution | Editable Browser, Cloud Run/FastAPI/region, ADK/Gemini/Vertex, tools, Firestore, Agent Platform Sessions, clip/image paths. |
| 7 | 9 / Technologies to be used in the solution | Same v5 architecture service roles; exact current saved-sample/live-generation-limited wording. |
| 8 | 11 / Snapshots of the prototype | Frame 02 risk + complete why paragraph; frame 04 rewrite + condition; frame 05's byte-matched actual saved still asset; exact 46.8% to 15.8% caption. |
| 9 | 12 / Prototype Performance report/Benchmarking | AUC 0.67 and interpretation, 60 calls / three models / best 8/20 / five samples / zero calls/cost, clip-review accuracy unmeasured. |
| 10 | 13 / Additional Details/Future Development (if any) | All four v5 next steps. |
| 11 | 14 / Provide links to your | Public repo and live URL hyperlinks; video field explicitly pending. |

Omitted from the displayed presentation: source 2 (download instructions), 7 (optional wireframe), 10 (optional implementation cost, for which no estimate was authorized), 15 (blank), 16 (non-content thank-you image). Their source resources remain in the package, but they are not referenced as displayed slides. The section order is unchanged. The optional additional final-check screenshot was not added: the two actual saved stills already fill the available process-slide body, and the architecture slide is occupied by the required editable diagram.

## Regen fidelity report

Content canon: the exact v5 Track B table, preserved at `reports/final_v6/CODEX_ONESHOT_preflight_final_v5.md`. Format canon: current organizer template, original template resources, 9144000 x 5143500 EMU, Google Sans Flex/Medium/SemiBold, and LibreOffice 26.2.4.2 export with a private UserInstallation profile. The template itself is the generation specification; no stale generated deck was used.

Before authoring, the parent was told that Artifact Tool's PPTX roundtrip rewrote every master/layout/theme part. Surgical OOXML edits were therefore selected to meet the user's explicit preservation requirement. Template pages were rendered and inspected before filling. The PDF renderer initially substituted Liberation Sans; that was detected and corrected before final delivery by session-only registration of reference-family fonts from official google/fonts.

| Axis | Difference | Classification | Rationale/action |
| --- | --- | --- | --- |
| Content | Empty fields/instructions filled with v5 facts, screenshots and diagram | Reported intentional | User-requested deck. Exact full quotes, figures and claim limits retained. |
| Text | Opportunities and link instruction prompts replaced by actual content | Reported intentional | Fill template fixed sections while preserving section headings. |
| Displayed page count | 16 source pages to 11 content pages | Reported intentional | Instructional/optional/blank/non-content pages omitted as mapped above, no added slides. |
| Masters/layout/theme | 2/2 master parts, 22/22 layout parts, 2/2 theme parts byte-identical | Preserved | No style resource edit. |
| Embedded font resources | 6/6 font parts byte-identical | Preserved | Original font names/styles remain in editable PPTX. |
| Cover formatting | Every non-text XML attribute and all original image resources identical | Preserved | Only three field text values appended; fonts, sizes, paragraphs, geometry and branding unchanged. |
| New content geometry | New native text, cropped evidence pictures, six architecture boxes and five connectors | Reported intentional | Authorized content in original empty body area. All new text/diagram objects editable. |
| PDF font availability | Official complete Google Sans Flex instances, reference-family aliases; five right-arrow glyphs use Lucida Grande | Reported intentional render dependency | Per-session CoreText registration; no persistent install or existing-font change. PDF body text embeds GoogleSansFlex, Medium and SemiBold. Character-level inspection identifies Lucida Grande only for four U+2192 arrows on page 5 and one on page 8, with zero body letters/digits in fallback. |
| PDF rendering | LibreOffice export used | Reported intentional method | Artifact Tool PDF export failed bundled module resolution. No runtime library patch. |
| Speaker notes | Empty note bodies gain v5 canonical-row provenance and known README source URLs | Reported intentional | Source citations required by the presentation skill. Only 11 existing note parts changed in the final delta; note 14 attribution was corrected to docs/submission-notes.md after independent review. Visible slide/resource bytes and final PDF are identical to the inspected version. |
| Unprovided video link | Pending label, original template duration label retained | Reported incomplete field | Track D waits for the user URL. |

Unreported remaining differences: 0. Authoring/export verdict: DONE. Submission links verdict: WAITING. The README pending-export statement becomes false now that the PDF exists; parent agent is responsible for replacing it with the verified PDF link.

## Validation and reproduction

`track_b_fidelity.json` contains package-level byte comparisons and changed-part inventory. `track_b_number_check.json` contains each author-parser token, full quote checks and the independent-audit count/exception qualification. The independent inventory is `track_b_independent_audit/REPORT.md` and `export_audit.json`. `track_b_qa.json` pins deliverable hashes, dimensions, page paths and visual review. `track_b_artifact_tool_feasibility.json` records the actual tool limitations. The finalizer receipt `track_b_finalizer_00850a0a470a.json`, named for the final PPTX hash, contains structural/font/import results. Earlier finalizer files are explicitly draft receipts for superseded pre-notes hashes. It reports 0 findings; 20 warnings are original template title/bottom-bar bounds, with no newly added object outside slide bounds. First-party Artifact Tool import succeeds with 11 slides. This is not a claim of native PowerPoint execution.

Rebuild from repo root:

1. Run `python3 reports/final_v6/track_b_font_runtime.py prepare` (requires fontTools), then `register`. It downloads a pinned official font source and verifies SHA-256 before instancing the three exact family aliases. Source/font hashes and license/source URLs are in `track_b_font_metadata.json`.
2. Run `python3 reports/final_v6/track_b_build_deck.py`. This never edits the source template. It writes the editable PPTX and fidelity/text records. Input image hashes must agree with `track_b_saved_stills.json`.
3. Export with a fresh private profile: `soffice '-env:UserInstallation=file:///tmp/preflight-v6-lo-export' --headless --convert-to pdf --outdir docs docs/Preflight_pitch_deck.pptx`.
4. Run `pdftoppm -r 50 -png docs/Preflight_pitch_deck.pdf docs/deck_check/page` and `pdftotext -layout docs/Preflight_pitch_deck.pdf docs/deck_check/deck_text.txt` and repeat number/visual checks.
5. Run `track_b_finalize.mjs` with the bundled Node executable and `RUNTIME_NODE_MODULES` set to the bundled modules. Its finalizer writes a hash-named receipt and a private validated copy without changing the delivered PPTX bytes.
6. Run `python3 reports/final_v6/track_b_font_runtime.py unregister` after PDF export. All three session fonts were successfully unregistered after this export (`track_b_font_cleanup.json`). No user's running LibreOffice GUI process was killed or altered.

Local build scratch under `track_b_build/` is excluded from the committed package. Original/final decks, render/text QA, source-image assets and reproducible scripts/metadata remain reviewable. No runtime code, image, Cloud Run setting, tag, git history, image generation or Veo call was changed by this track.
