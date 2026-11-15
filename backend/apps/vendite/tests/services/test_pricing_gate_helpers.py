# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il BB del gate prezzi di riga (`_pricing_gate_helpers`) nei pezzi che
#        nascono con K-5 / D-5 di brief-db-provenienza-prezzo-segue-il-prezzo
#        (§8.7, §8.11): la provenienza dichiarata dal form, l'esito che si scrive
#        sulla riga, il prezzo che non cambia, l'errore del listino che risale
#        quando il payload non porta un prezzo.
# Note: I casi dei tre rami del gate visti da un dominio stanno nei test dei
#       service (`test_contratti_service`, `test_preventivi_service`, …); il
#       legame col DB vero (il contesto calcolato da
#       `vendite.fn_prezzo_resolver_contesto`) in `tests/db/`.
# ------------------------------------------------------------
"""Indice test:

1) ProvenienzaDichiarataTests.test_assente_e_none
2) ProvenienzaDichiarataTests.test_si_legge_e_si_toglie_dal_corpo
3) ProvenienzaDichiarataTests.test_forma_sbagliata_e_un_400_del_dominio
4) EsitoPrezzoRigaTests.test_applica_scrive_le_quattro_colonne_e_fonde_l_audit
5) EsitoPrezzoRigaTests.test_applica_senza_provenienza_non_tocca_le_colonne
6) PrezzoInvariatoTests.test_casi
7) GateTests.test_senza_prezzo_l_errore_del_listino_risale
8) GateTests.test_col_prezzo_l_errore_del_listino_lascia_il_prezzo_del_payload
8b) GateTests.test_fuori_listino_senza_permesso_e_403
9) GateTests.test_col_prezzo_dichiarato_e_listino_muto_e_409
10) GateTests.test_dichiarazione_senza_contesto_e_409
11) GateTests.test_senza_prezzo_la_dichiarazione_non_conta
12) SenzaListinoTests.test_dichiarazione_senza_listino_e_409 (offerta, contratto)
13) SenzaListinoTests.test_senza_dichiarazione_il_prezzo_del_payload_passa
"""

from __future__ import annotations

from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services._pricing_gate_helpers import (
    CHIAVE_PROVENIENZA_DICHIARATA,
    COLONNE_PROVENIENZA_RIGA,
    PROVENIENZA_MANUALE_RIGA,
    EsitoPrezzoRiga,
    ProvenienzaDichiarata,
    prezzo_invariato,
    provenienza_dichiarata,
    resolve_or_check_override_prezzo,
)

_TESTATA = {"id": 1, "billing_account_id": 10, "utility_id": 3, "data": "2026-05-15"}


class ProvenienzaDichiarataTests(TestCase):

    def test_assente_e_none(self) -> None:
        self.assertIsNone(provenienza_dichiarata({}, error_code="E_X", function_name="t"))

    def test_si_legge_e_si_toglie_dal_corpo(self) -> None:
        corpo = {
            "prezzo_unitario": "10",
            CHIAVE_PROVENIENZA_DICHIARATA: {
                "origine_prezzo": " CATEGORIA ", "listino_versione_id": 7, "listino_riga_id": "70",
            },
        }
        self.assertEqual(
            provenienza_dichiarata(corpo, error_code="E_X", function_name="t"),
            ProvenienzaDichiarata("CATEGORIA", 7, 70),
        )
        # ⛔ Non e' una colonna: non deve arrivare al repository.
        self.assertNotIn(CHIAVE_PROVENIENZA_DICHIARATA, corpo)

    def test_forma_sbagliata_e_un_400_del_dominio(self) -> None:
        for nome, valore in {
            "non un oggetto": "CATEGORIA",
            "senza origine": {"listino_riga_id": 70},
            "chiave ignota": {"origine_prezzo": "CATEGORIA", "prezzo": 10},
            "id non intero": {"origine_prezzo": "CATEGORIA", "listino_riga_id": "settanta"},
        }.items():
            with self.subTest(caso=nome), self.assertRaises(ServiceError) as ctx:
                provenienza_dichiarata(
                    {CHIAVE_PROVENIENZA_DICHIARATA: valore}, error_code="E_X", function_name="t",
                )
            self.assertEqual(ctx.exception.code, "E_X")


