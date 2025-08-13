from __future__ import annotations
from typing import Optional
from sqlite3 import Connection

def totals_by_link(
    db: Connection,
    start: Optional[str] = None,
    end: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """
    Retorna links com total de cliques no intervalo (opcional).
    Inclui links sem cliques. Busca por q em slug/target_url.
    """
    join_extra = []
    join_params = []
    if start:
        join_extra.append("c.ts >= ?")
        join_params.append(start + " 00:00:00")
    if end:
        join_extra.append("c.ts < date(?, '+1 day')")
        join_params.append(end)
    join_sql = (" AND " + " AND ".join(join_extra)) if join_extra else ""

    where = []
    where_params = []
    if q:
        where.append("(l.slug LIKE ? OR l.target_url LIKE ?)")
        like = f"%{q}%"
        where_params.extend([like, like])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
    SELECT
      l.id, l.slug, l.target_url, l.is_permanent, l.created_at,
      COALESCE(COUNT(c.id), 0) AS clicks
    FROM links l
    LEFT JOIN clicks c
      ON c.link_id = l.id {join_sql}
    {where_sql}
    GROUP BY l.id
    ORDER BY l.created_at DESC
    LIMIT ? OFFSET ?
    """
    params = (*join_params, *where_params, limit, offset)
    return db.execute(sql, params).fetchall()

def count_links(db: Connection, q: Optional[str] = None) -> int:
    """
    Conta quantos links existem (para paginação), filtrando por q (slug/target_url).
    *Não* depende de start/end, pois o filtro de data é para os cliques.
    """
    where = []
    params = []
    if q:
        where.append("(slug LIKE ? OR target_url LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    row = db.execute(f"SELECT COUNT(*) AS n FROM links {where_sql}", params).fetchone()
    return int(row["n"]) if row else 0

def clicks_per_day(db: Connection, link_id: int, start: Optional[str] = None, end: Optional[str] = None):
    where = ["link_id = ?"]
    params = [link_id]
    if start:
        where.append("ts >= ?")
        params.append(start + " 00:00:00")
    if end:
        where.append("ts < date(?, '+1 day')")
        params.append(end)
    sql = f"""
    SELECT date(ts) AS day, COUNT(*) AS clicks
    FROM clicks
    WHERE {" AND ".join(where)}
    GROUP BY day
    ORDER BY day
    """
    return db.execute(sql, params).fetchall()

def recent_clicks(db: Connection, link_id: int, start: Optional[str] = None, end: Optional[str] = None, limit: int = 100):
    where = ["link_id = ?"]
    params = [link_id]
    if start:
        where.append("ts >= ?")
        params.append(start + " 00:00:00")
    if end:
        where.append("ts < date(?, '+1 day')")
        params.append(end)
    sql = f"""
    SELECT ts, ip, user_agent, referrer
    FROM clicks
    WHERE {" AND ".join(where)}
    ORDER BY ts DESC
    LIMIT ?
    """
    return db.execute(sql, (*params, limit)).fetchall()

def get_link_by_slug(db: Connection, slug: str):
    return db.execute(
        "SELECT id, slug, target_url, is_permanent, created_at FROM links WHERE slug = ?",
        (slug,),
    ).fetchone()