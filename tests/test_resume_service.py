from types import SimpleNamespace

from services.resume_service import analyze_resume_text, extract_resume_text_from_file


def test_extract_resume_text_from_file_text():
    file_obj = SimpleNamespace(
        filename="resume.txt",
        read=lambda: b"Jane Doe\nPython developer\nSQL\n",
    )

    result = extract_resume_text_from_file(file_obj)

    assert "Jane Doe" in result
    assert "Python developer" in result


def test_analyze_resume_text_returns_structured_result_without_external_api(monkeypatch):
    monkeypatch.delenv("ANALYZER_URL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = analyze_resume_text("Senior Python engineer with Flask and SQL", role="Backend Engineer")

    assert result["role"] == "Backend Engineer"
    assert result["Skills"]
    assert result["MissingSkills"]
    assert result["Roadmap"]
    assert result["InterviewQuestions"]
    assert "overall_score" in result


def test_analyze_resume_text_uses_api_payload(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"role":"Data Analyst","Skills":["SQL","Python"],"MissingSkills":["A/B testing"],"Roadmap":["Build a dashboard"],"InterviewQuestions":["Tell me about a KPI"]}'

    def fake_urlopen(req, timeout=30):
        assert timeout == 30
        return FakeResponse()

    monkeypatch.setenv("ANALYZER_URL", "https://example.test/analyze")
    monkeypatch.setenv("ANALYZER_API_KEY", "secret")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = analyze_resume_text("Strong data analyst resume", role="Data Analyst")

    assert result["role"] == "Data Analyst"
    assert "SQL" in result["Skills"]
    assert 40 <= result["overall_score"] <= 75
