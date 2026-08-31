import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///resumetrics.db")
    ANALYZER_URL = os.getenv("ANALYZER_URL", "")
    ANALYZER_API_KEY = os.getenv("ANALYZER_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-text-bison-001")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
