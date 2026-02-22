from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from datetime import datetime, timedelta
import os
import json
import urllib.request
import smtplib
from email.mime.text import MIMEText
import click
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

# =========================
# App / Config
# =========================
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

DB_PATH = os.path.join(os.path.dirname(__file__), "mvp.db")

# 今治（必要なら変更）
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

def current_user_id():
    return session.get("user_id")

def login_required():
    if not current_user_id():
        return False
    return True

# =========================
# Pressure (MSLP)
# =========================
def fetch_pressure_48h_msl():
    url = (
        "https://api.open-meteo.com/v1/jma?"
        f"latitude={LAT}&longitude={LON}"
        "&hourly=pressure_msl"
        f"&timezone={TIMEZONE}"
    )
    with urllib.request.urlopen(url) as res:
        data = json.loads(res.read().decode())

    times = data["hourly"]["time"]
    pressures = data["hourly"]["pressure_msl"]

    labels = [t.replace("T", " ")[:16] for t in times[:48]]
    values = [round(float(p), 1) for p in pressures[:48]]
    return labels, values

def fetch_today_pressures_msl():
    today = datetime.now().strftime("%Y-%m-%d")
    url = (
        "https://api.open-meteo.com/v1/jma?"
        f"latitude={LAT}&longitude={LON}"
        "&hourly=pressure_msl"
        f"&timezone={TIMEZONE}"
    )
    with urllib.request.urlopen(url) as res:
        data = json.loads(res.read().decode())

    times = data["hourly"]["time"]
    pressures = data["hourly"]["pressure_msl"]

    vals = [float(p) for t, p in zip(times, pressures) if str(t).startswith(today)]
    if len(vals) < 6:
        vals = [float(p) for p in pressures[:24]]
    return vals

# =========================
# Routes
# =========================
@app.route("/")
def index():
    if not login_required():
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/api/pressure")
def api_pressure():
    if not current_user_id():
        return jsonify({"error": "unauthorized"}), 401

    labels, values = fetch_pressure_48h_msl()
    n = len(values)
    if n == 0:
        return jsonify({"error": "no data"}), 500

    # 「現在」は最後ではなく、今に近い点を探す（安全策）
    def _parse_label_to_dt(lb: str) -> datetime:
        s = lb.strip().replace("T", " ")
        if len(s) >= 16:
            s = s[:16]
        return datetime.strptime(s, "%Y-%m-%d %H:%M")

    now = datetime.now()
    best_i = 0
    best_diff = None
    for i, lb in enumerate(labels):
        try:
            dt = _parse_label_to_dt(lb)
        except Exception:
            continue
        diff = abs((dt - now).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_i = i
    i_now = best_i

    current_hpa = round(values[i_now], 1)
    current_time = labels[i_now]

    # 3時間前比
    delta_3h = None
    base_time_3h = None
    if i_now >= 3:
        delta_3h = round(values[i_now] - values[i_now - 3], 1)
        base_time_3h = labels[i_now - 3]

    # トレンド（直近3時間）
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

    # 最も下がる3時間帯（これを「要注意」に表示）
    danger = None
    if n >= 4:
        best_i = None
        best_drop = 0.0
        for i in range(0, n - 3):
            drop = values[i + 3] - values[i]  # 3時間での変化（マイナスが危険）
            if best_i is None or drop < best_drop:
                best_i = i
                best_drop = drop
        danger = {
            "start": labels[best_i],
            "end": labels[best_i + 3],
            "delta_hpa": round(best_drop, 1)
        }

    # リスク判定（3時間低下量ベース）
    risk = "不明"
    if danger is not None:
        drop3 = abs(danger["delta_hpa"])
        if drop3 >= 8:
            risk = "警戒"
        elif drop3 >= 4:
            risk = "注意"
        else:
            risk = "安定"

    # 互換（古いUIが delta_hpa/danger_time を使う場合）
    delta_hpa_legacy = delta_3h if delta_3h is not None else 0.0
    danger_time_legacy = danger["start"] if danger else current_time

    return jsonify({
        "labels": labels,
        "values": values,

        "current_hpa": current_hpa,
        "current_time": current_time,

        "delta_3h": delta_3h,
        "delta_3h_base_time": base_time_3h,
        "trend": trend,

        "danger_window": danger,
        "risk": risk,

        # 旧互換（index.html がこれを見てる可能性が高い）
        "delta_hpa": delta_hpa_legacy,
        "danger_time": danger_time_legacy,
    })

@app.route("/health", methods=["GET", "POST"])
def health():
    if not login_required():
        return redirect(url_for("login"))

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

    conn = get_conn()
    logs = conn.execute(
        "SELECT log_at, score, note FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT 50",
        (current_user_id(),)
    ).fetchall()
    conn.close()

    return render_template("health.html", logs=logs)

@app.route("/login", methods=["GET", "POST"])
def login():
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

@app.route("/logout")
def logout():
    session.clear()
    flash("ログアウトしました")
    return redirect(url_for("login"))

# =========================
# SMTP
# =========================
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER)

def send_email(to_addr, subject, body):
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        raise RuntimeError("SMTP設定が未設定です（.env を確認してください）")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = to_addr

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

# =========================
# CLI
# =========================
@app.cli.command("test-email")
@click.option("--to", "to_addr", default=lambda: os.getenv("MAIL_TEST_TO", ""))
def test_email(to_addr):
    if not to_addr:
        raise click.ClickException(".env の MAIL_TEST_TO が空です")
    send_email(to_addr, "P-Alert SMTP テスト", "これはP-AlertからのSMTP疎通テストです。")
    click.echo(f"OK: sent to {to_addr}")

