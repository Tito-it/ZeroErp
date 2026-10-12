# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Aggiorna date di consegna» (brief-db-date-consegna-righe-in-blocco
#        §5, §8): la FORMA della richiesta nel BB `_date_consegna_righe` e i
#        due service che lo usano (ordine, preventivo). Repository finto: la
#        scrittura vera e i lock del DB li prova `tests/db/test_date_consegna_righe_db.py`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) DateConsegnaRigheTests.test_tutte_scrive_su_tutte_le_righe
2) DateConsegnaRigheTests.test_solo_vuote_e_anteprima_arrivano_al_repository
3) DateConsegnaRigheTests.test_colonna_che_il_documento_non_ha_e_400
4) DateConsegnaRigheTests.test_data_obbligatoria
5) DateConsegnaRigheTests.test_modalita_sconosciuta_e_400
6) DateConsegnaRigheTests.test_chiave_estranea_e_400
7) DateConsegnaRigheTests.test_anteprima_non_booleana_e_400
8) OrdiniDateConsegnaTests.test_nessun_pre_check_di_stato
9) OrdiniDateConsegnaTests.test_ordine_fuori_perimetro_e_404
10) OrdiniDateConsegnaTests.test_il_rifiuto_del_lock_passa_col_suo_codice
11) PreventiviDateConsegnaTests.test_la_data_confermata_non_e_del_preventivo
12) PreventiviDateConsegnaTests.test_preventivo_fuori_perimetro_e_404
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.services import ordini_service, preventivi_service
from apps.vendite.services._date_consegna_righe import aggiorna_date_consegna_righe

_REPO_ORDINI = "apps.vendite.services.ordini_service.OrdiniRepository"
_REPO_PREVENTIVI = "apps.vendite.services.preventivi_service.PreventiviRepository"


# Scopo: un repository finto con le colonne VERE del documento (il metodo
#        di classe del repository), cosi' la whitelist provata e' quella del repository.
def _repo(classe: type) -> MagicMock:
    repo = MagicMock()
    repo.colonne_date_consegna.return_value = classe.colonne_date_consegna()
    repo.scrivi_data_consegna.return_value = {"aggiornate": 3, "saltate": 1}
    return repo


def _chiama(repo: MagicMock, payload: dict) -> dict:
    return aggiorna_date_consegna_righe(
        repo, 7, payload, error_code="E_ORD_VALIDAZIONE", function_name="test",
    )


class DateConsegnaRigheTests(SimpleTestCase):
    def test_tutte_scrive_su_tutte_le_righe(self) -> None:
        repo = _repo(OrdiniRepository)
        out = _chiama(repo, {
            "colonna": "data_consegna_confermata", "data": "2026-11-20", "modalita": "TUTTE",
        })
        repo.scrivi_data_consegna.assert_called_once_with(
            7, "data_consegna_confermata", date(2026, 11, 20),
            solo_vuote=False, anteprima=False,
        )
        self.assertEqual(out["aggiornate"], 3)
        self.assertEqual(out["saltate_spedite"], 1)
        self.assertFalse(out["anteprima"])

    def test_solo_vuote_e_anteprima_arrivano_al_repository(self) -> None:
        repo = _repo(OrdiniRepository)
        out = _chiama(repo, {
            "colonna": "data_consegna_richiesta_cliente", "data": "2026-11-20",
            "modalita": "solo_vuote", "anteprima": True,
        })
        repo.scrivi_data_consegna.assert_called_once_with(
            7, "data_consegna_richiesta_cliente", date(2026, 11, 20),
            solo_vuote=True, anteprima=True,
        )
        self.assertEqual(out["modalita"], "SOLO_VUOTE")
        self.assertTrue(out["anteprima"])

    def test_colonna_che_il_documento_non_ha_e_400(self) -> None:
        repo = _repo(PreventiviRepository)
        with self.assertRaises(ServiceError) as cm:
            _chiama(repo, {
                "colonna": "data_consegna_confermata", "data": "2026-11-20", "modalita": "TUTTE",
            })
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "colonna")
        repo.scrivi_data_consegna.assert_not_called()

    def test_data_obbligatoria(self) -> None:
        repo = _repo(OrdiniRepository)
        with self.assertRaises(ServiceError) as cm:
            _chiama(repo, {
                "colonna": "data_consegna_confermata", "data": None, "modalita": "TUTTE",
            })
        self.assertEqual(cm.exception.context.get("field"), "data")
        repo.scrivi_data_consegna.assert_not_called()

    def test_modalita_sconosciuta_e_400(self) -> None:
        repo = _repo(OrdiniRepository)
        with self.assertRaises(ServiceError) as cm:
            _chiama(repo, {
                "colonna": "data_consegna_confermata", "data": "2026-11-20", "modalita": "QUALCUNA",
            })
        self.assertEqual(cm.exception.context.get("field"), "modalita")
        repo.scrivi_data_consegna.assert_not_called()

    def test_chiave_estranea_e_400(self) -> None:
        repo = _repo(OrdiniRepository)
        with self.assertRaises(ServiceError):
            _chiama(repo, {
                "colonna": "data_consegna_confermata", "data": "2026-11-20",
                "modalita": "TUTTE", "riga_id": 60,
            })
        repo.scrivi_data_consegna.assert_not_called()

    def test_anteprima_non_booleana_e_400(self) -> None:
        repo = _repo(OrdiniRepository)
        with self.assertRaises(ServiceError) as cm:
            _chiama(repo, {
                "colonna": "data_consegna_confermata", "data": "2026-11-20",
                "modalita": "TUTTE", "anteprima": "si",
            })
        self.assertEqual(cm.exception.context.get("field"), "anteprima")


