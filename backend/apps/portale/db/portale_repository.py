# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository accesso DB per app Portale.
#        Risoluzione entita' origine (billing_account / fornitori) ->
#        soggetto_ruolo_id + dati anagrafici usati dal service invito.
#        Orchestra anche la creazione atomica di auth_user + identita_digitali
#        per i flussi invito portale (simmetrica a amm_software_repository
#        per gli operatori interni).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection


class PortaleRepository:
    """Accesso DB per invito portale + creazione identita portale."""

    # Scopo: Risolve soggetto_ruolo_id + dati anagrafici di un cliente.
    # Il parametro e' cliente_id = PK di anagrafiche.clienti (coerente con
    # ClientiDetailView). Il soggetto_ruolo_id deriva direttamente da
    # clienti.soggetto_ruolo_id (ruolo CL del cliente, coerente con
    # il trigger guard_coerenza che pretende tipo CL per CLIENTE_PORTALE):
    # non si passa da billing_account.soggetto_ruolo_id per non dipendere
    # dal FK del BA, che semanticamente e' il holder e potrebbe divergere.
    # Ritorna None se il cliente non esiste.
    def get_cliente_info(self, cliente_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT cl.id                        AS cliente_id,
                   ba.id                        AS billing_account_id,
                   ba.codice                    AS ba_codice,
                   sr.id                        AS soggetto_ruolo_id,
                   s.id                         AS soggetto_id,
                   s.ragione_sociale_completa   AS ragione_sociale,
                   s.cognome                    AS cognome,
                   s.nome                       AS nome,
                   s.codice_fiscale             AS codice_fiscale
              FROM anagrafiche.clienti cl
              JOIN anagrafiche.soggetti_ruoli sr  ON sr.id = cl.soggetto_ruolo_id
              JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
              JOIN anagrafiche.soggetti s         ON s.id = sr.soggetto_id
             WHERE cl.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [cliente_id])
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description or []]
            return dict(zip(cols, row))

    # Scopo: Risolve soggetto_ruolo_id + dati anagrafici di un fornitore.
    # Simmetrico a get_cliente_info per il ruolo FO.
    def get_fornitore_info(self, fornitore_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT f.id                         AS fornitore_id,
                   sr.id                        AS soggetto_ruolo_id,
                   s.id                         AS soggetto_id,
                   s.ragione_sociale_completa   AS ragione_sociale,
                   s.cognome                    AS cognome,
                   s.nome                       AS nome,
                   s.codice_fiscale             AS codice_fiscale,
                   f.pec_email                  AS pec_email
              FROM anagrafiche.fornitori f
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.soggetto_ruolo_id
              JOIN anagrafiche.soggetti s        ON s.id = sr.soggetto_id
             WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [fornitore_id])
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description or []]
            return dict(zip(cols, row))

    # Scopo: Verifica se esiste gia' un'identita attiva con un certo
    # ruolo_applicativo legata a un dato soggetto_ruolo_id. Usato dal service
    # invito per evitare duplicazioni e per lo stato "portale attivo" mostrato
    # dalla UI admin. Ritorna dict con auth_user_id + stato se trovata, None
    # altrimenti.
    def find_identita_portale(
        self, soggetto_ruolo_id: int, ruolo_applicativo: str
    ) -> dict[str, Any] | None:
        sql = """
            SELECT id               AS identita_id,
                   auth_user_id,
                   attivo,
                   invito_inviato_at,
                   deve_cambiare_password
              FROM anagrafiche.identita_digitali
             WHERE soggetto_ruolo_id = %s
               AND ruolo_applicativo = %s::config.ruolo_applicativo
             ORDER BY attivo DESC, id DESC
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_ruolo_id, ruolo_applicativo])
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description or []]
            return dict(zip(cols, row))

    # Scopo: Verifica se esiste gia' un auth_user con la stessa email.
    # Il vincolo UNIQUE su email e' a livello DB; questo check anticipa
    # l'errore lato service con un codice di errore parlante.
    def find_auth_user_by_email(self, email: str) -> int | None:
        sql = "SELECT id FROM django.auth_user WHERE LOWER(email) = LOWER(%s) LIMIT 1"
        with connection.cursor() as cursor:
            cursor.execute(sql, [email])
            row = cursor.fetchone()
            return int(row[0]) if row else None

    # Scopo: Crea una nuova riga auth_user per un portale user.
    # Username derivato da email (prefisso prima della @), con suffisso
    # progressivo se gia' esistente. is_active=true: il filtraggio ruolo
    # avviene via identita_digitali.attivo + ruolo_applicativo=DISABILITATO.
    # Ritorna l'id del nuovo auth_user.
    def create_auth_user_portale(
        self,
        *,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
    ) -> int:
        username = self._build_unique_username(email)
        sql = """
            INSERT INTO django.auth_user
                   (username, email, password, first_name, last_name,
                    is_active, is_staff, is_superuser, date_joined)
            VALUES (%s, %s, %s, %s, %s, true, false, false, now())
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [username, email, password_hash, first_name, last_name],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Crea l'identita_digitali del portale user. Il trigger DB
    # `trgfn_identita_digitali_guard_coerenza` (§7.1.1) verifica coerenza
    # ruolo_applicativo x tipo soggetto: qui passiamo i campi minimi
    # (attivo=true, niente invito_inviato_at che verra' settato dal service
    # dopo l'invio email).
    def create_identita_portale(
        self,
        *,
        auth_user_id: int,
        soggetto_ruolo_id: int,
        ruolo_applicativo: str,
    ) -> int:
        sql = """
            INSERT INTO anagrafiche.identita_digitali
                   (auth_user_id, soggetto_ruolo_id, ruolo_applicativo,
                    attivo, deve_cambiare_password, storicizza)
            VALUES (%s, %s, %s::config.ruolo_applicativo,
                    true, true, true)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql, [auth_user_id, soggetto_ruolo_id, ruolo_applicativo]
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Genera uno username unico a partire dall'email.
    # Strategia: prefisso email + suffisso _2/_3... se il base esiste.
    # Fallback completo all'email se il prefisso e' vuoto o troppo corto.
    def _build_unique_username(self, email: str) -> str:
        base = (email.split("@", 1)[0] or email).strip().lower()
        if not base:
            base = "user"
        candidate = base
        idx = 2
        while self._username_exists(candidate):
            candidate = f"{base}_{idx}"
            idx += 1
            if idx > 100:
                # Fallback: aggiunge random — il caller vedra' eventuale
                # errore UNIQUE dal DB se persiste.
                import secrets  # noqa: PLC0415
                candidate = f"{base}_{secrets.token_hex(4)}"
                break
        return candidate

    # Scopo: Check esistenza username (case-sensitive come da auth_user).
    def _username_exists(self, username: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM django.auth_user WHERE username = %s LIMIT 1",
                [username],
            )
            return cursor.fetchone() is not None
