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

3. Create a `.env` file with your configuration (optional)

```
DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname
ANALYZER_URL=
ANALYZER_API_KEY=
```

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

## Notes

- Keep secrets out of source control; use the host's environment variables or the platform's secret config.
- For heavy/slow analysis, consider background jobs (RQ/Celery) and a job status UI.
