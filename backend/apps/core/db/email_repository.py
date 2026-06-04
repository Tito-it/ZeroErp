# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per accesso DB a tabelle email
#        (config.email_account, config.email_template, config.email_log).
#        Chiama anche le funzioni PG di risoluzione con fallback.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection


# Scopo: Parsa un campo JSONB che psycopg2 potrebbe restituire come stringa.
def _parse_jsonb_field(row: dict[str, Any], field: str) -> None:
    val = row.get(field)
    if isinstance(val, str):
        try:
            row[field] = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass

from apps.core.db._helpers import fetchone_scalar, row_to_dict, rows_to_list
from apps.core.services import crypto_service


class EmailRepository:
    """Accesso DB per config.email_account, config.email_template, config.email_log."""

    # -------------------------------------------------------
    # Email Account — CRUD + risoluzione
    # -------------------------------------------------------

    # Scopo: Lista account email con filtri opzionali, paginazione e conteggio.
    def list_accounts(
        self,
        *,
        search: str | None = None,
        attivo_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        params: list[Any] = []

        if attivo_only:
            conditions.append("ea.attivo IS TRUE")
        if search:
            conditions.append("(ea.codice ILIKE %s OR ea.descrizione ILIKE %s OR ea.email_from ILIKE %s)")
            like = f"%{search}%"
            params.extend([like, like, like])

        where = " AND ".join(conditions) if conditions else "TRUE"
        sql = f"""
            SELECT ea.id, ea.codice, ea.descrizione,
                   ea.unita_organizzativa_id,
                   uo.descrizione AS unita_organizzativa_descrizione,
                   ea.smtp_host, ea.smtp_port, ea.smtp_use_tls, ea.smtp_use_ssl,
                   ea.smtp_username, ea.email_from, ea.email_reply_to,
                   ea.attivo,
                   COUNT(*) OVER() AS total_count
              FROM config.email_account ea
              LEFT JOIN config.unita_organizzative uo ON uo.id = ea.unita_organizzativa_id
             WHERE {where}
             ORDER BY ea.codice
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params.extend([limit, offset])

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = rows_to_list(cursor)

        total = rows[0]["total_count"] if rows else 0
        for r in rows:
            r.pop("total_count", None)
        return rows, total

    # Scopo: Dettaglio singolo account per ID con password crittografata (uso interno service).
    def get_account_with_password(self, account_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, codice, smtp_host, smtp_port, smtp_use_tls, smtp_use_ssl,
                   smtp_username, smtp_password_encrypted, email_from, email_reply_to
              FROM config.email_account
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [account_id])
            return row_to_dict(cursor)

    # Scopo: Dettaglio singolo account email per ID (senza password in chiaro).
    #        Include flag `has_smtp_password` (derivato da smtp_password_encrypted IS NOT NULL)
    #        e `meta` jsonb decodificato — usati dalla view detail per derivare
    #        capability `can_test` e ultimo esito test (Fase 6).
    def get_account(self, account_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT ea.id, ea.codice, ea.descrizione,
                   ea.unita_organizzativa_id,
                   uo.descrizione AS unita_organizzativa_descrizione,
                   ea.smtp_host, ea.smtp_port, ea.smtp_use_tls, ea.smtp_use_ssl,
                   ea.smtp_username, ea.email_from, ea.email_reply_to,
                   ea.attivo,
                   ea.smtp_password_encrypted IS NOT NULL AS has_smtp_password,
                   ea.meta
              FROM config.email_account ea
              LEFT JOIN config.unita_organizzative uo ON uo.id = ea.unita_organizzativa_id
             WHERE ea.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [account_id])
            result = row_to_dict(cursor)
            if result:
                _parse_jsonb_field(result, "meta")
            return result

    # Scopo: Crea un nuovo account email. La password SMTP viene crittografata.
    def create_account(
        self,
        *,
        codice: str,
        descrizione: str,
        smtp_host: str,
        smtp_port: int,
        smtp_use_tls: bool,
        smtp_use_ssl: bool,
        smtp_username: str,
        smtp_password: str,
        email_from: str,
        email_reply_to: str | None = None,
        unita_organizzativa_id: int | None = None,
        attivo: bool = True,
    ) -> int:
        encrypted_pw = crypto_service.encrypt(smtp_password) if smtp_password else None
        sql = """
            INSERT INTO config.email_account
                (codice, descrizione, unita_organizzativa_id,
                 smtp_host, smtp_port, smtp_use_tls, smtp_use_ssl,
                 smtp_username, smtp_password_encrypted,
                 email_from, email_reply_to, attivo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = [
            codice, descrizione, unita_organizzativa_id,
            smtp_host, smtp_port, smtp_use_tls, smtp_use_ssl,
            smtp_username, encrypted_pw,
            email_from, email_reply_to, attivo,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return fetchone_scalar(cursor)

    # Colonne aggiornabili — whitelist per prevenire SQL injection da kwargs
    _ACCOUNT_UPDATE_COLS = frozenset({
        "codice", "descrizione", "unita_organizzativa_id",
        "smtp_host", "smtp_port", "smtp_use_tls", "smtp_use_ssl",
        "smtp_username", "email_from", "email_reply_to", "attivo",
    })

    # Scopo: Aggiorna un account email. Se smtp_password fornita, la ri-crittografa.
    def update_account(self, account_id: int, **kwargs: Any) -> bool:
        fields: list[str] = []
        params: list[Any] = []

        # Gestione speciale: password in chiaro → crittografata
        if "smtp_password" in kwargs:
            raw_pw = kwargs.pop("smtp_password")
            if raw_pw:
                fields.append("smtp_password_encrypted = %s")
                params.append(crypto_service.encrypt(raw_pw))

        for col, val in kwargs.items():
            if col not in self._ACCOUNT_UPDATE_COLS:
                continue
            if isinstance(val, str):
                val = val.strip()
            fields.append(f"{col} = %s")
            params.append(val)

        if not fields:
            return False

        fields.append("data_update = now()")
        params.append(account_id)
        sql = f"UPDATE config.email_account SET {', '.join(fields)} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0

    # Scopo: Elimina un account email per ID.
    def delete_account(self, account_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM config.email_account WHERE id = %s", [account_id])
            return cursor.rowcount > 0

    # Scopo: Persiste in `email_account.meta` l'esito dell'ultimo test SMTP.
    #        outcome ∈ {"SUCCESS", "FAILED"}; tested_at ISO-8601 UTC.
    #        message: testo opzionale (es. errore SMTP). Usa jsonb_set
    #        per non sovrascrivere altre chiavi presenti in meta.
    def update_account_last_test(
        self,
        account_id: int,
        *,
        outcome: str,
        tested_at: str,
        message: str | None = None,
    ) -> bool:
        sql = """
            UPDATE config.email_account
               SET meta = COALESCE(meta, '{}'::jsonb)
                          || jsonb_build_object(
                              'last_test_outcome', %s::text,
                              'last_test_at', %s::text,
                              'last_test_message', %s::text
                          ),
                   data_update = now()
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [outcome, tested_at, message, account_id])
            return cursor.rowcount > 0

    # Scopo: Risolve account email per reparto con fallback via funzione PG.
    def resolve_account(self, unita_organizzativa_id: int | None = None) -> dict[str, Any] | None:
        sql = "SELECT config.fn_resolve_email_account(%s) AS result"
        with connection.cursor() as cursor:
            cursor.execute(sql, [unita_organizzativa_id])
            row = cursor.fetchone()
            if row and row[0]:
                return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return None

    # -------------------------------------------------------
    # Email Template — CRUD + risoluzione
    # -------------------------------------------------------

    # Scopo: Lista template email con filtri, paginazione e conteggio.
    def list_templates(
        self,
        *,
        search: str | None = None,
        codice: str | None = None,
        attivo_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        params: list[Any] = []

        if attivo_only:
            conditions.append("et.attivo IS TRUE")
        if codice:
            conditions.append("et.codice = %s")
            params.append(codice)
        if search:
            conditions.append("(et.codice ILIKE %s OR et.oggetto ILIKE %s)")
            like = f"%{search}%"
            params.extend([like, like])

        where = " AND ".join(conditions) if conditions else "TRUE"
        sql = f"""
            SELECT et.id, et.codice,
                   et.unita_organizzativa_id,
                   uo.descrizione AS unita_organizzativa_descrizione,
                   et.tipo_prestazione_id,
                   et.lingua, et.oggetto,
                   et.variabili_disponibili,
                   et.attivo,
                   COUNT(*) OVER() AS total_count
              FROM config.email_template et
              LEFT JOIN config.unita_organizzative uo ON uo.id = et.unita_organizzativa_id
             WHERE {where}
             ORDER BY et.codice, et.lingua
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params.extend([limit, offset])

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = rows_to_list(cursor)

        total = rows[0]["total_count"] if rows else 0
        for r in rows:
            r.pop("total_count", None)
            _parse_jsonb_field(r, "variabili_disponibili")
        return rows, total

    # Scopo: Dettaglio singolo template email per ID (incluso corpo).
    def get_template(self, template_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT et.id, et.codice,
                   et.unita_organizzativa_id,
                   uo.descrizione AS unita_organizzativa_descrizione,
                   et.tipo_prestazione_id,
                   et.lingua, et.oggetto, et.corpo_html, et.corpo_testo,
                   et.variabili_disponibili,
                   et.attivo
              FROM config.email_template et
              LEFT JOIN config.unita_organizzative uo ON uo.id = et.unita_organizzativa_id
             WHERE et.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [template_id])
            result = row_to_dict(cursor)
            if result:
                _parse_jsonb_field(result, "variabili_disponibili")
            return result

    # Scopo: Crea un nuovo template email.
    def create_template(
        self,
        *,
        codice: str,
        oggetto: str,
        corpo_html: str,
        corpo_testo: str | None = None,
        lingua: str = "it",
        unita_organizzativa_id: int | None = None,
        tipo_prestazione_id: int | None = None,
        variabili_disponibili: list[str] | None = None,
        attivo: bool = True,
    ) -> int:
        sql = """
            INSERT INTO config.email_template
                (codice, unita_organizzativa_id, tipo_prestazione_id,
                 lingua, oggetto, corpo_html, corpo_testo,
                 variabili_disponibili, attivo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            RETURNING id
        """
        params = [
            codice, unita_organizzativa_id, tipo_prestazione_id,
            lingua, oggetto, corpo_html, corpo_testo,
            json.dumps(variabili_disponibili or []),
            attivo,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return fetchone_scalar(cursor)

    _TEMPLATE_UPDATE_COLS = frozenset({
        "codice", "oggetto", "corpo_html", "corpo_testo", "lingua",
        "unita_organizzativa_id", "tipo_prestazione_id",
        "variabili_disponibili", "attivo",
    })

    # Scopo: Aggiorna un template email.
    def update_template(self, template_id: int, **kwargs: Any) -> bool:
        # Serializza variabili_disponibili se presente
        if "variabili_disponibili" in kwargs and kwargs["variabili_disponibili"] is not None:
            kwargs["variabili_disponibili"] = json.dumps(kwargs["variabili_disponibili"])

        fields: list[str] = []
        params: list[Any] = []
        for col, val in kwargs.items():
            if col not in self._TEMPLATE_UPDATE_COLS:
                continue
            if isinstance(val, str):
                val = val.strip()
            if col == "variabili_disponibili":
                fields.append(f"{col} = %s::jsonb")
            else:
                fields.append(f"{col} = %s")
            params.append(val)

        if not fields:
            return False

        fields.append("data_update = now()")
        params.append(template_id)
        sql = f"UPDATE config.email_template SET {', '.join(fields)} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0

    # Scopo: Elimina un template email per ID.
    def delete_template(self, template_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM config.email_template WHERE id = %s", [template_id])
            return cursor.rowcount > 0

    # Scopo: Risolve template email per codice/reparto/tipo/lingua con fallback PG.
    def resolve_template(
        self,
        codice: str,
        unita_organizzativa_id: int | None = None,
        tipo_prestazione_id: int | None = None,
        lingua: str = "it",
    ) -> dict[str, Any] | None:
        sql = "SELECT config.fn_resolve_email_template(%s, %s, %s, %s) AS result"
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice, unita_organizzativa_id, tipo_prestazione_id, lingua])
            row = cursor.fetchone()
            if row and row[0]:
                return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return None

    # -------------------------------------------------------
    # Email Log — Insert + consultazione
    # -------------------------------------------------------

    # Scopo: Inserisce un record nel log email.
    def insert_log(
        self,
        *,
        email_account_id: int | None,
        email_template_id: int | None,
        destinatario: str,
        destinatari_cc: list[str] | None = None,
        oggetto: str,
        corpo_inviato_html: str | None = None,
        corpo_inviato_testo: str | None = None,
        stato: str = "PENDING",
        ambito: str = "SISTEMA",
        unita_organizzativa_id: int | None = None,
        pratica_id: int | None = None,
        auth_user_id: int | None = None,
        contesto_json: dict[str, Any] | None = None,
    ) -> int:
        sql = """
            INSERT INTO config.email_log
                (email_account_id, email_template_id, destinatario, destinatari_cc,
                 oggetto, corpo_inviato_html, corpo_inviato_testo,
                 stato, ambito, unita_organizzativa_id, pratica_id,
                 auth_user_id, contesto_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id
        """
        params = [
            email_account_id, email_template_id, destinatario, destinatari_cc,
            oggetto, corpo_inviato_html, corpo_inviato_testo,
            stato, ambito, unita_organizzativa_id, pratica_id,
            auth_user_id, json.dumps(contesto_json or {}),
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return fetchone_scalar(cursor)

    # Scopo: Aggiorna stato di un record log email (SENT, FAILED, RETRY).
    def update_log_stato(
        self,
        log_id: int,
        stato: str,
        *,
        errore: str | None = None,
        inviato_at: str | None = None,
    ) -> bool:
        sql = """
            UPDATE config.email_log
               SET stato = %s,
                   errore = %s,
                   inviato_at = CASE WHEN %s IS NOT NULL THEN %s::timestamptz ELSE inviato_at END,
                   tentativi = tentativi + 1
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [stato, errore, inviato_at, inviato_at, log_id])
            return cursor.rowcount > 0

    # Scopo: Lista log email con filtri, paginazione e conteggio.
    def list_logs(
        self,
        *,
        search: str | None = None,
        stato: str | None = None,
        ambito: str | None = None,
        unita_organizzativa_id: int | None = None,
        pratica_id: int | None = None,
        data_da: str | None = None,
        data_a: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        params: list[Any] = []

        if stato:
            conditions.append("el.stato = %s")
            params.append(stato)
        if ambito:
            conditions.append("el.ambito = %s")
            params.append(ambito)
        if unita_organizzativa_id is not None:
            conditions.append("el.unita_organizzativa_id = %s")
            params.append(unita_organizzativa_id)
        if pratica_id is not None:
            conditions.append("el.pratica_id = %s")
            params.append(pratica_id)
        if data_da:
            conditions.append("el.data_insert >= %s::date")
            params.append(data_da)
        if data_a:
            conditions.append("el.data_insert < (%s::date + INTERVAL '1 day')")
            params.append(data_a)
        if search:
            conditions.append("(el.destinatario ILIKE %s OR el.oggetto ILIKE %s)")
            like = f"%{search}%"
            params.extend([like, like])

        where = " AND ".join(conditions) if conditions else "TRUE"
        sql = f"""
            SELECT el.id, el.destinatario, el.destinatari_cc, el.oggetto,
                   el.stato, el.errore, el.tentativi, el.inviato_at,
                   el.ambito, el.unita_organizzativa_id, el.pratica_id,
                   el.auth_user_id, el.data_insert,
                   ea.codice AS account_codice,
                   et.codice AS template_codice,
                   COUNT(*) OVER() AS total_count
              FROM config.email_log el
              LEFT JOIN config.email_account ea ON ea.id = el.email_account_id
              LEFT JOIN config.email_template et ON et.id = el.email_template_id
             WHERE {where}
             ORDER BY el.data_insert DESC, el.id DESC
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params.extend([limit, offset])

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = rows_to_list(cursor)

        total = rows[0]["total_count"] if rows else 0
        for r in rows:
            r.pop("total_count", None)
        return rows, total

    # Scopo: Aggiorna email_log_id dopo invio da outbox.
    def update_log_outbox_link(self, log_id: int, email_outbox_id: int) -> None:
        sql = "UPDATE config.email_log SET email_outbox_id = %s WHERE id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [email_outbox_id, log_id])

    # Scopo: Dettaglio singolo log email per ID (con corpo inviato).
    def get_log(self, log_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT el.id, el.destinatario, el.destinatari_cc, el.oggetto,
                   el.corpo_inviato_html, el.corpo_inviato_testo,
                   el.stato, el.errore, el.tentativi, el.max_tentativi,
                   el.inviato_at, el.ambito,
                   el.unita_organizzativa_id, el.pratica_id,
                   el.auth_user_id, el.contesto_json, el.data_insert,
                   ea.codice AS account_codice, ea.email_from AS account_email_from,
                   et.codice AS template_codice
              FROM config.email_log el
              LEFT JOIN config.email_account ea ON ea.id = el.email_account_id
              LEFT JOIN config.email_template et ON et.id = el.email_template_id
             WHERE el.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [log_id])
            return row_to_dict(cursor)

    # -------------------------------------------------------
    # Email Outbox — CRUD bozze
    # -------------------------------------------------------

    # Scopo: Crea una bozza email nell'outbox.
    def create_outbox(
        self,
        *,
        destinatario: str,
        oggetto: str,
        corpo_html: str,
        corpo_testo: str | None = None,
        destinatari_cc: list[str] | None = None,
        email_account_id: int | None = None,
        email_template_id: int | None = None,
        ambito: str = "SISTEMA",
        unita_organizzativa_id: int | None = None,
        pratica_id: int | None = None,
        auth_user_id: int | None = None,
        creato_da_user_id: int | None = None,
        contesto_json: dict[str, Any] | None = None,
    ) -> int:
        sql = """
            INSERT INTO config.email_outbox
                (email_account_id, email_template_id, ambito,
                 unita_organizzativa_id, pratica_id,
                 destinatario, destinatari_cc, oggetto, corpo_html, corpo_testo,
                 stato, contesto_json, auth_user_id, creato_da_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'DRAFT', %s::jsonb, %s, %s)
            RETURNING id
        """
        params = [
            email_account_id, email_template_id, ambito,
            unita_organizzativa_id, pratica_id,
            destinatario, destinatari_cc, oggetto, corpo_html, corpo_testo,
            json.dumps(contesto_json or {}), auth_user_id, creato_da_user_id,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return fetchone_scalar(cursor)

    # Scopo: Dettaglio bozza outbox per ID con allegati.
    def get_outbox(self, outbox_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT eo.id, eo.destinatario, eo.destinatari_cc,
                   eo.oggetto, eo.corpo_html, eo.corpo_testo,
                   eo.stato, eo.ambito,
                   eo.unita_organizzativa_id, eo.pratica_id,
                   eo.auth_user_id, eo.creato_da_user_id,
                   eo.email_account_id, eo.email_template_id,
                   eo.email_log_id, eo.inviato_at,
                   eo.contesto_json, eo.data_insert,
                   ea.codice AS account_codice, ea.email_from AS account_email_from
              FROM config.email_outbox eo
              LEFT JOIN config.email_account ea ON ea.id = eo.email_account_id
             WHERE eo.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [outbox_id])
            result = row_to_dict(cursor)
        if result:
            result["allegati"] = self.list_allegati_by_outbox(outbox_id)
        return result

    # Scopo: Lista bozze outbox con filtri e paginazione.
    def list_outbox(
        self,
        *,
        creato_da_user_id: int | None = None,
        unita_organizzativa_id: int | None = None,
        stato: str | None = None,
        pratica_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        params: list[Any] = []

        if creato_da_user_id is not None:
            conditions.append("eo.creato_da_user_id = %s")
            params.append(creato_da_user_id)
        if unita_organizzativa_id is not None:
            conditions.append("eo.unita_organizzativa_id = %s")
            params.append(unita_organizzativa_id)
        if stato:
            conditions.append("eo.stato = %s")
            params.append(stato)
        if pratica_id is not None:
            conditions.append("eo.pratica_id = %s")
            params.append(pratica_id)

        where = " AND ".join(conditions) if conditions else "TRUE"
        sql = f"""
            SELECT eo.id, eo.destinatario, eo.oggetto, eo.stato,
                   eo.ambito, eo.pratica_id,
                   eo.creato_da_user_id, eo.data_insert,
                   ea.codice AS account_codice,
                   COUNT(*) OVER() AS total_count
              FROM config.email_outbox eo
              LEFT JOIN config.email_account ea ON ea.id = eo.email_account_id
             WHERE {where}
             ORDER BY eo.data_insert DESC, eo.id DESC
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params.extend([limit, offset])

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = rows_to_list(cursor)

        total = rows[0]["total_count"] if rows else 0
        for r in rows:
            r.pop("total_count", None)
        return rows, total

    _OUTBOX_UPDATE_COLS = frozenset({
        "oggetto", "corpo_html", "corpo_testo", "destinatario", "destinatari_cc",
    })

    # Scopo: Aggiorna campi editabili di una bozza DRAFT.
    def update_outbox(self, outbox_id: int, **kwargs: Any) -> bool:
        fields: list[str] = []
        params: list[Any] = []
        for col, val in kwargs.items():
            if col not in self._OUTBOX_UPDATE_COLS:
                continue
            if isinstance(val, str):
                val = val.strip()
            fields.append(f"{col} = %s")
            params.append(val)
        if not fields:
            return False
        fields.append("data_update = now()")
        params.append(outbox_id)
        sql = f"UPDATE config.email_outbox SET {', '.join(fields)} WHERE id = %s AND stato = 'DRAFT'"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0

    # Scopo: Aggiorna stato di una bozza outbox.
    def update_outbox_stato(
        self, outbox_id: int, stato: str,
        *, email_log_id: int | None = None, inviato_at: str | None = None,
    ) -> bool:
        sql = """
            UPDATE config.email_outbox
               SET stato = %s, data_update = now(),
                   email_log_id = COALESCE(%s, email_log_id),
                   inviato_at = COALESCE(%s::timestamptz, inviato_at)
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [stato, email_log_id, inviato_at, outbox_id])
            return cursor.rowcount > 0

    # -------------------------------------------------------
    # Email Allegato — CRUD
    # -------------------------------------------------------

    # Scopo: Inserisce un record allegato.
    def create_allegato(
        self,
        *,
        email_outbox_id: int | None = None,
        email_log_id: int | None = None,
        nome_file: str,
        mime_type: str,
        dimensione_bytes: int,
        file_path: str,
        origine: str = "UPLOAD",
    ) -> int:
        sql = """
            INSERT INTO config.email_allegato
                (email_outbox_id, email_log_id, nome_file, mime_type,
                 dimensione_bytes, file_path, origine)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = [email_outbox_id, email_log_id, nome_file, mime_type,
                  dimensione_bytes, file_path, origine]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return fetchone_scalar(cursor)

    # Scopo: Lista allegati per una bozza outbox.
    def list_allegati_by_outbox(self, outbox_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT id, nome_file, mime_type, dimensione_bytes, file_path, origine, data_insert
              FROM config.email_allegato
             WHERE email_outbox_id = %s
             ORDER BY data_insert
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [outbox_id])
            return rows_to_list(cursor)

    # Scopo: Lista allegati per un log email.
    def list_allegati_by_log(self, log_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT id, nome_file, mime_type, dimensione_bytes, file_path, origine, data_insert
              FROM config.email_allegato
             WHERE email_log_id = %s
             ORDER BY data_insert
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [log_id])
            return rows_to_list(cursor)

    # Scopo: Dettaglio singolo allegato per ID.
    def get_allegato(self, allegato_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, email_outbox_id, email_log_id,
                   nome_file, mime_type, dimensione_bytes, file_path, origine, data_insert
              FROM config.email_allegato
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [allegato_id])
            return row_to_dict(cursor)

    # Scopo: Elimina un allegato per ID. Ritorna il file_path per pulizia storage.
    def delete_allegato(self, allegato_id: int) -> str | None:
        sql = "SELECT file_path FROM config.email_allegato WHERE id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [allegato_id])
            row = cursor.fetchone()
            if not row:
                return None
            file_path = row[0]
            cursor.execute("DELETE FROM config.email_allegato WHERE id = %s", [allegato_id])
            return file_path

    # Scopo: Copia allegati da outbox a log dopo invio.
    def copy_allegati_to_log(self, outbox_id: int, log_id: int) -> int:
        sql = """
            UPDATE config.email_allegato
               SET email_log_id = %s
             WHERE email_outbox_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [log_id, outbox_id])
            return cursor.rowcount
