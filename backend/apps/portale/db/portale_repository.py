# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
from apps.core.db._helpers import row_to_dict, rows_to_list


# Il tipo di contatto che vince nell'email suggerita dell'invito: per codice
# (config.tipi_contatti.codice), mai per id.
TIPO_CONTATTO_PRINCIPALE = "PRINCIPALE"


class PortaleRepository:
    """Accesso DB per invito portale + creazione identita portale."""

    # Scopo: L'email da proporre nell'invito al portale, presa dai contatti
    #        del ruolo. I candidati li sceglie il BB del DB
    #        `script.fn_get_contatti` (un contatto per tipo: ruolo+istanza,
    #        poi ruolo, poi soggetto); qui si sceglie tra i tipi: prima il
    #        contatto PRINCIPALE, poi IL predefinito del BB
    #        `script.fn_get_contatto_default`. Nessuno dei due con email: None.
    # ⭐ Dal 2026-11-26 il predefinito lo sceglie il BB: ogni contesto ha il
    #    suo (brief-db-revisione-anagrafiche §22, D-T7b-4), e fra quello del
    #    ruolo e quello del soggetto vince il piu' specifico. Prima l'ORDER BY
    #    locale prendeva il predefinito con l'id piu' basso, cioe' di solito
    #    quello del SOGGETTO: l'invito andava a un'altra persona.
    # ⚠️ Il predefinito piu' specifico senza email NON ripiega su quello di un
    #    contesto meno specifico (Tid, 2026-11-26), e un contatto di un altro
    #    tipo, non predefinito, non si propone (Tid, 2026-11-21): l'operatore
    #    scrive l'email.
    def get_email_contatto_suggerita(
        self, soggetto_id: str, soggetto_ruolo_id: int,
    ) -> str | None:
        sql = """
            SELECT email FROM (
                SELECT NULLIF(btrim(c.email), '') AS email, 1 AS ordine
                  FROM script.fn_get_contatti(%s::uuid, %s::bigint) c
                  JOIN config.tipi_contatti tc ON tc.id = c.tipo_contatto_id
                 WHERE tc.codice = %s
                UNION ALL
                SELECT NULLIF(btrim(d.email), ''), 2
                  FROM script.fn_get_contatto_default(%s::uuid, %s::bigint) d
            ) candidati
             WHERE email IS NOT NULL
             ORDER BY ordine
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                str(soggetto_id), soggetto_ruolo_id, TIPO_CONTATTO_PRINCIPALE,
                str(soggetto_id), soggetto_ruolo_id,
            ])
            row = cursor.fetchone()
        return row[0] if row else None

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
                   s.codice_fiscale             AS codice_fiscale
              FROM anagrafiche.fornitori f
              JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.soggetto_ruolo_id
              JOIN anagrafiche.soggetti s        ON s.id = sr.soggetto_id
             WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [fornitore_id])
            return row_to_dict(cursor)

    # Scopo: La veste di UNA credenziale su un soggetto, per tipo: la terna
    #        (credenziale, ruolo anagrafico, tipo) che il DB rende unica sulle
    #        vesti accese (`uq_identita_digitali_credenziale_sr_ruolo_attivo`,
    #        giro 4 del brief-db-accessi-area-clienti, D-M7 e D-M8). La usano
    #        l'invito (la veste da creare o da reinvitare) e l'attivazione
    #        dello shop dal portale (la veste della persona della sessione).
    #        Ritorna `{identita_id, auth_user_id, attivo}` o None.
    # ⭐ Fino al 2026-11-28 si cercava per (ruolo anagrafico, tipo), e la veste
    #    di un altro referente dello stesso cliente era un errore («collegata a
    #    un altro utente»): era il divieto che D-M7 ha ritirato. Cercando per
    #    credenziale, la veste di un'altra persona non si trova per costruzione.
    # ⚠️ Accese ce n'e' al piu' una (l'indice); spente il modello ne ammette
    #    piu' d'una sulla stessa terna: vince l'accesa, poi la piu' recente.
    def find_veste_credenziale(
        self, auth_user_id: int, soggetto_ruolo_id: int, ruolo_applicativo: str,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT id               AS identita_id,
                   auth_user_id,
                   attivo
              FROM anagrafiche.identita_digitali
             WHERE auth_user_id = %s
               AND soggetto_ruolo_id = %s
               AND ruolo_applicativo = %s::config.ruolo_applicativo
             ORDER BY attivo DESC, id DESC
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id, soggetto_ruolo_id, ruolo_applicativo])
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

    # Scopo: I REFERENTI di un soggetto per un tipo di veste, per la scheda
    #        accessi del cliente e del fornitore: una voce per veste, anche
    #        spenta, in ordine di nascita. Con `identita_id` la voce di quella
    #        veste sola, se e' di questo soggetto e di questo tipo (la
    #        disattivazione di un referente): lista vuota altrimenti.
    #        Ogni voce: `identita_id`, `auth_user_id`, `username`, `email`,
    #        `stato` e `token_scade_at` (`script.fn_stato_veste`),
    #        `utilizzabile` (`script.fn_veste_utilizzabile`), `attivo`,
    #        `valido_dal`, `valido_al`, `invito_inviato_at`.
    # ⭐ Un elenco dal 2026-11-28 (giro 4, D-M7): un cliente o un fornitore ha
    #    piu' referenti, ognuno con la sua veste. Fino ad allora la lettura
    #    prendeva «la veste del ruolo e tipo» con `LIMIT 1`, e lo stato
    #    `NESSUNO` era del BE: ora la veste che non c'e' e' l'elenco vuoto.
    # ⛔ LO STATO E LA PORTA SI CALCOLANO SOLO A DB (A-7; D-G3-1 del giro 3):
    #    le stesse due funzioni servono la lista «Altri accessi»
    #    (`anagrafiche.vw_accessi_altri`). Sono due domande: lo stato e' il
    #    ciclo di vita dell'invito e della revoca, `utilizzabile` dice se la
    #    veste apre la porta oggi (una veste `ATTIVO` fuori dalle sue date no).
    # ⚠️ Il token della veste lo riconosce `fn_stato_veste` dall'`identita_id`
    #    nel meta (§7.4 del brief area accessi): lo scrive solo l'emissione di
    #    un invito (`InvitoVeste.emetti`).
    def list_referenti(
        self,
        soggetto_ruolo_id: int,
        ruolo_applicativo: str,
        *,
        identita_id: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT idg.id               AS identita_id,
                   idg.auth_user_id,
                   u.username,
                   u.email,
                   sv.stato,
                   sv.token_scade_at,
                   script.fn_veste_utilizzabile(idg.id) AS utilizzabile,
                   idg.attivo,
                   idg.valido_dal,
                   idg.valido_al,
                   idg.invito_inviato_at
              FROM anagrafiche.identita_digitali idg
              CROSS JOIN LATERAL script.fn_stato_veste(idg.id) sv
              LEFT JOIN django.auth_user u ON u.id = idg.auth_user_id
             WHERE idg.soggetto_ruolo_id = %s
               AND idg.ruolo_applicativo = %s::config.ruolo_applicativo
               AND (%s::bigint IS NULL OR idg.id = %s::bigint)
             ORDER BY idg.id
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql, [soggetto_ruolo_id, ruolo_applicativo, identita_id, identita_id],
            )
            return rows_to_list(cursor)

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
