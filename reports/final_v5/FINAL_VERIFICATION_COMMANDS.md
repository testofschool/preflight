# Final v5 publication verification

Run from the repository root after package production is complete. These commands were prepared and inspected offline; the final scans and network verification have not been run by the readiness auditor.

Before the content commit, inspect the final diff and confirm the runtime source remains unchanged. Run the existing worktree/index marker scanner and retain its exit code:

```sh
../.preflight-cloud-venv/bin/python scripts/check_secrets.py --include-index > reports/final_v5/secrets_prepublication.json
```

Require exit 0, `complete=true`, `hit_count=0` and an empty `errors` list. It scans file bytes and all index blobs without printing matched values. It is a fixed-pattern marker check, not a guarantee against every possible secret format. Do not print raw matches or command diagnostics.

After committing the final package content, scan all reachable refs:

```sh
../.preflight-cloud-venv/bin/python scripts/scan_history_v3.py --report reports/final_v5/history_scan_content_commit.json
```

Require exit 0, `complete=true`, `passed=true`, `hit_count=0` and an empty `errors` list. The script refuses to overwrite existing receipts, so a repeat needs a fresh report path. It scans binary blobs and reachable commit/tag objects as well as text blobs.

After pushing, replace `FULL_PUSHED_COMMIT_SHA` with the exact full SHA and run:

```sh
../.preflight-cloud-venv/bin/python reports/final_v5/verify_public_package.py --expected-commit FULL_PUSHED_COMMIT_SHA --report reports/final_v5/public_access_content_commit.json
```

Require exit 0 and `pass=true`. The verifier anonymously clones public main into `/private/tmp`, disables credentials, global/system Git settings and hooks, checks all three fixed tag targets, compares the cloned main and source tag against the frozen 25-file runtime digest, verifies public repository and README HTTP 200, compares public README bytes with the clone, and counts the Brief description. Temporary data is removed; only sanitized metadata is saved.

Existing tag targets must remain:

| Tag | Commit |
| --- | --- |
| `aibc-2026-submission` | `dd12f279e364cbd217a4178b51c1d270cacebbdd` |
| `aibc-2026-submission-v2` | `bdcdecdf6db6b0c2bebea8a35ed350de5f005940` |
| `aibc-2026-submission-v3` | `d638c0690cb17d60316922eb30a14f150fe7c23c` |

Frozen runtime SHA-256: `a3f7c0a10ebec2e00ff7bc7bfc01676c712405aff0a8dad55f8c82eef2364fa7`. The starting main `de0d563530405adf3dae5a26f5ded3f7a009917d`, source tag and initial worktree all match this digest. The native image receipt records `sha256:4bf0668ae549f7ab924f17e36105b621f1f25676aefb6e53e06154db4384e932`; the parent performs fresh native configuration/image verification for Track A separately.

Do not treat `public_access_content_commit.json` as YouTube verification or as Track D completion. The auditor found one `<VIDEO_URL>` placeholder in each of README and submission notes; the final public URL has not been supplied. When Felix supplies it, replace both placeholders, verify anonymous accessibility and public visibility, then commit, push, scan and clone again with fresh receipt filenames. HTTP 200 by itself does not establish public versus unlisted visibility.

If a later commit only appends receipts or the report, the earlier receipts remain bounded to their recorded content commit. Either repeat the history scan and public check for the later SHA with fresh filenames, or clearly state that later receipt append lies outside the earlier checks. Avoid claiming a receipt verified its own future commit.
