# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per gestione soggetti (PF/PG/ENTE).
#        CRUD soggetti, contatti, indirizzi soggetto, ruoli.
#        Accesso DB-first via cursor e funzioni PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.anagrafiche.db._helpers import extract_paginated

_SOGGETTI_ORDER_COLS = {
    "ragione_sociale_completa", "codice_fiscale", "partita_iva",
    "tipo_descrizione", "date_insert",
}


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
        limit: int = 25, offset: int = 0,
        order_by: str = "ragione_sociale_completa", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        order_col = order_by if order_by in _SOGGETTI_ORDER_COLS else "ragione_sociale_completa"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
        search_pattern = f"%{search.strip()}%" if search and search.strip() else None
        sql = f"""
            SELECT s.id, s.ragione_sociale_completa, s.codice_fiscale,
                   s.partita_iva, s.cognome, s.nome, s.ragione_sociale,
                   tsd.descrizione AS tipo_descrizione,
                   tsd.id AS tipo_soggetto_dettaglio_id,
                   ts.id AS natura_soggetto,
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
             ORDER BY {order_col} {direction}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params = [
            search_pattern, search_pattern, search_pattern, search_pattern,
            tipo_soggetto_dettaglio_id, tipo_soggetto_dettaglio_id,
            limit, offset,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return extract_paginated(cursor)

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
            return str(row[0]) if row else None

    # Scopo: Dettaglio completo soggetto con tipo e natura.
    def get_soggetto(self, soggetto_id: str) -> dict[str, Any] | None:
        sql = """
            SELECT s.id, s.ragione_sociale_completa, s.codice_fiscale,
                   s.partita_iva, s.cognome, s.nome, s.ragione_sociale,
                   s.sesso, s.data_nascita, s.comune_id AS comune_nascita_id,
                   tsd.id AS tipo_soggetto_dettaglio_id,
                   tsd.descrizione AS tipo_descrizione,
                   ts.id AS natura_soggetto
              FROM anagrafiche.soggetti s
              JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
              JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
             WHERE s.id = %s::uuid
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # =================================================================
    # Creazione soggetti
    # =================================================================

    # Scopo: Crea soggetto PF chiamando la funzione DB building block.
    #        Obiettivo: INSERT soggetto + contatto default, tutto in funzione PG.
    def crea_soggetto_pf(
        self, *, cognome: str, nome: str, codice_fiscale: str, email: str,
        data_nascita: str | None = None, sesso: str = "M",
        stato_iso2: str = "IT",
    ) -> str:
        sql = """
            SELECT anagrafiche.fn_crea_soggetto_pf(
                p_cognome        := %s,
                p_nome           := %s,
                p_codice_fiscale := %s,
                p_email          := %s,
                p_data_nascita   := %s::date,
                p_sesso          := %s,
                p_stato_iso2     := %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                cognome, nome, codice_fiscale, email,
                data_nascita, sesso, stato_iso2,
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
                p_codice_sdi                 := %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                ragione_sociale, tipo_soggetto_dettaglio_id, email,
                codice_fiscale, partita_iva, stato_iso2,
                forma_giuridica_id, id_prov_iscri_rea, iscrizione_rea,
                capitale_sociale, socio_unico, liquidazione,
                destinatario_fe, pec_fatturazione, codice_sdi,
            ])
            row = cursor.fetchone()
            assert row is not None
            return str(row[0])

    # =================================================================
    # Aggiornamento soggetti
    # =================================================================

    # Scopo: Aggiorna campi modificabili di un soggetto.
    def update_soggetto(self, soggetto_id: str, data: dict[str, Any]) -> bool:
        _ALLOWED = {
            "cognome", "nome", "ragione_sociale", "codice_fiscale",
            "partita_iva", "sesso", "data_nascita", "comune_id",
        }
        # Mapping alias frontend → colonna DB
        _ALIAS = {"comune_nascita_id": "comune_id"}
        mapped = {_ALIAS.get(k, k): v for k, v in data.items()}
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
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Crea contatto per un soggetto.
    def crea_contatto(
        self, soggetto_id: str, *, nominativo: str, email: str | None = None,
        telefono: str | None = None, cellulare: str | None = None,
        pec: str | None = None, tipo_contatto_id: int | None = None,
        unita_organizzativa_id: int | None = None, note: str | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO anagrafiche.contatti
                (soggetto_id, nominativo, email, telefono, cellulare, pec,
                 tipo_contatto_id, unita_organizzativa_id, note)
            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, nominativo, email, telefono, cellulare, pec,
                      tipo_contatto_id, unita_organizzativa_id, note
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                soggetto_id, nominativo, email, telefono, cellulare, pec,
                tipo_contatto_id, unita_organizzativa_id, note,
            ])
            row = cursor.fetchone()
            assert row is not None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))

    # Scopo: Aggiorna un contatto esistente con verifica ownership soggetto.
    def update_contatto(self, contatto_id: int, data: dict[str, Any],
                        soggetto_id: str | None = None) -> bool:
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
        sql = f"UPDATE anagrafiche.contatti SET {set_clause} {where}"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    # =================================================================
    # Indirizzi soggetto
    # =================================================================

    # Scopo: Lista indirizzi layer soggetto.
    def get_soggetto_indirizzi(self, soggetto_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT isog.id, isog.tipo_indirizzo_id,
                   ti.descrizione AS tipo_indirizzo_descrizione,
                   ti.codice_interno AS tipo_indirizzo_codice,
                   isog.indirizzo_dettaglio_id,
                   isog.indirizzo_libero,
                   isog.stato_id, isog.comune_id,
                   COALESCE(isog.indirizzo_libero,
                            idet.indirizzo_normalizzato) AS indirizzo_display
              FROM anagrafiche.indirizzi_soggetti isog
              JOIN config.tipi_indirizzi ti ON ti.id = isog.tipo_indirizzo_id
              LEFT JOIN anagrafiche.indirizzi_dettaglio idet
                ON idet.id = isog.indirizzo_dettaglio_id
             WHERE isog.soggetto_id = %s::uuid
             ORDER BY ti.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

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

    # =================================================================
    # Ruoli
    # =================================================================

    # Scopo: Lista ruoli assegnati a un soggetto.
    def get_soggetto_ruoli(self, soggetto_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT sr.id, sr.tipo_ruolo_id,
                   tr.codice AS ruolo_codice,
                   tr.descrizione AS ruolo_descrizione
              FROM anagrafiche.soggetti_ruoli sr
              JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
             WHERE sr.soggetto_id = %s::uuid
             ORDER BY tr.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Assegna ruolo a soggetto (get or create, idempotente).
    def assign_ruolo(self, soggetto_id: str, codice_ruolo: str) -> int:
        sql = """
            SELECT script.fn_get_or_create_soggetto_ruolo(%s::uuid, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id, codice_ruolo])
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # =================================================================
    # Dati societari
    # =================================================================

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
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description]
            return dict(zip(cols, row))
