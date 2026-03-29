# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio invito operatore al primo accesso.
#        Genera password temporanea, imposta flag cambio password,
#        crea token invito, invia email con link di attivazione.
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
import secrets
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import connection, transaction

from apps.core.db.auth_repository import AuthRepository
from apps.core.db.email_repository import EmailRepository
from apps.core.services.email_service import EmailDispatchService
from apps.core.services.error_manager import ErrorManager
from apps.core.services.token_service import TokenService

logger = logging.getLogger("security")

E_INVITO = "E_INVITO_OPERATORE"
_INVITO_TOKEN_TIPO = "INVITO_OPERATORE"
_INVITO_SCADENZA_ORE = 72
_TEMPLATE_INVITO = "INVITO_OPERATORE"


class InvitoOperatoreService:
    """Gestione invito operatore: verifica, genera, invia, reinvia."""

    def __init__(self) -> None:
        self._auth_repo = AuthRepository()
        self._token_service = TokenService()
        self._email_service = EmailDispatchService()

    # Scopo: Verifica se un operatore e' invitabile, genera token e invia email.
    #        Imposta password temporanea e flag deve_cambiare_password.
    #        Obiettivo: l'operatore riceve un link e al primo accesso sceglie la password.
    def invia_invito(self, auth_user_id: int, invitato_da_user_id: int) -> dict[str, Any]:
        # 1. Verifica invitabilita' via funzione PG
        check = self._check_invitabile(auth_user_id)
        ErrorManager.require(
            check.get("invitabile", False),
            code=E_INVITO,
            message=check.get("motivo", "Operatore non invitabile."),
        )
        email = check["email"]

        # 2-4. Operazioni atomiche: password + flag + token
        with transaction.atomic():
            # 2. Imposta password temporanea casuale (non comunicata all'operatore)
            temp_password = secrets.token_urlsafe(16)
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE django.auth_user SET password = %s WHERE id = %s",
                    [make_password(temp_password), auth_user_id],
                )

            # 3. Imposta flag deve_cambiare_password
            self._auth_repo.set_deve_cambiare_password(auth_user_id, True)

            # 4. Genera token invito
            token_plain = self._token_service.create(
            tipo=_INVITO_TOKEN_TIPO,
            auth_user_id=auth_user_id,
            scadenza_ore=_INVITO_SCADENZA_ORE,
                meta={"invitato_da_user_id": invitato_da_user_id},
            )

        # 5. Risolvi reparto per account email mittente
        uo_id = self._auth_repo.get_unita_organizzativa_id(auth_user_id)

        # 6. Costruisci link frontend
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        link = f"{frontend_url}/attivazione/{token_plain}"

        # 7. Recupera nome invitante
        invitato_da_nome = self._get_user_display_name(invitato_da_user_id)

        # 8. Recupera nome operatore
        operatore_nome = self._get_user_names(auth_user_id)

        # 9. Invia email (non blocca il flusso se fallisce — il token e' gia' valido)
        try:
            self._email_service.send_email(
            codice_template=_TEMPLATE_INVITO,
            destinatario=email,
            variabili={
                "nome": operatore_nome.get("first_name", ""),
                "cognome": operatore_nome.get("last_name", ""),
                "azienda": "ZeroErp",
                "link": link,
                "scadenza_ore": str(_INVITO_SCADENZA_ORE),
                "invitato_da": invitato_da_nome,
            },
            unita_organizzativa_id=uo_id,
            ambito="SISTEMA",
                auth_user_id=auth_user_id,
            )
        except Exception:
            logger.exception("Errore invio email invito per user_id=%s — token valido, invito recuperabile", auth_user_id)

        # 10. Aggiorna timestamp invito
        self._auth_repo.set_invito_inviato_at(auth_user_id)

        logger.info("security.invito_inviato user_id=%s email=%s da=%s", auth_user_id, email, invitato_da_user_id)

        # Maschera email per la response
        masked = self._mask_email(email)
        return {"inviato": True, "email": masked}

    # Scopo: Reinvia invito invalidando token precedenti.
    def reinvia_invito(self, auth_user_id: int, invitato_da_user_id: int) -> dict[str, Any]:
        self._token_service.invalidate_all(_INVITO_TOKEN_TIPO, auth_user_id)
        return self.invia_invito(auth_user_id, invitato_da_user_id)

    # Scopo: Chiama fn_check_operatore_invitabile e ritorna il risultato JSONB.
    def _check_invitabile(self, auth_user_id: int) -> dict[str, Any]:
        sql = "SELECT script.fn_check_operatore_invitabile(%s)"
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            row = cursor.fetchone()
            if row and row[0]:
                return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return {"invitabile": False, "motivo": "Errore verifica invitabilita'."}

    # Scopo: Recupera nome visualizzabile di un utente.
    def _get_user_display_name(self, auth_user_id: int) -> str:
        sql = "SELECT first_name, last_name, username FROM django.auth_user WHERE id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            row = cursor.fetchone()
            if row:
                name = f"{row[0]} {row[1]}".strip()
                return name if name else row[2]
        return "Amministratore"

    # Scopo: Recupera first_name e last_name di un utente.
    def _get_user_names(self, auth_user_id: int) -> dict[str, str]:
        sql = "SELECT first_name, last_name FROM django.auth_user WHERE id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            row = cursor.fetchone()
            if row:
                return {"first_name": row[0] or "", "last_name": row[1] or ""}
        return {"first_name": "", "last_name": ""}

    # Scopo: Maschera email per la response (es. "m***@azienda.it").
    @staticmethod
    def _mask_email(email: str) -> str:
        if not email or "@" not in email:
            return "***"
        local, domain = email.split("@", 1)
        if len(local) <= 1:
            return f"*@{domain}"
        return f"{local[0]}***@{domain}"
