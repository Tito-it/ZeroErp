# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: TypedDict per le entita' di `documenti`. Tipizzano le righe
#        ritornate dai repository (lista template, dettaglio template,
#        lista versioni, dettaglio versione, asset). Allineate al DDL
#        Fase A delle tabelle `documenti.template_documenti`,
#        `template_documenti_versioni`, `template_asset`,
#        `documenti_generati`, `documenti_generati_file`,
#        `documenti_generati_eventi`.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date, datetime
from typing import Any, TypedDict


class TemplateDocumentoListRow(TypedDict):
    """Riga lista template — proiezione leggera (no html/css/markdown)."""

    id: int
    codice: str
    codice_interno: str
    descrizione: str
    is_default: bool
    attivo: bool
    tipo_documento_output_id: int
    tipo_documento_output_codice: str
    tipo_documento_output_descrizione: str
    sorgente_tipo_id: int
    sorgente_tipo_codice: str
    sorgente_tipo_descrizione: str
    context_builder_code: str
    file_name_pattern: str | None
    # Modello standard di sistema: senza emittente, ripiego di chi non ha
    # modelli suoi (brief-db-modelli-documento-standard). Le tre colonne
    # dell'emittente sono NULL solo qui (CHECK a DB).
    standard: bool
    emittente_fiscale_id: int | None
    emittente_fiscale_codice: str | None
    # Ragione sociale del SOGGETTO emittente (`soggetti.ragione_sociale_completa`),
    # non `emittenti_fiscali.descrizione` (etichetta interna divergente, in via di
    # eliminazione — brief `brief-emittente-ragione-sociale-dal-soggetto.md`).
    # Rinominata da `emittente_fiscale_descrizione` il 2026-08-03 (piano
    # PrimeVue 5, registro), in pari con viste e seed liste.
    emittente_ragione_sociale: str | None
    data_insert: datetime
    data_update: datetime


class TemplateDocumentoDetailRow(TemplateDocumentoListRow):
    """Dettaglio template — include meta + audit completo."""

    meta: dict[str, Any]
    storicizza: bool
    user_insert: str
    user_update: str
    # Non e' una colonna: la forma dei dati che il builder del template
    # produce oggi (`CONTEXT_VERSION`), None se il builder non e' registrato.
    versione_contesto_builder: int | None


class TemplateVersioneListRow(TypedDict):
    """Riga lista versioni di un template — proiezione leggera (no html/css/markdown)."""

    id: int
    template_documento_id: int
    versione: int
    stato: str
    titolo: str
    formato_template: str
    render_engine_id: int
    render_engine_codice_interno: str
    render_engine_codice: str
    render_engine_descrizione: str
    page_format: str
    page_orientation: str
    valido_dal: date | None
    valido_al: date | None
    # La forma dei dati che la versione legge (NOT NULL, >= 1): stampa e
    # pubblicazione passano solo se e' quella del builder del template.
    versione_contesto: int
    attivo: bool
    data_insert: datetime
    data_update: datetime


class TemplateVersioneDetailRow(TemplateVersioneListRow):
    """
    Dettaglio versione — include payload HTML/CSS/markdown e parametri layout.
    Usato solo dall'endpoint dettaglio singolo (mai in lista).
    """

    html_template: str
    css_template: str | None
    markdown_template: str | None
    margin_top_mm: float
    margin_right_mm: float
    margin_bottom_mm: float
    margin_left_mm: float
    context_schema: dict[str, Any]
    meta: dict[str, Any]
    storicizza: bool
    user_insert: str
    user_update: str


class TemplateAssetListRow(TypedDict):
    """Riga lista asset — proiezione leggera (no binario, no audit completo)."""

    id: int
    codice: str
    codice_interno: str
    descrizione: str
    asset_tipo_id: int
    asset_tipo_codice: str
    asset_tipo_descrizione: str
    mime_type: str
    file_name: str
    file_size_bytes: int
    storage_key: str
    sha256: str
    emittente_fiscale_id: int
    emittente_fiscale_codice: str
    emittente_ragione_sociale: str
    valido_dal: date
    valido_al: date | None
    attivo: bool
    data_insert: datetime
    data_update: datetime


class TemplateAssetDetailRow(TemplateAssetListRow):
    """Dettaglio asset — include meta + audit completo."""

    meta: dict[str, Any]
    storicizza: bool
    user_insert: str
    user_update: str
