import io
import json
import re
import urllib.parse
import urllib.request


def extract_linkedin_text_from_file(file_storage):
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
        except Exception as exc:
            raise ValueError(f"Unable to parse PDF: {exc}") from exc

    try:
        return content.decode("utf-8", errors="ignore").strip()
    except Exception as exc:
        raise ValueError(f"Unable to read uploaded file: {exc}") from exc


def _normalize_linkedin_url(raw_url):
    value = (raw_url or "").strip()
    if not value:
        raise ValueError("Please provide a LinkedIn profile URL.")

    if value.startswith("//"):
        value = "https:" + value
    if not value.startswith(("http://", "https://")):
        if "linkedin.com" in value:
            value = "https://" + value
        elif "/in/" in value or "linkedin.com/in" in value:
            value = "https://www.linkedin.com" + ("/" if not value.startswith("/") else "") + value
        else:
            raise ValueError("Please provide a valid LinkedIn profile URL.")

    parsed = urllib.parse.urlparse(value)
    if "linkedin.com" not in parsed.netloc.lower():
        raise ValueError("Please provide a valid LinkedIn profile URL.")

    return value


def _extract_linkedin_profile_text(url):
    normalized_url = _normalize_linkedin_url(url)

    try:
        with urllib.request.urlopen(normalized_url, timeout=20) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        raise RuntimeError(f"Unable to fetch profile: {exc}") from exc

    cleaned = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    cleaned = re.sub(r"<style.*?</style>", " ", cleaned, flags=re.S | re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _parse_linkedin_text(profile_text):
    text = profile_text or ""
    headline = re.search(r"Headline\s*[:\-]?\s*(.*?)(?=(?:About|Experience|Skills|$))", text, re.I | re.S)
    about = re.search(r"About\s*[:\-]?\s*(.*?)(?=(?:Experience|Skills|$))", text, re.I | re.S)
    experience = re.search(r"Experience\s*[:\-]?\s*(.*?)(?=(?:Skills|$))", text, re.I | re.S)
    skills_match = re.search(r"Skills\s*[:\-]?\s*(.*?)(?=(?:Education|Recommendations|$))", text, re.I | re.S)

    headline_value = (headline.group(1).strip() if headline else "").replace("\n", " ")
    about_value = (about.group(1).strip() if about else "").replace("\n", " ")
    experience_value = (experience.group(1).strip() if experience else "").replace("\n", " ")
    skills_text = (skills_match.group(1).strip() if skills_match else "")

    skill_tokens = []
    if skills_text:
        skill_tokens = [part.strip() for part in re.split(r"[,|•]", skills_text) if part.strip()][:10]
    if not skill_tokens:
        skill_tokens = re.findall(r"[A-Za-z][A-Za-z+/#.-]{2,}", text)[:10]

    return {
        "headline": headline_value or "Profile headline not found",
        "about": about_value or "About section missing or not parseable.",
        "experience": experience_value or "Experience section missing or not parseable.",
        "skills": skill_tokens or ["Communication", "Strategy", "Collaboration"],
    }


def generate_linkedin_review(profile_text_or_url):
    if not profile_text_or_url or not str(profile_text_or_url).strip():
        raise ValueError("Please provide a LinkedIn URL or profile text.")

    raw = str(profile_text_or_url).strip()
    try:
        if raw.startswith(("http://", "https://", "//")) or "linkedin.com" in raw.lower() or "/in/" in raw:
            profile_text = _extract_linkedin_profile_text(raw)
        else:
            profile_text = raw
    except ValueError:
        profile_text = raw
    except RuntimeError:
        profile_text = raw

    parsed = _parse_linkedin_text(profile_text)
    suggestions = []

    if len(parsed["headline"]) < 25:
        suggestions.append("Add a clearer professional headline that includes your target role, strengths, and value proposition.")
    if len(parsed["about"]) < 80:
        suggestions.append("Expand the About section with your core strengths, leadership impact, and measurable achievements.")
    if len(parsed["experience"]) < 80:
        suggestions.append("Add more outcome-driven bullets for each role, focusing on scope, metrics, and business impact.")
    if not parsed["skills"]:
        suggestions.append("List key skills in a cleaner format and align them with the roles you want to target.")
    else:
        suggestions.append("Reorder your skills to emphasize the most relevant technical and leadership competencies for your target role.")

    if not suggestions:
        suggestions.append("Your LinkedIn profile is already strong; focus on small refinements that increase clarity and keyword alignment.")

    return {
        "status": "success",
        "headline": parsed["headline"],
        "about": parsed["about"],
        "experience": parsed["experience"],
        "skills": parsed["skills"],
        "suggestions": suggestions,
    }
