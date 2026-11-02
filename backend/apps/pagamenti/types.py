# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: TypedDict delle righe DB del dominio `pagamenti` — distinte contabili,
#        loro righe, ricevuta del posting e saldi.
# Note: I nomi delle chiavi seguono le colonne del database, non il gergo del
#       frontend: la traduzione la fa la view, non il tipo.
# ------------------------------------------------------------

from datetime import date, datetime
from decimal import Decimal
from typing import Any, TypedDict


# ══════════════════════════════════════════════════════════════════
#  La distinta (testata contabile)
# ══════════════════════════════════════════════════════════════════

# ⭐ «Distinta» e non «movimento»: la testata NON ha importo e NON ha nessun
#   riferimento bancario — quello sta sulla riga (`riferimento_ente`). E' il
#   documento che raccoglie N importi arrivati insieme.
class DistintaRow(TypedDict):
    id: int
    codice: str
    centro_riscossione_id: int
    centro_codice: str | None
    centro_descrizione: str | None
    ente_incasso_id: int | None
    ente_codice: str | None
    ente_descrizione: str | None
    data_contabile: date
    data_registrazione: date
    stato_id: int
    stato_codice: str | None
    stato_descrizione: str | None
    stato_is_final: bool | None
    # ⭐ «Registrabile» sta nel catalogo (D20-d): la bandiera che la madre del
    #   posting legge al posto del letterale. Il frontend spegne «Registra» col
    #   motivo quando e' falsa, invece di lasciarlo finire in 409.
    stato_is_registrabile: bool | None
    # ⭐ «Le righe si lavorano ancora?» sta nel catalogo (D-1, brief-db-righe-
    #   distinta-annullata-fuori-dalle-code): false sull'ANNULLATA, che congela
    #   le righe; true sulla CHIUSA, dove sospese e scartate hanno un futuro.
    stato_righe_lavorabili: bool | None
    # La chiave i18n della riga «dove sono» del drawer, dal `meta` dello stato
    # (`nessuna_azione_key`, lo stesso campo degli otto domini con
    # `DrawerActionsBar :info-key`). NULL finche' il seed non c'e'.
    stato_info_key: str | None
    origine: str
    # ── Di chi e' (D3, 2026-09-17) ──────────────────────────────────────────
    # L'emittente e' una colonna della testata (NOT NULL), e il codice
    # `DIS-<SIGLA>-<ANNO>-<7 cifre>` lo porta dentro. Il soggetto-ruolo e' la
    # chiave del DB; PK, sigla e ragione sociale sono i tre nomi che
    # `EmittenteFiscaleField` legge in edit — gli stessi dei documenti di
    # vendite. ⚠️ `registro_id` e `anno` sono NULL sul pregresso `VC_…`.
    emittente_soggetto_ruolo_id: int
    emittente_fiscale_id: int | None
    emittente_fiscale_codice: str | None
    emittente_ragione_sociale: str | None
    registro_id: int | None
    anno: int | None
    importo_dichiarato: Decimal | None
    data_conferma: datetime | None
    user_conferma: str | None
    # ⚠️ Al PLURALE, ed e' una correzione: l'unico su `vendite_contabili_lotti`
    # e' `(lotto_id, contabile_id)`, non il solo `contabile_id` — una distinta
    # puo' appartenere a piu' lotti, e leggerla come un valore solo avrebbe
    # significato duplicare la riga nell'elenco per mostrarne uno.
    lotti_ids: list[int] | None
    meta: Any
    # ── Totali derivati (non colonne: si contano sulle righe attive) ────────
    # `totale_righe` conta TUTTE le righe attive, SCARTATA compresa: quel
    # denaro E' arrivato, e la quadratura chiede «ho letto tutto cio' che
    # c'era», non «tutto e' nostro». E' la stessa somma che il guard di
    # validazione confronta con `importo_dichiarato`.
    righe_totali: int
    righe_registrabili: int
    totale_righe: Decimal
    totale_registrabile: Decimal
    scarto_dichiarato: Decimal | None


# ⭐ La riga per STATO (BE-1): quante righe attive e per che importo in uno
#   stato del catalogo — la fotografia del dialog di validazione, e la sorgente
#   di «di cui non nostre» in quadratura. L'array e' ORDINATO dal catalogo.
class RigaPerStato(TypedDict):
    stato_codice_interno: str
    stato_descrizione: str | None
    righe: int
    # ⚠️ Un `float`, non un `Decimal`: l'array lo costruisce il database con
    #   `jsonb_build_object` e `jsonb_out` lo decodifica con `json.loads`, che
    #   rende i numeri JSON come float (la stessa forma dei `dettaglio` delle
    #   check). Chi somma passa da `Decimal(str(...))`, mai dal float.
    importo: float


