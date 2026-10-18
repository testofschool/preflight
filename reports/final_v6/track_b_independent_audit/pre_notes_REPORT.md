# Independent Track B final-export audit

Observed 2026-10-18T17:45:49+09:00. Read-only audit of PDF SHA-256 `7f056e614806efd563daee155bd8a0c0f194bbbec64edd6557e77c61a401aef0` and PPTX SHA-256 `137ea04bec138b894af93818d6a168126013ca4700f21654a81136c3c588d94a`.

Result: artifact size, official-template style preservation and visual checks PASS within the stated scope. Deck has 11 pages, 660,305 bytes, below 5,000,000 bytes. Public demo URL and duration-rule reconciliation remain incomplete. This is not a submission-ready or final Track F verdict.

| Axis | Observed difference / result | Classification |
| --- | --- | --- |
| Masters/layouts/themes | All 26 original shared parts, including relationships, are byte-identical | Preserved |
| Original media | All 5 original media resources are byte-identical; unused resources remain in archive | Preserved; not every retained resource is displayed |
| Fonts | Explicit family set remains Arial, Google Sans Flex, Google Sans Flex Medium, Google Sans Flex SemiBold (plus empty theme placeholders) | Preserved |
| Slide dimensions | 9144000 × 5143500 EMU unchanged | Preserved |
| Slide 1 | Shape 54 bounds unchanged; all slide-1 non-text XML identical | Intentional field-text fill only |
| Page/slide count | Original 16; exported 11. Retains original slides 1,3,4,5,6,8,9,11,12,13,14 | Reported intentional omission of instruction slide 2, optional wireframes 7, optional cost 10, blank 15 and native thank-you 16 |
| Original shape changes | Shape 54 fields filled; slide 4 shape 79 instructional prompts removed below title; slide 14 shape 159 keeps title while link fields move into authored boxes | Reported intentional content filling / mapped template use |
| Visual inspection | Contact sheet and every page at 120 dpi inspected; all 11 corresponding 50 dpi check renders exist. No tofu, authored text overflow, missing section or unintended overlap found | PASS; screenshot details remain images |

## Numbers, including exceptions

Broad numeric extraction inventories every digit sequence in native PDF text, including digits inside URLs and identifiers. It found 33 occurrences and 24 unique tokens. The 22 distinct tokens supplied by the v5 table account for all newly authored Preflight quantities and model/region identifiers. Two additional native-PDF-text tokens are explicitly retained below. Embedded visual text was separately reviewed using render OCR and visual inspection.

| Extra number / token | Location | Classification and implication |
| --- | --- | --- |
| 3 | PDF page 11: “Demo Video Link (3 Minutes)” | Native official-template duration quantity. It is not an invented Preflight result. It still expresses a duration requirement; it conflicts with the current 172-second / 2:52 file if interpreted as a minimum or exact requirement. Do not call duration eligibility PASS. Parent has separately observed dashboard 3–4 minutes and requested user direction. |
| 45 | PDF page 11 live URL `preflight-jcgro45veq-as.a.run.app` | URL identifier digits, not a numerical claim. Required exact destination; no value change. |
| 2 | Organizer H2S branding image, visible on all 11 pages (OCR independently catches page 1) | Proper-name logo digit inherited unchanged from original template image. Not a new numerical claim. |

Embedded demo screenshot numbers 46.8% and 15.8%, plus authored 0 model calls / $0.00 labels, match the approved v5 values. OCR reads Veo 3.1 as “31” on page 4, drops the percent sign from screenshot 46.8 on page 8, and emits an unsupported “3” from page-8 screenshot glyphs; visual/native-text checks identify those as OCR errors, not extra claims. The omitted instruction screenshot contains browser UI numbers, but it is not displayed in the exported PDF.

Unsupported newly authored Preflight quantities found: 0. This does not mean the PDF contains no numeric tokens outside the v5 table; the three exception classes above are disclosed. See `export_audit.json` for every native-text occurrence and `render_ocr_numeric_inventory.json` for supplemental OCR.

No deck, source, runtime, README, notes, Git history or tags were edited by this audit. Remaining actions are to obtain/verify the public URL, resolve the official duration requirement against the chosen final video, and perform Track F at its required final timing.
