# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per gestione soggetti (PF/PG/ENTE).
#        CRUD soggetti, contatti, indirizzi soggetto, ruoli.
#        Accesso DB-first via cursor e funzioni PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from apps.core.db._helpers import row_to_dict, rows_to_list
from apps.core.db.parameter_repository import ParameterRepository

from django.db import connection

from apps.anagrafiche.db._helpers import extract_paginated

_SOGGETTI_ORDER_COLS = {
    "codice", "ragione_sociale_completa", "codice_fiscale", "partita_iva",
    "tipo_descrizione", "date_insert",
}

# Lunghezza minima della search bar soggetti (resolver). Esposto via
# config-resolver al frontend per evitare cablato duplicato. Costante
# applicativa: se serve parametrizzazione per emittente, promuovere a
# config.parameters (chiave es. MIN_SEARCH_LENGTH_SOGGETTI).
MIN_SEARCH_LENGTH_SOGGETTI = 3


class SoggettiRepository:
    """Accesso DB per soggetti, contatti, indirizzi soggetto, ruoli."""

    # =================================================================
    # Lista e dettaglio soggetti
    # =================================================================

    # Scopo: Lista paginata soggetti con search su ragione_sociale_completa,
    #        codice_fiscale, partita_iva. Filtro per tipo_soggetto_dettaglio_id.
    def list_soggetti(
        self, *, search: str | None = None,
        tipo_soggetto_dettaglio_id: int | None = None,
        emittente_ids: list[int] | None = None,
        limit: int = 25, offset: int = 0,
        order_by: str = "ragione_sociale_completa", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in _SOGGETTI_ORDER_COLS else "ragione_sociale_completa"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT s.id, s.codice, s.ragione_sociale_completa, s.codice_fiscale,
                   s.partita_iva, s.cognome, s.nome, s.ragione_sociale,
                   tsd.descrizione AS tipo_descrizione,
                   tsd.id AS tipo_soggetto_dettaglio_id,
                   ts.id AS natura_soggetto,
                   (SELECT COALESCE(jsonb_agg(jsonb_build_object(
                       'soggetto_ruolo_id', sr.id,
                       'codice', COALESCE(tr.codice_interno, tr.codice),
                       'descrizione', tr.descrizione
                   ) ORDER BY tr.descrizione), '[]'::jsonb)
                    FROM anagrafiche.soggetti_ruoli sr
                    JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
                   WHERE sr.soggetto_id = s.id
                     AND (
                       -- Nessun filtro emittente: mostra tutti i ruoli
                       %s::bigint[] IS NULL
                       -- Ruoli non-CL: sempre visibili
                       OR COALESCE(tr.codice_interno, tr.codice) != 'CL'
                       -- Ruolo CL: visibile solo se almeno un cliente
                       -- del soggetto e' nello scope emittente dell'operatore
                       OR EXISTS (
                           SELECT 1
                             FROM anagrafiche.clienti cl
                             JOIN anagrafiche.billing_account ba
                               ON ba.id = cl.billing_account_id
                            WHERE cl.soggetto_ruolo_id = sr.id
                              AND (
                                    -- Mapping specifico
                                    EXISTS (
                                        SELECT 1
                                          FROM anagrafiche.emittenti_fiscali_billing_account efba
                                         WHERE efba.emittente_soggetto_ruolo_id = ANY(%s::bigint[])
                                           AND efba.billing_account_id = ba.id
                                    )
                                 OR (
                                      -- Fallback default, solo BA senza mapping specifico
                                      EXISTS (
                                          SELECT 1
                                            FROM anagrafiche.emittenti_fiscali_billing_account efba
                                           WHERE efba.emittente_soggetto_ruolo_id = ANY(%s::bigint[])
                                             AND efba.is_default = true
                                      )
                                      AND NOT EXISTS (
                                          SELECT 1
                                            FROM anagrafiche.emittenti_fiscali_billing_account efba2
                                           WHERE efba2.billing_account_id = ba.id
                                      )
                                    )
                                  )
                       )
                     )
                   ) AS ruoli,
                   COUNT(*) OVER () AS total_count
              FROM anagrafiche.soggetti s
              JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
              JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
             WHERE (%s::text IS NULL OR (
                       s.ragione_sociale_completa ILIKE %s
                    OR s.codice_fiscale ILIKE %s
                    OR s.partita_iva ILIKE %s
                   ))
               AND (%s::bigint IS NULL OR s.tipo_soggetto_dettaglio_id = %s)
             ORDER BY {order_col} {direction}, s.id
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params = [
            emittente_ids, emittente_ids, emittente_ids,
            search_pattern, search_pattern, search_pattern, search_pattern,
            tipo_soggetto_dettaglio_id, tipo_soggetto_dettaglio_id,
            limit, offset,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            results, total_count = extract_paginated(cursor)
        # Normalizza ruoli (jsonb_agg): psycopg in alcune configurazioni
        # ritorna jsonb come stringa anziche' lista. Garantiamo sempre list.
        for r in results:
            ruoli = r.get("ruoli")
            if isinstance(ruoli, str):
                try:
                    r["ruoli"] = json.loads(ruoli)
                except (ValueError, TypeError):
                    r["ruoli"] = []
            elif ruoli is None:
                r["ruoli"] = []
        return results, total_count

    # Scopo: Recupera il codice catastale (Belfiore) di un comune da extra_country.
    def get_codice_catastale(self, comune_id: int) -> str | None:
        sql = """
            SELECT extra_country->>'codice_catastale'
              FROM config.comuni
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [comune_id])
            row = cursor.fetchone()
            return str(row[0]) if row and row[0] else None

    # Scopo: Verifica esistenza soggetto (query leggera, SELECT 1).
    def exists_soggetto(self, soggetto_id: str) -> bool:
        sql = "SELECT 1 FROM anagrafiche.soggetti WHERE id = %s::uuid"
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return cursor.fetchone() is not None

    # Scopo: Risolve la natura (PF/PG/ENC) dal tipo_soggetto_dettaglio_id.
    def get_natura_by_tipo_id(self, tipo_id: int) -> str | None:
        sql = """
            SELECT ts.id
              FROM config.tipi_soggetto_dettaglio tsd
              JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
             WHERE tsd.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_id])
            row = cursor.fetchone()
            return str(row[0]) if row and row[0] else None

    # Scopo: Dettaglio completo soggetto con tipo, natura e comune nascita.
    def get_soggetto(self, soggetto_id: str) -> dict[str, Any] | None:
        sql = """
            SELECT s.id, s.ragione_sociale_completa, s.codice_fiscale,
                   s.partita_iva, s.cognome, s.nome, s.ragione_sociale,
                   s.sesso, s.data_nascita::text, s.comune_id AS comune_nascita_id,
                   c.descrizione AS comune_nascita_descrizione,
                   p.sigla AS comune_nascita_provincia_sigla,
                   tsd.id AS tipo_soggetto_dettaglio_id,
                   tsd.descrizione AS tipo_descrizione,
                   ts.id AS natura_soggetto
              FROM anagrafiche.soggetti s
              JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
              JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
              LEFT JOIN config.comuni c ON c.id = s.comune_id
              LEFT JOIN config.province p ON p.id = c.provincia_id
             WHERE s.id = %s::uuid
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return row_to_dict(cursor)

    # =================================================================
    # Creazione soggetti
    # =================================================================

    # Scopo: Crea soggetto PF chiamando la funzione DB building block.
    #        Obiettivo: INSERT soggetto + contatto default, tutto in funzione PG.
    def crea_soggetto_pf(
        self, *, cognome: str, nome: str, codice_fiscale: str, email: str,
        data_nascita: str | None = None, sesso: str = "M",
        stato_iso2: str = "IT",
        comune_nascita_id: int | None = None,
        tipo_contatto_id: int | None = None,
    ) -> str:
        sql = """
            SELECT anagrafiche.fn_crea_soggetto_pf(
                p_cognome           := %s,
                p_nome              := %s,
                p_codice_fiscale    := %s,
                p_email             := %s,
                p_data_nascita      := %s::date,
                p_sesso             := %s,
                p_stato_iso2        := %s,
                p_comune_nascita_id := %s,
                p_tipo_contatto_id  := %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                cognome, nome, codice_fiscale, email,
                data_nascita, sesso, stato_iso2, comune_nascita_id, tipo_contatto_id,
            ])
            row = cursor.fetchone()
            assert row is not None
            return str(row[0])

    # Scopo: Crea soggetto PG chiamando la funzione DB building block.
    #        Obiettivo: INSERT soggetto + contatto default + dati societari
    #        (se policy REQUIRED o dati forniti). Non crea indirizzi ne' ruoli.
    def crea_soggetto_pg(
        self, *, ragione_sociale: str, tipo_soggetto_dettaglio_id: int,
        email: str, codice_fiscale: str | None = None,
        partita_iva: str | None = None, stato_iso2: str = "IT",
        forma_giuridica_id: int | None = None,
        id_prov_iscri_rea: int | None = None,
        iscrizione_rea: str | None = None,
        capitale_sociale: float | None = None,
        socio_unico: str = "SU", liquidazione: str = "LN",
        destinatario_fe: str | None = None,
        pec_fatturazione: str | None = None,
        codice_sdi: str | None = None,
        tipo_contatto_id: int | None = None,
    ) -> str:
        sql = """
            SELECT anagrafiche.fn_crea_soggetto_pg(
                p_ragione_sociale            := %s,
                p_tipo_soggetto_dettaglio_id := %s,
                p_email                      := %s,
                p_codice_fiscale             := %s,
                p_partita_iva                := %s,
                p_stato_iso2                 := %s,
                p_forma_giuridica_id         := %s,
                p_id_prov_iscri_rea          := %s,
                p_iscrizione_rea             := %s,
                p_capitale_sociale           := %s,
                p_socio_unico                := %s::anagrafiche.socio_unico_enum,
                p_liquidazione               := %s::anagrafiche.liquidazione_enum,
                p_destinatario_fe            := %s,
                p_pec_fatturazione           := %s,
                p_codice_sdi                 := %s,
                p_tipo_contatto_id           := %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                ragione_sociale, tipo_soggetto_dettaglio_id, email,
                codice_fiscale, partita_iva, stato_iso2,
                forma_giuridica_id, id_prov_iscri_rea, iscrizione_rea,
                capitale_sociale, socio_unico, liquidazione,
                destinatario_fe, pec_fatturazione, codice_sdi,
                tipo_contatto_id,
            ])
            row = cursor.fetchone()
            assert row is not None
            return str(row[0])

    # =================================================================
    # Aggiornamento soggetti
    # =================================================================

    # Scopo: Aggiorna campi modificabili di un soggetto.
    # Normalizza stringhe vuote a NULL per evitare conflitti con trigger
    # che controllano IS NOT NULL (es. partita_iva, codice_fiscale).
    def update_soggetto(self, soggetto_id: str, data: dict[str, Any]) -> bool:
        _ALLOWED = {
            "cognome", "nome", "ragione_sociale", "codice_fiscale",
            "partita_iva", "sesso", "data_nascita", "comune_id",
        }
        # Campi dove stringa vuota deve diventare NULL
        _NULLABLE = {"codice_fiscale", "partita_iva", "data_nascita", "comune_id"}
        # Mapping alias frontend → colonna DB
        _ALIAS = {"comune_nascita_id": "comune_id"}
        mapped = {_ALIAS.get(k, k): v for k, v in data.items()}
        # Normalizza stringhe vuote a None per campi nullable
        for k in _NULLABLE:
            if k in mapped and mapped[k] is not None:
                val = mapped[k]
                if isinstance(val, str) and not val.strip():
                    mapped[k] = None
        fields = [(k, v) for k, v in mapped.items() if k in _ALLOWED]
        if not fields:
            return False
        set_clause = ", ".join([f"{f[0]} = %s" for f in fields])
        values = [f[1] for f in fields]
        values.append(soggetto_id)
        sql = f"UPDATE anagrafiche.soggetti SET {set_clause} WHERE id = %s::uuid"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    # =================================================================
    # Contatti
    # =================================================================

    # Scopo: Lista contatti di un soggetto.
    def get_soggetto_contatti(self, soggetto_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT c.id, c.nominativo, c.email, c.telefono, c.cellulare,
                   c.pec, c.note, c.tipo_contatto_id,
                   tc.descrizione AS tipo_contatto_descrizione,
                   c.unita_organizzativa_id
              FROM anagrafiche.contatti c
              LEFT JOIN config.tipi_contatti tc ON tc.id = c.tipo_contatto_id
             WHERE c.soggetto_id = %s::uuid
             ORDER BY c.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return rows_to_list(cursor)

    # Scopo: Crea contatto per un soggetto. Se soggetto_ruolo_id fornito, il contatto
    #        e' specifico del ruolo; altrimenti e' a livello soggetto (fallback).
    def crea_contatto(
        self, soggetto_id: str, *, nominativo: str, email: str | None = None,
        telefono: str | None = None, cellulare: str | None = None,
        pec: str | None = None, tipo_contatto_id: int | None = None,
        unita_organizzativa_id: int | None = None, note: str | None = None,
        soggetto_ruolo_id: int | None = None, istanza_utility_id: int | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO anagrafiche.contatti
                (soggetto_id, soggetto_ruolo_id, istanza_utility_id, nominativo, email,
                 telefono, cellulare, pec, tipo_contatto_id, unita_organizzativa_id, note)
            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, nominativo, email, telefono, cellulare, pec,
                      tipo_contatto_id, unita_organizzativa_id, note,
                      soggetto_ruolo_id, istanza_utility_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                soggetto_id, soggetto_ruolo_id, istanza_utility_id, nominativo, email,
                telefono, cellulare, pec, tipo_contatto_id, unita_organizzativa_id, note,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna un contatto esistente con verifica ownership soggetto o ruolo.
    def update_contatto(self, contatto_id: int, data: dict[str, Any],
                        soggetto_id: str | None = None,
                        soggetto_ruolo_id: int | None = None) -> bool:
        _ALLOWED = {
            "nominativo", "email", "telefono", "cellulare", "pec",
            "tipo_contatto_id", "unita_organizzativa_id", "note",
        }
        fields = [(k, v) for k, v in data.items() if k in _ALLOWED]
        if not fields:
            return False
        set_clause = ", ".join([f"{f[0]} = %s" for f in fields])
        values = [f[1] for f in fields]
        values.append(contatto_id)
        where = "WHERE id = %s"
        if soggetto_id is not None:
            where += " AND soggetto_id = %s::uuid"
            values.append(soggetto_id)
        if soggetto_ruolo_id is not None:
            where += " AND soggetto_ruolo_id = %s"
            values.append(soggetto_ruolo_id)
        sql = f"UPDATE anagrafiche.contatti SET {set_clause} {where}"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    # Scopo: Elimina contatto con ownership check.
    def delete_contatto(self, contatto_id: int, soggetto_id: str) -> bool:
        sql = """
            DELETE FROM anagrafiche.contatti
             WHERE id = %s AND soggetto_id = %s::uuid
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [contatto_id, soggetto_id])
            return cursor.rowcount > 0

    # =================================================================
    # Indirizzi soggetto
    # =================================================================

    # Scopo: Lista indirizzi layer soggetto con dettaglio geografico per UI.
    def get_soggetto_indirizzi(self, soggetto_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT isog.id, isog.tipo_indirizzo_id,
                   ti.descrizione AS tipo_indirizzo_descrizione,
                   ti.codice_interno AS tipo_indirizzo_codice,
                   isog.indirizzo_dettaglio_id,
                   isog.indirizzo_libero,
                   isog.stato_id, isog.comune_id,
                   COALESCE(isog.indirizzo_libero,
                            idet.indirizzo_normalizzato) AS indirizzo_display,
                   idet.stradario_id,
                   idet.civico,
                   idet.estensione_civico,
                   idet.palazzina,
                   idet.scala,
                   idet.piano,
                   idet.interno,
                   idet.via_norm AS stradario_display,
                   s.comune_id AS det_comune_id,
                   c.descrizione AS descrizione_comune
              FROM anagrafiche.indirizzi_soggetti isog
              JOIN config.tipi_indirizzi ti ON ti.id = isog.tipo_indirizzo_id
              LEFT JOIN anagrafiche.indirizzi_dettaglio idet
                ON idet.id = isog.indirizzo_dettaglio_id
              LEFT JOIN config.stradario s
                ON s.id = idet.stradario_id
              LEFT JOIN config.comuni c
                ON c.id = s.comune_id
             WHERE isog.soggetto_id = %s::uuid
             ORDER BY ti.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return rows_to_list(cursor)

    # Scopo: Crea indirizzo soggetto chiamando la funzione DB.
    #        Supporta modalita' normalizzata (indirizzo_dettaglio_id)
    #        e modalita' libera (indirizzo_libero + stato_id).
    def crea_indirizzo_soggetto(
        self, soggetto_id: str, *,
        tipo_indirizzo_codice: str,
        indirizzo_dettaglio_id: int | None = None,
        indirizzo_libero: str | None = None,
        stato_id: int | None = None,
        comune_id: int | None = None,
        codice_postale_id: int | None = None,
    ) -> int:
        sql = """
            SELECT anagrafiche.fn_crea_indirizzo_soggetto(
                p_soggetto_id            := %s::uuid,
                p_tipo_indirizzo_codice  := %s,
                p_indirizzo_dettaglio_id := %s,
                p_indirizzo_libero       := %s,
                p_stato_id               := %s,
                p_comune_id              := %s,
                p_codice_postale_id      := %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                soggetto_id, tipo_indirizzo_codice,
                indirizzo_dettaglio_id, indirizzo_libero,
                stato_id, comune_id, codice_postale_id,
            ])
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Elimina un'associazione indirizzo-soggetto per id.
    def delete_indirizzo_soggetto(self, indirizzo_soggetto_id: int, soggetto_id: str) -> bool:
        sql = """
            DELETE FROM anagrafiche.indirizzi_soggetti
             WHERE id = %s AND soggetto_id = %s::uuid
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [indirizzo_soggetto_id, soggetto_id])
            return cursor.rowcount > 0

    # =================================================================
    # Indirizzi ruolo (anagrafiche.indirizzi — con istanza_utility_id)
    # =================================================================

    # Scopo: Restituisce i tipo_indirizzo_id gia' presenti per un soggetto_ruolo.
    #        Usato per evitare INSERT duplicati quando il ruolo esiste gia'.
    def get_existing_tipo_indirizzo_ids(self, soggetto_ruolo_id: int) -> set[int]:
        sql = """
            SELECT tipo_indirizzo_id
              FROM anagrafiche.indirizzi
             WHERE soggetto_ruolo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_ruolo_id])
            return {row[0] for row in cursor.fetchall()}

    # Campi ammessi per update indirizzi ruolo.
    _IND_RUOLO_ALLOWED = {
        "tipo_indirizzo_id", "istanza_utility_id", "indirizzo_dettaglio_id",
        "indirizzo_libero", "stato_id", "comune_id", "codice_postale_id",
        "administrative_area", "locality", "sublocality", "postal_box",
    }
    _IND_RUOLO_NULLABLE = {
        "istanza_utility_id", "indirizzo_dettaglio_id", "indirizzo_libero",
        "stato_id", "comune_id", "codice_postale_id",
        "administrative_area", "locality", "sublocality", "postal_box",
    }

    # Scopo: Crea indirizzo a livello ruolo.
    #        Supporta modalita' normalizzata (indirizzo_dettaglio_id)
    #        e libera (indirizzo_libero + stato_id).
    #        Il trigger guard valida tipo_indirizzo_id vs matrice ammessi.
    def crea_indirizzo_ruolo(
        self, soggetto_ruolo_id: int, *,
        tipo_indirizzo_id: int,
        istanza_utility_id: int | None = None,
        indirizzo_dettaglio_id: int | None = None,
        indirizzo_libero: str | None = None,
        stato_id: int | None = None,
        comune_id: int | None = None,
        codice_postale_id: int | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO anagrafiche.indirizzi
                (soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
                 indirizzo_dettaglio_id, indirizzo_libero,
                 stato_id, comune_id, codice_postale_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
                      indirizzo_dettaglio_id, indirizzo_libero,
                      stato_id, comune_id, codice_postale_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
                indirizzo_dettaglio_id, indirizzo_libero,
                stato_id, comune_id, codice_postale_id,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna indirizzo ruolo con ownership check su soggetto_ruolo_id.
    def update_indirizzo_ruolo(
        self, indirizzo_id: int, soggetto_ruolo_id: int,
        data: dict[str, Any],
    ) -> bool:
        # Normalizza stringhe vuote a None per campi nullable
        for k in self._IND_RUOLO_NULLABLE:
            if k in data and isinstance(data[k], str) and not data[k].strip():
                data[k] = None
        fields = [(k, v) for k, v in data.items() if k in self._IND_RUOLO_ALLOWED]
        if not fields:
            return False
        set_clause = ", ".join(f"{f[0]} = %s" for f in fields)
        values: list[Any] = [f[1] for f in fields]
        values.extend([indirizzo_id, soggetto_ruolo_id])
        sql = (
            f"UPDATE anagrafiche.indirizzi SET {set_clause} "  # noqa: S608
            "WHERE id = %s AND soggetto_ruolo_id = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    # Scopo: Elimina indirizzo ruolo con ownership check su soggetto_ruolo_id.
    def delete_indirizzo_ruolo(
        self, indirizzo_id: int, soggetto_ruolo_id: int,
    ) -> bool:
        sql = """
            DELETE FROM anagrafiche.indirizzi
             WHERE id = %s AND soggetto_ruolo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [indirizzo_id, soggetto_ruolo_id])
            return cursor.rowcount > 0

    # Scopo: Risolve tipo_indirizzo codice → id. Usa COALESCE(codice_interno, codice) per match.
    def resolve_tipo_indirizzo_id(self, codice: str) -> int | None:
        sql = "SELECT id FROM config.tipi_indirizzi WHERE COALESCE(codice_interno, codice) = %s LIMIT 1"
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice])
            row = cursor.fetchone()
            return row[0] if row else None

    # =================================================================
    # Ruoli
    # =================================================================

    # Scopo: Lista ruoli assegnati a un soggetto, con filtro scope emittente
    #        sul ruolo CL (stessa logica a 3 livelli di list_soggetti).
    def get_soggetto_ruoli(
        self, soggetto_id: str, emittente_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT sr.id, sr.tipo_ruolo_id,
                   COALESCE(tr.codice_interno, tr.codice) AS ruolo_codice,
                   tr.descrizione AS ruolo_descrizione
              FROM anagrafiche.soggetti_ruoli sr
              JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
             WHERE sr.soggetto_id = %s::uuid
               AND (
                 %s::bigint[] IS NULL
                 OR COALESCE(tr.codice_interno, tr.codice) != 'CL'
                 OR EXISTS (
                     SELECT 1
                       FROM anagrafiche.clienti cl
                       JOIN anagrafiche.billing_account ba
                         ON ba.id = cl.billing_account_id
                      WHERE cl.soggetto_ruolo_id = sr.id
                        AND (
                              EXISTS (
                                  SELECT 1
                                    FROM anagrafiche.emittenti_fiscali_billing_account efba
                                   WHERE efba.emittente_soggetto_ruolo_id = ANY(%s::bigint[])
                                     AND efba.billing_account_id = ba.id
                              )
                           OR (
                                EXISTS (
                                    SELECT 1
                                      FROM anagrafiche.emittenti_fiscali_billing_account efba
                                     WHERE efba.emittente_soggetto_ruolo_id = ANY(%s::bigint[])
                                       AND efba.is_default = true
                                )
                                AND NOT EXISTS (
                                    SELECT 1
                                      FROM anagrafiche.emittenti_fiscali_billing_account efba2
                                     WHERE efba2.billing_account_id = ba.id
                                )
                              )
                            )
                 )
               )
             ORDER BY tr.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id, emittente_ids, emittente_ids, emittente_ids])
            return rows_to_list(cursor)

    # Scopo: Verifica se un CF esiste gia' in anagrafica. Ritorna soggetto trovato o None.
    def find_by_codice_fiscale(self, codice_fiscale: str) -> dict[str, Any] | None:
        sql = """
            SELECT s.id, s.codice, s.ragione_sociale_completa, s.codice_fiscale
              FROM anagrafiche.soggetti s
             WHERE UPPER(TRIM(s.codice_fiscale)) = UPPER(TRIM(%s))
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice_fiscale])
            return row_to_dict(cursor)

    # Scopo: Verifica se una P.IVA esiste gia' in anagrafica. Ritorna soggetto trovato o None.
    def find_by_partita_iva(self, partita_iva: str) -> dict[str, Any] | None:
        sql = """
            SELECT s.id, s.codice, s.ragione_sociale_completa, s.partita_iva
              FROM anagrafiche.soggetti s
             WHERE UPPER(TRIM(s.partita_iva)) = UPPER(TRIM(%s))
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [partita_iva])
            return row_to_dict(cursor)

    # Scopo: Assegna ruolo a soggetto (get or create, idempotente).
    # codice_ruolo puo' essere il campo `codice` o `codice_interno` di config.tipi_ruoli.
    # La funzione DB accetta codice_interno: risolviamo con un sub-select.
    def assign_ruolo(self, soggetto_id: str, codice_ruolo: str) -> int:
        sql = """
            SELECT script.fn_get_or_create_soggetto_ruolo(
                %s::uuid,
                COALESCE(
                    (SELECT codice_interno FROM config.tipi_ruoli
                     WHERE codice = %s OR codice_interno = %s LIMIT 1),
                    %s
                )
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id, codice_ruolo, codice_ruolo, codice_ruolo])
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # =================================================================
    # Dati societari
    # =================================================================

    # =================================================================
    # Config resolver per tipo ruolo
    # =================================================================

    # Scopo: Dato un codice tipo_ruolo, restituisce le nature ammesse,
    # i tipi_soggetto_dettaglio con i requisiti CF/PIVA, il default
    # tipo_soggetto_dettaglio (da config.parameters) e min_search_length.
    # Usato dal SoggettoResolver frontend per adattare form e ricerca.
    # emittente_fiscale_id: se valorizzato, usato per risolvere override
    # del default sul livello emittente (catena fn_get_parameter_full).
    def get_config_resolver(
        self, tipo_ruolo_codice: str,
        emittente_fiscale_id: int | None = None,
    ) -> dict[str, Any] | None:
        # 1. Recupera tipo_ruolo
        sql_ruolo = """
            SELECT tr.id, COALESCE(tr.codice_interno, tr.codice) AS codice, tr.descrizione
              FROM config.tipi_ruoli tr
             WHERE COALESCE(tr.codice_interno, tr.codice) = %s
        """
        # 2. Nature ammesse per il ruolo (dalla matrice config)
        sql_nature = """
            SELECT ts.id AS tipo_soggetto_id,
                   ts.descrizione AS tipo_soggetto_descrizione,
                   ts.natura_soggetto
              FROM config.tipi_ruoli_nature_ammesse trna
              JOIN config.tipi_soggetto ts ON ts.id = trna.tipo_soggetto_id
             WHERE trna.tipo_ruolo_id = %s
               AND trna.attivo = true
               AND (trna.valido_dal IS NULL OR trna.valido_dal <= CURRENT_DATE)
               AND (trna.valido_al IS NULL OR trna.valido_al >= CURRENT_DATE)
        """
        # 3. Tipi soggetto dettaglio filtrati per nature ammesse
        sql_dettaglio = """
            SELECT tsd.id, tsd.codice_interno, tsd.descrizione,
                   ts.id AS tipo_soggetto_id,
                   ts.natura_soggetto,
                   tsd.cf_obbligatorio, tsd.piva_obbligatoria,
                   tsd.formato_cf, tsd.formato_piva,
                   tsd.dati_societari_policy
              FROM config.tipi_soggetto_dettaglio tsd
              JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
             WHERE (%s::bigint[] IS NULL OR ts.id = ANY(%s))
             ORDER BY tsd.codice_interno
        """
        with connection.cursor() as cursor:
            cursor.execute(sql_ruolo, [tipo_ruolo_codice])
            ruolo = row_to_dict(cursor)
            if not ruolo:
                return None

            cursor.execute(sql_nature, [ruolo["id"]])
            nature = rows_to_list(cursor)

            # Se nessuna natura configurata, il ruolo accetta tutte le nature (NULL = nessun filtro)
            nature_ids = [n["tipo_soggetto_id"] for n in nature] if nature else None

            cursor.execute(sql_dettaglio, [nature_ids, nature_ids])
            dettagli = rows_to_list(cursor)

        # 4. Default tipo_soggetto_dettaglio per ruolo (codice_interno via
        # config.parameters, override gratuito per emittente). Usiamo
        # ruolo["codice"] (validato dal DB) per costruire la chiave: evita
        # di propagare l'input utente raw nella stringa parametro.
        # Delega a ParameterRepository per coerenza con la firma di
        # script.fn_get_parameter_full.
        param_code = f"DEFAULT_TIPO_SOGGETTO_DETTAGLIO_{ruolo['codice']}"
        default_codice = ParameterRepository().get_parameter(
            param_code, emittente_fiscale_id=emittente_fiscale_id,
        )

        # Risolvi id dal codice_interno matchando i dettagli gia' caricati
        # (no extra query). Se il codice non e' tra i dettagli ammessi per
        # questo ruolo (config errata o cambio nature), default a None.
        default_id = next(
            (d["id"] for d in dettagli if d.get("codice_interno") == default_codice),
            None,
        ) if default_codice else None

        return {
            "tipo_ruolo": ruolo["codice"],
            "tipo_ruolo_descrizione": ruolo["descrizione"],
            "nature_ammesse": [n["natura_soggetto"] for n in nature] if nature else ["PF", "PG", "ENTE"],
            "tipi_soggetto_dettaglio": dettagli,
            "default_tipo_soggetto_dettaglio_id": default_id,
            "min_search_length": MIN_SEARCH_LENGTH_SOGGETTI,
        }

    # Scopo: Recupera dati societari del soggetto (se esistono).
    def get_dati_societari(self, soggetto_id: str) -> dict[str, Any] | None:
        sql = """
            SELECT ds.id, ds.forma_giuridica_id,
                   fg.descrizione AS forma_giuridica_descrizione,
                   fg.codice AS forma_giuridica_codice,
                   fg.rea_policy, fg.capitale_sociale_policy,
                   ds.id_prov_iscri_rea, ds.iscrizione_rea,
                   ds.capitale_sociale,
                   ds.socio_unico, ds.liquidazione,
                   ds.destinatario_fe, ds.pec_fatturazione, ds.codice_sdi
              FROM anagrafiche.dati_societari ds
              LEFT JOIN config.forme_giuridiche fg ON fg.id = ds.forma_giuridica_id
             WHERE ds.soggetto_id = %s::uuid
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return row_to_dict(cursor)
