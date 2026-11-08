# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Un campo obbligatorio ASSENTE dal corpo e' un 400 col codice che la
#        pagina dell'endpoint documenta, e col campo. Fino al 2026-10-20 le view
#        lo leggevano con `payload["x"]`: un KeyError, cioe' un 500 `E_GENERICO`
#        per un errore di chi chiama. Service mockati, nessun accesso DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_campo_assente_e_400_col_codice_documentato — POST pratica, stato pratica,
   stato flusso, genera pratica, competenze flusso: 400, campo, service non chiamato
"""

import json
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.pratiche.tests.api.test_flussi_api import _mock_flusso_row


_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_VIEWS = "apps.pratiche.api.views"


class CampiObbligatoriCorpoApiTests(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(f"{_VIEWS}.PraticheRepository", autospec=True)
    def test_campo_assente_e_400_col_codice_documentato(self, MockRepo, _auth) -> None:
        MockRepo.return_value.get_flusso.return_value = _mock_flusso_row(5, pratica_id=1)
        casi = (
            # (url, corpo, servizio da non chiamare, codice, campo)
            ("/api/v1/pratiche/", {"tipo_prestazione_id": 5},
             "pratiche_service.crea_pratica", "E_PRATICA_VALIDATION", "emittente_fiscale_id"),
            ("/api/v1/pratiche/", {"emittente_fiscale_id": 10},
             "pratiche_service.crea_pratica", "E_PRATICA_VALIDATION", "tipo_prestazione_id"),
            ("/api/v1/pratiche/1/stato/", {},
             "pratiche_service.cambia_stato_pratica", "E_PRATICA_VALIDATION", "nuovo_stato"),
            ("/api/v1/pratiche/1/flussi/5/stato/", {},
             "pratiche_service.completa_flusso", "E_FLUSSO_VALIDATION", "nuovo_stato"),
            ("/api/v1/pratiche/1/flussi/5/genera/", {},
             "generazione_service.genera_pratica_manuale", "E_INVALID_ID", "regola_id"),
            ("/api/v1/pratiche/competenze-flussi/",
             {"unita_organizzativa_id": 2, "risorsa_umana_id": 3},
             "pratiche_service.crea_competenza_flusso", "E_INVALID_ID", "template_flusso_id"),
        )
        for url, corpo, servizio, codice, campo in casi:
            with self.subTest(url=url, campo=campo), patch(f"{_VIEWS}.{servizio}") as svc:
                resp = self.client.post(url, data=json.dumps(corpo), content_type="application/json")
                self.assertEqual(resp.status_code, 400, resp.content)
                errore = resp.json()["error"]
                self.assertEqual(errore["code"], codice)
                self.assertIn(campo, json.dumps(errore))
                svc.assert_not_called()
