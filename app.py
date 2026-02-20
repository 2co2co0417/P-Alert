from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from datetime import datetime, timedelta
import os
import random
import json
import urllib.request
import urllib.parse

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


@app.route("/", methods=["GET"])
def index():
    if not current_user_id():
        return redirect(url_for("login"))

    # 気圧ダッシュボードだけ表示
    return render_template("index.html")


@app.route("/health", methods=["GET", "POST"])
def health():
    if not current_user_id():
        return redirect(url_for("login"))

    # POST（登録）
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
            (current_user_id(), datetime.now().isoformat(timespec="seconds"), score_int, note)
        )
        conn.commit()
        conn.close()

        flash("記録しました")
        return redirect(url_for("health"))

    # GET（表示）
    conn = get_conn()
    logs = conn.execute(
        "SELECT log_at, score, note FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT 50",
        (current_user_id(),)
    ).fetchall()
    conn.close()

    return render_template("health.html", logs=logs)


@app.route("/login", methods=["GET", "POST"])
def login():
    # ここは「ログイン専用ページ」表示
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_conn()
        user = conn.execute("SELECT id, pw_hash FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if not user or not check_password_hash(user["pw_hash"], password):
            flash("メールまたはパスワードが違います")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]
        flash("ログインしました")
        return redirect(url_for("index"))

    return render_template("auth.html", mode="login")


@app.route("/register", methods=["GET", "POST"])
def register():
    # ここは「新規登録ページ」表示（テンプレートは同じ auth.html を使う）
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("メールとパスワードは必須です")
            return redirect(url_for("register"))

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
            return redirect(url_for("register"))

        flash("登録しました。ログインしてください。")
        return redirect(url_for("login"))

    return render_template("auth.html", mode="register")
def fetch_pressure(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/jma?"
        f"latitude={lat}&longitude={lon}"
        "&hourly=surface_pressure"
        "&timezone=Asia%2FTokyo"
    )

    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read())

    times = data["hourly"]["time"]
    pressures = data["hourly"]["surface_pressure"]

    # 48時間分だけ返す
    labels = [t[5:16].replace("T", " ") for t in times[:48]]
    values = [round(p, 1) for p in pressures[:48]]

    return labels, values

from flask import jsonify
from datetime import datetime

def _parse_label_to_dt(label: str) -> datetime:
    """
    labelsの形式が 'YYYY-MM-DD HH:MM' でも 'YYYY-MM-DDTHH:MM' でもパースする。
    タイムゾーンはラベル側がJST前提（Open-Meteoにtimezone=Asia/Tokyoを付けるのが理想）。
    """
    s = label.strip()
    s = s.replace("T", " ")
    # 秒が付いても切り捨て
    if len(s) >= 16:
        s = s[:16]
    return datetime.strptime(s, "%Y-%m-%d %H:%M")

def _find_now_index(labels):
    now = datetime.now()  # サーバーのローカル時刻（日本ならJST）
    dts = []
    for lb in labels:
        try:
            dts.append(_parse_label_to_dt(lb))
        except Exception:
            dts.append(None)

    # パースできた中で「nowに一番近い」indexを選ぶ（未来・過去どちらでも最短）
    best_i = 0
    best_diff = None
    for i, dt in enumerate(dts):
        if dt is None:
            continue
        diff = abs((dt - now).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_i = i
    return best_i

@app.route("/api/pressure")
def api_pressure():
    labels, values = fetch_pressure(34.07, 132.99)

    n = len(values)
    if n == 0:
        return jsonify({"error": "no data"}), 500

    # ✅「現在」は配列の最後ではなく、“今に近い時刻”の点
    i_now = _find_now_index(labels)

    current_hpa = round(values[i_now], 1)
    current_time = labels[i_now]

    # ✅ 3時間前比（可能なら）
    delta_3h = None
    base_time_3h = None
    if i_now >= 3:
        delta_3h = round(values[i_now] - values[i_now - 3], 1)
        base_time_3h = labels[i_now - 3]

    # ✅ trend（直近3時間で判定）
    trend = "不明"
    if delta_3h is not None:
        if delta_3h <= -6:
            trend = "急降下"
        elif delta_3h <= -3:
            trend = "やや注意"
        elif delta_3h < 3:
            trend = "安定"
        else:
            trend = "上昇"

    # ✅ これからの危険時間帯（連続3時間で最も下がる区間）
    danger = None
    if n >= 4:
        best_i = None
        best_drop = 0.0
        for i in range(0, n - 3):
            drop = values[i + 3] - values[i]
            if best_i is None or drop < best_drop:
                best_i = i
                best_drop = drop
        danger = {"start": labels[best_i], "end": labels[best_i + 3], "delta_hpa": round(best_drop, 1)}

    # ✅ risk（3時間低下量ベース）
    risk = "不明"
    if danger is not None:
        drop3 = abs(danger["delta_hpa"])
        if drop3 >= 8:
            risk = "警戒"
        elif drop3 >= 4:
            risk = "注意"
        else:
            risk = "安定"

    # 互換：旧フィールドも残したければここで返してOK
    # delta_hpa を旧UIが使うなら、意味が変わると混乱するので「直近3h」を入れておくのが無難
    delta_hpa_legacy = delta_3h if delta_3h is not None else 0.0
    danger_time_legacy = danger["start"] if danger else labels[i_now]

    return jsonify({
        "labels": labels,
        "values": values,

        "current_hpa": current_hpa,
        "current_time": current_time,

        "delta_3h": delta_3h,
        "delta_3h_base_time": base_time_3h,
        "trend": trend,

        "danger_window": danger,

        # 旧互換（必要なら）
        "delta_hpa": delta_hpa_legacy,
        "danger_time": danger_time_legacy,

        "risk": risk
    })





@app.route("/logout")
def logout():
    session.clear()
    flash("ログアウトしました")
    return redirect(url_for("login"))

import click
from pressure_job import run_daily_pressure_check

@app.cli.command("daily-pressure-check")
def daily_pressure_check_cmd():
    """毎日: 気圧を保存→前日比→閾値超えたらメール通知"""
    run_daily_pressure_check()
    click.echo("daily-pressure-check: done")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
