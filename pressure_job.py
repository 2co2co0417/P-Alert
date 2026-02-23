import os
import sqlite3
from datetime import datetime, timedelta, date
import requests
import smtplib
from email.mime.text import MIMEText

DB_PATH = os.getenv("DB_PATH", "mvp.db")

# 今治あたり（例）※あなたのアプリの設定に合わせて統一してください
LAT = float(os.getenv("LAT", "33.59"))
LON = float(os.getenv("LON", "132.97"))

THRESHOLD_HPA = float(os.getenv("ALERT_THRESHOLD_HPA", "4.0"))  # ±4hPa

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER)

def _conn():
    return sqlite3.connect(DB_PATH)

def fetch_current_pressure_hpa():
    url = (
        "https://api.open-meteo.com/v1/jma"
        f"?latitude={LAT}&longitude={LON}"
        "&hourly=pressure_msl"
        "&timezone=Asia%2FTokyo"
        "&forecast_days=2"
    )
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()

    times = data["hourly"]["time"]
    pressures = data["hourly"]["pressure_msl"]  # ← ここが画面と揃うはず

    now = datetime.now()
    best_i = 0
    best_diff = None
    for i, t in enumerate(times):
        dt = datetime.fromisoformat(t)
        diff = abs((dt - now).total_seconds())
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_i = i

    val = pressures[best_i]

    # Paで来てもhPaで来ても吸収（保険）
    if val > 2000:
        hpa = val / 100.0
    else:
        hpa = float(val)

    picked_time = times[best_i]
    return hpa, picked_time

def get_users(cur):
    # usersテーブルに email がある前提
    cur.execute("SELECT id, email FROM users")
    return cur.fetchall()

def already_sent(cur, user_id, yyyy_mm_dd, kind):
    cur.execute(
        "SELECT 1 FROM alerts_sent WHERE user_id=? AND date=? AND kind=?",
        (user_id, yyyy_mm_dd, kind),
    )
    return cur.fetchone() is not None

def mark_sent(cur, user_id, yyyy_mm_dd, kind):
    cur.execute(
        "INSERT OR IGNORE INTO alerts_sent(user_id, date, kind) VALUES (?, ?, ?)",
        (user_id, yyyy_mm_dd, kind),
    )

def upsert_pressure(cur, user_id, yyyy_mm_dd, pressure_hpa):
    cur.execute(
        """
        INSERT INTO pressure_daily(user_id, date, pressure_hpa)
        VALUES(?, ?, ?)
        ON CONFLICT(user_id, date) DO UPDATE SET pressure_hpa=excluded.pressure_hpa
        """,
        (user_id, yyyy_mm_dd, pressure_hpa),
    )

def get_pressure(cur, user_id, yyyy_mm_dd):
    cur.execute(
        "SELECT pressure_hpa FROM pressure_daily WHERE user_id=? AND date=?",
        (user_id, yyyy_mm_dd),
    )
    row = cur.fetchone()
    return None if row is None else float(row[0])

def send_email(to_addr, subject, body):
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        raise RuntimeError("SMTP設定が未設定です（SMTP_HOST/USER/PASS など）")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = to_addr

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

def run_daily_pressure_check():
    today = date.today()
    yday = today - timedelta(days=1)
    today_s = today.isoformat()
    yday_s = yday.isoformat()

    current_hpa, picked_time = fetch_current_pressure_hpa()

    with _conn() as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        users = get_users(cur)

        for (user_id, email) in users:
            # ① 今日の気圧を保存
            upsert_pressure(cur, user_id, today_s, current_hpa)

            # ② 前日データがなければ比較できない（初回は保存だけ）
            yday_hpa = get_pressure(cur, user_id, yday_s)
            if yday_hpa is None:
                continue

            delta = current_hpa - yday_hpa  # 今日 - 昨日
            kind = "daily_delta"

            # ③ しきい値超え + 未送信なら送る
            if abs(delta) >= THRESHOLD_HPA and not already_sent(cur, user_id, today_s, kind):
                direction = "上昇" if delta > 0 else "下降"
                subject = f"[P-Alert] 気圧変化 {direction} {abs(delta):.1f}hPa（前日比）"
                body = (
                    f"計測時刻（採用データ）: {picked_time}\n"
                    f"今日: {current_hpa:.1f} hPa\n"
                    f"昨日: {yday_hpa:.1f} hPa\n"
                    f"前日比: {delta:+.1f} hPa\n\n"
                    f"判定: ±{THRESHOLD_HPA:.1f}hPa を超えました。\n"
                    "体調に気をつけて、無理せずお過ごしください。"
                )
                send_email(email, subject, body)
                mark_sent(cur, user_id, today_s, kind)

        con.commit()
    
if __name__ == "__main__":
    run_daily_pressure_check()