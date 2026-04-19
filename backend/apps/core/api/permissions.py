# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Permission classes DRF per ZeroErp.
# IsAdminZeroERP: check diretto ruolo_sistema = ADMIN (endpoint amministrazione).
# ZeroERPPermission: risoluzione completa area funzionale + livello accesso.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.core.services.auth_constants import (
    RUOLI_PORTALE,
    RUOLI_SHOP,
    RUOLO_APPLICATIVO_DISABILITATO,
)
from apps.core.services.permissions_cache import load_user_cache, save_user_cache
from apps.core.services.permissions_resolver import LIVELLO_MAP, PermissionResolver

logger = logging.getLogger(__name__)


class IsAdminZeroERP(BasePermission):
    """Permission class per endpoint riservati agli amministratori.

    Verifica che l'utente abbia il binding SUPER_ADMIN attivo
    (`script.fn_is_super_admin`). Non passa dal sistema profili area /
    override (check diretto). Nome classe invariato per retrocompatibilita'
    con le view esistenti; la semantica "ADMIN" diventa "SUPER_ADMIN".
    """

    # Scopo: Verifica che l'utente sia SUPER_ADMIN. Bypass per
    # superuser Django (coerenza con ZeroERPPermission).
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        cache = ZeroERPPermission._get_cache(request)
        try:
            if PermissionResolver.is_super_admin(user, cache=cache):
                return True

            logger.warning(
                "security.admin_denied user_id=%s path=%s",
                user.id, request.path,
            )
            self.message = "Accesso riservato agli amministratori."
            return False
        finally:
            ZeroERPPermission._save_cache_to_redis(request)


