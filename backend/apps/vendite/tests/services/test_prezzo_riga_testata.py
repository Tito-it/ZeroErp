# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I due BB del gate prezzi di riga letto dalla testata
#        (`_prezzo_riga_testata`, regola del 2 del 2026-11-15, passo 6e di
#        brief-db-provenienza-prezzo-segue-il-prezzo): la sola differenza fra
#        ordine e DDT (`prezzo_assente_ammesso`: guscio e prezzo obbligatorio
#        contro nucleo e prezzo assente ammesso) e la data della testata di
#        offerta e contratto (`campo_data`).
# Note: Il cablaggio dei domini resta nei loro test (`test_ordini_service`
#       «usano il guscio», `test_ddt_service` BE-B6, `test_pricing_gate_helpers`
#       `SenzaListinoTests`); il resolver vero in `tests/db/`.
# ------------------------------------------------------------
"""Indice test:

1) RegolePrezzoTestataTests.test_il_flag_sceglie_guscio_o_nucleo
2) RegolePrezzoTestataTests.test_senza_contesto_l_ordine_rifiuta_il_ddt_no
3) RegolePrezzoTestataTests.test_le_frasi_nominano_il_documento
4) ConListinoTests.test_la_data_viene_dal_campo_della_testata
5) ConListinoTests.test_la_data_della_testata_vince_sull_alias
6) RegolePrezzoTestataTests.test_la_patch_sulla_classe_arriva_al_gate
"""

from __future__ import annotations

from contextlib import nullcontext
from datetime import date
from unittest.mock import create_autospec, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.services._pricing_gate_helpers import EsitoPrezzoRiga
from apps.vendite.services._prezzo_riga_testata import (
    RegolePrezzoTestata,
    resolve_or_check_override_prezzo_con_listino,
)

_PRICING = "apps.vendite.services.pricing_service.PricingService"
_GATE = "apps.vendite.services._prezzo_riga_testata.resolve_or_check_override_prezzo"

_TESTATA = {
    "id": 7, "billing_account_id": 100, "utility_id": 5,
    "data": "2026-08-19", "emittente_fiscale_id": 3,
}


def _regole(*, prezzo_assente_ammesso: bool) -> RegolePrezzoTestata:
    return RegolePrezzoTestata(
        documento="DDT" if prezzo_assente_ammesso else "Ordine",
        error_code="E_X_VALIDAZIONE",
        function_name="test",
        prezzo_assente_ammesso=prezzo_assente_ammesso,
    )


def _repo():
    # Il contratto del BB e' il solo metodo dell'emittente: lo hanno uguale
    # ordini e DDT, quindi basta uno dei due come spec.
    repo = create_autospec(DdtRepository, instance=True)
    repo.get_emittente_sr_id_by_fiscale_id.return_value = 42
    return repo


