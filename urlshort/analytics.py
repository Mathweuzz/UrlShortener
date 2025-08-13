from __future__ import annotations
from typing import Optional
from sqlite3 import Connection

def totals_by_link(db: Connection, start: Optional[str] = None, end: Optional[str] = None, limit: int = 200):
    """
    Retorna links com total de cliques no intervalo (opcional).
    start/end em 'YYYY-MM-DD'. Inclui links sem cliques.
    """
    join_extra = []
    params = []
    if start:
        join_extra.append("c.ts >= ?")
        params.append(start + " 00:00:00")
    if end:
        join_extra.append("c.ts < date(?, '+1 day')")
        params.append(end)

    join_sql = ""
    if join_extra:
        join_sql = " AND " + " AND ".join(join_extra)

    sql = f"""
    SELECT
      l.id, l.slug, l.target_url, l.is_permanent, l.created_at,
      COALESCE(COUNT(c.id), 0) AS clicks
    FROM links l
    LEFT JOIN clicks c
      ON c.link_id = l.id {join_sql}
    GROUP BY l.id
    ORDER BY l.created_at DESC
    LIMIT ?
    """
    return db.execute(sql, (*params, limit)).fetchall()

def clicks_per_day(db: Connection, link_id: int, start: Optional[str] = None, end: Optional[str] = None):
    """
    Agrupa cliques por dia (YYYY-MM-DD).
    """
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
    """
    Lista cliques recentes (com filtro opcional).
    """
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
