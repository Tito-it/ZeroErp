# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test del BB `_annullo_con_legami` (mock repository e lineage,
#        no DB) e dell'annullo con conferma del preventivo
#        (brief-db-annullo-documento-con-legami R-1, R-2).
# rev 2026-10-19 (brief-db-grammatica-unica-documenti lotto 2a): il documento
#        si nomina col codice di `config.sorgenti` (`DDT_VENDITA`,
#        `ORDINE_VENDITA`), lo stesso che va al lineage.
# rev 2026-10-19 (stesso brief, lotto 2b): anche l'`origine` dei legami e' il
#        codice della sorgente (tranne ONERE); il tipo del lineage e' l'origine
#        stessa, per le sole origini che sono un documento da aprire.
# ------------------------------------------------------------

"""
Indice test eseguiti (classe :: metodo):

AnnulloConLegamiBBTests
 1) test_legami_conta_le_righe_del_lettore      — `legami` = count(*), non righe distinte
 2) test_nomi_dal_lineage_nelle_due_direzioni   — origini «indietro», commessa «avanti»
 3) test_nessun_legame_non_legge_il_lineage     — zero legami: niente lineage
 4) test_dichiarazione_non_numerica             — 400 col campo legami_confermati
 5) test_dichiarazione_assente                  — None al primo tentativo
 5-bis) test_commessa_nomi_dal_lineage          — la commessa: origini «indietro» anche
                                                   contratto e bolla; consumo e onere senza tipo
 5-ter) test_origine_fuori_elenco_senza_tipo    — una sorgente non dichiarata non si apre

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
    base = {"riga_id": None, "riga_nr": None, "origine": "ORDINE_VENDITA", "natura": "CONSUMO",
            "origine_id": 12, "origine_riga_id": 5, "qta": Decimal("10")}
    return {**base, **k}


class AnnulloConLegamiBBTests(SimpleTestCase):
    @patch(_PASSAGGI, return_value={"indietro": [], "avanti": []})
    @patch(_REPO_V)
    def test_legami_conta_le_righe_del_lettore(self, repo_cls, _pass) -> None:
        # Una riga di ri-consegna da un reso nato da un ordine porta DUE legami:
        # la conferma dichiara il count(*) del lettore, come il verbo.
        repo_cls.return_value.list_documento_legami.return_value = [
            _legame(riga_id=31, riga_nr=1, origine="ORDINE_VENDITA"),
            _legame(riga_id=31, riga_nr=1, origine="RESO_VENDITA", origine_id=9),
        ]
        out = bb.legami_del_documento("DDT_VENDITA", 7)
        self.assertEqual(out["legami"], 2)
        self.assertEqual(out["documento"], "DDT_VENDITA")
        repo_cls.return_value.list_documento_legami.assert_called_once_with("DDT_VENDITA", 7)

    @patch(_PASSAGGI)
    @patch(_REPO_V)
    def test_nomi_dal_lineage_nelle_due_direzioni(self, repo_cls, passaggi) -> None:
        repo_cls.return_value.list_documento_legami.return_value = [
            _legame(riga_id=40, riga_nr=1, origine="PREVENTIVO", origine_id=3),
            _legame(origine="OFFERTA_COMMERCIALE", natura="PROVENIENZA", origine_id=4, origine_riga_id=None),
            _legame(origine="COMMESSA", origine_id=50),
            _legame(origine="ORDINE_VENDITA", origine_id=77),  # il lineage non lo vede
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
        righe = bb.legami_del_documento("ORDINE_VENDITA", 8)["righe"]
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

    # ⭐ La commessa (brief-db-annullo-a-valle-riapre-a-monte D-2): i suoi
    #    legami vengono da preventivo, ordine, contratto, bolla (lineage
    #    «indietro» della commessa), dal reso dell'accredito e dai consumi; gli
    #    oneri non hanno niente a monte. ATTIVITA_CONSUMI e ONERE restano senza tipo:
    #    la finestra li nomina senza link.
    @patch(_PASSAGGI)
    @patch(_REPO_V)
    def test_commessa_nomi_dal_lineage(self, repo_cls, passaggi) -> None:
        repo_cls.return_value.list_documento_legami.return_value = [
            _legame(riga_id=1, origine="CONTRATTO", origine_id=21, origine_riga_id=None),
            _legame(riga_id=2, origine="DDT_VENDITA", origine_id=31, origine_riga_id=None),
            _legame(riga_id=3, origine="ATTIVITA_CONSUMI", origine_id=41, origine_riga_id=None),
            _legame(riga_id=4, origine="ONERE", natura="ANNULLO", origine_id=None,
                    origine_riga_id=None),
        ]
        passaggi.return_value = {
            "indietro": [
                {"from_tipo_codice_interno": "CONTRATTO", "from_doc_id": 21, "from_codice": "CT-21"},
                {"from_tipo_codice_interno": "DDT_VENDITA", "from_doc_id": 31, "from_codice": "DDT-31"},
            ],
            "avanti": [],
        }
        out = bb.legami_del_documento("COMMESSA", 9)
        passaggi.assert_called_once_with("COMMESSA", 9)
        self.assertEqual(out["legami"], 4)
        self.assertEqual(
            [(r["origine_tipo_codice_interno"], r["origine_codice"]) for r in out["righe"]],
            [("CONTRATTO", "CT-21"), ("DDT_VENDITA", "DDT-31"), (None, None), (None, None)],
        )

    # ⭐ Che un'origine sia un documento da aprire lo dichiara il backend
    #    (`_ORIGINI_DOCUMENTO`), non il fatto che sia una sorgente: una
    #    sorgente che il lettore imparasse a dare resta senza tipo (la finestra
    #    la nomina, senza link) e senza nome, anche se il lineage la vede.
    @patch(_PASSAGGI)
    @patch(_REPO_V)
    def test_origine_fuori_elenco_senza_tipo(self, repo_cls, passaggi) -> None:
        repo_cls.return_value.list_documento_legami.return_value = [
            _legame(riga_id=1, origine="FATTURA", origine_id=61, origine_riga_id=None),
        ]
        passaggi.return_value = {
            "indietro": [
                {"from_tipo_codice_interno": "FATTURA", "from_doc_id": 61, "from_codice": "FT-61"},
            ],
            "avanti": [],
        }
        riga = bb.legami_del_documento("COMMESSA", 9)["righe"][0]
        self.assertIsNone(riga["origine_tipo_codice_interno"])
        self.assertIsNone(riga["origine_codice"])

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
