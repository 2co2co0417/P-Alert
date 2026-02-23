import sqlite3
from flask import Blueprint, render_template, request, redirect, session, flash

settei_bp = Blueprint("settei", __name__, url_prefix="/settei")

DB_PATH = "mvp.db"  # あなたのDB名に合わせる

def calc_effective_threshold(s):
    base_t = float(s["base_threshold"])
    drink = float(s["drink_offset"])
    pollen = float(s["pollen_offset"]) if int(s["pollen_enabled"]) == 1 else 0.0
    effective = base_t - drink - pollen
    # 下限（暴発防止）※好みで0.0でもOK
    return max(effective, 0.5)
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
def calc_effective_threshold(s):
    """
    実効しきい値 = 基本 - 飲酒 - 花粉(オン時)
    s は sqlite3.Row を想定（s["base_threshold"] で取れる）
    """
    base_t = float(s["base_threshold"])
    drink = float(s["drink_offset"])
    pollen = float(s["pollen_offset"]) if int(s["pollen_enabled"]) == 1 else 0.0
    effective = base_t - drink - pollen

    # 暴発防止（好みで 0.0 にしてもOK）
    return max(effective, 0.5)
def get_user_settings(user_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM user_settings WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if row is None:
        db.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))
        db.commit()
        row = db.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (user_id,)
        ).fetchone()

    db.close()
    return row

@settei_bp.route("/", methods=["GET", "POST"])
def settei_home():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    if request.method == "POST":
        ...
        return redirect("/settei/")

    s = get_user_settings(user_id)
    effective = calc_effective_threshold(s)
    return render_template("settei.html", s=s, effective=effective)
@settei_bp.route("/test-alert", methods=["POST"])
def test_alert():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    s = get_user_settings(user_id)
    effective = calc_effective_threshold(s)

    # いまは「テストしたよ」だけ（安全）
    flash(f"✅ テストアラート（模擬）: 現在の実効しきい値は {effective:.1f} hPa です。")
    return redirect("/settei/")