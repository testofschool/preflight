# Track A — DONE / PASS

At 2026-10-18 17:23 KST, `preflight-00027-pit` was promoted to **100% traffic**. The only effective revision-spec change is `PREFLIGHT_PREVIEW_DAILY_LIMIT=60` → `500`. The per-minute limit remains **5**, live generation remains **false**, and warming remains **false**.

- Native image digest before and after: `sha256:4bf0668ae549f7ab924f17e36105b621f1f25676aefb6e53e06154db4384e932`.
- All 25 runtime source files match the existing native Cloud Build provenance receipt. No runtime source edit, image build, image change, live/warm generation, Veo call, commit, push, or Git tag change was performed by this track.
- Offline unit gate: **94 passed, 0 failed**, including **57 new v5 cases**. Every original sample entry and every pinned rewrite entry is tested across both request variants with saved-hit and absent-cache-document paths. The tests also cover whitespace-normalized samples, typed rejection, malformed cache metadata, admission/cache failures, 5/min, and the 500/day boundary. Image-provider construction and generation are guarded by local tripwires; all test dependencies are local fakes.
- Candidate HTTP gate: status `preview_mode="samples"`; original + rewritten spoon/laptop previews **2/2 HTTP 200 cache hits**, **0 model calls**, **$0.00**; one typed preview **HTTP 503**, exact limited copy; `/preflight` **2/2 HTTP 200** with pinned samples and **0 rewrite calls**.
- Production stayed on `preflight-00025-lij` at 100% during candidate preparation and all HTTP gates. Promotion happened only after all gates passed. Final native traffic and digest were verified.

Evidence: `track_a_before.json`, `track_a_candidate.json`, `track_a_gate.json`, `track_a_promotion.json`, `track_a_source_and_tests.json`, `track_a_test_coverage.json`, `track_a_tests.txt`, and `track_a_tests.junit.xml`.

Execution accounting: two harness invocations, **one** candidate-creation command, **one** promotion command, **zero** rollback commands. Invocation 1 stopped before any mutation because the harness compared Cloud Run's service template image tag / omitted default container name directly with the immutable revision's resolved image digest / `app-1` name. Its failure and diagnosis are preserved separately as `track_a_attempt1_*`. Correcting this API-representation comparison changed only the harness; no actual candidate gate failed and no runtime workaround was made.

The initial unit-test draft had 90 passes and 2 failures because it incorrectly classified whitespace-wrapped samples as typed prompts. The existing input validator strips whitespace. The corrected test explicitly proves that this additional admitted path remains free. The initial test output is preserved as `track_a_tests_initial.txt`.

The native revision listing contains `preflight-00027-pit` followed by `preflight-00025-lij`, with no revision 26 shown. Only one candidate creation was executed here; no second or failed candidate is inferred from the skipped number. See `track_a_revision_creation_inspection.json`.

The saved harness includes a bounded post-promotion rollback guard added while the successful invocation was already awaiting candidate creation. The running success path was unchanged and final verification passed; this fallback was not exercised. A supervising read checked the successful completion. Track A's worktree changes are limited to the new test module and `track_a_*` report/harness artifacts; the parent coordinates commits and push.
