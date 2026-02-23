from flask import Blueprint, render_template

# Blueprint作成
settei_bp = Blueprint("settei", __name__, url_prefix="/settei")


# 画面表示だけ
@settei_bp.route("/")
def settei_home():
    return render_template("settei.html")