class EsitoPrezzoRigaTests(TestCase):

    def test_applica_scrive_le_quattro_colonne_e_fonde_l_audit(self) -> None:
        campi: dict = {"prezzo_unitario": "9"}
        EsitoPrezzoRiga(
            prezzo=Decimal("9"), provenienza=PROVENIENZA_MANUALE_RIGA,
            meta={"override_user_id": 42},
        ).applica(campi, meta_base='{"nota": "di prima"}')
        self.assertEqual(campi["prezzo_unitario"], Decimal("9"))
        for colonna in COLONNE_PROVENIENZA_RIGA:
            self.assertIn(colonna, campi)
        self.assertEqual(campi["origine_prezzo"], "MANUALE")
        # Il meta della riga (anche come stringa JSON) non si perde.
        self.assertEqual(campi["meta"], {"nota": "di prima", "override_user_id": 42})

    def test_applica_senza_provenienza_non_tocca_le_colonne(self) -> None:
        campi: dict = {"prezzo_unitario": "9"}
        EsitoPrezzoRiga(prezzo=None).applica(campi)
        self.assertEqual(campi, {"prezzo_unitario": "9"})


class PrezzoInvariatoTests(TestCase):

    def test_casi(self) -> None:
        riga = {"prezzo_unitario": Decimal("10.0000000001"), "uom_operativa_id": 5}
        casi = [
            ("senza prezzo nei campi", {"qta_operativa": 2}, False),
            ("stesso prezzo, al netto del trasporto", {"prezzo_unitario": 10.0}, True),
            ("stesso prezzo, stessa unita'", {"prezzo_unitario": "10", "uom_operativa_id": 5}, True),
            ("stesso prezzo, altra unita'", {"prezzo_unitario": "10", "uom_operativa_id": 6}, False),
            ("prezzo cambiato", {"prezzo_unitario": "10.01"}, False),
            ("prezzo tolto", {"prezzo_unitario": None}, False),
            ("malformato: lo giudica il gate", {"prezzo_unitario": "dieci"}, False),
            ("booleano: lo giudica il gate", {"prezzo_unitario": True}, False),
        ]
        for nome, campi, atteso in casi:
            with self.subTest(caso=nome):
                self.assertIs(prezzo_invariato(campi, riga), atteso)
        self.assertTrue(prezzo_invariato({"prezzo_unitario": None}, {"prezzo_unitario": None}))


