ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Patch di sicurezza del sistema operativo + librerie native per WeasyPrint.
#
# `apt-get upgrade` NON e' cosmesi: l'immagine base `python:*-slim` si porta
# dietro i pacchetti Debian con cui e' stata pubblicata, e fra quel momento e
# oggi Debian ne ha gia' corretti alcuni. Trivy, nel job `docker` della CI, li
# vede come HIGH/CRITICAL *con correzione disponibile* — quindi `ignore-unfixed`
# non li filtra — e fa uscire 1 il gate. Senza questa riga il job e' rosso per
# vulnerabilita' che non stanno nel nostro codice ma che noi possiamo comunque
# chiudere: applicarle e' la risposta giusta, silenziare lo scanner no.
#
# ⚠️ Il layer resta in cache finche' l'istruzione e i layer sopra non cambiano:
# l'aggiornamento NON si ri-applica a ogni build. Il rinfresco naturale arriva
# quando cambia il digest dell'immagine base (che Docker ricostruisce spesso).
# Se il gate Trivy tornasse rosso su pacchetti di sistema, e' qui che si guarda.
#
# Le librerie native (Pango/Cairo/HarfBuzz/PixBuf) servono a WeasyPrint per il
# rendering PDF (motore documentale parametrico, Decisione 73): sono caricate
# via cffi a runtime e senza di esse l'import di weasyprint fallisce in
# container.
RUN apt-get update \
  && apt-get upgrade -y \
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
