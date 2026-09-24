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

from apps.core.services.email_constants import AMBITO_SISTEMA
from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    fetchone_scalar,
    jsonb_out,
    row_to_dict,
    rows_to_list,
    sql_order_direction,
)
from apps.core.db.sql_write_helpers import execute_dynamic_update
from apps.core.services import crypto_service


# Whitelist ORDER BY delle tre liste email: chiave = `campo_sorgente` che il
# frontend invia come sortField, valore = espressione SQL qualificata. Le
# descrizioni delle UO restano nude perche' sono alias di output della SELECT.
#
# Prima del 2026-08-01 le tre liste NON sapevano ordinare: l'ORDER BY era
# cablato nel repository (`ea.codice`, `et.codice, et.lingua`,
# `el.data_insert DESC`) e le view non leggevano nemmeno `order_by`. La lista
# log lo INVIAVA gia' — lo store manda `order_by=data_insert` — e veniva
# ignorato in silenzio.
EMAIL_ACCOUNT_ORDER_COLUMNS: dict[str, str] = {  # alias: ea = config.email_account
    "codice": "ea.codice",
    "descrizione": "ea.descrizione",
    "email_from": "ea.email_from",
    "smtp_host": "ea.smtp_host",
    "unita_organizzativa_descrizione": "unita_organizzativa_descrizione",
    "attivo": "ea.attivo",
}

EMAIL_TEMPLATE_ORDER_COLUMNS: dict[str, str] = {  # alias: et = config.email_template
    "codice": "et.codice",
    "lingua": "et.lingua",
    "oggetto": "et.oggetto",
    "unita_organizzativa_descrizione": "unita_organizzativa_descrizione",
    "attivo": "et.attivo",
}

# alias: el = config.email_log, ea = account, et = template
EMAIL_LOG_ORDER_COLUMNS: dict[str, str] = {
    "data_insert": "el.data_insert",
    "destinatario": "el.destinatario",
    "oggetto": "el.oggetto",
    "stato": "el.stato",
    "ambito": "el.ambito",
    "tentativi": "el.tentativi",
    "inviato_at": "el.inviato_at",
    "account_codice": "account_codice",
    "template_codice": "template_codice",
}


# Cosa si PUO' cercare nelle tre liste email; cosa si cerca lo dice il catalogo
# della lista (`add_ricerca_full_condition`, brief-be-ricerca-full-liste-residue
# §2), letto a ogni ricerca. Colonne semplici della tabella nel `FROM` (alias
# `ea`, `et`, `el`), proiettate con lo stesso nome: forma a tupla.
# ⭐ Soglie (brief §6): account e template sono tabelle di CONFIGURAZIONE e
#    cercano da un carattere (Tid, 2026-09-23); il log e' un registro, non
#    configurazione, e resta al default del BB (sotto soglia il termine non
#    filtra — prima del 2026-09-24 filtrava da un carattere).
_RICERCA_EMAIL_ACCOUNT = RicercaFull("config.email_account", ("codice", "descrizione", "email_from"))
_RICERCA_EMAIL_TEMPLATE = RicercaFull("config.email_template", ("codice", "oggetto"))
_RICERCA_EMAIL_LOG = RicercaFull("config.email_log", ("destinatario", "oggetto"))


