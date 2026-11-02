# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le due view di restore per id dei lookup cross-dominio (istanze
#        utility, contesto soggetto/ruolo) passano al service lo scope
#        emittente risolto per l'UTENTE, non un `None`.
# Note: ⚠️ La regola la prova `tests/db/test_lookup_restore_scope_db.py` sul
#       repository; qui si prova il TRASPORTO. Le view hanno `skip_area_check`
#       e `emittente_ids=None` e' il bypass: una view che passasse None
#       riaprirebbe D10-bis con tutti i test del repository verdi.
#       Mock del service e JWT auth, nessun accesso DB (compatibilita' CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_restore_istanza_propaga_scope_emittente
 2) test_restore_ruolo_propaga_scope_emittente
 3) test_restore_soggetto_propaga_scope_emittente
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC_IU = "apps.anagrafiche.api.views_istanze_utility.IstanzeUtilityService"
_PERM_IU = "apps.anagrafiche.api.views_istanze_utility.PermissionResolver"
_SVC_SOG = "apps.anagrafiche.api.views_soggetti.SoggettiService"
_PERM_SOG = "apps.anagrafiche.api.views_soggetti.PermissionResolver"

_FAKE_UUID = "00000000-0000-0000-0000-000000000001"


class TestLookupRestoreScopeApi(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        # Cache del throttle condivisa dalla suite (vedi test_clienti_api).
        cache.clear()

    # 1. Restore istanza: lo scope dell'utente arriva al service.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_IU)
    @patch(_SVC_IU)
    def test_restore_istanza_propaga_scope_emittente(self, mock_svc_cls, mock_perm, _auth):
        mock_perm.get_emittenti_sr_ids.return_value = [11, 22]
        mock_svc_cls.return_value.get_lookup_by_id.return_value = {"id": 900}
        resp = self.client.get("/api/v1/anagrafiche/istanze-utility/900/lookup/")
        self.assertEqual(resp.status_code, 200)
        mock_svc_cls.return_value.get_lookup_by_id.assert_called_once_with(
            900, emittente_ids=[11, 22],
        )

    # 2. Restore riga ruolo: idem.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_SOG)
    @patch(_SVC_SOG)
    def test_restore_ruolo_propaga_scope_emittente(self, mock_svc_cls, mock_perm, _auth):
        mock_perm.get_emittenti_sr_ids.return_value = [11, 22]
        mock_svc_cls.return_value.get_ruoli_lookup_by_id.return_value = {"soggetto_ruolo_id": 165}
        resp = self.client.get("/api/v1/anagrafiche/soggetti-ruoli/lookup-by-id/?soggetto_ruolo_id=165")
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_svc_cls.return_value.get_ruoli_lookup_by_id.call_args.kwargs
        self.assertEqual(kwargs["emittente_ids"], [11, 22])

    # 3. Restore riga «senza ruolo»: la chiave alternativa non e' una porta laterale.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_SOG)
    @patch(_SVC_SOG)
    def test_restore_soggetto_propaga_scope_emittente(self, mock_svc_cls, mock_perm, _auth):
        mock_perm.get_emittenti_sr_ids.return_value = [11, 22]
        mock_svc_cls.return_value.get_ruoli_lookup_by_id.return_value = {"soggetto_ruolo_id": None}
        resp = self.client.get(f"/api/v1/anagrafiche/soggetti-ruoli/lookup-by-id/?soggetto_id={_FAKE_UUID}")
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_svc_cls.return_value.get_ruoli_lookup_by_id.call_args.kwargs
        self.assertEqual(kwargs["soggetto_id"], _FAKE_UUID)
        self.assertEqual(kwargs["emittente_ids"], [11, 22])
