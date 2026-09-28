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

from datetime import datetime
from typing import Any

from django.db import connection


# Scopo: Lo stato accessi di una veste che ESISTE, dai suoi quattro fatti
# (vedi `PortaleRepository.get_stato_identita` per il significato). Funzione
# pura: il caso «link pendente, email mai partita» si prova costruendolo.
def stato_veste(
    *,
    attivo: bool,
    token_scade_at: datetime | None,
    token_emesso_at: datetime | None,
    invito_inviato_at: datetime | None,
) -> str:
    if attivo:
        return "ATTIVO"
    if token_scade_at is None:
        return "DISATTIVO"
    spedito = (
        invito_inviato_at is not None
        and token_emesso_at is not None
        and invito_inviato_at >= token_emesso_at
    )
    return "PENDING" if spedito else "NON_SPEDITO"


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
            return dict(zip(cols, row, strict=True))

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
            return dict(zip(cols, row, strict=True))

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
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description or []]
            return dict(zip(cols, row, strict=True))

    # Scopo: La credenziale di un'email, senza distinguere maiuscole e
    # minuscole. La regola vive nel DB (`script.fn_get_auth_user_id_for_email`,
    # P-2): la stessa della madre dell'operatore, cosi' portale e operatore
    # riconoscono la stessa persona. Due credenziali con la stessa email →
    # `E_CREDENZIALE_EMAIL_AMBIGUA` dal DB (prima un `LIMIT 1` ne sceglieva
    # una a caso). Email vuota o sconosciuta → None.
    def find_auth_user_by_email(self, email: str) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_get_auth_user_id_for_email(%s)", [email])
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else None

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
        sql = """
            INSERT INTO anagrafiche.identita_digitali
                   (auth_user_id, soggetto_ruolo_id, ruolo_applicativo,
                    attivo, storicizza)
            VALUES (%s, %s, %s::config.ruolo_applicativo,
                    %s, true)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    auth_user_id,
                    soggetto_ruolo_id,
                    ruolo_applicativo,
                    attivo,
                ],
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

    # Scopo: Legge lo stato completo di un'identita (per una data coppia
    # soggetto_ruolo + ruolo_applicativo) decorato con info sul token
    # pendente, se presente. Serve all'admin UI per distinguere 5 stati:
    #   NESSUNO     : identita non esiste (mai invitato)
    #   PENDING     : identita esiste, attivo=false, token non consumato attivo
    #                 E l'email d'invito e' partita DOPO l'emissione di quel token
    #   NON_SPEDITO : come PENDING, ma l'email di quel token non e' partita
    #                 (`invito_inviato_at` nullo o precedente al token)
    #   DISATTIVO   : identita esiste, attivo=false, nessun token pending
    #   ATTIVO      : identita esiste, attivo=true
    # ⭐ NON_SPEDITO (2026-09-28, F-3 dell'analisi difetti doc API core): il
    #    token nasce nell'emissione, l'email parte dopo e fuori transazione, e
    #    `invito_inviato_at` si scrive solo se e' partita. Un token pendente da
    #    solo diceva «invito inviato» anche a email fallita. Si confronta col
    #    token pendente (uno per veste: l'emissione invalida i precedenti), non
    #    col solo `invito_inviato_at` — quello di un invito PRECEDENTE andato a
    #    buon fine non dice niente del link di adesso. `>=`: emissione e
    #    spedizione possono stare nella stessa transazione (stesso `now()`).
    # Ritorna dict con chiavi:
    #   stato (str), identita_id (int|None), auth_user_id (int|None),
    #   invito_inviato_at (datetime|None), token_scade_at (datetime|None).
    # `token_scade_at` e' il `MAX(scadenza)` tra i token non consumati non
    # scaduti della coppia veste (INVITO_PORTALE/ATTIVAZIONE_PORTALE_CROSS
    # o INVITO_SHOP/ATTIVAZIONE_SHOP_CROSS) — usato dalla UI per mostrare
    # "scade tra N ore".
    def get_stato_identita(
        self, soggetto_ruolo_id: int, ruolo_applicativo: str,
        token_tipi: tuple[str, ...],
    ) -> dict[str, Any]:
        sql = """
            WITH id_row AS (
                SELECT id, auth_user_id, attivo, invito_inviato_at
                  FROM anagrafiche.identita_digitali
                 WHERE soggetto_ruolo_id = %s
                   AND ruolo_applicativo = %s::config.ruolo_applicativo
                 ORDER BY attivo DESC, id DESC
                 LIMIT 1
            ),
            tk AS (
                SELECT MAX(t.scadenza) AS token_scade_at,
                       MAX(t.data_insert) AS token_emesso_at
                  FROM config.token_monouso t
                  JOIN id_row r ON r.auth_user_id = t.auth_user_id
                 -- Il token della VESTE, non della credenziale: cliente e
                 -- fornitore portale condividono i tipi di token.
                   AND t.meta ->> 'identita_id' = r.id::text
                 WHERE t.tipo = ANY(%s::text[])
                   AND t.utilizzato = false
                   AND t.scadenza > now()
            )
            SELECT r.id, r.auth_user_id, r.attivo, r.invito_inviato_at,
                   tk.token_scade_at, tk.token_emesso_at,
                   u.username, u.email
              FROM id_row r
              LEFT JOIN tk ON true
              LEFT JOIN django.auth_user u ON u.id = r.auth_user_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_ruolo_id, ruolo_applicativo, list(token_tipi)])
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
            identita_id, auth_user_id, attivo, invito_at,
            token_scade_at, token_emesso_at, username, email,
        ) = row
        stato = stato_veste(
            attivo=attivo, token_scade_at=token_scade_at,
            token_emesso_at=token_emesso_at, invito_inviato_at=invito_at,
        )
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
