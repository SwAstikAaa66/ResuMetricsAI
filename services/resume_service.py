import io
import json
import os
import urllib.error
import urllib.request

from config import Config


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
            return "\n".join(p.text for p in document.paragraphs).strip()
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
        candidate = text[start : end + 1]
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

    normalized = {
        "role": parsed.get("role") or role_label,
        "Skills": skills if isinstance(skills, list) else [],
        "MissingSkills": missing_skills if isinstance(missing_skills, list) else [],
        "Roadmap": roadmap if isinstance(roadmap, list) else [],
        "InterviewQuestions": interview_questions if isinstance(interview_questions, list) else [],
    }
    normalized["overall_score"] = _calculate_overall_score(normalized)
    return normalized


def _calculate_overall_score(result):
    skills = len(result.get("Skills", []))
    roadmap = len(result.get("Roadmap", []))
    interview = len(result.get("InterviewQuestions", []))
    missing = len(result.get("MissingSkills", []))

    score = 42
    score += min(skills * 4, 20)
    score += min(roadmap * 3, 12)
    score += min(interview * 2, 10)
    score -= min(missing * 3, 15)

    return max(38, min(92, score))


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
    api_key = os.getenv("GEMINI_API_KEY") or Config.GEMINI_API_KEY
    if not api_key:
        raise ValueError("Missing Gemini API key")

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta2/models/{Config.GEMINI_MODEL}:generate?key={api_key}"
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
        raise RuntimeError(f"Gemini API request failed: {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini API request failed: {exc.reason}") from exc

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
                candidate_text = " ".join(
                    str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in candidate
                )
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

    analysis = {
        "role": role_label,
        "Skills": profile["Skills"],
        "MissingSkills": profile["MissingSkills"],
        "Roadmap": profile["Roadmap"],
        "InterviewQuestions": profile["InterviewQuestions"],
        "_fallback": True,
    }
    analysis["overall_score"] = _calculate_overall_score(analysis)
    return analysis


def analyze_resume_text(text, role=None):
    text = (text or "").strip()
    role_label = (role or "Professional").strip() or "Professional"

    try:
        analyzer_url = os.getenv("ANALYZER_URL") or Config.ANALYZER_URL
        if analyzer_url:
            headers = {"Content-Type": "application/json"}
            api_key = os.getenv("ANALYZER_API_KEY") or Config.ANALYZER_API_KEY
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            payload = {"text": text, "role": role_label}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(analyzer_url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
            parsed = json.loads(body)
            normalized = _normalize_analysis_output(parsed, role_label)
            if not normalized["Skills"] or not normalized["Roadmap"] or not normalized["InterviewQuestions"]:
                raise ValueError("Primary analyzer returned incomplete analysis")
            return normalized

        gemini_api_key = os.getenv("GEMINI_API_KEY") or Config.GEMINI_API_KEY
        if gemini_api_key:
            try:
                return _call_gemini_api(text, role_label)
            except Exception as exc:
                print("Gemini API failed:", exc)
                return _generate_fallback_analysis(role_label, text)

        return _generate_fallback_analysis(role_label, text)
    except Exception as exc:
        print("Resume analysis failed, using fallback:", exc)
        return _generate_fallback_analysis(role_label, text)
