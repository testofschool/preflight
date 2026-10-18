# Track F selected deck verification — 21:30 support

**PASS** — the current selected deck is the later user-approved v10 pair, verified against the primary sibling evidence directory. This check does not reopen the earlier G redesign decision.

| Artifact | SHA-256 | Bytes / pages |
| --- | --- | --- |
| Current PDF | `15ecda0625f41e3a846e03da4685270e3cc4f276c4582808bad11fe2913f514a` | 585,134 B / 11 pages |
| Current PPTX | `6e322734aafafd873cff29bba04b0b3c1e61d983aa5268ebd17c9d724aa03313` | 1,981,973 B |

Both current files exactly match `final_run_v10_20261018/d/output`, the retained anonymous-copy files, and (PDF) the retained native-form download. Identity was rechecked unchanged at audit close.

The later v10 instruction explicitly selected the preserved v8 source pair: PDF `24053fc97a89b1e5f559658665790eac41e2037fe767ebaadab8ad2bc627fe09`, PPTX `d71d9470044e6e640f31f490711a6539b5b4d574b31c7b672aeca7e5e5f95ac3`. `d/PREBUILD.md`, `d/REPORT.md`, `d/checks.json` and `READY.json` pin that selection. Direct package/text comparisons find exactly the approved changes: displayed page 10 removes only “On-page emphasis of the risk drop.”; displayed page 11 replaces the visible URL and hyperlink target with `https://youtu.be/1A8I-9NZ3Kc`. `(3:28)` and the future-tabs line remain.

Only `ppt/slides/slide13.xml`, `ppt/slides/slide14.xml`, and its relationships part differ from the authorized baseline. Reversing the URL restores exact baseline bytes; removing the single baseline paragraph reproduces page 10. Every other package part/order is preserved. Native PDF text changes only on pages 10 and 11 and matches these deltas. Cover, architecture pages 6–7 and the already-existing business-model sentence remain baseline-identical.

All 26 official master/layout/theme parts, 6 font parts and 5 original media parts remain byte-identical to the official template. Four PDF families are embedded: Google Sans Flex, Medium, SemiBold and LucidaGrande. LucidaGrande supplies only right-arrow symbols (the JSON inventories their pages/text). Native PDF and PPTX a:t text contain no Hangul. Raw theme XML contains 16 Hangul characters in inherited font-family identifiers; those official resources are byte-identical and the JSON inventories them separately. The PDF is below 5,000,000 bytes.

Page 11 has exactly three native URI annotations:

- `https://github.com/testofschool/preflight`
- `https://youtu.be/1A8I-9NZ3Kc`
- `https://preflight-jcgro45veq-as.a.run.app/`

README, submission notes and current PDF contain the same selected YouTube URL. Existing full-size v10 renders of pages 10/11 were inspected; the authorized text/link changes are legible, with no new clipping or tofu observed.

The historical image-led v7 candidate remains a failed visual candidate. The later explicit v10 selection supersedes its old shipping-hash snapshot; the selected current 11-page deck is authorized. This report verifies artifact identity/fidelity and native links. Fresh YouTube public-versus-unlisted status, upload playback, current native form state, remote release state and Submit are outside this read-only support pass. Primary v10 receipts retain their own earlier observations, with source hashes listed in the JSON.

Only the two owned report files were written. No deck edit, export, font registration, Git mutation, model call or cloud mutation occurred.
