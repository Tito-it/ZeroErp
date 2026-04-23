# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per preventivi vendita (CRUD testata, righe, indirizzi, integrazione).
# ------------------------------------------------------------

# Repository preventivi vendita: letture su viste DB denormalizzate,
# scritture dirette su tabelle, chiamate a funzioni DB per operazioni complesse.
# Il ricalcolo totali e' gestito da trigger AFTER su preventivi_righe.

import json
from datetime import date
from typing import Any

from django.db import connection

from apps.core.db._helpers import row_to_dict, rows_to_list
from apps.vendite.types import (
    PreventivoDetailRow,
    PreventivoIndirizzoRow,
    PreventivoListRow,
    PreventivoPraticaRow,
    PreventivoRigaRow,
    PreventivoStatoFatturazioneRow,
)


class PreventiviRepository:

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Testata (via vista vw_preventivi_list)
    # ══════════════════════════════════════════════════════════

    # Scopo: Restituisce elenco preventivi paginato dalla vista denormalizzata.
    # La vista include emittente_fiscale_id per scope permessi.
    # Perimetro: sola lettura; nessun side-effect.
    # Risultato: tuple (lista PreventivoListRow, conteggio totale).
    def list_preventivi(
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
    ) -> tuple[list[PreventivoListRow], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []

        # Filtri dinamici parametrizzati
        if stato_codice is not None:
            conditions.append("v.stato_codice = %s")
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
            conditions.append("(v.numero ILIKE %s OR v.cliente_denominazione ILIKE %s)")
            # cliente_denominazione nella vista e' ragione_sociale_completa
            like = f"%{search}%"
            params.extend([like, like])

        # Scope emittente: la vista espone emittente_fiscale_id
        if auth_user_id is not None:
            conditions.append(
                "(script.fn_get_emittenti_scope_sr_ids(%s) IS NULL "
                "OR v.emittente_fiscale_id = ANY("
                "script.fn_get_emittenti_scope_sr_ids(%s)))"
            )
            params.extend([auth_user_id, auth_user_id])

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_sql = f"SELECT COUNT(*) FROM vendite.vw_preventivi_list v {where}"
        data_sql = f"""
            SELECT * FROM vendite.vw_preventivi_list v
            {where}
            ORDER BY v.data DESC, v.numero DESC
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            total_count = row[0] if row else 0

            cursor.execute(data_sql, [*params, safe_limit, safe_offset])
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Restituisce dettaglio singolo preventivo con tutte le decodifiche.
    # Usa query diretta (non vista lista) per includere campi extra (meta, storicizza, audit).
    def get_preventivo(self, preventivo_id: int) -> PreventivoDetailRow | None:
        sql = """
            SELECT
                p.id,
                p.uid::text AS uid,
                p.numero,
                p.rev,
                p.is_revision_attiva,
                p.data::text AS data,
                p.stato_doc_preventivo_id,
                sdp.codice_interno AS stato_codice_interno,
                sdp.codice AS stato_codice,
                sdp.descrizione AS stato_descrizione,
                p.billing_account_id,
                s.ragione_sociale_completa AS cliente_denominazione,
                p.utility_id,
                u.descrizione AS utility_descrizione,
                p.istanza_utility_id,
                p.valuta_id,
                v.codice AS valuta_codice,
                p.termine_pagamento_id,
                tp.descrizione AS termine_pagamento_descrizione,
                p.validita_dal::text AS validita_dal,
                p.validita_al::text AS validita_al,
                p.competenza_mese::text AS competenza_mese,
                COALESCE(p.fatturazione_immediata, false) AS fatturazione_immediata,
                p.totale_imponibile::text AS totale_imponibile,
                p.totale_iva::text AS totale_iva,
                p.totale_documento::text AS totale_documento,
                p.storicizza,
                p.meta,
                p.data_insert::text AS data_insert,
                p.user_insert,
                p.data_update::text AS data_update,
                p.user_update
            FROM vendite.preventivi p
            JOIN config.stati_doc_preventivi sdp ON sdp.id = p.stato_doc_preventivo_id
            LEFT JOIN anagrafiche.billing_account ba ON ba.id = p.billing_account_id
            LEFT JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
            LEFT JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
            LEFT JOIN config.utilities u ON u.id = p.utility_id
            LEFT JOIN config.valute v ON v.id = p.valuta_id
            LEFT JOIN config.termini_pagamento tp ON tp.id = p.termine_pagamento_id
            WHERE p.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return row_to_dict(cursor)

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Righe (via vista vw_preventivi_righe_dettaglio)
    # ══════════════════════════════════════════════════════════

    # Scopo: Restituisce righe preventivo dalla vista denormalizzata.
    # La vista include importo_riga e importo_iva_riga calcolati.
    def list_righe(self, preventivo_id: int) -> list[PreventivoRigaRow]:
        sql = """
            SELECT * FROM vendite.vw_preventivi_righe_dettaglio
            WHERE preventivo_id = %s
            ORDER BY ordine, id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Indirizzi
    # ══════════════════════════════════════════════════════════

    # Scopo: Restituisce indirizzi preventivo con tipo.
    def list_indirizzi(self, preventivo_id: int) -> list[PreventivoIndirizzoRow]:
        sql = """
            SELECT
                pi.id,
                pi.preventivo_id,
                pi.tipo_indirizzo_id,
                ti.descrizione AS tipo_indirizzo_descrizione,
                pi.snapshot,
                pi.origine_indirizzo_id,
                pi.origine_soggetto_ruolo_id
            FROM vendite.preventivi_indirizzi pi
            LEFT JOIN config.tipi_indirizzi ti ON ti.id = pi.tipo_indirizzo_id
            WHERE pi.preventivo_id = %s
            ORDER BY pi.tipo_indirizzo_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Testata
    # ══════════════════════════════════════════════════════════

    # Scopo: Inserisce un nuovo preventivo e restituisce id e uid.
    def create_preventivo(
        self,
        *,
        billing_account_id: int | None,
        utility_id: int,
        istanza_utility_id: int | None = None,
        valuta_id: int | None = None,
        termine_pagamento_id: int | None = None,
        validita_dal: date | None = None,
        validita_al: date | None = None,
        competenza_mese: date | None = None,
        fatturazione_immediata: bool = False,
        stato_doc_preventivo_id: int,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO vendite.preventivi (
                billing_account_id, utility_id, istanza_utility_id,
                valuta_id, termine_pagamento_id,
                validita_dal, validita_al, competenza_mese,
                fatturazione_immediata, stato_doc_preventivo_id, meta
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            RETURNING id, uid::text AS uid, numero
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                billing_account_id, utility_id, istanza_utility_id,
                valuta_id, termine_pagamento_id,
                validita_dal, validita_al, competenza_mese,
                fatturazione_immediata, stato_doc_preventivo_id,
                json.dumps(meta or {}),
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna campi modificabili della testata preventivo.
    # Accetta anche None per azzerare campi nullable.
    # Campi jsonb (meta) vengono serializzati con json.dumps e cast ::jsonb.
    def update_preventivo(
        self,
        preventivo_id: int,
        **kwargs: Any,
    ) -> bool:
        fields: list[str] = []
        params: list[Any] = []
        for col, val in kwargs.items():
            if isinstance(val, dict):
                fields.append(f"{col} = %s::jsonb")
                params.append(json.dumps(val))
            else:
                if isinstance(val, str):
                    val = val.strip()
                fields.append(f"{col} = %s")
                params.append(val)
        if not fields:
            return False
        params.append(preventivo_id)
        sql = f"UPDATE vendite.preventivi SET {', '.join(fields)} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0

    # Scopo: Cambia stato preventivo invocando la funzione DB.
    # La funzione valida transizione via config.transizioni_stati_preventivi,
    # guard su righe/totale per EMESSO, blocco annullamento con commessa attiva.
    def cambia_stato(
        self, preventivo_id: int, nuovo_stato_codice: str, user: str
    ) -> dict[str, Any]:
        sql = """
            SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, %s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id, nuovo_stato_codice, user])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Crea nuova revisione invocando la funzione DB.
    # Copia testata + righe attive + indirizzi, disattiva revisione precedente.
    def crea_revisione(self, preventivo_id: int, user: str) -> dict[str, Any]:
        sql = """
            SELECT * FROM vendite.fn_crea_revisione_preventivo(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id, user])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Righe
    #  Nota: il ricalcolo totali e' automatico via trigger AFTER
    #  trg_preventivi_righe_z90_ricalcola_totali_ins_upd_dlt
    # ══════════════════════════════════════════════════════════

    # Scopo: Inserisce una nuova riga preventivo. I campi
    #        `stato_approvazione_prezzo` + `pratica_approvazione_prezzo_id`
    #        servono al workflow L3 (Sprint E listini v5 §14.6): default NULL
    #        per righe normali, valorizzati se la creazione contestualmente
    #        attiva una richiesta di approvazione out-of-policy.
    def create_riga(
        self,
        *,
        preventivo_id: int,
        articolo_id: str,
        descrizione: str | None = None,
        quantita: str | None = None,
        qta_operativa: str | None = None,
        uom_operativa_id: int | None = None,
        factor_to_base: str | None = None,
        prezzo_unitario: str | None = None,
        sconto_percentuale: str | None = None,
        iva_id: int | None = None,
        ordine: int | None = None,
        meta: dict[str, Any] | None = None,
        stato_approvazione_prezzo: str | None = None,
        pratica_approvazione_prezzo_id: int | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO vendite.preventivi_righe (
                preventivo_id, articolo_id, descrizione,
                quantita, qta_operativa, uom_operativa_id, factor_to_base,
                prezzo_unitario, sconto_percentuale, iva_id, ordine, meta,
                stato_approvazione_prezzo, pratica_approvazione_prezzo_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s
            )
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                preventivo_id, articolo_id, descrizione,
                quantita, qta_operativa, uom_operativa_id, factor_to_base,
                prezzo_unitario, sconto_percentuale, iva_id, ordine,
                json.dumps(meta or {}),
                stato_approvazione_prezzo, pratica_approvazione_prezzo_id,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna una riga preventivo esistente.
    # Campi jsonb (meta) vengono serializzati con json.dumps e cast ::jsonb.
    def update_riga(self, riga_id: int, **kwargs: Any) -> bool:
        fields: list[str] = []
        params: list[Any] = []
        for col, val in kwargs.items():
            if isinstance(val, dict):
                fields.append(f"{col} = %s::jsonb")
                params.append(json.dumps(val))
            else:
                if isinstance(val, str):
                    val = val.strip()
                fields.append(f"{col} = %s")
                params.append(val)
        if not fields:
            return False
        params.append(riga_id)
        sql = f"UPDATE vendite.preventivi_righe SET {', '.join(fields)} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0

    # Scopo: Disattiva una riga preventivo (soft delete).
    def delete_riga(self, riga_id: int) -> bool:
        sql = "UPDATE vendite.preventivi_righe SET attivo = false WHERE id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [riga_id])
            return cursor.rowcount > 0

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Indirizzi
    # ══════════════════════════════════════════════════════════

    # Scopo: Upsert indirizzo preventivo (uno per tipo).
    def upsert_indirizzo(
        self,
        *,
        preventivo_id: int,
        tipo_indirizzo_id: int,
        snapshot: dict[str, Any],
        origine_indirizzo_id: int | None = None,
        origine_soggetto_ruolo_id: int | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO vendite.preventivi_indirizzi (
                preventivo_id, tipo_indirizzo_id, snapshot,
                origine_indirizzo_id, origine_soggetto_ruolo_id
            ) VALUES (%s, %s, %s::jsonb, %s, %s)
            ON CONFLICT ON CONSTRAINT uq_preventivi_indirizzi_uno_per_tipo_
            DO UPDATE SET
                snapshot = EXCLUDED.snapshot,
                origine_indirizzo_id = EXCLUDED.origine_indirizzo_id,
                origine_soggetto_ruolo_id = EXCLUDED.origine_soggetto_ruolo_id
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                preventivo_id, tipo_indirizzo_id, json.dumps(snapshot),
                origine_indirizzo_id, origine_soggetto_ruolo_id,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # ══════════════════════════════════════════════════════════
    #  INTEGRAZIONE — Commesse / Fatturazione
    # ══════════════════════════════════════════════════════════

    # Scopo: Discovery righe preventivo eleggibili per push in commessa.
    # TODO: l'orchestrazione completa (get_or_create_commessa + upsert righe)
    # sara' aggiunta quando il CommessePushOrchestrator verra' esteso per
    # supportare il push singolo preventivo (oggi gestisce solo push batch).
    def count_righe_pushable(self, preventivo_id: int) -> int:
        sql = """
            SELECT count(*) AS cnt
            FROM vendite.fn_list_preventivi_da_pushare()
            WHERE preventivo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            row = cursor.fetchone()
            return row[0] if row else 0

    # Scopo: Stato fatturazione aggregato del preventivo (per badge UI).
    # Usa la vista DB che fa il join via segment_key e filtra per sorgente PREVENTIVO.
    def stato_fatturazione(self, preventivo_id: int) -> PreventivoStatoFatturazioneRow | None:
        sql = """
            SELECT *
            FROM vendite.vw_preventivi_stato_fatturazione
            WHERE preventivo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return row_to_dict(cursor)

    # ══════════════════════════════════════════════════════════
    #  INTEGRAZIONE — Pratiche
    # ══════════════════════════════════════════════════════════

    # Scopo: Risolve contesto anagrafico dal preventivo per creazione pratica.
    # Restituisce emittente_fiscale_id (PK numerica anagrafiche.emittenti_fiscali.id),
    # soggetto_id e soggetto_ruolo_id ricavati dal billing_account del preventivo.
    # L'emittente fiscale viene risolto via anagrafiche.fn_get_emittente_fiscale_pk
    # (mapping specifico BA -> fallback gestore globale, errore esplicito se manca).
    def resolve_contesto_pratica(self, preventivo_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                anagrafiche.fn_get_emittente_fiscale_pk(p.billing_account_id)
                    AS emittente_fiscale_id,
                sr.soggetto_id::text AS soggetto_id,
                ba.soggetto_ruolo_id
            FROM vendite.preventivi p
            JOIN anagrafiche.billing_account ba ON ba.id = p.billing_account_id
            JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
            WHERE p.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return row_to_dict(cursor)

    # Scopo: Inserisce link preventivo → pratica in pratiche_sorgenti.
    def link_pratica(
        self,
        *,
        pratica_id: int,
        sorgente_tipo_id: int,
        sorgente_uid: str,
        ruolo_link: str = "ROOT",
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO pratiche.pratiche_sorgenti (
                pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link
            ) VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Restituisce pratiche collegate al preventivo via vista DB.
    # La vista filtra gia' per sorgente_tipo codice = 'PREVENTIVO'.
    def list_pratiche(self, preventivo_id: int) -> list[PreventivoPraticaRow]:
        sql = """
            SELECT *
            FROM vendite.vw_preventivi_pratiche
            WHERE preventivo_id = %s
            ORDER BY data_apertura DESC NULLS LAST
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════
    #  LOOKUP — Risoluzione config per creazione
    # ══════════════════════════════════════════════════════════

    # Scopo: Restituisce l'id dello stato DRAFT (bozza) da config.stati_doc_preventivi.
    # Usa codice_interno (immutabile) per lookup applicativi.
    def get_stato_bozza_id(self) -> int | None:
        sql = """
            SELECT id FROM config.stati_doc_preventivi
            WHERE codice_interno = 'DRAFT' AND attivo = true
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: Restituisce l'id del tipo sorgente PREVENTIVO da config.sorgenti.
    def get_sorgente_tipo_preventivo_id(self) -> int | None:
        sql = """
            SELECT id FROM config.sorgenti
            WHERE codice_interno = 'PREVENTIVO' AND attivo = true
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
            return row[0] if row else None
