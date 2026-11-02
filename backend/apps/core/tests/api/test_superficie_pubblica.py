# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio della superficie raggiungibile SENZA token: l'admin
#        Django non esiste, la root non redirige, Swagger/OpenAPI c'e'
#        solo con `API_DOCS_ENABLED`.
# Note: un 200 qui e' un'esposizione, non un successo. Se una rotta
#       deve tornare pubblica, si cambia questo test per decisione.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) SuperficiePubblicaTests.test_admin_django_non_esiste
2) SuperficiePubblicaTests.test_admin_django_non_e_installato
3) SuperficiePubblicaTests.test_root_non_redirige
4) SuperficiePubblicaTests.test_api_docs_spente_rispondono_404
5) SuperficiePubblicaTests.test_api_docs_accese_rispondono
"""

from django.apps import apps
from django.conf import settings
from django.test import Client, override_settings

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest


# ⚠️ Base `JwtMockedApiTest` anche se qui non c'e' nessun token: le chiamate
#    `/api/*` passano dai middleware che scrivono sul DB (lingua, log), e la
#    base li spegne. Il client resta anonimo, e nessun mock tocca l'auth.
class SuperficiePubblicaTests(JwtMockedApiTest):
    # Scopo: Prepara il client anonimo (nessun token: e' il punto del test).
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: `/admin/` e la sua login non devono esistere: erano una form di
    #        login a sessione aperta a chiunque raggiungesse il proxy.
    def test_admin_django_non_esiste(self):
        for path in ("/admin/", "/admin/login/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    # Scopo: Il cancello sta anche a monte della rotta: l'app non e' installata,
    #        quindi nessun `include(admin.site.urls)` puo' ricomparire per caso.
    def test_admin_django_non_e_installato(self):
        self.assertFalse(apps.is_installed("django.contrib.admin"))
        self.assertNotIn("django.contrib.admin", settings.INSTALLED_APPS)

    # Scopo: La root non porta da nessuna parte (prima redirigeva a `/admin/`).
    def test_root_non_redirige(self):
        self.assertEqual(self.client.get("/").status_code, 404)

    # Scopo: Con la documentazione API spenta le due rotte non esistono (404,
    #        non 403: non confermano nemmeno di esserci).
    @override_settings(API_DOCS_ENABLED=False)
    def test_api_docs_spente_rispondono_404(self):
        for path in ("/api/schema/", "/api/docs/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    # Scopo: Con il flag acceso il cancello lascia passare (il contenuto e'
    #        provato da `test_diagnostics_api`).
    @override_settings(API_DOCS_ENABLED=True)
    def test_api_docs_accese_rispondono(self):
        for path in ("/api/schema/", "/api/docs/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
