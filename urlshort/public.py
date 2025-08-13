from flask import Blueprint, render_template, current_app

bp = Blueprint("public", __name__)

@bp.get("/")
def index():
    # página inical pública
    render_template(
        "public/index.html",
        base_url=current_app.config.get("BASE_URL", "https://localhost:5000"),
    )