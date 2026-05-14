# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per gestione emittenti fiscali (ruolo EF).
#        CRUD emittenti, lista paginata via JOIN soggetti_ruoli + soggetti.
#        Accesso DB-first via cursor e funzione script.fn_get_or_create_soggetto_ruolo.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.anagrafiche.db._helpers import extract_paginated
from apps.core.db._helpers import row_to_dict, rows_to_list


_EMITTENTI_ORDER_COLS = {
    "codice", "descrizione", "ragione_sociale_completa",
    "attivo", "data_insert",
}


class EmittentiFiscaliRepository:
    """Accesso DB per emittenti fiscali."""

    # =================================================================
    # Lookup
    # =================================================================

    # Scopo: Risolve il `soggetto_ruolo_id` dell'emittente fiscale dato il
    # suo `id` (PK reale). Single source of truth per i caller cross-dominio
    # (vendite/preventivi/contratti) che devono passare lo sr_id alle fn
    # pricing/componenti (che lavorano su soggetto_ruolo_id, non sulla PK
    # `emittenti_fiscali.id`). Vedi memoria `feedback_emittente_pk_vs_soggetto_ruolo`.
    # Ritorna None se l'id non esiste. Estratto da
    # `*Repository.get_emittente_sr_id_by_fiscale_id` duplicato simmetrico
    # (Fase H residue 2026-05-14): i repo sorgente ora delegano qui.
    def get_sr_id_by_fiscale_id(self, fiscale_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali "
                "WHERE id = %s",
                [fiscale_id],
            )
            row = cursor.fetchone()
            return int(row[0]) if row else None

    # =================================================================
    # Creazione
    # =================================================================

    # Scopo: Ottiene o crea il ruolo EMITTENTE FISCALE per un soggetto.
    #        Delega alla funzione DB script.fn_get_or_create_soggetto_ruolo con codice 'EF'.
    def get_or_create_ruolo_emittente(self, soggetto_id: str) -> int:
        sql = "SELECT script.fn_get_or_create_soggetto_ruolo(%s, 'EF') AS ruolo_id"
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Crea record emittente fiscale.
    #        I trigger DB gestiscono: guard ruolo EF, normalize, audit, tx_id, storicizzazione,
    #        bootstrap del default mapping in emittenti_fiscali_billing_account (primo emittente).
    #        Campi obbligatori (NOT NULL su tabella): soggetto_ruolo_id, codice, descrizione.
    def create_emittente(self, **kwargs: Any) -> int:
        # Colonne fisse obbligatorie
        cols = ["soggetto_ruolo_id", "codice", "descrizione"]
        vals: list[Any] = [
            kwargs["soggetto_ruolo_id"],
            kwargs["codice"],
            kwargs["descrizione"],
        ]
        # Colonne opzionali: incluse solo se valorizzate (non None)
        _OPTIONAL = [
            "attivo",
            "regime_fiscale_rf",
            "bollo_auto",
            "bollo_soglia",
            "rounding_policy",
            "valuta_id",
        ]
        for col in _OPTIONAL:
            val = kwargs.get(col)
            if val is not None:
                cols.append(col)
                vals.append(val)
        placeholders = ["%s"] * len(cols)
        sql = f"""
            INSERT INTO anagrafiche.emittenti_fiscali ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata emittenti fiscali con search e filtro attivo.
    #        Join con soggetti_ruoli e soggetti per display fields.
    def list_emittenti_fiscali(
        self, *,
        search: str | None = None,
        attivo: bool | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "descrizione",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in _EMITTENTI_ORDER_COLS else "descrizione"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT ef.id,
                   ef.uid,
                   ef.soggetto_ruolo_id,
                   ef.codice,
                   ef.descrizione,
                   ef.attivo,
                   ef.regime_fiscale_rf,
                   ef.bollo_auto,
                   ef.bollo_soglia,
                   ef.rounding_policy,
                   ef.valuta_id,
                   v.iso_code AS valuta_iso,
                   sr.soggetto_id,
                   s.ragione_sociale_completa,
                   s.codice_fiscale,
                   s.partita_iva,
                   ef.data_insert,
                   ef.data_update,
                   COUNT(*) OVER () AS total_count
              FROM anagrafiche.emittenti_fiscali ef
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
              JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
              LEFT JOIN config.valute v          ON v.id  = ef.valuta_id
             WHERE (%s::text IS NULL OR (
                       ef.codice ILIKE %s
                    OR ef.descrizione ILIKE %s
                    OR s.ragione_sociale_completa ILIKE %s
                    OR s.codice_fiscale ILIKE %s
                    OR s.partita_iva ILIKE %s
                   ))
               AND (%s::boolean IS NULL OR ef.attivo = %s)
             ORDER BY {order_col} {direction}, ef.id
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params: list[Any] = [
            search_pattern, search_pattern, search_pattern,
            search_pattern, search_pattern, search_pattern,
            attivo, attivo,
            limit, offset,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return extract_paginated(cursor)

    # Scopo: Dettaglio completo di un emittente fiscale con dati soggetto e valuta.
    def get_emittente(self, emittente_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT ef.id,
                   ef.uid,
                   ef.soggetto_ruolo_id,
                   ef.codice,
                   ef.descrizione,
                   ef.attivo,
                   ef.regime_fiscale_rf,
                   ef.bollo_auto,
                   ef.bollo_soglia,
                   ef.rounding_policy,
                   ef.valuta_id,
                   v.iso_code             AS valuta_iso,
                   v.descrizione          AS valuta_descrizione,
                   ef.brand_meta,
                   -- Soggetto
                   sr.soggetto_id,
                   s.ragione_sociale_completa,
                   s.codice_fiscale,
                   s.partita_iva,
                   -- Audit
                   ef.data_insert,
                   ef.data_update
              FROM anagrafiche.emittenti_fiscali ef
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
              JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
              LEFT JOIN config.valute v          ON v.id  = ef.valuta_id
             WHERE ef.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [emittente_id])
            return row_to_dict(cursor)

    # =================================================================
    # Aggiornamento
    # =================================================================

    # Campi editabili sull'emittente (codice escluso: bloccato dal trigger lock_columns).
    _UPDATE_ALLOWED = {
        "descrizione",
        "attivo",
        "regime_fiscale_rf",
        "bollo_auto",
        "bollo_soglia",
        "rounding_policy",
        "valuta_id",
    }
    _UPDATE_NULLABLE = {
        "regime_fiscale_rf",
        "rounding_policy",
        "bollo_soglia",
        "valuta_id",
    }

    # Scopo: Aggiorna campi editabili di un emittente fiscale (delta update).
    #        Il campo codice e' bloccato dal trigger DB (lock_columns) e va escluso.
    def update_emittente(self, emittente_id: int, data: dict[str, Any]) -> bool:
        # Normalizza stringhe vuote a None per campi nullable
        for k in self._UPDATE_NULLABLE:
            if k in data and isinstance(data[k], str) and not data[k].strip():
                data[k] = None
        fields = [(k, v) for k, v in data.items() if k in self._UPDATE_ALLOWED]
        if not fields:
            return False
        set_clause = ", ".join(f"{f[0]} = %s" for f in fields)
        values: list[Any] = [f[1] for f in fields]
        values.append(emittente_id)
        sql = f"UPDATE anagrafiche.emittenti_fiscali SET {set_clause} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    # =================================================================
    # Risoluzione id <-> soggetto_ruolo_id
    # =================================================================

    # Scopo: Risolve soggetto_ruolo_id da emittente_id (per metodi sub-resource).
    def get_soggetto_ruolo_id(self, emittente_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali WHERE id = %s",
                [emittente_id],
            )
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: Restituisce la P.IVA del soggetto base (None se non valorizzata).
    #        Usato per validare che l'emittente fiscale sia legato a un soggetto
    #        con P.IVA valida (requisito legale per emissione fattura SDI).
    def get_soggetto_partita_iva(self, soggetto_id: str) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT partita_iva FROM anagrafiche.soggetti WHERE id = %s",
                [soggetto_id],
            )
            row = cursor.fetchone()
            if not row:
                return None
            piva = row[0]
            if isinstance(piva, str):
                piva = piva.strip()
                return piva or None
            return piva


# =================================================================
# Sotto-tabella: emittenti_fiscali_billing_account (mapping BA -> emittente)
# =================================================================


class EmittentiFiscaliBillingAccountRepository:
    """Accesso DB per il mapping BA -> emittente fiscale.

    Regole:
      - Il default globale e' il record con billing_account_id IS NULL e is_default = true.
      - Esiste al piu' UN default (UNIQUE INDEX su is_default WHERE is_default).
      - Ogni BA puo' essere mappato a un solo emittente (UNIQUE su billing_account_id).
      - is_default e billing_account_id sono vincolati da un CHECK: True+NULL oppure False+NOT NULL.
    """

    _ORDER_COLS = {
        "billing_account_codice", "billing_account_ragione_sociale",
        "id_fiscale_univoco", "is_default", "data_insert",
    }

    # Scopo: Lista paginata mapping BA per un emittente, con search su
    #        ragione_sociale_completa, codice BA e id_fiscale_univoco_cf_piva.
    def list_by_emittente(
        self,
        emittente_soggetto_ruolo_id: int,
        *,
        search: str | None = None,
        limit: int = 25,
        offset: int = 0,
        order_by: str = "billing_account_codice",
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in self._ORDER_COLS else "billing_account_codice"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT m.id,
                   m.billing_account_id,
                   m.is_default,
                   ba.codice                   AS billing_account_codice,
                   s.ragione_sociale_completa   AS billing_account_ragione_sociale,
                   s.id_fiscale_univoco_cf_piva AS id_fiscale_univoco,
                   m.data_insert,
                   m.data_update,
                   COUNT(*) OVER ()            AS total_count
              FROM anagrafiche.emittenti_fiscali_billing_account m
              LEFT JOIN anagrafiche.billing_account ba ON ba.id = m.billing_account_id
              LEFT JOIN anagrafiche.soggetti_ruoli sr  ON sr.id = ba.soggetto_ruolo_id
              LEFT JOIN anagrafiche.soggetti s         ON s.id  = sr.soggetto_id
             WHERE m.emittente_soggetto_ruolo_id = %s
               AND (%s::text IS NULL OR (
                       ba.codice ILIKE %s
                    OR s.ragione_sociale_completa ILIKE %s
                    OR s.id_fiscale_univoco_cf_piva ILIKE %s
                   ))
             ORDER BY m.is_default DESC, {order_col} {direction} NULLS LAST, m.id
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params: list[Any] = [
            emittente_soggetto_ruolo_id,
            search_pattern, search_pattern, search_pattern, search_pattern,
            limit, offset,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return extract_paginated(cursor)

    # Scopo: Inserisce un mapping BA per l'emittente.
    #        Se billing_account_id e' None, crea il default globale (is_default=true).
    #        Il CHECK constraint chk_emittenti_fiscali_ba_default garantisce coerenza.
    def create_mapping(
        self,
        emittente_soggetto_ruolo_id: int,
        billing_account_id: int | None,
    ) -> int:
        is_default = billing_account_id is None
        sql = """
            INSERT INTO anagrafiche.emittenti_fiscali_billing_account
                   (emittente_soggetto_ruolo_id, billing_account_id, is_default)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [emittente_soggetto_ruolo_id, billing_account_id, is_default])
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Elimina un mapping per id.
    #        I trigger DB (default_guard) impediscono di rimuovere il default se necessario.
    def delete_mapping(self, mapping_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM anagrafiche.emittenti_fiscali_billing_account WHERE id = %s",
                [mapping_id],
            )
            return cursor.rowcount > 0

    # Scopo: Verifica che un mapping appartenga all'emittente atteso (sicurezza sub-resource).
    def belongs_to_emittente(self, mapping_id: int, emittente_soggetto_ruolo_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM anagrafiche.emittenti_fiscali_billing_account
                 WHERE id = %s AND emittente_soggetto_ruolo_id = %s
                """,
                [mapping_id, emittente_soggetto_ruolo_id],
            )
            return cursor.fetchone() is not None

    # Scopo: Riepilogo dei mapping per un emittente, indipendente da paginazione/search.
    #        Usato dal FE per disabilitare il pulsante "default" senza dipendere dalla
    #        pagina corrente: vedi analisi-refactor.frontend-amm-software (A8/C3).
    def summary_by_emittente(
        self,
        emittente_soggetto_ruolo_id: int,
    ) -> dict[str, Any]:
        sql = """
            SELECT
                COUNT(*) FILTER (WHERE is_default)              AS default_count,
                COUNT(*) FILTER (WHERE NOT is_default)          AS specifici_count
              FROM anagrafiche.emittenti_fiscali_billing_account
             WHERE emittente_soggetto_ruolo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [emittente_soggetto_ruolo_id])
            row = cursor.fetchone()
            assert row is not None
            return {
                "has_default": bool(row[0]),
                "count_specifici": int(row[1]),
            }


