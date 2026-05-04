ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Librerie native richieste da WeasyPrint per il rendering PDF (motore
# documentale parametrico, Decisione 73). Pango/Cairo/HarfBuzz/PixBuf
# sono caricate via cffi a runtime; senza di esse l'import di weasyprint
# fallisce in container.
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
       libpango-1.0-0 \
       libpangoft2-1.0-0 \
       libharfbuzz0b \
       libfontconfig1 \
       libcairo2 \
       libgdk-pixbuf-2.0-0 \
       shared-mime-info \
  && rm -rf /var/lib/apt/lists/*

# Copia solo requirements prima (per sfruttare cache Docker)
COPY backend/requirements.txt ./requirements.txt

# Upgrade pip + wheel (fix CVE) e install deps
RUN python -m pip install --no-cache-dir -U pip wheel \
  && python -m pip install --no-cache-dir -r requirements.txt

# Ora copia il codice
COPY backend/ .

CMD ["gunicorn","zeroerp_backend.wsgi:application","--bind","0.0.0.0:8000","--workers","2","--timeout","60"]
