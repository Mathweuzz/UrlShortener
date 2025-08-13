from flask import Flask
from datetime import timedelta

def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__, 
                static_folder="static", 
                template_folder="templates")

    app.config.update(
        SECRET_KEY="dev-secret-change-me",
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        BASE_URL="http://localhost:5000",
        DB_PATH="var/data.db",
        SLUG_LEN=6,
        REDIRECT_CACHE=3600,
    )
    if config_overrides:
        app.config.update(config_overrides)

    from .public import bp as public_bp
    from .admin import bp as admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from . import db as db_ext
    db_ext.init_app(app)

    @app.after_request
    def set_security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        return resp

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
