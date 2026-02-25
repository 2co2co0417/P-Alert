import sqlite3
<<<<<<< HEAD
from flask import Blueprint, render_template, request, redirect, session
from flask_login import login_required, current_user
from flask import url_for
=======
import json
from flask import Blueprint, render_template, request, redirect, flash
from flask_login import login_required, current_user

>>>>>>> MVP-mkmaguro
settei_bp = Blueprint("settei", __name__, url_prefix="/settei")

DB_PATH = "mvp.db"

<<<<<<< HEAD
=======

# =========================
# DB接続
# =========================
>>>>>>> MVP-mkmaguro
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

<<<<<<< HEAD
@settei_bp.route("/", methods=["GET", "POST"])
@login_required
def settei_home():
    user_id = int(current_user.id)
=======
>>>>>>> MVP-mkmaguro

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
<<<<<<< HEAD
        print("===== SETTEI POST HIT =====")
        print("FORM:", dict(request.form))
        print("===========================")

        base = float(request.form.get("base_threshold", 4.0))
        drink_choice = request.form.get("drink_choice", "none")
        pollen_on = True if request.form.get("pollen_enabled") else False

        drink_map = {
            "none": 0.0,
            "beer_whisky": 0.5,
            "wine": 1.0,
            "shochu": 0.5,
        }
        drink_adjust = drink_map.get(drink_choice, 0.0)
        pollen_adjust = 0.5 if pollen_on else 0.0

        effective = base - drink_adjust - pollen_adjust

    # いったん保存せず、表示だけ確認
        
        return redirect(url_for("settei.settei_home"))
=======

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
>>>>>>> MVP-mkmaguro

    # -------------------------
    # 表示処理
    # -------------------------
    s = get_user_settings(user_id)
<<<<<<< HEAD
    effective = calc_effective_threshold(s)
    return render_template("settei.html", s=s, effective=effective)
@settei_bp.route("/test-alert", methods=["POST"])
@login_required
def test_alert():
    user_id = int(current_user.id)
    if not user_id:
        return redirect("/login")
=======
>>>>>>> MVP-mkmaguro

    preferred = []
    if s["preferred_drinks"]:
        preferred = json.loads(s["preferred_drinks"])

<<<<<<< HEAD
    return redirect("/settei/")
=======
    return render_template(
        "settei.html",
        preferred=preferred
    )
    print("DB PATH:", DB_PATH)
>>>>>>> MVP-mkmaguro
