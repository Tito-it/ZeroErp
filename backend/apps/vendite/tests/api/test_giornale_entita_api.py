# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: GET /vendite/fatture/<id>/giornale/ e /vendite/lotti/<id>/giornale/ —
#        le due STORIE per entita', che dal 2026-09-27 sono la lista a
#        catalogo `vendite.giornale` (brief-db-liste-datatable-grezze §3.1).
#        Repository mockato, nessun DB: la PORTA (cancello di lista col suo
#        parametro emittente), il contratto di lista standard dalla query
#        string al repository, i 400 e l'envelope.
#
# Indice test:
#   1. porte: `lista_codice = vendite.giornale` e `lista_emittente_param`
#      dichiarati sulle DUE view, con lo stesso nome
#   2. fattura: `limit`/`offset`/`order_by`/`order_dir` arrivano al
#      repository; la pagina si ricava dall'offset
#   3. fattura: senza ordinamento arriva il default della lista (`quando`,
#      direzione `None`: la decide il repository, DESC sulle date)
#   4. fattura: `order_by` fuori whitelist -> 400
#   5. lotto: `info` assente = solo problemi; `info=true` le include;
#      `info_count` nell'envelope
#   6. lotto: `info` e `ritirate` strict -> 400 su un valore non booleano
#   7. il vecchio contratto (`sort_by`/`page_size`) NON e' piu' letto
#   8. il cancello riceve l'emittente della query su tutte e due le Storie
# ------------------------------------------------------------
from unittest.mock import Mock, patch

from django.test import Client

from apps.vendite.api._giornale_params import EMITTENTE_PARAM_GIORNALE_ENTITA
from apps.vendite.api.fatture_views import ApiFatturaGiornale
from apps.vendite.api.views import ApiLottoGiornale
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = patch(
    "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
    return_value=(Mock(), None),
)
_REPO = "apps.vendite.services.vendite_service.VenditeRepository"
_URL_FATTURA = "/api/v1/vendite/fatture/7/giornale/"
_URL_LOTTO = "/api/v1/vendite/lotti/6260/giornale/"


class GiornaleEntitaApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. ⭐ Le due Storie e il trasversale sono la STESSA lista: stesso cancello
    #    di perimetro, e il drawer lo scioglie passando l'emittente del
    #    documento — col nome che le due view dichiarano uguale.
    def test_porte_dichiarano_la_lista_e_il_parametro_emittente(self) -> None:
        for view in (ApiFatturaGiornale, ApiLottoGiornale):
            with self.subTest(view=view.__name__):
                self.assertEqual(view.lista_codice, "vendite.giornale")
                self.assertEqual(view.lista_emittente_param, EMITTENTE_PARAM_GIORNALE_ENTITA)
        self.assertEqual(EMITTENTE_PARAM_GIORNALE_ENTITA, "emittente_soggetto_ruolo_id")

    # 2.
    @_AUTH
    @patch(_REPO)
    def test_fattura_contratto_di_lista_fino_al_repository(self, repo_cls, _auth) -> None:
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = {"id": 7}
        repo.list_giornale_entita.return_value = ([], 30, 0, 0)
        resp = self.client.get(_URL_FATTURA, {
            "limit": "10", "offset": "20", "order_by": "gravita", "order_dir": "asc",
            EMITTENTE_PARAM_GIORNALE_ENTITA: "5",
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        chiamata = repo.list_giornale_entita.call_args.kwargs
        self.assertEqual(
            (chiamata["limit"], chiamata["offset"], chiamata["sort_by"], chiamata["sort_dir"]),
            (10, 20, "gravita", "asc"),
        )
        data = resp.json()["data"]
        self.assertEqual((data["page"], data["page_size"], data["count"]), (3, 10, 30))
        self.assertEqual(data["fattura_id"], 7)

    # 3.
    @_AUTH
    @patch(_REPO)
    def test_fattura_senza_ordinamento_arriva_il_default_della_lista(self, repo_cls, _auth) -> None:
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = {"id": 7}
        repo.list_giornale_entita.return_value = ([], 0, 0, 0)
        self.assertEqual(self.client.get(_URL_FATTURA).status_code, 200)
        chiamata = repo.list_giornale_entita.call_args.kwargs
        self.assertEqual((chiamata["sort_by"], chiamata["sort_dir"]), ("quando", None))

    # 4.
    @_AUTH
    @patch(_REPO)
    def test_fattura_ordinamento_fuori_whitelist_400(self, repo_cls, _auth) -> None:
        resp = self.client.get(_URL_FATTURA, {"order_by": "cosa"})
        self.assertEqual(resp.status_code, 400, resp.content)
        repo_cls.return_value.list_giornale_entita.assert_not_called()

    # 5.
    @_AUTH
    @patch(_REPO)
    def test_lotto_filtro_info(self, repo_cls, _auth) -> None:
        repo = repo_cls.return_value
        repo.get_lotto.return_value = {"id": 6260}
        repo.list_giornale_lotto.return_value = ([], 286, 2, 173)
        resp = self.client.get(_URL_LOTTO)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(repo.list_giornale_lotto.call_args.kwargs["escludi_info"])
        data = resp.json()["data"]
        self.assertEqual((data["count"], data["info_count"], data["ritirate_count"]), (113, 173, 2))

        resp = self.client.get(_URL_LOTTO, {"info": "true"})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(repo.list_giornale_lotto.call_args.kwargs["escludi_info"])

    # 6. ⛔ Strict: un valore che non e' un booleano non diventa `True` per caso.
    @_AUTH
    @patch(_REPO)
    def test_lotto_booleani_strict_400(self, repo_cls, _auth) -> None:
        repo_cls.return_value.get_lotto.return_value = {"id": 6260}
        for nome in ("info", "ritirate"):
            with self.subTest(parametro=nome):
                resp = self.client.get(_URL_LOTTO, {nome: "banana"})
                self.assertEqual(resp.status_code, 400, resp.content)

    # 7. ⚠️ Il vecchio contratto non ha piu' effetto: la lista manda `order_by`
    #    e `limit`; `sort_by` si ignora, `page_size` e' un 400 (§A3).
    @_AUTH
    @patch(_REPO)
    def test_vecchio_contratto_non_letto(self, repo_cls, _auth) -> None:
        repo = repo_cls.return_value
        repo.get_lotto.return_value = {"id": 6260}
        repo.list_giornale_lotto.return_value = ([], 0, 0, 0)
        resp = self.client.get(_URL_LOTTO, {"sort_by": "gravita"})
        self.assertEqual(resp.status_code, 200, resp.content)
        chiamata = repo.list_giornale_lotto.call_args.kwargs
        self.assertEqual(chiamata["sort_by"], "quando")
        # ⛔ Dal 2026-10-20 `page_size` su una lista a `limit`/`offset` e' un
        #    400, non un parametro ignorato (brief-be-verifica-documentazione-api §A3).
        resp = self.client.get(_URL_LOTTO, {"page_size": "3"})
        self.assertEqual(resp.status_code, 400, resp.content)

    # 8. ⭐ Il cancello (`initial()`) legge l'emittente dalla query col nome che
    #    la view dichiara: e' cio' che non sbarra (422) chi vede piu' emittenti
    #    dentro un drawer gia' aperto. La sola dichiarazione (test 1) non prova
    #    che il valore arrivi.
    @_AUTH
    @patch("apps.core.services.perimetro_emittente.guard_lista_per_codice")
    @patch(_REPO)
    def test_il_cancello_riceve_l_emittente_della_query(self, repo_cls, guard, _auth) -> None:
        repo = repo_cls.return_value
        repo.get_fattura_testata.return_value = {"id": 7}
        repo.list_giornale_entita.return_value = ([], 0, 0, 0)
        repo.get_lotto_by_id.return_value = {"id": 6260}
        repo.list_giornale_lotto.return_value = ([], 0, 0, 0)
        for url in (_URL_FATTURA, _URL_LOTTO):
            with self.subTest(url=url):
                guard.reset_mock()
                self.client.get(url, {EMITTENTE_PARAM_GIORNALE_ENTITA: "5"})
                guard.assert_called_once()
                self.assertEqual(guard.call_args.kwargs["lista_codice"], "vendite.giornale")
                self.assertEqual(guard.call_args.kwargs["emittente_esplicito"], 5)
