import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "33.59"))
    DEFAULT_LON = float(os.getenv("DEFAULT_LON", "132.97"))

    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "")

    PRESSURE_CHANGE_THRESHOLD_HPA = float(os.getenv("PRESSURE_CHANGE_THRESHOLD_HPA", "8.0"))
    FORECAST_HOURS = int(os.getenv("FORECAST_HOURS", "24"))
