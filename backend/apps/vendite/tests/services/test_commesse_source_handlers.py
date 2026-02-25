# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari handler sorgente commesse.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CommesseSourceHandlersTests.test_handler_ordini_sorgente_codice_ordine_vendita
2) CommesseSourceHandlersTests.test_process_rows_crea_commessa_e_upsert
3) CommesseSourceHandlersTests.test_process_rows_dry_run_skippa_upsert
4) CommesseSourceHandlersTests.test_process_rows_extract_tipo_commessa_da_meta
5) CommesseSourceHandlersTests.test_process_rows_extract_policy_fatturazione_da_meta
6) CommesseSourceHandlersTests.test_process_rows_default_priorita_operativa_normale
7) CommesseSourceHandlersTests.test_process_rows_default_prezzo_da_riallineare_false
8) CommesseSourceHandlersTests.test_process_rows_default_stato_approvazione_bozza
9) CommesseSourceHandlersTests.test_process_rows_isolamento_errori_per_riga
10) CommesseSourceHandlersTests.test_handler_contratti_esiste
11) CommesseSourceHandlersTests.test_handler_ddt_esiste
12) CommesseSourceHandlersTests.test_handler_consumi_expand_rows_fanout
"""

from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock

from apps.vendite.db.commesse_repository import CommesseRepository, PushableRow
from apps.vendite.services.commesse_source_handlers import (
    ComponenteConsumabile,
    HandlerConsumi,
    HandlerContratti,
    HandlerDdt,
    HandlerOrdini,
    HandlerPreventivi,
)


def _make_row(**overrides) -> PushableRow:
    """Crea un PushableRow con valori di default ragionevoli."""
    defaults = {
        "billing_account_id": 1,
        "utility_id": 2,
        "emittente_soggetto_ruolo_id": 3,
        "competenza_dal": date(2026, 6, 1),
        "competenza_al": date(2026, 6, 30),
        "fatturazione_immediata": False,
        "sorgente_tipo_id": 5,
        "sorgente_uid": "uid-001",
        "segment_key": "TEST:uid-001:R:1",
        "articolo_id": "art-uuid-001",
        "istanza_utility_id": 4,
        "data_attivita": date(2026, 6, 1),
        "uom_id": None,
        "quantita": Decimal("10.0"),
        "qta_operativa": Decimal("10.0"),
        "uom_operativa_id": None,
        "factor_to_base": Decimal("1"),
        "competenza_mese": date(2026, 6, 1),
        "prezzo_snapshot": Decimal("22.50"),
        "prezzo_bloccato": True,
        "pricing_mode": "FIXED",
        "tipo_movimento": "NORMALE",
        "tipo_consumo": "CONGUAGLIO",
        "valuta_id": 1,
        "meta": {"tipo_commessa": "AUTO", "policy_fatturazione": "DA_DOCUMENTO"},
    }
    defaults.update(overrides)
    return PushableRow(**defaults)


def _mock_repo(commessa_id: int = 10, attivita_id: int = 77) -> MagicMock:
    """Crea un mock CommesseRepository con risposte standard."""
    repo = MagicMock(spec=CommesseRepository)
    repo.fetch_pushable_rows.return_value = []
    repo.get_or_create_commessa.return_value = commessa_id
    repo.link_sorgente.return_value = 1
    repo.upsert_attivita.return_value = attivita_id
    return repo


class CommesseSourceHandlersTests(TestCase):

    # Scopo: Verifica che HandlerOrdini usi ORDINE_VENDITA (#1), non ORDINE.
    def test_handler_ordini_sorgente_codice_ordine_vendita(self):
        repo = _mock_repo()
        handler = HandlerOrdini(repo)
        self.assertEqual(handler.sorgente_codice, "ORDINE_VENDITA")
        self.assertEqual(handler.name, "HandlerOrdini")

    # Scopo: Happy path — una riga → get_or_create_commessa + link + upsert.
    def test_process_rows_crea_commessa_e_upsert(self):
        repo = _mock_repo()
        row = _make_row()
        repo.fetch_pushable_rows.return_value = [row]
        handler = HandlerPreventivi(repo)

        result = handler.run()

        self.assertEqual(result.created, 1)
        self.assertEqual(result.errors, [])
        repo.get_or_create_commessa.assert_called_once()
        repo.link_sorgente.assert_called_once()
        repo.upsert_attivita.assert_called_once()

    # Scopo: dry_run=True → nessuna chiamata upsert, ma commessa creata e linked.
    def test_process_rows_dry_run_skippa_upsert(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerPreventivi(repo)

        result = handler.run(dry_run=True)

        self.assertEqual(result.created, 1)
        repo.get_or_create_commessa.assert_called_once()
        repo.link_sorgente.assert_called_once()
        repo.upsert_attivita.assert_not_called()

    # Scopo: tipo_commessa estratto da meta (#6).
    def test_process_rows_extract_tipo_commessa_da_meta(self):
        repo = _mock_repo()
        row = _make_row(meta={"tipo_commessa": "REALE", "policy_fatturazione": "DA_DOCUMENTO"})
        repo.fetch_pushable_rows.return_value = [row]
        handler = HandlerPreventivi(repo)

        handler.run()

        call_kwargs = repo.get_or_create_commessa.call_args.kwargs
        self.assertEqual(call_kwargs["tipo_commessa"], "REALE")

    # Scopo: policy_fatturazione estratto da meta (#6).
    def test_process_rows_extract_policy_fatturazione_da_meta(self):
        repo = _mock_repo()
        row = _make_row(meta={"tipo_commessa": "AUTO", "policy_fatturazione": "MANUALE"})
        repo.fetch_pushable_rows.return_value = [row]
        handler = HandlerOrdini(repo)

        handler.run()

        call_kwargs = repo.get_or_create_commessa.call_args.kwargs
        self.assertEqual(call_kwargs["policy_fatturazione"], "MANUALE")

    # Scopo: priorita_operativa default NORMALE (#7).
    def test_process_rows_default_priorita_operativa_normale(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerOrdini(repo)

        handler.run()

        # get_or_create_commessa NON passa priorita_operativa → usa default "NORMALE"
        call_kwargs = repo.get_or_create_commessa.call_args.kwargs
        self.assertNotIn("priorita_operativa", call_kwargs)

    # Scopo: prezzo_da_riallineare default False nell'input (#5).
    def test_process_rows_default_prezzo_da_riallineare_false(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerOrdini(repo)

        handler.run()

        inp = repo.upsert_attivita.call_args[0][0]
        self.assertFalse(inp.prezzo_da_riallineare)

    # Scopo: stato_approvazione default BOZZA, stato_emissione default NON_EMESSA (#10).
    def test_process_rows_default_stato_approvazione_bozza(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerPreventivi(repo)

        handler.run()

        inp = repo.upsert_attivita.call_args[0][0]
        self.assertEqual(inp.stato_approvazione, "BOZZA")
        self.assertEqual(inp.stato_emissione, "NON_EMESSA")

    # Scopo: errore su riga 1 non blocca riga 2 — isolamento per riga.
    def test_process_rows_isolamento_errori_per_riga(self):
        repo = _mock_repo()
        row1 = _make_row(segment_key="FAIL:row1")
        row2 = _make_row(segment_key="OK:row2")
        repo.fetch_pushable_rows.return_value = [row1, row2]
        # La prima get_or_create_commessa fallisce, la seconda riesce.
        repo.get_or_create_commessa.side_effect = [RuntimeError("DB error"), 10]
        handler = HandlerOrdini(repo)

        result = handler.run()

        self.assertEqual(result.created, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("FAIL:row1", result.errors[0])

    # Scopo: HandlerContratti esiste e ha sorgente_codice CONTRATTO (#8).
    def test_handler_contratti_esiste(self):
        repo = _mock_repo()
        handler = HandlerContratti(repo)
        self.assertEqual(handler.sorgente_codice, "CONTRATTO")
        self.assertEqual(handler.name, "HandlerContratti")

    # Scopo: HandlerDdt esiste e ha sorgente_codice DDT_VENDITA (#8).
    def test_handler_ddt_esiste(self):
        repo = _mock_repo()
        handler = HandlerDdt(repo)
        self.assertEqual(handler.sorgente_codice, "DDT_VENDITA")
        self.assertEqual(handler.name, "HandlerDdt")

    # Scopo: HandlerConsumi fan-out 1→N con _expand_rows (#9).
    def test_handler_consumi_expand_rows_fanout(self):
        repo = _mock_repo()
        row = _make_row(
            segment_key="CONS:uid-001",
            articolo_id=None,
            prezzo_snapshot=None,
            meta={"tipo_commessa": "AUTO", "policy_fatturazione": "DA_DOCUMENTO"},
        )
        repo.fetch_pushable_rows.return_value = [row]

        # Patch _fetch_componenti per restituire 2 componenti.
        componenti = [
            ComponenteConsumabile(
                codice="COMP_A",
                articolo_id="art-A",
                quantita=Decimal("5.0"),
                prezzo=Decimal("10.0"),
                uom_id=1,
            ),
            ComponenteConsumabile(
                codice="COMP_B",
                articolo_id="art-B",
                quantita=Decimal("3.0"),
                prezzo=Decimal("8.0"),
                uom_id=2,
            ),
        ]
        handler = HandlerConsumi(repo)
        handler._fetch_componenti = MagicMock(return_value=componenti)

        result = handler.run()

        self.assertEqual(result.created, 2)
        self.assertEqual(repo.upsert_attivita.call_count, 2)
        # Verifica segment_key espanso.
        calls = repo.upsert_attivita.call_args_list
        keys = [c[0][0].segment_key for c in calls]
        self.assertIn("CONS:uid-001:COMP:COMP_A", keys)
        self.assertIn("CONS:uid-001:COMP:COMP_B", keys)
