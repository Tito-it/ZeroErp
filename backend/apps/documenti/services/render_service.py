# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
#            per HTML+CSS -> bytes PDF.
#
#        Errori applicativi mappati su `E_DOCUMENTI_RENDER_FAILED`:
#         - engine non in whitelist applicativa
#         - jinja: variabile mancante / sintassi malformata
#         - WeasyPrint: errore interno engine
#         - html_template vuoto o NULL
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from apps.core.services.error_manager import ErrorManager

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


# Scopo: Render del documento PDF a partire dalla versione template e dal
#        contesto applicativo. Funzione pura (no DB, no storage):
#        l'orchestratore di Tranche I fa setup + persistence; questo modulo
#        isola l'engine.
def render_pdf(
    *,
    template_versione: dict[str, Any],
    context: dict[str, Any],
) -> bytes:
    _guard_versione_minima(template_versione)
    engine = (template_versione.get("render_engine_codice_interno") or "").upper()
    if engine not in _ENGINE_WHITELIST:
        ErrorManager.raise_error(
            code=E_RENDER_FAILED,
            message=f"Render engine '{engine}' non supportato in v1.",
            detail=f"engine_ammessi={sorted(_ENGINE_WHITELIST)!r}",
        )
        raise  # unreachable, per type checker

    html_source = _render_html_with_jinja(
        template_versione["html_template"], context,
    )
    css_source = template_versione.get("css_template") or ""
    return _render_with_weasyprint(html_source, css_source)


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
            raise  # unreachable


# Scopo: Render Jinja del sorgente HTML con `context` come namespace.
#        `StrictUndefined`: variabile mancante nel context -> eccezione
#        parlante (fail-fast), non stringa vuota silenziosa. I template
#        documentali sono creati da admin via Configurazione e sono fidati:
#        autoescape disabilitato per non doppio-escape contenuti pre-formattati
#        nel template stesso. Eventuali stringhe utente nel context vanno
#        passate gia' escapate dal builder (responsabilita' del dominio
#        sorgente).
def _render_html_with_jinja(html_template: str, context: dict[str, Any]) -> str:
    # Import locale: evita di pagare il costo di parsing Jinja a meno che
    # il render non sia effettivamente invocato.
    from jinja2 import Environment, StrictUndefined
    from jinja2 import TemplateError as _JinjaTemplateError
    env = Environment(
        autoescape=False,
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
        raise  # unreachable


# Scopo: Conversione HTML+CSS -> PDF tramite WeasyPrint. Lazy import per
#        permettere ai test mock-only di non risolvere la dep nativa.
#        `base_url=None`: il template dovrebbe usare URL assolute per
#        risorse esterne (asset documentali via storage_uri risolvibile).
def _render_with_weasyprint(html_source: str, css_source: str) -> bytes:
    # Lazy import: la libreria carica binding Pango/Cairo all'import time;
    # i test che non esercitano davvero WeasyPrint mockano questa funzione.
    try:
        from weasyprint import CSS, HTML
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
        raise  # unreachable
    try:
        document = HTML(string=html_source)
        stylesheets = [CSS(string=css_source)] if css_source else None
        pdf_bytes = document.write_pdf(stylesheets=stylesheets)
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
        raise  # unreachable
    if not pdf_bytes:
        ErrorManager.raise_error(
            code=E_RENDER_FAILED,
            message="WeasyPrint ha restituito output PDF vuoto.",
        )
        raise  # unreachable
    return pdf_bytes
