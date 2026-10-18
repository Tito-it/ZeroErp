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

# Le colonne di una veste, lette da `get_identita_dettaglio` e
# `get_veste_utilizzabile`: le due letture tornano lo stesso dict.
_SELECT_VESTE = """
            SELECT id,
                   soggetto_ruolo_id,
                   ruolo_applicativo::text AS ruolo_applicativo,
                   attivo,
                   valido_dal,
                   valido_al,
                   invito_inviato_at
              FROM anagrafiche.identita_digitali"""


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

    # Scopo: La credenziale di un'email, senza distinguere maiuscole e
    # minuscole. La regola vive nel DB (`script.fn_get_auth_user_id_for_email`,
    # P-2): la stessa della madre dell'operatore, cosi' portale, shop e
    # operatore riconoscono la stessa persona. Due credenziali con la stessa
    # email → `E_CREDENZIALE_EMAIL_AMBIGUA` dal DB (prima un `LIMIT 1` ne
    # sceglieva una a caso). Email vuota o sconosciuta → None.
    # ⭐ Sede unica (regola del 2, 2026-10-06): la leggono l'invito del
    # portale, il login per email di portale e shop (L-4) e il reset password.
    # Fino a quel giorno stava in `PortaleRepository`.
    def find_auth_user_id_per_email(self, email: str) -> int | None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_get_auth_user_id_for_email(%s)", [email])
            auth_user_id = fetchone_scalar(cursor)
            return int(auth_user_id) if auth_user_id is not None else None

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

    # Scopo: I fatti che servono al cancello degli obblighi (brief sicurezza
    # §3.4-bis, T-0), in UNA andata e ritorno perche' il cancello gira a ogni
    # richiesta col Bearer: il cambio password obbligatorio, l'obbligo del
    # secondo fattore col suo motivo, lo stato del device. Le tre funzioni
    # rispondono sempre con una riga, anche a riga assente: il significato
    # dell'assenza resta loro. Il segreto del device NON si legge qui.
    def get_fatti_obblighi(self, auth_user_id: int) -> dict[str, Any]:
        sql = """
            SELECT script.fn_get_deve_cambiare_password(%(id)s) AS deve_cambiare_password,
                   o.obbligatorio                               AS totp_obbligatorio,
                   o.motivo                                     AS totp_motivo,
                   d.stato                                      AS totp_stato
              FROM script.fn_totp_obbligatorio(%(id)s) o
             CROSS JOIN script.fn_get_totp_device(%(id)s) d
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, {"id": auth_user_id})
            row = row_to_dict(cursor)
        assert row is not None
        return row

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

    # Scopo: Risolve la prima veste UTILIZZABILE dell'utente il cui
    # ruolo_applicativo rientra nei ruoli ammessi dal namespace chiamante
    # (es. ("OPERATORE",) per /admin/token/, ("CLIENTE_PORTALE",
    # "FORNITORE_PORTALE") per /portale/token/).
    # Post modello 1:N: un auth_user puo' avere piu' vesti con
    # ruoli_applicativi diversi; questo helper scopre quale "veste" il
    # namespace sta richiedendo e ritorna solo quella.
    # ⭐ «Utilizzabile» lo decide il DB, `script.fn_veste_utilizzabile`
    #    (brief-db-veste-utilizzabile): accesa, nelle sue date, soggetto attivo
    #    e, per l'operatore umano, rapporto attivo e nelle sue date. Il Python
    #    non riscrive la regola e non calcola date. Fra le vesti della porta si
    #    prende la prima utilizzabile: una scaduta non copre una valida.
    # Ritorna None se l'utente non ha alcuna veste utilizzabile per i ruoli
    # richiesti (la view tradurra' in 403 E_VESTE_NON_ATTIVA: spenta e fuori
    # date hanno lo stesso esito, D-4).
    #
    # Invariante: per un singolo (auth_user_id, namespace) il risultato e'
    # atteso UNIVOCO. `ORDER BY id LIMIT 1` garantisce deterministicita' (la
    # piu' vecchia) se dovessero comunque coesistere piu' vesti utilizzabili
    # con ruoli in `ruoli_applicativi` diversi — stato da considerarsi anomalo.
    def find_veste_utilizzabile_per_ruoli(
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
               AND ruolo_applicativo::text = ANY(%s)
               AND script.fn_veste_utilizzabile(id)
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
    # ⛔ E' una LETTURA, non dice se la veste vale: per quello
    #    `get_veste_utilizzabile`.
    def get_identita_dettaglio(
        self, identita_id: int, auth_user_id: int
    ) -> dict[str, Any] | None:
        # NB: auth_user_id non viene ritornato nel dict (e' gia' esposto
        # altrove nel /me/ via `profile.utente.auth_user_id`); filtra
        # solo come guard anti-tampering.
        sql = f"""
            {_SELECT_VESTE}
             WHERE id = %s AND auth_user_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [identita_id, auth_user_id])
            return row_to_dict(cursor)

    # Scopo: La veste di una sessione, se e' della credenziale ed e'
    # UTILIZZABILE oggi (`script.fn_veste_utilizzabile`); altrimenti None.
    # E' la sola domanda «questa veste lascia ancora lavorare?» per i punti
    # che la fanno a sessione aperta: refresh, secondo passo del secondo
    # fattore, cambio password. Ogni richiesta la fa in `set_jwt_gucs`, che
    # chiama lo stesso building block dentro la sua query.
    # ⚠️ Un guasto della lettura PROPAGA: non e' una prova che la veste valga.
    def get_veste_utilizzabile(
        self, identita_id: int, auth_user_id: int
    ) -> dict[str, Any] | None:
        sql = f"""
            {_SELECT_VESTE}
             WHERE id = %s AND auth_user_id = %s
               AND script.fn_veste_utilizzabile(id)
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

    # Scopo: Nome, cognome, username di una credenziale e la ragione sociale
    # completa del suo soggetto (stringhe, mai None), per le variabili e il
    # saluto delle email. None se la credenziale non esiste.
    # Il soggetto: quello della veste OPERATORE (la persona), poi delle vesti
    # attive, a parita' la veste piu' vecchia. Senza vesti: stringa vuota.
    # Tabelle senza RLS: vale anche dalle richieste anonime (reset password).
    def get_nomi_credenziale(self, auth_user_id: int) -> dict[str, str] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT au.first_name, au.last_name, au.username,
                       (SELECT s.ragione_sociale_completa
                          FROM anagrafiche.identita_digitali idg
                          JOIN anagrafiche.soggetti_ruoli sr ON sr.id = idg.soggetto_ruolo_id
                          JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
                         WHERE idg.auth_user_id = au.id
                         ORDER BY (idg.ruolo_applicativo::text = 'OPERATORE') DESC,
                                  idg.attivo DESC, idg.id
                         LIMIT 1)
                  FROM django.auth_user au
                 WHERE au.id = %s
                """,
                [auth_user_id],
            )
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "first_name": row[0] or "",
            "last_name": row[1] or "",
            "username": row[2] or "",
            "ragione_sociale_completa": (row[3] or "").strip(),
        }

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
        # Dal 2026-10-18 (2b-2) la madre del DB `anagrafiche.fn_accendi_veste`:
        # stesso filtro (credenziale e vesti ammesse), una veste gia' accesa
        # resta com'e', l'audit lo scrivono i trigger. Era la terza copia
        # dell'UPDATE, con il builder pgTAP e il provisioning di sviluppo.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT anagrafiche.fn_accendi_veste("
                "%s::bigint, %s::integer, %s::config.ruolo_applicativo[])",
                [identita_id, auth_user_id, list(ruoli_applicativi)],
            )
            row = cursor.fetchone()
        return bool(row and row[0])

    # Scopo: Imposta l'obbligo di cambio password della CREDENZIALE (D-7).
    # Chiamanti: cambio/reset/attivazione (False).
    # Credenziale inesistente → E_CREDENZIALE_NON_TROVATA dal DB.
    def set_deve_cambiare_password(self, auth_user_id: int, valore: bool) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_imposta_deve_cambiare_password(%s, %s)",
                [auth_user_id, valore],
            )
