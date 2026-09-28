# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per auth_user (Django).
# Chiama anagrafiche.fn_crea_auth_user per creare un utente
# Django con guard unicita' username/email.
# Gestisce anche lo stato della credenziale (config.credenziali, P-1 del
# brief-db-blocco-login-per-credenziale): freno sui tentativi falliti per
# credenziale + provenienza, attesa crescente, cambio password obbligatorio.
# Per un nome che non trova una credenziale lo stesso freno vale sul nome
# tentato (config.nomi_tentati, R-7 §13): la chiave la sceglie il DB.
# ⛔ Nessun SQL diretto su quelle tabelle (chiuse all'app in scrittura): solo
# le funzioni del DB, che sono la sede unica di «riga assente = niente stato».
# Riusabile da qualsiasi dominio che necessiti un utente Django.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from django.contrib.auth.hashers import is_password_usable
from django.db import connection

from apps.core.db._helpers import fetchone_scalar, jsonb_out, row_to_dict, rows_to_list


class AuthRepository:
    """Building block: operazioni atomiche su auth_user."""

    # Scopo: Crea un auth_user Django invocando fn_crea_auth_user.
    # Ritorna auth_user.id. Guard unicita' username/email nel DB.
    def crea_auth_user(
        self,
        *,
        username: str,
        email: str,
        password_hash: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> int:
        sql = """
            SELECT anagrafiche.fn_crea_auth_user(
                p_username      := %s,
                p_email         := %s,
                p_password_hash := %s,
                p_first_name    := %s,
                p_last_name     := %s
            )
        """
        params = [username, email, password_hash, first_name, last_name]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return fetchone_scalar(cursor)

    # Scopo: Dice se il nome tentato puo' provare ad entrare da questa provenienza.
    # Solleva dal DB, nell'ordine: E_CREDENZIALE_BLOCCATA (blocco dell'admin),
    # E_UTENTE_BLOCCATO (freno su questa provenienza), E_LOGIN_ATTESA (attesa
    # crescente). La chiave la sceglie il DB (R-7, brief §13.1): la credenziale
    # se `auth_user_id` c'e', altrimenti l'impronta del nome — quindi si chiama
    # SEMPRE, anche per un nome che non trova niente. `nome_digest` = 32 byte
    # (`nome_tentato.digest_nome_tentato`), obbligatorio anche con la
    # credenziale; `provenienza` = IP fidato del chiamante (`get_client_ip`),
    # obbligatorio: il DB rifiuta NULL.
    def check_blocco_login(
        self, auth_user_id: int | None, *, nome_digest: bytes, provenienza: str,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_check_blocco_login(%s, %s::bytea, %s::inet)",
                [auth_user_id, nome_digest, provenienza],
            )

    # Scopo: Registra l'esito di un tentativo di login per chiave + provenienza.
    # Successo → azzera la credenziale e la SOLA coppia da cui si e' entrati
    # (un successo senza credenziale e' una chiamata non valida).
    # Fallimento → conta sulla coppia (freno) e sulla chiave (attesa): la
    # credenziale se c'e', altrimenti il nome tentato, con gli stessi numeri.
    # Ritorna { bloccato, minuti_rimanenti, tentativi, attesa_secondi }.
    def registra_tentativo_login(
        self,
        auth_user_id: int | None,
        *,
        nome_digest: bytes,
        provenienza: str,
        successo: bool,
    ) -> dict:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_registra_tentativo_login(%s, %s::bytea, %s::inet, %s)",
                [auth_user_id, nome_digest, provenienza, successo],
            )
            row = cursor.fetchone()
            if not row or not row[0]:
                return {
                    "bloccato": False, "minuti_rimanenti": 0,
                    "tentativi": 0, "attesa_secondi": 0,
                }
            # ⛔ `jsonb_out` e NON `coerce_jsonb_dict`, ed e' una scelta di
            #    SICUREZZA. Questo esito decide se un account e' bloccato, e il
            #    chiamante lo legge con `result.get("bloccato")`: il ripiego a
            #    `{}` del gemello darebbe `None` — cioe' «non bloccato» — su un
            #    JSON che non si e' saputo leggere. Un fail-OPEN silenzioso su
            #    un percorso di autenticazione. Qui un decode error deve
            #    esplodere: il login si rifiuta, che e' il verso giusto.
            return jsonb_out(row[0])

    # Scopo: Azzera i tentativi falliti della credenziale su TUTTE le provenienze
    # (D-2): lo chiama il reset password riuscito. Non tocca il blocco
    # dell'admin (D-B3) ne' il cambio password obbligatorio. L'accesso
    # riuscito non passa di qui: lo fa `registra_tentativo_login(successo=True)`
    # sulla sola coppia da cui si e' entrati.
    def azzera_tentativi_credenziale(self, auth_user_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_azzera_tentativi_credenziale(%s)",
                [auth_user_id],
            )

    # Scopo: Legge l'obbligo di cambio password della CREDENZIALE (D-7):
    # la password e' una sola, per tutte le vesti. Riga assente = False,
    # e quel default vive solo nella funzione del DB.
    def get_deve_cambiare_password(self, auth_user_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_get_deve_cambiare_password(%s)",
                [auth_user_id],
            )
            return bool(fetchone_scalar(cursor))

    # Scopo: Recupera unita_organizzativa_id dell'operatore via helper DB
    # script.fn_get_uo_id_for_user (post multi-face §13.3.7).
    def get_unita_organizzativa_id(self, auth_user_id: int) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_get_uo_id_for_user(%s)",
                [auth_user_id],
            )
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else None

    # Scopo: Aggiorna invito_inviato_at sull'identita digitale specifica
    # del flusso corrente (post modello 1:N §8.4.1).
    # `identita_id` obbligatorio: con modello 1:N lo stesso auth_user puo'
    # essere stato invitato a piu' "vesti" in momenti diversi; il timestamp
    # di invito va scritto sulla riga che si sta effettivamente invitando,
    # non su una qualunque. Il filtro auth_user_id resta come guard
    # anti-tampering. Non filtra piu' su `attivo=true`: durante il flusso
    # cross-veste (§8.4.1) l'identita e' creata `attivo=false` e il
    # timestamp va comunque scritto per audit.
    def set_invito_inviato_at(
        self, auth_user_id: int, *, identita_id: int
    ) -> bool:
        sql = """
            UPDATE anagrafiche.identita_digitali
               SET invito_inviato_at = now(), data_update = now()
             WHERE id = %s
               AND auth_user_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [identita_id, auth_user_id])
            return cursor.rowcount > 0

    # Scopo: Risolve la prima identita digitale attiva dell'utente il cui
    # ruolo_applicativo rientra nei ruoli ammessi dal namespace chiamante
    # (es. ("OPERATORE",) per /admin/token/, ("CLIENTE_PORTALE",
    # "FORNITORE_PORTALE") per /portale/token/).
    # Post modello 1:N: un auth_user puo' avere piu' identita attive con
    # ruoli_applicativi diversi; questo helper scopre quale "veste" il
    # namespace sta richiedendo e ritorna solo quella.
    # Ritorna None se l'utente non ha alcuna identita attiva per i ruoli
    # richiesti (la view tradurra' in 403 E_VESTE_NON_ATTIVA).
    #
    # Invariante: per un singolo (auth_user_id, namespace) il risultato e'
    # atteso UNIVOCO. Il modello multi-face assegna un auth_user dedicato
    # per ogni identita, quindi la probabilita' di collisione e' bassa.
    # `ORDER BY id LIMIT 1` garantisce deterministicita' (la piu' vecchia)
    # se dovessero comunque coesistere piu' identita attive con ruoli in
    # `ruoli_applicativi` diversi — stato da considerarsi anomalo.
    def find_identita_attiva_for_ruoli(
        self,
        auth_user_id: int,
        ruoli_applicativi: Sequence[str],
    ) -> dict[str, Any] | None:
        # Short-circuit: senza ruoli ammessi non esiste veste valida;
        # ritorna None senza toccare il DB (evita anche `ANY(ARRAY[]::text[])`
        # che richiederebbe cast esplicito sull'enum Postgres).
        if not ruoli_applicativi:
            return None
        sql = """
            SELECT id,
                   soggetto_ruolo_id,
                   ruolo_applicativo::text AS ruolo_applicativo
              FROM anagrafiche.identita_digitali
             WHERE auth_user_id = %s
               AND attivo = true
               AND ruolo_applicativo::text = ANY(%s)
             ORDER BY id
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id, list(ruoli_applicativi)])
            return row_to_dict(cursor)

    # Scopo: Ritorna i dettagli di una singola identita digitale per
    # l'auth_user specificato. Post modello 1:N: /me/ (§8.3.6) usa questo
    # helper per esporre solo la "veste" del JWT corrente invece di
    # risolvere ambiguamente una delle N identita attive dell'utente.
    # Il filtro auth_user_id e' guard anti-tampering (defense-in-depth):
    # se un client passasse un identita_id altrui (non ha senso con JWT
    # firmato, ma comunque) non riceverebbe dati di altri utenti.
    def get_identita_dettaglio(
        self, identita_id: int, auth_user_id: int
    ) -> dict[str, Any] | None:
        # NB: auth_user_id non viene ritornato nel dict (e' gia' esposto
        # altrove nel /me/ via `profile.utente.auth_user_id`); filtra
        # solo come guard anti-tampering.
        sql = """
            SELECT id,
                   soggetto_ruolo_id,
                   ruolo_applicativo::text AS ruolo_applicativo,
                   attivo,
                   valido_dal,
                   valido_al,
                   invito_inviato_at
              FROM anagrafiche.identita_digitali
             WHERE id = %s AND auth_user_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [identita_id, auth_user_id])
            return row_to_dict(cursor)

    # Scopo: Le vesti di una credenziale per un ruolo, attive o spente, in
    # ordine di id. Serve all'invito, che lavora su una veste SPENTA (regola
    # unica: la veste nasce spenta e la accende l'attivazione). Una lista, non
    # «la prima»: il modello ammette piu' vesti spente sullo stesso ruolo
    # (l'unique vale solo WHERE attivo), e decide il chiamante cosa farne.
    def find_identita_per_ruolo(
        self, auth_user_id: int, ruolo_applicativo: str
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT id,
                   soggetto_ruolo_id,
                   ruolo_applicativo::text AS ruolo_applicativo,
                   attivo
              FROM anagrafiche.identita_digitali
             WHERE auth_user_id = %s
               AND ruolo_applicativo::text = %s
             ORDER BY id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id, ruolo_applicativo])
            return rows_to_list(cursor)

    # Scopo: Nome, cognome e username di una credenziale (stringhe, mai None),
    # per le variabili delle email d'invito. None se la credenziale non esiste.
    def get_nomi_credenziale(self, auth_user_id: int) -> dict[str, str] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT first_name, last_name, username FROM django.auth_user WHERE id = %s",
                [auth_user_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return {"first_name": row[0] or "", "last_name": row[1] or "", "username": row[2] or ""}

    # Scopo: Dice se la credenziale ha una password VERA, cioe' scelta dalla
    # persona (attivando un invito, col reset, col cambio). E' il
    # discriminante dei due flussi d'invito, uguale per ogni veste: senza →
    # la persona la sceglie all'attivazione; con → attiva con un clic. Una
    # credenziale nata da un invito o dalla creazione dell'operatore ha il
    # segnaposto non utilizzabile, e lo tiene finche' non si attiva.
    def auth_user_ha_password(self, auth_user_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT password FROM django.auth_user WHERE id = %s",
                [auth_user_id],
            )
            row = cursor.fetchone()
        return bool(row) and is_password_usable(row[0])

    # Scopo: Accende la veste di un invito, al consumo del token. Il filtro su
    # credenziale e ruolo e' il guard: l'`identita_id` viene dal meta del
    # token, e una veste di un'altra credenziale o di un'altra porta non si
    # accende da qui. Ritorna False se nessuna riga corrisponde (veste
    # rimossa, o token che non le appartiene): il chiamante annulla.
    def attiva_identita(
        self,
        identita_id: int,
        *,
        auth_user_id: int,
        ruoli_applicativi: Sequence[str],
    ) -> bool:
        sql = """
            UPDATE anagrafiche.identita_digitali
               SET attivo = true, data_update = now()
             WHERE id = %s
               AND auth_user_id = %s
               AND ruolo_applicativo::text = ANY(%s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [identita_id, auth_user_id, list(ruoli_applicativi)])
            return cursor.rowcount > 0

    # Scopo: Imposta l'obbligo di cambio password della CREDENZIALE (D-7).
    # Chiamanti: cambio/reset/attivazione (False).
    # Credenziale inesistente → E_CREDENZIALE_NON_TROVATA dal DB.
    def set_deve_cambiare_password(self, auth_user_id: int, valore: bool) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_imposta_deve_cambiare_password(%s, %s)",
                [auth_user_id, valore],
            )
