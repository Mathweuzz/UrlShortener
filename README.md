# URL Shortener (Flask + sqlite3)

MVP de encurtador de URLs com analytics, feito em Flask (sem ORM), banco sqlite3 (stdlib) e Jinja.

## Rodar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask
flask --app urlshort.app run --debug