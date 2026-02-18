from flask import Flask, render_template, request, redirect, url_for, flash, session
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from config import Config
from models import db, User, SymptomLog
from services import fetch_pressure_forecast, pressure_change_max
from tasks import run_pressure_alert_check

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # ---- scheduler: 1時間ごとに通知チェック（発表デモならこれで十分）
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(lambda: run_pressure_alert_check(app), "interval", minutes=60)
    scheduler.start()

    # --------------------
    # helpers
    # --------------------
    def current_user():
        uid = session.get("user_id")
        if not uid:
            return None
        return User.query.get(uid)

    def login_required():
        if not session.get("user_id"):
            flash("ログインが必要です。", "warning")
            return False
        return True

    # --------------------
    # routes
    # --------------------
    @app.route("/")
    def index():
        return render_template("index.html", user=current_user())

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not email or not password:
                flash("メールとパスワードを入力してください。", "danger")
                return redirect(url_for("register"))

            if User.query.filter_by(email=email).first():
                flash("そのメールは既に登録されています。", "warning")
                return redirect(url_for("register"))

            u = User(email=email, threshold_hpa=app.config["PRESSURE_CHANGE_THRESHOLD_HPA"],
                     lat=app.config["DEFAULT_LAT"], lon=app.config["DEFAULT_LON"])
            u.set_password(password)
            db.session.add(u)
            db.session.commit()

            flash("登録しました。ログインしてください。", "success")
            return redirect(url_for("login"))

        return render_template("register.html", user=current_user())

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            u = User.query.filter_by(email=email).first()
            if not u or not u.check_password(password):
                flash("メールまたはパスワードが違います。", "danger")
                return redirect(url_for("login"))

            session["user_id"] = u.id
            flash("ログインしました。", "success")
            return redirect(url_for("dashboard"))

        return render_template("login.html", user=current_user())

    @app.route("/logout")
    def logout():
        session.clear()
        flash("ログアウトしました。", "info")
        return redirect(url_for("index"))

    @app.route("/dashboard")
    def dashboard():
        if not login_required():
            return redirect(url_for("login"))

        u = current_user()
        series = fetch_pressure_forecast(u.lat, u.lon, app.config["FORECAST_HOURS"])
        maxdiff = pressure_change_max(series)

        return render_template(
            "dashboard.html",
            user=u,
            series=series,
            maxdiff=maxdiff,
            now=datetime.now(),
        )

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        if not login_required():
            return redirect(url_for("login"))

        u = current_user()

        if request.method == "POST":
            u.notify_enabled = True if request.form.get("notify_enabled") == "on" else False

            # 数値の安全変換
            def to_float(val, default):
                try:
                    return float(val)
                except:
                    return default

            u.threshold_hpa = to_float(request.form.get("threshold_hpa"), u.threshold_hpa)
            u.lat = to_float(request.form.get("lat"), u.lat)
            u.lon = to_float(request.form.get("lon"), u.lon)

            db.session.commit()
            flash("設定を保存しました。", "success")
            return redirect(url_for("settings"))

        return render_template("settings.html", user=u)

    @app.route("/symptoms/new", methods=["GET", "POST"])
    def symptom_new():
        if not login_required():
            return redirect(url_for("login"))
        u = current_user()

        if request.method == "POST":
            symptom = request.form.get("symptom", "").strip()
            severity = request.form.get("severity", "3").strip()
            memo = request.form.get("memo", "").strip()

            if not symptom:
                flash("症状名を入力してください。", "danger")
                return redirect(url_for("symptom_new"))

            try:
                sev = int(severity)
                if sev < 1 or sev > 5:
                    raise ValueError()
            except:
                flash("重さ(1〜5)を正しく選んでください。", "danger")
                return redirect(url_for("symptom_new"))

            log = SymptomLog(user_id=u.id, symptom=symptom, severity=sev, memo=memo)
            db.session.add(log)
            db.session.commit()

            flash("体調を記録しました。", "success")
            return redirect(url_for("symptom_list"))

        return render_template("symptom_new.html", user=u)

    @app.route("/symptoms")
    def symptom_list():
        if not login_required():
            return redirect(url_for("login"))
        u = current_user()

        logs = SymptomLog.query.filter_by(user_id=u.id).order_by(SymptomLog.logged_at.desc()).limit(50).all()
        return render_template("symptom_list.html", user=u, logs=logs)

    # デモ用：ボタンで今すぐ通知チェック（発表でウケるやつ）
    @app.route("/run-check")
    def run_check_now():
        if not login_required():
            return redirect(url_for("login"))
        run_pressure_alert_check(app)
        flash("通知チェックを実行しました（メール設定が無い場合はコンソール出力です）。", "info")
        return redirect(url_for("dashboard"))

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
