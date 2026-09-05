# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gestione bozze email (outbox): preparazione da template,
#        modifica, conferma invio, annullamento, allegati.
#        Le bozze sono editabili prima dell'invio effettivo.
# ------------------------------------------------------------

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.db import transaction

from apps.core.db.email_repository import EmailRepository
from apps.core.services.email_service import E_EMAIL, EmailDispatchService
from apps.core.services.error_manager import ErrorManager

E_OUTBOX = "E_OUTBOX"

ALLOWED_MIME_TYPES = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/msword",
    "image/jpeg",
    "image/png",
    "image/gif",
    "text/plain",
    "text/csv",
})


def _get_attachments_root() -> str:
    """Scopo: Ritorna il path root per gli allegati, leggendo da settings a runtime."""
    return getattr(settings, "EMAIL_ATTACHMENTS_ROOT", os.path.join(settings.BASE_DIR, "email_attachments"))


def _get_max_size_bytes() -> int:
    """Scopo: Ritorna la dimensione massima allegato in bytes, leggendo da settings a runtime."""
    mb = getattr(settings, "EMAIL_ATTACHMENT_MAX_SIZE_MB", 10)
    return mb * 1024 * 1024


def _get_max_count() -> int:
    """Scopo: Ritorna il numero massimo allegati per email, leggendo da settings a runtime."""
    return getattr(settings, "EMAIL_ATTACHMENT_MAX_COUNT", 10)


