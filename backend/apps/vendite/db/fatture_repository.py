# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso dati della LISTA fatture — la settima lista del ciclo attivo.
#        Sola lettura dalla vista canonica `vendite.vw_fatture_lista`, sullo
#        stampo delle sei sorelle (preventivi, offerte, ordini, contratti, ddt,
#        resi).
#
#        ⭐ Perché esiste. Fino al 2026-08-24 la fattura era l'unico documento
#        del ciclo attivo SENZA la sua lista: si raggiungeva solo passando da un
#        lotto, da un cruscotto o da un collegamento. Il caso che l'ha resa
#        urgente: una commessa di competenza giugno fatturata ad agosto produce
#        un documento con data agosto, e chi lo cerca lo cerca per QUELLA data —
#        non per la competenza della commessa.
#
#        ⛔ La sorgente è la VISTA, mai una query nostra: è la regola di tutte e
#        sei le sorelle, e una seconda verità sullo stesso elenco divergerebbe
#        al primo ritocco.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from apps.config.sorgenti import SORGENTE_FATTURA
from apps.core.api.constants import MAX_LIMIT
from apps.core.db._helpers import (
    colonne_identita,
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    sql_order_clause,
    rows_to_list,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.db.righe_lista_mixin import RigheListaCompletaMixin
from apps.vendite.db._lineage_sintesi import unisci_sintesi_lineage

# Scopo: whitelist ORDER BY della lista fatture. Le chiavi sono i
#        `campo_sorgente` del catalogo `vendite.fatture` — quelli che il FE
#        manda come `sortField` — e i valori le colonne reali della vista.
# ⛔ Whitelist CHIUSA: un nome fuori elenco ripiega sul default invece di
#    entrare nella query.
# ⚠️ `valuta_codice` e `azioni` restano fuori di proposito: il seed li dichiara
#    NON ordinabili, e offrire qui una capacità che il catalogo non espone
#    sarebbe irraggiungibile — il presidio dei seed la segnala.
# Colonne che la ricerca libera SA cercare nella lista `vendite.fatture`. Quali cerca
# davvero lo decide il catalogo a ogni ricerca (`add_ricerca_full_condition`);
# `test_ricerca_full_seed` verifica che coprano le `ricercabile_full` del seed.
# ⚠️ `numero` e' un intero nella vista: il cast a testo lo fa il BB.
_RICERCA_FATTURE = RicercaFull(
    "vendite.fatture",
    (
        "numero", "ragione_sociale_completa", "ba_codice", "id_fiscale_univoco_cf_piva",
    ),
)

_ORDER_COLS_FATTURE: dict[str, str] = {
    "numero": "v.numero",
    "serie": "v.serie",
    "anno": "v.anno",
    "data": "v.data",
    "natura_doc_descrizione": "v.natura_doc_descrizione",
    "tipo_doc_fiscale_descrizione": "v.tipo_doc_fiscale_descrizione",
    "utility_descrizione": "v.utility_descrizione",
    "ragione_sociale_completa": "v.ragione_sociale_completa",
    "id_fiscale_univoco_cf_piva": "v.id_fiscale_univoco_cf_piva",
    "ba_codice": "v.ba_codice",
    "stato_descrizione": "v.stato_descrizione",
    "imponibile_tot": "v.imponibile_tot",
    "imposta_tot": "v.imposta_tot",
    "totale_doc": "v.totale_doc",
    "totale_a_pagare": "v.totale_a_pagare",
    "emittente_ragione_sociale": "v.emittente_ragione_sociale",
    "data_insert": "v.data_insert",
    "user_insert": "v.user_insert",
    # Colonne lineage, come sulle sorelle: pratica e fase ordinabili, la
    # frontiera no (è un chip composto, non un valore).
    "pratica_numero": "v.pratica_numero",
    "fase": "v.fase",
}


# ── Le righe di UNA fattura come lista configurabile `vendite.fattura_righe`
#    (lista 102, brief-db-liste-righe-documento lotto C, 2026-09-28) ──
# ⭐ La sorgente e' `vw_fattura_righe_lista`: il SOLO primo livello della
#    rappresentazione del documento (`vw_fattura_righe_esposte`), con i
#    componenti esposti di un kit DENTRO il padre (`componenti` jsonb). Cosi'
#    paginazione e ordinamento spostano un kit intero, e un ordinamento per
#    importo non stacca i componenti dal loro padre (D-8.3).
# Le colonne `ordinabile = t` del seed (`riga_rettificata` no: e' composta).
# `test_liste_configurabili_seed` e `gen_seed_lista.py` leggono questa costante.
_ORDER_COLS_RIGHE_FATTURA: dict[str, str] = colonne_identita(
    "riga_nr", "articolo_codice", "descrizione", "quantita", "uom_codice",
    "prezzo_unitario", "sconto_percentuale", "importo_riga", "iva_descrizione",
)
# Le `ricercabile_full = t` del seed. `test_ricerca_full_seed` legge questa costante.
_RICERCA_RIGHE_FATTURA = RicercaFull("vendite.fattura_righe", ("descrizione", "articolo_codice"))


class FattureRepository(RigheListaCompletaMixin):
    """Letture della lista fatture dalla vista canonica, e delle righe di una
    fattura (BB `RigheListaCompletaMixin`: pagina e lettura completa, che usa
    il contesto di stampa)."""

    # Righe: la vista di lista, la chiave calcolata e l'ordine del documento.
    # ⚠️ `riga_key` e non `id`: il padre di un kit non esiste in tabella e non
    #    ha un id. ⚠️ Nessun filtro `attivo`: la vista non lo ha — le righe di
    #    una fattura non si disattivano, si rettificano con una nota di credito.
    # ⭐ L'ordine del documento e' `ordinamento, riga_nr`: `ordinamento` tiene
    #    la capofila accanto alle sue parti di plafond, `riga_nr` le mette in fila.
    _righe_vista = "vendite.vw_fattura_righe_lista"
    _righe_fk_documento = "fattura_id"
    _righe_ordine_documento = "ordinamento"
    _righe_ordine_documento_extra = ("riga_nr",)
    _righe_chiave = "riga_key"
    # I componenti esposti di un kit: una LISTA per chi la legge (drawer,
    # note di riga, contesto di stampa), non il testo del jsonb.
    _righe_jsonb = ("componenti",)
    _righe_solo_attive = False
    _righe_ordinamento = _ORDER_COLS_RIGHE_FATTURA
    _righe_ricerca = _RICERCA_RIGHE_FATTURA

    # Scopo: elenco fatture paginato, filtrato e ordinato.
    #
    # ⚠️ `data_da`/`data_al` filtrano la DATA DEL DOCUMENTO, non la competenza
    #    della commessa che l'ha generato — ed è tutto il punto della lista.
    # ⚠️ Lo scope emittente si SOMMA alla RLS, non la sostituisce: la vista è
    #    `security_invoker` e `vendite.fatture` ha la sua policy, quindi il
    #    filtro applicativo è difesa in profondità (api.md §Scope emittente).
    # Risultato: tuple (righe, conteggio totale).
    def list_fatture(
        self,
        *,
        stato_codice: str | None = None,
        billing_account_id: int | None = None,
        id_fiscale: str | None = None,
        utility_id: int | None = None,
        natura_doc_codice: str | None = None,
        data_da: date | None = None,
        data_al: date | None = None,
        search: str | None = None,
        auth_user_id: int | None = None,
        limit: int,
        offset: int,
        order_by: str = "data",
        order_dir: str = "desc",
        max_limit: int = MAX_LIMIT,
    ) -> tuple[list[dict[str, Any]], int]:
        # NULL = valore MINIMO (lo mette `sql_order_clause`): `numero` è NULL su
        # tutte le fatture non ancora numerate, e i default PostgreSQL le
        # manderebbero IN CIMA proprio ordinando dal più recente.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS_FATTURE,
            default=_ORDER_COLS_FATTURE["data"],
            tiebreak="v.id",
            default_desc=True,
        )
        # La pagina si ferma al cap; l'export chiede di più per poter RILEVARE
        # il superamento invece di troncare in silenzio.
        safe_limit, safe_offset = limiti_pagina(limit, offset, tetto=max_limit)

        conditions: list[str] = []
        params: list[Any] = []

        # `stato_codice` arriva dal FE come `codice_interno` (convenzione
        # LookupSelect); nella vista la colonna è `stato_codice_interno`.
        if stato_codice is not None:
            conditions.append("v.stato_codice_interno = %s")
            params.append(stato_codice)
        if billing_account_id is not None:
            conditions.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        # ⭐ Identificativo fiscale, confronto ESATTO — e non e' un doppione della
        #    ricerca libera, che sullo stesso campo fa `ILIKE %...%`. Serve al
        #    collegamento dalla lista SOGGETTI: un soggetto e' una persona
        #    giuridica, non un conto, e i suoi documenti si raccolgono per
        #    codice fiscale / partita IVA.
        # ⚠️ Un `ILIKE` qui sarebbe sbagliato in modo silenzioso: una partita IVA
        #    e' contenuta in altre partite IVA piu' lunghe, e il collegamento
        #    consegnerebbe le fatture di qualcun altro senza dare nessun segno.
        if id_fiscale is not None:
            conditions.append("v.id_fiscale_univoco_cf_piva = %s")
            params.append(id_fiscale)
        if utility_id is not None:
            conditions.append("v.utility_id = %s")
            params.append(utility_id)
        # ⭐ La natura distingue FATTURA da NOTA_CREDITO: su un elenco fiscale è
        # il filtro che separa ciò che incassi da ciò che restituisci.
        if natura_doc_codice is not None:
            conditions.append("v.natura_doc_codice_interno = %s")
            params.append(natura_doc_codice)
        if data_da is not None:
            conditions.append("v.data >= %s")
            params.append(data_da)
        if data_al is not None:
            conditions.append("v.data <= %s")
            params.append(data_al)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_FATTURE)

        add_emittente_scope_condition(
            conditions, params,
            auth_user_id=auth_user_id,
            column="v.emittente_fiscale_id",
            convention="pk",
        )

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_sql = f"SELECT COUNT(*) FROM vendite.vw_fatture_lista v {where}"  # noqa: S608
        # Tiebreak `v.id` per paginazione deterministica. ⚠️ `id` e non
        # `numero`: quest'ultimo è NULL sulle non numerate.
        data_sql = f"""
            SELECT v.*
            FROM vendite.vw_fatture_lista v
            {where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
        """  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            total_count = row[0] if row else 0

            cursor.execute(data_sql, [*params, safe_limit, safe_offset])
            results = rows_to_list(cursor)

        # Le colonne del grafo dalla sintesi, per le chiavi della pagina
        # (brief-db-lineage-seminata-per-chiave B1): la vista non le porta piu'.
        unisci_sintesi_lineage(results, tipo_codice_interno=SORGENTE_FATTURA)
        return results, total_count
