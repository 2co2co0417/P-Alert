from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # 本番は必ず変更

DB_PATH = os.path.join(os.path.dirname(__file__), "mvp.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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

    conn.commit()
    conn.close()


def current_user_id():
    return session.get("user_id")


@app.route("/", methods=["GET", "POST"])
def index():
    if not current_user_id():
        return redirect(url_for("login"))

    if request.method == "POST":
        score = request.form.get("score", "").strip()
        note = request.form.get("note", "").strip()

        try:
            score_int = int(score)
        except ValueError:
            flash("体調スコアは整数で入力してください（例：1〜10）")
            return redirect(url_for("index"))

        if score_int < 1 or score_int > 10:
            flash("体調スコアは 1〜10 の範囲で入力してください")
            return redirect(url_for("index"))

        conn = get_conn()
        conn.execute(
            "INSERT INTO logs (user_id, log_at, score, note) VALUES (?, ?, ?, ?)",
            (current_user_id(), datetime.now().isoformat(timespec="seconds"), score_int, note)
        )
        conn.commit()
        conn.close()

        flash("記録しました")
        return redirect(url_for("index"))

    conn = get_conn()
    logs = conn.execute(
        "SELECT log_at, score, note FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT 50",
        (current_user_id(),)
    ).fetchall()
    conn
