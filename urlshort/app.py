import os, json, time, logging, logging.config
from pathlib import Path
from flask import Flask, request, g
from datetime import timedelta

def _boolenv(v: str) -> bool:
    return str(v).lower() in ("1", "true", "yes", "on")

def _apply_env_overrides(app: Flask):
    env_specs = {
        "BASE_URL": str, "DB_PATH": str, "PAGE_SIZE": int, "SLUG_LEN": int,
        "REDIRECT_CACHE": int, "RATE_LIMIT_MAX": int, "RATE_LIMIT_WINDOW": int,
        "MAX_FORM_BYTES": int, "LOG_LEVEL": str, "DEBUG": _boolenv
    }
    for k, caster in env_specs.items():
        if k in os.environ:
            try:
                app.config[k] = caster(os.environ[k])
            except Exception:
                app.config[k] = os.environ[k]

def _load_config_and_logging(app: Flask):
    app.config.update(
        SECRET_KEY="dev-secret-change-me",
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        BASE_URL="http://localhost:5000",
        DB_PATH="var/data.db",
        PAGE_SIZE=20,
        SLUG_LEN=6,
        REDIRECT_CACHE=3600,
        RATE_LIMIT_MAX=10,
        RATE_LIMIT_WINDOW=60,
        MAX_FORM_BYTES=4096,
        LOG_LEVEL="INFO",
    )

    cfg_path = os.environ.get("APP_CONFIG", "config/config.json")
    cfg = None
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        app.config.update(cfg.get("app", {}))

    db_path = Path(app.config.get("DB_PATH", "var/data.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    log_cfg = (cfg or {}).get("logging")
    if log_cfg:
        for h in log_cfg.get("handlers", {}).values():
            fn = h.get("filename")
            if fn:
                Path(fn).parent.mkdir(parents=True, exist_ok=True)
        logging.config.dictConfig(log_cfg)
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    _apply_env_overrides(app)
    lvl = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, lvl, logging.INFO)
    logging.getLogger("app").setLevel(level)
    logging.getLogger("access").setLevel(level)

def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    _load_config_and_logging(app)
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

    @app.before_request
    def _start_timer():
        g._t0 = time.perf_counter()

    @app.after_request
    def set_security_headers_and_access_log(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self';"
        )
        try:
            dur_ms = int((time.perf_counter() - getattr(g, "_t0", time.perf_counter())) * 1000)
        except Exception:
            dur_ms = -1
        logging.getLogger("access").info(
            '%s %s %s %s %dms ua="%s" ref="%s"',
            request.remote_addr or "-",
            request.method,
            request.full_path.rstrip("?") if request.query_string else request.path,
            resp.status_code,
            dur_ms,
            request.headers.get("User-Agent", "-"),
            request.headers.get("Referer", "-"),
        )
        return resp

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)