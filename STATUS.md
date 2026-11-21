# Royals Attack Stats: build and update status

Pattern: same as RosterPulse (GitHub repo + updater Worker + D1 + loader Worker).

| Piece | Name |
|---|---|
| Repo | jeffscarcello-tech/royals-builds |
| Test site Worker | royalstest (D1 binding DB) |
| Test database | royalstest (4c7d1a8b-c714-45fb-bfc4-def6cc90bffb) |
| Updater Worker | royals-updater (cron */5, binding TEST_DB, repo folder test/) |
| Live site (old, KV upload) | royalsstats, not changed yet |

Releases: edit source/, bump source/version.json (and the app-version meta in source/build/app.src.html), run source/updater/build_app.py, copy dist/app.json and dist/build.txt into test/.
Loader and updater Worker code (source/updater/loader.js, updater.js) are deployed through the Cloudflare connector, not through GitHub.
/admin on royalstest: ADMIN_PASSWORD secret is set (Jeff has it; never stored in this repo).

Current build: 2026-11-21.1 (test only)
