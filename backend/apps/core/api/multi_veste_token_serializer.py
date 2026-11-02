# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Serializer login multi-veste. Post autenticazione credenziali,
#   risolve l'identita digitale attiva dell'utente con ruolo_applicativo
#   nel subset ammesso dal namespace chiamante (admin/portale/shop) e
#   la inietta nei claim JWT (identita_id, ruolo_applicativo).
#   Solleva VesteNonAttivaError (403 E_VESTE_NON_ATTIVA) se l'utente non
#   ha alcuna identita valida per il namespace — distinto dal 401
#   credenziali errate per non innescare blocco-tentativi.
#   Usato da AdminTokenView / PortaleTokenView / ShopTokenView (§8.3.3).
#   La chiave d'ingresso e' della porta (L-4, D-9): il nome utente per admin,
#   l'email per portale e shop (`_IngressoPerEmailSerializer`).
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from django.contrib.auth.models import User
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.api.token_serializers import SidTokenObtainPairSerializer
from apps.core.db.auth_repository import AuthRepository
from apps.core.services.auth_constants import (
    JWT_CLAIM_EMITTENTE_ATTIVO_ID,
    JWT_CLAIM_IDENTITA_ID,
    JWT_CLAIM_RUOLO_APPLICATIVO,
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    RUOLO_APPLICATIVO_OPERATORE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
)
from apps.core.services.credenziale_ingresso import (
    credenziale_per_email,
    credenziale_per_nome_utente,
    normalizza_email,
)
from apps.core.services.emittente_attivo_service import EmittenteAttivoService

E_VESTE_NON_ATTIVA = "E_VESTE_NON_ATTIVA"


class VesteNonAttivaError(AuthenticationFailed):
    """Identita attiva assente per il namespace richiesto.

    Credenziali OK ma l'utente non ha la veste prevista per il namespace
    di login (es. operatore che tenta /portale/token/ senza identita
    CLIENTE_PORTALE/FORNITORE_PORTALE). Distinto dal 401 di credenziali
    errate: non deve far incrementare i contatori di tentativi falliti
    ne' scatenare blocco utente/IP.
    """

    status_code = status.HTTP_403_FORBIDDEN
    default_code = E_VESTE_NON_ATTIVA
    default_detail = "Non hai accesso a questo canale."


# Scopo: Emette il refresh token di una SESSIONE NUOVA in una veste — la
#        catena unica per chi apre una sessione: login e cambio password.
#        Sessione nuova vuol dire `sid` nuovo (con l'OutstandingToken
#        allineato, via `SidTokenObtainPairSerializer.get_token`), i due claim
#        della veste (`identita_id`, `ruolo_applicativo`) e, solo per gli
#        OPERATORI, l'emittente attivo risolto come al login:
#          - operatore   → il suo emittente di permesso;
#          - super admin → la preferenza salvata, se ancora valida;
#          - nessuno dei due → claim OMESSO = «Tutti gli emittenti», e il FE
#            chiede di scegliere (`deve_scegliere` in /me/).
#        Portale e shop non hanno un emittente dentro cui lavorare: un claim
#        inerte li' sarebbe solo rumore in un token firmato.
#        I claim si agganciano al refresh: SimpleJWT li copia sull'access.
#
#        ⛔ Regola del 2 (2026-09-24, ok Tid): fino a quel giorno la catena
#        viveva solo nel serializer del login, e il cambio password emetteva
#        con `RefreshToken.for_user` — un token SENZA veste, che la richiesta
#        dopo rifiutava con 401 `E_JWT_SENZA_IDENTITA` (M-2 dell'analisi
#        difetti). Chi apre una sessione passa di qui.
#        `identita` e' la riga della veste: servono `id` e `ruolo_applicativo`.
def emetti_refresh_veste(user: Any, identita: Mapping[str, Any]) -> RefreshToken:
    refresh = SidTokenObtainPairSerializer.get_token(user)
    refresh[JWT_CLAIM_IDENTITA_ID] = int(identita["id"])
    refresh[JWT_CLAIM_RUOLO_APPLICATIVO] = identita["ruolo_applicativo"]
    if identita["ruolo_applicativo"] == RUOLO_APPLICATIVO_OPERATORE:
        attivo = EmittenteAttivoService().risolvi_per_login(user.id)
        if attivo is not None:
            refresh[JWT_CLAIM_EMITTENTE_ATTIVO_ID] = int(attivo)
    return refresh


