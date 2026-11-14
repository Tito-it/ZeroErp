# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API del verbo sui fondi fattura — `DELETE /vendite/fondi-fattura/<id>/`
#        (BE-4 di brief-db-fondo-fattura-ricalcolo-e-governo §9.3).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) FondoFatturaDeleteApiTests.test_delete_ok_envelope
2) FondoFatturaDeleteApiTests.test_delete_senza_idempotency_key
3) FondoFatturaDeleteApiTests.test_delete_requires_jwt
4) FondoFatturaDeleteApiTests.test_id_dal_path_non_dal_corpo
5) FondoFatturaDeletePermessoTests.test_delete_lo_decide_l_azione_non_l_area

⭐ PERCHE' QUESTO FILE ESISTE, quando il service ha gia' i suoi test.
I test del service girano sulla funzione: non attraversano la ROTTA, il metodo
HTTP, il controllo della `Idempotency-Key` ne' l'envelope. Il verbo qui e' un
`DELETE` con CORPO VUOTO passato a `handle_post_json`, che nasce per le POST e
fa `parse_json_body`: se quel parsing non reggesse il vuoto, ogni chiamata
tornerebbe 400 e tutti i test del service resterebbero verdi.
"""

from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase

from apps.core.api.permissions import MotivoDiniego, ZeroERPPermission
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova
from apps.vendite.api.views_fondi_fattura import ApiFondoFatturaDelete

_URL = "/api/v1/vendite/fondi-fattura/987/"
_ESITO = {
    "status": "deleted",
    "fondo_source_id": 987,
    "deleted_righe": 1,
    "deleted_fondi": 1,
    "deleted_source": 1,
}


class FondoFatturaDeleteApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: il giro completo — rotta, metodo, chiave, envelope e contatori.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.vendite.api.views_fondi_fattura.fn_cancella_fondo_fattura")
    def test_delete_ok_envelope(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _ESITO
        response = self.client.delete(_URL, headers={"idempotency-key": "k-1"})
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "deleted")
        self.assertEqual(data["deleted_source"], 1)

    # Scopo: ⭐ la chiave e' OBBLIGATORIA, e il gesto e' irreversibile: senza,
    #        un doppio invio riceverebbe un errore per un'operazione riuscita.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.vendite.api.views_fondi_fattura.fn_cancella_fondo_fattura")
    def test_delete_senza_idempotency_key(self, mocked_fn, _mock_auth):
        response = self.client.delete(_URL)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"]["code"], "E_IDEMPOTENCY_KEY_REQUIRED"
        )
        # ⛔ E il service NON dev'essere stato chiamato: un rifiuto che arriva
        #    DOPO la cancellazione sarebbe la peggiore delle risposte.
        mocked_fn.assert_not_called()

    # Scopo: nessun accesso anonimo a un gesto che cancella denaro.
    def test_delete_requires_jwt(self):
        response = self.client.delete(_URL, headers={"idempotency-key": "k-2"})
        self.assertEqual(response.status_code, 401)

    # Scopo: ⚠️ l'id viene dal PATH e il corpo si ignora. Un corpo che potesse
    #        dirottare il bersaglio sarebbe un modo per cancellare l'atto di un
    #        altro passando dal permesso sul proprio.
    @patch(
        "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
        return_value=(Mock(), None),
    )
    @patch("apps.vendite.api.views_fondi_fattura.fn_cancella_fondo_fattura")
    def test_id_dal_path_non_dal_corpo(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _ESITO
        response = self.client.delete(
            _URL,
            data='{"fondo_source_id": 1}',
            content_type="application/json",
            headers={"idempotency-key": "k-3"},
        )
        self.assertEqual(response.status_code, 200)
        mocked_fn.assert_called_once_with(fondo_source_id=987)


class FondoFatturaDeletePermessoTests(SimpleTestCase):
    # Scopo: ⭐ il cancello e' l'azione `governa_fondo_fattura` (`pericolosa`),
    #        e si prova sul COMPORTAMENTO della catena per un DELETE, non sul
    #        nome dell'attributo: fino al 2026-11-14 il test pinnava
    #        `post_permission`, che per un DELETE non legge nessuno, e il gesto
    #        passava col solo livello sull'area vendite.
    def tearDown(self) -> None:
        patch.stopall()

    def _valuta(self, *, azione_concessa: bool):
        resolver = patch("apps.core.api.permissions.PermissionResolver").start()
        resolver.get_ruolo_applicativo.return_value = RUOLO_APPLICATIVO_OPERATORE
        resolver.is_super_admin.return_value = False
        # Il livello sull'area concede tutto: decide solo l'azione.
        resolver.get_livello_area.return_value = "TUTTO"
        resolver.get_livello_oggetto.return_value = "TUTTO"
        resolver.check_azione.return_value = azione_concessa
        esito = ZeroERPPermission.valuta(
            operatore_di_prova(user_id=3), ApiFondoFatturaDelete, method="DELETE", cache={},
        )
        return esito, resolver

    def test_delete_lo_decide_l_azione_non_l_area(self):
        esito, resolver = self._valuta(azione_concessa=False)
        self.assertFalse(esito.consentito)
        self.assertIs(esito.motivo, MotivoDiniego.AZIONE_NEGATA)
        self.assertEqual(esito.azione, "governa_fondo_fattura")
        resolver.check_azione.assert_called_once()

        esito, _ = self._valuta(azione_concessa=True)
        self.assertTrue(esito.consentito)
        self.assertEqual(ApiFondoFatturaDelete.area_funzionale, "vendite")
