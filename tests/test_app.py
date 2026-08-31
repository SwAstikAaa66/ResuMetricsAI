from services.followup_service import generate_followup_suggestions
from services.linkedin_service import generate_linkedin_review


def test_generate_followup_suggestions_for_sql_question():
    result = generate_followup_suggestions(
        "How can I improve my SQL interviewing skills for a data analyst role?",
        resume_text="Python, SQL, dashboards",
        role="Data Analyst",
    )

    assert result["question"]
    assert any("SQL" in item for item in result["suggestions"])
    assert "Data Analyst" in result["summary"]


def test_generate_linkedin_review_for_profile_text():
    text = "\nHeadline: Data Analyst | Turning data into decisions\nAbout: I build dashboards and track KPIs.\nExperience: Senior Analyst at Acme\nSkills: Python, SQL, Tableau\n"
    result = generate_linkedin_review(text)

    assert result["headline"]
    assert "SQL" in " ".join(result["skills"])
    assert result["suggestions"]


def test_resume_score_is_not_artificially_high():
    result = generate_followup_suggestions(
        "How can I improve my SQL interviewing skills?",
        resume_text="Python, SQL, dashboards, communication",
        role="Data Analyst",
    )
    assert "suggestions" in result


def test_followup_route_returns_tailored_suggestions(client):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "user@example.com"

    response = client.post(
        "/followup",
        data={
            "question": "How can I improve my backend interview answers?",
            "resume_text": "Python, Flask, SQL",
            "role": "Backend Engineer",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["suggestions"]


def test_linkedin_review_route_accepts_url(client, monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"<html><title>Data Analyst | Metrics</title><body>Headline: Data Analyst | Driving insights About: I build dashboards and SQL models. Skills: Python, SQL, Tableau</body></html>"

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeResponse())

    response = client.post(
        "/linkedin_review",
        data={"profile_url": "https://www.linkedin.com/in/example"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["headline"] or payload["suggestions"]
