# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test API lookup utilities-per-emittente: la combo «Utility» mostra le
#        utility che le aziende GESTISCONO (brief-db-utility-gestite-dall-
#        emittente §10 R-2, 2026-11-27): con `emittente_fiscale_id` quelle
#        dell'azienda, senza quelle gestite da almeno un'azienda del perimetro;
#        col `ruolo` anche ammesse per il ruolo del soggetto. La regola e' del
#        BB del DB `anagrafiche.fn_utilities_emittente`.
#        ⛔ Fino al 2026-11-27 la combo leggeva la sola matrice (ammesse per
#        EF): proponeva utility che l'azienda non gestisce, e il salvataggio
#        le rifiutava con le FK `*_utility_gestita`.
#        Due meta': la PORTA con repository finto, e la regola sul DB vero con
#        utility e aziende FABBRICATE nel test (un confronto coi dati esistenti
#        passerebbe a vuoto su un DB ricostruito da zero).
#
# Indice test:
#   1. senza parametri: il repository riceve il perimetro, nessun ruolo, nessuna azienda
#   2. `?ruolo= cl ` arriva com'e' (strip, niente maiuscolo); `emittente_fiscale_id` intero
#   3. `emittente_fiscale_id` non numerico: 400 prima del repository
#   4. [DB vero] con l'azienda: le gestite ci sono; tolta la riga, l'utility esce;
#      quella non ammessa per EF non c'e'
#   5. [DB vero] col ruolo del soggetto: solo quelle ammesse ANCHE per quel ruolo
#   6. [DB vero] senza azienda: le gestite dalle aziende del PERIMETRO, non da altre
# ------------------------------------------------------------
from unittest import TestCase
from unittest.mock import Mock, patch

from django.db import connection
from django.test import Client

