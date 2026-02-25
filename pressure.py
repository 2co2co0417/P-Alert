from flask import Blueprint, render_template, redirect, url_for, jsonify
from datetime import datetime
from flask_login import login_required, current_user
import json
import urllib.request

pressure_bp = Blueprint("pressure", __name__)


# ----------------------------
# ダッシュボード画面
# ----------------------------
@pressure_bp.route("/")
@login_required
def index():
    return render_template("index.html")

# ----------------------------
# 気圧取得
# ----------------------------
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

def _calc_danger_window(labels, values):
    """
    48時間の series から「最悪3時間の下げ幅」を計算して返す。
    api_pressure() の danger_window と同じ定義。
    """
    danger = None
    if len(values) >= 4:
        best_i = 0
        best_drop = 0
        for i in range(len(values) - 3):
            drop = values[i + 3] - values[i]
            if drop < best_drop:
                best_drop = drop
                best_i = i
        danger = {
            "start": labels[best_i],
            "end": labels[best_i + 3],
            "delta_hpa": round(best_drop, 1)
        }
    return danger
# ----------------------------
# API
# ----------------------------
@login_required
@pressure_bp.route("/api/pressure")
def api_pressure():

    labels, values = fetch_pressure(34.07, 132.99)

    if not values:
        return jsonify({"error": "no data"}), 500

    i_now = _find_now_index(labels)

    current_hpa = values[i_now]
    current_time = labels[i_now]

    delta_3h = None
    if i_now >= 3:
        delta_3h = round(values[i_now] - values[i_now - 3], 1)

    danger = _calc_danger_window(labels, values)

    risk = "安定"
    if danger:
        drop3 = abs(danger["delta_hpa"])
        if drop3 >= 8:
            risk = "警戒"
        elif drop3 >= 4:
            risk = "注意"

    return jsonify({
        "labels": labels,
        "values": values,
        "current_hpa": current_hpa,
        "current_time": current_time,
        "delta_3h": delta_3h,
        "danger_window": danger,
        "risk": risk
    })

def get_pressure_delta(lat=34.07, lon=132.99):
    """
    現在時刻を基準に、3時間前との差（hPa）を返す。
    api_pressure() の delta_3h と同じ定義。
    """
    labels, values = fetch_pressure(lat, lon)
    if not values:
        return None

    i_now = _find_now_index(labels)
    if i_now is None:
        return None

    if i_now >= 3:
        return round(values[i_now] - values[i_now - 3], 1)

    return None

def get_danger_delta_hpa(lat=34.07, lon=132.99):
    """
    48時間の予測から「最悪3時間の下げ幅（hPa）」だけ返す。
    api_pressure() の danger_window.delta_hpa と同じ定義。
    """
    labels, values = fetch_pressure(lat, lon)
    if not values:
        return None

    danger = _calc_danger_window(labels, values)
    if not danger:
        return None

    return danger["delta_hpa"]