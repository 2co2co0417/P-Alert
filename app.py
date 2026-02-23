from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from datetime import datetime
import os
from flask_login import LoginManager
from flask_login import UserMixin
from flask_login import login_required

from werkzeug.security import generate_password_hash, check_password_hash
from user import User
from auth import auth_bp
from pressure import pressure_bp
from settei import settei_bp
import json
import urllib.request
import smtplib
from email.mime.text import MIMEText
import click
from werkzeug.security import generate_password_hash, check_password_hash


# =========================
# App / Config
# =========================
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

#LoginManager 初期化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

app.register_blueprint(auth_bp)
app.register_blueprint(pressure_bp)
app.register_blueprint(settei_bp)

# DB設定
DB_PATH = os.path.join(os.path.dirname(__file__), "mvp.db")
print("APP DB PATH:", DB_PATH)

# 気圧取得用設定（メール機能）
LAT = float(os.getenv("LAT", "34.07"))
LON = float(os.getenv("LON", "132.99"))
TIMEZONE = "Asia%2FTokyo"

# =========================
# DB helpers
# =========================
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        pw_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        log_at TEXT NOT NULL,
        score INTEGER NOT NULL,
        note TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pressure_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        pressure_hpa REAL,
        p_min REAL,
        p_max REAL,
        p_range REAL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(user_id, date),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts_sent (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        kind TEXT NOT NULL,
        sent_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(user_id, date, kind),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

#ユーザー組み込み関数
@login_manager.user_loader
def load_user(user_id):
    conn = get_conn()
    user = conn.execute(
        "SELECT id FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    if user:
        return User(user["id"])
    return None

@app.route("/health", methods=["GET", "POST"])
@login_required
def health():

    if request.method == "POST":
        score = request.form.get("score", "").strip()
        note = request.form.get("note", "").strip()

        try:
            score_int = int(score)
        except ValueError:
            flash("体調スコアは整数で入力してください（例：1〜10）")
            return redirect(url_for("health"))

        if score_int < 1 or score_int > 10:
            flash("体調スコアは 1〜10 の範囲で入力してください")
            return redirect(url_for("health"))

        conn = get_conn()
        conn.execute(
            "INSERT INTO logs (user_id, log_at, score, note) VALUES (?, ?, ?, ?)",
            (current_user.id, datetime.now().isoformat(timespec="seconds"), score_int, note)
        )
        conn.commit()
        conn.close()

        flash("記録しました")
        return redirect(url_for("health"))

    conn = get_conn()
    logs = conn.execute(
        "SELECT log_at, score, note FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT 50",
        (current_user.id,)
    ).fetchall()
    conn.close()

    return render_template("health.html", logs=logs)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, use_reloader=False)

