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
# `fn_annulla_reso`, `fn_genera_ddt_riconsegna`). Clone strutturale ridotto di
# `ddt_repository` (niente componenti BoM / prezzi / push / PDF): il reso non
# inventa articoli — le righe sono snapshot delle righe del DDT sorgente
# (copiate qui, nessun trigger di copia a DB). La numerazione a CONFERMATO e
# la derivazione `quantita` da `qta_operativa` sono trigger DB; l'over-return
# e l'over-ri-spedizione sono guard DB con lock.

import json
from datetime import date
from typing import Any

from django.db import connection

from apps.core.db._helpers import call_jsonb_fn, row_to_dict, rows_to_list
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
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
    "stato_codice_interno": "v.stato_codice_interno",
    "ddt_origine_numero": "v.ddt_origine_numero",
    "data_insert": "v.data_insert",
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
    ) -> tuple[list[dict[str, Any]], int]:
        order_column = _ORDER_COLS_RESI.get(order_by, _ORDER_COLS_RESI["data"])
        direction = "DESC" if order_dir and order_dir.lower() == "desc" else "ASC"
        safe_limit = max(1, min(int(limit), 200))
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
            ORDER BY {order_column} {direction}, v.id ASC
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
    #        copertura ri-consegna derivata dal ponte `resi_righe_riconsegne`
    #        (qta_riconsegnata/qta_residua/stato_riconsegna, stessa formula
    #        della vista coda — R1: stato DERIVATO, nessuna colonna fisica).
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
                COALESCE(ric.tot, 0::numeric)                 AS qta_riconsegnata,
                (rr.quantita - COALESCE(ric.tot, 0::numeric)) AS qta_residua,
                CASE
                    WHEN tr.riapre_residuo IS NOT TRUE THEN NULL
                    WHEN COALESCE(ric.tot, 0::numeric) = 0::numeric
                        THEN 'DA_RICONSEGNARE'
                    WHEN COALESCE(ric.tot, 0::numeric) < rr.quantita
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

    # Scopo: Coda "da accreditare" (righe reso CONFERMATE a credito) dalla
    #        vista `vw_resi_da_accreditare`. Filtri + scope emittente +
    #        paginazione. La vista si auto-limita ai resi CONFERMATI con
    #        tipo_reso.riapre_residuo=false. Predisposizione slice NC.
    def list_da_accreditare(
        self,
        *,
        billing_account_id: int | None = None,
        data_da: date | None = None,
        data_al: date | None = None,
        auth_user_id: int | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        return self._list_coda(
            "vendite.vw_resi_da_accreditare",
            billing_account_id=billing_account_id,
            data_da=data_da,
            data_al=data_al,
            auth_user_id=auth_user_id,
            limit=limit,
            offset=offset,
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
        auth_user_id: int | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        return self._list_coda(
            "vendite.vw_resi_da_riconsegnare",
            billing_account_id=billing_account_id,
            data_da=data_da,
            data_al=data_al,
            auth_user_id=auth_user_id,
            limit=limit,
            offset=offset,
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
        auth_user_id: int | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
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
        add_emittente_scope_condition(
            conditions, params,
            auth_user_id=auth_user_id,
            column="v.emittente_fiscale_id",
            convention="pk",
        )
        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_sql = f"SELECT COUNT(*) FROM {vista} v {where}"  # noqa: S608
        data_sql = f"""
            SELECT v.* FROM {vista} v
            {where}
            ORDER BY v.data DESC, v.reso_id DESC, v.resi_riga_id ASC
            LIMIT %s OFFSET %s
        """  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            total_count = row[0] if row else 0

            cursor.execute(data_sql, [*params, safe_limit, safe_offset])
            results = rows_to_list(cursor)

        return results, total_count

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
        righe_json = json.dumps(righe) if righe is not None else None
        sql = (
            "SELECT vendite.fn_genera_ddt_riconsegna("
            "%s, %s::jsonb, COALESCE(%s, CURRENT_DATE))"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(reso_id), righe_json, data])
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

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
