#!/bin/sh
set -e
python - <<'PY'
import time
from sqlalchemy import create_engine, text
from app.core.config import get_settings

url = get_settings().database_url
for attempt in range(30):
    try:
        engine = create_engine(url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        break
    except Exception as exc:
        print(f"waiting for database ({attempt}): {exc}")
        time.sleep(2)
else:
    raise SystemExit("database is not ready")
PY
alembic upgrade head
python -m app.scripts.seed
python -m app.scripts.create_admin
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
