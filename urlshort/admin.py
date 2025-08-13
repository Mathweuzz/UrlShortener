from __future__ import annotations
from datetime import datetime, timedelta
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
    Filtros GET: ?start=YYYY-MM-DD&end=YYYY-MM-DD
    """
    db = get_db()
    start = _parse_date(request.args.get("start"))
    end = _parse_date(request.args.get("end"))

    rows = an.totals_by_link(db, start=start, end=end, limit=200)
    return render_template("admin/index.html", rows=rows, start=start, end=end)

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

    # padrão: últimos 30 dias se nenhum filtro
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
        link=link,
        per_day=per_day,
        recent=recent,
        start=start,
        end=end,
        total_clicks=total_clicks,
        base_url=current_app.config.get("BASE_URL", "http://localhost:5000"),
    )
