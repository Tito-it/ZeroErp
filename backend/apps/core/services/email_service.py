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

# Marker per account placeholder (seed iniziale senza SMTP reale)
_SMTP_PLACEHOLDER_HOST = "smtp.example.com"
_SMTP_TIMEOUT_SEND = 30
_SMTP_TIMEOUT_TEST = 10


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

    # Scopo: Determina se un account e' in console mode.
    #        Console mode se: host vuoto/placeholder (indipendentemente da DEBUG),
    #        oppure DEBUG=True con qualsiasi account.
    def is_console_mode(self, account: dict[str, Any]) -> bool:
        smtp_host = account.get("smtp_host", "")
        if not smtp_host or smtp_host == _SMTP_PLACEHOLDER_HOST:
            return True
        return settings.DEBUG

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
        ambito: str = "SISTEMA",
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
        ambito: str = "SISTEMA",
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
        if self.is_console_mode(account):
            self._send_console(account, destinatario, destinatari_cc, oggetto, corpo_html, corpo_testo)
            now = datetime.now(timezone.utc).isoformat()
            self._repo.update_log_stato(log_id, "SENT", inviato_at=now)
            return log_id, True

        success = self._send_smtp(account, destinatario, destinatari_cc, oggetto, corpo_html, corpo_testo, log_id)
        return log_id, success

    # Scopo: Invia email via SMTP reale, aggiorna log con esito. Ritorna True se successo.
    def _send_smtp(
        self,
        account: dict[str, Any],
        destinatario: str,
        destinatari_cc: list[str] | None,
        oggetto: str,
        corpo_html: str,
        corpo_testo: str | None,
        log_id: int,
    ) -> bool:
        server: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            encrypted_pw = account.get("smtp_password_encrypted")
            if not encrypted_pw:
                self._repo.update_log_stato(log_id, "FAILED", errore="Password SMTP non configurata per l'account.")
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
            self._repo.update_log_stato(log_id, "SENT", inviato_at=now)
            logger.info("Email inviata: log_id=%s dest=%s", log_id, destinatario)
            return True

        except (smtplib.SMTPException, OSError, ValueError) as exc:
            self._repo.update_log_stato(log_id, "FAILED", errore=str(exc)[:500])
            logger.exception("Errore invio email: log_id=%s dest=%s", log_id, destinatario)
            return False
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass

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
    def retry_log_entry(self, log_id: int, account: dict[str, Any], log_detail: dict[str, Any]) -> bool:
        if self.is_console_mode(account):
            self._send_console(
                account,
                log_detail["destinatario"],
                log_detail.get("destinatari_cc"),
                log_detail["oggetto"],
                log_detail.get("corpo_inviato_html", ""),
                log_detail.get("corpo_inviato_testo"),
            )
            now = datetime.now(timezone.utc).isoformat()
            self._repo.update_log_stato(log_id, "SENT", inviato_at=now)
            return True
        return self._send_smtp(
            account,
            log_detail["destinatario"],
            log_detail.get("destinatari_cc"),
            log_detail["oggetto"],
            log_detail.get("corpo_inviato_html", ""),
            log_detail.get("corpo_inviato_testo"),
            log_id,
        )

    # Scopo: Testa la connessione SMTP di un account (senza inviare email).
    def test_connection(self, account_id: int) -> dict[str, Any]:
        account = self._repo.get_account_with_password(account_id)
        ErrorManager.require(account is not None, code=E_EMAIL, message="Account non trovato.")
        assert account is not None

        if self.is_console_mode(account):
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