class ZeroERPPermission(BasePermission):
    """Permission class centrale di Zero ERP.

    Risolve automaticamente l'area funzionale dallo schema del model
    e verifica il livello di accesso tramite PermissionResolver.

    Per ViewSet usa ``view.action`` (list, retrieve, create, ...).
    Per APIView usa ``request.method`` (GET, POST, PUT, ...).

    Le view possono dichiarare:
    - ``area_funzionale = "vendite"`` per indicare l'area quando non c'e' queryset
    - ``<action>_permission = "codename"`` per azioni di processo custom
      (es. ``post_permission = "genera_fatture_lotti"``)
    """

    # Mapping azione ViewSet -> tipo di accesso CRUD richiesto
    ACTION_REQUIRES: dict[str, str] = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
    }

    # Mapping metodo HTTP -> tipo di accesso (fallback per APIView)
    METHOD_REQUIRES: dict[str, str] = {
        "GET": "view",
        "HEAD": "view",
        "OPTIONS": "view",
        "POST": "add",
        "PUT": "change",
        "PATCH": "change",
        "DELETE": "delete",
    }

    # Scopo: Verifica i permessi di accesso per la richiesta corrente.
    # Per APIView senza action usa il metodo HTTP.
    # Per ViewSet usa l'action. Per azioni custom con attributo
    # <action>_permission, verifica l'azione di processo.
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Django superuser bypass
        if user.is_superuser:
            return True

        # Inizializza cache per-request (pre-popolata da Redis L2 se disponibile)
        cache = self._get_cache(request)

        try:
            # Check ruolo applicativo (DISABILITATO => 403 immediato)
            ruolo_app = PermissionResolver.get_ruolo_applicativo(user, cache=cache)
            if ruolo_app == RUOLO_APPLICATIVO_DISABILITATO:
                logger.warning(
                    "security.permission_denied user_id=%s reason=DISABILITATO path=%s",
                    user.id, request.path,
                )
                self.message = "Utente disabilitato. Contattare l'amministratore."
                return False
            # SUPER_ADMIN bypass (sostituisce il vecchio check ruolo_sistema = ADMIN)
            if PermissionResolver.is_super_admin(user, cache=cache):
                return True

            # Determina l'azione richiesta
            action = getattr(view, "action", None)

            # Azione custom con permesso esplicito
            # (es. run_pipeline_permission = 'genera_fatture_lotti')
            if action:
                action_perm = getattr(view, f"{action}_permission", None)
                if action_perm:
                    result = PermissionResolver.check_azione(
                        user, action_perm, cache=cache
                    )
                    if not result:
                        logger.warning(
                            "security.permission_denied user_id=%s reason=azione_negata azione=%s path=%s",
                            user.id, action_perm, request.path,
                        )
                        self.message = "Non hai i permessi per questa operazione."
                    return result

            # Fallback per APIView: controlla <method>_permission
            if not action:
                method = request.method
                if method:
                    method_perm = getattr(
                        view, f"{method.lower()}_permission", None
                    )
                    if method_perm:
                        result = PermissionResolver.check_azione(
                            user, method_perm, cache=cache
                        )
                        if not result:
                            logger.warning(
                                "security.permission_denied user_id=%s reason=azione_negata azione=%s path=%s",
                                user.id, method_perm, request.path,
                            )
                            self.message = "Non hai i permessi per questa operazione."
                        return result

            # CRUD standard: determina il tipo di accesso richiesto
            if action:
                required = self.ACTION_REQUIRES.get(action)
            else:
                required = self.METHOD_REQUIRES.get(request.method or "")

            if required is None:
                # Fail-closed: azione sconosciuta senza *_permission -> nega.
                logger.warning(
                    "security.permission_denied user_id=%s reason=azione_sconosciuta "
                    "action=%s method=%s path=%s",
                    user.id, action, request.method, request.path,
                )
                self.message = "Non hai i permessi per questa operazione."
                return False

            # Determina area funzionale dal model o dall'attributo della view
            area_schema_db = self._resolve_area(view, cache)
            if area_schema_db is None:
                # Fail-closed: nessun model collegato e nessun area_funzionale.
                # Le view che intenzionalmente non richiedono area devono
                # dichiarare skip_area_check = True.
                if getattr(view, "skip_area_check", False):
                    return True
                logger.warning(
                    "security.permission_denied user_id=%s reason=area_non_definita "
                    "view=%s path=%s",
                    user.id, type(view).__name__, request.path,
                )
                self.message = "Non hai i permessi per questa operazione."
                return False

            # Risolvi livello (oggetto o area).
            # Fonti model: 1) queryset ORM, 2) attributo model_permission
            # dichiarato sulla view (per DomainAPIView con raw SQL).
            # Se presente, fn_resolve_livello_oggetto fa fallback
            # automatico al livello area se non c'e' override.
            app_label, model_name = self._get_model_meta(view)
            if not app_label:
                mp = getattr(view, "model_permission", None)
                if mp:
                    app_label, model_name = mp
            if app_label and model_name:
                livello = PermissionResolver.get_livello_oggetto(
                    user, app_label, model_name, area_schema_db, cache=cache
                )
            else:
                livello = PermissionResolver.get_livello_area(
                    user, area_schema_db, cache=cache
                )

            allowed_actions = LIVELLO_MAP.get(livello, frozenset())
            if required not in allowed_actions:
                logger.warning(
                    "security.permission_denied user_id=%s reason=livello_insufficiente "
                    "area=%s livello=%s required=%s path=%s",
                    user.id, area_schema_db, livello, required, request.path,
                )
                self._set_deny_message(user, ruolo_app, area_schema_db, cache)
                return False
            return True
        finally:
            self._save_cache_to_redis(request)

    # Scopo: Imposta il messaggio di errore specifico per il diniego.
    # Distingue tra reparto senza profilo e permesso negato generico.
    # Il messaggio "reparto senza profilo" si applica solo agli OPERATORI
    # interni (utenti portale/shop hanno profili bindati sul ruolo
    # applicativo, non sul reparto).
    def _set_deny_message(
        self,
        user: Any,
        ruolo_app: str | None,
        area_schema_db: str,
        cache: dict[str, Any],
    ) -> None:
        from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE

        if ruolo_app == RUOLO_APPLICATIVO_OPERATORE and not PermissionResolver.has_profilo_applicabile_per_area(
            user, area_schema_db, cache=cache
        ):
            self.message = (
                "Il reparto non ha ancora un profilo permessi configurato."
            )
        else:
            self.message = "Non hai i permessi per questa operazione."

    @staticmethod
    def _get_cache(request: Request) -> dict[str, Any]:
        """Scopo: Restituisce o crea la cache permessi per-request.
        Tenta di pre-popolare da Redis (L2) se la cache L1 non esiste."""
        if not hasattr(request, "_zeroerp_perms_cache"):
            user = request.user
            redis_data = load_user_cache(user.id) if user and user.is_authenticated else None
            request._zeroerp_perms_cache = redis_data or {}  # type: ignore[attr-defined]
            request._zeroerp_perms_cache_loaded_from_redis = redis_data is not None  # type: ignore[attr-defined]
        return request._zeroerp_perms_cache  # type: ignore[attr-defined]

    @staticmethod
    def _save_cache_to_redis(request: Request) -> None:
        """Scopo: Persiste la cache per-request su Redis se e' stata arricchita."""
        user = request.user
        if not user or not user.is_authenticated:
            return
        cache_dict = getattr(request, "_zeroerp_perms_cache", None)
        if not cache_dict:
            return
        # Salva solo se la cache non proveniva gia' da Redis invariata
        already_from_redis = getattr(request, "_zeroerp_perms_cache_loaded_from_redis", False)
        if not already_from_redis or len(cache_dict) > 0:
            save_user_cache(user.id, cache_dict)

    @staticmethod
    def _get_model_meta(view: Any) -> tuple[str | None, str | None]:
        """Scopo: Estrae app_label e model_name dal queryset della view."""
        qs = getattr(view, "queryset", None)
        if qs is not None:
            model = qs.model
            return model._meta.app_label, model._meta.model_name
        return None, None

    @classmethod
    def _resolve_area(
        cls, view: Any, cache: dict[str, Any]
    ) -> str | None:
        """Scopo: Determina l'area funzionale dalla view.
        1. Prova dal queryset model (schema DB)
        2. Fallback all'attributo area_funzionale della view."""
        app_label, model_name = cls._get_model_meta(view)
        if app_label and model_name:
            return PermissionResolver.get_area_schema_db(app_label, model_name)

        # Fallback: attributo esplicito sulla view
        return getattr(view, "area_funzionale", None)


