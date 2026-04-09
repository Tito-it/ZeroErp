# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Base classes per view API.
#        DomainAPIView: view di dominio con JWT + permessi area.
#        AdminAPIView: view admin con JWT + check diretto ruolo_sistema.
#        Ref: docs/it/dev/api.md
# ------------------------------------------------------------

from rest_framework.views import APIView

from apps.core.api.jwt_audit_authentication import JwtAuditAuthentication
from apps.core.api.permissions import IsAdminZeroERP, ZeroERPPermission


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

    Check diretto ruolo_sistema = ADMIN. skip_area_check implicito
    perche' IsAdminZeroERP bypassa il resolver aree.

    Usa `JwtAuditAuthentication` (vedi DomainAPIView).
    """
    authentication_classes = [JwtAuditAuthentication]
    permission_classes = [IsAdminZeroERP]
    skip_area_check = True
