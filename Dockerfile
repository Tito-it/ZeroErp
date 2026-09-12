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
# ⚠️ `libharfbuzz-subset0` dal 2026-09-13 (WeasyPrint 70): senza, il subsetting
#    dei font ripiega su fontTools con l'avviso «will be unsupported in future
#    versions» a ogni stampa — cioe' con la 71 una stampa che non esce. Va
#    installato anche sulle macchine di sviluppo (`apt install`).
RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get install -y --no-install-recommends \
       libpango-1.0-0 \
       libpangoft2-1.0-0 \
       libharfbuzz0b \
       libharfbuzz-subset0 \
       libfontconfig1 \
       libcairo2 \
       libgdk-pixbuf-2.0-0 \
       shared-mime-info \
  && rm -rf /var/lib/apt/lists/*

# Copia solo requirements prima (per sfruttare cache Docker)
COPY backend/requirements.txt ./requirements.txt

# Installazione delle dipendenze, e poi RIMOZIONE DI PIP dall'immagine finale.
#
# Perche' si toglie pip. Non e' solo igiene (un'immagine di runtime non ha
# bisogno di un gestore di pacchetti): e' la correzione di due segnalazioni
# HIGH che facevano fallire il gate Trivy della CI, `msgpack 1.1.2` e
# `setuptools 70.3.0`. Nessuno dei due e' in `requirements.txt`: sono le copie
# VENDORIZZATE dentro pip, elencate nel suo `_vendor/vendor.txt`. Verificato
# scaricando l'ultimo pip pubblicato (26.2.1): vendorizza esattamente quelle due
# versioni, quindi `pip install -U pip` NON le corregge e non esiste una
# versione di pip che lo faccia. Sono codice del gestore di pacchetti, non
# raggiungibile dall'applicazione — ma finche' pip resta nell'immagine, per uno
# scanner sono pacchetti installati a tutti gli effetti, e ha ragione lui.
#
# Tutto in un solo RUN: se la rimozione stesse in un layer a parte, pip
# resterebbe comunque dentro quello precedente e lo scanner lo troverebbe lo
# stesso. `wheel` va disinstallato PRIMA di pip, altrimenti non c'e' piu' nessuno
# che possa farlo.
#
# ℹ️ Se in un container serve pip per diagnosi: `python -m ensurepip` lo
# ripristina — il modulo della standard library resta.
RUN python -m pip install --no-cache-dir -U pip wheel \
  && python -m pip install --no-cache-dir -r requirements.txt \
  && python -m pip uninstall -y wheel \
  && python -m pip uninstall -y pip

# Ora copia il codice
COPY backend/ .

CMD ["gunicorn","zeroerp_backend.wsgi:application","--bind","0.0.0.0:8000","--workers","2","--timeout","60"]
