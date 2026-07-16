from flask import Flask, render_template, request, redirect, url_for, session
import io
import os
import json
import urllib.request
import urllib.error
from db import engine, Base, SessionLocal
import models
from sqlalchemy.exc import OperationalError

app = Flask(__name__, template_folder="templates")
app.secret_key = "dev-secret-key"


def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created or already exist.")
    except OperationalError as error:
        print("Warning: Could not create database tables.")
        print("Check DATABASE_URL, credentials, and network access.")
        print(error)


# Resume analyzer helper: calls external API if available, otherwise returns a simple heuristic result.
ANALYZER_URL = os.getenv("ANALYZER_URL", "")
ANALYZER_API_KEY = os.getenv("ANALYZER_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-text-bison-001")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def extract_resume_text_from_file(file_storage):
    filename = (file_storage.filename or "").lower()
    content = file_storage.read()
    if not content:
        return ""

    if filename.endswith(".pdf"):
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            return text.strip()
        except Exception:
            return ""

    if filename.endswith(".docx"):
        try:
            from docx import Document
            document = Document(io.BytesIO(content))
            text = "\n".join(p.text for p in document.paragraphs)
            return text.strip()
        except Exception:
            return ""

    try:
        return content.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def _parse_json_from_response(text):
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty AI response")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not parse JSON from AI response")


def _normalize_analysis_output(parsed, role=None):
    role_label = (role or "Professional").strip() or "Professional"
    skills = parsed.get("Skills") or parsed.get("skills") or []
    missing_skills = parsed.get("MissingSkills") or parsed.get("missing_skills") or []
    roadmap = parsed.get("Roadmap") or parsed.get("roadmap") or []
    interview_questions = parsed.get("InterviewQuestions") or parsed.get("interview_questions") or []

    return {
        "role": parsed.get("role") or role_label,
        "Skills": skills if isinstance(skills, list) else [],
        "MissingSkills": missing_skills if isinstance(missing_skills, list) else [],
        "Roadmap": roadmap if isinstance(roadmap, list) else [],
        "InterviewQuestions": interview_questions if isinstance(interview_questions, list) else [],
    }


def _build_gemini_prompt(role, text):
    role_text = role.strip() if role else "a professional role"
    return (
        "You are a resume analysis assistant.\n"
        "Read the user resume text below and the target role, then return a single JSON object with exact keys:"
        " role, Skills, MissingSkills, Roadmap, InterviewQuestions.\n"
        "Do not include any extra explanation or markdown formatting.\n\n"
        f"Target Role: {role_text}\n\n"
        "Resume Text:\n"
        f"{text}\n\n"
        "Respond with JSON only."
    )


def _call_gemini_api(text, role=None):
    if not GEMINI_API_KEY:
        raise ValueError("Missing Gemini API key")

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta2/models/{GEMINI_MODEL}:generate?key={GEMINI_API_KEY}"
    )
    payload = {
        "prompt": {"text": _build_gemini_prompt(role, text)},
        "temperature": 0.2,
        "max_output_tokens": 560,
    }
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Gemini API request failed: {exc.code} {exc.reason}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini API request failed: {exc.reason}")

    resp_json = json.loads(body)
    candidate_text = ""

    if isinstance(resp_json, dict):
        if "candidates" in resp_json and isinstance(resp_json["candidates"], list) and resp_json["candidates"]:
            candidate = resp_json["candidates"][0]
            if isinstance(candidate, dict):
                candidate_text = candidate.get("output") or candidate.get("content") or candidate.get("text") or ""
        elif "output" in resp_json:
            candidate = resp_json["output"]
            if isinstance(candidate, list):
                candidate_text = " ".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in candidate)
            else:
                candidate_text = str(candidate)

    if not candidate_text:
        candidate_text = json.dumps(resp_json)

    parsed = _parse_json_from_response(candidate_text)
    normalized = _normalize_analysis_output(parsed, role)
    if not normalized["Skills"] or not normalized["Roadmap"] or not normalized["InterviewQuestions"]:
        raise ValueError("Gemini response incomplete")
    return normalized


