from __future__ import annotations
import sqlite3, secrets, logging
from typing import Optional
from urllib.parse import urlparse
from flask import Blueprint, request, jsonify, current_app, abort, make_response
from .db import get_db
from .security import check_rate_limit
from . import analytics as an

bp = Blueprint("api", __name__)
log = logging.getLogger("app")
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def _auth_or_401():
    want = current_app.config.get("API_TOKEN")
    got = request.headers.get("Authorization", "")
    if not want or not got.startswith("Bearer "):
        resp = make_response(jsonify({"error": "unauthorized"}), 401)
        resp.headers["WWW-Authenticate"] = 'Bearer realm="api"'
        return resp
    token = got.split(" ", 1)[1]
    if token != want:
        resp = make_response(jsonify({"error": "unauthorized"}), 401)
        resp.headers["WWW-Authenticate"] = 'Bearer error="invalid_token"'
        return resp
    return None

def _is_valid_http_url(u: str) -> bool:
    if not u or len(u) > 2048:
        return False
    p = urlparse(u)
    return p.scheme in ("http", "https") and bool(p.netloc)

def _base62_slug(n: int = 6) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))

@bp.post("/links")
def api_create_link():
    unauth = _auth_or_401()
    if unauth is not None:
        return unauth

    check_rate_limit(scope="api-create")

    if not request.is_json:
        return jsonify({"error": "expected application/json"}), 400
    data = request.get_json(silent=True) or {}
    target_url = (data.get("target_url") or "").strip()
    is_permanent = 1 if bool(data.get("is_permanent", True)) else 0

    if not _is_valid_http_url(target_url):
        return jsonify({"error": "invalid url"}), 400

    slug_req = data.get("slug")
    if slug_req:
        if not (1 <= len(slug_req) <= int(current_app.config.get("SLUG_LEN", 6)) * 2):
            return jsonify({"error": "invalid slug length"}), 400
        if any(ch not in ALPHABET for ch in slug_req):
            return jsonify({"error": "slug must be base62"}), 400

    db = get_db()
    slug_len = int(current_app.config.get("SLUG_LEN", 6))
    slug = None

    if slug_req:
        try:
            db.execute(
                "INSERT INTO links (slug, target_url, is_permanent) VALUES (?,?,?)",
                (slug_req, target_url, is_permanent),
            )
            db.commit()
            slug = slug_req
        except sqlite3.IntegrityError:
            return jsonify({"error": "slug conflict"}), 409
    else:
        for _ in range(10):
            cand = _base62_slug(slug_len)
            try:
                db.execute(
                    "INSERT INTO links (slug, target_url, is_permanent) VALUES (?,?,?)",
                    (cand, target_url, is_permanent),
                )
                db.commit()
                slug = cand
                break
            except sqlite3.IntegrityError:
                continue
        if not slug:
            return jsonify({"error": "failed to allocate slug"}), 500

    short_url = f"{current_app.config.get('BASE_URL', '').rstrip('/')}/{slug}"
    log.info("api.create slug=%s is_perm=%s target=%s", slug, is_permanent, target_url)

    resp = jsonify({
        "slug": slug,
        "short_url": short_url,
        "target_url": target_url,
        "is_permanent": bool(is_permanent)
    })
    return resp, 201, {"Location": short_url}

@bp.get("/links/<slug>")
def api_get_link(slug: str):

    unauth = _auth_or_401()
    if unauth is not None:
        return unauth

    check_rate_limit(scope="api-get")

    db = get_db()
    link = an.get_link_by_slug(db, slug)
    if not link:
        return jsonify({"error": "not found"}), 404

    start = request.args.get("start")
    end = request.args.get("end")
    aggregate = request.args.get("aggregate")


    if aggregate == "day":
        per_day = an.clicks_per_day(db, link_id=link["id"], start=start, end=end)
        clicks_total = sum(r["clicks"] for r in per_day) if per_day else 0
        return jsonify({
            "slug": link["slug"],
            "target_url": link["target_url"],
            "is_permanent": bool(link["is_permanent"]),
            "created_at": link["created_at"],
            "clicks_total": clicks_total,
            "clicks_per_day": [{"day": r["day"], "clicks": r["clicks"]} for r in per_day],
            "short_url": f"{current_app.config.get('BASE_URL', '').rstrip('/')}/{link['slug']}"
        })

    row = db.execute(
        """
        SELECT COUNT(*) AS n
        FROM clicks
        WHERE link_id = ?
          AND (? IS NULL OR ts >= ? || ' 00:00:00')
          AND (? IS NULL OR ts <  date(?,'+1 day'))
        """,
        (link["id"], start, start, end, end)
    ).fetchone()
    clicks_total = int(row["n"]) if row else 0

    return jsonify({
        "slug": link["slug"],
        "target_url": link["target_url"],
        "is_permanent": bool(link["is_permanent"]),
        "created_at": link["created_at"],
        "clicks_total": clicks_total,
        "short_url": f"{current_app.config.get('BASE_URL', '').rstrip('/')}/{link['slug']}"
    })
