# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `normalizza_codici_riga` (apps/vendite/services/
#        _righe_codici.py): i codici a vocabolario di una riga di contratto o
#        di offerta letti in una forma sola.
# ------------------------------------------------------------
"""
Indice test:

RigheCodiciTests (unit, senza DB)
 1) test_strip_e_maiuscolo           — « trimestrale » -> TRIMESTRALE
 2) test_vuota_e_null_sono_null      — '' e None -> None, per ogni campo
 3) test_assente_resta_assente       — PATCH: «non mandata» non e' «azzerata»
 4) test_non_stringa_e_400_col_campo — 3 -> E_VENDITE_VALIDATION, field
 5) test_altre_chiavi_intatte        — tocca solo i CAMPI_CODICE_RIGA, payload d'ingresso intatto
 6) test_contratto_legge_come_il_bb       — `_build_data_riga` = il BB (l'offerta: test_offerte_service 66-67)
"""

from __future__ import annotations

from django.test import SimpleTestCase

from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.service_errors import ServiceError
from apps.vendite.services._righe_codici import CAMPI_CODICE_RIGA, normalizza_codici_riga

_V = PayloadValidator(validation_code="E_VENDITE_VALIDATION", log_to_db=False)


class RigheCodiciTests(SimpleTestCase):
    # Scopo: 1) la forma del codice a catalogo.
    def test_strip_e_maiuscolo(self):
        out = normalizza_codici_riga(_V, {"periodicita": " trimestrale "})
        self.assertEqual(out["periodicita"], "TRIMESTRALE")

    # Scopo: 2) vuota e null sono lo stesso «non scritto» (NULL, mai '').
    def test_vuota_e_null_sono_null(self):
        for campo in CAMPI_CODICE_RIGA:
            for valore in ("", "   ", None):
                with self.subTest(campo=campo, valore=valore):
                    self.assertIsNone(normalizza_codici_riga(_V, {campo: valore})[campo])

    # Scopo: 3) una chiave assente non compare: in PATCH azzererebbe la colonna.
    def test_assente_resta_assente(self):
        self.assertEqual(normalizza_codici_riga(_V, {}), {})

    # Scopo: 4) un non-stringa e' un 400 col campo, non un AttributeError.
    def test_non_stringa_e_400_col_campo(self):
        with self.assertRaises(ServiceError) as cm:
            normalizza_codici_riga(_V, {"tipo_erogazione": 3})
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(cm.exception.context.get("field"), "tipo_erogazione")

    # Scopo: 5) le altre chiavi passano com'erano, e il payload d'ingresso
    #        non si modifica (il chiamante puo' riusarlo).
    def test_altre_chiavi_intatte(self):
        ingresso = {"descrizione": " libera ", "periodicita": "mensile"}
        out = normalizza_codici_riga(_V, ingresso)
        self.assertEqual(out["descrizione"], " libera ")
        self.assertEqual(ingresso["periodicita"], "mensile")

    # Scopo: 6) il punto della regola del 2: il contratto, con lo stesso
    #        ingresso, scrive cio' che scrive il BB (e quindi l'offerta).
    def test_contratto_legge_come_il_bb(self):
        from apps.vendite.services.contratti_service import ContrattiService

        ingresso = {"fonte_quantita_attesa": " manuale ", "periodicita": "", "generazione_canone": None}
        dal_contratto = ContrattiService.__new__(ContrattiService)
        dal_contratto._v = _V
        data = dal_contratto._build_data_riga(ingresso, for_create=False)
        attesi = normalizza_codici_riga(_V, ingresso)
        for campo in ingresso:
            self.assertEqual(data[campo], attesi[campo])