class GateTests(TestCase):

    def _gate(self, resolver: MagicMock, **kw):
        return resolve_or_check_override_prezzo(
            testata=kw.pop("testata", _TESTATA), articolo_id="art", uom_id=5,
            auth_user_id=42, function_name="t", resolver_fn=resolver,
            error_code_validazione="E_X", **kw,
        )

    def test_senza_prezzo_l_errore_del_listino_risale(self) -> None:
        resolver = MagicMock(side_effect=ServiceError(code="E_PREZZO_LISTINO_NON_TROVATO", message="x"))
        with self.assertRaises(ServiceError) as ctx:
            self._gate(resolver, payload_prezzo=None)
        self.assertEqual(ctx.exception.code, "E_PREZZO_LISTINO_NON_TROVATO")

    def test_col_prezzo_l_errore_del_listino_lascia_il_prezzo_del_payload(self) -> None:
        # R-1 (2026-11-15): il prezzo del payload resta, ma e' a mano: L1 si
        # chiede anche fuori listino, e la riga e' MANUALE.
        resolver = MagicMock(side_effect=ServiceError(code="E_PREZZO_LISTINO_NON_TROVATO", message="x"))
        with patch("apps.vendite.services._pricing_gate_helpers.check_permesso_override_prezzo") as l1:
            esito = self._gate(resolver, payload_prezzo="12")
        l1.assert_called_once()
        self.assertEqual(esito.prezzo, Decimal("12"))
        self.assertEqual(esito.provenienza, PROVENIENZA_MANUALE_RIGA)

    def test_fuori_listino_senza_permesso_e_403(self) -> None:
        # R-1: senza il permesso di override un prezzo a mano non passa,
        # nemmeno su un articolo che il listino non prezza o senza contesto.
        for nome, kw in (
            ("resolver che solleva", {"resolver": MagicMock(side_effect=ServiceError(code="E_PREZZO_LISTINO_NON_TROVATO", message="x"))}),
            ("senza contesto", {"resolver": MagicMock(), "testata": {**_TESTATA, "billing_account_id": None}}),
        ):
            with self.subTest(nome), patch(
                "apps.vendite.services._pricing_gate_helpers.check_permesso_override_prezzo",
                side_effect=ServiceError(code="E_PRICING_OVERRIDE_NON_AUTORIZZATO", message="no"),
            ), self.assertRaises(ServiceError) as ctx:
                resolver = kw.pop("resolver")
                self._gate(resolver, payload_prezzo="12", **kw)
            self.assertEqual(ctx.exception.code, "E_PRICING_OVERRIDE_NON_AUTORIZZATO")

    def test_col_prezzo_dichiarato_e_listino_muto_e_409(self) -> None:
        resolver = MagicMock(side_effect=ServiceError(code="E_PREZZO_LISTINO_NON_TROVATO", message="x"))
        with self.assertRaises(ServiceError) as ctx:
            self._gate(
                resolver, payload_prezzo="12",
                dichiarata=ProvenienzaDichiarata("CATEGORIA", 7, 70),
            )
        self.assertEqual(ctx.exception.code, "E_PRICING_PROVENIENZA_SUPERATA")

    def test_dichiarazione_senza_contesto_e_409(self) -> None:
        resolver = MagicMock()
        with self.assertRaises(ServiceError) as ctx:
            self._gate(
                resolver, payload_prezzo="12", testata={**_TESTATA, "billing_account_id": None},
                dichiarata=ProvenienzaDichiarata("CATEGORIA", 7, 70),
            )
        self.assertEqual(ctx.exception.code, "E_PRICING_PROVENIENZA_SUPERATA")
        resolver.assert_not_called()

    def test_senza_prezzo_la_dichiarazione_non_conta(self) -> None:
        resolver = MagicMock(return_value={
            "prezzo_finale": "30", "origine": "CATEGORIA",
            "listino_versione_id": 8, "listino_riga_id": 80, "prezzo_resolver_context": {},
        })
        with patch("apps.vendite.services._pricing_gate_helpers.check_permesso_override_prezzo") as l1:
            esito = self._gate(
                resolver, payload_prezzo=None,
                dichiarata=ProvenienzaDichiarata("PROMO", 1, 1),
            )
        self.assertEqual(esito.prezzo, Decimal("30"))
        self.assertEqual(esito.provenienza["listino_riga_id"], 80)
        l1.assert_not_called()


# R-2 della revisione del 2026-11-15: offerta e contratto senza listino non
# chiamano il gate, e una dichiarazione «dal listino» li' non si puo'
# verificare. Prima diventava MANUALE in silenzio; ora e' il 409 del gate.
class SenzaListinoTests(TestCase):

    def _wrapper(self):
        from apps.vendite.services.contratti_service import (
            resolve_or_check_override_prezzo_riga_contratto,
        )
        from apps.vendite.services.offerte_service import (
            resolve_or_check_override_prezzo_riga_offerta,
        )
        return {
            "contratto": resolve_or_check_override_prezzo_riga_contratto,
            "offerta": resolve_or_check_override_prezzo_riga_offerta,
        }

    def _chiama(self, fn, *, dichiarata):
        return fn(
            testata={**_TESTATA, "listino_id": None}, articolo_id="a1", uom_id=2,
            payload_prezzo="12", auth_user_id=42, function_name="t", dichiarata=dichiarata,
        )

    def test_dichiarazione_senza_listino_e_409(self) -> None:
        for nome, fn in self._wrapper().items():
            with self.subTest(nome), self.assertRaises(ServiceError) as ctx:
                self._chiama(fn, dichiarata=ProvenienzaDichiarata("CATEGORIA", 7, 70))
            self.assertEqual(ctx.exception.code, "E_PRICING_PROVENIENZA_SUPERATA")

    def test_senza_dichiarazione_il_prezzo_del_payload_passa(self) -> None:
        for nome, fn in self._wrapper().items():
            with self.subTest(nome):
                esito = self._chiama(fn, dichiarata=None)
                self.assertEqual(esito.prezzo, "12")
                self.assertIsNone(esito.provenienza)
