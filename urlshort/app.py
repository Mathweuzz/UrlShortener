from flask import Flask
from datetime import timedelta

def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    app.config.update(
        SECRET_KEY="dev-secret-change-me",
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),

        BASE_URL="http://localhost:5000",
        DB_PATH="var/data.db",
        SLUG_LEN=6,

        RATE_LIMIT_MAX=10,          
        RATE_LIMIT_WINDOW=60,       
        MAX_FORM_BYTES=4096,        
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

    from . import security as sec
    sec.init_app(app)

    @app.after_request
    def set_security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self';"
        )
        return resp

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
