import json
from urllib.parse import quote

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from db import SessionLocal
import models
from services.followup_service import generate_followup_suggestions
from services.linkedin_service import extract_linkedin_text_from_file, generate_linkedin_review
from services.resume_service import analyze_resume_text, extract_resume_text_from_file

bp = Blueprint("main", __name__)


@bp.route("/", methods=["GET", "POST"])
def home():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    return render_template("base.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        next_page = request.form.get("next", "").strip()

        if not email or not password:
            return render_template("login.html", error="Email and password are required.", email=email, next=next_page)

        with SessionLocal() as db:
            user = db.query(models.User).filter(models.User.email == email).first()
            if user and user.password == password:
                session["user_id"] = user.id
                session["user_email"] = user.email
                if next_page.startswith("/"):
                    return redirect(next_page)
                return redirect(url_for("main.dashboard"))

        return render_template("login.html", error="Invalid credentials", email=email, next=next_page)

    return render_template("login.html", email="", next=request.args.get("next", ""))


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            return render_template("signup.html", error="Email and password are required.", email=email)

        with SessionLocal() as db:
            existing = db.query(models.User).filter(models.User.email == email).first()
            if existing:
                return render_template("signup.html", error="Email already exists.", email=email)

            user = models.User(email=email, password=password)
            db.add(user)
            db.commit()
            db.refresh(user)

            session["user_id"] = user.id
            session["user_email"] = user.email
            return redirect(url_for("main.dashboard"))

    return render_template("signup.html", email="")


@bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(f"{url_for('main.login')}?next={quote(request.path, safe='')}")

    if request.method == "POST":
        resume_text = request.form.get("resume", "").strip()
        role = request.form.get("role", "").strip()
        error_message = None

        resume_file = request.files.get("resume_file")
        if resume_file and resume_file.filename:
            try:
                extracted = extract_resume_text_from_file(resume_file)
                if extracted:
                    resume_text = extracted
                elif not resume_text:
                    error_message = "We could not read the uploaded file. Please paste resume text instead."
            except Exception as exc:
                error_message = "Unable to read the uploaded resume. Please try another file or paste the content manually."
                print("Resume file extraction failed:", exc)

        if not resume_text:
            return render_template(
                "dashboard.html",
                user={"name": session.get("user_email", "User")},
                result={"error": "Please paste resume text or upload a valid PDF/DOCX file."},
                success=False,
            )

        try:
            result = analyze_resume_text(resume_text, role=role)
        except Exception as exc:
            result = {"error": "Resume analysis failed. Please try again later.", "role": role or "Professional"}
            print("Resume analysis error:", exc)

        with SessionLocal() as db:
            report = models.Reports(user_id=user_id, resume_text=resume_text, result=json.dumps(result))
            db.add(report)
            db.commit()

        if error_message:
            result["error"] = error_message

        return render_template(
            "dashboard.html",
            user={"name": session.get("user_email", "User")},
            result=result,
            success=True,
        )

    return render_template("dashboard.html", user={"name": session.get("user_email", "User")}, result=None)


@bp.route("/history")
def history():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(f"{url_for('main.login')}?next={quote(request.path, safe='')}")

    with SessionLocal() as db:
        reports = db.query(models.Reports).filter(models.Reports.user_id == user_id).all()

    history_items = []
    for report in reports:
        try:
            payload = json.loads(report.result or "{}") if report.result else {}
        except (TypeError, ValueError):
            payload = {}
        history_items.append({"id": report.id, "payload": payload})

    return render_template("history.html", reports=history_items)


@bp.route("/followup", methods=["GET", "POST"])
def followup():
    if request.method == "GET":
        return jsonify({
            "status": "info",
            "message": "Send a POST request with question, resume_text, and optional role.",
        })

    try:
        question = request.form.get("question", "").strip()
        resume_text = request.form.get("resume_text", "").strip()
        role = request.form.get("role", "").strip()
        result = generate_followup_suggestions(question, resume_text=resume_text, role=role)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to generate follow-up suggestions right now.",
        }), 500


@bp.route("/linkedin_review", methods=["GET", "POST"])
def linkedin_review():
    if request.method == "GET":
        return jsonify({
            "status": "info",
            "message": "Send a LinkedIn profile URL or upload a PDF/text file to review.",
        })

    try:
        profile_url = request.form.get("profile_url", "").strip()
        uploaded_file = request.files.get("profile_file")
        raw_input = ""

        if uploaded_file and uploaded_file.filename:
            try:
                raw_input = extract_linkedin_text_from_file(uploaded_file)
            except Exception as exc:
                return jsonify({"status": "error", "message": f"Unable to read uploaded profile file: {exc}"}), 400
        elif profile_url:
            raw_input = profile_url
        else:
            return jsonify({"status": "error", "message": "Please provide a LinkedIn URL or upload a PDF/text profile."}), 400

        result = generate_linkedin_review(raw_input)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to review the LinkedIn profile right now.",
        }), 500


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.home"))
