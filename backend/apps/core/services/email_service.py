# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio invio email generico per reparto/contesto.
#        Risolve account SMTP e template con fallback,
#        renderizza variabili, invia via SMTP o console (DEBUG),
#        logga ogni invio in config.email_log.
# ------------------------------------------------------------

from __future__ import annotations

import logging
import re
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from django.conf import settings

from apps.core.db.email_repository import EmailRepository
from apps.core.services import crypto_service
from apps.core.services.error_manager import ErrorManager

logger = logging.getLogger("zeroerp.email")

E_EMAIL = "E_EMAIL"

# Marker per account placeholder (seed iniziale senza SMTP reale).
# Esposto come pubblico: consumato anche da `email_views._derive_test_capability`
# (Fase 6). Centralizzare qui evita drift della definizione di "console mode".
SMTP_PLACEHOLDER_HOST = "smtp.example.com"
_SMTP_TIMEOUT_SEND = 30
_SMTP_TIMEOUT_TEST = 10

# ⭐ I TRE CANALI con cui un'email esce, e sono TRE di proposito: fino al
#    2026-09-11 erano DUE — «SMTP» e «console» — e in «console» ci cadevano due
#    situazioni opposte, l'una voluta e l'altra un guasto.
CANALE_SMTP = "SMTP"
CANALE_CONSOLE = "CONSOLE"
CANALE_NON_CONFIGURATO = "NON_CONFIGURATO"


# Scopo: «Questo account PUO' spedire?» — host assente o ancora quello del seed.
# ⛔ E' il predicato che `email_views._derive_test_capability` riscriveva a mano
#    (regola del 2): il commento sopra `SMTP_PLACEHOLDER_HOST` dichiarava di
#    centralizzare la definizione, ma la copia esisteva lo stesso.
def smtp_non_configurato(account: dict[str, Any]) -> bool:
    host = (account.get("smtp_host") or "").strip()
    return not host or host == SMTP_PLACEHOLDER_HOST


# Il messaggio che finisce in `config.email_log.errore`: deve dire che cos'e'
# successo E dove si rimedia, perche' chi lo legge sta guardando il giornale
# delle email e non il codice.
# ⛔ `conseguenza` NON e' un abbellimento: lo stesso predicato serve due percorsi
#    che hanno fatto due cose diverse. Sulla via dell'invio c'e' una mail che non
#    e' partita; sul pulsante «prova connessione» non c'e' nessuna mail — e
#    scriverlo lo stesso, come si e' fatto fino al 2026-09-11, e' un messaggio
#    che afferma un fatto mai avvenuto proprio nella schermata dove una persona
#    lo legge (finisce in `email_account.meta.last_test_message`).
_CONSEGUENZA_INVIO = "L'email NON e' stata spedita."
_CONSEGUENZA_TEST = "Non c'e' nessuna connessione da provare."


def _motivo_non_configurato(
    account: dict[str, Any], *, conseguenza: str = _CONSEGUENZA_INVIO,
) -> str:
    codice = account.get("codice") or account.get("codice_interno") or "?"
    return (
        f"SMTP non configurato per l'account '{codice}': smtp_host vale "
        f"'{account.get('smtp_host') or ''}'. {conseguenza} "
        f"Configurare l'account da Amm. Software → Email accounts."
    )


