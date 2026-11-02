# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Render PDF di una versione template (Tranche I).
#        Pipeline:
#         1. valida engine whitelisted (v1: solo `WEASYPRINT`,
#            Decisione 3 — engine NON hardcoded ma estensibile via
#            `documenti.render_engine_documento`);
#         2. compone il sorgente HTML con Jinja2 (variabili `{{ ... }}` e
#            cicli `{% for ... %}`, Decisione 4). Configurazione
#            `StrictUndefined` per fail-fast su variabili mancanti nel
#            context: errore parlante invece di silenzioso campo vuoto;
#         3. invoca WeasyPrint (lazy import, libreria nativa
#            Pango/Cairo/HarfBuzz/PixBuf gia' installata da Tranche B)
#            per HTML+CSS -> bytes PDF, con un `url_fetcher` NOSTRO: le
#            risorse che un template puo' caricare sono una lista chiusa
#            (`asset:<codice_interno>` e `data:`), il resto e' un errore
#            (brief-be-documenti-risorse-esterne-render-pdf §4);
#         4. la PAGINA (formato, orientamento, margini) la decidono le
#            colonne della versione, non il CSS del template (D-1 strada A e
#            R-BE-V2a, Tid 2026-10-04; `_regola_pagina`).
#
#        Errori applicativi mappati su `E_DOCUMENTI_RENDER_FAILED`:
#         - engine non in whitelist applicativa
#         - jinja: variabile mancante / sintassi malformata
#         - WeasyPrint: errore interno engine
#         - html_template vuoto o NULL
#         - risorsa rifiutata dal fetcher (schema non ammesso, asset che
#           non c'e', tetto di risorse per render superato)
# ------------------------------------------------------------

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import unquote

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError

logger = logging.getLogger(__name__)

E_RENDER_FAILED = "E_DOCUMENTI_RENDER_FAILED"

# Whitelist applicativa engine. v1: solo WeasyPrint. Decisione 3 +
# Tranche B (settings + Dockerfile native deps gia' presenti).
# Nuovi engine si aggiungono qui + lookup `render_engine_documento`.
# Match sul codice_interno IMMUTABILE: il `codice` e' l'etichetta mutabile
# (rinominabile dall'utente) e non puo' reggere la whitelist di logica.
_ENGINE_WHITELIST: frozenset[str] = frozenset({"WEASYPRINT"})


# Scopo: Costanti chiavi versione lette per il render. Centralizzate per
#        documentare il contratto col repo `_VERSIONI_PROJECTION_DETAIL`.
_VERSIONE_KEYS_REQUIRED = (
    "html_template",
    "render_engine_codice_interno",
)

# Scopo: Contratto del risolutore di asset che l'orchestratore passa al
#        render: riceve il `codice_interno` scritto dopo `asset:` e ritorna
#        `(contenuto, mime_type)`. Il PERIMETRO (emittente del template, solo
#        asset validi oggi o no) e' tutto suo: questo modulo resta puro e non
#        legge ne' DB ne' storage. Un asset che non c'e' lo segnala sollevando
#        `ServiceError`, che il render ripropaga cosi' com'e'.
RisolviAsset = Callable[[str], tuple[bytes, str]]

# Gli schemi che un template puo' caricare (lista chiusa, §4.2 del brief):
# `asset:` passa dal risolutore, `data:` non accede a niente.
# ⛔ `file:` e `http(s):` restano FUORI. Il template e' per emittente: col
#    fetcher di default leggerebbe il filesystem del backend (lo storage di un
#    altro emittente, il file delle variabili d'ambiente) o farebbe richieste
#    verso la rete interna.
_SCHEMA_ASSET = "asset"
_SCHEMA_DATA = "data"

# Tetto degli `asset:` caricati in UN render (§4.4, deciso da Tid il
# 2026-10-01). WeasyPrint non ha guardie sui cicli di `@import`: un CSS che
# importa se stesso ricorre senza fine, e il fetcher vede le singole URL, non
# la catena. Un tetto per render copre in un colpo solo cicli, import annidati
# e SVG che richiamano altre risorse.
# ⭐ Conta SOLO `asset:` (Tid, 2026-10-01): un `data:` porta il contenuto
#    scritto nell'URL stesso, quindi non puo' richiamare se stesso, e ogni
#    catena che si allunga passa per forza da un `asset:`. Contarlo fermava
#    un template con molte icone inline senza nessun ciclo.
# ⚠️ Le immagini WeasyPrint le tiene in cache per URL: lo stesso logo su ogni
#    pagina conta una volta sola.
_MAX_RISORSE_PER_RENDER = 50


