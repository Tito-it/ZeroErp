# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit per PricingDiagnoseService. Repository mockato — nessun
#        accesso DB (compat CI). Verifica orchestrazione 3 stadi + esito
#        atteso + azioni suggerite.
# ------------------------------------------------------------

# Indice test (1..8):
#   1) test_ba_non_trovato_raises_not_found
#   2) test_solo_matrice_applicabile
#   3) test_promo_attiva_categoria_non_partecipa
#   4) test_promo_applicabile_vince
#   5) test_contratto_modalita_a_b_applicabile
#   6) test_contratto_modalita_c_articolo_non_negoziato
#   7) test_nessuno_stadio_applicabile_errore_atteso_categoria
#   8) test_nessuno_stadio_con_contratto_c_errore_atteso_articolo

from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock

from apps.core.services.error_manager import ServiceError
from apps.vendite.services.pricing_diagnose_service import PricingDiagnoseService


_ART = "11111111-1111-1111-1111-111111111111"
_DATA = date(2026, 5, 5)


def _ba(*, partecipa_promo=True, categoria_id=1):
    return {
        "ba_id": 7,
        "categoria_cliente_id": categoria_id,
        "categoria_codice": "GOLD",
        "categoria_descrizione": "Gold",
        "categoria_partecipa_promo": partecipa_promo,
    }


def _make_service(repo: MagicMock) -> PricingDiagnoseService:
    return PricingDiagnoseService(repo=repo)


def _common_args():
    return {
        "articolo_id": _ART,
        "uom_id": 12,
        "data_riferimento": _DATA,
        "ba_id": 7,
        "utility_id": 5,
        "emittente_soggetto_ruolo_id": 72,
    }


class PricingDiagnoseServiceTests(TestCase):
    def test_ba_non_trovato_raises_not_found(self):
        repo = MagicMock()
        repo.get_ba_categoria.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            _make_service(repo).diagnose(**_common_args())
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    def test_solo_matrice_applicabile(self):
        repo = MagicMock()
        repo.get_ba_categoria.return_value = _ba()
        repo.find_promo_attiva.return_value = None
        repo.find_contratto_attivo.return_value = None
        repo.find_matrice_riga.return_value = {
            "matrice_riga_id": 99,
            "listino_id": 11,
            "listino_codice": "COM-001",
            "listino_descrizione": "Commercio standard",
            "classe_match": "FALLBACK_NULL",
        }
        out = _make_service(repo).diagnose(**_common_args())
        self.assertFalse(out["stadio_0_promo"]["applicabile"])
        self.assertFalse(out["stadio_1_contratto"]["applicabile"])
        self.assertTrue(out["stadio_2_categoria"]["applicabile"])
        self.assertEqual(out["esito_atteso"]["origine"], "CATEGORIA")
        self.assertEqual(out["azioni_suggerite"], [])

    def test_promo_attiva_categoria_non_partecipa(self):
        # Promo attiva ma categoria !partecipa_promo: stadio 0 non applicabile.
        repo = MagicMock()
        repo.get_ba_categoria.return_value = _ba(partecipa_promo=False)
        repo.find_promo_attiva.return_value = {
            "id": 1, "codice": "P1", "descrizione": "Promo",
        }
        repo.find_contratto_attivo.return_value = None
        repo.find_matrice_riga.return_value = None
        out = _make_service(repo).diagnose(**_common_args())
        self.assertFalse(out["stadio_0_promo"]["applicabile"])
        self.assertTrue(out["stadio_0_promo"]["promo_attiva_articolo"])
        self.assertIn(
            "non partecipa", out["stadio_0_promo"]["motivo"].lower(),
        )

    def test_promo_applicabile_vince(self):
        repo = MagicMock()
        repo.get_ba_categoria.return_value = _ba(partecipa_promo=True)
        repo.find_promo_attiva.return_value = {
            "id": 1, "codice": "P1", "descrizione": "Promo Q1",
        }
        repo.find_contratto_attivo.return_value = None
        repo.find_matrice_riga.return_value = None
        out = _make_service(repo).diagnose(**_common_args())
        self.assertTrue(out["stadio_0_promo"]["applicabile"])
        self.assertEqual(out["esito_atteso"]["origine"], "PROMO")

    def test_contratto_modalita_a_b_applicabile(self):
        repo = MagicMock()
        repo.get_ba_categoria.return_value = _ba()
        repo.find_promo_attiva.return_value = None
        repo.find_contratto_attivo.return_value = {
            "contratto_id": 42,
            "contratto_numero": "2026/000123",
            "listino_id": 11,
            "modalita_pricing": "A_O_B",
        }
        repo.find_matrice_riga.return_value = None
        out = _make_service(repo).diagnose(**_common_args())
        self.assertTrue(out["stadio_1_contratto"]["applicabile"])
        self.assertEqual(out["esito_atteso"]["origine"], "CONTRATTO_LISTINO")
        # contratto_riga_articolo_negoziato NON deve essere chiamato per A/B.
        repo.contratto_riga_articolo_negoziato.assert_not_called()

    def test_contratto_modalita_c_articolo_non_negoziato(self):
        repo = MagicMock()
        repo.get_ba_categoria.return_value = _ba()
        repo.find_promo_attiva.return_value = None
        repo.find_contratto_attivo.return_value = {
            "contratto_id": 42,
            "contratto_numero": "2026/000123",
            "listino_id": None,
            "modalita_pricing": "C",
        }
        repo.contratto_riga_articolo_negoziato.return_value = False
        repo.find_matrice_riga.return_value = None
        out = _make_service(repo).diagnose(**_common_args())
        self.assertFalse(out["stadio_1_contratto"]["applicabile"])
        self.assertFalse(out["stadio_1_contratto"]["articolo_negoziato_in_C"])
        self.assertEqual(
            out["esito_atteso"]["errore_atteso"],
            "E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C",
        )

    def test_nessuno_stadio_applicabile_errore_atteso_categoria(self):
        repo = MagicMock()
        repo.get_ba_categoria.return_value = _ba()
        repo.find_promo_attiva.return_value = None
        repo.find_contratto_attivo.return_value = None
        repo.find_matrice_riga.return_value = None
        out = _make_service(repo).diagnose(**_common_args())
        self.assertEqual(
            out["esito_atteso"]["errore_atteso"],
            "E_CATEGORIA_LISTINO_NON_MAPPATA",
        )
        # Suggerimenti attesi: matrice + contratto + promo.
        self.assertGreaterEqual(len(out["azioni_suggerite"]), 2)

    def test_nessuno_stadio_con_contratto_c_errore_atteso_articolo(self):
        repo = MagicMock()
        repo.get_ba_categoria.return_value = _ba()
        repo.find_promo_attiva.return_value = None
        repo.find_contratto_attivo.return_value = {
            "contratto_id": 42, "contratto_numero": "X",
            "listino_id": None, "modalita_pricing": "C",
        }
        repo.contratto_riga_articolo_negoziato.return_value = False
        repo.find_matrice_riga.return_value = None
        out = _make_service(repo).diagnose(**_common_args())
        self.assertEqual(
            out["esito_atteso"]["errore_atteso"],
            "E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C",
        )
        # Suggerimento specifico C: aggiungere riga al contratto.
        self.assertTrue(
            any("contratto" in a.lower() and "riga" in a.lower()
                for a in out["azioni_suggerite"]),
            f"azioni: {out['azioni_suggerite']}",
        )
