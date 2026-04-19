# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Base classes per view API.
#        DomainAPIView: view di dominio con JWT + permessi area.
#        AdminAPIView: view admin con JWT + check SUPER_ADMIN.
#        PortaleAPIView: view portale clienti/fornitori.
#        ShopAPIView: view shop online (catalogo pubblico + clienti).
#        Ref: docs/it/dev/api.md
# ------------------------------------------------------------

from rest_framework.views import APIView

from apps.core.api.jwt_audit_authentication import JwtAuditAuthentication
from apps.core.api.permissions import (
    IsAdminZeroERP,
    PortaleBasePermission,
    ShopBasePermission,
    ZeroERPPermission,
)


class DomainAPIView(APIView):
    """Base per view di dominio con JWT + permessi area.

    Ogni sottoclasse DEVE definire `area_funzionale`.
    Opzionalmente: `is_search_endpoint = True` per throttling ricerca.

    Usa `JwtAuditAuthentication` (subclass di JWTAuthentication) per
    propagare l'identita utente come GUC PG dopo authenticate().
    Vedi guida risorse-umane-e-accessi.md sezione "Propagazione
    identita utente al database (GUC)".
    """
    authentication_classes = [JwtAuditAuthentication]
    permission_classes = [ZeroERPPermission]


class AdminAPIView(APIView):
    """Base per view riservate ad amministratori (Amm. Software).

    Check diretto binding SUPER_ADMIN tramite
    `PermissionResolver.is_super_admin`. skip_area_check implicito
    perche' `IsAdminZeroERP` bypassa il resolver aree.

    Usa `JwtAuditAuthentication` (vedi DomainAPIView).
    """
    authentication_classes = [JwtAuditAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True


class PortaleAPIView(APIView):
    """Base per view del portale clienti/fornitori (`/api/portale/*`).

    Richiede autenticazione JWT + `ruolo_applicativo` in
    `RUOLI_PORTALE` (CLIENTE_PORTALE, FORNITORE_PORTALE).

    Le view portale NON dichiarano `area_funzionale`: il set di
    endpoint portale e' deliberatamente ristretto (lettura propri
    dati) e non passa per la catena livello area. Lo scope dati e'
    applicato a livello DB (scope_policy + RLS).

    Ref: WIP sviluppo-multi-face-auth.md §13.4.13-14.
    """
    authentication_classes = [JwtAuditAuthentication]
    permission_classes = [PortaleBasePermission]
    skip_area_check = True


class ShopAPIView(APIView):
    """Base per view del negozio online (`/api/shop/*`).

    Ammette richieste anonime (catalogo pubblico) e autenticate con
    `ruolo_applicativo = SHOP_CUSTOMER`. Le view che richiedono
    autenticazione obbligatoria (checkout, ordini, profilo) devono
    verificare `request.user.is_authenticated` esplicitamente o usare
    un sotto-mixin dedicato.

    Ref: WIP sviluppo-multi-face-auth.md §13.4.13-14.
    """
    authentication_classes = [JwtAuditAuthentication]
    permission_classes = [ShopBasePermission]
    skip_area_check = True
