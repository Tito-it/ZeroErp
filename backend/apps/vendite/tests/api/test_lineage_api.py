# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API "passaggi" (lineage/genealogia documenti):
#        routing sugli 8 domini (6 documenti + commessa + fattura) +
#        envelope + tipo sorgente corretto.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LineagePassaggiApiTests.test_passaggi_ok_envelope
2) LineagePassaggiApiTests.test_passaggi_requires_jwt
3) LineagePassaggiApiTests.test_routing_domini_tipo_corretto
4) LineagePassaggiApiTests.test_ogni_tipo_in_whitelist_ha_la_sua_rotta
"""

from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_PASSAGGI_RESPONSE = {
    "nodo": {
        "tipo_codice": "ORDINE_VENDITA",
        "codice": "ORD0000163",
        "stato_codice_interno": "CONFERMATO",
        "stato_descrizione": "Confermato",
        "fase": "IN_CORSO",
        "is_abortito": False,
        "is_transitato": True,
        "n_discendenti_diretti": 1,
        "n_discendenti_attivi": 1,
        "n_sorgenti": 1,
    },
    "pratica": {"pratica_id": 818, "pratica_numero": "PRA-0000818", "n_pratiche": 1},
    "frontiera": {
        "tipo_codice": "DDT_VENDITA",
        "codice": "DDT0000031",
        "stato_codice_interno": "SPEDITO",
        "fase": "IN_CORSO",
        "n_discendenti_attivi": 1,
    },
    "avanti": [
        {
            "livello": 1,
            "ordine": 1,
            "arco": "H",
            "from_codice": "ORD0000163",
            "to_codice": "DDT0000031",
            "to_fase": "IN_CORSO",
            "is_ramo_inverso": False,
        }
    ],
    "indietro": [],
}

# Le 8 rotte di dominio -> tipo sorgente atteso dalla view (P-1; COMMESSA
# aggiunta in Fase C, genealogia inversa; FATTURA il 2026-08-21 con l'arco N
# verso la nota di credito).
_ROUTES = {
    "/api/v1/vendite/preventivi/185/passaggi/": "PREVENTIVO",
    "/api/v1/vendite/offerte/78/passaggi/": "OFFERTA_COMMERCIALE",
    "/api/v1/vendite/ordini/163/passaggi/": "ORDINE_VENDITA",
    "/api/v1/vendite/contratti/7/passaggi/": "CONTRATTO",
    "/api/v1/vendite/ddt/31/passaggi/": "DDT_VENDITA",
    "/api/v1/vendite/resi/4/passaggi/": "RESO_VENDITA",
    "/api/v1/vendite/commesse/186/passaggi/": "COMMESSA",
    "/api/v1/vendite/fatture/835/passaggi/": "FATTURA",
}


class LineagePassaggiApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.client = Client()

    _URL = "/api/v1/vendite/ordini/163/passaggi/"

    # Scopo: GET ok con envelope standard e passthrough dei campi FE-critici
    #        (pratica, frontiera, catena avanti).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.services.vendite_service.get_documento_passaggi")
    def test_passaggi_ok_envelope(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _PASSAGGI_RESPONSE
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["pratica"]["pratica_numero"], "PRA-0000818")
        self.assertEqual(data["frontiera"]["codice"], "DDT0000031")
        self.assertEqual(data["avanti"][0]["arco"], "H")
        self.assertEqual(mocked_fn.call_args.args, ("ORDINE_VENDITA", 163))

    # Scopo: Endpoint protetto da JWT.
    def test_passaggi_requires_jwt(self):
        response = self.client.get(self._URL)
        self.assertEqual(response.status_code, 401)

    # Scopo: Le 7 rotte di dominio risolvono e passano al service il proprio
    #        tipo sorgente + il doc_id del path.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.services.vendite_service.get_documento_passaggi")
    def test_routing_domini_tipo_corretto(self, mocked_fn, _mock_auth):
        mocked_fn.return_value = _PASSAGGI_RESPONSE
        for url, tipo_atteso in _ROUTES.items():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            tipo, doc_id = mocked_fn.call_args.args
            self.assertEqual(tipo, tipo_atteso, url)
            self.assertEqual(str(doc_id), url.split("/passaggi/")[0].rsplit("/", 1)[1], url)

    # Scopo: ⭐ LE DUE LISTE NON DEVONO DIVERGERE. La whitelist del service e le
    #        rotte sono scritte in due file diversi, e ognuna delle due
    #        divergenze e' muta: un tipo in whitelist senza rotta e' un 404 che
    #        nessun test raggiunge; una rotta senza il tipo e' un 400 che
    #        arriva solo all'operatore che ci clicca sopra.
    #        Il presidio e' costato una riga il giorno in cui e' entrata
    #        FATTURA — e senza, quella riga non l'avrebbe chiesta nessuno.
    def test_ogni_tipo_in_whitelist_ha_la_sua_rotta(self):
        from apps.vendite.services.vendite_service import LINEAGE_TIPI_DOCUMENTO
        self.assertEqual(
            sorted(_ROUTES.values()), sorted(LINEAGE_TIPI_DOCUMENTO)
        )
