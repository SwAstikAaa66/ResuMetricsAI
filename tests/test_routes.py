def test_home_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ResuMetrics AI" in response.data


def test_login_page_shows_error_for_invalid_credentials(client):
    response = client.post(
        "/login",
        data={"email": "user@example.com", "password": "wrong"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data


def test_dashboard_accepts_resume_and_returns_analysis(client):
    with client.session_transaction() as session:
        session["user_id"] = 1
        session["user_email"] = "user@example.com"

    response = client.post(
        "/dashboard",
        data={
            "resume": "Python developer with Flask and SQL experience.",
            "role": "Backend Engineer",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Skills" in response.data
    assert b"Roadmap" in response.data


def test_history_requires_login(client):
    response = client.get("/history")
    assert response.status_code == 302
    assert response.location.endswith("/login?next=%2Fhistory")
