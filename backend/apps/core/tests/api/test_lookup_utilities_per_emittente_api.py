# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API lookup utilities-per-emittente: la combo «Utility» mostra le
#        utility AMMESSE per il ruolo EF (`config.utilities_tipi_ruolo`),
#        uguali per ogni operatore, intersecate col ruolo del soggetto se dato.
#        ⛔ Dal 2026-10-14 non le filtra la tabella dei PARAMETRI di
#        fatturazione `anagrafiche.emittenti_fiscali_utilities` (opzionale per
#        il modello): un emittente con i parametri della sola luce si vedeva
#        sparire il gas (analisi-be-difetti-emersi-verifica-doc-api-core §6).
#        Due meta': la PORTA con repository finto, e la regola sul DB vero con
#        le utility FABBRICATE nel test (un confronto coi dati esistenti
#        passerebbe a vuoto su un DB ricostruito da zero).
#
# Indice test:
#   1. senza `ruolo`: il repository e' chiamato con None, l'envelope e' `results`
#   2. `?ruolo=cl` normalizzato a 'CL'
#   3. [DB vero] le utility ammesse per EF ci sono, quella non ammessa no
#   4. [DB vero] col ruolo del soggetto: solo quelle ammesse ANCHE per quel ruolo
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
_URL = "/api/v1/core/lookup/utilities-per-emittente/"


@patch(_AUTH, return_value=(Mock(id=42, is_superuser=True, is_authenticated=True), None))
@patch(_REPO)
class LookupUtilitiesPerEmittenteApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Senza ruolo: nessuna intersezione, e nessun emittente in gioco.
    def test_senza_ruolo(self, repo_cls, _auth) -> None:
        repo_cls.return_value.list_utilities_per_emittente.return_value = [
            {"id": 1, "codice": "EE", "codice_interno": "ENERGIA", "descrizione": "Energia"},
        ]
        resp = self.client.get(_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(len(resp.json()["data"]["results"]), 1)
        repo_cls.return_value.list_utilities_per_emittente.assert_called_once_with(None)

    # 2. Il ruolo arriva maiuscolo.
    def test_ruolo_normalizzato(self, repo_cls, _auth) -> None:
        repo_cls.return_value.list_utilities_per_emittente.return_value = []
        resp = self.client.get(_URL, {"ruolo": "cl"})
        self.assertEqual(resp.status_code, 200, resp.content)
        repo_cls.return_value.list_utilities_per_emittente.assert_called_once_with("CL")


class LookupUtilitiesPerEmittenteDbTests(TestCase):
    # ⚠️ `unittest.TestCase` di proposito: parla col DB provvisto, dentro una
    #    transazione annullata a fine test (`apri_transazione_annullata`).
    def setUp(self) -> None:
        richiedi_db_provvisto()
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            self.ammessa_ef = self._utility(cur, "ZTUEF1")
            self.ammessa_ef_e_cl = self._utility(cur, "ZTUEF2")
            self.non_ammessa = self._utility(cur, "ZTUNO")
            self._ammetti(cur, self.ammessa_ef, "EF")
            self._ammetti(cur, self.ammessa_ef_e_cl, "EF")
            self._ammetti(cur, self.ammessa_ef_e_cl, "CL")
            self._ammetti(cur, self.non_ammessa, "CL")

    @staticmethod
    def _utility(cur, codice: str) -> int:
        cur.execute(
            "INSERT INTO config.utilities (codice, descrizione, codice_interno)"
            " VALUES (%s, %s, %s) RETURNING id",
            [codice, f"Utility di prova {codice}", codice],
        )
        return int(cur.fetchone()[0])

    @staticmethod
    def _ammetti(cur, utility_id: int, ruolo: str) -> None:
        cur.execute(
            "INSERT INTO config.utilities_tipi_ruolo (utility_id, tipo_ruolo_id)"
            " SELECT %s, id FROM config.tipi_ruoli WHERE codice_interno = %s",
            [utility_id, ruolo],
        )
        if cur.rowcount != 1:
            raise AssertionError(f"tipo ruolo {ruolo} assente dal catalogo")

    @staticmethod
    def _ids(righe: list[dict]) -> set[int]:
        return {r["id"] for r in righe}

    # 3. Le ammesse per EF ci sono; quella ammessa solo per CL no.
    def test_ammesse_per_ef(self) -> None:
        ids = self._ids(LookupRepository().list_utilities_per_emittente())
        self.assertIn(self.ammessa_ef, ids)
        self.assertIn(self.ammessa_ef_e_cl, ids)
        self.assertNotIn(self.non_ammessa, ids)

    # 4. Col ruolo del soggetto: l'intersezione.
    def test_intersezione_col_ruolo_soggetto(self) -> None:
        ids = self._ids(LookupRepository().list_utilities_per_emittente("CL"))
        self.assertIn(self.ammessa_ef_e_cl, ids)
        self.assertNotIn(self.ammessa_ef, ids)
        self.assertNotIn(self.non_ammessa, ids)
