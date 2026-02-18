from models import db, User
from services import fetch_pressure_forecast, pressure_change_max, send_email_smtp

def run_pressure_alert_check(app):
    """
    全ユーザーの設定を見て、閾値を超えたらメール。
    """
    with app.app_context():
        users = User.query.all()

        for u in users:
            if not u.notify_enabled:
                continue

            series = fetch_pressure_forecast(u.lat, u.lon, app.config["FORECAST_HOURS"])
            maxdiff = pressure_change_max(series)

            if maxdiff >= float(u.threshold_hpa):
                subject = "【P-Alert】気圧変化が大きい予報です"
                body = (
                    f"こんにちは、P-Alertです。\n\n"
                    f"今後{app.config['FORECAST_HOURS']}時間の予報で、気圧の変化が大きい可能性があります。\n"
                    f"最大差分（連続時間の差）：{maxdiff:.1f} hPa\n"
                    f"設定閾値：{u.threshold_hpa:.1f} hPa\n\n"
                    f"無理せず、休憩や水分補給を。\n"
                )

                # メール設定が未入力なら「デモとしてコンソール出力」に倒す
                if not app.config["SMTP_HOST"] or not app.config["SMTP_USER"]:
                    print(f"[DEMO ALERT] to={u.email} maxdiff={maxdiff:.1f}hPa")
                    continue

                send_email_smtp(
                    smtp_host=app.config["SMTP_HOST"],
                    smtp_port=app.config["SMTP_PORT"],
                    smtp_user=app.config["SMTP_USER"],
                    smtp_pass=app.config["SMTP_PASS"],
                    mail_from=app.config["MAIL_FROM"],
                    to_email=u.email,
                    subject=subject,
                    body=body,
                )
