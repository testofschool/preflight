# Final source and repository verification commands

Run from `/Users/felix/Desktop/AI Builder Cup 2026/preflight` after committing the final source that must match the already built runtime. These commands were identified from the existing scripts; they were not executed by the report writer. Preserve prior receipts by choosing a new history-scan filename for later repeat scans.

## Native source and image provenance

```sh
../.preflight-cloud-venv/bin/python scripts/verify_preview_source_v4.py \
  --build-id 095a35c2-74ad-49cb-8ae8-507a6216ee74 \
  --revision preflight-00025-lij \
  --commit HEAD \
  --report reports/preview_v4/source_match.json
```

Required output: `pass=true`, `files=25`, `runtime_matches_commit=true`, `image_digest_matches=true`; both runtime source hashes must equal `a3f7c0a10ebec2e00ff7bc7bfc01676c712405aff0a8dad55f8c82eef2364fa7`. The helper reads the exact native revision and generation-pinned Cloud Build source archive and compares the native image digest. This is the provenance receipt consumed by the repaired promotion guard.

## Indexed worktree and all-history secret checks

```sh
../.preflight-cloud-venv/bin/python scripts/check_secrets.py --include-index \
  > reports/preview_v4/secrets_source_release.json
../.preflight-cloud-venv/bin/python scripts/scan_history_v3.py \
  --report reports/preview_v4/history_scan_source_release.json
```

Require complete scans with `hit_count=0` and no errors. `scan_history_v3.py` scans all reachable refs, including binary blobs and commit/tag objects, and refuses to overwrite an existing report. After later receipt/tag commits, use `history_scan_final_release.json` for the final repeat.

## Public refs after pushing the source and new tag

```sh
GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 \
  GIT_ASKPASS=/usr/bin/false git -c credential.helper= -c http.extraHeader= \
  ls-remote https://github.com/testofschool/preflight.git \
  refs/heads/main refs/tags/aibc-2026-submission \
  refs/tags/aibc-2026-submission-v2 refs/tags/aibc-2026-submission-v3
```

Expected older tags: `dd12f279e364cbd217a4178b51c1d270cacebbdd` and `bdcdecdf6db6b0c2bebea8a35ed350de5f005940`. The new tag must target the verified production source commit. A public-ref lookup does not replace the separately required fresh anonymous clone and cloned HEAD/tag agreement. There is no standalone public-clone verifier in this repository; reuse the minimal-environment anonymous-clone procedure documented in `reports/preview_v3/public_access.json` and save fresh v4 evidence.
