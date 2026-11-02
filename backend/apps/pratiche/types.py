# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
    soggetto_ruolo_id: int | None
    istanza_utility_id: int | None
    stato_id: int
    priorita_id: int
    risorsa_umana_id: int | None
    unita_organizzativa_id: int | None
    pratica_padre_id: int | None
    flusso_origine_id: int | None
    canale_origine_id: int | None
    codice: str | None
    descrizione: str | None
    data_apertura: str | None
    data_scadenza: str | None
    meta: dict[str, Any]
    data_insert: str
    user_insert: str
    # Campi display da JOIN
    tipo_prestazione_codice: str
    tipo_prestazione_descrizione: str
    stato_codice_interno: str
    stato_descrizione: str
    priorita_codice_interno: str
    priorita_descrizione: str
    soggetto_display: str | None
    soggetto_id_fiscale: str | None
    risorsa_umana_display: str | None
    unita_organizzativa_descrizione: str | None


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
    # Campi display da JOIN
    stato_codice_interno: str
    stato_descrizione: str
    template_flusso_codice: str | None
    template_flusso_descrizione: str | None
    # Contesto pratica (header standard drawer esecuzione flussi)
    pratica_codice: str | None
    pratica_data_apertura: str | None
    pratica_soggetto_display: str | None
    pratica_soggetto_id_fiscale: str | None


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
    giorni_rimanenti: int | None
    stato_tempo: str | None


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


# -- Tabella pratiche.competenze_flussi --

class CompetenzaFlussoRow(TypedDict):
    id: int
    template_flusso_id: int
    unita_organizzativa_id: int
    risorsa_umana_id: int
    attivo: bool
    template_flusso_codice: str
    template_flusso_descrizione: str
    unita_organizzativa_descrizione: str
    risorsa_umana_display: str


# -- Return di pratiche.fn_coda_lavoro_operatore() --

class CodaLavoroRow(TypedDict):
    livello: str
    flusso_id: int
    pratica_id: int
    pratica_codice: str | None
    pratica_descrizione: str | None
    priorita_codice: str
    tipo_prestazione_codice: str
    template_flusso_codice: str | None
    template_flusso_desc: str | None
    # stato_flusso_codice = display (mutabile); _interno = logica (immutabile, severity).
    stato_flusso_codice_interno: str
    stato_flusso_codice: str
    sequenza: int
    data_scadenza: str | None
    risorsa_assegnata: str | None
    # Aggiunti dal wrapper repository (non dalla fn): ordinale che preserva
    # l'ordinamento della fn + descrittore stato documento sorgente
    # (proiezione V10, display fields doc_*).
    ordinality: int
    doc_risolto: bool | None
    doc_stato_codice_interno: str | None
    doc_stato_descrizione: str | None
    doc_fase: str | None
    doc_esito: str | None
    doc_terminale: bool | None
    doc_sorgente_descrizione: str | None