# ⭐ Il DETTAGLIO della distinta: la riga di lista piu' cio' che solo il
#   dettaglio porta — il verbo «valida» col suo motivo (D20-a, la terna di
#   §12.5 con prefisso `validazione_blocco`, dalla STESSA check che il guard
#   chiama per rifiutare) e le righe per stato.
# ⚠️ La terna e `can_validare` sono `None` quando lo stato corrente non ammette
#   VALIDATA fra le uscite (lo decide il service dalla matrice): un motivo su un
#   verbo che non si propone e' rumore, non informazione.
class DistintaDettaglioRow(DistintaRow):
    validazione_blocco_reason: str | None
    validazione_blocco_reason_key: str | None
    validazione_blocco_dettaglio: Any
    can_validare: bool | None
    righe_per_stato: list[RigaPerStato]


# ══════════════════════════════════════════════════════════════════
#  La riga contabile
# ══════════════════════════════════════════════════════════════════

# La riga e' l'UNITA' DI ALLOCAZIONE (D1): un incasso che copre tre rate diventa
# tre righe sotto la stessa distinta. ⛔ Non si «spezza» una riga per gestire un
# importo sbagliato (D1-ter, 2026-08-24): quello si registra e poi si sistema.
class RigaContabileRow(TypedDict):
    id: int
    contabile_id: int
    importo: Decimal
    riferimento_ente: str | None
    data_pagamento: date | None
    data_valuta: date | None
    data_operazione: date | None
    fattura_id: int | None
    # `numero` e' un bigint a database, non una stringa: e' il progressivo, e
    # la forma leggibile (serie/anno/numero) la compone chi la mostra.
    fattura_numero: int | None
    fattura_anno: int | None
    fattura_serie: str | None
    # ── Il documento, non il contatore (D19-b) ─────────────────────────────
    # Il numero parlante viene dalla sede unica `fn_numero_documento_fattura`
    # (NULL sulla non numerata); registro e natura dal documento. Servono a chi
    # corregge un importo per sapere su che cosa lo corregge, e alla natura per
    # SEGNALARE una nota di credito, non per nasconderla.
    fattura_numero_documento: str | None
    fattura_data: date | None
    fattura_totale_doc: Decimal | None
    fattura_registro_codice: str | None
    # ⚠️ Senza il prefisso `fattura_` (dal 2026-09-18): e' il nome con cui ogni
    #    proiezione porta la natura, ed e' la gemella che il `formato =
    #    natura_doc` del catalogo liste legge dalla riga.
    natura_doc_codice_interno: str | None
    natura_doc_descrizione: str | None
    billing_account_id: int | None
    billing_account_codice: str | None
    billing_account_descrizione: str | None
    scadenza_id: int | None
    scadenza_numero_rata: int | None
    scadenza_data: date | None
    scadenza_importo: Decimal | None
    forzata: bool
    motivo_forzatura: str | None
    stato_id: int
    stato_codice: str | None
    stato_descrizione: str | None
    stato_is_postabile: bool | None
    stato_richiede_abbinamento: bool | None
    motivo_sospeso: str | None
    fondo_source_id: int | None
    attivo: bool
    meta: Any
    # ── Il verbo «elimina» e il suo motivo (D17, linee-guida-sql §12.5) ──────
    # La terna del PRIMO motivo di `script.fn_check_riga_contabile_eliminabile`
    # (in lista la sua meta' `_su_distinta`, sulla testata) piu' il flag
    # derivato (`reason IS NULL`). NULL/True = si puo' eliminare.
    # ⛔ Il nome dice QUALE verbo: `abbina` e `sospendi` hanno i loro blocchi,
    #    e una colonna generica li confonderebbe (api.md §capability).
    elimina_blocco_reason: str | None
    elimina_blocco_reason_key: str | None
    elimina_blocco_dettaglio: Any
    can_eliminare: bool