def _generate_fallback_analysis(role=None, text=""):
    role_label = (role or "Professional").strip() or "Professional"
    role_lower = role_label.lower()

    role_profile = {
        "data": {
            "Skills": ["Data Analysis", "SQL", "Machine Learning", "Visualization"],
            "MissingSkills": ["Production machine learning deployment", "Advanced statistical modeling", "Data pipeline automation"],
            "Roadmap": [
                f"Build a data-driven portfolio project for {role_label}.",
                "Practice end-to-end data pipelines and modeling.",
                "Prepare concise stories about data impact and insights.",
            ],
            "InterviewQuestions": [
                "How would you approach a production machine learning problem?",
                "Describe a project where you turned raw data into business insights.",
            ],
        },
        "backend": {
            "Skills": ["API Design", "System Design", "Database Optimization", "Cloud Architecture"],
            "MissingSkills": ["Distributed systems design", "Cloud-native deployment", "API resiliency and performance tuning"],
            "Roadmap": [
                f"Build a backend service that supports {role_label} use cases.",
                "Master scalable APIs and production monitoring.",
                "Study security, observability, and reliability patterns.",
            ],
            "InterviewQuestions": [
                "How would you design a scalable backend system?",
                "What strategies do you use to improve API performance?",
            ],
        },
        "engineer": {
            "Skills": ["API Design", "System Design", "Python", "Cloud Architecture"],
            "MissingSkills": ["Distributed systems design", "Cloud-native deployment", "Infrastructure automation"],
            "Roadmap": [
                f"Build a project showcasing {role_label} engineering skills.",
                "Practice system design and architecture patterns.",
                "Prepare real-world examples for interviews.",
            ],
            "InterviewQuestions": [
                "How would you scale an engineering system for high traffic?",
                "Describe a time you reduced system complexity.",
            ],
        },
        "developer": {
            "Skills": ["Python", "JavaScript", "API Design", "Unit Testing"],
            "MissingSkills": ["Architecture design", "Performance optimization", "DevOps practices"],
            "Roadmap": [
                f"Build a complete application that highlights {role_label} experience.",
                "Improve code quality with tests and documentation.",
                "Review real-world deployment and delivery workflows.",
            ],
            "InterviewQuestions": [
                "How do you ensure code quality in your projects?",
                "Explain a challenging feature you implemented.",
            ],
        },
        "product": {
            "Skills": ["Product Strategy", "Stakeholder Communication", "Roadmapping", "Research"],
            "MissingSkills": ["Cross-functional leadership", "Data-informed prioritization", "Launch planning"],
            "Roadmap": [
                f"Build a product case study tailored to {role_label}.",
                "Practice communicating strategy and metrics clearly.",
                "Refine prioritization and stakeholder alignment skills.",
            ],
            "InterviewQuestions": [
                "How do you prioritize product features?",
                "Describe a successful product launch you contributed to.",
            ],
        },
    }

    profile = next((profile for key, profile in role_profile.items() if key in role_lower), None)
    if profile is None:
        profile = {
            "Skills": ["Communication", "Problem Solving", "Collaboration", "Domain Knowledge"],
            "MissingSkills": ["Advanced role-specific strategy", "Leadership in cross-team initiatives", "Technical execution at scale"],
            "Roadmap": [
                f"Build a relevant portfolio item for {role_label}.",
                "Validate your work with measurable outcomes.",
                "Prepare scenario-based interview answers.",
            ],
            "InterviewQuestions": [
                f"What makes you a strong fit for {role_label}?",
                "How do you approach learning new domain skills quickly?",
            ],
        }

    return {
        "role": role_label,
        "Skills": profile["Skills"],
        "MissingSkills": profile["MissingSkills"],
        "Roadmap": profile["Roadmap"],
        "InterviewQuestions": profile["InterviewQuestions"],
        "_fallback": True,
    }


