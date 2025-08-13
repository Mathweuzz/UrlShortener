from __future__ import annotations
import sqlite3
import secrets
from urllib.parse import urlparse
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
from .db import get_db

bp = Blueprint("public", __name__)

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def base62_slug(n: int = 6) -> str:
    # Usa fonte criptográfica para evitar previsibilidade simples
    return "".join(secrets.choice(ALPHABET) for _ in range(n))

def get_client_ip() -> str | None:
    # Usa o primeiro IP do X-Forwarded-For quando existir
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr

def is_valid_http_url(u: str) -> bool:
    if not u or len(u) > 2048:
        return False
    p = urlparse(u)
    return p.scheme in ("http", "https") and bool(p.netloc)

def is_loop_to_base(u: str, base: str) -> bool:
    # Bloqueia encurtar qualquer URL que aponte para o próprio domínio base
    try:
        pu, pb = urlparse(u), urlparse(base)
        if not pb.netloc:
            return False
        return (pu.netloc.lower() == pb.netloc.lower()) or u.startswith(base)
    except Exception:
        return False

@bp.route("/", methods=["GET", "POST"])
def index():
    db = get_db()
    base_url = current_app.config.get("BASE_URL", "http://localhost:5000")

    if request.method == "POST":
        target_url = (request.form.get("target_url") or "").strip()
        is_perm = 1 if (request.form.get("is_permanent") == "1") else 0

        # Validações
        if not is_valid_http_url(target_url):
            flash("URL inválida: use http(s) e até 2048 caracteres.", "error")
            links = db.execute(
                "SELECT id, slug, target_url, is_permanent, created_at FROM links ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
            return render_template("public/index.html", base_url=base_url, links=links), 400

        if is_loop_to_base(target_url, base_url):
            flash("Loop bloqueado: não é permitido encurtar o próprio domínio.", "error")
            links = db.execute(
                "SELECT id, slug, target_url, is_permanent, created_at FROM links ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
            return render_template("public/index.html", base_url=base_url, links=links), 400

        created_ip = get_client_ip()

        # Geração de slug com checagem de colisão via UNIQUE
        slug_len = int(current_app.config.get("SLUG_LEN", 6))
        max_tries = 10
        slug = None
        for _ in range(max_tries):
            candidate = base62_slug(slug_len)
            try:
                db.execute(
                    "INSERT INTO links (slug, target_url, is_permanent, created_ip) VALUES (?,?,?,?)",
                    (candidate, target_url, is_perm, created_ip),
                )
                db.commit()
                slug = candidate
                break
            except sqlite3.IntegrityError:
                continue

        if not slug:
            flash("Falha ao gerar slug único. Tente novamente.", "error")
            links = db.execute(
                "SELECT id, slug, target_url, is_permanent, created_at FROM links ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
            return render_template("public/index.html", base_url=base_url, links=links), 500

        short_url = f"{base_url.rstrip('/')}/{slug}"
        flash(f"Link criado: {short_url}", "success")
        return redirect(url_for("public.index"))

    # GET: lista recentes
    links = db.execute(
        "SELECT id, slug, target_url, is_permanent, created_at FROM links ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    return render_template("public/index.html", base_url=base_url, links=links)

@bp.get("/<slug>")
def follow(slug: str):
    """
    Resolve o slug, registra o clique e redireciona (301/302).
    """
    db = get_db()
    row = db.execute(
        "SELECT id, target_url, is_permanent FROM links WHERE slug = ?",
        (slug,),
    ).fetchone()

    if not row:
        # 404 amigável
        return render_template("public/not_found.html", slug=slug), 404

    # Registrar clique
    ip = get_client_ip()
    ua = request.headers.get("User-Agent")
    ref = request.headers.get("Referer")  # (sic) nome do cabeçalho HTTP
    db.execute(
        "INSERT INTO clicks (link_id, ip, user_agent, referrer) VALUES (?,?,?,?)",
        (row["id"], ip, ua, ref),
    )
    db.commit()

    # Redirecionar com status apropriado
    code = 301 if row["is_permanent"] else 302
    resp = redirect(row["target_url"], code=code)

    # Cabeçalhos de cache apropriados
    if code == 301:
        max_age = int(current_app.config.get("REDIRECT_CACHE", 3600))
        resp.headers["Cache-Control"] = f"public, max-age={max_age}"
    else:
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"

    return resp
