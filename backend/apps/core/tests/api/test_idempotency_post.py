# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio della regola «una POST che scrive porta l'Idempotency-Key»
#        (decisione Tid 2026-10-20, brief-be-verifica-documentazione-api §A5),
#        applicata per costruzione in `_ApiViewBase.initial()`.
#        Fino a quel giorno la key era una scelta della singola view: 82
#        scritture su 457 la chiedevano, senza un criterio.
# ------------------------------------------------------------
"""Indice test:
1. test_post_senza_key_e_400
2. test_post_con_key_passa
3. test_post_che_legge_non_la_chiede
4. test_view_senza_post_lascia_il_405
5. test_refuso_del_tipo_segue_i_permessi
6. test_patch_put_delete_get_non_la_chiedono
7. test_le_quattro_porte_ereditano_la_regola
8. test_le_post_che_leggono_lo_dichiarano
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.api.base_views import (
    AdminAPIView,
    DomainAPIView,
    PortaleAPIView,
    ShopAPIView,
    _ApiViewBase,
)
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.service_errors import ServiceError

_CHIAVE = "apps.core.api.base_views.get_idempotency_key"
# `initial()` di DRF (autenticazione, permessi, throttle) e' gia' provato da
# DRF: qui si guarda solo cio' che la base aggiunge DOPO.
_DRF_INITIAL = "rest_framework.views.APIView.initial"


class _Scrive(DomainAPIView):
    area_funzionale = "vendite"

    def post(self, request):  # pragma: no cover - mai chiamata
        raise AssertionError


class _Legge(_Scrive):
    post_accesso = "view"


# Senza `post`: una POST e' un 405 di DRF, non un 400 sulla key.
class _SoloGet(DomainAPIView):
    area_funzionale = "vendite"


# Un refuso del tipo di accesso: i permessi lo trattano da scrittura
# (fail-closed), e il gate della key segue la STESSA regola.
class _Refuso(_Scrive):
    post_accesso = "View"


def _initial(view_class, metodo: str) -> None:
    request = MagicMock()
    request.method = metodo
    request.user = MagicMock(is_authenticated=True)
    with patch(_DRF_INITIAL):
        view_class().initial(request)


class IdempotencyPostTests(TestCase):
    def test_post_senza_key_e_400(self) -> None:
        with patch(_CHIAVE, return_value=None), self.assertRaises(ServiceError) as ctx:
            _initial(_Scrive, "POST")
        self.assertEqual(ctx.exception.code, "E_IDEMPOTENCY_KEY_REQUIRED")
        self.assertEqual(ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 400)

    def test_post_con_key_passa(self) -> None:
        with patch(_CHIAVE, return_value="k"):
            _initial(_Scrive, "POST")

    def test_post_che_legge_non_la_chiede(self) -> None:
        with patch(_CHIAVE, return_value=None):
            _initial(_Legge, "POST")

    def test_view_senza_post_lascia_il_405(self) -> None:
        with patch(_CHIAVE, return_value=None):
            _initial(_SoloGet, "POST")

    def test_refuso_del_tipo_segue_i_permessi(self) -> None:
        with patch(_CHIAVE, return_value=None), self.assertRaises(ServiceError):
            _initial(_Refuso, "POST")

    def test_patch_put_delete_get_non_la_chiedono(self) -> None:
        for metodo in ("GET", "PATCH", "PUT", "DELETE"):
            with self.subTest(metodo=metodo), patch(_CHIAVE, return_value=None):
                _initial(_Scrive, metodo)

    def test_le_quattro_porte_ereditano_la_regola(self) -> None:
        for porta in (DomainAPIView, AdminAPIView, PortaleAPIView, ShopAPIView):
            with self.subTest(porta=porta.__name__):
                self.assertTrue(issubclass(porta, _ApiViewBase))

    # ⚠️ Il verso opposto: una POST che LEGGE e non lo dichiara chiede la key e
    #    il permesso di scrittura. Le letture trovate il 2026-10-20 restano
    #    dichiarate (se una perde l'attributo, il frontend riceve un 400).
    def test_le_post_che_leggono_lo_dichiarano(self) -> None:
        from apps.amm_software.api.email_views import EmailTemplatePreviewView
        from apps.anagrafiche.api.views_indirizzi import IndirizziCheckDuplicatoView
        from apps.anagrafiche.api.views_soggetti import GeneraCFView, ValidaCFPIVAView
        from apps.vendite.api.views_iva import IvaResolveView
        from apps.vendite.api.views_pricing import PricingDiagnoseView, PricingResolveView

        for view in (
            EmailTemplatePreviewView, IndirizziCheckDuplicatoView, GeneraCFView,
            ValidaCFPIVAView, IvaResolveView, PricingDiagnoseView, PricingResolveView,
        ):
            with self.subTest(view=view.__name__):
                self.assertEqual(getattr(view, "post_accesso", None), "view")