# Scopo: risolve la clausola ORDER BY dalla whitelist, con fallback esplicito.
#        Il tiebreaker sull'id lo aggiunge il chiamante: e' l'unica cosa che
#        cambia fra le tre liste (`ea.id`, `et.id`, `el.id`). La direzione passa
#        da `sql_order_direction` (convenzione di casa: NULL come valore
#        minimo), non da un if riscritto qui.
def _email_order_clause(
    order_by: str | None,
    order_dir: str | None,
    *,
    colonne: dict[str, str],
    default: str,
) -> str:
    colonna = colonne.get(order_by or "", default)
    return f"{colonna} {sql_order_direction(order_dir)}"


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
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        params: list[Any] = []

        if attivo_only:
            conditions.append("ea.attivo IS TRUE")
        add_ricerca_full_condition(
            conditions, params, search, _RICERCA_EMAIL_ACCOUNT, alias="ea", min_caratteri=1,
        )

        where = " AND ".join(conditions) if conditions else "TRUE"
        order_clause = _email_order_clause(
            order_by, order_dir,
            colonne=EMAIL_ACCOUNT_ORDER_COLUMNS, default="ea.codice",
        )
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
             ORDER BY {order_clause}, ea.id
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
        # `codice_interno` e' la chiave logica IMMUTABILE (NOT NULL, lockata,
        # nessun default DB): qui il `codice` e' MUTABILE (in _ACCOUNT_UPDATE_COLS),
        # quindi codice_interno va fissato = codice alla create e poi resta stabile
        # anche se il codice viene rinominato. Senza, l'INSERT viola NOT NULL
        # (colonna aggiunta dal DB in 20260629-05, vedi analisi-hardcoded-codice.md §4 #2).
        sql = """
            INSERT INTO config.email_account
                (codice, codice_interno, descrizione, unita_organizzativa_id,
                 smtp_host, smtp_port, smtp_use_tls, smtp_use_ssl,
                 smtp_username, smtp_password_encrypted,
                 email_from, email_reply_to, attivo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = [
            codice, codice, descrizione, unita_organizzativa_id,
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
                return jsonb_out(row[0])
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
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        params: list[Any] = []

        if attivo_only:
            conditions.append("et.attivo IS TRUE")
        if codice:
            conditions.append("et.codice = %s")
            params.append(codice)
        add_ricerca_full_condition(
            conditions, params, search, _RICERCA_EMAIL_TEMPLATE, alias="et", min_caratteri=1,
        )

        where = " AND ".join(conditions) if conditions else "TRUE"
        # Default storico a due chiavi (`codice, lingua`): un template esiste in
        # piu' lingue, e separarle a video renderebbe la lista illeggibile.
        order_clause = _email_order_clause(
            order_by, order_dir,
            colonne=EMAIL_TEMPLATE_ORDER_COLUMNS, default="et.codice",
        )
        if not order_by:
            order_clause = "et.codice ASC, et.lingua ASC"
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
             ORDER BY {order_clause}, et.id
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

    # Scopo: Aggiorna un template email. `variabili_disponibili` (lista) va a
    #        ::jsonb via il BB (niente pre-dump manuale); whitelist colonne.
    def update_template(self, template_id: int, **kwargs: Any) -> bool:
        return execute_dynamic_update(
            "config.email_template", template_id, kwargs,
            allowed=self._TEMPLATE_UPDATE_COLS,
            extra_set="data_update = now()",
        )

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
                return jsonb_out(row[0])
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
        # ⛔ Nessun default, come su `create_outbox` (2026-09-05). `ambito`
        #    classifica A CHI APPARTIENE l'email, ed e' la colonna su cui il
        #    database sta per montare una policy di lettura: un valore di
        #    RIPIEGO non puo' fare da cancello di sicurezza, o basta un campo
        #    dimenticato per classificare come segreta una riga qualunque.
        #    Prerequisito dichiarato dal team DB per la policy su
        #    `config.email_log` (brief residui §1-nonies).
        ambito: str,
        unita_organizzativa_id: int | None = None,
        pratica_id: int | None = None,
        auth_user_id: int | None = None,
        contesto_json: dict[str, Any] | None = None,
    ) -> int:
        # ⛔ LE EMAIL DI SISTEMA PASSANO DA UNA PORTA LORO, e non e' una
        #    preferenza di stile: dal 2026-09-05 `config.email_log` ha la RLS
        #    accesa, e la policy ammette in scrittura solo il super admin o
        #    l'identita' tecnica di `send_pending_emails`. Un reset password
        #    nasce su un endpoint NON autenticato — nessuna sessione, nessuna
        #    GUC — e un invito puo' partire da un admin che super admin non e':
        #    misurato il 2026-09-05, entrambi venivano RIFIUTATI.
        # ⭐ `config.fn_accoda_email_sistema` e' `SECURITY DEFINER` e sa scrivere
        #    UNA COSA SOLA: `ambito='SISTEMA'`, emittente `NULL`. Non prende
        #    l'ambito come parametro proprio per non essere una porta di
        #    servizio con cui scrivere qualunque riga aggirando la policy.
        # ⚠️ Il bivio guarda LA RIGA, non il chiamante: `_send_smtp` e
        #    `retry_log_entry` arrivano qui sia dal percorso senza sessione sia
        #    dal worker, che l'identita' ce l'ha. E' l'ambito a decidere.
        if ambito == AMBITO_SISTEMA:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT config.fn_accoda_email_sistema(
                        p_destinatario           => %s,
                        p_oggetto                => %s,
                        p_corpo_html             => %s,
                        p_corpo_testo            => %s,
                        p_email_account_id       => %s,
                        p_email_template_id      => %s,
                        p_auth_user_id           => %s,
                        p_contesto_json          => %s::jsonb,
                        p_unita_organizzativa_id => %s,
                        p_destinatari_cc         => %s,
                        p_pratica_id             => %s)
                    """,
                    [
                        destinatario, oggetto, corpo_inviato_html, corpo_inviato_testo,
                        email_account_id, email_template_id, auth_user_id,
                        json.dumps(contesto_json or {}),
                        unita_organizzativa_id, destinatari_cc, pratica_id,
                    ],
                )
                return fetchone_scalar(cursor)

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

    # Scopo: Aggiorna stato di un record log email (SENT, FAILED, RETRY,
    #        SIMULATA). ⚠️ L'elenco autorevole e' il `CHECK`
    #        `chk_email_log_stato`, specchiato in
    #        `amm_software_service._EMAIL_LOG_STATI_VALIDI`: qui si dice
    #        cosa passa di qua, non cosa e' ammesso.
    #
    # ⛔ `ambito` NON ha un default, e serve a scegliere la porta — non a
    #    descrivere la riga. Su una `SISTEMA` l'UPDATE diretto e' rifiutato
    #    dalla policy per lo stesso motivo per cui lo era l'INSERT: chi ha
    #    appena spedito un reset password non ha una sessione.
    # ⭐ `config.fn_chiudi_email_sistema` tocca SOLO righe `SISTEMA` e SOLO i
    #    campi dell'esito. ⚠️ Se la riga non e' di sistema **solleva**, e quel
    #    rifiuto NON va trasformato in un ripiego sull'UPDATE diretto: dice che
    #    qualcuno sta usando la porta di sistema per l'email di un'azienda, ed e'
    #    il solo posto in cui quel difetto si vede.
    def update_log_stato(
        self,
        log_id: int,
        stato: str,
        *,
        ambito: str,
        errore: str | None = None,
        inviato_at: str | None = None,
    ) -> bool:
        if ambito == AMBITO_SISTEMA:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT config.fn_chiudi_email_sistema(%s, %s, %s, %s::timestamptz)",
                    [log_id, stato, errore, inviato_at],
                )
                return bool(fetchone_scalar(cursor))

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
        order_by: str | None = None,
        order_dir: str | None = None,
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
        add_ricerca_full_condition(conditions, params, search, _RICERCA_EMAIL_LOG, alias="el")

        where = " AND ".join(conditions) if conditions else "TRUE"
        # Default `data_insert DESC`: un log si legge dal piu' recente.
        order_clause = _email_order_clause(
            order_by or "data_insert", order_dir or "desc",
            colonne=EMAIL_LOG_ORDER_COLUMNS, default="el.data_insert",
        )
        # `emittente_ragione_sociale` e' la colonna 872 del catalogo (lista
        # `config.email_log`, D-4 del brief perimetro-emittente-cataloghi-
        # globali, 2026-09-18): il super admin su «Tutti gli emittenti» vede le
        # email di tutte le aziende con l'azienda accanto, ed e' cio' che rende
        # la lista `multi_emittente` certificabile a DB. Ragione sociale del
        # SOGGETTO dell'emittente, stessa catena di `_PRESET_SELECT_SQL`
        # (`ui_admin_repository.py`); NULL sulle righe `SISTEMA`, che un
        # emittente non ce l'hanno.
        sql = f"""
            SELECT el.id, el.destinatario, el.destinatari_cc, el.oggetto,
                   el.stato, el.errore, el.tentativi, el.inviato_at,
                   el.ambito, el.unita_organizzativa_id, el.pratica_id,
                   el.auth_user_id, el.data_insert,
                   ea.codice AS account_codice,
                   et.codice AS template_codice,
                   el.emittente_fiscale_id,
                   s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
                   COUNT(*) OVER() AS total_count
              FROM config.email_log el
              LEFT JOIN config.email_account ea ON ea.id = el.email_account_id
              LEFT JOIN config.email_template et ON et.id = el.email_template_id
              LEFT JOIN anagrafiche.emittenti_fiscali ef
                     ON ef.id = el.emittente_fiscale_id
              LEFT JOIN anagrafiche.soggetti_ruoli sr_ef
                     ON sr_ef.id = ef.soggetto_ruolo_id
              LEFT JOIN anagrafiche.soggetti s_ef
                     ON s_ef.id = sr_ef.soggetto_id
             WHERE {where}
             ORDER BY {order_clause}, el.id DESC
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
        # ⛔ Nessun default: lo dichiara chi crea la bozza. Vedi `EmailPrepareView`.
        ambito: str,
        # ⭐ L'azienda a cui la bozza appartiene. Obbligatoria per il database su
        #    tutto cio' che non e' `SISTEMA` (`chk_email_outbox_ambito_emittente`),
        #    ed e' la colonna su cui la policy RLS filtra: senza, la riga non
        #    sarebbe di nessuno e nessun operatore la vedrebbe.
        emittente_fiscale_id: int | None = None,
        unita_organizzativa_id: int | None = None,
        pratica_id: int | None = None,
        auth_user_id: int | None = None,
        creato_da_user_id: int | None = None,
        contesto_json: dict[str, Any] | None = None,
    ) -> int:
        sql = """
            INSERT INTO config.email_outbox
                (email_account_id, email_template_id, ambito, emittente_fiscale_id,
                 unita_organizzativa_id, pratica_id,
                 destinatario, destinatari_cc, oggetto, corpo_html, corpo_testo,
                 stato, contesto_json, auth_user_id, creato_da_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'DRAFT', %s::jsonb, %s, %s)
            RETURNING id
        """
        params = [
            email_account_id, email_template_id, ambito, emittente_fiscale_id,
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
