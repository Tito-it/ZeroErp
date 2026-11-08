# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: la LISTA delle righe di un contratto e di un'offerta
#        (`GET contratti/<id>/righe/lista/`, `GET offerte/<id>/righe/lista/` e
#        i loro `…/export/`; liste `vendite.contratto_righe` 103 e
#        `vendite.offerta_righe` 106) e il service del contratto
#        (brief-db-liste-righe-documento lotto D; brief-db-righe-esclusione-
#        solo-non-si-vende §8.1 per l'offerta, 2026-10-05). Mock di
#        repository, cancello e UI: nessun accesso DB (CI-compatible).
# ------------------------------------------------------------

"""⛔ PERCHE' QUESTO FILE ESISTE.

Le view nascono dalla factory dei documenti gemelli, e sbagliarne un parametro
non da' errore: un kwarg del padre sbagliato arriva al service come `None`, un
nome sbagliato del parametro emittente lascia chi vede piu' emittenti davanti a
`E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` a drawer aperto. E il service legge PRIMA
la testata: la funzione su un contratto che l'operatore non vede risponde zero
righe, cioe' «questo contratto non ha righe» invece di «non lo vedi».
⭐ Contratto e offerta girano gli STESSI test di view (classe base): sono due
dichiarazioni della stessa factory. La lettura della testata del service la
prova, per tutti e sette i documenti, `test_righe_pagina_dopo_testata`.

Indice test (contratto e offerta, ciascuno):

 1) test_lista_pagina_col_documento_del_percorso
 2) test_lista_ed_export_col_cancello_del_documento
 3) test_export_alza_il_tetto
 4) test_lista_ed_export_col_permesso_del_documento
 5) test_la_risorsa_di_scrittura_resta_senza_cancello_di_lista

Solo contratto (service):

 6) test_service_fuori_perimetro_404_senza_leggere_le_righe
 7) test_service_legge_la_pagina_dopo_la_testata
"""

from unittest import TestCase
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from django.urls import resolve

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.ui.tests._coda_export import coda_export_finta
from apps.vendite.services.contratti_service import ContrattiService

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_GUARD = "apps.core.services.perimetro_emittente.guard_lista_per_codice"


class _RigheListaApiBase:
    """I test comuni; le sottoclassi dicono service, percorsi, lista e permesso."""

    service: str
    base: str
    # La risorsa che serve il POST di creazione: niente cancello di lista.
    risorsa_scrittura: str
    lista_codice: str
    model_permission: tuple[str, str]

    def setUp(self) -> None:
        super().setUp()  # type: ignore[misc]  # il TestCase della sottoclasse
        self.client = Client()
        cache.clear()

    def test_lista_pagina_col_documento_del_percorso(self) -> None:
        with patch(_AUTH, return_value=(Mock(), None)), patch(self.service) as svc:
            svc.return_value.list_righe_pagina.return_value = ([{"riga_key": "A:7"}], 3)
            resp = self.client.get(f"{self.base}?search=canone&order_by=prezzo_finale&order_dir=desc&limit=10")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["count"], 3)
        self.assertEqual(resp.json()["data"]["results"], [{"riga_key": "A:7"}])
        svc.return_value.list_righe_pagina.assert_called_once_with(
            42, search="canone", order_by="prezzo_finale", order_dir="desc",
            limit=10, offset=0,
        )

    def test_lista_ed_export_col_cancello_del_documento(self) -> None:
        with patch(_AUTH, return_value=(Mock(), None)), patch(self.service) as svc:
            svc.return_value.list_righe_pagina.return_value = ([], 0)
            for suffisso in ("", "export/"):
                cache.clear()
                with self.subTest(export=bool(suffisso)), patch(_GUARD) as guard, coda_export_finta():
                    resp = self.client.get(f"{self.base}{suffisso}?emittente_fiscale_id=3")
                    self.assertEqual(resp.status_code, 200)
                    guard.assert_called_once()
                    self.assertEqual(guard.call_args.kwargs["lista_codice"], self.lista_codice)
                    self.assertEqual(guard.call_args.kwargs["emittente_esplicito"], 3)

    def test_export_alza_il_tetto(self) -> None:
        with patch(_AUTH, return_value=(Mock(), None)), patch(self.service) as svc:
            svc.return_value.list_righe_pagina.return_value = ([{"riga_key": "A:7"}], 1)
            with coda_export_finta("righe.csv"):
                resp = self.client.get(f"{self.base}export/?formato=csv")
        self.assertEqual(resp.status_code, 200)
        kwargs = svc.return_value.list_righe_pagina.call_args.kwargs
        self.assertEqual((kwargs["limit"], kwargs["max_limit"]), (EXPORT_MAX_ROWS + 1, EXPORT_MAX_ROWS + 1))
        self.assertNotIn("auth_user_id", kwargs)

    def test_lista_ed_export_col_permesso_del_documento(self) -> None:
        for suffisso in ("", "export/"):
            with self.subTest(export=bool(suffisso)):
                view = resolve(f"{self.base}{suffisso}").func.view_class
                self.assertEqual(view.model_permission, self.model_permission)

    # ⭐ Il percorso suo esiste per questo: la risorsa serve anche il POST di
    #    creazione, e un cancello di lista li' rifiuterebbe la creazione a chi
    #    vede piu' emittenti (decisione di Tid del lotto A).
    def test_la_risorsa_di_scrittura_resta_senza_cancello_di_lista(self) -> None:
        view = resolve(self.risorsa_scrittura).func.view_class
        self.assertIsNone(getattr(view, "lista_codice", None))


class TestContrattoRigheListaApi(_RigheListaApiBase, JwtMockedApiTest):
    service = "apps.vendite.api.views_contratti.ContrattiService"
    base = "/api/v1/vendite/contratti/42/righe/lista/"
    risorsa_scrittura = "/api/v1/vendite/contratti/42/righe/"
    lista_codice = "vendite.contratto_righe"
    model_permission = ("vendite", "contratto")


class TestOffertaRigheListaApi(_RigheListaApiBase, JwtMockedApiTest):
    service = "apps.vendite.api.views_offerte.OfferteService"
    base = "/api/v1/vendite/offerte/42/righe/lista/"
    risorsa_scrittura = "/api/v1/vendite/offerte/42/eccezioni/"
    lista_codice = "vendite.offerta_righe"
    model_permission = ("vendite", "offerta_commerciale")


class ContrattoRighePaginaServiceTests(TestCase):

    @patch("apps.vendite.services.contratti_service.ContrattoRigheListaRepository", autospec=True)
    @patch("apps.vendite.services.contratti_service.ContrattiRepository", autospec=True)
    def test_service_fuori_perimetro_404_senza_leggere_le_righe(self, contratti, righe) -> None:
        contratti.return_value.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().list_righe_pagina(42, limit=10)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")
        contratti.return_value.get_stato_codice.assert_called_once_with(42)
        righe.return_value.list_righe_pagina.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattoRigheListaRepository", autospec=True)
    @patch("apps.vendite.services.contratti_service.ContrattiRepository", autospec=True)
    def test_service_legge_la_pagina_dopo_la_testata(self, contratti, righe) -> None:
        contratti.return_value.get_stato_codice.return_value = "DRAFT"
        righe.return_value.list_righe_pagina.return_value = ([], 0)
        ContrattiService().list_righe_pagina(42, search="x", limit=10, offset=20)
        args, kwargs = righe.return_value.list_righe_pagina.call_args
        self.assertEqual(args, (42,))
        self.assertEqual((kwargs["search"], kwargs["limit"], kwargs["offset"]), ("x", 10, 20))
