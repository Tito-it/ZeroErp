# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
from apps.core.api.cancello_obblighi import TUTTI_GLI_OBBLIGHI, obblighi_in_vigore

from apps.core.api.success_responses import success_response
from apps.core.db.auth_repository import AuthRepository
from apps.core.db.core_repository import CoreRepository
from apps.core.services.auth_constants import (
    JWT_CLAIM_EMITTENTE_ATTIVO_ID,
    JWT_CLAIM_IDENTITA_ID,
)
from apps.core.services.emittente_attivo_service import EmittenteAttivoService
from apps.core.services.fuso_aziendale import fuso_aziendale
from apps.core.api.endpoint_helpers import utente_autenticato_id


class UserProfileView(DomainAPIView):
    """Profilo utente corrente — dati soggetto, risorse umane, emittente."""

    skip_area_check = True
    # Il profilo e' dove il frontend legge gli obblighi pendenti: deve
    # rispondere anche quando ce n'e' uno (cancello_obblighi).
    obblighi_ammessi = TUTTI_GLI_OBBLIGHI

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
                                    "profilo SUPER_ADMIN (id 9100). Emesso da "
                                    "script.fn_get_user_profile (GUC-aware)."
                                ),
                            ),
                            "ruolo_applicativo": serializers.CharField(
                                allow_null=True,
                                help_text=(
                                    "Ruolo applicativo dell'identita' attiva: "
                                    "OPERATORE | CLIENTE_PORTALE | "
                                    "FORNITORE_PORTALE | SHOP_CUSTOMER | "
                                    "API_CLIENT | null. "
                                    "Emesso da script.fn_get_user_profile "
                                    "(GUC-first: la veste del JWT corrente)."
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
                            "permessi_oggetto": serializers.DictField(
                                help_text=(
                                    "Livello EFFETTIVO per ogni oggetto del catalogo "
                                    "config.area_model_overrides: "
                                    "{'app_label.model_name': 'TUTTO'|'LETTURA'|'BLOCCATO'}. "
                                    "Gia' risolto a DB (override, area dell'oggetto, "
                                    "tetto d'area): il frontend lo legge, non lo ricalcola. "
                                    "Un oggetto fuori catalogo vale l'area del suo app_label. "
                                    "Prodotta da script.fn_get_user_object_permissions_map "
                                    "(fino al 2026-10-04: i soli override grezzi)."
                                ),
                            ),
                            "azioni_abilitate": serializers.DictField(
                                help_text=(
                                    "Azioni di processo: {permission_codename: bool}, "
                                    "col tetto d'area (un'azione abilitata sotto "
                                    "un'area che non arriva al suo livello_minimo_area "
                                    "vale false). Prodotta da "
                                    "script.fn_get_user_actions_map."
                                ),
                            ),
                            "obblighi_pendenti": serializers.ListField(
                                child=serializers.ChoiceField(choices=sorted(TUTTI_GLI_OBBLIGHI)),
                                help_text=(
                                    "Gli obblighi della credenziale che il cancello fa "
                                    "rispettare, nell'ordine in cui si chiudono: il "
                                    "frontend porta alla pagina del primo."
                                ),
                            ),
                            "fuso_aziendale": serializers.CharField(
                                help_text=(
                                    "Nome IANA del fuso dell'azienda (es. "
                                    "'Europe/Rome'), dal parametro "
                                    "SYSTEM_FUSO_ORARIO via "
                                    "script.fn_fuso_operativo. Il frontend "
                                    "lo usa per l'«oggi» e per le ore a video: "
                                    "un solo fuso in tutta l'applicazione, "
                                    "non quello del browser."
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
        user_id = utente_autenticato_id(request)
        profile = repo.get_user_profile(user_id)
        # `is_super_admin` e `ruolo_applicativo` arrivano SEMPRE dal top-level
        # di `script.fn_get_user_profile` (GUC-aware dal 20260421-03/-05), e
        # `ruolo_sistema` non viene emesso dalla Fase 7 (29-04-2026).
        # ⛔ Fino al 2026-09-12 qui vivevano tre ripieghi «per funzioni DB
        # pre-cutover» — due `if not in profile` sul resolver e un `pop` della
        # chiave morta: software vivo che serviva dati che il modello non
        # produce piu' (analisi-software-per-dati-morti §2.3). Tolti.
        # `is_admin_globale` (refactor operatore-emittenti Q1) dipende da
        # `is_super_admin`, va calcolato dopo la lettura.
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
        # ⚠️ La cache seminata col valore GIA' pubblicato nel profilo, e non un
        # dizionario vuoto: `puo_scegliere` si decide sul bypass SUPER_ADMIN, e
        # senza il travaso `descrivi` interrogherebbe il database una seconda
        # volta nella stessa richiesta. Non e' (solo) il round-trip: due letture
        # indipendenti possono rispondere diverso, e questa risposta
        # dichiarerebbe `is_super_admin` in un campo e lo contraddirebbe
        # nell'altro. Una domanda, una risposta.
        profile["emittente_attivo"] = EmittenteAttivoService().descrivi(
            user_id, self._emittente_attivo_del_jwt(request),
            user=request.user,
            cache={"is_super_admin": bool(profile.get("is_super_admin"))},
        )
        # Gli obblighi che il cancello fa rispettare, nell'ordine (brief
        # sicurezza §3.4-bis, T-4): il guard del frontend porta alla pagina
        # che chiude il primo. La regola e' una, quella del cancello.
        profile["obblighi_pendenti"] = list(obblighi_in_vigore(user_id))
        # Il fuso dell'azienda per il frontend (brief un-solo-fuso-aziendale,
        # B-1): lo stesso valore che il backend usa, dalla stessa cache —
        # niente seconda lettura del parametro.
        profile["fuso_aziendale"] = fuso_aziendale().key
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
            auth_user_id=utente_autenticato_id(request),
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