# Scopo: Render del documento PDF a partire dalla versione template e dal
#        contesto applicativo. Funzione pura (no DB, no storage):
#        l'orchestratore di Tranche I fa setup + persistence; questo modulo
#        isola l'engine. `risolvi_asset` e' obbligatorio: ogni chiamante
#        dichiara il perimetro degli asset che il suo render vede.
def render_pdf(
    *,
    template_versione: dict[str, Any],
    context: dict[str, Any],
    risolvi_asset: RisolviAsset,
) -> bytes:
    _guard_versione_minima(template_versione)
    engine = (template_versione.get("render_engine_codice_interno") or "").upper()
    if engine not in _ENGINE_WHITELIST:
        ErrorManager.raise_error(
            code=E_RENDER_FAILED,
            message=f"Render engine '{engine}' non supportato in v1.",
            detail=f"engine_ammessi={sorted(_ENGINE_WHITELIST)!r}",
        )

    html_source = _render_html_with_jinja(
        template_versione["html_template"], context,
    )
    css_source = template_versione.get("css_template") or ""
    return _render_with_weasyprint(
        html_source, css_source,
        css_pagina=_regola_pagina(template_versione),
        risolvi_asset=risolvi_asset,
    )


# =====================================================================
# Helpers privati
# =====================================================================


# Scopo: Verifica che la versione abbia i campi minimi richiesti per il render.
#        `html_template` e' la sorgente principale; markdown_template e'
#        opzionale e in v1 non viene processato (Decisione 4: markdown solo
#        per blocchi controllati pre-convertiti).
def _guard_versione_minima(versione: dict[str, Any]) -> None:
    for key in _VERSIONE_KEYS_REQUIRED:
        if not versione.get(key):
            ErrorManager.raise_error(
                code=E_RENDER_FAILED,
                message=f"Versione template incompleta: campo '{key}' mancante.",
                detail=f"versione_id={versione.get('id')!r}",
            )


# I campi della versione da cui si compone la pagina: tutti NOT NULL a DB
# (`template_documenti_versioni`), e `_VERSIONI_PROJECTION_DETAIL` li porta.
_CAMPI_PAGINA = (
    "page_format",
    "page_orientation",
    "margin_top_mm",
    "margin_right_mm",
    "margin_bottom_mm",
    "margin_left_mm",
)

# Un codice di vocabolario e' un identificatore: finisce in un foglio CSS, e
# qualunque altra cosa (spazi, `;`, `}`) vorrebbe dire una regola in piu'.
_RE_CODICE_PAGINA = re.compile(r"^[A-Za-z0-9_]+$")


# Scopo: La regola `@page` dalle colonne della versione: formato e
#        orientamento (codici dei vocabolari `documenti.formati_pagina` e
#        `orientamenti_pagina`, che sono gia' parole CSS: `A4`, `A3`,
#        `LETTER`, `PORTRAIT`, `LANDSCAPE` — in CSS il maiuscolo non conta) e
#        i quattro margini in millimetri.
# ⭐ VINCONO LE COLONNE (R-BE-V2a, Tid 2026-10-04): sono cio' che il drawer
#    della versione fa scegliere. Il resto dell'`@page` del template (i
#    margin box: pie' di pagina, numeri) resta suo.
# ⛔ `!important` NON e' un vezzo: WeasyPrint tratta i fogli passati con
#    `stylesheets=` come origine USER, che perde contro qualunque `@page`
#    scritto in uno `<style>` dell'HTML (origine author) — a prescindere
#    dall'ordine. Solo un `!important` di origine user batte l'author.
#    Provato il 2026-10-04: senza, un A3 orizzontale usciva A4 verticale.
# ⛔ Un campo assente e' una proiezione rotta, non un default: le colonne sono
#    NOT NULL, quindi ci si ferma invece di stampare un A4 di ripiego.
def _regola_pagina(versione: dict[str, Any]) -> str:
    mancanti = [c for c in _CAMPI_PAGINA if versione.get(c) is None]
    if mancanti:
        ErrorManager.raise_error(
            code=E_RENDER_FAILED,
            message="Versione template incompleta: mancano i dati della pagina.",
            detail=f"versione_id={versione.get('id')!r} campi={mancanti!r}",
        )
    formato = str(versione["page_format"])
    orientamento = str(versione["page_orientation"])
    for campo, codice in (("page_format", formato), ("page_orientation", orientamento)):
        if not _RE_CODICE_PAGINA.match(codice):
            ErrorManager.raise_error(
                code=E_RENDER_FAILED,
                message="Versione template con un valore di pagina non valido.",
                detail=f"versione_id={versione.get('id')!r} {campo}={codice!r}",
            )
    margini = []
    for campo in _CAMPI_PAGINA[2:]:
        try:
            mm = Decimal(str(versione[campo]))
        except InvalidOperation:
            mm = None
        if mm is None or not mm.is_finite() or mm < 0:
            ErrorManager.raise_error(
                code=E_RENDER_FAILED,
                message="Versione template con un margine di pagina non valido.",
                detail=f"versione_id={versione.get('id')!r} {campo}={versione[campo]!r}",
            )
        margini.append(f"{mm:f}mm")
    return (
        f"@page {{ size: {formato} {orientamento} !important;"
        f" margin: {' '.join(margini)} !important; }}"
    )