class RegolePrezzoTestataTests(SimpleTestCase):

    # Scopo: ⛔ guscio e prezzo obbligatorio vanno insieme, ed e' un flag solo:
    #        se divergessero, l'ordine accetterebbe un prezzo assente o il DDT
    #        fermerebbe una riga che il brief-ddt-righe-senza-prezzo ammette.
    @patch(_PRICING)
    def test_il_flag_sceglie_guscio_o_nucleo(self, pricing_cls) -> None:
        pricing = pricing_cls.return_value
        for ammesso, chiamato, non_chiamato in (
            (False, pricing.resolve_prezzo, pricing.resolve_prezzo_esito),
            (True, pricing.resolve_prezzo_esito, pricing.resolve_prezzo),
        ):
            pricing.reset_mock()
            with self.subTest(prezzo_assente_ammesso=ammesso):
                _regole(prezzo_assente_ammesso=ammesso).resolve_prezzo_riga(
                    _repo(), _TESTATA, articolo_id="ART1", uom_id=5,
                )
                chiamato.assert_called_once()
                non_chiamato.assert_not_called()
                # L'emittente e' il soggetto_ruolo (42), non la PK della testata (3).
                self.assertEqual(chiamato.call_args.kwargs["emittente_soggetto_ruolo_id"], 42)

    # Scopo: senza billing account il gate non interroga il listino e, senza
    #        prezzo nel payload, torna senza prezzo: sull'ordine e' un 400 col
    #        campo, sul DDT un esito ammesso.
    @patch(_PRICING)
    def test_senza_contesto_l_ordine_rifiuta_il_ddt_no(self, pricing_cls) -> None:
        testata = {**_TESTATA, "billing_account_id": None}
        argomenti = {
            "articolo_id": "ART1", "uom_id": 5, "payload_prezzo": None,
            "dichiarata": None, "auth_user_id": 1, "function_name": "test",
        }

        with self.assertRaises(ServiceError) as cm:
            _regole(prezzo_assente_ammesso=False).gate_prezzo_riga(_repo(), testata, **argomenti)
        self.assertEqual(cm.exception.code, "E_X_VALIDAZIONE")

        esito = _regole(prezzo_assente_ammesso=True).gate_prezzo_riga(_repo(), testata, **argomenti)
        self.assertIsNone(esito.prezzo)
        pricing_cls.return_value.resolve_prezzo_esito.assert_not_called()

    def test_le_frasi_nominano_il_documento(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            _regole(prezzo_assente_ammesso=False).data_riferimento({**_TESTATA, "data": None})
        self.assertIn("Ordine senza data", str(cm.exception.message))
        with self.assertRaises(ServiceError) as cm:
            _regole(prezzo_assente_ammesso=True).emittente_sr_id(
                _repo(), {**_TESTATA, "emittente_fiscale_id": None},
            )
        self.assertIn("DDT senza emittente fiscale", str(cm.exception.message))

    # Scopo: ⛔ il gate passa dai METODI della classe (`gate` ->
    #        `resolve_prezzo_riga` -> `emittente_sr_id`, `data_riferimento`), e
    #        i test dei domini patchano la classe contando su questo. Un metodo
    #        che ricopiasse la regola dentro di se' renderebbe quelle patch
    #        mute: questo test diventa rosso.
    @patch("apps.vendite.services._pricing_gate_helpers.transaction")
    @patch(_PRICING)
    @patch.object(RegolePrezzoTestata, "data_riferimento", return_value=date(2026, 1, 2))
    @patch.object(RegolePrezzoTestata, "emittente_sr_id", return_value=77)
    def test_la_patch_sulla_classe_arriva_al_gate(self, _sr, _dr, pricing_cls, tx) -> None:
        # Il gate interroga il resolver in un savepoint: qui non c'e' il DB.
        tx.atomic.return_value = nullcontext()
        pricing = pricing_cls.return_value
        pricing.resolve_prezzo.return_value = {"prezzo_finale": "10.00"}
        _regole(prezzo_assente_ammesso=False).gate_prezzo_riga(
            _repo(), _TESTATA, articolo_id="ART1", uom_id=5, payload_prezzo=None,
            dichiarata=None, auth_user_id=1, function_name="test",
        )
        kwargs = pricing.resolve_prezzo.call_args.kwargs
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 77)
        self.assertEqual(kwargs["data_riferimento"], date(2026, 1, 2))


class ConListinoTests(SimpleTestCase):

    def _chiama(self, testata):
        return resolve_or_check_override_prezzo_con_listino(
            testata=testata, campo_data="valido_dal", articolo_id="a1", uom_id=2,
            payload_prezzo=None, auth_user_id=1, function_name="t",
            resolver_fn=lambda *a, **k: {}, error_code_validazione="E_X",
        )

    @patch(_GATE, return_value=EsitoPrezzoRiga(prezzo=None))
    def test_la_data_viene_dal_campo_della_testata(self, gate) -> None:
        self._chiama({"listino_id": 9, "valido_dal": "2026-05-01"})
        self.assertEqual(gate.call_args.kwargs["testata"]["data"], "2026-05-01")

    @patch(_GATE, return_value=EsitoPrezzoRiga(prezzo=None))
    def test_la_data_della_testata_vince_sull_alias(self, gate) -> None:
        self._chiama({"listino_id": 9, "data": "2026-06-01", "valido_dal": "2026-05-01"})
        self.assertEqual(gate.call_args.kwargs["testata"]["data"], "2026-06-01")