# =================================================================
# Sotto-tabella: emittenti_fiscali_utilities (parametri per emittente+utility)
# =================================================================


_UTILITIES_UPDATE_ALLOWED = {
    "minimo_soglia_min",
    "minimo_soglia_max",
    "arrotondamento_importi_dec",
    "metodo_arrotondamento_importi",
    "attivo",
}
_UTILITIES_UPDATE_NULLABLE = {
    "minimo_soglia_min",
    "minimo_soglia_max",
}

# Identificatori della tabella override per il pattern slot/override.
# Costanti modulo: usate sia da list_by_emittente (delega a LookupRepository) sia
# implicitamente registrate nella whitelist di LookupRepository._ALLOWED_UTILITY_OVERRIDES.
# Allinearle se la tabella o la colonna FK cambia nome.
_UTILITIES_OVERRIDES_TABLE = "anagrafiche.emittenti_fiscali_utilities"
_UTILITIES_OVERRIDES_FK_COLUMN = "emittente_soggetto_ruolo_id"


class EmittentiFiscaliUtilitiesRepository:
    """Accesso DB per la matrice emittente_fiscale x utility (parametri fatturazione).

    Vincoli:
      - UNIQUE (emittente_soggetto_ruolo_id, utility_id)
      - Trigger child_requires_active_parent: emittente padre deve essere attivo
      - Trigger guard_utility_tipo_ruolo: la utility deve essere ammessa per il ruolo EF
        (vedi config.utilities_tipi_ruolo, fail-open se la utility non ha matrice)
    """

    # Scopo: Matrice utility ammesse per ruolo EF + override specifici dell'emittente.
    #        Delega al metodo generico LookupRepository.list_entity_utility_matrix
    #        (pattern slot/override). Ritorna SEMPRE tutte le utility ammesse: per
    #        quelle non personalizzate, i campi override sono NULL e record_id e' NULL.
    def list_by_emittente(self, emittente_soggetto_ruolo_id: int) -> list[dict[str, Any]]:
        from apps.core.db.lookup_repository import LookupRepository
        return LookupRepository().list_entity_utility_matrix(
            entity_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
            tipo_ruolo_codice="EF",
            overrides_table=_UTILITIES_OVERRIDES_TABLE,
            overrides_fk_column=_UTILITIES_OVERRIDES_FK_COLUMN,
        )

    # Scopo: Inserisce un record utility per l'emittente.
    #        Tutti i campi NOT NULL devono essere forniti (arrotondamento_dec, metodo).
    def create_record(
        self,
        *,
        emittente_soggetto_ruolo_id: int,
        utility_id: int,
        arrotondamento_importi_dec: int,
        metodo_arrotondamento_importi: str,
        minimo_soglia_min: Any = None,
        minimo_soglia_max: Any = None,
        attivo: bool | None = None,
    ) -> int:
        cols = [
            "emittente_soggetto_ruolo_id",
            "utility_id",
            "arrotondamento_importi_dec",
            "metodo_arrotondamento_importi",
        ]
        vals: list[Any] = [
            emittente_soggetto_ruolo_id,
            utility_id,
            arrotondamento_importi_dec,
            metodo_arrotondamento_importi,
        ]
        if minimo_soglia_min is not None:
            cols.append("minimo_soglia_min")
            vals.append(minimo_soglia_min)
        if minimo_soglia_max is not None:
            cols.append("minimo_soglia_max")
            vals.append(minimo_soglia_max)
        if attivo is not None:
            cols.append("attivo")
            vals.append(attivo)
        placeholders = ["%s"] * len(cols)
        sql = f"""
            INSERT INTO anagrafiche.emittenti_fiscali_utilities ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Aggiorna campi editabili (delta update). utility_id e' immutabile (PK logica).
    def update_record(self, record_id: int, data: dict[str, Any]) -> bool:
        clean = dict(data)
        for k in _UTILITIES_UPDATE_NULLABLE:
            if k in clean and isinstance(clean[k], str) and not clean[k].strip():
                clean[k] = None
        fields = [(k, v) for k, v in clean.items() if k in _UTILITIES_UPDATE_ALLOWED]
        if not fields:
            return False
        set_clause = ", ".join(f"{f[0]} = %s" for f in fields)
        values: list[Any] = [f[1] for f in fields]
        values.append(record_id)
        sql = f"UPDATE anagrafiche.emittenti_fiscali_utilities SET {set_clause} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    # Scopo: Elimina un record utility per id.
    def delete_record(self, record_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM anagrafiche.emittenti_fiscali_utilities WHERE id = %s",
                [record_id],
            )
            return cursor.rowcount > 0

    # Scopo: Verifica appartenenza del record all'emittente atteso (sicurezza sub-resource).
    def belongs_to_emittente(self, record_id: int, emittente_soggetto_ruolo_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM anagrafiche.emittenti_fiscali_utilities
                 WHERE id = %s AND emittente_soggetto_ruolo_id = %s
                """,
                [record_id, emittente_soggetto_ruolo_id],
            )
            return cursor.fetchone() is not None


