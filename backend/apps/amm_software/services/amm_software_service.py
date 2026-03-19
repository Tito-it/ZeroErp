# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service layer per Amm. Software — validazione, orchestrazione.
#        Ref: docs/it/dev/api.md (sezione 6 Layering)
# ------------------------------------------------------------

from __future__ import annotations

import uuid as uuid_mod
from typing import Any

from django.contrib.auth.hashers import make_password

from apps.core.api.payload_validators import optional_int
from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.core.services.permissions_cache import invalidate_department, invalidate_user
from apps.amm_software.constants import DEFAULT_RUOLO_SISTEMA, DEFAULT_SESSO, RUOLO_ADMIN
from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository

E_AMM_VALIDAZIONE = "E_AMM_VALIDAZIONE"
E_AMM_NOT_FOUND = "E_AMM_UTENTE_NOT_FOUND"


class AmmSoftwareService:
    """Service per gestione operatori, permessi, profili reparto."""

    def __init__(self) -> None:
        self._repo = AmmSoftwareRepository()

    # =================================================================
    # Utenti
    # =================================================================

    # Scopo: Crea operatore completo. Due flussi:
    # Flusso A (soggetto_id assente): crea soggetto PF nuovo — cognome/nome/CF obbligatori.
    # Flusso B (soggetto_id presente): associa soggetto esistente — dati persona non richiesti.
    # In entrambi: username, email, password, qualifica obbligatori.
    def create_operatore(self, payload: dict) -> dict[str, Any]:
        soggetto_id = (payload.get("soggetto_id") or "").strip() or None
        username = (payload.get("username") or "").strip()
        email = (payload.get("email") or "").strip()
        password = payload.get("password") or ""
        raw_qualifica = payload.get("qualifica_id")

        # Guard UUID soggetto_id (flusso B)
        if soggetto_id:
            try:
                uuid_mod.UUID(soggetto_id)
            except (ValueError, AttributeError):
                ErrorManager.require(False, code=E_AMM_VALIDAZIONE, message="UUID soggetto non valido.")

        # Guard qualifica_id numerico
        try:
            qualifica_id = int(raw_qualifica) if raw_qualifica is not None else None
        except (ValueError, TypeError):
            qualifica_id = None

        # Validazione comune (entrambi i flussi)
        ErrorManager.require(bool(username), code=E_AMM_VALIDAZIONE, message="Username obbligatorio.")
        ErrorManager.require(bool(email), code=E_AMM_VALIDAZIONE, message="Email obbligatoria.")
        ErrorManager.require(bool(password), code=E_AMM_VALIDAZIONE, message="Password obbligatoria.")
        ErrorManager.require(qualifica_id is not None and qualifica_id > 0, code=E_AMM_VALIDAZIONE, message="Qualifica obbligatoria.")

        # Validazione flusso A: dati persona obbligatori solo se soggetto nuovo
        cognome = (payload.get("cognome") or "").strip()
        nome = (payload.get("nome") or "").strip()
        codice_fiscale = (payload.get("codice_fiscale") or "").strip()

        if not soggetto_id:
            ErrorManager.require(bool(cognome), code=E_AMM_VALIDAZIONE, message="Cognome obbligatorio per soggetto nuovo.")
            ErrorManager.require(bool(nome), code=E_AMM_VALIDAZIONE, message="Nome obbligatorio per soggetto nuovo.")
            ErrorManager.require(bool(codice_fiscale), code=E_AMM_VALIDAZIONE, message="Codice fiscale obbligatorio per soggetto nuovo.")

        auth_user_id = self._repo.crea_operatore(
            soggetto_id=soggetto_id,
            cognome=cognome or None,
            nome=nome or None,
            codice_fiscale=codice_fiscale or None,
            username=username,
            email=email,
            password_hash=make_password(password),
            qualifica_id=qualifica_id,  # type: ignore[arg-type]
            unita_organizzativa_id=int(payload["unita_organizzativa_id"]) if payload.get("unita_organizzativa_id") else None,
            data_nascita=payload.get("data_nascita"),
            sesso=payload.get("sesso", DEFAULT_SESSO),
            ruolo_sistema=payload.get("ruolo_sistema", DEFAULT_RUOLO_SISTEMA),
            valido_dal=payload.get("valido_dal"),
            valido_al=payload.get("valido_al"),
            comune_nascita_id=optional_int(payload, "comune_nascita_id"),
            indirizzo_resid_dettaglio_id=optional_int(payload, "indirizzo_resid_dettaglio_id"),
            indirizzo_domfisc_dettaglio_id=optional_int(payload, "indirizzo_domfisc_dettaglio_id"),
        )
        return self._repo.get_utente_detail(auth_user_id) or {}

    # Scopo: Dettaglio utente con validazione esistenza.
    def get_utente(self, auth_user_id: int) -> dict[str, Any]:
        utente = self._repo.get_utente_detail(auth_user_id)
        ErrorManager.require(utente is not None, code=E_AMM_NOT_FOUND, message=f"Utente {auth_user_id} non trovato.")
        assert utente is not None
        return utente

    # Scopo: Aggiorna utente e invalida cache permessi.
    def update_utente(self, auth_user_id: int, payload: dict) -> dict[str, Any]:
        self.get_utente(auth_user_id)  # verifica esistenza
        self._repo.update_utente(
            auth_user_id,
            email=payload.get("email"),
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            ruolo_sistema=payload.get("ruolo_sistema"),
            unita_organizzativa_id=payload.get("unita_organizzativa_id"),
            attivo=payload.get("attivo"),
            valido_al=payload.get("valido_al"),
        )
        invalidate_user(auth_user_id)
        return self._repo.get_utente_detail(auth_user_id) or {}

    # Scopo: Disabilita utente, invalida cache e blacklist token.
    # Guard: impedisce di disabilitare l'ultimo ADMIN attivo.
    def disabilita_utente(self, auth_user_id: int) -> dict[str, Any]:
        utente = self.get_utente(auth_user_id)
        if utente.get("ruolo_sistema") == RUOLO_ADMIN:
            if self._repo.count_admin_attivi() <= 1:
                raise ServiceError(
                    code="E_ADMIN_ULTIMO",
                    message="Impossibile disabilitare l'ultimo amministratore.",
                    detail="Deve esistere almeno un utente ADMIN attivo nel sistema.",
                )
        self._repo.disabilita_utente(auth_user_id)
        invalidate_user(auth_user_id)
        _blacklist_user_tokens(auth_user_id)
        return self._repo.get_utente_detail(auth_user_id) or {}

    # Scopo: Riattiva utente disabilitato, invalida cache.
    def riattiva_utente(self, auth_user_id: int) -> dict[str, Any]:
        self.get_utente(auth_user_id)  # verifica esistenza
        self._repo.riattiva_utente(auth_user_id)
        invalidate_user(auth_user_id)
        return self._repo.get_utente_detail(auth_user_id) or {}

    # =================================================================
    # Override permessi
    # =================================================================

    # Scopo: Salva override aree e invalida cache.
    def put_override_aree(self, auth_user_id: int, items: list) -> list:
        self._repo.put_override_aree(auth_user_id, items)
        invalidate_user(auth_user_id)
        return self._repo.get_override_aree(auth_user_id)

    # Scopo: Salva override azioni e invalida cache.
    def put_override_azioni(self, auth_user_id: int, items: list) -> list:
        self._repo.put_override_azioni(auth_user_id, items)
        invalidate_user(auth_user_id)
        return self._repo.get_override_azioni(auth_user_id)

    # Scopo: Salva scope emittenti e invalida cache.
    def put_emittenti_scope(self, auth_user_id: int, emittente_ids: list) -> list:
        self._repo.put_emittenti_scope(auth_user_id, emittente_ids)
        invalidate_user(auth_user_id)
        return self._repo.get_emittenti_scope(auth_user_id)

    # Scopo: Lista utenti con filtri.
    def list_utenti(self, **params) -> tuple[list, int]:
        return self._repo.list_utenti(**params)

    # Scopo: Lista override aree.
    def get_override_aree(self, auth_user_id: int) -> list:
        return self._repo.get_override_aree(auth_user_id)

    # Scopo: Lista override azioni.
    def get_override_azioni(self, auth_user_id: int) -> list:
        return self._repo.get_override_azioni(auth_user_id)

    # Scopo: Lista emittenti scope.
    def get_emittenti_scope(self, auth_user_id: int) -> list:
        return self._repo.get_emittenti_scope(auth_user_id)

    # Scopo: Lista reparti.
    def list_reparti(self) -> list:
        return self._repo.list_reparti()

    # Scopo: Profilo reparto.
    def get_profilo_reparto(self, uo_id: int) -> dict:
        return self._repo.get_profilo_reparto(uo_id)

    # Scopo: Lista UO.
    def list_unita_organizzative(self) -> list:
        return self._repo.list_unita_organizzative()

    # Scopo: Lista aree funzionali.
    def list_aree_funzionali(self) -> list:
        return self._repo.list_aree_funzionali()

    # Scopo: Lista azioni processo.
    def list_azioni_processo(self) -> list:
        return self._repo.list_azioni_processo()

    # Scopo: Lista emittenti fiscali.
    def list_emittenti_fiscali(self) -> list:
        return self._repo.list_emittenti_fiscali()

    # =================================================================
    # Profili reparto
    # =================================================================

    # Scopo: Salva profilo reparto e invalida cache di tutti gli operatori del reparto.
    def put_profilo_reparto(self, uo_id: int, aree: list, azioni: list) -> dict:
        self._repo.put_profilo_reparto(uo_id, aree, azioni)
        invalidate_department(uo_id)
        return self._repo.get_profilo_reparto(uo_id)


# Scopo: Invalida token JWT utente via blacklist SimpleJWT (best-effort).
def _blacklist_user_tokens(auth_user_id: int) -> None:
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        tokens = OutstandingToken.objects.filter(user_id=auth_user_id)
        for token in tokens:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                rt = RefreshToken(token.token)
                rt.blacklist()
            except Exception:
                pass
    except ImportError:
        pass
