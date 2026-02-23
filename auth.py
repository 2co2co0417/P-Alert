from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from user import User

auth_bp = Blueprint("auth", __name__)

# DB接続（app.pyと同じロジック）
import os
DB_PATH = os.path.join(os.path.dirname(__file__), "mvp.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =============================
# ログイン
# =============================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_conn()
        user = conn.execute(
            "SELECT id, pw_hash FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if not user or not check_password_hash(user["pw_hash"], password):
            flash("メールまたはパスワードが違います")
            return redirect(url_for("auth.login"))

        login_user(User(user["id"]))
        flash("ログインしました")
        return redirect(url_for("pressure.index"))

    return render_template("auth.html", mode="login")


# =============================
# 新規登録
# =============================
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("メールとパスワードは必須です")
            return redirect(url_for("auth.register"))

        pw_hash = generate_password_hash(password)

        try:
            conn = get_conn()
            conn.execute(
                "INSERT INTO users (email, pw_hash, created_at) VALUES (?, ?, ?)",
                (email, pw_hash, datetime.now().isoformat(timespec="seconds"))
            )
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            flash("そのメールは既に登録されています")
            return redirect(url_for("auth.register"))

        flash("登録しました。ログインしてください。")
        return redirect(url_for("auth.login"))

    return render_template("auth.html", mode="register")


# =============================
# ログアウト
# =============================
@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("ログアウトしました")
    return redirect(url_for("auth.login"))