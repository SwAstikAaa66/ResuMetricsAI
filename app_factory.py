from flask import Flask

import models  # noqa: F401
from db import Base, engine
from routes.main import bp as main_bp


def create_app(test_config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object("config.Config")
    if test_config:
        app.config.update(test_config)

    app.secret_key = app.config.get("SECRET_KEY") or "change-me-in-production"
    Base.metadata.create_all(bind=engine)
    app.register_blueprint(main_bp)
    return app
