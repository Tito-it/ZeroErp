# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Sanitizzazione HTML "trusted preview" per anteprime template
#        email e altri contenuti HTML editabili da utenti privilegiati.
#        Whitelist-based via bleach (no <script>, no event handler, no
#        protocolli pericolosi). Defense-in-depth con iframe sandbox FE.
# ------------------------------------------------------------

from __future__ import annotations

import re

import bleach


# Pre-pulizia: rimuove l'intero blocco <script>...</script> e <style>...</style>.
# Bleach con strip=True elimina i tag ma preserva il testo interno, che per
# <script>/<style> e' codice eseguibile/CSS — va eliminato del tutto.
_SCRIPT_BLOCK_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL)
_STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>.*?</style\s*>", re.IGNORECASE | re.DOTALL)


# Whitelist tag ammessi nelle anteprime template email.
# Coerente con i tag consentiti dai principali client di posta
# (Gmail, Outlook, Apple Mail) — niente form, iframe, object, embed.
_ALLOWED_TAGS: frozenset[str] = frozenset({
    "p", "div", "span", "br", "hr",
    "strong", "b", "em", "i", "u", "s", "small",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tfoot", "tr", "td", "th",
    "a", "img", "blockquote", "pre", "code",
})

# Attributi ammessi per tag. Per-tag whitelist — niente attributi globali
# permissivi (nessun on*, niente style globale).
_ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "td": ["colspan", "rowspan", "align"],
    "th": ["colspan", "rowspan", "align", "scope"],
    "table": ["border", "cellpadding", "cellspacing", "width"],
    "*": ["class", "id", "title"],
}

# Protocolli ammessi negli URL (href, src). Esclusi `javascript:`, `data:`
# (eccetto immagini base64 — non necessarie nelle anteprime), `file:`, ecc.
_ALLOWED_PROTOCOLS: frozenset[str] = frozenset({"http", "https", "mailto"})


# Scopo: Sanifica una stringa HTML proveniente da contenuto editabile
#        (template email, note libere) restituendo HTML innocuo per
#        rendering server-side. Usa bleach con whitelist stretta:
#        rimuove <script>, gli event handler `on*`, i protocolli non
#        ammessi (javascript:, data:, ecc.) ed escapa tutto cio` che
#        non e` in whitelist. Pensato per "trusted preview" interna,
#        sempre da abbinare a iframe sandbox lato client.
def sanitize_email_html(html: str | None) -> str:
    if not html:
        return ""
    # Step 1: elimina i blocchi <script>/<style> con il loro contenuto.
    cleaned = _SCRIPT_BLOCK_RE.sub("", html)
    cleaned = _STYLE_BLOCK_RE.sub("", cleaned)
    # Step 2: bleach con whitelist tag/attr/protocol. strip=True rimuove i
    # tag fuori whitelist; il loro contenuto testuale (innocuo dopo lo
    # step 1) puo' restare come testo.
    return bleach.clean(
        cleaned,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )
