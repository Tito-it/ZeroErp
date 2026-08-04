# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Sequence

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed

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

    I claim custom sono agganciati al refresh token: SimpleJWT li copia
    in automatico sull'access token tramite la property `access_token`
    (eccezione: i `no_copy_claims` standard — exp, jti, token_type).
    """

    allowed_ruoli_applicativi: Sequence[str] = ()
    _auth_repo: AuthRepository = AuthRepository()

    # Scopo: Esegue validate SimpleJWT standard + risoluzione identita veste
    # + injection dei claim custom. Fallisce se l'utente non ha la veste.
    def validate(self, attrs: dict) -> dict:
        # Step 1: verifica credenziali. super() popola self.user.
        data = super().validate(attrs)

        # Step 2: risolve l'identita dell'utente per la veste del namespace.
        identita = self._auth_repo.find_identita_attiva_for_ruoli(
            auth_user_id=self.user.id,
            ruoli_applicativi=self.allowed_ruoli_applicativi,
        )
        if identita is None:
            raise VesteNonAttivaError()

        # Step 3: rigenera i token con claim custom. super().validate ha
        # gia' chiamato internamente get_token() e scritto i token base in
        # `data`; qui li sovrascriviamo con una copia arricchita dei claim
        # custom. Il doppio get_token() e' un costo in-memory trascurabile
        # (nessuna query DB) e preferibile all'alternativa — trasformare
        # get_token() da classmethod a instance-method — che romperebbe
        # il contratto SimpleJWT.
        refresh = self.get_token(self.user)
        refresh[JWT_CLAIM_IDENTITA_ID] = int(identita["id"])
        refresh[JWT_CLAIM_RUOLO_APPLICATIVO] = identita["ruolo_applicativo"]

        # Step 4: emittente attivo (impersonazione di scope). Solo per gli
        # OPERATORI: portale e shop non hanno un emittente dentro cui lavorare,
        # e un claim inerte li' sarebbe solo rumore in un token firmato.
        #   - operatore  → il suo emittente di permesso;
        #   - super admin → la preferenza salvata, se ancora valida;
        #   - nessuno dei due → claim OMESSO = «Tutti gli emittenti», e il FE
        #     chiede di scegliere (`deve_scegliere` in /me/).
        # Il claim si aggancia al refresh: SimpleJWT lo copia sull'access.
        if identita["ruolo_applicativo"] == RUOLO_APPLICATIVO_OPERATORE:
            attivo = EmittenteAttivoService().risolvi_per_login(self.user.id)
            if attivo is not None:
                refresh[JWT_CLAIM_EMITTENTE_ATTIVO_ID] = int(attivo)

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)
        return data


# ── Sottoclassi concrete per namespace (§8.3.3) ─────────────
# Ogni namespace di login espone SOLO il suo subset di ruoli_applicativi.
# Un operatore che tenta /portale/token/ o un cliente che tenta /admin/token/
# riceve 403 E_VESTE_NON_ATTIVA senza enumeration di quali ruoli esistono.


class AdminTokenSerializer(MultiVesteTokenSerializer):
    """Login per /api/v1/admin/token/ — solo operatori interni."""

    allowed_ruoli_applicativi = (RUOLO_APPLICATIVO_OPERATORE,)


class PortaleTokenSerializer(MultiVesteTokenSerializer):
    """Login per /api/v1/portale/token/ — clienti e fornitori del portale."""

    allowed_ruoli_applicativi = (
        RUOLO_APPLICATIVO_CLIENTE_PORTALE,
        RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    )


class ShopTokenSerializer(MultiVesteTokenSerializer):
    """Login per /api/v1/shop/token/ — shop B2C autenticato."""

    allowed_ruoli_applicativi = (RUOLO_APPLICATIVO_SHOP_CUSTOMER,)