class MultiVesteTokenSerializer(SidTokenObtainPairSerializer):
    """Serializer login per namespace multi-veste (admin / portale / shop).

    Eredita da SidTokenObtainPairSerializer (non da TokenObtainPairSerializer
    diretto) per preservare il claim `sid` (session ID stabile, usato dal
    session audit). Le nostre view settano `serializer_class` esplicito:
    senza questa catena il TOKEN_OBTAIN_SERIALIZER configurato in
    SIMPLE_JWT non viene piu' applicato.

    Le sottoclassi (AdminTokenView / PortaleTokenView / ShopTokenView,
    §8.3.3) settano `allowed_ruoli_applicativi` con i ruoli ammessi dal
    namespace. Dopo la verifica credenziali:
      1. cerca l'identita attiva dell'utente con ruolo in
         `allowed_ruoli_applicativi`;
      2. inietta nei token i claim `identita_id` + `ruolo_applicativo`;
      3. solleva VesteNonAttivaError se l'utente non ha la veste.

    I claim li inietta `emetti_refresh_veste`, la catena comune a chi apre
    una sessione (login e cambio password).
    """

    allowed_ruoli_applicativi: Sequence[str] = ()
    _auth_repo: AuthRepository = AuthRepository()

    # Scopo: La credenziale del nome tentato, cercata come la cerca
    # `authenticate` per questa porta (best-effort, None se non c'e'). Qui la
    # chiave e' il nome utente: stessa ricerca di `ModelBackend`
    # (`get_by_natural_key`, uguaglianza esatta). Le porte che entrano per
    # email la ridefiniscono (`_IngressoPerEmailSerializer`).
    # ⛔ Il nome arriva gia' normalizzato dal campo del serializer: lookup,
    #    `authenticate` e impronta del freno leggono lo STESSO valore.
    @classmethod
    def trova_credenziale(cls, nome: str) -> User | None:
        return credenziale_per_nome_utente(nome)

    # Scopo: Esegue validate SimpleJWT standard + risoluzione identita veste
    # + injection dei claim custom. Fallisce se l'utente non ha la veste.
    def validate(self, attrs: dict) -> dict:
        # Step 1: verifica credenziali. super() popola self.user.
        data = super().validate(attrs)
        # `super().validate` solleva AuthenticationFailed se la credenziale non
        # passa: qui `self.user` c'e' per costruzione.
        assert self.user is not None

        # Step 2: risolve l'identita dell'utente per la veste del namespace.
        identita = self._auth_repo.find_veste_utilizzabile_per_ruoli(
            auth_user_id=self.user.id,
            ruoli_applicativi=self.allowed_ruoli_applicativi,
        )
        if identita is None:
            raise VesteNonAttivaError()

        # Step 3: rigenera i token con i claim della veste. super().validate
        # ha gia' chiamato internamente get_token() e scritto i token base in
        # `data`; qui li sovrascriviamo con quelli emessi dal BB della veste.
        # Il doppio get_token() costa due scritture (INSERT
        # dell'OutstandingToken e UPDATE del `sid`) per un token che non esce
        # mai dalla view: e' preferibile all'alternativa — trasformare
        # get_token() da classmethod a instance-method — che romperebbe il
        # contratto SimpleJWT.
        refresh = emetti_refresh_veste(self.user, identita)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)
        return data


# Scopo: Il campo d'ingresso delle porte per email: `CharField` (spazi ai bordi
# tolti, vuoto rifiutato) piu' la normalizzazione dell'email. Nessun controllo
# di formato: un valore che non e' un'email non trova una credenziale e conta
# come un nome tentato qualunque, con le stesse risposte.
class EmailIngressoField(serializers.CharField):
    def to_internal_value(self, data: Any) -> str:
        return normalizza_email(super().to_internal_value(data))


class _IngressoPerEmailSerializer(MultiVesteTokenSerializer):
    """Base delle porte che entrano con l'EMAIL (portale, shop: L-4, D-9).

    Il campo del corpo e' `email`, e `authenticate(email=…)` arriva a
    `CredenzialePerEmailBackend`. ⭐ Regola del 2: due porte, una sede.
    """

    username_field = "email"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = EmailIngressoField(write_only=True)

    @classmethod
    def trova_credenziale(cls, nome: str) -> User | None:
        return credenziale_per_email(nome)


# ── Sottoclassi concrete per namespace (§8.3.3) ─────────────
# Ogni namespace di login espone SOLO il suo subset di ruoli_applicativi.
# Un operatore che tenta /portale/token/ o un cliente che tenta /admin/token/
# riceve 403 E_VESTE_NON_ATTIVA senza enumeration di quali ruoli esistono.


class AdminTokenSerializer(MultiVesteTokenSerializer):
    """Login per /api/v1/admin/token/ — solo operatori interni."""

    allowed_ruoli_applicativi = (RUOLO_APPLICATIVO_OPERATORE,)


class PortaleTokenSerializer(_IngressoPerEmailSerializer):
    """Login per /api/v1/portale/token/ — clienti e fornitori del portale, con l'email."""

    allowed_ruoli_applicativi = (
        RUOLO_APPLICATIVO_CLIENTE_PORTALE,
        RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    )


class ShopTokenSerializer(_IngressoPerEmailSerializer):
    """Login per /api/v1/shop/token/ — shop B2C autenticato, con l'email."""

    allowed_ruoli_applicativi = (RUOLO_APPLICATIVO_SHOP_CUSTOMER,)
