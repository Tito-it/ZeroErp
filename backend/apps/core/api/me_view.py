# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Endpoint GET /api/v1/core/me/ — profilo utente completo.
#        Restituisce dati utente, soggetto, risorse umane e emittente
#        fiscale associato, chiamando script.fn_get_user_profile.
# ------------------------------------------------------------

from __future__ import annotations

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.request import Request
from apps.core.api.base_views import DomainAPIView

from apps.core.api.success_responses import success_response
from apps.core.db.core_repository import CoreRepository
from apps.core.services.permissions_resolver import PermissionResolver


class UserProfileView(DomainAPIView):
    """Profilo utente corrente — dati soggetto, risorse umane, emittente."""

    skip_area_check = True

    @extend_schema(
        summary="Profilo utente corrente",
        description=(
            "Restituisce il profilo completo dell'utente autenticato: "
            "dati anagrafici (soggetto), risorse umane, ruolo_sistema, "
            "dati emittente fiscale associato (se presente), flag "
            "`is_admin_globale` derivato dalla regola Q1 del refactor "
            "operatore-emittenti, e mappa permessi per area funzionale. "
            "Il payload base e' prodotto dalla funzione DB "
            "script.fn_get_user_profile; il flag `is_admin_globale` viene "
            "calcolato in Python come "
            "`ruolo_sistema=='ADMIN' AND user_emittente_fiscale_id IS NULL`."
        ),
        responses={
            200: inline_serializer(
                name="UserProfileResponse",
                fields={
                    "data": inline_serializer(
                        name="UserProfileData",
                        fields={
                            "utente": serializers.DictField(
                                help_text="Dati auth_user: id, username, first_name, last_name, email."
                            ),
                            "ruolo_sistema": serializers.CharField(
                                allow_null=True,
                                help_text=(
                                    "ADMIN | OPERATIVO | DISABILITATO | null. "
                                    "Legacy — ricostruito da is_super_admin + "
                                    "ruolo_applicativo. Nuovi consumer usino "
                                    "direttamente is_super_admin + ruolo_applicativo."
                                ),
                            ),
                            "is_super_admin": serializers.BooleanField(
                                help_text=(
                                    "True se l'utente ha binding attivo al "
                                    "profilo SUPER_ADMIN (id 9100). Letto via "
                                    "PermissionResolver.is_super_admin."
                                ),
                            ),
                            "ruolo_applicativo": serializers.CharField(
                                allow_null=True,
                                help_text=(
                                    "Ruolo applicativo dell'identita' attiva: "
                                    "OPERATORE | CLIENTE_PORTALE | "
                                    "FORNITORE_PORTALE | SHOP_CUSTOMER | "
                                    "API_CLIENT | DISABILITATO | null. "
                                    "Letto via PermissionResolver.get_ruolo_applicativo."
                                ),
                            ),
                            "risorse_umane": serializers.DictField(
                                help_text="Dati risorsa umana: qualifica, UO, validita'."
                            ),
                            "soggetto": serializers.DictField(
                                help_text="Dati soggetto dell'utente (da fn_get_soggetto_dati_by_ruolo)."
                            ),
                            "emittente": serializers.DictField(
                                allow_null=True,
                                help_text="Dati emittente fiscale + soggetto ditta (null se non associato).",
                            ),
                            "is_admin_globale": serializers.BooleanField(
                                help_text=(
                                    "True se l'utente e' admin globale (ruolo_sistema=ADMIN "
                                    "+ nessuna riga in user_emittenti_fiscali). False per "
                                    "operatori e admin di emittente. Refactor operatore-"
                                    "emittenti, decisione Q1."
                                ),
                            ),
                            "permessi_area": serializers.DictField(
                                help_text=(
                                    "Mappa livello accesso per area funzionale: "
                                    "{schema_db: 'TUTTO'|'LETTURA'|'BLOCCATO'}. "
                                    "Prodotta da script.fn_get_user_permissions_map."
                                ),
                            ),
                        },
                    ),
                    "meta": serializers.DictField(required=False),
                },
            )
        },
    )
    # Scopo: Restituisce via GET il profilo completo dell'utente autenticato.
    # Chiama script.fn_get_user_profile(auth_user_id) e arricchisce con
    # is_admin_globale (refactor operatore-emittenti Q1: admin senza riga
    # in user_emittenti_fiscali = admin globale; admin con riga = admin
    # di emittente).
    def get(self, request: Request):
        repo = CoreRepository()
        profile = repo.get_user_profile(request.user.id)
        profile["is_admin_globale"] = self._compute_is_admin_globale(profile)
        # Multi-face auth Stage B: espone i campi nativi (is_super_admin +
        # ruolo_applicativo) in affiancamento al legacy ruolo_sistema. I
        # consumer FE ne leggono direttamente senza ricostruzione.
        profile["is_super_admin"] = PermissionResolver.is_super_admin(request.user)
        profile["ruolo_applicativo"] = PermissionResolver.get_ruolo_applicativo(
            request.user
        )
        return success_response(profile)

    # Scopo: Calcola il flag is_admin_globale dal profilo. Regola Q1 del
    # refactor operatore-emittenti: ADMIN senza riga in user_emittenti_fiscali
    # = admin globale (vede tutti gli emittenti). ADMIN con riga = admin di
    # emittente (vede solo il suo). OPERATIVO non e' mai admin.
    @staticmethod
    def _compute_is_admin_globale(profile: dict) -> bool:
        if profile.get("ruolo_sistema") != "ADMIN":
            return False
        emittente = profile.get("emittente") or {}
        # user_emittente_fiscale_id valorizzato → admin di emittente
        # (riga in config.user_emittenti_fiscali). NULL → admin globale.
        return emittente.get("user_emittente_fiscale_id") is None