class EmailDispatchService:
    """Servizio invio email con risoluzione account/template per reparto."""

    def __init__(self) -> None:
        self._repo = EmailRepository()

    # Scopo: Renderizza un template sostituendo le variabili {{chiave}} con i valori.
    def render_template(self, testo: str, variabili: dict[str, Any]) -> str:
        def _replace(match: re.Match) -> str:
            key = match.group(1).strip()
            val = variabili.get(key)
            return str(val) if val is not None else match.group(0)

        return re.sub(r"\{\{(\s*\w+\s*)\}\}", _replace, testo)

    # Scopo: Con quale canale esce DAVVERO questa email: SMTP, console (stampata
    #        a video) oppure nessuno, perche' l'account non e' configurato.
    #
    # ⛔ FINO AL 2026-09-11 I CANALI ERANO DUE, e in «console» cadevano due
    #    situazioni opposte: lo sviluppo dichiarato (`DEBUG`), dove stampare a
    #    video E' il comportamento voluto, e un account rimasto col placeholder
    #    del seed su un host di esercizio, dove e' un GUASTO DI CONFIGURAZIONE.
    #    Entrambe finivano marcate `SENT`, cioe' indistinguibili da una consegna.
    # 🔴 Il caso e' successo davvero: il 2026-09-10 il digest dei presidi e' stato
    #    dichiarato «inviato» su un host con `DEBUG = False` e
    #    `smtp_host = smtp.example.com`, e nessuno avrebbe potuto accorgersene —
    #    il giornale diceva SENT e nessun presidio guarda oltre.
    # ⇒ Il terzo canale non aggiunge un caso: SEPARA due casi che c'erano gia'.
    def canale_invio(self, account: dict[str, Any]) -> str:
        if smtp_non_configurato(account):
            # ⚠️ In DEBUG resta console: senza SMTP lo sviluppo deve poter girare.
            #    Fuori da DEBUG e' configurazione che manca, e si dice.
            return CANALE_CONSOLE if settings.DEBUG else CANALE_NON_CONFIGURATO
        return CANALE_CONSOLE if settings.DEBUG else CANALE_SMTP

    # Scopo: Determina se un account e' in console mode (stampa a video).
    # ⚠️ Resta come nome storico e delega al canale: NON risponde piu' vero su un
    #    account col placeholder fuori da DEBUG — li' il canale e' `NON_CONFIGURATO`.
    def is_console_mode(self, account: dict[str, Any]) -> bool:
        return self.canale_invio(account) == CANALE_CONSOLE

    # Scopo: Risolve template e account con fallback, renderizza le variabili.
    #        Usato da send_email e da EmailOutboxService.prepare_draft.
    #        Ritorna (template, account, oggetto, corpo_html, corpo_testo).
    def resolve_and_render(
        self,
        *,
        codice_template: str,
        variabili: dict[str, Any],
        unita_organizzativa_id: int | None = None,
        tipo_prestazione_id: int | None = None,
        lingua: str = "it",
        error_code: str = E_EMAIL,
    ) -> tuple[dict[str, Any], dict[str, Any], str, str, str | None]:
        # 1. Risolvi template con fallback
        template = self._repo.resolve_template(
            codice_template,
            unita_organizzativa_id=unita_organizzativa_id,
            tipo_prestazione_id=tipo_prestazione_id,
            lingua=lingua,
        )
        ErrorManager.require(
            template is not None,
            code=error_code,
            message=f"Template email '{codice_template}' non trovato.",
        )
        assert template is not None

        # 2. Risolvi account SMTP con fallback
        account = self._repo.resolve_account(unita_organizzativa_id)
        ErrorManager.require(
            account is not None,
            code=error_code,
            message="Nessun account email configurato (ne' per reparto ne' SISTEMA).",
        )
        assert account is not None

        # 3. Renderizza oggetto e corpo
        oggetto = self.render_template(template["oggetto"], variabili)
        corpo_html = self.render_template(template["corpo_html"], variabili)
        corpo_testo = None
        if template.get("corpo_testo"):
            corpo_testo = self.render_template(template["corpo_testo"], variabili)

        return template, account, oggetto, corpo_html, corpo_testo

    # Scopo: Invia un'email risolvendo account e template con fallback per reparto.
    #        In modalita' DEBUG con account senza smtp_host, logga in console.
    #        Obiettivo: un unico punto di invio per tutto il sistema.
    #        Crea sempre un record in config.email_log. Ritorna (log_id, successo).
    def send_email(
        self,
        *,
        codice_template: str,
        destinatario: str,
        variabili: dict[str, Any],
        unita_organizzativa_id: int | None = None,
        tipo_prestazione_id: int | None = None,
        lingua: str = "it",
        # ⛔ Nessun default, come su `create_outbox` (2026-09-05). `ambito`
        #    classifica A CHI APPARTIENE l'email, ed e' la colonna su cui il
        #    database sta per montare una policy di lettura: un valore di
        #    RIPIEGO non puo' fare da cancello di sicurezza, o basta un campo
        #    dimenticato per classificare come segreta una riga qualunque.
        #    Prerequisito dichiarato dal team DB per la policy su
        #    `config.email_log` (brief residui §1-nonies).
        ambito: str,
        pratica_id: int | None = None,
        auth_user_id: int | None = None,
        destinatari_cc: list[str] | None = None,
    ) -> tuple[int, bool]:
        template, account, oggetto, corpo_html, corpo_testo = self.resolve_and_render(
            codice_template=codice_template,
            variabili=variabili,
            unita_organizzativa_id=unita_organizzativa_id,
            tipo_prestazione_id=tipo_prestazione_id,
            lingua=lingua,
        )

        return self.send_raw(
            account=account,
            destinatario=destinatario,
            destinatari_cc=destinatari_cc,
            oggetto=oggetto,
            corpo_html=corpo_html,
            corpo_testo=corpo_testo,
            email_account_id=account["id"],
            email_template_id=template["id"],
            ambito=ambito,
            unita_organizzativa_id=unita_organizzativa_id,
            pratica_id=pratica_id,
            auth_user_id=auth_user_id,
            contesto_json=variabili,
        )

    # Scopo: Invia email da dati gia' renderizzati (usato sia da send_email che da outbox).
    #        Crea log, tenta invio, aggiorna stato. Ritorna (log_id, successo).
    def send_raw(
        self,
        *,
        account: dict[str, Any],
        destinatario: str,
        destinatari_cc: list[str] | None = None,
        oggetto: str,
        corpo_html: str,
        corpo_testo: str | None = None,
        email_account_id: int | None = None,
        email_template_id: int | None = None,
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
    ) -> tuple[int, bool]:
        # Crea record log con stato PENDING
        log_id = self._repo.insert_log(
            email_account_id=email_account_id,
            email_template_id=email_template_id,
            destinatario=destinatario,
            destinatari_cc=destinatari_cc,
            oggetto=oggetto,
            corpo_inviato_html=corpo_html,
            corpo_inviato_testo=corpo_testo,
            stato="PENDING",
            ambito=ambito,
            unita_organizzativa_id=unita_organizzativa_id,
            pratica_id=pratica_id,
            auth_user_id=auth_user_id,
            contesto_json=contesto_json,
        )

        # Invio
        canale = self.canale_invio(account)
        if canale == CANALE_NON_CONFIGURATO:
            self._registra_non_configurato(log_id, account, ambito)
            return log_id, False
        if canale == CANALE_CONSOLE:
            self._send_console(account, destinatario, destinatari_cc, oggetto, corpo_html, corpo_testo)
            now = datetime.now(timezone.utc).isoformat()
            # ⚠️ RESIDUO DICHIARATO: anche qui `SENT` dice una cosa che non e'
            #    successa — la mail e' stata stampata, non consegnata. Lo stato
            #    onesto sarebbe un valore suo (`CONSOLE`), e il vocabolario vive
            #    nel `CHECK chk_email_log_stato`: e' una richiesta al team DB,
            #    non una cosa che il backend possa decidere da solo.
            #    ⭐ Il caso PERICOLOSO — placeholder su un host di esercizio — non
            #    passa piu' di qui: cade nel ramo sopra. Qui resta lo sviluppo
            #    dichiarato, dove chi guarda sa gia' che non parte niente.
            self._repo.update_log_stato(log_id, "SENT", ambito=ambito, inviato_at=now)
            return log_id, True

        success = self._send_smtp(
            account, destinatario, destinatari_cc, oggetto, corpo_html,
            corpo_testo, log_id, ambito,
        )
        return log_id, success

    # Scopo: Invia email via SMTP reale, aggiorna log con esito. Ritorna True se successo.
    # ⚠️ `ambito` arriva fin qui perche' l'esito dell'invio si scrive su
    #    `config.email_log`, e su una riga `SISTEMA` quella scrittura passa da
    #    una porta diversa (vedi `EmailRepository.update_log_stato`). Non e' un
    #    parametro descrittivo: sceglie la porta.
    def _send_smtp(
        self,
        account: dict[str, Any],
        destinatario: str,
        destinatari_cc: list[str] | None,
        oggetto: str,
        corpo_html: str,
        corpo_testo: str | None,
        log_id: int,
        ambito: str,
    ) -> bool:
        server: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            encrypted_pw = account.get("smtp_password_encrypted")
            if not encrypted_pw:
                self._repo.update_log_stato(
                    log_id, "FAILED", ambito=ambito,
                    errore="Password SMTP non configurata per l'account.",
                )
                return False
            password = crypto_service.decrypt(encrypted_pw)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = oggetto
            msg["From"] = account["email_from"]
            msg["To"] = destinatario
            if destinatari_cc:
                msg["Cc"] = ", ".join(destinatari_cc)
            if account.get("email_reply_to"):
                msg["Reply-To"] = account["email_reply_to"]

            if corpo_testo:
                msg.attach(MIMEText(corpo_testo, "plain", "utf-8"))
            msg.attach(MIMEText(corpo_html, "html", "utf-8"))

            all_recipients = [destinatario] + (destinatari_cc or [])

            if account.get("smtp_use_ssl"):
                server = smtplib.SMTP_SSL(account["smtp_host"], account["smtp_port"], timeout=_SMTP_TIMEOUT_SEND)
            else:
                server = smtplib.SMTP(account["smtp_host"], account["smtp_port"], timeout=_SMTP_TIMEOUT_SEND)
                if account.get("smtp_use_tls"):
                    server.starttls()

            server.login(account["smtp_username"], password)
            server.sendmail(account["email_from"], all_recipients, msg.as_string())

            now = datetime.now(timezone.utc).isoformat()
            self._repo.update_log_stato(log_id, "SENT", ambito=ambito, inviato_at=now)
            logger.info("Email inviata: log_id=%s dest=%s", log_id, destinatario)
            return True

        except (smtplib.SMTPException, OSError, ValueError) as exc:
            self._repo.update_log_stato(
                log_id, "FAILED", ambito=ambito, errore=str(exc)[:500],
            )
            logger.exception("Errore invio email: log_id=%s dest=%s", log_id, destinatario)
            return False
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass

    # Scopo: Registra sul giornale che l'email NON e' partita perche' l'account
    #        non e' configurato — con il motivo e la strada per rimediare.
    # ⛔ `FAILED` e non `SENT`, ed e' il punto di tutta questa modifica: una mail
    #    che non e' partita deve leggersi diversa da una consegnata. `FAILED` e'
    #    gia' nel vocabolario del `CHECK`, quindi questo ramo non aspetta nessuno.
    # ⭐ E TORNA IN CODA — ed e' un BENE, non un difetto. La `SELECT` di
    #    `send_pending_emails` ripesca anche i `FAILED` finche'
    #    `tentativi < max_tentativi` (default 3), e `tentativi` lo incrementa
    #    l'UPDATE dell'esito da ENTRAMBE le strade (`update_log_stato` e, per
    #    l'ambito SISTEMA, `config.fn_chiudi_email_sistema`) — quindi la riga si
    #    ferma da se' dopo tre giri.
    #    ⇒ Il ripescaggio e' il RECUPERO: se l'SMTP viene configurato entro quei
    #    tre tick, la mail parte da sola. E' esattamente il caso capitato il
    #    2026-09-11, dove il digest era stato accodato prima dell'SMTP.
    # ⚠️ Questo commento diceva l'opposto — «non torna in coda» — leggendo il
    #    commento in testa a `send_pending_emails`, che nomina «PENDING o RETRY»
    #    e OMETTE `FAILED`. La SELECT vera dice altro: *un commento non e' una
    #    fonte, e l'ho scoperto fidandomene.*
    # ⚠️ IL LIMITE VERO sta a valle e NON e' di questo ramo: esaurito il terzo
    #    tentativo la riga e' terminale, e un rilancio a mano non esiste —
    #    `retry_log_entry` ha un chiamante solo (quel command, che non la ripesca
    #    piu') e su `config.email_log` non c'e' nessuna rotta di scrittura. Vale
    #    per QUALUNQUE mail fallita, non per il solo placeholder: e' la politica
    #    di retry del giornale, che esisteva prima di questa modifica.
    #    ⇒ Il rimedio, se si vuole, e' un verbo «rilancia» sul giornale email —
    #    il service c'e' gia', manca la rotta. E' lavoro di backend, non una
    #    richiesta al team DB.
    def _registra_non_configurato(
        self, log_id: int, account: dict[str, Any], ambito: str,
    ) -> None:
        motivo = _motivo_non_configurato(account)
        logger.error("Email NON inviata: log_id=%s %s", log_id, motivo)
        self._repo.update_log_stato(log_id, "FAILED", ambito=ambito, errore=motivo)

    # Scopo: Logga email in console (modalita' DEBUG senza SMTP reale).
    def _send_console(
        self,
        account: dict[str, Any],
        destinatario: str,
        destinatari_cc: list[str] | None,
        oggetto: str,
        corpo_html: str,
        corpo_testo: str | None,
    ) -> None:
        separator = "=" * 60
        logger.info(
            "\n%s\nEMAIL (console mode)\n%s\n"
            "Da:       %s\nA:        %s\nCC:       %s\nOggetto:  %s\n"
            "%s\n%s\n%s",
            separator, separator,
            account.get("email_from", "N/D"),
            destinatario,
            ", ".join(destinatari_cc) if destinatari_cc else "(nessuno)",
            oggetto,
            "-" * 60,
            corpo_testo or "(solo HTML)",
            separator,
        )

    # Scopo: Ritenta l'invio di un'email gia' presente nel log (per management command).
    #        Usa l'account specificato, aggiorna lo stato del log.
    # ⚠️ L'ambito si legge dal `log_detail` che il chiamante ha gia' in mano
    #    (`get_log` lo consegna): serve a scegliere la porta con cui si
    #    scrive l'esito, non a descrivere la riga.
    def retry_log_entry(self, log_id: int, account: dict[str, Any], log_detail: dict[str, Any]) -> bool:
        ambito = log_detail["ambito"]
        canale = self.canale_invio(account)
        if canale == CANALE_NON_CONFIGURATO:
            # ⛔ Ritentare su un account che non puo' spedire non e' un tentativo:
            #    e' lo stesso guasto una seconda volta. Si dice, e si torna False.
            self._registra_non_configurato(log_id, account, ambito)
            return False
        if canale == CANALE_CONSOLE:
            self._send_console(
                account,
                log_detail["destinatario"],
                log_detail.get("destinatari_cc"),
                log_detail["oggetto"],
                log_detail.get("corpo_inviato_html", ""),
                log_detail.get("corpo_inviato_testo"),
            )
            now = datetime.now(timezone.utc).isoformat()
            self._repo.update_log_stato(log_id, "SENT", ambito=ambito, inviato_at=now)
            return True
        return self._send_smtp(
            account,
            log_detail["destinatario"],
            log_detail.get("destinatari_cc"),
            log_detail["oggetto"],
            log_detail.get("corpo_inviato_html", ""),
            log_detail.get("corpo_inviato_testo"),
            log_id,
            ambito,
        )

    # Scopo: Testa la connessione SMTP di un account (senza inviare email).
    def test_connection(self, account_id: int) -> dict[str, Any]:
        account = self._repo.get_account_with_password(account_id)
        ErrorManager.require(account is not None, code=E_EMAIL, message="Account non trovato.")
        assert account is not None

        canale = self.canale_invio(account)
        if canale == CANALE_NON_CONFIGURATO:
            # ⛔ Rispondeva `success: True` — ed e' il verde che ha ingannato di
            #    persona il 2026-09-10: «test connessione OK» su un account che
            #    non poteva spedire nulla. Un test che non prova niente non
            #    risponde OK.
            # ⚠️ La CONSEGUENZA e' quella del test, non quella dell'invio: qui
            #    nessuna mail e' in gioco, e questo messaggio lo legge un
            #    amministratore nel drawer (`meta.last_test_message`).
            return {
                "success": False,
                "message": _motivo_non_configurato(
                    account, conseguenza=_CONSEGUENZA_TEST,
                ),
            }
        if canale == CANALE_CONSOLE:
            return {"success": True, "message": "Console mode (DEBUG) — nessun test SMTP necessario."}

        encrypted_pw = account.get("smtp_password_encrypted")
        if not encrypted_pw:
            return {"success": False, "message": "Password SMTP non configurata per l'account."}

        server: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            password = crypto_service.decrypt(encrypted_pw)
            if account.get("smtp_use_ssl"):
                server = smtplib.SMTP_SSL(account["smtp_host"], account["smtp_port"], timeout=_SMTP_TIMEOUT_TEST)
            else:
                server = smtplib.SMTP(account["smtp_host"], account["smtp_port"], timeout=_SMTP_TIMEOUT_TEST)
                if account.get("smtp_use_tls"):
                    server.starttls()
            server.login(account["smtp_username"], password)
            return {"success": True, "message": "Connessione SMTP riuscita."}
        except Exception as exc:
            return {"success": False, "message": f"Errore SMTP: {exc}"}
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass
