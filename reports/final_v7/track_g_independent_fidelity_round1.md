# Independent Track G technical fidelity audit

Content canon: the frozen v6 fallback PPTX/PDF; format canon: official template SHA-256 `29923ab726aa1382946c70ff527c769f0b9e95a55e889f2e01e7ad62641ea629`, preserved OOXML resources and v6 export workflow. The approved delta is an image-led 12-page map with a closing page before Links.

Current candidate technical gate: **FAIL pending source-footer cleanup**. This is separate from the fresh isolated PDF visual review. No deck/source/runtime edits or Git staging/commit were performed by this auditor.

PDF SHA-256 `88d9807dd8016803f05826f0a62953b04538b6760600528b791d06973cc72c4a`; 934571 bytes; 12 pages. PPTX SHA-256 `8f74a48a011500d84081f2c162feadd0ad13efb5b28198ea77a3af999144bf9a`; 2563693 bytes.

| Axis | Result / observed difference | Classification |
| --- | --- | --- |
| Master/layout/theme resources | All 26 original parts byte-identical | Preserved |
| Embedded font resources | All 6 original parts byte-identical | Preserved |
| Original media | All 5 original media parts byte-identical, including unused archive resources | Preserved |
| Slide 1 | XML byte-identical to v6; all non-text XML identical to official original | Preserved |
| Slide size | 9144000 × 5143500 EMU unchanged | Preserved |
| Page map | 11 → 12; original content sections retained in order, new closing before Links | Approved intentional delta |
| Authored colors | B4563B / EF7F60 added for requested coral workflow marker; inherited themes/colors unchanged | Reported intentional delta |
| Fonts in PDF | 3 Google Sans Flex families embedded. LucidaGrande embedded only for 3 right-arrow glyphs (2 on page 10, 1 on page 11), no body letters/digits | Disclosed symbol fallback |
| OOXML integrity | ZIP/XML/internal relationship checks pass; all title text retained; manifest objects match actual OOXML | PASS |
| PDF native text | Banned words: 0. Unsupported quantitative tokens: 0 after explicit identifier inventory below | PASS |
| PDF size/renders | 934,571 B ≤ 5,000,000; 12 expected 500 × 282 render PNGs at 50 dpi | PASS |

Words are whitespace tokens, including standalone arrows/pluses/slashes and numbers. Template headings/field labels and genuine citations/image attribution are excluded. Filled cover values and link destinations are counted: cover 24 words, Links 5. Explanatory footer prose counts as authored body; it cannot be hidden by putting “Source:” in front.

| Page | Headline words | Authored body incl. explanatory footer | Main raster area % | Raster + requested native diagram/card area % | Budget result |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 0 | 24 | 0.0 | 0.0 | PASS |
| 2 | 7 | 18 | 41.92 | 41.92 | PASS |
| 3 | 5 | 22 | 0.0 | 40.77 | PASS |
| 4 | 5 | 26 | 41.38 | 41.38 | FAIL |
| 5 | 4 | 10 | 24.04 | 45.04 | PASS |
| 6 | 5 | 28 | 0.0 | 43.0 | FAIL |
| 7 | 4 | 29 | 0.0 | 44.12 | FAIL |
| 8 | 6 | 24 | 40.62 | 40.62 | PASS |
| 9 | 5 | 31 | 0.0 | 50.43 | FAIL |
| 10 | 7 | 39 | 20.4 | 42.83 | FAIL |
| 11 | 4 | 23 | 41.92 | 41.92 | PASS |
| 12 | 0 | 5 | 0.0 | 0.0 | PASS |

Page 5 has 24.04% actual product raster area; the producer reaches 45.04% by including full storyboard card backgrounds. Page 10 has 20.40% actual product raster area; 42.83% includes large initials cards. The numbers are reported separately so that decorative background area is not silently represented as picture area. Native diagrams/chips/metric cards on other pages are explicitly requested by the map. The isolated visual review decides whether these compositions meet the picture-led requirement.

Footer body additions causing failures: page 4 (6 words about motion), page 6 (13 words about service behavior), page 7 (11 words about satisfying the number classification), page 9 (8 caveat words), page 10 (14 words explaining header-count provenance). Page 8’s 5 orientation words yield 24 and pass. Move compliance/provenance explanations to the audit/notes; preserve necessary product caveats inside the 25-word body.

Numeric exceptions are explicit and are not performance values: Gemini `3.5` is the user-mapped technology identifier on page 7 (two occurrences including the source note); `3` in `(3 Minutes)` is unchanged official-template text; `45` is inside the exact live URL. No visible step digits were authored. The unchanged H2S image includes a brand-name `2`. Every native occurrence/context is listed in the JSON.

Real product raster words are not counted as newly authored slide prose. They remain real screenshot evidence, potentially dense or unreadable under the visual rubric. The crop inventory independently recreates each derivative byte-for-byte from its declared source. Risk pixels show only allowed 46.8% and 15.8%; OCR 25.8% is a false reading verified visually. Generated-photo OCR digits 18/5 and header OCR 7 are texture/arrow false positives, not visible numerical claims. Both concept photos were inspected for visible text/logos; none observed. Their exact model return is reported as `UNREPORTED`; no generation was performed by this auditor.

Regen difference classification: content/geometry/media replacements on content pages, the new closing page, and the coral marker are intentional mapped deltas; template resources, cover, headings, dimensions remain preserved. The candidate introduces footer budget failures, which remain unresolved here. The now-false 11-page-current-deck proposition must only be updated if root promotes v7; fallback remains preserved.

Full machine evidence: `track_g_independent_fidelity.json`, extracted PDF text, and raster inventory. No isolated rubric verdict is claimed by this report.
