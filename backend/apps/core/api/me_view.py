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
from apps.core.db.auth_repository import AuthRepository
from apps.core.db.core_repository import CoreRepository
from apps.core.services.auth_constants import (
    JWT_CLAIM_EMITTENTE_ATTIVO_ID,
    JWT_CLAIM_IDENTITA_ID,
)
from apps.core.services.emittente_attivo_service import EmittenteAttivoService
from apps.core.services.permissions_resolver import PermissionResolver


class UserProfileView(DomainAPIView):
    """Profilo utente corrente — dati soggetto, risorse umane, emittente."""

    skip_area_check = True

    @extend_schema(
        summary="Profilo utente corrente",
        description=(
            "Restituisce il profilo completo dell'utente autenticato: "
            "dati anagrafici (soggetto), risorse umane, identita' "
            "multi-face (`is_super_admin`, `ruolo_applicativo`), dati "
            "emittente fiscale associato (se presente), flag "
            "`is_admin_globale` derivato dalla regola Q1 del refactor "
            "operatore-emittenti, e mappa permessi per area funzionale. "
            "Il payload base e' prodotto dalla funzione DB "
            "script.fn_get_user_profile; il flag `is_admin_globale` viene "
            "calcolato in Python come "
            "`is_super_admin AND user_emittente_fiscale_id IS NULL`."
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
                                    "True se l'utente e' admin globale "
                                    "(is_super_admin=True + nessuna riga in "
                                    "user_emittenti_fiscali). False per "
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
                            "identita": serializers.DictField(
                                allow_null=True,
                                help_text=(
                                    "§8.3.6: dettaglio dell'identita digitale "
                                    "specifica del JWT corrente (id, "
                                    "soggetto_ruolo_id, ruolo_applicativo, "
                                    "attivo, valido_dal/al, invito_inviato_at). "
                                    "None per token pre-refactor (difensivo). "
                                    "Il FE usa identita.id per mostrare la veste "
                                    "attiva all'utente con piu' identita."
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
    # is_admin_globale (refactor operatore-emittenti Q1) + dati identita
    # specifica del JWT (§8.3.6 multi-face: il JWT indica QUALE "veste"
    # sta usando l'utente tra le N attive possibili).
    def get(self, request: Request):
        repo = CoreRepository()
        profile = repo.get_user_profile(request.user.id)
        # Garantisce i campi nativi multi-face (is_super_admin +
        # ruolo_applicativo): `fn_get_user_profile` gia' li popola; il
        # fallback via resolver e' difensivo per scenari pre-migration o
        # funzioni DB pre-cutover. `is_admin_globale` (refactor operatore-
        # emittenti Q1) dipende da `is_super_admin`, va calcolato dopo.
        if "is_super_admin" not in profile:
            profile["is_super_admin"] = PermissionResolver.is_super_admin(
                request.user
            )
        if "ruolo_applicativo" not in profile:
            profile["ruolo_applicativo"] = PermissionResolver.get_ruolo_applicativo(
                request.user
            )
        # Rimuove eventuale `ruolo_sistema` proveniente dalla fn DB (post-
        # cutover §4.6.H.2 ma legacy a livello API): l'output e' multi-face
        # puro (Fase 7 amm-software).
        profile.pop("ruolo_sistema", None)
        profile["is_admin_globale"] = self._compute_is_admin_globale(profile)
        # §8.3.6: arricchisce con il blocco identita del JWT corrente.
        # Non tutti gli auth_user hanno una singola identita (modello 1:N):
        # il JWT porta l'identita_id preciso iniettato al login, e /me/
        # deve riflettere ESATTAMENTE quella veste (non una delle N).
        profile["identita"] = self._identita_del_jwt(request)
        # Impersonazione di scope: dentro quale emittente sta lavorando questa
        # SESSIONE (dal claim, non dalla preferenza salvata: dopo un passaggio
        # a «Tutti gli emittenti» i due valori divergono, ed è il claim che
        # comanda la GUC e quindi ciò che l'utente vede).
        profile["emittente_attivo"] = EmittenteAttivoService().descrivi(
            request.user.id, self._emittente_attivo_del_jwt(request),
        )
        return success_response(profile)

    # Scopo: Legge `emittente_attivo_id` dal JWT validato. Claim assente =
    # modalità «Tutti gli emittenti» (o token emesso prima del cantiere).
    @staticmethod
    def _emittente_attivo_del_jwt(request: Request) -> int | None:
        token = request.auth
        if token is None or not hasattr(token, "get"):
            return None
        valore = token.get(JWT_CLAIM_EMITTENTE_ATTIVO_ID)
        return int(valore) if valore is not None else None

    # Scopo: Legge identita_id dal JWT validato e ritorna il dettaglio
    # dell'identita, oppure None se il JWT non ha il claim (token
    # pre-refactor — in teoria gia' rifiutato da JwtAuditAuthentication
    # §8.3.4, quindi caso difensivo) o l'identita non appartiene
    # all'auth_user del JWT (guard anti-tampering in repo).
    @staticmethod
    def _identita_del_jwt(request: Request) -> dict | None:
        token = request.auth
        if token is None:
            return None
        identita_id = token.get(JWT_CLAIM_IDENTITA_ID) if hasattr(
            token, "get"
        ) else None
        if identita_id is None:
            return None
        return AuthRepository().get_identita_dettaglio(
            identita_id=int(identita_id),
            auth_user_id=int(request.user.id),
        )

    # Scopo: Calcola il flag is_admin_globale dal profilo. Regola Q1 del
    # refactor operatore-emittenti: super admin senza riga in
    # user_emittenti_fiscali = admin globale (vede tutti gli emittenti).
    # Super admin con riga = admin di emittente (vede solo il suo).
    # Non super admin non e' mai admin.
    @staticmethod
    def _compute_is_admin_globale(profile: dict) -> bool:
        if not profile.get("is_super_admin"):
            return False
        emittente = profile.get("emittente") or {}
        # user_emittente_fiscale_id valorizzato → admin di emittente
        # (riga in config.user_emittenti_fiscali). NULL → admin globale.
        return emittente.get("user_emittente_fiscale_id") is None
