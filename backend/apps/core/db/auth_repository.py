# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per auth_user (Django).
# Chiama anagrafiche.fn_crea_auth_user per creare un utente
# Django con guard unicita' username/email.
# Gestisce anche il blocco login per tentativi falliti
# (fn_check_blocco_login, fn_registra_tentativo_login).
# Riusabile da qualsiasi dominio che necessiti un utente Django.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from django.db import connection

from apps.core.db._helpers import fetchone_scalar, jsonb_out


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

    # Scopo: Verifica se l'utente e' bloccato per tentativi falliti.
    # Lancia errore DB (E_UTENTE_BLOCCATO) se blocco attivo.
    # Se blocco scaduto, lo resetta automaticamente.
    def check_blocco_login(self, auth_user_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_check_blocco_login(%s)",
                [auth_user_id],
            )

    # Scopo: Registra esito tentativo login (successo/fallimento).
    # Se fallimento supera soglia, imposta blocco temporaneo.
    # Ritorna { bloccato, minuti_rimanenti, tentativi }.
    def registra_tentativo_login(self, auth_user_id: int, *, successo: bool) -> dict:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_registra_tentativo_login(%s, %s)",
                [auth_user_id, successo],
            )
            row = cursor.fetchone()
            if not row or not row[0]:
                return {"bloccato": False, "minuti_rimanenti": 0, "tentativi": 0}
            # ⛔ `jsonb_out` e NON `coerce_jsonb_dict`, ed e' una scelta di
            #    SICUREZZA. Questo esito decide se un account e' bloccato, e il
            #    chiamante lo legge con `result.get("bloccato")`: il ripiego a
            #    `{}` del gemello darebbe `None` — cioe' «non bloccato» — su un
            #    JSON che non si e' saputo leggere. Un fail-OPEN silenzioso su
            #    un percorso di autenticazione. Qui un decode error deve
            #    esplodere: il login si rifiuta, che e' il verso giusto.
            return jsonb_out(row[0])

    # Scopo: Legge il flag deve_cambiare_password dell'identita digitale
    # puntata dal JWT della sessione corrente (post modello 1:N §8.4.1).
    # `identita_id` kw-only opzionale:
    # - valorizzato: filtra sulla veste specifica (caso tipico: flussi
    #   autenticati che hanno il claim nel JWT). Pattern "puntare la
    #   veste specifica" allineato a `set_jwt_gucs` §8.3.4 e
    #   `get_identita_dettaglio` §8.3.6. Il filtro auth_user_id resta come
    #   guard anti-tampering.
    # - None: fallback legacy pre-1:N (prende la prima identita attiva).
    #   Accettabile solo per flussi non autenticati o cross-veste
    #   dell'auth_user (es. check middleware in contesti senza JWT
    #   validato). Da evitare nei nuovi caller.
    def get_deve_cambiare_password(
        self, auth_user_id: int, *, identita_id: int | None = None
    ) -> bool:
        if identita_id is not None:
            sql = """
                SELECT deve_cambiare_password
                  FROM anagrafiche.identita_digitali
                 WHERE id = %s
                   AND auth_user_id = %s
                   AND attivo = true
            """
            params: list[Any] = [identita_id, auth_user_id]
        else:
            sql = """
                SELECT deve_cambiare_password
                  FROM anagrafiche.identita_digitali
                 WHERE auth_user_id = %s
                   AND attivo = true
                 LIMIT 1
            """
            params = [auth_user_id]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return bool(row[0]) if row else False

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
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description or []]
            return dict(zip(cols, row))

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
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c.name for c in cursor.description or []]
            return dict(zip(cols, row))

    # Scopo: Imposta il flag deve_cambiare_password. Due semantiche in base
    # a `identita_id` kw-only (post modello 1:N §8.4.1):
    # - `identita_id` valorizzato: aggiorna SOLO la veste specifica.
    #   Usato da invito operatore/portale (§8.4.1), cambio password
    #   autenticato (flag resettato per la veste corrente), attivazione
    #   invito (flag resettato per la veste appena attivata). Il filtro
    #   auth_user_id resta come guard anti-tampering. Non filtra su
    #   `attivo=true`: durante l'invito cross-veste l'identita e'
    #   `attivo=false` al momento del set flag.
    # - `identita_id` None: aggiorna TUTTE le identita attive dell'utente.
    #   Semantica "globale": usata dal password reset self-service
    #   (l'utente ha dimenticato la password, al reset rientra su tutte
    #   le vesti attive senza dover cambiare password di nuovo).
    def set_deve_cambiare_password(
        self, auth_user_id: int, valore: bool, *, identita_id: int | None = None
    ) -> bool:
        if identita_id is not None:
            sql = """
                UPDATE anagrafiche.identita_digitali
                   SET deve_cambiare_password = %s, data_update = now()
                 WHERE id = %s
                   AND auth_user_id = %s
            """
            params: list[Any] = [valore, identita_id, auth_user_id]
        else:
            sql = """
                UPDATE anagrafiche.identita_digitali
                   SET deve_cambiare_password = %s, data_update = now()
                 WHERE auth_user_id = %s
                   AND attivo = true
            """
            params = [valore, auth_user_id]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0
