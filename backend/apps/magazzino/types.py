# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: TypedDict delle righe DB del dominio `magazzino` — il documento
#        interno (inventario / rettifica) e le sue righe, il piano di un
#        inventario, la ricevuta del posting, la disponibilita' e il registro
#        dei movimenti.
# Note: I nomi delle chiavi seguono le colonne del database (e i
#       `campo_sorgente` delle liste a catalogo), non il gergo del frontend.
#       ⚠️ Le due famiglie condividono la forma della testata: `descrizione`
#       e' `None` sulla rettifica, che la colonna non ce l'ha; sulla riga il
#       nome della quantita' e' FISICO (`qta_contata` / `qta_delta`) perche' e'
#       cio' che la lista a catalogo chiede alla riga — due chiavi, non una
#       `qta` che nasconderebbe quale delle due famiglie si sta leggendo.
# ------------------------------------------------------------

from datetime import date, datetime
from decimal import Decimal
from typing import Any, TypedDict


# ══════════════════════════════════════════════════════════════════
#  Il documento interno (testata)
# ══════════════════════════════════════════════════════════════════

class DocumentoInternoRow(TypedDict):
    id: int
    uid: str
    data: date
    # Lo stato GREZZO (`DRAFT` | `CONFIRM` | `POSTED` | `CANCEL`): l'etichetta
    # e' una chiave i18n del frontend (`magazzino.documenti_interni.stato.*`),
    # la severity una mappa in `core/utils/severity.js`. Nessuna tabella di
    # stato a DB (D-L2-h), quindi niente `stato_descrizione`.
    stato: str
    magazzino_id: int
    magazzino_codice: str
    magazzino_descrizione: str
    # Decide se la riga vuole l'ubicazione (D-L2-m): il form la mostra SOLO
    # se vero, e la primitiva la pretende/vieta di conseguenza.
    magazzino_usa_ubicazioni: bool
    descrizione: str | None
    righe_count: int
    sorgente_tipo_id: int | None
    sorgente_riga: int | None
    sorgente_uid: str | None
    meta: dict[str, Any]
    data_insert: datetime
    user_insert: str
    data_update: datetime
    user_update: str | None


# Il riepilogo del piano (solo inventario), `count(*) FILTER` sugli esiti di
# `fn_inventario_piano`: cio' che il pulsante «Piano» mostra come badge e la
# conferma di «Registra» cita («N righe con differenza, M non contate»).
class PianoRiepilogo(TypedDict):
    n_righe: int
    n_con_delta: int
    n_invariate: int
    n_non_contate: int
    n_non_postabili: int


# ══════════════════════════════════════════════════════════════════
#  La riga
# ══════════════════════════════════════════════════════════════════

class RigaDocumentoInternoRow(TypedDict, total=False):
    id: int
    # ⚠️ La FK verso la testata ha il nome FISICO della famiglia
    # (`inventario_id` / `rettifica_id`): arriva con quel nome.
    articolo_id: str
    articolo_codice: str
    articolo_descrizione: str
    articolo_requires_lotto: bool
    articolo_requires_serial: bool
    # Una delle due, per famiglia.
    qta_contata: Decimal
    qta_delta: Decimal
    # Solo inventario: la scrive il posting (`fn_posta_inventario`).
    qta_sistema: Decimal | None
    # Solo rettifica.
    motivo: str | None
    costo_unitario: Decimal | None
    ubicazione_id: int | None
    ubicazione_codice: str | None
    lotto_id: int | None
    lotto_codice: str | None
    asset_id: int | None
    asset_seriale: str | None
    meta: dict[str, Any]
    data_insert: datetime
    user_insert: str
    data_update: datetime


# ══════════════════════════════════════════════════════════════════
#  Il piano di un inventario (`fn_inventario_piano`, decodificato)
# ══════════════════════════════════════════════════════════════════

class PianoRigaRow(TypedDict):
    # La chiave STABILE della riga per la lista (`dataKey` di
    # `<ListaConfigurabile>`): `articolo|ubicazione|lotto|asset`, perche'
    # `riga_id` e' NULL sulle NON_CONTATA e un `id` qui non esiste.
    chiave_riga: str
    # NULL sulle posizioni `NON_CONTATA`: a registro c'e' merce che il
    # conteggio non ha nominato — non e' una riga del documento.
    riga_id: int | None
    articolo_id: str
    articolo_codice: str
    articolo_descrizione: str
    ubicazione_id: int | None
    ubicazione_codice: str | None
    lotto_id: int | None
    lotto_codice: str | None
    asset_id: int | None
    asset_seriale: str | None
    qta_contata: Decimal | None
    qta_sistema: Decimal
    delta: Decimal | None
    causale_codice_interno: str | None
    # INV_INIZIALE | RETT_POS | RETT_NEG | INVARIATA | NON_CONTATA | NON_POSTABILE
    esito: str
    # La coppia della famiglia «riga» (api.md §Capability di riga): il primo
    # motivo di `fn_check_riga_magazzino`, cosi' com'e', su `NON_POSTABILE`.
    posting_blocco_reason: str | None
    posting_blocco_reason_key: str | None


