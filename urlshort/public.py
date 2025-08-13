from __future__ import annotations
import sqlite3
import secrets
from urllib.parse import urlparse
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
from .db import get_db

bp = Blueprint("public", __name__)

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def base62_slug(n: int = 6) -> str:
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
            # Re-render com 400 em caso de erro de validação
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
        # PRG 
        return redirect(url_for("public.index"))

    # get lista recentes
    links = db.execute(
        "SELECT id, slug, target_url, is_permanent, created_at FROM links ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    return render_template("public/index.html", base_url=base_url, links=links)
