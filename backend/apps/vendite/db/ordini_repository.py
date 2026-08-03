# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per ordini di vendita (CRUD testata, righe, componenti BoM).
# ------------------------------------------------------------

# Repository ordini di vendita: letture sulla vista canonica
# `vendite.vw_ordini_lista` (lista DEF-8) e su `vendite.ordini` (dettaglio),
# scritture dirette su tabelle, chiamate a funzioni DB per i componenti BoM.
# Il ricalcolo totali e' gestito da trigger DB su ordini_righe; il backend
# non lo orchestra. Clone strutturale di `preventivi_repository` adattato alle
# colonne reali della testata/riga ordine (riga_nr, sconto_percentuale, iva_id) e
# senza revisioni (gli ordini non hanno `rev`).

import json
from datetime import date
from typing import Any

from django.db import connection

from apps.core.db._helpers import (
    call_jsonb_fn,
    row_to_dict,
    rows_to_list,
    sql_order_direction,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.db.sql_write_helpers import execute_dynamic_update
from apps.vendite.db._componenti_repo_mixin import ComponentiRepositoryMixin
from apps.vendite.db._indirizzi_repo_mixin import IndirizziDocumentoRepositoryMixin
from apps.vendite.db._riepilogo_iva_repo_mixin import RiepilogoIvaRepositoryMixin


# Scopo: Whitelist colonne ORDER BY per la lista ordini (SQL injection safe).
#        La lista legge dalla vista canonica `vendite.vw_ordini_lista`
#        (alias `v`); le chiavi sono i `campo_sorgente` del catalogo liste
#        ('vendite.ordini') che il FE invia come sortField della DataTable.
#        Nomi canonici del soggetto (lezione DEF-8). `serie`/`anno` non
#        ordinabili (fuori dalla whitelist): la chiave logica e' `numero`.
_ORDER_COLS_ORDINI: dict[str, str] = {
    "numero": "v.numero",
    "anno": "v.anno",
    "serie": "v.serie",
    "data": "v.data",
    "ragione_sociale_completa": "v.ragione_sociale_completa",
    "ba_codice": "v.ba_codice",
    "id_fiscale_univoco_cf_piva": "v.id_fiscale_univoco_cf_piva",
    "utility_codice": "v.utility_codice",
    "utility_descrizione": "v.utility_descrizione",
    "totale_doc": "v.totale_doc",
    "imponibile_tot": "v.imponibile_tot",
    "iva_tot": "v.iva_tot",
    "fatturazione_trigger": "v.fatturazione_trigger",
    "stato_descrizione": "v.stato_descrizione",
    "data_insert": "v.data_insert",
    # Colonne lineage (Fase B): pratica + fase ordinabili (frontiera no).
    "pratica_numero": "v.pratica_numero",
    "fase": "v.fase",
}


class OrdiniRepository(
    ComponentiRepositoryMixin,
    RiepilogoIvaRepositoryMixin,
    IndirizziDocumentoRepositoryMixin,
):
    """Repository ordini di vendita.

    Eredita da `ComponentiRepositoryMixin` per il CRUD componenti BoM
    modello unificato (`ordini_righe_componenti`). I metodi specifici
    `init_componenti_riga` (chiama `fn_ordine_riga_componenti_init`) e
    `preview_componenti_riga` (chiama `fn_ordine_riga_componenti_preview`)
    sono definiti localmente. Eredita da `RiepilogoIvaRepositoryMixin` la
    lettura del riepilogo IVA (vista derivata on-the-fly dalle righe attive,
    nessun trigger: a differenza dei preventivi non espone `id` tecnico).
    """

    # Configurazione mixin componenti (tabella + FK riga padre).
    _componenti_table_name = "vendite.ordini_righe_componenti"
    _componenti_fk_riga = "riga_ordine_id"

    # Configurazione mixin riepilogo IVA.
    _riepilogo_iva_vista = "vendite.vw_ordini_riepilogo_iva_dettaglio"
    _riepilogo_iva_fk_documento = "ordine_id"

    # Configurazione mixin indirizzi documento.
    _indirizzi_table = "vendite.ordini_indirizzi"
    _indirizzi_fk_documento = "ordine_id"
    _indirizzi_ambito = "ORDINI"
    _indirizzi_documento_table = "vendite.ordini"
    # Ancora ownership/auto-default = soggetto_ruolo NATIVO della testata
    # (NOT NULL): regge anche l'ordine prospect con billing_account NULL.
    _indirizzi_doc_sr_column = "soggetto_ruolo_id"

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Testata (via vista canonica vw_ordini_lista)
    # ══════════════════════════════════════════════════════════

    # Scopo: Elenco ordini paginato dalla vista canonica
    #        `vendite.vw_ordini_lista` (DEF-8). Espone i nomi CANONICI
    #        (ragione_sociale_completa, id_fiscale_univoco_cf_piva, ba_codice),
    #        `stato_codice_interno` per la severity del Tag FE, e
    #        `emittente_fiscale_id` per lo scope operatore.
    # Risultato: tuple (lista righe, conteggio totale).
    def list_ordini(
        self,
        *,
        stato_codice: str | None = None,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
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
        order_column = _ORDER_COLS_ORDINI.get(order_by, _ORDER_COLS_ORDINI["data"])
        direction = sql_order_direction(order_dir)
        # `max_limit`: lista cap 200 (gia' via parse_list_params), export fino a
        # EXPORT_MAX_ROWS+1 per non troncare in silenzio (guard su COUNT reale).
        safe_limit = max(1, min(int(limit), max_limit))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []

        # `stato_codice` arriva dal FE come `codice_interno` (LookupSelect
        # value-field): nella vista canonica la colonna e' `stato_codice_interno`.
        if stato_codice is not None:
            conditions.append("v.stato_codice_interno = %s")
            params.append(stato_codice)
        if billing_account_id is not None:
            conditions.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        if utility_id is not None:
            conditions.append("v.utility_id = %s")
            params.append(utility_id)
        if data_da is not None:
            conditions.append("v.data >= %s")
            params.append(data_da)
        if data_al is not None:
            conditions.append("v.data <= %s")
            params.append(data_al)
        if search and len(search) >= 3:
            # Ricerca estesa (decisione §8.5): numero + nomi canonici cliente.
            conditions.append(
                "(v.numero ILIKE %s OR v.ragione_sociale_completa ILIKE %s "
                "OR v.ba_codice ILIKE %s OR v.id_fiscale_univoco_cf_piva ILIKE %s)"
            )
            like = f"%{search}%"
            params.extend([like, like, like, like])

        # Scope emittente (defense-in-depth applicativa). La vista
        # `vw_ordini_lista` e' `security_invoker=on`: la RLS della tabella base
        # filtra gia' per emittente in scope; questo filtro si somma (api.md
        # §"Scope emittente"). Array risolto UNA volta in Python dal BB condiviso; convenzione PK su
        # `emittenti_fiscali.id` (memoria feedback_emittente_pk_vs_soggetto_ruolo).
        add_emittente_scope_condition(
            conditions, params,
            auth_user_id=auth_user_id,
            column="v.emittente_fiscale_id",
            convention="pk",
        )

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_sql = f"SELECT COUNT(*) FROM vendite.vw_ordini_lista v {where}"  # noqa: S608
        # Tiebreaker v.id obbligatorio per paginazione deterministica
        # (frontend-standards "Paginazione deterministica").
        data_sql = f"""
            SELECT v.*, s.codice_interno AS frontiera_tipo_codice
            FROM vendite.vw_ordini_lista v
            LEFT JOIN config.sorgenti s ON s.id = v.frontiera_tipo_id
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

    # Scopo: Dettaglio singolo ordine. Riusa la vista canonica (che ha gia'
    #        tutte le decodifiche + agente + documento di origine) e aggiunge
    #        i campi non esposti in lista: `meta`, `storicizza`,
    #        `istanza_utility_id` del BA (serve al FE per la cascata indirizzi
    #        a 3 livelli nel drawer indirizzi documento).
    #        `emittente_ragione_sociale` (ragione sociale del SOGGETTO
    #        emittente, consumata da EmittenteFiscaleField nel drawer EDIT)
    #        arriva dalla vista (esposta dal DB team il 2026-07-13).
    #        Ritorna None se id inesistente.
    def get_ordine(self, ordine_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                v.*,
                o.meta,
                o.storicizza,
                -- Corsia di instradamento: colonna aggiunta dalla Fase B del
                -- brief emissione mirata. Letta dalla tabella e non dalla vista
                -- di lista, che non la espone (la vista e' del team DB).
                o.fatturazione_immediata,
                ba.istanza_utility_id
              FROM vendite.vw_ordini_lista v
              JOIN vendite.ordini o ON o.id = v.id
              LEFT JOIN anagrafiche.billing_account ba
                ON ba.id = v.billing_account_id
             WHERE v.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ordine_id])
            return row_to_dict(cursor)

    # Scopo: Contesto minimo per la generazione documento (stampa PDF). Mirror
    #        di `PreventiviRepository.get_for_documento_generation`: ritorna
    #        id + uid + emittente_fiscale_id, i campi che
    #        `resolve_contesto_documentale` usa per il guard NOT_FOUND/emittente
    #        e l'orchestrator per scope/snapshot. None se id inesistente.
    def get_for_documento_generation(
        self, ordine_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                id,
                uid::text AS uid,
                emittente_fiscale_id
              FROM vendite.ordini
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(ordine_id)])
            return row_to_dict(cursor)

    # Scopo: Capability data-driven dell'ordine per il detail API. Wrapper su
    #        `script.fn_available_actions_ordine` (matrice transizioni
    #        `config.transizioni_stati_ordini`): ritorna jsonb con
    #        available_actions, can_change_state, can_edit_testata/righe,
    #        can_push_commessa(+reason/_reason_key), non_editable_fields,
    #        stato_codice. Blob opaco lato Python (passato intatto al FE).
    #        Pattern gemello di preventivi/offerte/contratti. {} se la fn
    #        ritorna NULL (ordine inesistente — il caller verifica a monte).
    def get_capabilities(self, ordine_id: int) -> dict[str, Any]:
        return call_jsonb_fn("script.fn_available_actions_ordine", ordine_id)

    # Scopo: Stato corrente (codice_interno) dell'ordine. Usato dal service
    #        come guard pre-operazione (es. modifica ammessa solo in DRAFT).
    def get_stato_codice(self, ordine_id: int) -> str | None:
        sql = """
            SELECT sd.codice_interno
              FROM vendite.ordini o
              JOIN config.stati_doc_ordini sd ON sd.id = o.stato_doc_ordine_id
             WHERE o.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ordine_id])
            row = cursor.fetchone()
            return row[0] if row else None

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Righe
    # ══════════════════════════════════════════════════════════

    # Scopo: Righe attive dell'ordine con decodifiche articolo/uom/iva e flag
    #        `is_composito_caso_a` (per il chevron expander FE). Importo riga
    #        calcolato (quantita * prezzo * (1 - sconto%)). Espone anche
    #        l'avanzamento evasione per riga (fulfillment multi-DDT): qta evasa
    #        e residuo in UNITA' OPERATIVA (fulfillment.qta_evasa e' in base;
    #        quantita = qta_operativa * factor_to_base, ROUND 6 come
    #        trgfn_qta_from_operativa). Alimenta il pannello "Genera DDT".
    def list_righe(self, ordine_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                r.id,
                r.ordine_id,
                r.riga_nr,
                r.attivo,
                r.articolo_id,
                a.codice                AS articolo_codice,
                a.descrizione           AS articolo_descrizione,
                r.descrizione,
                r.quantita,
                r.qta_operativa,
                r.factor_to_base,
                r.uom_operativa_id,
                um.codice               AS uom_codice,
                r.prezzo_unitario,
                r.sconto_percentuale,
                r.iva_id,
                iva.codice              AS iva_codice,
                iva.descrizione         AS iva_descrizione,
                iva.aliquota_iva        AS iva_aliquota,
                ROUND(
                    (r.quantita * COALESCE(r.prezzo_unitario, 0::numeric)) *
                    (1::numeric - COALESCE(r.sconto_percentuale, 0::numeric) / 100::numeric),
                    2
                ) AS importo_riga,
                ROUND(
                    COALESCE(ful.qta_evasa_base, 0::numeric)
                    / NULLIF(r.factor_to_base, 0::numeric),
                    6
                ) AS qta_evasa_operativa,
                ROUND(
                    GREATEST(
                        r.quantita - COALESCE(ful.qta_evasa_base, 0::numeric),
                        0::numeric
                    ) / NULLIF(r.factor_to_base, 0::numeric),
                    6
                ) AS qta_residua_operativa,
                r.meta,
                r.data_insert,
                r.data_update,
                EXISTS (
                    SELECT 1
                      FROM vendite.ordini_righe_componenti rc
                     WHERE rc.riga_ordine_id = r.id
                       AND rc.attivo IS TRUE
                ) AS is_composito_caso_a
              FROM vendite.ordini_righe r
              LEFT JOIN catalogo.articoli a    ON a.id   = r.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id = r.uom_operativa_id
              LEFT JOIN config.iva iva         ON iva.id = r.iva_id
              LEFT JOIN LATERAL (
                  SELECT SUM(f.qta_evasa) AS qta_evasa_base
                    FROM vendite.ordini_righe_fulfillment f
                   WHERE f.ordine_riga_id = r.id
              ) ful ON TRUE
             WHERE r.ordine_id = %s
               AND r.attivo IS TRUE
             ORDER BY r.riga_nr, r.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ordine_id])
            return rows_to_list(cursor)

    # Scopo: Carica una singola riga via lookup mirato per id (stessa proiezione
    #        di list_righe senza caricare l'intero elenco). Usato da aggiorna_riga.
    def get_riga(self, riga_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                r.id,
                r.ordine_id,
                r.riga_nr,
                r.attivo,
                r.articolo_id,
                a.codice                AS articolo_codice,
                a.descrizione           AS articolo_descrizione,
                r.descrizione,
                r.quantita,
                r.qta_operativa,
                r.factor_to_base,
                r.uom_operativa_id,
                um.codice               AS uom_codice,
                r.prezzo_unitario,
                r.sconto_percentuale,
                r.iva_id,
                iva.codice              AS iva_codice,
                r.meta,
                EXISTS (
                    SELECT 1
                      FROM vendite.ordini_righe_componenti rc
                     WHERE rc.riga_ordine_id = r.id
                       AND rc.attivo IS TRUE
                ) AS is_composito_caso_a
              FROM vendite.ordini_righe r
              LEFT JOIN catalogo.articoli a    ON a.id   = r.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id = r.uom_operativa_id
              LEFT JOIN config.iva iva         ON iva.id = r.iva_id
             WHERE r.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [riga_id])
            return row_to_dict(cursor)

    # Scopo: Load atomico di un componente con scope completo (componente →
    #        riga → ordine) in un'unica query JOIN, per i guard del service.
    def load_componente_with_scope(
        self, componente_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT c.id          AS componente_id,
                   c.riga_ordine_id,
                   r.ordine_id,
                   sd.codice_interno AS stato_codice_interno
              FROM vendite.ordini_righe_componenti c
              JOIN vendite.ordini_righe r ON r.id = c.riga_ordine_id
              JOIN vendite.ordini o       ON o.id = r.ordine_id
              JOIN config.stati_doc_ordini sd ON sd.id = o.stato_doc_ordine_id
             WHERE c.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [componente_id])
            return row_to_dict(cursor)

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Testata
    # ══════════════════════════════════════════════════════════

    # Scopo: Inserisce un nuovo ordine e restituisce id, uid, numero.
    #        `numero` e' generato dal trigger BEFORE INSERT
    #        (trgfn_ordini_gen_codice) → non si passa. `emittente_fiscale_id`
    #        opzionale: se None il trigger lo valorizza da GUC.
    #        `stato_doc_ordine_id` obbligatorio (DRAFT in create).
    def create_ordine(
        self,
        *,
        soggetto_ruolo_id: int,
        billing_account_id: int | None,
        utility_id: int | None = None,
        emittente_fiscale_id: int | None = None,
        valuta_id: int | None = None,
        modalita_pagamento_id: int | None = None,
        termine_pagamento_id: int | None = None,
        fatturazione_trigger: str | None = None,
        agente_soggetto_ruolo_id: int | None = None,
        data: date | None = None,
        stato_doc_ordine_id: int,
        meta: dict[str, Any] | None = None,
        fatturazione_immediata: bool | None = None,
    ) -> dict[str, Any]:
        cols: list[str] = ["soggetto_ruolo_id", "billing_account_id", "stato_doc_ordine_id"]
        vals: list[Any] = [soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id]
        # Colonne opzionali: omesse se None così i DEFAULT del DB (es.
        # fatturazione_trigger ereditato da BA via trgfn_ordini_normalize,
        # canale_origine='ADMIN') restano attivi.
        optional: dict[str, Any] = {
            "utility_id": utility_id,
            "emittente_fiscale_id": emittente_fiscale_id,
            "valuta_id": valuta_id,
            "modalita_pagamento_id": modalita_pagamento_id,
            "termine_pagamento_id": termine_pagamento_id,
            "fatturazione_trigger": fatturazione_trigger,
            "agente_soggetto_ruolo_id": agente_soggetto_ruolo_id,
            "data": data,
            # Corsia di instradamento (simmetria del flag): None = si lascia il
            # DEFAULT false del DB, cioe' corsia differita.
            "fatturazione_immediata": fatturazione_immediata,
        }
        for col, val in optional.items():
            if val is not None:
                cols.append(col)
                vals.append(val)
        cols.append("meta")
        placeholders = ["%s"] * (len(cols) - 1) + ["%s::jsonb"]
        vals.append(json.dumps(meta or {}))
        sql = (  # noqa: S608 — colonne whitelisted (chiavi statiche)
            f"INSERT INTO vendite.ordini ({', '.join(cols)}) "
            f"VALUES ({', '.join(placeholders)}) "
            f"RETURNING id, uid::text AS uid, numero"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Valorizza la provenienza upstream (documento_origine) di un ordine
    #        appena creato dalla conversione preventivo/offerta → ordine. UPDATE
    #        mirato sulle sole colonne `documento_origine_*` (NON lockate dal
    #        trigger immutabilità cliente, che intercetta solo
    #        billing_account_id/numero/soggetto_ruolo_id) → nessuna interferenza.
    #        Il CHECK di co-presenza richiede entrambe valorizzate insieme.
    def set_documento_origine(
        self, ordine_id: int, tipo: str, origine_id: int,
    ) -> bool:
        sql = """
            UPDATE vendite.ordini
               SET documento_origine_tipo = %s,
                   documento_origine_id   = %s
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo, int(origine_id), int(ordine_id)])
            return cursor.rowcount > 0

    # Scopo: Idempotenza 1:1 della conversione upstream → ordine. Ritorna il
    #        primo ordine già nato da (tipo, origine_id) o None. Specchio
    #        applicativo dell'UNIQUE parziale uq_ordini_v_documento_origine_offerta
    #        (per OFFERTA): il guard BE in crea_ordine_da_offerta lo usa per
    #        fallire fast con E_ORD_OFFERTA_GIA_CONVERTITA prima di lavorare,
    #        lasciando l'UNIQUE come rete sulla race concorrente.
    def get_ordine_by_documento_origine(
        self, tipo: str, origine_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT id, numero
              FROM vendite.ordini
             WHERE documento_origine_tipo = %s
               AND documento_origine_id   = %s
             ORDER BY id
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo, int(origine_id)])
            return row_to_dict(cursor)

    # Scopo: Risolve l'ordine COLLEGATO a una PRATICA (pratiche_sorgenti, sorgente
    #        ORDINE_VENDITA, ruolo COLLEGATO; aggancio fatto da
    #        PostSmistamentoHandler). Alimenta gli step pratica a valle
    #        (CONFERMA_ORDINE / INVIO_COMMESSA) che aprono l'OrdiniDrawer su
    #        quell'ordine. None se non agganciato. Cross-schema read vendite→pratiche
    #        (direzione anelli consentita). sorgente_uid = id ordine (text).
    def get_ordine_id_by_pratica(self, pratica_id: int) -> int | None:
        sql = """
            SELECT ps.sorgente_uid::bigint
              FROM pratiche.pratiche_sorgenti ps
              JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id
             WHERE s.codice_interno = 'ORDINE_VENDITA'
               AND ps.ruolo_link    = 'COLLEGATO'
               AND ps.pratica_id    = %s
             ORDER BY ps.id DESC
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            row = cursor.fetchone()
        return int(row[0]) if row else None

    # Scopo: Aggiorna campi modificabili della testata ordine. Accetta None per
    #        azzerare campi nullable. Campi jsonb (meta) serializzati ::jsonb.
    def update_ordine(self, ordine_id: int, **kwargs: Any) -> bool:
        return execute_dynamic_update("vendite.ordini", ordine_id, kwargs)

    # Scopo: Hard-delete ordine (flusso abbandono bozza). Guard di dominio
    #        (stato DRAFT, no DDT/fatture collegate) applicati nel service +
    #        trigger DB (trgfn_dlt_block_ordrig_ddtrig sulle righe). Le righe e
    #        i componenti hanno ON DELETE CASCADE.
    def delete_ordine(self, ordine_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.ordini WHERE id = %s",
                [ordine_id],
            )
            return cursor.rowcount > 0

    # Scopo: Cambia stato ordine via UPDATE diretto di stato_doc_ordine_id. La
    #        transizione e' validata dal trigger DB
    #        `trgfn_ordini_guard_transizione_approvazione` (niente fn dedicata).
    #        Usato per la conferma (DRAFT → CONFERMATO).
    def update_stato(self, ordine_id: int, stato_doc_ordine_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE vendite.ordini SET stato_doc_ordine_id = %s WHERE id = %s",
                [stato_doc_ordine_id, ordine_id],
            )
            return cursor.rowcount > 0

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Righe (ricalcolo totali automatico via trigger DB)
    # ══════════════════════════════════════════════════════════

    # Scopo: Prossimo riga_nr disponibile per l'ordine (riga_nr e' NOT NULL +
    #        UNIQUE per ordine, senza autoassegnazione DB).
    def next_riga_nr(self, ordine_id: int) -> int:
        sql = (
            "SELECT COALESCE(MAX(riga_nr), 0) + 1 "
            "FROM vendite.ordini_righe WHERE ordine_id = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [ordine_id])
            row = cursor.fetchone()
            return int(row[0]) if row else 1

    # Scopo: Lookup lean del flag `is_composito` dell'articolo (default prezzo
    #        padre composito = 0 / NULL; il prezzo padre e' SUM(figli) calcolata
    #        dal trigger DB post init componenti).
    def is_articolo_composito(self, articolo_id: str) -> bool:
        from apps.catalogo.db.catalogo_repository import CatalogoRepository
        return CatalogoRepository().is_articolo_composito(articolo_id)

    # Scopo: Inserisce una nuova riga ordine. `riga_nr` assegnato dal service
    #        via next_riga_nr. Ritorna id.
    def create_riga(
        self,
        *,
        ordine_id: int,
        riga_nr: int,
        articolo_id: str,
        descrizione: str | None = None,
        quantita: str | None = None,
        qta_operativa: str | None = None,
        uom_operativa_id: int | None = None,
        factor_to_base: str | None = None,
        prezzo_unitario: str | None = None,
        sconto_percentuale: str | None = None,
        iva_id: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO vendite.ordini_righe (
                ordine_id, riga_nr, articolo_id, descrizione,
                quantita, qta_operativa, uom_operativa_id, factor_to_base,
                prezzo_unitario, sconto_percentuale, iva_id, meta
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                ordine_id, riga_nr, articolo_id, descrizione,
                quantita, qta_operativa, uom_operativa_id, factor_to_base,
                prezzo_unitario, sconto_percentuale, iva_id,
                json.dumps(meta or {}),
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna una riga ordine esistente. Campi jsonb (meta) ::jsonb.
    def update_riga(self, riga_id: int, **kwargs: Any) -> bool:
        return execute_dynamic_update("vendite.ordini_righe", riga_id, kwargs)

    # Scopo: Elimina una riga ordine (HARD DELETE). La FK
    #        ordini_righe_componenti.riga_ordine_id ha ON DELETE CASCADE.
    #        Il trigger DB trgfn_dlt_block_ordrig_ddtrig blocca la delete se la
    #        riga e' gia' collegata a un DDT.
    def delete_riga(self, riga_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.ordini_righe WHERE id = %s",
                [riga_id],
            )
            return cursor.rowcount > 0

    # ══════════════════════════════════════════════════════════
    #  Componenti riga (BoM CASO A) — init/preview
    #  CRUD list/get/update/delete/purge da ComponentiRepositoryMixin.
    # ══════════════════════════════════════════════════════════

    # Scopo: Converte emittente_fiscale_id (PK) nel suo soggetto_ruolo_id, per
    #        le fn componenti che attendono sr_id (memoria
    #        feedback_emittente_pk_vs_soggetto_ruolo).
    def get_emittente_sr_id_by_fiscale_id(self, fiscale_id: int) -> int | None:
        from apps.anagrafiche.db.emittenti_fiscali_repository import (
            EmittentiFiscaliRepository,
        )
        return EmittentiFiscaliRepository().get_sr_id_by_fiscale_id(fiscale_id)

    # Scopo: Popola i componenti BoM per una riga padre composita invocando
    #        `vendite.fn_ordine_riga_componenti_init` (modello unificato).
    #        Idempotente: ritorna 0 se gia' presenti o articolo non composito.
    def init_componenti_riga(
        self,
        *,
        riga_id: int,
        emittente_soggetto_ruolo_id: int,
        data_riferimento: date,
        componenti_overrides: dict[str, Any] | None = None,
    ) -> int:
        overrides_json: str | None
        if componenti_overrides is None:
            overrides_json = None
        else:
            overrides_json = json.dumps(
                {str(k): str(v) for k, v in componenti_overrides.items()},
            )
        sql = (
            "SELECT vendite.fn_ordine_riga_componenti_init("
            "%s, %s, %s, %s::jsonb)"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                riga_id, emittente_soggetto_ruolo_id, data_riferimento,
                overrides_json,
            ])
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    # Scopo: Preview read-only componenti BoM per il drawer riga (modello
    #        unificato). Per ogni componente attivo/valido alla data ritorna
    #        prezzo_suggerito (NULL se resolver fail) + resolver_error_reason.
    def preview_componenti_riga(
        self,
        *,
        articolo_id: str,
        uom_id: int | None,
        quantita_padre,
        data_riferimento: date,
        ba_id: int | None,
        utility_id: int | None,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT articolo_componente_id,
                   componente_id,
                   componente_codice,
                   componente_descrizione,
                   coeff_qta_snapshot,
                   quantita_componente,
                   uom_id,
                   uom_codice,
                   iva_id,
                   prezzo_suggerito,
                   origine_prezzo,
                   resolver_error_reason,
                   obbligatorio,
                   esposto_in_fattura
              FROM vendite.fn_ordine_riga_componenti_preview(
                  %s, %s, %s, %s, %s, %s, %s, %s
              )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                articolo_id, uom_id, quantita_padre, data_riferimento,
                ba_id, utility_id, emittente_soggetto_ruolo_id,
                classe_utenza_id,
            ])
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════
    #  INTEGRAZIONE — Push commessa
    # ══════════════════════════════════════════════════════════

    # Scopo: Conteggio righe ordine eleggibili per il push singolo in commessa
    #        (via fn DB con parametro p_ordine_id). Usato dal service per il
    #        gating del pulsante push.
    def count_righe_pushable(self, ordine_id: int) -> int:
        sql = """
            SELECT COUNT(*) AS cnt
              FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ordine_id])
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    # ══════════════════════════════════════════════════════════
    #  LOOKUP — Risoluzione config per creazione/transizioni
    # ══════════════════════════════════════════════════════════

    # Scopo: soggetto_ruolo_id del cliente a partire dal billing_account.
    #        La testata ordine ha `soggetto_ruolo_id` NOT NULL mentre il FE
    #        seleziona il billing_account (cliente=BA, memoria
    #        feedback_cliente_billing_account): si deriva qui.
    def get_soggetto_ruolo_id_by_ba(self, billing_account_id: int) -> int | None:
        sql = "SELECT soggetto_ruolo_id FROM anagrafiche.billing_account WHERE id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [billing_account_id])
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: id di uno stato ordine via codice_interno (immutabile).
    def get_stato_id_by_codice(self, codice_interno: str) -> int | None:
        sql = """
            SELECT id FROM config.stati_doc_ordini
             WHERE codice_interno = %s AND attivo = true
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice_interno])
            row = cursor.fetchone()
            return row[0] if row else None
