from flask import Blueprint, render_template, jsonify
from datetime import datetime
from flask_login import login_required, current_user
import sqlite3
import json
import urllib.request
import os

pressure_bp = Blueprint("pressure", __name__)

# =========================
# DB設定
# =========================
DB_PATH = os.path.join(os.path.dirname(__file__), "mvp.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# ダッシュボード画面
# =========================
@pressure_bp.route("/")
@login_required
def index():

    db = get_db()

    row = db.execute(
        "SELECT preferred_drinks FROM user_settings WHERE user_id = ?",
        (current_user.id,)
    ).fetchone()

    db.close()

    preferred = []

    if row and row["preferred_drinks"]:
        try:
            preferred = json.loads(row["preferred_drinks"])
        except:
            preferred = []

    return render_template("index.html", preferred=preferred)


# =========================
# 気圧取得
# =========================
def fetch_pressure(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/jma?"
        f"latitude={lat}&longitude={lon}"
        "&hourly=pressure_msl"
        "&timezone=Asia%2FTokyo"
    )

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())

    times = data["hourly"]["time"]
    pressures = data["hourly"]["pressure_msl"]

    labels = [t.replace("T", " ")[:16] for t in times[:48]]
    values = [round(p, 1) for p in pressures[:48]]

    return labels, values


def _parse_label_to_dt(label: str) -> datetime:
    s = label.replace("T", " ")[:16]
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


def _find_now_index(labels):
    now = datetime.now()
    best_i = 0
    best_diff = None

    for i, lb in enumerate(labels):
        try:
            dt = _parse_label_to_dt(lb)
            diff = abs((dt - now).total_seconds())
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_i = i
        except:
            continue

    return best_i


# =========================
# API
# =========================
@login_required
@pressure_bp.route("/api/pressure")
def api_pressure():

    labels, values = fetch_pressure(34.07, 132.99)

    if not values:
        return jsonify({"error": "no data"}), 500

    i_now = _find_now_index(labels)

    current_hpa = values[i_now]
    current_time = labels[i_now]

    # =========================
    # 3時間差（表示用復活）
    # =========================
    delta_3h = None
    if i_now >= 3:
        delta_3h = round(values[i_now] - values[i_now - 3], 1)

    # =========================
    # 夜時間帯判定（15:00〜翌3:00）
    # =========================
    now = datetime.now()
    current_hour = now.hour
    is_night_mode = (current_hour >= 15 or current_hour <= 3)

    danger = None
    risk = "安定"

    if is_night_mode:

        # =========================
        # 今から8時間の最大下降幅
        # =========================
        best_drop = 0
        best_start = None
        best_end = None

        end_index = min(i_now + 8, len(values) - 1)

        for i in range(i_now, end_index):
            for j in range(i + 1, end_index + 1):
                drop = values[j] - values[i]
                if drop < best_drop:
                    best_drop = drop
                    best_start = labels[i]
                    best_end = labels[j]

        if best_start:
            danger = {
                "start": best_start,
                "end": best_end,
                "delta_hpa": round(best_drop, 1)
            }

            drop_abs = abs(best_drop)

            if drop_abs >= 8:
                risk = "警戒"
            elif drop_abs >= 4:
                risk = "注意"
            else:
                risk = "安定"

    return jsonify({
        "labels": labels,
        "values": values,
        "current_hpa": current_hpa,
        "current_time": current_time,
        "delta_3h": delta_3h,
        "danger_window": danger,
        "risk": risk,
        "is_night_mode": is_night_mode
    })