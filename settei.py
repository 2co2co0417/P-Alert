import sqlite3
import json
from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_required, current_user

settei_bp = Blueprint("settei", __name__, url_prefix="/settei")

DB_PATH = "mvp.db"


# =========================
# DB接続
# =========================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# ユーザー設定取得（なければ作る）
# =========================
def get_user_settings(user_id):
    db = get_db()

    row = db.execute(
        "SELECT * FROM user_settings WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if row is None:
        db.execute(
            "INSERT INTO user_settings (user_id, preferred_drinks) VALUES (?, ?)",
            (user_id, "[]")
        )
        db.commit()

        row = db.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (user_id,)
        ).fetchone()

    db.close()
    return row


# =========================
# 設定画面
# =========================
@settei_bp.route("/", methods=["GET", "POST"])
@login_required
def settei_home():

    user_id = current_user.id
    db = get_db()

    # -------------------------
    # 保存処理
    # -------------------------
    if request.method == "POST":

        preferred = request.form.getlist("preferred_drinks")
        preferred_json = json.dumps(preferred)

        db.execute("""
            UPDATE user_settings
            SET preferred_drinks = ?
            WHERE user_id = ?
        """, (preferred_json, user_id))

        db.commit()
        db.close()

        flash("保存しました")
        return redirect("/settei/")

    # -------------------------
    # 表示処理
    # -------------------------
    s = get_user_settings(user_id)

    preferred = []
    if s and "preferred_drinks" in s.keys() and s["preferred_drinks"]:
        preferred = json.loads(s["preferred_drinks"])

    return render_template(
        "settei.html",
        preferred=preferred
    )