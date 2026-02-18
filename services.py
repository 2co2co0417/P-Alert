import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Tuple

def fetch_pressure_forecast(lat: float, lon: float, hours: int) -> List[Tuple[str, float]]:
    """
    Open-Meteoから surface_pressure の時系列を取る。
    戻り: [(ISO時間文字列, hPa), ...]
    """
    url = "https://api.open-meteo.com/v1/jma"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "surface_pressure",
        "forecast_days": 2,
        "timezone": "Asia/Tokyo",
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    times = data["hourly"]["time"]
    pressures = data["hourly"]["surface_pressure"]

    result = []
    for t, p in zip(times[:hours], pressures[:hours]):
        # 単位揺れ吸収：もしPaっぽく大きい値ならhPaへ
        # 例: 101325 (Pa) -> 1013.25 (hPa)
        p_hpa = p / 100.0 if p > 2000 else p
        result.append((t, float(p_hpa)))

    return result

def pressure_change_max(series: List[Tuple[str, float]]) -> float:
    """
    連続平均との差分の最大値（hPa）
    """
    if len(series) < 2:
        return 0.0
    max_diff = 0.0
    for i in range(1, len(series)):
        diff = abs(series[i][1] - series[i-1][1])
        if diff > max_diff:
            max_diff = diff
    return max_diff

def send_email_smtp(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    mail_from: str,
    to_email: str,
    subject: str,
    body: str,
):
    msg = MIMEMultipart()
    msg["From"] = mail_from
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