# Scopo: Render Jinja del sorgente HTML con `context` come namespace.
#        `StrictUndefined`: variabile mancante nel context -> eccezione
#        parlante (fail-fast), non stringa vuota silenziosa.
# ⛔ `autoescape=True`, e il posto giusto e' QUI, non nei builder. Il context
#    porta dati scritti dagli utenti (ragioni sociali, indirizzi, descrizioni
#    riga, note): senza escape un `<link rel="attachment" href="file://...">`
#    in un campo anagrafica diventava HTML vero, e WeasyPrint lo avrebbe
#    eseguito — un file del server allegato al PDF. Fino al 2026-09-26
#    l'escape era delegato a «ogni builder», e nessuno dei quattro lo faceva:
#    una protezione che dipende da ogni punto di trasporto non c'e'.
# ⚠️ L'escape tocca solo i VALORI interpolati: l'HTML scritto nel template dal
#    configuratore resta com'e'. Un blocco del context che fosse GIA' HTML
#    (oggi nessuno) va marcato `markupsafe.Markup` dal builder, mai con
#    `|safe` nel template.
def _render_html_with_jinja(html_template: str, context: dict[str, Any]) -> str:
    # Import locale: evita di pagare il costo di parsing Jinja a meno che
    # il render non sia effettivamente invocato.
    from jinja2 import Environment, StrictUndefined
    from jinja2 import TemplateError as _JinjaTemplateError
    env = Environment(
        autoescape=True,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    try:
        compiled = env.from_string(html_template)
        return compiled.render(**context)
    except _JinjaTemplateError as exc:
        ErrorManager.raise_error(
            code=E_RENDER_FAILED,
            message="Errore di rendering del template HTML (Jinja).",
            detail=f"{type(exc).__name__}: {exc}",
        )


# Scopo: Conversione HTML+CSS -> PDF tramite WeasyPrint. Lazy import per
#        permettere ai test mock-only di non risolvere la dep nativa.
#        Nessun `base_url` e un fetcher nostro (`_crea_fetcher`): una risorsa
#        si richiama solo con `asset:<codice_interno>` o `data:`.
# ⛔ `FatalURLFetchingError` deriva da `BaseException`, non da `Exception`:
#    senza il suo `except` un rifiuto del fetcher uscirebbe da qui senza
#    codice applicativo.
def _render_with_weasyprint(
    html_source: str,
    css_source: str,
    *,
    css_pagina: str,
    risolvi_asset: RisolviAsset,
) -> bytes:
    # Lazy import: la libreria carica binding Pango/Cairo all'import time;
    # i test che non esercitano davvero WeasyPrint mockano questa funzione.
    try:
        from weasyprint import CSS, HTML
        from weasyprint.urls import (
            FatalURLFetchingError,
            URLFetcher,
            URLFetcherResponse,
        )
    except (ImportError, OSError) as exc:
        logger.warning(
            "documenti.render.weasyprint_unavailable type=%s err=%s",
            type(exc).__name__, exc,
        )
        ErrorManager.raise_error(
            code=E_RENDER_FAILED,
            message="WeasyPrint non disponibile o dipendenze native mancanti.",
            detail=str(exc),
        )
    fetcher = _crea_fetcher(URLFetcher, URLFetcherResponse, risolvi_asset)
    try:
        document = HTML(string=html_source, url_fetcher=fetcher)
        # La regola della pagina per ULTIMA: e' quella delle colonne.
        stylesheets = [
            *([CSS(string=css_source, url_fetcher=fetcher)] if css_source else []),
            CSS(string=css_pagina),
        ]
        pdf_bytes = document.write_pdf(stylesheets=stylesheets)
    except FatalURLFetchingError as exc:
        # Il fetcher ha rifiutato una risorsa e WeasyPrint si e' fermato.
        _solleva_rifiuto(fetcher.primo_rifiuto or exc.__cause__ or exc)
    except Exception as exc:
        # WeasyPrint ha varie eccezioni interne (ParseError, FontError, ecc.):
        # mappiamo tutto su E_DOCUMENTI_RENDER_FAILED con dettaglio diagnostico.
        logger.warning(
            "documenti.render.weasyprint_error type=%s err=%s",
            type(exc).__name__, exc,
        )
        ErrorManager.raise_error(
            code=E_RENDER_FAILED,
            message="Errore di rendering PDF (WeasyPrint).",
            detail=f"{type(exc).__name__}: {exc}",
        )
    # ⛔ Un PDF uscito non prova che nessuna risorsa sia stata rifiutata.
    #    WeasyPrint in qualche punto inghiotte il rifiuto anche con
    #    `fail_on_errors`: `SVGImage.draw` cattura `BaseException` e logga, quindi
    #    un SVG che richiama `file://` darebbe un PDF con l'immagine monca e
    #    nessun errore. Il fetcher tiene il primo rifiuto, e qui si legge.
    if fetcher.primo_rifiuto is not None:
        _solleva_rifiuto(fetcher.primo_rifiuto)
    if not pdf_bytes:
        ErrorManager.raise_error(
            code=E_RENDER_FAILED,
            message="WeasyPrint ha restituito output PDF vuoto.",
        )
    return pdf_bytes


# Scopo: Il rifiuto di una risorsa da parte del fetcher. Il messaggio porta
#        l'URL rifiutata e finisce nel `detail` di E_DOCUMENTI_RENDER_FAILED.
class _RisorsaRifiutata(Exception):
    pass


# Scopo: Traduce il rifiuto di una risorsa nell'errore applicativo. Un
#        `ServiceError` del risolutore (asset che non c'e', storage) esce col
#        suo codice e il suo detail; ogni altro rifiuto diventa
#        E_DOCUMENTI_RENDER_FAILED con l'URL nel detail.
def _solleva_rifiuto(causa: BaseException) -> None:
    if isinstance(causa, ServiceError):
        raise causa
    logger.warning("documenti.render.risorsa_rifiutata err=%s", causa)
    ErrorManager.raise_error(
        code=E_RENDER_FAILED,
        message="Il template richiama una risorsa non ammessa nel render PDF.",
        detail=str(causa),
    )


# Scopo: Costruisce il fetcher di UN render: ha uno stato (il contatore del
#        tetto), quindi non si condivide fra render. Lista chiusa: `asset:`
#        va al risolutore dell'orchestratore, `data:` al gestore standard di
#        WeasyPrint, ogni altro schema e' rifiutato.
#        `fail_on_errors=True` e' il punto che conta: di default WeasyPrint
#        logga il fallimento e va avanti, e il PDF esce senza logo senza che
#        nessuno sappia perche'. Cosi' ogni rifiuto ferma il render.
#        `allowed_protocols={data}` e' il secondo cancello sul solo ramo che
#        passa al fetcher standard. `primo_rifiuto` registra il primo errore,
#        per i punti in cui WeasyPrint lo inghiotte (vedi il chiamante).
#        Le classi di WeasyPrint arrivano dal chiamante, che le ha gia'
#        importate in modo lazy.
def _crea_fetcher(
    url_fetcher_cls: Any,
    response_cls: Any,
    risolvi_asset: RisolviAsset,
) -> Any:

    class _FetcherRender(url_fetcher_cls):
        def __init__(self) -> None:
            super().__init__(
                allowed_protocols={_SCHEMA_DATA}, fail_on_errors=True,
            )
            self._caricate = 0
            self.primo_rifiuto: BaseException | None = None

        def fetch(self, url: str, headers: Any = None) -> Any:
            try:
                return self._fetch_ammesso(url, headers)
            except Exception as exc:
                if self.primo_rifiuto is None:
                    self.primo_rifiuto = exc
                raise

        def _fetch_ammesso(self, url: str, headers: Any) -> Any:
            schema, _, resto = url.partition(":")
            schema = schema.strip().lower()
            if schema == _SCHEMA_ASSET:
                self._caricate += 1
                if self._caricate > _MAX_RISORSE_PER_RENDER:
                    raise _RisorsaRifiutata(
                        f"superato il tetto di {_MAX_RISORSE_PER_RENDER} asset "
                        f"per render (ciclo di @import?): {url!r}"
                    )
                codice_interno = unquote(resto).strip()
                if not codice_interno:
                    raise _RisorsaRifiutata(f"asset senza codice: {url!r}")
                contenuto, mime_type = risolvi_asset(codice_interno)
                return response_cls(
                    url, body=contenuto, headers={"Content-Type": mime_type},
                )
            if schema == _SCHEMA_DATA:
                return super().fetch(url, headers)
            raise _RisorsaRifiutata(
                f"schema non ammesso (ammessi: asset:, data:): {url!r}"
            )

    return _FetcherRender()
