# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test degli endpoint HTTP del dominio `pagamenti`.
# Note: Il service e' mockato: qui si prova il CONTRATTO — che le rotte
#       esistano, che chiedano il JWT, che i filtri arrivino tradotti e che
#       le scritture pretendano la chiave di idempotenza.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1)  PagamentiRotteTests.test_le_rotte_esistono
2)  PagamentiAuthTests.test_lista_richiede_jwt
3)  PagamentiAuthTests.test_dettaglio_richiede_jwt
4)  PagamentiAuthTests.test_registra_richiede_jwt
5)  DistinteListApiTests.test_lista_ok
6)  DistinteListApiTests.test_filtri_arrivano_tradotti
7)  DistinteListApiTests.test_stato_e_origine_normalizzati_maiuscoli
8)  DistinteListApiTests.test_data_malformata_400
9)  DistinteListApiTests.test_creazione_senza_idempotency_key_rifiutata
10) DistinteListApiTests.test_creazione_con_idempotency_key_ok
11) DistintaDetailApiTests.test_dettaglio_ok
12) DistintaDetailApiTests.test_patch_passa_il_payload_al_service
13) RegistrazioneApiTests.test_anteprima_ok
14) RegistrazioneApiTests.test_registrazione_restituisce_la_ricevuta_intatta
15) Slice3RotteTests.test_le_rotte_della_slice_3_esistono
16) Slice3ApiTests.test_abbina_senza_idempotency_key_rifiutato
17) Slice3ApiTests.test_abbina_ok
18) Slice3ApiTests.test_coda_filtri_tradotti
19) Slice3ApiTests.test_saldo_rata_ok
20) Slice3ApiTests.test_saldo_fattura_ok
"""

from datetime import date
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = patch(
    "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate",
    return_value=(Mock(), None),
)

_LISTA = {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [{"id": 7, "codice": "CNT-0001", "origine": "MANUALE"}],
}

_DETTAGLIO = {
    "distinta": {"id": 7, "codice": "CNT-0001", "righe_totali": 0},
    "righe": [],
    "stati_distinta": [],
    "stati_riga": [],
    "stati_richiedibili": ["VALIDATA", "BOZZA", "ANNULLATA"],
}


class PagamentiRotteTests(JwtMockedApiTest):
    # Scopo: Le otto rotte del dominio esistono e sono montate sotto
    #        /api/v1/pagamenti/. ⚠️ Fino al 2026-08-24 quel prefisso era un 404
    #        secco: questo test e' cio' che impedisce di tornarci.
    def test_le_rotte_esistono(self):
        self.assertEqual(
            reverse("pagamenti-distinte-list"), "/api/v1/pagamenti/distinte/"
        )
        self.assertEqual(
            reverse("pagamenti-distinta-detail", args=[7]),
            "/api/v1/pagamenti/distinte/7/",
        )
        self.assertEqual(
            reverse("pagamenti-distinta-righe", args=[7]),
            "/api/v1/pagamenti/distinte/7/righe/",
        )
        self.assertEqual(
            reverse("pagamenti-distinta-stato", args=[7]),
            "/api/v1/pagamenti/distinte/7/stato/",
        )
        self.assertEqual(
            reverse("pagamenti-distinta-anteprima-registrazione", args=[7]),
            "/api/v1/pagamenti/distinte/7/anteprima-registrazione/",
        )
        self.assertEqual(
            reverse("pagamenti-distinta-registra", args=[7]),
            "/api/v1/pagamenti/distinte/7/registra/",
        )
        self.assertEqual(
            reverse("pagamenti-riga-detail", args=[11]), "/api/v1/pagamenti/righe/11/"
        )
        self.assertEqual(
            reverse("pagamenti-riga-stato", args=[11]),
            "/api/v1/pagamenti/righe/11/stato/",
        )


class PagamentiAuthTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    # Scopo: Nessun endpoint del dominio e' pubblico.
    def test_lista_richiede_jwt(self):
        self.assertEqual(self.client.get("/api/v1/pagamenti/distinte/").status_code, 401)

    def test_dettaglio_richiede_jwt(self):
        self.assertEqual(
            self.client.get("/api/v1/pagamenti/distinte/7/").status_code, 401
        )

    # Scopo: ⚠️ Il gesto irreversibile per primo: un 401 qui e' l'ultima cosa
    #        che si vorrebbe scoprire mancante.
    def test_registra_richiede_jwt(self):
        self.assertEqual(
            self.client.post("/api/v1/pagamenti/distinte/7/registra/").status_code, 401
        )


class DistinteListApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.list_distinte")
    def test_lista_ok(self, mocked, _auth):
        mocked.return_value = _LISTA
        response = self.client.get("/api/v1/pagamenti/distinte/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["results"][0]["id"], 7)

    # Scopo: I filtri arrivano al service gia' tipizzati — la view traduce, il
    #        service non riparsa stringhe.
    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.list_distinte")
    def test_filtri_arrivano_tradotti(self, mocked, _auth):
        mocked.return_value = _LISTA
        self.client.get(
            "/api/v1/pagamenti/distinte/"
            "?centro_riscossione_id=39&ente_incasso_id=4"
            "&data_da=2026-08-01&data_a=2026-08-31&page=2&page_size=25"
        )
        kwargs = mocked.call_args.kwargs
        self.assertEqual(kwargs["centro_riscossione_id"], 39)
        self.assertEqual(kwargs["ente_incasso_id"], 4)
        self.assertEqual(kwargs["data_da"], date(2026, 8, 1))
        self.assertEqual(kwargs["data_a"], date(2026, 8, 31))
        self.assertEqual(kwargs["page"], 2)
        self.assertEqual(kwargs["page_size"], 25)

    # Scopo: I due vocabolari chiusi si confrontano in maiuscolo: `manuale` e
    #        `MANUALE` sono la stessa richiesta, e chiedere all'operatore di
    #        ricordarsene sarebbe una trappola.
    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.list_distinte")
    def test_stato_e_origine_normalizzati_maiuscoli(self, mocked, _auth):
        mocked.return_value = _LISTA
        self.client.get("/api/v1/pagamenti/distinte/?stato=bozza&origine=manuale")
        kwargs = mocked.call_args.kwargs
        self.assertEqual(kwargs["stato"], "BOZZA")
        self.assertEqual(kwargs["origine"], "MANUALE")

    # Scopo: ⛔ Nessuna coercion silenziosa su una data malformata: un filtro
    #        che si spegne da solo mostra una lista che sembra completa.
    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.list_distinte")
    def test_data_malformata_400(self, mocked, _auth):
        response = self.client.get("/api/v1/pagamenti/distinte/?data_da=ieri")
        self.assertEqual(response.status_code, 400)
        mocked.assert_not_called()

    # Scopo: ⚠️ Aprire una distinta e' una scrittura: senza chiave di
    #        idempotenza un doppio invio produrrebbe due documenti.
    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.crea_distinta")
    def test_creazione_senza_idempotency_key_rifiutata(self, mocked, _auth):
        response = self.client.post(
            "/api/v1/pagamenti/distinte/",
            data={"centro_riscossione_id": 39, "data_contabile": "2026-08-24"},
            content_type="application/json",
        )
        self.assertEqual(response.json()["error"]["code"], "E_IDEMPOTENCY_KEY_REQUIRED")
        mocked.assert_not_called()

    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.crea_distinta")
    def test_creazione_con_idempotency_key_ok(self, mocked, _auth):
        mocked.return_value = {**_DETTAGLIO, "gia_popolata": False}
        response = self.client.post(
            "/api/v1/pagamenti/distinte/",
            data={"centro_riscossione_id": 39, "data_contabile": "2026-08-24"},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="test-key-0001",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["data"]["gia_popolata"])


class DistintaDetailApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.get_distinta")
    def test_dettaglio_ok(self, mocked, _auth):
        mocked.return_value = _DETTAGLIO
        response = self.client.get("/api/v1/pagamenti/distinte/7/")
        self.assertEqual(response.status_code, 200)
        # ⭐ I cataloghi viaggiano col dettaglio: il frontend non li cabla.
        self.assertIn("stati_riga", response.json()["data"])

    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.aggiorna_distinta")
    def test_patch_passa_il_payload_al_service(self, mocked, _auth):
        mocked.return_value = _DETTAGLIO
        response = self.client.patch(
            "/api/v1/pagamenti/distinte/7/",
            data={"importo_dichiarato": "1250.50"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mocked.call_args.args[1], {"importo_dichiarato": "1250.50"}
        )


class RegistrazioneApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.anteprima_registrazione")
    def test_anteprima_ok(self, mocked, _auth):
        mocked.return_value = {
            "contabile_id": 7,
            "righe_registrabili": 2,
            "totale_registrabile": "300.00",
            "righe_non_registrabili": [],
        }
        response = self.client.get(
            "/api/v1/pagamenti/distinte/7/anteprima-registrazione/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["righe_registrabili"], 2)

    # Scopo: 🔴 La ricevuta risale INTATTA, esito compreso. `NULLA_DA_POSTARE`
    #        non e' un errore e non diventa un 409: il database dice il fatto,
    #        e la frase la sceglie il frontend.
    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.registra_distinta")
    def test_registrazione_restituisce_la_ricevuta_intatta(self, mocked, _auth):
        mocked.return_value = {
            "movimenti_creati": 0,
            "righe_postate": 0,
            "righe_saltate": 0,
            "totale_postato": "0.00",
            "esito": "NULLA_DA_POSTARE",
        }
        response = self.client.post(
            "/api/v1/pagamenti/distinte/7/registra/",
            data={},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="test-key-0002",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["esito"], "NULLA_DA_POSTARE")


class Slice3RotteTests(JwtMockedApiTest):
    # Scopo: Le sei rotte della slice 3 esistono e stanno dove il contratto
    #        dice. ⚠️ `rate/fuori-capienza/` deve stare PRIMA del pattern con
    #        l'id: l'ordine e' la regola, non la fortuna.
    def test_le_rotte_della_slice_3_esistono(self):
        self.assertEqual(
            reverse("pagamenti-riga-abbina", args=[11]),
            "/api/v1/pagamenti/righe/11/abbina/",
        )
        self.assertEqual(reverse("pagamenti-righe-coda"), "/api/v1/pagamenti/righe/")
        self.assertEqual(
            reverse("pagamenti-rate-fuori-capienza"),
            "/api/v1/pagamenti/rate/fuori-capienza/",
        )
        self.assertEqual(
            reverse("pagamenti-rata-saldo", args=[900]),
            "/api/v1/pagamenti/rate/900/saldo/",
        )
        self.assertEqual(
            reverse("pagamenti-fattura-saldo", args=[2263]),
            "/api/v1/pagamenti/fatture/2263/saldo/",
        )
        self.assertEqual(
            reverse("pagamenti-fattura-rate", args=[2263]),
            "/api/v1/pagamenti/fatture/2263/rate/",
        )


class Slice3ApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    # Scopo: Abbinare e' una scrittura, e la conferma della forzatura si
    #        ripete: senza chiave di idempotenza un doppio invio la applica due
    #        volte.
    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.abbina_riga")
    def test_abbina_senza_idempotency_key_rifiutato(self, mocked, _auth):
        response = self.client.post(
            "/api/v1/pagamenti/righe/11/abbina/",
            data={"fattura_id": 2263, "billing_account_id": 41},
            content_type="application/json",
        )
        self.assertEqual(response.json()["error"]["code"], "E_IDEMPOTENCY_KEY_REQUIRED")
        mocked.assert_not_called()

    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.abbina_riga")
    def test_abbina_ok(self, mocked, _auth):
        mocked.return_value = {"riga": {"id": 11, "stato_codice": "ABBINATA"}}
        response = self.client.post(
            "/api/v1/pagamenti/righe/11/abbina/",
            data={"fattura_id": 2263, "billing_account_id": 41, "forzata": True},
            content_type="application/json",
            HTTP_IDEMPOTENCY_KEY="test-key-0003",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mocked.call_args.args[1]["forzata"])

    @_AUTH
    @patch("apps.pagamenti.api.views.pagamenti_service.list_coda_righe")
    def test_coda_filtri_tradotti(self, mocked, _auth):
        mocked.return_value = {"count": 0, "page": 1, "page_size": 50,
                               "total_pages": 0, "results": []}
        self.client.get("/api/v1/pagamenti/righe/?coda=sospese&billing_account_id=41")
        kwargs = mocked.call_args.kwargs
        self.assertEqual(kwargs["coda"], "SOSPESE")
        self.assertEqual(kwargs["billing_account_id"], 41)

    @_AUTH
    @patch("apps.pagamenti.api.views.saldi_service.saldo_rata")
    def test_saldo_rata_ok(self, mocked, _auth):
        mocked.return_value = {"livello": "RATA", "residuo": "1000.00",
                               "in_lavorazione": "0", "incassato": "800.00",
                               "has_movimenti": True}
        response = self.client.get(
            "/api/v1/pagamenti/rate/900/saldo/?escludi_riga_id=11"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mocked.call_args.kwargs["escludi_riga_id"], 11)

    # Scopo: ⚠️ Il saldo di un documento sta in `pagamenti` e NON in `vendite`:
    #        le chiamate laterali fra moduli di pari livello non sono ammesse.
    #        Lo consuma il drawer fattura, quindi salta il controllo d'area.
    @_AUTH
    @patch("apps.pagamenti.api.views.saldi_service.saldo_documento")
    def test_saldo_fattura_ok(self, mocked, _auth):
        mocked.return_value = {"livello": "DOCUMENTO", "residuo": "500.00",
                               "in_lavorazione": "100.00", "incassato": None,
                               "has_movimenti": True}
        response = self.client.get("/api/v1/pagamenti/fatture/2263/saldo/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"]["incassato"])
