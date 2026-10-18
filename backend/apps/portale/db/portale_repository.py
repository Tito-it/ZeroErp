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
from apps.core.db._helpers import row_to_dict


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
            return row_to_dict(cursor)

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
            return row_to_dict(cursor)

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
                   invito_inviato_at
              FROM anagrafiche.identita_digitali
             WHERE soggetto_ruolo_id = %s
               AND ruolo_applicativo = %s::config.ruolo_applicativo
             ORDER BY attivo DESC, id DESC
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_ruolo_id, ruolo_applicativo])
            return row_to_dict(cursor)

    # Scopo: Crea una nuova riga auth_user per un portale user.
    # Username derivato da email (prefisso prima della @), con suffisso
    # progressivo se gia' esistente. is_active=true: se la persona entra lo
    # decide la veste (`identita_digitali.attivo`).
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
    # ruolo_applicativo x tipo soggetto.
    # Parametro `attivo` OBBLIGATORIO kw-only (no default, §8.4.1 FRAG9): un
    # default implicito sarebbe security-risky (un futuro caller che lo
    # dimentica creerebbe accidentalmente identita attiva). Oggi l'invito la
    # crea `False` in tutti e due i flussi: l'identita si attiva al consumo
    # del token (M-3, 2026-09-24). Il cambio password obbligatorio non e'
    # della veste ma della credenziale (D-7, `config.credenziali`).
    def create_identita_portale(
        self,
        *,
        auth_user_id: int,
        soggetto_ruolo_id: int,
        ruolo_applicativo: str,
        attivo: bool,
    ) -> int:
        # ⭐ Dal 2026-10-18 (2b-2, lotto 6) la madre del DB
        #    `anagrafiche.fn_crea_veste_portale`: solo le tre vesti esterne,
        #    `attivo` senza default (l'invito la crea spenta, lo shop accesa).
        #    La veste OPERATORE ha le sue madri.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT anagrafiche.fn_crea_veste_portale("
                "%s::integer, %s::bigint, %s::config.ruolo_applicativo, %s::boolean)",
                [auth_user_id, soggetto_ruolo_id, ruolo_applicativo, attivo],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Disattiva un'identita senza eliminarla (soft revoke). Il verso
    # opposto e' `AuthRepository.attiva_identita`, al consumo di un nuovo
    # invito. Serve all'admin per revocare una veste portale o shop a un
    # cliente/fornitore senza perdere lo storico.
    # Ritorna True se ha effettivamente aggiornato una riga (identita esisteva
    # e attivo era true o comunque la UPDATE e' passata).
    def disattiva_identita(self, identita_id: int) -> bool:
        sql = """
            UPDATE anagrafiche.identita_digitali
               SET attivo = false, data_update = now()
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [identita_id])
            return cursor.rowcount > 0

    # Scopo: Legge lo stato accessi di una veste (per una data coppia
    # soggetto_ruolo + ruolo_applicativo) per l'admin UI:
    #   NESSUNO     : la veste non esiste (mai invitato) — del BE, perche'
    #                 non e' uno stato di una veste ma l'assenza della riga
    #   ATTIVO · PENDING · NON_SPEDITO · DISATTIVO : di `script.fn_stato_veste`
    # ⛔ LO STATO DI UNA VESTE SI CALCOLA SOLO A DB (A-7, brief-db-be-fe-area-
    #    accessi): la stessa funzione serve questa scheda e la lista «Altri
    #    accessi» (`anagrafiche.vw_accessi_altri`). Fino al 2026-10-02 la
    #    regola stava qui (`stato_veste`, con la CTE del token pendente), e la
    #    lista l'avrebbe riscritta: due copie che rispondono in due modi.
    # ⚠️ Una differenza col calcolo di prima, dichiarata dal team DB (§7.4):
    #    il token della veste si riconosce dall'`identita_id` nel meta, senza
    #    filtrare il TIPO del token sulle due della porta. Lo scrive solo
    #    l'emissione di un invito (`InvitoVeste.emetti`); il reset password
    #    no. Il punto da guardare: un token non d'invito che porti
    #    `identita_id`.
    # Ritorna dict con chiavi:
    #   stato (str), identita_id (int|None), auth_user_id (int|None),
    #   username, email, invito_inviato_at (datetime|None),
    #   token_scade_at (datetime|None: scadenza del token pendente piu'
    #   lontano, per «scade tra N ore»).
    def get_stato_identita(
        self, soggetto_ruolo_id: int, ruolo_applicativo: str,
    ) -> dict[str, Any]:
        sql = """
            WITH id_row AS (
                SELECT id, auth_user_id, invito_inviato_at
                  FROM anagrafiche.identita_digitali
                 WHERE soggetto_ruolo_id = %s
                   AND ruolo_applicativo = %s::config.ruolo_applicativo
                 ORDER BY attivo DESC, id DESC
                 LIMIT 1
            )
            SELECT r.id, r.auth_user_id, r.invito_inviato_at,
                   sv.stato, sv.token_scade_at,
                   u.username, u.email
              FROM id_row r
              CROSS JOIN LATERAL script.fn_stato_veste(r.id) sv
              LEFT JOIN django.auth_user u ON u.id = r.auth_user_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_ruolo_id, ruolo_applicativo])
            row = cursor.fetchone()

        if not row:
            return {
                "stato": "NESSUNO",
                "identita_id": None,
                "auth_user_id": None,
                "username": None,
                "email": None,
                "invito_inviato_at": None,
                "token_scade_at": None,
            }

        (
            identita_id, auth_user_id, invito_at,
            stato, token_scade_at, username, email,
        ) = row
        return {
            "stato": stato,
            "identita_id": int(identita_id),
            "auth_user_id": int(auth_user_id) if auth_user_id is not None else None,
            "username": username,
            "email": email,
            "invito_inviato_at": invito_at,
            "token_scade_at": token_scade_at,
        }

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
                import secrets
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
