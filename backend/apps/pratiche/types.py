# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Tipi condivisi modulo pratiche per ridurre chiavi "magiche"
#        e firme duplicate. Basati sulle colonne effettive dello schema DB.
# ------------------------------------------------------------

from typing import Any, TypedDict


# -- Tabella pratiche.pratiche --

class PraticaRow(TypedDict):
    id: int
    emittente_fiscale_id: int
    tipo_prestazione_id: int
    soggetto_id: str | None
    stato_id: int
    priorita_id: int
    risorsa_umana_id: int | None
    unita_organizzativa_id: int | None
    pratica_padre_id: int | None
    flusso_origine_id: int | None
    canale_origine_id: int | None
    solo_interna: bool
    codice: str | None
    descrizione: str | None
    data_scadenza: str | None
    meta: dict[str, Any]
    data_insert: str
    user_insert: str


# -- Tabella pratiche.flussi --

class FlussoRow(TypedDict):
    id: int
    pratica_id: int
    template_flusso_id: int | None
    stato_id: int
    flusso_padre_id: int | None
    risorsa_umana_id: int | None
    unita_organizzativa_id: int | None
    sequenza: int
    esito: str | None
    note_esito: str | None
    data_scadenza: str | None
    meta: dict[str, Any]
    data_insert: str
    user_insert: str


# -- Tabella pratiche.giornale --

class GiornaleRow(TypedDict):
    id: int
    pratica_id: int
    flusso_id: int | None
    azione: str
    origine: str
    dettaglio: dict[str, Any]
    tx_id: str | None
    data_insert: str
    user_insert: str


# -- Tabella pratiche.template_flussi --

class TemplateFlussoRow(TypedDict):
    id: int
    tipo_prestazione_id: int
    handler_id: int | None
    codice: str
    descrizione: str
    sequenza: int
    obbligatorio: bool
    direzione: str
    attivo: bool
    handler_params: dict[str, Any]
    meta: dict[str, Any]


# -- Return di pratiche.fn_check_prerequisiti_flusso() --

class PrerequisitoCheckRow(TypedDict):
    prerequisito_id: int
    codice: str
    descrizione: str
    soddisfatto: bool


# -- Tabella pratiche.regole_generazione --

class RegolaGenerazioneRow(TypedDict):
    id: int
    template_flusso_origine_id: int
    tipo_prestazione_dest_id: int
    template_flusso_dest_id: int | None
    esito_richiesto: str | None
    auto: bool
    attivo: bool
    descrizione: str | None
    meta: dict[str, Any]


# -- Tabella pratiche.sospensioni --

class SospensioneRow(TypedDict):
    id: int
    pratica_id: int
    flusso_id: int | None
    data_inizio: str
    data_fine: str | None
    data_riattivazione_prevista: str | None
    motivo: str
    data_insert: str
    user_insert: str
    data_update: str | None
    user_update: str | None


# -- Tabella pratiche.formule_tempo --

class FormulaTempoRow(TypedDict):
    id: int
    tipo_prestazione_id: int
    template_flusso_da_id: int
    template_flusso_a_id: int
    giorni_esecuzione: int
    giorni_warning: int
    giorni_critico: int
    attivo: bool
    descrizione: str | None
    meta: dict[str, Any]


# -- Tabella pratiche.calcoli_tempo --

class CalcoloTempoRow(TypedDict):
    id: int
    pratica_id: int
    flusso_da_id: int
    flusso_a_id: int
    formula_tempo_id: int
    data_inizio_calcolo: str
    data_fine_calcolo: str | None
    giorni_lordi: int | None
    giorni_sospensione: int | None
    giorni_netti: int | None
    giorni_formula: int
    sforato: bool | None


# -- Tabella config.transizioni_stati_pratiche / flussi --

class TransizioneStatoRow(TypedDict):
    id: int
    stato_da_id: int
    stato_a_id: int
    attivo: bool


# -- Tabella config.canali_pratiche (usata nei flussi) --

class CanalePraticaRow(TypedDict):
    id: int
    codice: str
    descrizione: str | None
    codice_interno: str
