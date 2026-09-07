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

2. Upload deploy cache to Supabase:

```bash
python scripts/sync_supabase_cache.py
```

This uploads lightweight class summaries plus teachers, TP, CP, OH, and assignment summaries.

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
```

3. Open `Actions` -> `Sync LMS Data` -> `Run workflow`.

The workflow runs `python main.py` and then `python scripts/sync_supabase_cache.py`, so Vercel will read the updated Supabase cache without a new deploy.

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
```

`SKIP_PREPARE_DATA=1` keeps Vercel builds fast and avoids running the long LMS fetch during deploy.

## Notes

- `/cr`, `/tp`, and `/mentors` use lightweight class summaries, so they do not download all slots.
- Student data in `/cr` is fetched on demand per class and cached in Supabase.
- Full slot-heavy class data is still local-first. Do not upload `public/classes.json` with slots unless you intentionally need it; it is very large.
