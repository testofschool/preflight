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