class EmailOutboxService:
    """Gestione bozze email: preparazione, modifica, invio, annullamento, allegati."""

    def __init__(self) -> None:
        self._repo = EmailRepository()
        self._dispatch = EmailDispatchService()

    # Scopo: Prepara una bozza email risolvendo template e account, pre-compilando
    #        oggetto e corpo con le variabili fornite. La bozza e' editabile.
    def prepare_draft(
        self,
        *,
        codice_template: str,
        destinatario: str,
        variabili: dict[str, Any],
        unita_organizzativa_id: int | None = None,
        tipo_prestazione_id: int | None = None,
        lingua: str = "it",
        # ⛔ Senza default, ed e' il punto: `SISTEMA` come ripiego rendeva
        #    indistinguibile «non dichiarato» da «di sistema», proprio sulla
        #    colonna su cui il database decide chi puo' leggere.
        ambito: str,
        emittente_fiscale_id: int | None = None,
        pratica_id: int | None = None,
        auth_user_id: int | None = None,
        creato_da_user_id: int | None = None,
        destinatari_cc: list[str] | None = None,
    ) -> dict[str, Any]:
        # Risolvi template + account + renderizza (metodo condiviso con EmailDispatchService)
        template, account, oggetto, corpo_html, corpo_testo = self._dispatch.resolve_and_render(
            codice_template=codice_template,
            variabili=variabili,
            unita_organizzativa_id=unita_organizzativa_id,
            tipo_prestazione_id=tipo_prestazione_id,
            lingua=lingua,
            error_code=E_OUTBOX,
        )

        # Crea bozza
        outbox_id = self._repo.create_outbox(
            destinatario=destinatario,
            destinatari_cc=destinatari_cc,
            oggetto=oggetto,
            corpo_html=corpo_html,
            corpo_testo=corpo_testo,
            email_account_id=account["id"],
            email_template_id=template["id"],
            ambito=ambito,
            emittente_fiscale_id=emittente_fiscale_id,
            unita_organizzativa_id=unita_organizzativa_id,
            pratica_id=pratica_id,
            auth_user_id=auth_user_id,
            creato_da_user_id=creato_da_user_id,
            contesto_json=variabili,
        )

        return self._repo.get_outbox(outbox_id) or {}

    # Scopo: Aggiorna campi editabili di una bozza DRAFT.
    def update_draft(self, outbox_id: int, **kwargs: Any) -> dict[str, Any]:
        outbox = self._repo.get_outbox(outbox_id)
        ErrorManager.require(outbox is not None, code=E_OUTBOX, message="Bozza non trovata.")
        assert outbox is not None
        ErrorManager.require(outbox["stato"] == "DRAFT", code=E_OUTBOX, message="Solo bozze DRAFT sono modificabili.")

        # Filtra solo campi editabili (stessa whitelist del repository)
        fields = {k: v for k, v in kwargs.items() if k in EmailRepository._OUTBOX_UPDATE_COLS}
        if fields:
            self._repo.update_outbox(outbox_id, **fields)

        return self._repo.get_outbox(outbox_id) or {}

    # Scopo: Conferma e invia una bozza via send_raw pubblico di EmailDispatchService.
    #        Crea email_log, copia allegati, aggiorna stato outbox.
    def confirm_and_send(self, outbox_id: int) -> dict[str, Any]:
        outbox = self._repo.get_outbox(outbox_id)
        ErrorManager.require(outbox is not None, code=E_OUTBOX, message="Bozza non trovata.")
        assert outbox is not None
        ErrorManager.require(
            outbox["stato"] == "DRAFT",
            code=E_OUTBOX, message="Solo bozze DRAFT possono essere inviate.",
        )

        # Porta a READY
        self._repo.update_outbox_stato(outbox_id, "READY")

        # Risolvi account per invio
        account = self._repo.resolve_account(outbox.get("unita_organizzativa_id"))
        ErrorManager.require(account is not None, code=E_OUTBOX, message="Nessun account email configurato.")
        assert account is not None

        # Invio via metodo pubblico send_raw — crea log + invia
        log_id, success = self._dispatch.send_raw(
            account=account,
            destinatario=outbox["destinatario"],
            destinatari_cc=outbox.get("destinatari_cc"),
            oggetto=outbox["oggetto"],
            corpo_html=outbox["corpo_html"],
            corpo_testo=outbox.get("corpo_testo"),
            email_account_id=outbox["email_account_id"],
            email_template_id=outbox["email_template_id"],
            ambito=outbox["ambito"],
            unita_organizzativa_id=outbox.get("unita_organizzativa_id"),
            pratica_id=outbox.get("pratica_id"),
            auth_user_id=outbox.get("auth_user_id"),
            contesto_json=outbox.get("contesto_json"),
        )

        # Fix analisi-fix-transazioni #16 (Classe C — saga/outbox). Lo stato READY
        # e' gia' committato PRIMA dello SMTP (autocommit sopra): l'invio esterno
        # sta fuori da qualunque transazione DB. I tre write POST-invio (link
        # outbox↔log + copia allegati + stato finale) vanno pero' fusi in UNA
        # transazione: prima erano autocommit separati, quindi un fallimento di
        # `copy_allegati_to_log` lasciava outbox READY + log linkato + allegati
        # mancanti (stato parziale). Ora o tutti e tre o nessuno: se il blocco
        # fallisce l'outbox resta READY "pulito". La riconciliazione dei READY
        # fantasma residui e' un follow-up (§Classe C, step 4): va progettata per
        # NON ri-inviare (lo SMTP e' gia' partito) — recupero idempotente, non
        # re-send. NB: l'email_log e' creato da send_raw (side-effect gia'
        # avvenuto) e non fa parte di questa tx.
        now = datetime.now(timezone.utc).isoformat()
        with transaction.atomic():
            self._repo.update_log_outbox_link(log_id, outbox_id)
            self._repo.copy_allegati_to_log(outbox_id, log_id)
            if success:
                self._repo.update_outbox_stato(outbox_id, "SENT", email_log_id=log_id, inviato_at=now)
            else:
                # Torna a DRAFT per permettere all'operatore di riprovare
                self._repo.update_outbox_stato(outbox_id, "DRAFT", email_log_id=log_id)

        return self._repo.get_outbox(outbox_id) or {}

    # Scopo: Annulla una bozza DRAFT.
    def cancel_draft(self, outbox_id: int) -> dict[str, Any]:
        outbox = self._repo.get_outbox(outbox_id)
        ErrorManager.require(outbox is not None, code=E_OUTBOX, message="Bozza non trovata.")
        assert outbox is not None
        ErrorManager.require(outbox["stato"] == "DRAFT", code=E_OUTBOX, message="Solo bozze DRAFT annullabili.")

        # Elimina allegati fisici
        for allegato in outbox.get("allegati", []):
            _delete_file(allegato.get("file_path"))

        self._repo.update_outbox_stato(outbox_id, "CANCELLED")
        return self._repo.get_outbox(outbox_id) or {}

    # Scopo: Aggiunge un allegato a una bozza DRAFT, salvando il file su storage.
    def add_attachment(
        self,
        outbox_id: int,
        file_name: str,
        file_content: bytes,
        mime_type: str,
    ) -> dict[str, Any]:
        outbox = self._repo.get_outbox(outbox_id)
        ErrorManager.require(outbox is not None, code=E_OUTBOX, message="Bozza non trovata.")
        assert outbox is not None
        ErrorManager.require(outbox["stato"] == "DRAFT", code=E_OUTBOX, message="Solo bozze DRAFT accettano allegati.")

        # Validazioni
        ErrorManager.require(
            mime_type in ALLOWED_MIME_TYPES,
            code=E_OUTBOX, message=f"Tipo file '{mime_type}' non consentito.",
        )
        size = len(file_content)
        max_bytes = _get_max_size_bytes()
        ErrorManager.require(
            size <= max_bytes,
            code=E_OUTBOX, message=f"File troppo grande ({size} bytes, max {max_bytes}).",
        )
        current_count = len(outbox.get("allegati", []))
        max_count = _get_max_count()
        ErrorManager.require(
            current_count < max_count,
            code=E_OUTBOX, message=f"Numero massimo allegati raggiunto ({max_count}).",
        )

        # Salva file su storage
        root = _get_attachments_root()
        now = datetime.now(timezone.utc)
        sub_dir = os.path.join(str(now.year), f"{now.month:02d}")
        abs_dir = os.path.join(root, sub_dir)
        os.makedirs(abs_dir, exist_ok=True)

        ext = os.path.splitext(file_name)[1] or ""
        unique_name = f"{uuid.uuid4().hex}{ext}"
        abs_path = os.path.join(abs_dir, unique_name)
        rel_path = os.path.join(sub_dir, unique_name)

        with open(abs_path, "wb") as f:
            f.write(file_content)

        allegato_id = self._repo.create_allegato(
            email_outbox_id=outbox_id,
            nome_file=file_name,
            mime_type=mime_type,
            dimensione_bytes=size,
            file_path=rel_path,
            origine="UPLOAD",
        )

        return self._repo.get_allegato(allegato_id) or {}

    # Scopo: Rimuove un allegato (file + record DB).
    def remove_attachment(self, allegato_id: int) -> bool:
        file_path = self._repo.delete_allegato(allegato_id)
        if file_path:
            _delete_file(file_path)
            return True
        return False


# Scopo: Elimina file fisico da storage (ignora errori se non esiste).
def _delete_file(rel_path: str | None) -> None:
    if not rel_path or not rel_path.strip():
        return
    abs_path = os.path.join(_get_attachments_root(), rel_path)
    try:
        os.remove(abs_path)
    except OSError:
        pass
