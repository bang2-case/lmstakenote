# Deploy Vercel + Supabase

## Local sync flow

1. Refresh data locally when needed:

```bash
python main.py
```

For class-only refresh:

```bash
python main.py --only=classes
```

2. Upload database tables to Supabase:

```bash
python scripts/sync_supabase_db.py
```

This uploads the generated SQLite tables into the private `lms` schema in Supabase. The deployed API reads these relational tables first.

By default, `lms.slot_comments` is skipped and cleared because it can contain hundreds of thousands of long comment rows and may exceed small Supabase database limits. The class list, `/cr`, student details, assignments, teachers, DEMO, TP/CP/OH data, and slot status summaries still use the relational database normally.

Only include the full comment table when you specifically need duplicate-comment checking on the deployed site and your Supabase database has enough space:

```bash
python scripts/sync_supabase_db.py --include-slot-comments
```

The legacy JSON cache is optional. Only run it manually if you need to debug an older deploy:

```bash
python scripts/sync_supabase_db.py --with-fallback-cache
```

## GitHub Actions sync flow

Use this when you want to update data without running Python locally.

1. In GitHub, open `Settings` -> `Secrets and variables` -> `Actions`.
2. Add these repository secrets:

```env
DATABASE_URL=your_supabase_pooler_url
LMS_TOKEN=your_lms_token
FIREBASE_API_KEY=optional_for_token_refresh
LMS_LOGIN_EMAIL=optional_for_token_refresh
LMS_LOGIN_PASSWORD=optional_for_token_refresh
GOOGLE_SHEET_ID=optional
GOOGLE_CREDENTIALS_JSON=optional_for_demo_export
```

GitHub Actions secrets are separate from Vercel Environment Variables. Values added only in Vercel are not available to this workflow.

3. Open `Actions` -> `Sync LMS Data` -> `Run workflow`.

The workflow runs `python main.py` and then `python scripts/sync_supabase_db.py`, so Vercel will read the updated Supabase database without a new deploy.
On the deployed website, the in-app refresh buttons are disabled in Supabase database mode. Use this GitHub Action whenever you want fresh data.
The workflow uses the lightweight default sync, so it skips and clears `lms.slot_comments` to avoid Supabase disk-space failures.

## Vercel environment variables

Set these in Vercel:

```env
DATABASE_URL=your_supabase_pooler_url
USE_SUPABASE=1
SKIP_PREPARE_DATA=1
LMS_TOKEN=your_lms_token
FIREBASE_API_KEY=optional_for_token_refresh
LMS_LOGIN_EMAIL=optional_for_token_refresh
LMS_LOGIN_PASSWORD=optional_for_token_refresh
GOOGLE_SHEET_ID=optional
GOOGLE_CREDENTIALS_JSON=optional_for_demo_export
```

`SKIP_PREPARE_DATA=1` keeps Vercel builds fast and avoids running the long LMS fetch during deploy.
`vercel.json` also sets this for the build command, so Vercel should not try to run `python main.py` while deploying.
For DEMO export on Vercel, set both `GOOGLE_SHEET_ID` and `GOOGLE_CREDENTIALS_JSON`. `GOOGLE_CREDENTIALS_JSON` can be the full service-account JSON on one line, or base64-encoded JSON.

## Notes

- `/cr`, `/tp`, and `/mentors` use lightweight class summaries, so they do not download all slots.
- Student data in `/cr` is fetched on demand per class and saved back into `lms.class_students`.
- Full slot-heavy class data now lives in relational Supabase tables (`lms.slots`, `lms.slot_students`) instead of relying on `public/classes.json`; `lms.slot_comments` is optional because it is much larger.
- The `lms` schema is intended for server-side access through `DATABASE_URL`; do not expose it through frontend Supabase keys.