# ⭐ La riga vista dalla CODA porta anche la sua distinta: una riga
#   cross-distinta senza il documento da cui viene non si lavora — chi la
#   guarda deve poterci tornare. ⚠️ Ed e' la colonna su cui il contratto
#   dichiara di saper ordinare.
class RigaCodaRow(RigaContabileRow):
    contabile_codice: str
    contabile_data: date
    contabile_origine: str
    # ── I fatti della testata che decidono il verbo (BE-4, D20-b) ───────────
    # Lo stato in cui la distinta si trova, se e' finale, e se e' REGISTRATA
    # (`data_conferma IS NOT NULL`, scritta dal posting). Da una «Sospesa» sotto
    # una distinta registrata si «abbina e registra» (la tardiva); sotto una
    # aperta si abbina e basta. Il frontend sceglie da un fatto, non ricalcola.
    contabile_stato_codice_interno: str | None
    contabile_is_final: bool | None
    # La bandiera del catalogo (D-1): la coda filtra su di lei, e il frontend
    # spegne le azioni leggendola invece di derivarla da finale + registrata.
    contabile_righe_lavorabili: bool | None
    contabile_registrata: bool


# ══════════════════════════════════════════════════════════════════
#  I due cataloghi di stato
# ══════════════════════════════════════════════════════════════════

# ⭐ I flag viaggiano col catalogo e NON si cablano nel frontend: quali stati
#   pretendono fattura e cliente lo dice `richiede_abbinamento`, quali occupano
#   spazio su una rata lo dice `is_postabile`.
# Le colonne che i DUE cataloghi (testata e riga) hanno in comune: la forma di
# ogni tabella di stato del dominio. ⚠️ Scritte una volta: i flag propri di
# ciascuno stanno nei due tipi sotto, non qui.
class _StatoCatalogoBase(TypedDict):
    id: int
    codice: str
    codice_interno: str
    descrizione: str | None
    is_final: bool
    ordine: int | None


# Il catalogo degli stati della DISTINTA.
class StatoCatalogoRow(_StatoCatalogoBase):
    # ⭐ Solo sulla TESTATA (D20-d): `true` sullo stato da cui si registra —
    #   quello in cui si entra validando. Il frontend lo usa per riconoscere
    #   «Porta a VALIDATA» senza confrontare il nome con un letterale.
    is_registrabile: bool


# Il catalogo degli stati della RIGA. ⚠️ Non ha `is_registrabile` (e' una
#   bandiera della testata): eredita la base, non `StatoCatalogoRow`.
class StatoRigaCatalogoRow(_StatoCatalogoBase):
    is_postabile: bool
    richiede_abbinamento: bool


# ══════════════════════════════════════════════════════════════════
#  La ricevuta del posting
# ══════════════════════════════════════════════════════════════════

# ⭐ `esito` e' a vocabolario chiuso: POSTATA | NULLA_DA_POSTARE. Il secondo NON
#   e' un errore — la funzione non solleva — ed e' il frontend a decidere la
#   frase (il database dice il fatto, chi parla con la persona lo racconta).
class RicevutaPosting(TypedDict):
    movimenti_creati: int
    righe_postate: int
    righe_saltate: int
    totale_postato: Decimal
    esito: str


# ⭐ La ricevuta della registrazione TARDIVA di una riga (D20-b): il movimento
#   nato, la riga registrata e il suo importo. `esito` e' sempre `POSTATA`:
#   una tardiva che non si puo' fare e' un RIFIUTO della madre, non un esito
#   (niente `NULLA_DA_POSTARE` qui, ed e' una differenza voluta).
class RicevutaTardiva(TypedDict):
    movimento_id: int
    riga_id: int
    importo: Decimal
    esito: str


# ══════════════════════════════════════════════════════════════════
#  I saldi — la forma UNICA dei tre livelli (documento, rata, cliente)
# ══════════════════════════════════════════════════════════════════

# 🔴 Vincolo del cantiere: i saldi hanno UNA SEDE SOLA. Questa forma vale per
#   tutti i livelli; una schermata sceglie QUALI numeri accendere, mai come si
#   chiamano. `incassato` e' None dove il database non lo sa ancora dire —
#   oggi il livello documento (richiesta DB-10 in corso).
class SaldoRow(TypedDict):
    # A quale livello si sta guardando: DOCUMENTO | RATA | (CLIENTE, quando si
    # accendera'). ⭐ Viaggia nella risposta perche' la stessa forma serve tre
    # domande diverse, e chi la riceve deve sapere a quale sta rispondendo.
    livello: str
    riferimento_id: int
    residuo: Decimal | None
    in_lavorazione: Decimal | None
    incassato: Decimal | None
    has_movimenti: bool
