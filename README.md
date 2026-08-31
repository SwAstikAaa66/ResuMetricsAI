# ResuMetrics AI

A small Flask app to submit resumes, analyze them, and store results.

## Quick start (local)

1. Create and activate a virtual environment

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Copy the example environment file and fill in your own values

```bash
copy .env.example .env
```

Example:

```
SECRET_KEY=change-me-in-production
DATABASE_URL=sqlite:///resumetrics.db
ANALYZER_URL=
ANALYZER_API_KEY=
GEMINI_API_KEY=
```

> Store real secrets in your local `.env` file or in your hosting platform's secret manager. Never commit credentials to Git.

4. Run the app

```bash
python app.py
```

Open http://127.0.0.1:5000

## Deploying

Recommended quick deploy options:

- Render (https://render.com): create a new Web Service, connect your GitHub repo, set the build command `pip install -r requirements.txt` and start command `gunicorn app:app`.
- Railway (https://railway.app): similar setup using `gunicorn app:app` as the start command.

Heroku (deprecated free tier) still works with a `Procfile`:

```
web: gunicorn app:app
```

## GitHub

To push this repo to GitHub:

```bash
git init
git add .
git commit -m "Initial commit"
# create repo on GitHub and push
git remote add origin git@github.com:youruser/yourrepo.git
git push -u origin main
```

## CI

A minimal GitHub Actions workflow is included at `.github/workflows/ci.yml` to run a quick import test.

## Security

⚠️ **Important**: Never commit `.env` or secrets to Git. The `.env` file is listed in `.gitignore` and should only exist locally. Use `.env.example` as a template for required keys.

For production:
- Set environment variables in your hosting platform (Render, Railway, etc.)
- Use a secret manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- Rotate credentials immediately if they are ever exposed

## Notes

- For heavy/slow analysis, consider background jobs (RQ/Celery) and a job status UI.
- All database connections use environment variables only—no hardcoded credentials.