def analyze_resume_text(text, role=None):
    text = (text or "").strip()
    role_label = (role or "Professional").strip() or "Professional"

    try:
        if ANALYZER_URL:
            headers = {"Content-Type": "application/json"}
            if ANALYZER_API_KEY:
                headers["Authorization"] = f"Bearer {ANALYZER_API_KEY}"
            payload = {"text": text, "role": role_label}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(ANALYZER_URL, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
            parsed = json.loads(body)
            normalized = _normalize_analysis_output(parsed, role_label)
            if not normalized["Skills"] or not normalized["Roadmap"] or not normalized["InterviewQuestions"]:
                raise ValueError("Primary analyzer returned incomplete analysis")
            return normalized

        if GEMINI_API_KEY:
            try:
                return _call_gemini_api(text, role_label)
            except Exception as exc:
                print("Gemini API failed:", exc)
                return _generate_fallback_analysis(role_label, text)

        return _generate_fallback_analysis(role_label, text)
    except Exception as exc:
        print("Resume analysis failed, using fallback:", exc)
        return _generate_fallback_analysis(role_label, text)


@app.route("/", methods=["GET", "POST"])
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    return render_template("base.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        next_page = request.form.get("next", "").strip()

        if not email or not password:
            return render_template(
                "login.html",
                error="Email and password are required.",
                email=email,
                next=next_page,
            )

        with SessionLocal() as db:
            user = db.query(models.User).filter(models.User.email == email).first()
            if user and user.password == password:
                session["user_id"] = user.id
                session["user_email"] = user.email
                if next_page.startswith("/"):
                    return redirect(next_page)
                return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid credentials",
            email=email,
            next=next_page,
        )

    return render_template("login.html", email="", next=request.args.get("next", ""))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            return render_template(
                "signup.html",
                error="Email and password are required.",
                email=email,
            )

        with SessionLocal() as db:
            existing = db.query(models.User).filter(models.User.email == email).first()
            if existing:
                return render_template(
                    "signup.html",
                    error="Email already exists.",
                    email=email,
                )

            user = models.User(email=email, password=password)
            db.add(user)
            db.commit()
            db.refresh(user)

            session["user_id"] = user.id
            session["user_email"] = user.email
            return redirect(url_for("dashboard"))

    return render_template("signup.html", email="")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login", next=request.path))

    if request.method == "POST":
        resume_text = request.form.get("resume", "").strip()
        role = request.form.get("role", "").strip()

        # Handle uploaded file safely and prefer extracted text when available.
        resume_file = request.files.get("resume_file")
        if resume_file and resume_file.filename:
            try:
                extracted = extract_resume_text_from_file(resume_file)
                if extracted:
                    resume_text = extracted
            except Exception as exc:
                print("Resume file extraction failed, using provided text:", exc)

        # Always return a valid analysis payload; fallback if any AI step fails.
        result = analyze_resume_text(resume_text, role=role)

        # Persist report as JSON string
        with SessionLocal() as db:
            report = models.Reports(user_id=user_id, resume_text=resume_text, result=json.dumps(result))
            db.add(report)
            db.commit()

        return render_template(
            "dashboard.html",
            user={"name": session.get("user_email", "User")},
            result=result,
            success=True,
        )

    return render_template(
        "dashboard.html",
        user={"name": session.get("user_email", "User")},
        result=None,
    )


@app.route("/history")
def history():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login", next=request.path))

    with SessionLocal() as db:
        reports = db.query(models.Reports).filter(models.Reports.user_id == user_id).all()

    return render_template("history.html", reports=reports)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    # Disable the auto-reloader to avoid repeated restart loops
    # while developing in editors that touch files frequently.
    app.run(debug=True, use_reloader=False)