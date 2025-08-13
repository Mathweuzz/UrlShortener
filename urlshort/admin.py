from flask import Blueprint, render_template

bp = Blueprint("admin", __name__)

@bp.get("/")
def admin_home():
    # painel admin 
    return render_template("admin/index.html")