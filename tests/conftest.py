import os

import pytest

from app_factory import create_app


@pytest.fixture()
def app():
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    app = create_app({"TESTING": True})
    with app.app_context():
        from db import Base, engine
        Base.metadata.create_all(bind=engine)
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()
