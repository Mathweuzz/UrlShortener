import os
import sqlite3
from flask import current_app, g
import click

DEFAULT_DB_PATH = "var/data.db"

def get_db() -> sqlite3.Connection:
    """
    Retorna uma conexão SQLite por request
    """
    if "db" not in g:
        db_path = current_app.config.get("DB_PATH", DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        conn = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        # Segurança/consistência
        conn.execute("PRAGMA foreign_keys = ON;")
        # Melhor para concorrência leitura/escrita
        conn.execute("PRAGMA journal_mode = WAL;")
        g.db = conn
    return g.db

def close_db(e=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    db = get_db()
    with current_app.open_resource("models.sql", mode="r") as f:
        sql = f.read()
    db.executescript(sql)
    db.commit()

@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("Banco inicializando em {}".format(current_app.config.get("DB_PATH", DEFAULT_DB_PATH)))

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)