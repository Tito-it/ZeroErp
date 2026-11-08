# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: GET /core/lookup/azioni-riga/ — il registro `config.azioni_riga` in
#        sola lettura, per il BB del pulsante di riga del frontend
#        (brief-modello-documento-vendita §15.11.1, BE-3). Due meta': la PORTA
#        e la FORMA con repository finto (senza DB), e una lettura sul DB
#        provvisto — il binding delle colonne per nome e la prima azione del
#        registro, il verso che i mock non vedono.
#
# Indice test:
#   1. senza JWT -> 401
#   2. envelope `{"data": {"results": [...]}}` — MAI la lista nuda
#      (api.md §L'ENVELOPE DI UN LOOKUP)
#   3. [DB vero] la lettura reale: le tre colonne per nome, la prima azione
#      del registro (`ESCLUDI_DOCUMENTO_DA_GIRO`) presente
#   4. [DB vero] un'azione SPENTA non esce: la si spegne davvero, in una
#      transazione annullata
# ------------------------------------------------------------
from unittest import TestCase
from unittest.mock import Mock, patch

from django.db import connection
from django.test import Client

from apps.core.db.lookup_repository import LookupRepository
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.core.api.views_lookup.LookupRepository"
_URL = "/api/v1/core/lookup/azioni-riga/"


class LookupAzioniRigaApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Senza JWT -> 401.
    def test_richiede_jwt(self) -> None:
        self.assertEqual(self.client.get(_URL).status_code, 401)

    # 2. La forma: `{"results": [...]}`, non la lista nuda. (Superuser: il
    #    permesso salta la catena e non parla col DB — qui si prova la forma.)
    @patch(_AUTH, return_value=(Mock(id=42, is_superuser=True, is_authenticated=True), None))
    @patch(_REPO, autospec=True)
    def test_il_lookup_torna_l_envelope_results(self, repo_cls, _auth) -> None:
        repo_cls.return_value.list_azioni_riga.return_value = [
            {
                "codice_interno": "ESCLUDI_DOCUMENTO_DA_GIRO",
                "colonna_motivo": "uscita_blocco_reason",
                "colonna_motivo_chiave": "uscita_blocco_reason_key",
            },
        ]
        resp = self.client.get(_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()["data"]
        self.assertIsInstance(data, dict)
        self.assertEqual(data["results"][0]["codice_interno"], "ESCLUDI_DOCUMENTO_DA_GIRO")
        repo_cls.return_value.list_azioni_riga.assert_called_once_with()


class LookupAzioniRigaDbTests(TestCase):
    # ⚠️ `unittest.TestCase` di proposito: questo test PARLA col DB provvisto
    #    (schema Liquibase completo), e `SimpleTestCase` glielo vieterebbe.
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 3. La lettura reale: colonne per nome, la prima azione.
    def test_lettura_reale_del_registro(self) -> None:
        righe = LookupRepository().list_azioni_riga()
        codici = {r["codice_interno"] for r in righe}
        self.assertIn("ESCLUDI_DOCUMENTO_DA_GIRO", codici)
        for r in righe:
            self.assertEqual(
                set(r), {"codice_interno", "colonna_motivo", "colonna_motivo_chiave"},
            )

    # 4. ⛔ Non si confronta col conteggio delle attive: sarebbe lo stesso
    #    predicato del repository riletto, verde per costruzione. Il caso si
    #    COSTRUISCE: la prima azione spenta, e la lettura non la porta piu'.
    def test_azione_spenta_non_esce(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE config.azioni_riga SET attivo = false"
                " WHERE codice_interno = 'ESCLUDI_DOCUMENTO_DA_GIRO'",
            )
            self.assertEqual(cur.rowcount, 1)
        codici = {r["codice_interno"] for r in LookupRepository().list_azioni_riga()}
        self.assertNotIn("ESCLUDI_DOCUMENTO_DA_GIRO", codici)
