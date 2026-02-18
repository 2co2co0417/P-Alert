from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # 通知設定
    notify_enabled = db.Column(db.Boolean, default=True, nullable=False)
    threshold_hpa = db.Column(db.Float, default=8.0, nullable=False)
    lat = db.Column(db.Float, default=33.59, nullable=False)
    lon = db.Column(db.Float, default=132.97, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    symptoms = db.relationship("SymptomLog", backref="user", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class SymptomLog(db.Model):
    __tablename__ = "symptom_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # 体調記録
    symptom = db.Column(db.String(100), nullable=False)   # 例: 頭痛/だるさ/めまい
    severity = db.Column(db.Integer, nullable=False)      # 1-5
    memo = db.Column(db.Text, nullable=True)

    # 記録時刻（ユーザーが入力した時刻 or 現在）
    logged_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