class PortaleBasePermission(BasePermission):
    """Permission class per endpoint `/api/portale/*` (clienti + fornitori).

    Richiede autenticazione JWT. Il ruolo applicativo dell'identita
    deve appartenere a `RUOLI_PORTALE`. Gli operatori interni e shop
    customer sono respinti con 403.

    Non applica scope dati (RLS + `script.fn_scope_*` lato DB sono i
    guardiani autorevoli). Non verifica livello area: il set di
    endpoint portale e' deliberatamente ristretto.
    """

    # Scopo: Verifica autenticazione + ruolo applicativo portale.
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        cache = ZeroERPPermission._get_cache(request)
        try:
            ruolo = PermissionResolver.get_ruolo_applicativo(user, cache=cache)
            if ruolo in RUOLI_PORTALE:
                return True

            logger.warning(
                "security.portale_denied user_id=%s ruolo=%s path=%s",
                user.id, ruolo, request.path,
            )
            self.message = "Accesso riservato agli utenti portale."
            return False
        finally:
            ZeroERPPermission._save_cache_to_redis(request)


class ShopBasePermission(BasePermission):
    """Permission class per endpoint `/api/shop/*` (negozio online).

    Ammette utenti anonimi (catalogo pubblico) e utenti autenticati
    con ruolo applicativo `SHOP_CUSTOMER`. Altri ruoli applicativi
    autenticati vengono respinti per evitare che un operatore o un
    cliente portale usi per errore gli endpoint shop.

    Le singole view che richiedono autenticazione obbligatoria (es.
    checkout, storico ordini) devono comunque verificare
    `request.user.is_authenticated` esplicitamente.
    """

    # Scopo: Ammette anonimo OR SHOP_CUSTOMER. Altri ruoli -> 403.
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            # Scopo: Endpoint pubblici (catalogo) ammettono anonimo.
            return True

        cache = ZeroERPPermission._get_cache(request)
        try:
            ruolo = PermissionResolver.get_ruolo_applicativo(user, cache=cache)
            if ruolo in RUOLI_SHOP:
                return True

            if ruolo == RUOLO_APPLICATIVO_DISABILITATO:
                self.message = "Utente disabilitato."
                return False

            logger.warning(
                "security.shop_denied user_id=%s ruolo=%s path=%s",
                user.id, ruolo, request.path,
            )
            self.message = "Accesso riservato ai clienti shop."
            return False
        finally:
            ZeroERPPermission._save_cache_to_redis(request)
