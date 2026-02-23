from flask import Blueprint, render_template

settei_bp = Blueprint("settei", __name__, url_prefix="/settei")

@settei_bp.route("/")
def settei_home():
    return render_template("settei.html")