@app.cli.command("daily-pressure-check")
def daily_pressure_check_cmd():
    today = datetime.now().strftime("%Y-%m-%d")
    vals = fetch_today_pressures_msl()

    p_min = min(vals)
    p_max = max(vals)
    p_range = p_max - p_min

    print(f"[INFO] {today} min={p_min:.1f} max={p_max:.1f} range={p_range:.1f}")

    conn = get_conn()
    cur = conn.cursor()
    users = cur.execute("SELECT id, email FROM users").fetchall()

    if not users:
        print("[WARN] users が0件です（送信先なし）")
        conn.close()
        return

    for u in users:
        user_id = int(u["id"])
        email = u["email"]

        cur.execute("""
            INSERT OR REPLACE INTO pressure_daily
            (user_id, date, pressure_hpa, p_min, p_max, p_range)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, today, float(vals[-1]), float(p_min), float(p_max), float(p_range)))

        if p_range >= 4.0:
            cur.execute("""
                SELECT 1 FROM alerts_sent
                WHERE user_id=? AND date=? AND kind='daily_range'
            """, (user_id, today))
            if cur.fetchone():
                continue

            send_email(
                to_addr=email,
                subject="P-Alert 気圧変動注意",
                body=f"本日({today})の気圧変動幅は {p_range:.1f} hPa です。体調にご注意ください。"
            )

            cur.execute("""
                INSERT OR IGNORE INTO alerts_sent (user_id, date, kind)
                VALUES (?, ?, ?)
            """, (user_id, today, "daily_range"))

            print(f"[MAIL] sent to {email}")

    conn.commit()
    conn.close()
    click.echo("daily-pressure-check: done")

@app.cli.command("night-forecast-alert")
def night_forecast_alert_cmd():
    """
    前夜アラート：明日の中で危険(3時間低下が閾値以上)が予測されたら、今夜メール通知する
    判定は pressure_msl（海面更正気圧）ベース
    """
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # 48hを取得（pressure_msl）
    labels, values = fetch_pressure_48h_msl()  # 既にある関数（MSLP統一済み前提）

    # 明日分だけ抽出
    t_labels = []
    t_values = []
    for lb, v in zip(labels, values):
        # labels は "YYYY-MM-DD HH:MM" 形式のはず
        if str(lb).startswith(tomorrow):
            t_labels.append(lb)
            t_values.append(float(v))

    if len(t_values) < 6:
        print(f"[WARN] 明日のデータが十分に取れませんでした: count={len(t_values)}")
        return

    # 明日の中で「最も下がる3時間帯」を探す
    best_i = None
    best_drop = 0.0  # よりマイナスが危険
    for i in range(0, len(t_values) - 3):
        drop = t_values[i + 3] - t_values[i]  # 3時間変化（マイナスが低下）
        if best_i is None or drop < best_drop:
            best_i = i
            best_drop = drop

    danger = {
        "start": t_labels[best_i],
        "end": t_labels[best_i + 3],
        "delta_hpa": round(best_drop, 1),
    }

    # リスク判定（3時間低下量ベース）
    drop3_abs = abs(danger["delta_hpa"])
    if drop3_abs >= 8:
        risk = "警戒"
        threshold = 8.0
    elif drop3_abs >= 4:
        risk = "注意"
        threshold = 4.0
    else:
        risk = "安定"
        threshold = 4.0

    print(f"[INFO] tomorrow={tomorrow} danger={danger} risk={risk}")

    # 安定なら通知しない
    if risk == "安定":
        print("[INFO] 安定のため通知なし")
        return

    conn = get_conn()
    cur = conn.cursor()

    users = cur.execute("SELECT id, email FROM users").fetchall()
    if not users:
        print("[WARN] users が0件です（送信先なし）")
        conn.close()
        return

    for u in users:
        user_id = int(u["id"])
        email = u["email"]

        # 「今日の夜」に1回だけ送る（date=today, kind='tomorrow_risk'）
        cur.execute("""
            SELECT 1 FROM alerts_sent
            WHERE user_id=? AND date=? AND kind='tomorrow_risk'
        """, (user_id, today))
        if cur.fetchone():
            print(f"[INFO] already sent (tomorrow_risk): {email}")
            continue

        subject = f"P-Alert 予報 {risk}（明日）"
        body = (
            f"明日({tomorrow})に気圧低下リスクが予測されています。\n\n"
            f"リスク: {risk}\n"
            f"最も下がる3時間帯: {danger['start']} 〜 {danger['end']}\n"
            f"3時間変化: {danger['delta_hpa']} hPa\n\n"
            f"目安: 注意=4hPa以上 / 警戒=8hPa以上（3時間変化）\n"
            f"無理のないスケジュールでどうぞ。"
        )

        send_email(to_addr=email, subject=subject, body=body)

        cur.execute("""
            INSERT OR IGNORE INTO alerts_sent (user_id, date, kind)
            VALUES (?, ?, ?)
        """, (user_id, today, "tomorrow_risk"))

        print(f"[MAIL] sent tomorrow_risk to {email}")

    conn.commit()
    conn.close()
    print("night-forecast-alert: done")
# =========================
# Main
# =========================
if __name__ == "__main__":
    send_email(
        "gclgcl0024@gmail.com",
        "【テスト】P-Alert通知",
        "これはP-Alertのテストメールです。"
    )
    app.run(debug=True)