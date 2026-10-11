# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test del BB `_annullo_con_legami` (mock repository e lineage,
#        no DB) e dell'annullo con conferma del preventivo
#        (brief-db-annullo-documento-con-legami R-1, R-2).
# ------------------------------------------------------------

"""
Indice test eseguiti (classe :: metodo):

AnnulloConLegamiBBTests
 1) test_legami_conta_le_righe_del_lettore      — `legami` = count(*), non righe distinte
 2) test_nomi_dal_lineage_nelle_due_direzioni   — origini «indietro», commessa «avanti»
 3) test_nessun_legame_non_legge_il_lineage     — zero legami: niente lineage
 4) test_dichiarazione_non_numerica             — 400 col campo legami_confermati
 5) test_dichiarazione_assente                  — None al primo tentativo

PreventivoAnnulloTests
 6) test_annullo_passa_dal_verbo                — repo.annulla, forma di fn_cambia_stato_preventivo
 7) test_get_legami_dopo_la_testata             — 404 prima, poi il BB col codice PREVENTIVO
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.vendite.services import _annullo_con_legami as bb
from apps.vendite.services import preventivi_service

_REPO_V = "apps.vendite.db.vendite_repository.VenditeRepository"
_PASSAGGI = "apps.vendite.services.vendite_service.get_documento_passaggi"
_PREV_REPO = "apps.vendite.services.preventivi_service.PreventiviRepository"


def _legame(**k):
    base = {"riga_id": None, "riga_nr": None, "origine": "ORDINE", "natura": "CONSUMO",
            "origine_id": 12, "origine_riga_id": 5, "qta": Decimal("10")}
    return {**base, **k}


class AnnulloConLegamiBBTests(SimpleTestCase):
    @patch(_PASSAGGI, return_value={"indietro": [], "avanti": []})
    @patch(_REPO_V)
    def test_legami_conta_le_righe_del_lettore(self, repo_cls, _pass) -> None:
        # Una riga di ri-consegna da un reso nato da un ordine porta DUE legami:
        # la conferma dichiara il count(*) del lettore, come il verbo.
        repo_cls.return_value.list_documento_legami.return_value = [
            _legame(riga_id=31, riga_nr=1, origine="ORDINE"),
            _legame(riga_id=31, riga_nr=1, origine="RESO", origine_id=9),
        ]
        out = bb.legami_del_documento("DDT", 7)
        self.assertEqual(out["legami"], 2)
        self.assertEqual(out["documento"], "DDT")
        repo_cls.return_value.list_documento_legami.assert_called_once_with("DDT", 7)

    @patch(_PASSAGGI)
    @patch(_REPO_V)
    def test_nomi_dal_lineage_nelle_due_direzioni(self, repo_cls, passaggi) -> None:
        repo_cls.return_value.list_documento_legami.return_value = [
            _legame(riga_id=40, riga_nr=1, origine="PREVENTIVO", origine_id=3),
            _legame(origine="OFFERTA", natura="PROVENIENZA", origine_id=4, origine_riga_id=None),
            _legame(origine="COMMESSA", origine_id=50),
            _legame(origine="ORDINE", origine_id=77),  # il lineage non lo vede
        ]
        passaggi.return_value = {
            "indietro": [
                {"from_tipo_codice_interno": "PREVENTIVO", "from_doc_id": 3, "from_codice": "PV-3"},
                {"from_tipo_codice_interno": "OFFERTA_COMMERCIALE", "from_doc_id": 4, "from_codice": "OF-4"},
            ],
            "avanti": [
                {"to_tipo_codice_interno": "COMMESSA", "to_doc_id": 50, "to_codice": "CM-50"},
            ],
        }
        righe = bb.legami_del_documento("ORDINE", 8)["righe"]
        passaggi.assert_called_once_with("ORDINE_VENDITA", 8)
        self.assertEqual(
            [(r["origine_tipo_codice_interno"], r["origine_codice"]) for r in righe],
            [("PREVENTIVO", "PV-3"), ("OFFERTA_COMMERCIALE", "OF-4"),
             ("COMMESSA", "CM-50"), ("ORDINE_VENDITA", None)],
        )

    @patch(_PASSAGGI)
    @patch(_REPO_V)
    def test_nessun_legame_non_legge_il_lineage(self, repo_cls, passaggi) -> None:
        repo_cls.return_value.list_documento_legami.return_value = []
        out = bb.legami_del_documento("CONTRATTO", 5)
        self.assertEqual(out["legami"], 0)
        passaggi.assert_not_called()

    def test_dichiarazione_non_numerica(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            bb.legami_confermati("due", validation_code="E_X", function_name="t")
        self.assertEqual(cm.exception.code, "E_X")
        self.assertEqual(cm.exception.context.get("field"), "legami_confermati")

    def test_dichiarazione_assente(self) -> None:
        self.assertIsNone(bb.legami_confermati(None, validation_code="E_X", function_name="t"))
        self.assertEqual(bb.legami_confermati("4", validation_code="E_X", function_name="t"), 4)


class PreventivoAnnulloTests(SimpleTestCase):
    @patch(_PREV_REPO)
    def test_annullo_passa_dal_verbo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "EMESSO"
        out = preventivi_service.cambia_stato(7, "ANNULLATO", legami_confermati=1)
        repo.annulla.assert_called_once_with(7, 1)
        repo.cambia_stato.assert_not_called()
        self.assertEqual(out, {
            "preventivo_id": 7, "stato_precedente": "EMESSO", "stato_nuovo": "ANNULLATO",
        })

    @patch("apps.vendite.services.preventivi_service.legami_del_documento")
    @patch(_PREV_REPO)
    def test_get_legami_dopo_la_testata(self, repo_cls, bb_legami) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            preventivi_service.get_legami(99)
        self.assertEqual(cm.exception.code, "E_PREV_NOT_FOUND")
        bb_legami.assert_not_called()
        repo.get_stato_codice.return_value = "ACCETTATO"
        preventivi_service.get_legami(7)
        bb_legami.assert_called_once_with("PREVENTIVO", 7)
