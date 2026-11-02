# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API del lookup risorse umane (`GET /anagrafiche/risorse-umane/lookup/`),
#        nato per il responsabile della commessa (brief-db-modifiche-certe-
#        ciclo-vendita-e-articolo, §5.5 voce 4). Presidia la FORMA della
#        risposta — `{"results": [...]}`, che e' quello che `useLookup` legge —
#        non solo lo status: una lista nuda sotto `data` da' un drawer bianco
#        con la suite verde (api.md §L'envelope di un lookup).
# ------------------------------------------------------------

"""
Indice test:
 1) test_la_rotta_esiste
 2) test_il_lookup_torna_l_envelope_results
 3) test_il_lookup_non_pretende_l_area_anagrafiche (skip_area_check)
 4) test_una_ricerca_troppo_corta_e_400
 5) test_il_service_passa_la_ricerca_al_repository (service, senza HTTP)
"""

from unittest.mock import Mock, patch

from django.test import Client
from django.urls import reverse

from apps.anagrafiche.services.anagrafiche_service import AnagraficheService
from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PERM = "apps.core.api.permissions.PermissionResolver"
_SVC = "apps.anagrafiche.api.views_risorse_umane.AnagraficheService"
_BASE = "/api/v1/anagrafiche/risorse-umane/lookup/"


class _UserStub:
    def __init__(self, user_id: int = 42) -> None:
        self.id = user_id
        self.is_authenticated = True
        self.is_superuser = False


class RisorseUmaneLookupApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        perm = patch(_PERM)
        resolver = perm.start()
        resolver.return_value.get_ruolo_applicativo.return_value = "OPERATORE"
        resolver.return_value.is_super_admin.return_value = False
        # ⭐ Livello d'area BLOCCATO su tutto: se la view guardasse l'area,
        #    risponderebbe 403 — e' cio' che prova il test 3.
        resolver.return_value.get_livello_area.return_value = "BLOCCATO"
        self.addCleanup(perm.stop)

    # 1. La rotta si risolve per nome.
    def test_la_rotta_esiste(self) -> None:
        self.assertEqual(reverse("anagrafiche-risorse-umane-lookup"), _BASE)

    # 2. La FORMA: `data` e' l'oggetto con `results`, mai la lista nuda.
    @patch(_AUTH, return_value=(_UserStub(), None))
    @patch(_SVC)
    def test_il_lookup_torna_l_envelope_results(self, mock_svc, _auth) -> None:
        righe = [{"id": 7, "display": "Bianchi Anna", "attivo": True}]
        mock_svc.return_value.lookup_risorse_umane.return_value = {"results": righe}
        resp = self.client.get(_BASE, HTTP_AUTHORIZATION="Bearer x")
        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        self.assertIsInstance(corpo["data"], dict)
        self.assertEqual(corpo["data"]["results"], righe)
        mock_svc.return_value.lookup_risorse_umane.assert_called_once_with(search=None)

    # 3. Lookup cross-dominio: lo consuma il drawer commessa (`vendite`), e con
    #    l'area `anagrafiche` BLOCCATA deve rispondere lo stesso.
    @patch(_AUTH, return_value=(_UserStub(), None))
    @patch(_SVC)
    def test_il_lookup_non_pretende_l_area_anagrafiche(self, mock_svc, _auth) -> None:
        mock_svc.return_value.lookup_risorse_umane.return_value = {"results": []}
        resp = self.client.get(_BASE + "?search=bia", HTTP_AUTHORIZATION="Bearer x")
        self.assertEqual(resp.status_code, 200)
        mock_svc.return_value.lookup_risorse_umane.assert_called_once_with(search="bia")

    # 4. Ricerca testuale: minimo 3 caratteri come ogni ricerca del progetto.
    def test_una_ricerca_troppo_corta_e_400(self) -> None:
        repo = Mock()
        with self.assertRaises(ServiceError) as ctx:
            AnagraficheService(repo).lookup_risorse_umane(search="bi")
        self.assertEqual(ctx.exception.code, "E_SEARCH_VALIDATION")
        repo.list_risorse_umane_lookup.assert_not_called()

    # 5. Il service pulisce il termine e lo passa al repository; assente =
    #    tutte le attive (nessun filtro).
    def test_il_service_passa_la_ricerca_al_repository(self) -> None:
        repo = Mock()
        repo.list_risorse_umane_lookup.return_value = [{"id": 7}]
        out = AnagraficheService(repo).lookup_risorse_umane(search="  bianchi ")
        self.assertEqual(out, {"results": [{"id": 7}]})
        repo.list_risorse_umane_lookup.assert_called_once_with(search="bianchi")
        repo.reset_mock()
        AnagraficheService(repo).lookup_risorse_umane(search="   ")
        repo.list_risorse_umane_lookup.assert_called_once_with(search=None)
