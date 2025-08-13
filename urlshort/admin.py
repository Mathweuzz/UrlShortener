from __future__ import annotations
from datetime import datetime, timedelta
from urllib.parse import urlencode
from flask import Blueprint, render_template, request, redirect, url_for, current_app, abort
from .db import get_db
from . import analytics as an

bp = Blueprint("admin", __name__)

def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None

@bp.get("/")
def admin_home():
    """
    Lista links com total de cliques.
    Filtros GET: ?q=...&start=YYYY-MM-DD&end=YYYY-MM-DD&page=1
    """
    db = get_db()
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))
    q = (request.args.get("q") or "").strip() or None

    page_size = int(current_app.config.get("PAGE_SIZE", 20))
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1
    offset = (page - 1) * page_size

    rows = an.totals_by_link(db, start=start, end=end, q=q, limit=page_size, offset=offset)
    total = an.count_links(db, q=q)
    total_pages = max(1, (total + page_size - 1) // page_size)

    args = {}
    if q: args["q"] = q
    if start: args["start"] = start
    if end: args["end"] = end
    has_prev = page > 1
    has_next = page < total_pages
    prev_url = url_for("admin.admin_home") + "?" + urlencode({**args, "page": page - 1}) if has_prev else None
    next_url = url_for("admin.admin_home") + "?" + urlencode({**args, "page": page + 1}) if has_next else None

    return render_template(
        "admin/index.html",
        rows=rows, start=start, end=end, q=q,
        page=page, total_pages=total_pages,
        has_prev=has_prev, has_next=has_next,
        prev_url=prev_url, next_url=next_url,
    )

@bp.get("/<slug>")
def admin_detail(slug: str):
    """
    Detalhe de um link: cliques por dia + tabela de cliques recentes.
    Filtros GET: ?start=YYYY-MM-DD&end=YYYY-MM-DD
    """
    db = get_db()
    link = an.get_link_by_slug(db, slug)
    if not link:
        abort(404)

    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))
    if not start and not end:
        end_dt = datetime.utcnow().date()
        start_dt = end_dt - timedelta(days=30)
        start, end = start_dt.isoformat(), end_dt.isoformat()

    per_day = an.clicks_per_day(db, link_id=link["id"], start=start, end=end)
    recent = an.recent_clicks(db, link_id=link["id"], start=start, end=end, limit=100)
    total_clicks = sum(r["clicks"] for r in per_day) if per_day else 0

    return render_template(
        "admin/detail.html",
        link=link, per_day=per_day, recent=recent,
        start=start, end=end, total_clicks=total_clicks,
        base_url=current_app.config.get("BASE_URL", "http://localhost:5000"),
    )
