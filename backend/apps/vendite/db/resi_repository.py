# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per resi di vendita (CRUD testata/righe, conferma/annullo,
#        generazione DDT di ri-consegna, code da-accreditare/da-riconsegnare).
# ------------------------------------------------------------

# Repository resi di vendita: letture sulla vista canonica
# `vendite.vw_resi_lista` (lista) e `vendite.resi` (dettaglio), scritture
# dirette su tabelle, chiamate alle funzioni madri DB (`fn_conferma_reso`,
# `fn_annulla_reso`, `fn_genera_ddt_riconsegna`, `fn_accredita_riga_reso`). Clone strutturale ridotto di
# `ddt_repository` (niente componenti BoM / prezzi / push / PDF): il reso non
# inventa articoli — le righe sono snapshot delle righe del DDT sorgente
# (copiate qui, nessun trigger di copia a DB). La numerazione a CONFERMATO e
# la derivazione `quantita` da `qta_operativa` sono trigger DB; l'over-return
# e l'over-ri-spedizione sono guard DB con lock.

import json
from datetime import date
from typing import Any

from django.db import connection

from apps.core.db._helpers import (
    call_jsonb_fn,
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
    sql_order_direction,
    sql_tiebreak_direction,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.vendite.db._coda_documento_filtro import filtro_coda_per_documento
from apps.core.db.sql_write_helpers import execute_dynamic_update

# Scopo: Whitelist colonne ORDER BY per la lista resi (SQL injection safe). Le
#        chiavi sono i `campo_sorgente` del catalogo liste ('vendite.resi') che
#        il FE invia come sortField; i valori sono le colonne reali di
#        `vendite.vw_resi_lista` (alias `v`).
_ORDER_COLS_RESI: dict[str, str] = {
    "numero": "v.numero",
    "data": "v.data",
    "anno": "v.anno",
    "destinatario_denominazione": "v.destinatario_denominazione",
    "ba_codice": "v.ba_codice",
    "id_fiscale_univoco_cf_piva": "v.id_fiscale_univoco_cf_piva",
    "stato_descrizione": "v.stato_descrizione",
    # `stato_codice_interno` uscita il 2026-07-31: colonna tecnica (severity del
    # Tag di stato), nel seed invisibile e `ordinabile=f`.
    "ddt_origine_numero": "v.ddt_origine_numero",
    "data_insert": "v.data_insert",
}

# Scopo: Config ORDER BY + search per le due code (viste dedicate), indicizzata
#        per nome vista. `order_cols`: whitelist SQL-safe sortField -> colonna
#        reale (le chiavi sono i `campo_sorgente` `ordinabile=t` del catalogo
#        liste `vendite.resi_da_accreditare` / `..._riconsegnare`, id 10/11).
#        `search_cols`: colonne `ricercabile_full=t` per la search ILIKE. Le due
#        code hanno colonne diverse (accreditare espone il conto del contatore
#        accredito_dovuto/tenuti/fatturati + etichetta DOVUTA|FACOLTATIVA;
#        riconsegnare la copertura resa/riconsegnata/residua + stato_riconsegna),
#        quindi due mappe distinte, non una condivisa.
_CODA_META: dict[str, dict[str, Any]] = {
    "vendite.vw_resi_da_accreditare": {
        "order_cols": {
            "reso_numero": "v.reso_numero",
            "data": "v.data",
            "destinatario_denominazione": "v.destinatario_denominazione",
            "descrizione": "v.descrizione",
            "ddt_numero": "v.ddt_numero",
            "qta_operativa": "v.qta_operativa",
            "motivo": "v.motivo",
            "ba_codice": "v.ba_codice",
            "quantita": "v.quantita",
            "accredito_dovuto": "v.accredito_dovuto",
            "etichetta": "v.etichetta",
            "tenuti": "v.tenuti",
            "fatturati": "v.fatturati",
        },
        "search_cols": [
            "v.reso_numero", "v.destinatario_denominazione",
            "v.descrizione", "v.ddt_numero", "v.ba_codice",
        ],
    },
    "vendite.vw_resi_da_riconsegnare": {
        "order_cols": {
            "reso_numero": "v.reso_numero",
            "data": "v.data",
            "destinatario_denominazione": "v.destinatario_denominazione",
            "descrizione": "v.descrizione",
            "ddt_numero": "v.ddt_numero",
            "qta_resa": "v.qta_resa",
            "qta_riconsegnata": "v.qta_riconsegnata",
            # Quota dichiarata definitiva (ponte resi_righe_rinunce): la coda
            # espone entrambe le uscite della copertura, non solo la consegnata.
            "qta_rinunciata": "v.qta_rinunciata",
            "qta_residua": "v.qta_residua",
            "stato_riconsegna": "v.stato_riconsegna",
        },
        "search_cols": [
            "v.reso_numero", "v.destinatario_denominazione",
            "v.descrizione", "v.ddt_numero",
        ],
    },
}


class ResiRepository:
    """Repository resi di vendita (motore resi su DDT)."""

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Testata (via vista canonica vw_resi_lista)
    # ══════════════════════════════════════════════════════════

    # Scopo: Elenco resi paginato dalla vista canonica `vendite.vw_resi_lista`.
    #        Espone i nomi canonici (destinatario_denominazione, ba_codice,
    #        id_fiscale_univoco_cf_piva), `stato_codice_interno` per la severity
    #        del Tag FE, il DDT di origine e `emittente_fiscale_id` per lo scope
    #        operatore (RLS `rls_resi_ef_whitelist` + filtro applicativo).
    # Risultato: tuple (lista righe, conteggio totale).
    def list_resi(
        self,
        *,
        stato_codice: str | None = None,
        billing_account_id: int | None = None,
        data_da: date | None = None,
        data_al: date | None = None,
        search: str | None = None,
        auth_user_id: int | None = None,
        limit: int,
        offset: int,
        order_by: str = "data",
        order_dir: str = "desc",
        max_limit: int = 200,
    ) -> tuple[list[dict[str, Any]], int]:
        order_column = _ORDER_COLS_RESI.get(order_by, _ORDER_COLS_RESI["data"])
        direction = sql_order_direction(order_dir)
        tiebreak_dir = sql_tiebreak_direction(direction)
        # `max_limit`: lista cap 200 (gia' via parse_list_params), export fino a
        # EXPORT_MAX_ROWS+1 per non troncare in silenzio (guard su COUNT reale).
        safe_limit = max(1, min(int(limit), max_limit))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []

        # `stato_codice` arriva dal FE come `codice_interno` (LookupSelect
        # value-field): nella vista la colonna e' `stato_codice_interno`.
        if stato_codice is not None:
            conditions.append("v.stato_codice_interno = %s")
            params.append(stato_codice)
        if billing_account_id is not None:
            conditions.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        if data_da is not None:
            conditions.append("v.data >= %s")
            params.append(data_da)
        if data_al is not None:
            conditions.append("v.data <= %s")
            params.append(data_al)
        if search and len(search) >= 3:
            # Ricerca estesa: numero reso + destinatario + codice BA +
            # id fiscale + numero DDT di origine.
            conditions.append(
                "(v.numero ILIKE %s OR v.destinatario_denominazione ILIKE %s "
                "OR v.ba_codice ILIKE %s OR v.id_fiscale_univoco_cf_piva ILIKE %s "
                "OR v.ddt_origine_numero ILIKE %s)"
            )
            like = f"%{search}%"
            params.extend([like, like, like, like, like])

        # Scope emittente (defense-in-depth applicativa, mirror ddt/ordini).
        # La vista e' `security_invoker=on` e `vendite.resi` ha la policy RLS
        # `rls_resi_ef_whitelist`: la RLS filtra gia'; questo filtro si somma.
        add_emittente_scope_condition(
            conditions, params,
            auth_user_id=auth_user_id,
            column="v.emittente_fiscale_id",
            convention="pk",
        )

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_sql = f"SELECT COUNT(*) FROM vendite.vw_resi_lista v {where}"  # noqa: S608
        # Tiebreaker v.id per paginazione deterministica.
        data_sql = f"""
            SELECT v.* FROM vendite.vw_resi_lista v
            {where}
            ORDER BY {order_column} {direction}, v.id {tiebreak_dir}
            LIMIT %s OFFSET %s
        """  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            total_count = row[0] if row else 0

            cursor.execute(data_sql, [*params, safe_limit, safe_offset])
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Dettaglio singolo reso. Riusa la vista canonica (decodifiche +
    #        provenienza DDT) e aggiunge i campi non esposti in lista (`meta`,
    #        `storicizza`). None se id inesistente (o fuori scope RLS -> 404).
    def get_reso(self, reso_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                v.*,
                r.meta,
                r.storicizza
              FROM vendite.vw_resi_lista v
              JOIN vendite.resi r ON r.id = v.id
             WHERE v.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [reso_id])
            return row_to_dict(cursor)

    # Scopo: Capability data-driven del reso per il detail API. Wrapper su
    #        `script.fn_available_actions_reso` (matrice
    #        `config.transizioni_stati_reso`): available_actions,
    #        can_change_state, can_edit_testata/righe (solo DRAFT),
    #        non_editable_fields, stato_codice. Mirror ridotto del DDT (niente
    #        push_commessa, niente pdf). Blob opaco lato Python (passato al FE).
    #        {} se la fn ritorna NULL (reso inesistente — caller verifica a monte).
    def get_capabilities(self, reso_id: int) -> dict[str, Any]:
        return call_jsonb_fn("script.fn_available_actions_reso", reso_id)

    # Scopo: Lettura LEGGERA per i guard delle righe: stato corrente + id del
    #        DDT di origine (via uid sorgente), senza materializzare la vista
    #        lista con le decodifiche. None se il reso non esiste.
    def get_stato_e_ddt_origine(self, reso_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT sdr.codice_interno AS stato_codice_interno,
                   d.id               AS ddt_origine_id
              FROM vendite.resi r
              JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
              LEFT JOIN vendite.ddt d ON d.uid = r.sorgente_uid
             WHERE r.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [reso_id])
            return row_to_dict(cursor)

    # Scopo: Stato corrente (codice_interno) del reso. Guard pre-operazione del
    #        service (es. righe modificabili solo in DRAFT).
    def get_stato_codice(self, reso_id: int) -> str | None:
        sql = """
            SELECT sdr.codice_interno
              FROM vendite.resi r
              JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
             WHERE r.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [reso_id])
            row = cursor.fetchone()
            return row[0] if row else None

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Righe
    # ══════════════════════════════════════════════════════════

    # Scopo: Conteggio righe attive del reso (per `righe_count` del detail).
    def count_righe(self, reso_id: int) -> int:
        sql = (
            "SELECT COUNT(*) FROM vendite.resi_righe "
            "WHERE reso_id = %s AND attivo IS TRUE"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [reso_id])
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    # Scopo: Righe attive del reso con decodifiche articolo/uom/tipo reso e la
    #        copertura ri-consegna: qta_riconsegnata (ponte
    #        `resi_righe_riconsegne`), qta_rinunciata (ponte
    #        `resi_righe_rinunce`), qta_residua e stato_riconsegna DERIVATI
    #        (R1: nessuna colonna fisica).
    #        ⚠️ Il residuo NON si ricalcola qui: arriva da
    #        `vendite.fn_resi_riga_residuo_riconsegna` — l'helper unico estratto
    #        dal team DB (brief chiusura-riconsegna §4.2-bis) proprio perche' la
    #        formula `quantita − Σric` era gia' triplicata a DB. Questa era la
    #        QUARTA copia, ed era diventata SBAGLIATA con l'arrivo delle rinunce
    #        (non le sottraeva): mostrava come ri-spedibile una quota gia'
    #        dichiarata definitiva. Le due uscite condividono la copertura, il
    #        residuo e' `quantita − Σric − Σrin` e lo dice una funzione sola.
    def list_righe(self, reso_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                rr.id,
                rr.reso_id,
                rr.riga_nr,
                rr.attivo,
                rr.ddt_riga_id,
                rr.ordine_riga_id,
                rr.articolo_id,
                a.codice                AS articolo_codice,
                a.descrizione           AS articolo_descrizione,
                rr.descrizione,
                rr.quantita,
                rr.qta_operativa,
                rr.factor_to_base,
                rr.uom_operativa_id,
                um.codice               AS uom_codice,
                rr.tipo_reso_id,
                tr.codice_interno       AS tipo_reso_codice_interno,
                tr.descrizione          AS tipo_reso_descrizione,
                tr.riapre_residuo,
                rr.motivo,
                COALESCE(ric.tot, 0::numeric) AS qta_riconsegnata,
                COALESCE(rin.tot, 0::numeric) AS qta_rinunciata,
                res.residuo AS qta_residua,
                -- Stati allineati 1:1 a vw_resi_da_riconsegnare (stessa
                -- semantica nel drawer e nella coda): RINUNCIATA quando la
                -- copertura si e' chiusa per rinuncia e non per consegna.
                CASE
                    WHEN tr.riapre_residuo IS NOT TRUE THEN NULL
                    WHEN res.residuo = 0::numeric
                         AND COALESCE(rin.tot, 0::numeric) > 0::numeric
                        THEN 'RINUNCIATA'
                    WHEN COALESCE(ric.tot, 0::numeric) = 0::numeric
                         AND COALESCE(rin.tot, 0::numeric) = 0::numeric
                        THEN 'DA_RICONSEGNARE'
                    WHEN res.residuo > 0::numeric
                        THEN 'PARZIALE'
                    ELSE 'COMPLETATA'
                END AS stato_riconsegna,
                rr.meta,
                rr.data_insert,
                rr.data_update
              FROM vendite.resi_righe rr
              LEFT JOIN catalogo.articoli a      ON a.id  = rr.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id = rr.uom_operativa_id
              LEFT JOIN config.tipi_reso tr      ON tr.id = rr.tipo_reso_id
              LEFT JOIN (
                    SELECT resi_riga_id, SUM(qta) AS tot
                      FROM vendite.resi_righe_riconsegne
                     GROUP BY resi_riga_id
              ) ric ON ric.resi_riga_id = rr.id
              LEFT JOIN (
                    SELECT resi_riga_id, SUM(qta) AS tot
                      FROM vendite.resi_righe_rinunce
                     GROUP BY resi_riga_id
              ) rin ON rin.resi_riga_id = rr.id
              -- Helper valutato UNA volta per riga e riusato da qta_residua e
              -- dai tre rami della CASE: senza il LATERAL sarebbero 3 chiamate
              -- per riga (STABLE non garantisce il riuso fra occorrenze).
              CROSS JOIN LATERAL (
                    SELECT vendite.fn_resi_riga_residuo_riconsegna(rr.id) AS residuo
              ) res
             WHERE rr.reso_id = %s
               AND rr.attivo IS TRUE
             ORDER BY rr.riga_nr, rr.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [reso_id])
            return rows_to_list(cursor)

    # Scopo: Carica una singola riga reso per id (proiezione lean per i guard
    #        del service: appartenenza al reso + snapshot corrente).
    def get_riga(self, riga_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                rr.id,
                rr.reso_id,
                rr.riga_nr,
                rr.attivo,
                rr.ddt_riga_id,
                rr.ordine_riga_id,
                rr.articolo_id,
                rr.descrizione,
                rr.quantita,
                rr.qta_operativa,
                rr.factor_to_base,
                rr.uom_operativa_id,
                rr.tipo_reso_id,
                rr.motivo,
                rr.meta
              FROM vendite.resi_righe rr
             WHERE rr.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [riga_id])
            return row_to_dict(cursor)

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Righe DDT per il pannello "crea reso" (dominio sorgente)
    # ══════════════════════════════════════════════════════════

    # Scopo: Righe attive del DDT sorgente con il gia'-reso cumulato (resi non
    #        ANNULLATI, stessa formula del guard DB `a20`) e il residuo ancora
    #        rendibile, in unita' base E operativa. Alimenta la UX del pannello
    #        FE "crea reso da DDT": il guard resta a DB (fail-fast 532), qui
    #        solo lettura — nessuna duplicazione di enforcement.
    def list_righe_ddt_per_reso(self, ddt_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                dr.id                   AS ddt_riga_id,
                dr.riga_nr,
                dr.articolo_id,
                a.codice                AS articolo_codice,
                a.descrizione           AS articolo_descrizione,
                dr.descrizione,
                dr.quantita             AS qta_consegnata,
                dr.qta_operativa,
                dr.factor_to_base,
                dr.uom_operativa_id,
                um.codice               AS uom_codice,
                COALESCE(res.tot, 0::numeric)                AS qta_gia_resa,
                (dr.quantita - COALESCE(res.tot, 0::numeric)) AS qta_resa_residua,
                CASE
                    WHEN COALESCE(dr.factor_to_base, 1::numeric) = 0::numeric
                        THEN NULL
                    ELSE (dr.quantita - COALESCE(res.tot, 0::numeric))
                         / COALESCE(dr.factor_to_base, 1::numeric)
                END AS qta_resa_residua_operativa
              FROM vendite.ddt_righe dr
              LEFT JOIN catalogo.articoli a      ON a.id  = dr.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id = dr.uom_operativa_id
              LEFT JOIN (
                    SELECT rr.ddt_riga_id, SUM(rr.quantita) AS tot
                      FROM vendite.resi_righe rr
                      JOIN vendite.resi r          ON r.id = rr.reso_id
                      JOIN config.stati_doc_reso s ON s.id = r.stato_doc_reso_id
                     WHERE s.codice_interno <> 'ANNULLATO'
                       AND rr.attivo IS TRUE
                     GROUP BY rr.ddt_riga_id
              ) res ON res.ddt_riga_id = dr.id
             WHERE dr.ddt_id = %s
               AND dr.attivo IS TRUE
             ORDER BY dr.riga_nr, dr.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ddt_id])
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Code di lavoro (viste dedicate)
    # ══════════════════════════════════════════════════════════

    # Scopo: Coda "da accreditare" dalla vista `vw_resi_da_accreditare`
    #        (forma contatore, brief DDT-resi §3c): righe reso CONFERMATE la
    #        cui partita ha differenza negativa (`accredito_dovuto =
    #        fatturati - tenuti > 0`), QUALUNQUE tipo di reso — il tipo e'
    #        degradato a `etichetta` DOVUTA (a credito) | FACOLTATIVA (per
    #        ri-consegna, scelta DL-26). Espone il conto (tenuti/fatturati/
    #        accredito_dovuto).
    #        ⚠️ Dal 2026-08-17 (partita merce generalizzata, S4) la chiave della
    #        vista e' `ddt_riga_id`, NOT NULL: i join a `ddt_righe`/`ddt` sono
    #        INNER, quindi `ddt_id`/`ddt_numero` ci sono SEMPRE. A poter mancare
    #        e' `ordine_riga_id`, che resta esposto ma non e' piu' la chiave —
    #        e' NULL sulla merce senza origine ordine (riga di DDT aggiunta a
    #        mano, DDT standalone), che prima usciva dal conto senza errore e
    #        ora entra. Nessun consumatore lo usi come chiave.
    #        Filtri + scope emittente + paginazione. Slice NC ci si appoggia.
    def list_da_accreditare(
        self,
        *,
        billing_account_id: int | None = None,
        data_da: date | None = None,
        data_al: date | None = None,
        search: str | None = None,
        etichetta: str | None = None,
        ddt_id: int | None = None,
        ordine_id: int | None = None,
        auth_user_id: int | None = None,
        limit: int,
        offset: int,
        order_by: str = "data",
        order_dir: str = "desc",
        max_limit: int = 200,
    ) -> tuple[list[dict[str, Any]], int]:
        # La condizione etichetta vive QUI, non nel builder condiviso: la
        # colonna esiste solo su questa vista, e il builder deve restare
        # neutro rispetto alle due code (niente parametri validi per meta'
        # dei chiamanti). Il service whitelist-a DOVUTA|FACOLTATIVA a monte.
        extra_conditions: list[str] = []
        extra_params: list[Any] = []
        if etichetta is not None:
            extra_conditions.append("v.etichetta = %s")
            extra_params.append(etichetta)
        return self._list_coda(
            "vendite.vw_resi_da_accreditare",
            billing_account_id=billing_account_id,
            data_da=data_da,
            data_al=data_al,
            search=search,
            ddt_id=ddt_id,
            ordine_id=ordine_id,
            auth_user_id=auth_user_id,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
            max_limit=max_limit,
            extra_conditions=extra_conditions,
            extra_params=extra_params,
        )

    # Scopo: Coda "da ri-consegnare" (righe reso CONFERMATE per ri-consegna con
    #        copertura incompleta) dalla vista `vw_resi_da_riconsegnare`: espone
    #        qta_resa/qta_riconsegnata/qta_residua e `stato_riconsegna` derivato.
    #        Si auto-svuota quando la copertura raggiunge la quantita' resa.
    def list_da_riconsegnare(
        self,
        *,
        billing_account_id: int | None = None,
        data_da: date | None = None,
        data_al: date | None = None,
        search: str | None = None,
        ddt_id: int | None = None,
        ordine_id: int | None = None,
        auth_user_id: int | None = None,
        limit: int,
        offset: int,
        order_by: str = "data",
        order_dir: str = "desc",
        max_limit: int = 200,
    ) -> tuple[list[dict[str, Any]], int]:
        return self._list_coda(
            "vendite.vw_resi_da_riconsegnare",
            billing_account_id=billing_account_id,
            data_da=data_da,
            data_al=data_al,
            search=search,
            ddt_id=ddt_id,
            ordine_id=ordine_id,
            auth_user_id=auth_user_id,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
            max_limit=max_limit,
        )

    # Scopo: Lettura condivisa delle due code (stesse colonne di filtro:
    #        billing_account_id, data, emittente_fiscale_id). Il nome vista
    #        arriva SOLO dai due wrapper (statico, no input utente).
    def _list_coda(
        self,
        vista: str,
        *,
        billing_account_id: int | None,
        data_da: date | None,
        data_al: date | None,
        search: str | None = None,
        ddt_id: int | None = None,
        ordine_id: int | None = None,
        extra_conditions: list[str] | None = None,
        extra_params: list[Any] | None = None,
        auth_user_id: int | None,
        limit: int,
        offset: int,
        order_by: str = "data",
        order_dir: str = "desc",
        max_limit: int = 200,
    ) -> tuple[list[dict[str, Any]], int]:
        # `max_limit` distingue le due chiamate: la lista pagina (cap 200,
        # il paginator manda al piu' 100), l'export chiede fino a
        # EXPORT_MAX_ROWS+1 per intercettare l'overflow SENZA troncare in
        # silenzio (il guard di build_export_response usa la COUNT reale).
        meta = _CODA_META[vista]
        order_column = meta["order_cols"].get(order_by) or "v.data"
        direction = sql_order_direction(order_dir, default_desc=True)
        # ⚠️ Qui il tiebreak NON si allinea alla direzione (regola 2026-08-03,
        # che vale per gli spareggi TECNICI): `v.reso_id DESC` raggruppa le
        # righe di uno stesso reso e `v.resi_riga_id ASC` le tiene nel loro
        # ordine naturale DENTRO il reso. Ribaltarle farebbe leggere le righe
        # di un reso al contrario ordinando la lista per un'altra colonna.
        safe_limit = max(1, min(int(limit), max_limit))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []
        if billing_account_id is not None:
            conditions.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        if data_da is not None:
            conditions.append("v.data >= %s")
            params.append(data_da)
        if data_al is not None:
            conditions.append("v.data <= %s")
            params.append(data_al)
        # Restrizione al documento: filtro COMUNE alle due code, quindi vive qui
        # accanto a billing_account_id e alle date — non negli `extra_conditions`
        # dei wrapper, che sono per le colonne di UNA vista sola (l'etichetta).
        # ⭐ Il predicato e' il BB condiviso col pannello situazione merce: le due
        # schermate rispondono alla stessa domanda e devono contare le stesse
        # righe.
        condizione_doc, params_doc = filtro_coda_per_documento(
            ddt_id=ddt_id, ordine_id=ordine_id
        )
        if condizione_doc is not None:
            conditions.append(condizione_doc)
            params.extend(params_doc)
        if extra_conditions:
            # Condizioni vista-specifiche costruite dal wrapper chiamante
            # (es. etichetta della coda accrediti): il builder resta neutro
            # rispetto alle colonne delle singole viste.
            conditions.extend(extra_conditions)
            params.extend(extra_params or [])
        if search and len(search) >= 3:
            # Ricerca estesa sulle colonne `ricercabile_full=t` della coda
            # (numero reso + destinatario + articolo + DDT [+ ba_codice]).
            cols = meta["search_cols"]
            conditions.append("(" + " OR ".join(f"{c} ILIKE %s" for c in cols) + ")")
            like = f"%{search}%"
            params.extend([like] * len(cols))
        add_emittente_scope_condition(
            conditions, params,
            auth_user_id=auth_user_id,
            column="v.emittente_fiscale_id",
            convention="pk",
        )
        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        # UNA valutazione della vista per pagina (BB core
        # `fetch_paged_with_total`): con la forma contatore le viste-coda
        # sono diventate costose (aggregati tenuti/fatturati per partita) e
        # la doppia query COUNT+SELECT ne pagava il prezzo due volte a ogni
        # paginazione. Il fallback COUNT scatta SOLO su pagina-oltre-l'ultima
        # (caso reale: le code si auto-svuotano a copertura/accredito
        # raggiunti). Tie-breaker stabile (reso_id, resi_riga_id) appeso
        # all'order utente per paginazione deterministica anche su colonne
        # non univoche.
        data_sql = f"""
            SELECT v.*, COUNT(*) OVER () AS total_count
            FROM {vista} v
            {where}
            ORDER BY {order_column} {direction}, v.reso_id DESC, v.resi_riga_id ASC
            LIMIT %s OFFSET %s
        """  # noqa: S608
        return fetch_paged_with_total(
            data_sql,
            [*params, safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) FROM {vista} v {where}",  # noqa: S608
            fallback_params=params,
            offset=safe_offset,
        )

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Testata
    # ══════════════════════════════════════════════════════════

    # Scopo: Inserisce un nuovo reso (sorgente DDT) e restituisce id, uid,
    #        numero. `numero` NON si passa: e' NULL in DRAFT e valorizzato dal
    #        trigger `trgfn_resi_gen_numero` alla transizione a CONFERMATO.
    #        BA/destinatario/utility/valuta/emittente NON si passano: li eredita
    #        `trgfn_resi_normalize` dal DDT sorgente (BEFORE INSERT, quindi i
    #        NOT NULL di tabella sono soddisfatti dal trigger).
    def create_reso(
        self,
        *,
        sorgente_tipo_id: int,
        sorgente_uid: str,
        stato_doc_reso_id: int,
        data: date | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cols: list[str] = ["sorgente_tipo_id", "sorgente_uid", "stato_doc_reso_id"]
        vals: list[Any] = [sorgente_tipo_id, sorgente_uid, stato_doc_reso_id]
        if data is not None:
            cols.append("data")
            vals.append(data)
        cols.append("meta")
        placeholders = ["%s"] * (len(cols) - 1) + ["%s::jsonb"]
        vals.append(json.dumps(meta or {}))
        sql = (  # noqa: S608 — colonne whitelisted (chiavi statiche)
            f"INSERT INTO vendite.resi ({', '.join(cols)}) "
            f"VALUES ({', '.join(placeholders)}) "
            f"RETURNING id, uid::text AS uid, numero"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna campi modificabili della testata reso (data/meta: il
    #        resto e' ereditato dal DDT sorgente e immutabile — vedi
    #        non_editable_fields della fn capabilities). Meta ::jsonb via BB.
    def update_reso(self, reso_id: int, **kwargs: Any) -> bool:
        return execute_dynamic_update("vendite.resi", reso_id, kwargs)

    # Scopo: Hard-delete reso (flusso abbandono bozza orfana). Guard di dominio
    #        (stato DRAFT, 0 righe) applicati nel service.
    def delete_reso(self, reso_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM vendite.resi WHERE id = %s", [reso_id])
            return cursor.rowcount > 0

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Righe (quantita base derivata da qta_operativa via trigger DB;
    #  over-return bloccato dal guard DB a20 con lock FOR UPDATE)
    # ══════════════════════════════════════════════════════════

    # Scopo: Prossimo riga_nr disponibile per il reso (NOT NULL + UNIQUE per reso).
    def next_riga_nr(self, reso_id: int) -> int:
        sql = (
            "SELECT COALESCE(MAX(riga_nr), 0) + 1 "
            "FROM vendite.resi_righe WHERE reso_id = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [reso_id])
            row = cursor.fetchone()
            return int(row[0]) if row else 1

    # Scopo: Inserisce una nuova riga reso. Lo snapshot articolo/descrizione/
    #        UoM/factor/ordine_riga_id arriva dal service (copiato dalla riga
    #        DDT: il reso non inventa articoli). `quantita` (base) NON si
    #        passa: la calcola SEMPRE il trigger `qta_from_operativa` da
    #        `qta_operativa` (obbligatoria, E_QTA_MISSING se assente).
    def create_riga(
        self,
        *,
        reso_id: int,
        riga_nr: int,
        ddt_riga_id: int,
        ordine_riga_id: int | None,
        articolo_id: str,
        descrizione: str,
        tipo_reso_id: int,
        qta_operativa: str,
        uom_operativa_id: int | None = None,
        factor_to_base: str | None = None,
        motivo: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO vendite.resi_righe (
                reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
                articolo_id, descrizione, tipo_reso_id,
                qta_operativa, uom_operativa_id, factor_to_base,
                motivo, meta
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
                articolo_id, descrizione, tipo_reso_id,
                qta_operativa, uom_operativa_id, factor_to_base,
                motivo, json.dumps(meta or {}),
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna una riga reso esistente (qta/tipo/motivo/meta). Meta ::jsonb.
    def update_riga(self, riga_id: int, **kwargs: Any) -> bool:
        return execute_dynamic_update("vendite.resi_righe", riga_id, kwargs)

    # Scopo: Elimina una riga reso (HARD DELETE, solo con testata DRAFT — guard
    #        nel service; il ponte ri-consegna esiste solo post-conferma).
    def delete_riga(self, riga_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.resi_righe WHERE id = %s", [riga_id],
            )
            return cursor.rowcount > 0

    # ══════════════════════════════════════════════════════════
    #  FUNZIONI MADRI DB — conferma / annullo / ri-consegna (atomiche)
    # ══════════════════════════════════════════════════════════

    # Scopo: Conferma reso via fn madre `vendite.fn_conferma_reso` (atomica,
    #        DB-first): guard DRAFT+righe, transizione a CONFERMATO (numero dal
    #        trigger), riapertura residuo ordine, proiezione stato ordine, flip
    #        DDT CONSEGNATO->RESO se reso totale.
    def conferma(self, reso_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT vendite.fn_conferma_reso(%s)", [int(reso_id)])

    # Scopo: Annulla reso via fn madre `vendite.fn_annulla_reso` (atomica):
    #        da DRAFT o CONFERMATO; post-conferma storna gli effetti (residuo,
    #        stato ordine, eventuale rientro DDT RESO->CONSEGNATO); bloccato se
    #        gia' ri-spedito (E_RESO_ANNULLO_CON_RICONSEGNE).
    def annulla(self, reso_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT vendite.fn_annulla_reso(%s)", [int(reso_id)])

    # Scopo: Genera il DDT di ri-consegna via fn madre
    #        `vendite.fn_genera_ddt_riconsegna` (atomica): nuovo DDT DRAFT +
    #        righe + ponte `resi_righe_riconsegne` (+fulfillment se
    #        order-backed). `righe` = [{resi_riga_id, qta}] in UNITA' BASE;
    #        None = tutta la copertura residua. Ritorna l'id del DDT creato.
    def genera_ddt_riconsegna(
        self,
        reso_id: int,
        righe: list[dict[str, Any]] | None = None,
        data: date | None = None,
    ) -> int:
        sql = (
            "SELECT vendite.fn_genera_ddt_riconsegna("
            "%s, %s::jsonb, COALESCE(%s, CURRENT_DATE))"
        )
        return self._chiama_madre_riconsegna(
            sql, reso_id, righe, extra=[data],
        )

    # Scopo: Chiude la ri-consegna via fn madre
    #        `vendite.fn_chiudi_riconsegna_reso` (atomica): dichiara che una
    #        quota di merce resa PER RI-CONSEGNA non tornera' al cliente —
    #        scrive `resi_righe_rinunce` e ri-proietta lo stato ordine (il
    #        residuo si chiude → EVASO). `righe` = [{resi_riga_id, qta}] in
    #        UNITA' BASE, None = tutta la copertura residua; `note` = motivo
    #        facoltativo dell'intera chiusura. Ritorna il numero di righe chiuse.
    #        NON muove numeri: l'accredito in coda resta identico, cambia solo
    #        la sua etichetta (FACOLTATIVA → DOVUTA) — brief §3.
    def chiudi_riconsegna(
        self,
        reso_id: int,
        righe: list[dict[str, Any]] | None = None,
        note: str | None = None,
    ) -> int:
        return self._chiama_madre_riconsegna(
            "SELECT vendite.fn_chiudi_riconsegna_reso(%s, %s::jsonb, %s)",
            reso_id, righe, extra=[note],
        )

    # Scopo: Riapre una chiusura via fn madre
    #        `vendite.fn_riapri_riconsegna_reso` (atomica): cancella le rinunce
    #        e ri-proietta lo stato ordine (torna PARZIALMENTE_EVASO). La quota
    #        torna ri-spedibile e l'accredito torna FACOLTATIVA (round-trip =
    #        stato iniziale). `righe` = [{resi_riga_id, qta}], None = tutte le
    #        rinunce del reso; lo scalo parte dalle rinunce piu' RECENTI (LIFO,
    #        deciso lato DB). Ritorna il numero di righe riaperte.
    def riapri_riconsegna(
        self,
        reso_id: int,
        righe: list[dict[str, Any]] | None = None,
    ) -> int:
        return self._chiama_madre_riconsegna(
            "SELECT vendite.fn_riapri_riconsegna_reso(%s, %s::jsonb)",
            reso_id, righe,
        )

    # Scopo: chiamata alle tre fn madri che lavorano la copertura ri-consegna
    #        (genera / chiudi / riapri). Condividono la stessa forma —
    #        `(reso_id, righe::jsonb [, extra...]) -> integer` con `None` =
    #        "tutta la copertura residua" — quindi anche la serializzazione
    #        delle righe e la lettura dello scalare stanno in un posto solo
    #        (era ripetuta 3 volte identica).
    def _chiama_madre_riconsegna(
        self,
        sql: str,
        reso_id: int,
        righe: list[dict[str, Any]] | None,
        extra: list[Any] | None = None,
    ) -> int:
        # NULL (non "[]") quando le righe non sono specificate: e' il jsonb che
        # le madri leggono come "lavora tutta la copertura residua".
        righe_json = json.dumps(righe) if righe is not None else None
        params: list[Any] = [int(reso_id), righe_json, *(extra or [])]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # ══════════════════════════════════════════════════════════
    #  FUNZIONE MADRE DB — accredito (nota di credito sui resi)
    # ══════════════════════════════════════════════════════════

    # Scopo: Accredita una riga di reso via fn madre
    #        `vendite.fn_accredita_riga_reso` (atomica, DB-first): dalla coda
    #        accrediti genera le righe di RETTIFICA in commessa (quantita'
    #        NEGATIVA, prezzo/sconto/IVA copiati dalla riga di fattura
    #        rettificata) e le registra sul ponte
    #        `vendite.resi_righe_accrediti`. Il DOCUMENTO non nasce qui: la nota
    #        di credito nasce al giro di fatturazione successivo.
    # ⚠️ `RETURNS TABLE`, non uno scalare (brief §20.4): una riga per rettifica
    #    creata — su un kit ne nasce una per componente, e se l'accredito dovuto
    #    consuma piu' righe di fattura a prezzi diversi ne nascono altrettante.
    #    Quindi `rows_to_list`, MAI `fetchone()`: qui un fetchone perderebbe in
    #    silenzio tutte le rettifiche dopo la prima — e la coda, che sottrae la
    #    quota accreditata, direbbe il vero mentre la risposta mente.
    #    Colonne: accredito_id, commessa_attivita_id,
    #    fattura_riga_rettificata_id, qta (unita' di RIGA DI FATTURA),
    #    qta_partita (unita' di MERCE).
    def accredita_riga_reso(self, resi_riga_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM vendite.fn_accredita_riga_reso(%s)",
                [int(resi_riga_id)],
            )
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════
    #  LOOKUP — Risoluzione config/sorgente per creazione
    # ══════════════════════════════════════════════════════════

    # Scopo: DDT sorgente per la creazione reso: uid + stato corrente in una
    #        lettura (guard applicativo parlante "solo DDT CONSEGNATO" nel
    #        service; il trigger DB trgfn_resi_guard_ddt_consegnato e' la
    #        fonte di verita' sull'INSERT).
    def get_ddt_sorgente(self, ddt_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT d.id,
                   d.uid::text AS uid,
                   d.numero,
                   sd.codice_interno AS stato_codice_interno
              FROM vendite.ddt d
              JOIN config.stati_doc_ddt sd ON sd.id = d.stato_doc_ddt_id
             WHERE d.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ddt_id])
            return row_to_dict(cursor)

    # Scopo: Snapshot della riga DDT per la creazione riga reso: articolo/
    #        descrizione/UoM/factor + `ordine_riga_id` dal fulfillment (NULL
    #        per DDT standalone) + `fulfillment_count` (il modello resi assume
    #        1:1 riga-DDT<->riga-ordine: il service rifiuta il caso teorico
    #        1..n invece di attribuire il reso a una riga ordine arbitraria).
    def get_ddt_riga_snapshot(self, ddt_riga_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                dr.id,
                dr.ddt_id,
                dr.articolo_id,
                dr.descrizione,
                dr.quantita,
                dr.qta_operativa,
                dr.uom_operativa_id,
                dr.factor_to_base,
                (
                    SELECT f.ordine_riga_id
                      FROM vendite.ordini_righe_fulfillment f
                     WHERE f.ddt_riga_id = dr.id
                     ORDER BY f.id
                     LIMIT 1
                ) AS ordine_riga_id,
                (
                    SELECT COUNT(*)
                      FROM vendite.ordini_righe_fulfillment f
                     WHERE f.ddt_riga_id = dr.id
                ) AS fulfillment_count
              FROM vendite.ddt_righe dr
             WHERE dr.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ddt_riga_id])
            return row_to_dict(cursor)

    # Scopo: id della sorgente `config.sorgenti` via codice_interno (riuso riga
    #        DDT_VENDITA esistente — mai id hardcoded).
    def get_sorgente_tipo_id_by_codice(self, codice_interno: str) -> int | None:
        sql = """
            SELECT id FROM config.sorgenti
             WHERE codice_interno = %s AND attivo = true
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice_interno])
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: id di uno stato reso via codice_interno (immutabile).
    def get_stato_id_by_codice(self, codice_interno: str) -> int | None:
        sql = """
            SELECT id FROM config.stati_doc_reso
             WHERE codice_interno = %s AND attivo = true
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice_interno])
            row = cursor.fetchone()
            return row[0] if row else None
