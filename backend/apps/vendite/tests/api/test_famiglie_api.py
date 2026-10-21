# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test degli endpoint HTTP del CRUD delle FAMIGLIE DI DOCUMENTO.
# Note: Il service e' mockato: qui si prova il CONTRATTO — che le rotte
#       esistano, che il CRUD chieda l'AMMINISTRATORE e il lookup no, e che i
#       filtri arrivino tradotti. Nessun accesso al database.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_le_rotte_esistono
2) test_lista_ok
3) test_filtri_arrivano_tradotti
4) test_crea_passa_il_payload_al_service
5) test_dettaglio_ok
6) test_patch_passa_il_payload_al_service
7) test_attivo_senza_booleano_e_400
8) test_attivo_ok
9) test_il_crud_pretende_l_amministratore
10) test_il_lookup_NON_pretende_l_amministratore
11) test_il_lookup_torna_l_envelope_results
12) test_le_sorgenti_pretendono_l_amministratore_e_tornano_results (2026-10-20)
"""

import json
from unittest.mock import Mock, patch


from apps.core.tests._helpers.jwt_mock import ClientApi
from django.urls import reverse

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_PERM_ADMIN = "apps.core.api.permissions.IsAdminZeroERP.has_permission"
_SVC = "apps.vendite.api.views_famiglie.FamiglieDocumentoService"

_BASE = "/api/v1/vendite/famiglie/"

_FAMIGLIA = {
    "id": 3, "codice_interno": "FATTURA", "descrizione": "Fatture",
    "tabella_documento": "vendite.fatture", "gestisce_serie": True,
    "n_registri": 2, "attivo": True,
}


class FamiglieRotteTests(JwtMockedApiTest):
    # 1. Le cinque rotte esistono e si risolvono per NOME: un `reverse` che
    #    fallisce dice «rotta non montata» prima ancora di parlare di risposte.
    def test_le_rotte_esistono(self):
        self.assertEqual(reverse("vendite-famiglie-list"), _BASE)
        self.assertEqual(reverse("vendite-famiglie-lookup"), f"{_BASE}lookup/")
        self.assertEqual(reverse("vendite-famiglie-export"), f"{_BASE}export/")
        self.assertEqual(reverse("vendite-famiglie-sorgenti"), f"{_BASE}sorgenti/")
        self.assertEqual(
            reverse("vendite-famiglie-detail", kwargs={"famiglia_id": 3}),
            f"{_BASE}3/",
        )
        self.assertEqual(
            reverse("vendite-famiglie-attivo", kwargs={"famiglia_id": 3}),
            f"{_BASE}3/attivo/",
        )


class FamiglieCrudApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN, return_value=True)
    @patch(_SVC)
    def test_lista_ok(self, mock_svc, _perm, _auth):
        mock_svc.return_value.list_famiglie.return_value = ([_FAMIGLIA], 1)
        resp = self.client.get(_BASE, HTTP_AUTHORIZATION="Bearer x")
        self.assertEqual(resp.status_code, 200)
        dati = json.loads(resp.content)["data"]
        self.assertEqual(dati["count"], 1)
        self.assertEqual(dati["results"][0]["codice_interno"], "FATTURA")

    # 3. ⚠️ I filtri si provano TRADOTTI, non solo «la chiamata risponde 200»:
    #    `attivo=false` che arriva al service come la stringa `"false"` sarebbe
    #    un filtro sempre vero, e la lista mostrerebbe tutto senza fallire.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN, return_value=True)
    @patch(_SVC)
    def test_filtri_arrivano_tradotti(self, mock_svc, _perm, _auth):
        mock_svc.return_value.list_famiglie.return_value = ([], 0)
        self.client.get(
            f"{_BASE}?attivo=false&gestisce_serie=true&search=fatt&order_by=descrizione",
            HTTP_AUTHORIZATION="Bearer x",
        )
        kwargs = mock_svc.return_value.list_famiglie.call_args.kwargs
        self.assertIs(kwargs["attivo"], False)
        self.assertIs(kwargs["gestisce_serie"], True)
        self.assertEqual(kwargs["search"], "fatt")
        self.assertEqual(kwargs["order_by"], "descrizione")

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN, return_value=True)
    @patch(_SVC)
    def test_crea_passa_il_payload_al_service(self, mock_svc, _perm, _auth):
        mock_svc.return_value.crea_famiglia.return_value = {
            **_FAMIGLIA, "registri_creati": 4,
        }
        resp = self.client.post(
            _BASE,
            data=json.dumps({"codice_interno": "PARCELLA", "descrizione": "Parcelle"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        payload = mock_svc.return_value.crea_famiglia.call_args.args[0]
        self.assertEqual(payload["codice_interno"], "PARCELLA")
        self.assertEqual(json.loads(resp.content)["data"]["registri_creati"], 4)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN, return_value=True)
    @patch(_SVC)
    def test_dettaglio_ok(self, mock_svc, _perm, _auth):
        mock_svc.return_value.get_famiglia.return_value = _FAMIGLIA
        resp = self.client.get(f"{_BASE}3/", HTTP_AUTHORIZATION="Bearer x")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_svc.return_value.get_famiglia.call_args.args[0], 3)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN, return_value=True)
    @patch(_SVC)
    def test_patch_passa_il_payload_al_service(self, mock_svc, _perm, _auth):
        mock_svc.return_value.update_famiglia.return_value = _FAMIGLIA
        resp = self.client.patch(
            f"{_BASE}3/",
            data=json.dumps({"descrizione": "Nuova"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        args = mock_svc.return_value.update_famiglia.call_args.args
        self.assertEqual(args[0], 3)
        self.assertEqual(args[1]["descrizione"], "Nuova")

    # 7. ⛔ `attivo` assente o non booleano e' un 400, non un `False` implicito:
    #    dedurre lo spegnimento da un campo mancante spegnerebbe una famiglia
    #    per una richiesta malformata.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN, return_value=True)
    @patch(_SVC)
    def test_attivo_senza_booleano_e_400(self, mock_svc, _perm, _auth):
        resp = self.client.post(
            f"{_BASE}3/attivo/",
            data=json.dumps({"attivo": "si"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 400)
        mock_svc.return_value.set_attivo.assert_not_called()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN, return_value=True)
    @patch(_SVC)
    def test_attivo_ok(self, mock_svc, _perm, _auth):
        mock_svc.return_value.set_attivo.return_value = {**_FAMIGLIA, "attivo": False}
        resp = self.client.post(
            f"{_BASE}3/attivo/",
            data=json.dumps({"attivo": False}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer x",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_svc.return_value.set_attivo.call_args.args, (3, False))


class FamiglieCancelloTests(JwtMockedApiTest):
    """⭐ Le due meta' della decisione D6, provate in ENTRAMBI i versi."""

    def setUp(self) -> None:
        super().setUp()
        self.client = ClientApi()

    # 9. Il CRUD e' per il solo amministratore (D6, Tid 2026-09-01).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN, return_value=False)
    @patch(_SVC)
    def test_il_crud_pretende_l_amministratore(self, mock_svc, _perm, _auth):
        for metodo, url in (
            (self.client.get, _BASE),
            (self.client.get, f"{_BASE}3/"),
            (self.client.get, f"{_BASE}export/"),
        ):
            with self.subTest(url=url):
                self.assertEqual(metodo(url, HTTP_AUTHORIZATION="Bearer x").status_code, 403)
        mock_svc.return_value.list_famiglie.assert_not_called()

    # 10. ⛔ E IL LOOKUP NO, ed e' la meta' che si dimentica: lo chiama il drawer
    #     dei REGISTRI — una schermata di dominio — per precompilare la forma del
    #     numero e per sapere quali campi mostrare. Dietro il cancello
    #     dell'amministratore quei campi si spegnerebbero per tutti gli altri, in
    #     silenzio, e il drawer ricadrebbe sui valori cablati che BE-F2 toglie.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN, return_value=False)
    @patch(_SVC)
    def test_il_lookup_NON_pretende_l_amministratore(self, mock_svc, _perm, _auth):
        mock_svc.return_value.list_lookup.return_value = []
        resp = self.client.get(f"{_BASE}lookup/", HTTP_AUTHORIZATION="Bearer x")
        self.assertNotEqual(resp.status_code, 403)

    # Scopo: (11) LA FORMA DELLA RISPOSTA, non solo il suo status.
    # ⛔ E' il presidio che mancava, e la sua assenza e' costata un drawer
    #    BIANCO con la suite verde (2026-09-08). Il lookup tornava la LISTA
    #    NUDA sotto `data`; il composable `useLookup` del frontend trasforma
    #    ogni risposta con `r.data.data.results`, che su una lista nuda vale
    #    `undefined`. Il `ref` delle famiglie passava da `[]` a `undefined` e il
    #    primo `.map()` in un computed sollevava: Vue svuota il sottoalbero, e
    #    il drawer dei registri si apriva vuoto — senza un errore da nessuna
    #    parte lato server.
    # ⚠️ E' la classe di difetto che nessuno dei due lati vede da solo: qui il
    #    200 era corretto, di la' il campo era `undefined`. A vederlo e' solo
    #    un test che guarda la FORMA, che e' quello che il frontend legge.
    # ⭐ La forma non e' inventata: e' quella di ogni lookup dedicato
    #    (`ProvinceLookupView` e le gemelle regioni/stati), ed e' il contratto
    #    che il BB `useLookup` assume per tutti i suoi chiamanti.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN, return_value=False)
    @patch(_SVC)
    def test_il_lookup_torna_l_envelope_results(self, mock_svc, _perm, _auth):
        righe = [{"codice_interno": "FATTURA", "descrizione": "Fattura"}]
        mock_svc.return_value.list_lookup.return_value = righe
        resp = self.client.get(f"{_BASE}lookup/", HTTP_AUTHORIZATION="Bearer x")
        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        self.assertIsInstance(
            corpo["data"], dict,
            "`data` deve essere l'oggetto con `results`, non la lista nuda: "
            "il frontend legge `data.data.results`",
        )
        self.assertEqual(corpo["data"]["results"], righe)

    # 12. Le sorgenti fra cui il drawer sceglie la famiglia da creare (dal
    #     2026-10-20, brief-db-grammatica-unica-documenti 2c): servono solo alla
    #     creazione, quindi stanno dietro lo STESSO cancello del CRUD — e hanno
    #     la forma `{"results": [...]}` di ogni lookup dedicato (vedi l'11).
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_PERM_ADMIN)
    @patch(_SVC)
    def test_le_sorgenti_pretendono_l_amministratore_e_tornano_results(
        self, mock_svc, perm, _auth,
    ):
        righe = [{"codice_interno": "PREVENTIVO", "etichetta": "Preventivo",
                  "famiglia_esistente": False, "tabella_numerata_da": None}]
        mock_svc.return_value.list_sorgenti_numerabili.return_value = righe
        perm.return_value = False
        resp = self.client.get(f"{_BASE}sorgenti/", HTTP_AUTHORIZATION="Bearer x")
        self.assertEqual(resp.status_code, 403)
        mock_svc.return_value.list_sorgenti_numerabili.assert_not_called()
        perm.return_value = True
        resp = self.client.get(f"{_BASE}sorgenti/", HTTP_AUTHORIZATION="Bearer x")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["results"], righe)
