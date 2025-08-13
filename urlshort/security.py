from __future__ import annotations
import time
import secrets
from collections import deque
from flask import request, session, current_app, abort, g

_RATE_BUCKETS: dict[str, deque[float]] = {}

def client_ip() -> str | None:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr

def _now() -> float:
    return time.time()

def check_rate_limit(scope: str, limit: int | None = None, window: int | None = None) -> bool:
    """
    Verifica/atualiza o bucket de rate limit por IP.
    Excede -> abort(429) e define Retry-After.
    """
    if limit is None:
        limit = int(current_app.config.get("RATE_LIMIT_MAX", 10))
    if window is None:
        window = int(current_app.config.get("RATE_LIMIT_WINDOW", 60))

    ip = client_ip() or "unknown"
    key = f"{scope}:{ip}"

    dq = _RATE_BUCKETS.get(key)
    now = _now()
    if dq is None:
        dq = deque()
        _RATE_BUCKETS[key] = dq

    while dq and (now - dq[0]) > window:
        dq.popleft()

    if len(dq) >= limit:
        retry_after = int(window - (now - dq[0]))
        g.rate_limited = retry_after
        abort(429)

    dq.append(now)
    return True


def generate_csrf_token() -> str:
    tok = session.get("_csrf_token")
    if not tok:
        tok = secrets.token_urlsafe(32)
        session["_csrf_token"] = tok
    return tok

def require_csrf() -> None:
    """
    Exige _csrf igual ao token da sessão para métodos de escrita.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        form_token = request.form.get("_csrf")
        sess_token = session.get("_csrf_token")
        if not (form_token and sess_token and form_token == sess_token):
            abort(400)


def init_app(app):
    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    @app.before_request
    def _limit_form_size():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            max_bytes = int(app.config.get("MAX_FORM_BYTES", 4096))
            cl = request.content_length
            if cl is not None and cl > max_bytes:
                abort(413)

    @app.errorhandler(429)
    def _handle_429(e):
        from flask import make_response
        resp = make_response(("Too Many Requests", 429))
        retry = getattr(g, "rate_limited", None)
        if retry is not None:
            resp.headers["Retry-After"] = str(retry)
        return resp