# La ricevuta del posting: un movimento per riga postabile con delta <> 0
# (inventario) o per riga (rettifica). ⚠️ `qta` e' FIRMATA (il verso della
# causale): e' cio' che il registro ha scritto, non la quantita' contata.
class MovimentoPostato(TypedDict):
    movimento_id: int
    riga_id: int
    qta: Decimal


# ══════════════════════════════════════════════════════════════════
#  Consultazione
# ══════════════════════════════════════════════════════════════════

class DisponibilitaRow(TypedDict):
    # `articolo|magazzino`: la chiave di riga per la lista (la vista non ha un id).
    chiave_riga: str
    articolo_id: str
    articolo_codice: str
    articolo_descrizione: str
    articolo_requires_lotto: bool
    articolo_requires_serial: bool
    magazzino_id: int
    magazzino_codice: str
    magazzino_descrizione: str
    giacenza: Decimal
    # NEGATIVA (somma firmata degli attesi APERTA in uscita): la vista la porta
    # in colonna, e `disponibile = giacenza + bloccata` — la somma, mai «meno».
    bloccata: Decimal
    disponibile: Decimal
    n_blocchi: int


class DisponibilitaArticoloRow(TypedDict):
    chiave_riga: str
    articolo_id: str
    articolo_codice: str
    articolo_descrizione: str
    giacenza: Decimal
    bloccata: Decimal
    disponibile: Decimal
    n_magazzini: int


# Un blocco: un atteso `APERTA` in USCITA (`qta < 0`) su (articolo, magazzino)
# — il drill-down di `n_blocchi` (D-L2-j, «gratis»).
class BloccoRow(TypedDict):
    id: int
    qta: Decimal
    data_prevista: datetime | None
    causale_codice: str | None
    causale_descrizione: str | None
    sorgente_codice_interno: str | None
    sorgente_riga: int | None
    sorgente_uid: str | None
    soggetto_ruolo_id: int | None
    soggetto_ragione_sociale: str | None
    nota: str | None
    data_insert: datetime


class MovimentoRow(TypedDict):
    id: int
    data_mov: datetime
    articolo_id: str
    articolo_codice: str
    articolo_descrizione: str
    magazzino_id: int
    magazzino_codice: str
    magazzino_descrizione: str
    qta: Decimal
    costo_unitario: Decimal | None
    causale_id: int
    causale_codice: str
    causale_descrizione: str
    causale_segno: int
    ubicazione_id: int | None
    ubicazione_codice: str | None
    lotto_id: int | None
    lotto_codice: str | None
    asset_id: int | None
    asset_seriale: str | None
    sorgente_tipo_id: int
    sorgente_codice_interno: str | None
    sorgente_riga: int | None
    sorgente_uid: str | None
    transfer_uid: str | None
    storno_di_movimento_id: int | None
    data_insert: datetime
    user_insert: str


# ══════════════════════════════════════════════════════════════════
#  Le anagrafiche (piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config)
# ══════════════════════════════════════════════════════════════════

class MagazzinoRow(TypedDict):
    id: int
    uid: str
    codice: str
    descrizione: str
    emittente_fiscale_id: int
    # Display field via LEFT JOIN: `None` se la RLS non lascia leggere la
    # decodifica — la riga resta, la colonna e' vuota.
    emittente_codice: str | None
    emittente_ragione_sociale: str | None
    emittente_soggetto_id: str | None
    indirizzo_dettaglio_id: int
    indirizzo_normalizzato: str | None
    usa_ubicazioni: bool
    predefinito: bool
    attivo: bool
    # Le ubicazioni ATTIVE del magazzino (badge «Ubicazioni (N)» del drawer).
    ubicazioni_count: int
    meta: dict[str, Any]
    data_insert: datetime
    user_insert: str
    data_update: datetime
    user_update: str | None


class UbicazioneRow(TypedDict):
    id: int
    magazzino_id: int
    codice: str
    descrizione: str | None
    tipo_id: int
    tipo_codice: str | None
    tipo_descrizione: str | None
    parent_id: int | None
    parent_codice: str | None
    area: str | None
    corsia: str | None
    scaffale: str | None
    piano: str | None
    posizione: str | None
    attivo: bool
    meta: dict[str, Any]
    data_insert: datetime
    user_insert: str
    data_update: datetime
    user_update: str | None


class LottoRow(TypedDict):
    id: int
    articolo_id: str
    codice: str
    data_arrivo: date
    data_scadenza: date | None
    attivo: bool
    meta: dict[str, Any]
    data_insert: datetime
    user_insert: str
    data_update: datetime
    user_update: str | None