from apps.core.db.lookup_repository import LookupRepository
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.core.tests.db_e2e import (
    apri_contesto_su,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_REPO = "apps.core.api.views_lookup.LookupRepository"
_URL = "/api/v1/core/lookup/utilities-per-emittente/"


@patch(_AUTH, return_value=(Mock(id=42, is_superuser=True, is_authenticated=True), None))
@patch(_REPO, autospec=True)
class LookupUtilitiesPerEmittenteApiTests(JwtMockedApiTest):
    come_super_admin = True
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Senza parametri: il perimetro di chi chiede, nessun ruolo, nessuna azienda.
    def test_senza_parametri(self, repo_cls, _auth) -> None:
        repo_cls.return_value.list_utilities_per_emittente.return_value = [
            {"id": 1, "codice": "EE", "codice_interno": "ENERGIA", "descrizione": "Energia"},
        ]
        resp = self.client.get(_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(len(resp.json()["data"]["results"]), 1)
        repo_cls.return_value.list_utilities_per_emittente.assert_called_once_with(
            auth_user_id=42, ruolo_codice_soggetto=None, emittente_fiscale_id=None,
        )

    # 2. Il ruolo e' il `codice_interno`: arriva al repository com'e' (solo
    #    lo spazio ai bordi si toglie), senza maiuscolo. Fino al 2026-11-04 la
    #    view faceva `.upper()` (brief-be-codice-maiuscolo §7.2).
    def test_ruolo_chiave_esatta_e_azienda(self, repo_cls, _auth) -> None:
        repo_cls.return_value.list_utilities_per_emittente.return_value = []
        resp = self.client.get(_URL, {"ruolo": " cl ", "emittente_fiscale_id": "7"})
        self.assertEqual(resp.status_code, 200, resp.content)
        repo_cls.return_value.list_utilities_per_emittente.assert_called_once_with(
            auth_user_id=42, ruolo_codice_soggetto="cl", emittente_fiscale_id=7,
        )

    # 3. Un'azienda non numerica e' un 400, e il repository non si chiama.
    def test_azienda_non_numerica(self, repo_cls, _auth) -> None:
        resp = self.client.get(_URL, {"emittente_fiscale_id": "abc"})
        self.assertEqual(resp.status_code, 400, resp.content)
        repo_cls.return_value.list_utilities_per_emittente.assert_not_called()


class LookupUtilitiesPerEmittenteDbTests(TestCase):
    # ⚠️ `unittest.TestCase` di proposito: parla col DB provvisto, dentro una
    #    transazione annullata a fine test (`apri_transazione_annullata`).
    def setUp(self) -> None:
        richiedi_db_provvisto("anagrafiche.fn_utilities_emittente(bigint, varchar)")
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            self.ammessa_ef = self._utility(cur, "ZTUEF1")
            self.ammessa_ef_e_cl = self._utility(cur, "ZTUEF2")
            self.non_ammessa = self._utility(cur, "ZTUNO")
            self._ammetti(cur, self.ammessa_ef, "EF")
            self._ammetti(cur, self.ammessa_ef_e_cl, "EF")
            self._ammetti(cur, self.ammessa_ef_e_cl, "CL")
            self._ammetti(cur, self.non_ammessa, "CL")
            # Due aziende di prova: ognuna gestisce ogni utility ammessa per
            # EF (lo fa l'helper). L'operatore della prima ha nel perimetro
            # solo la sua.
            self.azienda, self.operatore = self._azienda(cur, "ZTU1")
            self.altra, _ = self._azienda(cur, "ZTU2")
            apri_contesto_su(cur, self.operatore)

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
    def _azienda(cur, sigla: str) -> tuple[int, int]:
        cur.execute(
            "SELECT emittente_fiscale_id, auth_user_id"
            "  FROM dbops.fn_pgtap_crea_emittente_operatore(%s)",
            [sigla],
        )
        emittente_id, operatore = cur.fetchone()
        return int(emittente_id), int(operatore)

    @staticmethod
    def _togli(emittente_id: int, utility_id: int) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "DELETE FROM anagrafiche.emittenti_fiscali_utilities e"
                "  USING anagrafiche.emittenti_fiscali ef"
                " WHERE ef.id = %s AND e.emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id"
                "   AND e.utility_id = %s",
                [emittente_id, utility_id],
            )
            if cur.rowcount != 1:
                raise AssertionError("la riga dell'azienda di prova non c'era")

    def _ids(self, **kwargs) -> set[int]:
        righe = LookupRepository().list_utilities_per_emittente(
            auth_user_id=self.operatore, **kwargs,
        )
        return {r["id"] for r in righe}

    # 4. Con l'azienda: le gestite; tolta la riga, l'utility esce.
    def test_gestite_dall_azienda(self) -> None:
        ids = self._ids(emittente_fiscale_id=self.azienda)
        self.assertIn(self.ammessa_ef, ids)
        self.assertIn(self.ammessa_ef_e_cl, ids)
        self.assertNotIn(self.non_ammessa, ids)
        self._togli(self.azienda, self.ammessa_ef)
        ids = self._ids(emittente_fiscale_id=self.azienda)
        self.assertNotIn(self.ammessa_ef, ids)
        self.assertIn(self.ammessa_ef_e_cl, ids)

    # 5. Col ruolo del soggetto: l'intersezione.
    def test_intersezione_col_ruolo_soggetto(self) -> None:
        ids = self._ids(emittente_fiscale_id=self.azienda, ruolo_codice_soggetto="CL")
        self.assertIn(self.ammessa_ef_e_cl, ids)
        self.assertNotIn(self.ammessa_ef, ids)
        self.assertNotIn(self.non_ammessa, ids)

    # 6. Senza azienda: il perimetro. L'altra azienda gestisce ancora
    #    l'utility, ma non e' nel perimetro dell'operatore.
    def test_perimetro_senza_azienda(self) -> None:
        self.assertIn(self.ammessa_ef, self._ids())
        self._togli(self.azienda, self.ammessa_ef)
        self.assertNotIn(self.ammessa_ef, self._ids())
        self.assertNotIn(self.ammessa_ef, self._ids(emittente_fiscale_id=self.altra))
