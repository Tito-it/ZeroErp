FROM python:3.13-slim

WORKDIR /app

# Copia solo requirements prima (per sfruttare cache Docker)
COPY backend/requirements.txt ./requirements.txt

# Upgrade pip + wheel (fix CVE) e install deps
RUN python -m pip install --no-cache-dir -U pip wheel \
  && python -m pip install --no-cache-dir -r requirements.txt

# Ora copia il codice
COPY backend/ .

CMD ["gunicorn","zeroerp_backend.wsgi:application","--bind","0.0.0.0:8000","--workers","2","--timeout","60"]