class OrdiniDateConsegnaTests(SimpleTestCase):
    @patch(_REPO_ORDINI)
    def test_nessun_pre_check_di_stato(self, repo_cls) -> None:
        # Fuori bozza la data confermata si scrive: lo stato lo giudica il
        # lock nello stesso UPDATE, il service non lo guarda.
        repo = repo_cls.return_value
        repo.colonne_date_consegna.return_value = OrdiniRepository.colonne_date_consegna()
        repo.get_stato_codice.return_value = "PARZIALMENTE_EVASO"
        repo.scrivi_data_consegna.return_value = {"aggiornate": 2, "saltate": 1}
        out = ordini_service.aggiorna_date_consegna(7, {
            "colonna": "data_consegna_confermata", "data": "2026-11-20", "modalita": "TUTTE",
        })
        self.assertEqual((out["aggiornate"], out["saltate_spedite"]), (2, 1))
        repo.get_ordine.assert_not_called()

    @patch(_REPO_ORDINI)
    def test_ordine_fuori_perimetro_e_404(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            ordini_service.aggiorna_date_consegna(7, {
                "colonna": "data_consegna_confermata", "data": "2026-11-20", "modalita": "TUTTE",
            })
        self.assertEqual(cm.exception.code, "E_ORD_NOT_FOUND")
        repo.scrivi_data_consegna.assert_not_called()

    @patch(_REPO_ORDINI)
    def test_il_rifiuto_del_lock_passa_col_suo_codice(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.colonne_date_consegna.return_value = OrdiniRepository.colonne_date_consegna()
        repo.get_stato_codice.return_value = "CONFERMATO"
        repo.scrivi_data_consegna.side_effect = DatabaseError(
            "E_RIGA_DOC_NON_BOZZA: Ordine 12 in stato CONFERMATO, la riga non si modifica",
        )
        with self.assertRaises(ServiceError) as cm:
            ordini_service.aggiorna_date_consegna(7, {
                "colonna": "data_consegna_richiesta_cliente", "data": "2026-11-20",
                "modalita": "TUTTE",
            })
        self.assertEqual(cm.exception.code, "E_RIGA_DOC_NON_BOZZA")


class PreventiviDateConsegnaTests(SimpleTestCase):
    @patch(_REPO_PREVENTIVI)
    def test_la_data_confermata_non_e_del_preventivo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.colonne_date_consegna.return_value = PreventiviRepository.colonne_date_consegna()
        repo.get_preventivo.return_value = {"id": 9, "stato_codice_interno": "DRAFT"}
        with self.assertRaises(ServiceError) as cm:
            preventivi_service.aggiorna_date_consegna(9, {
                "colonna": "data_consegna_confermata", "data": "2026-11-20", "modalita": "TUTTE",
            })
        self.assertEqual(cm.exception.code, "E_PREV_VALIDAZIONE")
        repo.scrivi_data_consegna.assert_not_called()

    @patch(_REPO_PREVENTIVI)
    def test_preventivo_fuori_perimetro_e_404(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as cm:
            preventivi_service.aggiorna_date_consegna(9, {
                "colonna": "data_consegna_richiesta_cliente", "data": "2026-11-20",
                "modalita": "TUTTE",
            })
        self.assertEqual(cm.exception.code, "E_PREV_NOT_FOUND")
        repo.scrivi_data_consegna.assert_not_called()
