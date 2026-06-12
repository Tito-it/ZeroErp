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
13) CommesseSourceHandlersTests.test_process_rows_cache_commessa_evita_chiamate_ripetute
14) CommesseSourceHandlersTests.test_process_rows_batch_created_vs_updated

BoM expander (F2-BE-12 / sviluppo-listini-v5 §14.4):
15) BoMComponentExpanderTests.test_articolo_none_pass_through
16) BoMComponentExpanderTests.test_uom_none_pass_through
17) BoMComponentExpanderTests.test_utility_none_pass_through
18) BoMComponentExpanderTests.test_articolo_non_composito_pass_through
19) BoMComponentExpanderTests.test_caso_b_resolver_una_riga_padre_pass_through
20) BoMComponentExpanderTests.test_caso_a_resolver_n_righe_genera_n_pushable_row
21) BoMComponentExpanderTests.test_caso_a_segment_key_suffix_cmp
22) BoMComponentExpanderTests.test_caso_a_quantita_padre_per_coeff_qta_no_rounding
23) BoMComponentExpanderTests.test_caso_a_meta_arricchito_componente_di_e_esposto
24) BoMComponentExpanderTests.test_caso_a_eredita_tipo_doc_fiscale_e_valuta_dal_padre
25) BoMComponentExpanderTests.test_cache_is_composito_un_solo_lookup_per_articolo
26) BoMComponentExpanderTests.test_cache_resolver_un_solo_round_trip_per_chiave
27) BoMComponentExpanderTests.test_handler_default_invoca_bom_expander

BoM integrazione end-to-end (BE-2 / sviluppo-listini-v5 §14.4.3 S14.C-BE-2):
28) BoMHandlerIntegrationTests.test_tutti_5_handler_supportano_bom_expander_iniettato
29) BoMHandlerIntegrationTests.test_handler_consumi_override_prevale_su_bom
30) BoMHandlerIntegrationTests.test_misto_riga_composita_e_riga_semplice_stesso_run
31) BoMHandlerIntegrationTests.test_idempotenza_re_run_segment_key_stabili
32) BoMHandlerIntegrationTests.test_isolamento_errore_resolver_su_singola_riga
33) BoMHandlerIntegrationTests.test_due_righe_stesso_composito_riusano_cache_resolver

Ottimizzazioni post-review (O1 cache modulo + O2 skip qta zero):
34) BoMComponentExpanderTests.test_quantita_padre_zero_pass_through_o2
35) BoMComponentExpanderTests.test_quantita_padre_decimal_zero_pass_through_o2
36) BoMModuleCacheIsCompositoTests.test_default_is_composito_usa_cache_modulo
37) BoMModuleCacheIsCompositoTests.test_invalidate_module_cache_forza_re_query

Path snapshot componenti pre-popolati (refactor 2026-05-11):
38) BoMComponentExpanderTests.test_snapshot_loader_genera_pushable_rows_da_componenti
38b) BoMComponentExpanderTests.test_snapshot_loader_esposto_default_false_se_assente
39) BoMComponentExpanderTests.test_snapshot_loader_vuoto_fallback_resolver
40) BoMComponentExpanderTests.test_snapshot_loader_skip_se_riga_sorgente_id_none
"""

from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.vendite.db.commesse_repository import BatchUpsertResult, CommesseRepository, PushableRow
from apps.vendite.services.commesse_source_handlers import (
    BoMComponentExpander,
    ComponenteConsumabile,
    HandlerConsumi,
    HandlerContratti,
    HandlerDdt,
    HandlerOrdini,
    HandlerPreventivi,
    invalidate_is_composito_module_cache,
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
        "tipo_doc_fiscale_id": 7,
    }
    defaults.update(overrides)
    return PushableRow(**defaults)


def _mock_repo(commessa_id: int = 10, inserted: int = 1, updated: int = 0) -> MagicMock:
    """Crea un mock CommesseRepository con risposte standard."""
    repo = MagicMock(spec=CommesseRepository)
    repo.fetch_pushable_rows.return_value = []
    repo.get_or_create_commessa.return_value = commessa_id
    repo.link_sorgente.return_value = 1
    repo.batch_upsert_attivita.return_value = BatchUpsertResult(
        total_rows=inserted + updated, inserted=inserted, updated=updated, errors=[],
    )
    return repo


class CommesseSourceHandlersTests(TestCase):

    # Scopo: Verifica che HandlerOrdini usi ORDINE_VENDITA (#1), non ORDINE.
    def test_handler_ordini_sorgente_codice_ordine_vendita(self):
        repo = _mock_repo()
        handler = HandlerOrdini(repo)
        self.assertEqual(handler.sorgente_codice, "ORDINE_VENDITA")
        self.assertEqual(handler.name, "HandlerOrdini")

    # Scopo: Happy path — una riga → get_or_create_commessa + link + batch_upsert.
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
        repo.batch_upsert_attivita.assert_called_once()
        inputs = repo.batch_upsert_attivita.call_args[0][0]
        self.assertEqual(len(inputs), 1)

    # Scopo: sorgente_uid valorizzato → propagato a fetch_pushable_rows del repo.
    # Assicura che il push singolo UI-driven filtri davvero a livello DB.
    def test_run_propaga_sorgente_uid_al_fetch_pushable_rows(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerPreventivi(repo)

        handler.run(sorgente_uid=42)

        repo.fetch_pushable_rows.assert_called_once()
        kwargs = repo.fetch_pushable_rows.call_args.kwargs
        self.assertEqual(kwargs["sorgente_uid"], 42)

    # Scopo: sorgente_uid omesso → fetch_pushable_rows riceve None
    # (regressione: comportamento batch invariato).
    def test_run_senza_sorgente_uid_passa_none(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerPreventivi(repo)

        handler.run()

        kwargs = repo.fetch_pushable_rows.call_args.kwargs
        self.assertIsNone(kwargs["sorgente_uid"])

    # Scopo: righe_ids valorizzato (smistamento selettivo) → propagato a
    # fetch_pushable_rows; omesso → None (push completo invariato).
    def test_run_propaga_righe_ids_al_fetch_pushable_rows(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerPreventivi(repo)

        handler.run(sorgente_uid=42, righe_ids=[7, 9])

        kwargs = repo.fetch_pushable_rows.call_args.kwargs
        self.assertEqual(kwargs["righe_ids"], [7, 9])

        repo.fetch_pushable_rows.reset_mock()
        handler.run(sorgente_uid=42)
        kwargs = repo.fetch_pushable_rows.call_args.kwargs
        self.assertIsNone(kwargs["righe_ids"])

    # Scopo: dry_run=True → nessuna chiamata batch_upsert, ma commessa creata e linked.
    def test_process_rows_dry_run_skippa_upsert(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerPreventivi(repo)

        result = handler.run(dry_run=True)

        self.assertEqual(result.created, 1)
        repo.get_or_create_commessa.assert_called_once()
        repo.link_sorgente.assert_called_once()
        repo.batch_upsert_attivita.assert_not_called()

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

        inp = repo.batch_upsert_attivita.call_args[0][0][0]
        self.assertFalse(inp.prezzo_da_riallineare)

    # Scopo: stato_approvazione default BOZZA, stato_emissione default NON_EMESSA (#10).
    def test_process_rows_default_stato_approvazione_bozza(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerPreventivi(repo)

        handler.run()

        inp = repo.batch_upsert_attivita.call_args[0][0][0]
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
        # Batch chiamato con solo la riga riuscita.
        inputs = repo.batch_upsert_attivita.call_args[0][0]
        self.assertEqual(len(inputs), 1)

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
        repo = _mock_repo(inserted=2)
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
        repo.batch_upsert_attivita.assert_called_once()
        # Verifica segment_key espanso nel batch.
        inputs = repo.batch_upsert_attivita.call_args[0][0]
        self.assertEqual(len(inputs), 2)
        keys = [inp.segment_key for inp in inputs]
        self.assertIn("CONS:uid-001:COMP:COMP_A", keys)
        self.assertIn("CONS:uid-001:COMP:COMP_B", keys)

    # Scopo: due righe con stessi parametri commessa → get_or_create_commessa chiamata una sola volta (cache).
    def test_process_rows_cache_commessa_evita_chiamate_ripetute(self):
        repo = _mock_repo(inserted=2)
        # Due righe con stessi parametri commessa ma segment_key diverso.
        row1 = _make_row(segment_key="TEST:uid-001:R:1", sorgente_uid="uid-001")
        row2 = _make_row(segment_key="TEST:uid-002:R:1", sorgente_uid="uid-002")
        repo.fetch_pushable_rows.return_value = [row1, row2]
        handler = HandlerPreventivi(repo)

        result = handler.run()

        self.assertEqual(result.created, 2)
        # Cache: get_or_create_commessa chiamata 1 volta, non 2.
        repo.get_or_create_commessa.assert_called_once()
        # link_sorgente comunque chiamata per ogni riga (sorgente diversa).
        self.assertEqual(repo.link_sorgente.call_count, 2)
        # Batch upsert: 1 sola chiamata con 2 input.
        repo.batch_upsert_attivita.assert_called_once()
        self.assertEqual(len(repo.batch_upsert_attivita.call_args[0][0]), 2)

    # Scopo: Verifica distinzione created vs updated da BatchUpsertResult.
    def test_process_rows_batch_created_vs_updated(self):
        repo = _mock_repo(inserted=1, updated=1)
        row1 = _make_row(segment_key="NEW:row1", sorgente_uid="uid-001")
        row2 = _make_row(segment_key="UPD:row2", sorgente_uid="uid-002")
        repo.fetch_pushable_rows.return_value = [row1, row2]
        handler = HandlerPreventivi(repo)

        result = handler.run()

        self.assertEqual(result.created, 1)
        self.assertEqual(result.updated, 1)


# ============================================================
# BoMComponentExpander — sviluppo-listini-v5 §14.4 (F2-BE-12)
# ============================================================

def _make_composito_row(**overrides) -> PushableRow:
    """Crea un PushableRow con parametri sufficienti per invocare il resolver BoM.

    Differenze vs _make_row():
    - uom_id valorizzato (default 42) — senza uom il resolver non puo' girare
    - articolo_id stringa che il mock is_composito_fn interpreta come composito
    - quantita esplicita (necessaria per calcolo x coeff_qta)
    """
    defaults = {
        "billing_account_id": 100,
        "utility_id": 5,
        "emittente_soggetto_ruolo_id": 200,
        "competenza_dal": date(2026, 6, 1),
        "competenza_al": date(2026, 6, 30),
        "fatturazione_immediata": False,
        "sorgente_tipo_id": 7,
        "sorgente_uid": "uid-preventivo-001",
        "segment_key": "PREV:uid-preventivo-001:R:42",
        "articolo_id": "art-composito-01",
        "istanza_utility_id": 11,
        "data_attivita": date(2026, 6, 15),
        "uom_id": 42,
        "quantita": Decimal("3"),
        "qta_operativa": Decimal("3"),
        "uom_operativa_id": 42,
        "factor_to_base": Decimal("1"),
        "competenza_mese": date(2026, 6, 1),
        "prezzo_snapshot": Decimal("100.00"),
        "prezzo_bloccato": False,
        "pricing_mode": "FIXED",
        "tipo_movimento": "NORMALE",
        "tipo_consumo": "CONGUAGLIO",
        "valuta_id": 9,
        "meta": {"tipo_commessa": "AUTO", "policy_fatturazione": "DA_DOCUMENTO"},
        "tipo_doc_fiscale_id": 77,
    }
    defaults.update(overrides)
    return PushableRow(**defaults)


def _make_snapshot_componente(**overrides) -> dict:
    """Crea un dict stile ritorno `list_componenti_riga` (snapshot
    pricing pre-popolato sul documento sorgente, modello unificato BoM
    2026-05-13). Forma usata dal `componenti_loader` iniettato in
    `BoMComponentExpander` (path unico post cleanup legacy 2026-05-14).
    """
    defaults = {
        "componente_id": "cmp-01",
        "uom_operativa_id": 42,
        "prezzo_unitario": Decimal("10.00"),
        "coeff_qta_snapshot": Decimal("1"),
        "esposto_in_fattura": True,
        "origine_prezzo": "CATEGORIA",
    }
    defaults.update(overrides)
    return defaults


class BoMComponentExpanderTests(TestCase):
    """Test del BoMComponentExpander post cleanup legacy 2026-05-14:
    path unico = snapshot loader (modello unificato). Articolo composito
    senza loader → pass-through difensivo + warning audit.
    """

    # Scopo: articolo_id=None (consumi) -> pass-through.
    def test_articolo_none_pass_through(self):
        expander = BoMComponentExpander(is_composito_fn=MagicMock())
        row = _make_composito_row(articolo_id=None)

        result = expander.expand(row)

        self.assertEqual(result, [row])

    # Scopo: uom_id=None -> pass-through (parametri insufficienti).
    def test_uom_none_pass_through(self):
        expander = BoMComponentExpander(is_composito_fn=MagicMock())
        row = _make_composito_row(uom_id=None)

        result = expander.expand(row)

        self.assertEqual(result, [row])

    # Scopo: utility_id=None -> pass-through.
    def test_utility_none_pass_through(self):
        expander = BoMComponentExpander(is_composito_fn=MagicMock())
        row = _make_composito_row(utility_id=None)

        result = expander.expand(row)

        self.assertEqual(result, [row])

    # Scopo: is_composito=False -> pass-through, snapshot loader mai invocato.
    def test_articolo_non_composito_pass_through(self):
        is_composito = MagicMock(return_value=False)
        snapshot_loader = MagicMock()
        expander = BoMComponentExpander(
            is_composito_fn=is_composito,
            componenti_loader=snapshot_loader,
        )
        row = _make_composito_row()

        result = expander.expand(row)

        self.assertEqual(result, [row])
        is_composito.assert_called_once_with(row.articolo_id)
        snapshot_loader.assert_not_called()

    # ── Path snapshot componenti (path unico modello unificato) ──

    # Scopo: con componenti_loader iniettato + riga_sorgente_id valorizzato +
    # snapshot non vuoto, l'expander genera PushableRow dai componenti
    # pre-popolati. Modello unificato 2026-05-13: `esposto_in_fattura`
    # arriva dal snapshot (proiezione JOIN su articoli_componenti),
    # propagato nel meta. Tutti i figli passano in commessa.
    def test_snapshot_loader_genera_pushable_rows_da_componenti(self):
        snapshot_loader = MagicMock(return_value=[
            {
                "componente_id": "cmp-01",
                "uom_operativa_id": 42,
                "prezzo_unitario": Decimal("200.00"),
                "coeff_qta_snapshot": Decimal("1"),
                "origine_prezzo": "LISTINO_BUNDLE",
                "esposto_in_fattura": True,
            },
            {
                "componente_id": "cmp-02",
                "uom_operativa_id": 43,
                "prezzo_unitario": Decimal("75.00"),
                "coeff_qta_snapshot": Decimal("4"),
                "origine_prezzo": "MANUALE",
                "esposto_in_fattura": False,
            },
        ])
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
        )
        row = _make_composito_row(riga_sorgente_id=42)

        result = expander.expand(row)

        self.assertEqual(len(result), 2)
        snapshot_loader.assert_called_once_with(42)
        self.assertEqual([r.articolo_id for r in result], ["cmp-01", "cmp-02"])
        self.assertEqual(
            [r.prezzo_snapshot for r in result],
            [Decimal("200.00"), Decimal("75.00")],
        )
        # qta padre 3 × coeff 1 / 4
        self.assertEqual(result[0].quantita, Decimal("3"))
        self.assertEqual(result[1].quantita, Decimal("12"))
        # DEC-2 segment_key suffix '#CMP:{componente_id}'.
        self.assertIn("#CMP:cmp-01", result[0].segment_key)
        self.assertIn("#CMP:cmp-02", result[1].segment_key)
        # DEC-6 meta arricchito.
        self.assertEqual(result[0].meta["esposto_in_fattura"], True)
        self.assertEqual(result[0].meta["componente_di"], str(row.articolo_id))
        self.assertEqual(result[1].meta["esposto_in_fattura"], False)
        # origine_prezzo propagato in meta per audit downstream
        self.assertEqual(result[0].meta["origine_prezzo"], "LISTINO_BUNDLE")
        self.assertEqual(result[1].meta["origine_prezzo"], "MANUALE")
        # esposto_in_fattura letto dal snapshot (modello unificato): True
        # per il primo, False per il secondo. Era hardcoded True nel
        # vecchio modello (CASO A: solo esposti popolati in init).
        self.assertEqual(result[0].meta["esposto_in_fattura"], True)
        self.assertEqual(result[1].meta["esposto_in_fattura"], False)

    # Scopo: snapshot privo del flag `esposto_in_fattura` → default False.
    # Defense-in-depth contro caller che non popolano il campo (es. test
    # legacy, snapshot pre-modello-unificato non aggiornati).
    def test_snapshot_loader_esposto_default_false_se_assente(self):
        snapshot_loader = MagicMock(return_value=[
            {
                "componente_id": "cmp-01",
                "uom_operativa_id": 42,
                "prezzo_unitario": Decimal("100.00"),
                "coeff_qta_snapshot": Decimal("1"),
                "origine_prezzo": "MANUALE",
                # Nessun esposto_in_fattura
            },
        ])
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
        )
        row = _make_composito_row(riga_sorgente_id=42)

        result = expander.expand(row)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].meta["esposto_in_fattura"], False)

    # Scopo: composito senza snapshot loader → pass-through difensivo +
    # warning audit. Post cleanup legacy 2026-05-14 (no piu' fallback al
    # resolver legacy). Atteso solo in dev o per handler senza loader.
    def test_composito_senza_snapshot_loader_pass_through(self):
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            # niente componenti_loader
        )
        row = _make_composito_row(articolo_id="art-comp", riga_sorgente_id=42)

        with self.assertLogs(
            "apps.vendite.services.commesse_source_handlers", level="WARNING",
        ) as logs:
            result = expander.expand(row)

        self.assertEqual(result, [row])
        self.assertTrue(
            any("pass-through padre" in m for m in logs.output),
            f"Atteso warning pass-through: {logs.output}",
        )

    # Scopo: composito con snapshot vuoto → pass-through difensivo +
    # warning audit (atteso 0 in produzione, init popola SEMPRE tutti i
    # figli col modello unificato).
    def test_composito_snapshot_vuoto_pass_through(self):
        snapshot_loader = MagicMock(return_value=[])
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
        )
        row = _make_composito_row(articolo_id="art-comp", riga_sorgente_id=42)

        with self.assertLogs(
            "apps.vendite.services.commesse_source_handlers", level="WARNING",
        ) as logs:
            result = expander.expand(row)

        self.assertEqual(result, [row])
        snapshot_loader.assert_called_once_with(42)
        self.assertTrue(
            any("pass-through padre" in m for m in logs.output),
        )

    # Scopo: composito con riga_sorgente_id=None → pass-through difensivo.
    # Caso CONSUMI o sorgenti senza granularita' riga.
    def test_composito_riga_sorgente_id_none_pass_through(self):
        snapshot_loader = MagicMock()
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
        )
        row = _make_composito_row(riga_sorgente_id=None)

        with self.assertLogs(
            "apps.vendite.services.commesse_source_handlers", level="WARNING",
        ):
            result = expander.expand(row)

        self.assertEqual(result, [row])
        snapshot_loader.assert_not_called()

    # Scopo: DEC-3 — quantita componente = padre × coeff_qta_snapshot,
    # senza rounding. Test piena precisione con coeff_qta non intero.
    def test_snapshot_quantita_padre_per_coeff_qta_no_rounding(self):
        snapshot_loader = MagicMock(return_value=[
            _make_snapshot_componente(
                componente_id="cmp-01", coeff_qta_snapshot=Decimal("2.5"),
            ),
            _make_snapshot_componente(
                componente_id="cmp-02", coeff_qta_snapshot=Decimal("0.333"),
            ),
        ])
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
        )
        row = _make_composito_row(
            quantita=Decimal("3.7"), riga_sorgente_id=42,
        )

        result = expander.expand(row)

        # 3.7 * 2.5 = 9.25 (piena, no rounding)
        self.assertEqual(result[0].quantita, Decimal("9.25"))
        # 3.7 * 0.333 = 1.2321 (piena, no rounding)
        self.assertEqual(result[1].quantita, Decimal("1.2321"))

    # Scopo: DEC-5 — campi di contesto padre (tipo_doc_fiscale_id, valuta,
    # BA, utility, sorgente_uid, emittente, competenza, fatturazione_immediata)
    # ereditati dai componenti, non sovrascritti.
    def test_snapshot_eredita_tipo_doc_fiscale_e_valuta_dal_padre(self):
        snapshot_loader = MagicMock(return_value=[_make_snapshot_componente()])
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
        )
        row = _make_composito_row(
            tipo_doc_fiscale_id=999,
            valuta_id=555,
            billing_account_id=111,
            utility_id=222,
            sorgente_uid="SRC-abc",
            emittente_soggetto_ruolo_id=333,
            competenza_mese=date(2026, 9, 1),
            fatturazione_immediata=True,
            riga_sorgente_id=42,
        )

        result = expander.expand(row)

        componente = result[0]
        self.assertEqual(componente.tipo_doc_fiscale_id, 999)
        self.assertEqual(componente.valuta_id, 555)
        self.assertEqual(componente.billing_account_id, 111)
        self.assertEqual(componente.utility_id, 222)
        self.assertEqual(componente.sorgente_uid, "SRC-abc")
        self.assertEqual(componente.emittente_soggetto_ruolo_id, 333)
        self.assertEqual(componente.competenza_mese, date(2026, 9, 1))
        self.assertTrue(componente.fatturazione_immediata)

    # Scopo: DEC-6 — meta componente arricchito con `esposto_in_fattura`,
    # `componente_di` (audit inverso), `coeff_qta`, `origine_prezzo`.
    # Preserva meta padre.
    def test_snapshot_meta_arricchito(self):
        snapshot_loader = MagicMock(return_value=[
            _make_snapshot_componente(
                componente_id="cmp-01",
                esposto_in_fattura=True,
                coeff_qta_snapshot=Decimal("2"),
                origine_prezzo="MANUALE",
            ),
        ])
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
        )
        row = _make_composito_row(
            articolo_id="art-parent",
            meta={"tipo_commessa": "AUTO", "extra_padre": "x"},
            riga_sorgente_id=42,
        )

        result = expander.expand(row)

        self.assertEqual(result[0].meta["esposto_in_fattura"], True)
        self.assertEqual(result[0].meta["componente_di"], "art-parent")
        self.assertEqual(result[0].meta["coeff_qta"], "2")
        self.assertEqual(result[0].meta["origine_prezzo"], "MANUALE")
        # Preservato dal padre:
        self.assertEqual(result[0].meta["tipo_commessa"], "AUTO")
        self.assertEqual(result[0].meta["extra_padre"], "x")

    # Scopo: cache is_composito — lo stesso articolo passato N volte deve
    # provocare UN SOLO lookup via is_composito_fn.
    def test_cache_is_composito_un_solo_lookup_per_articolo(self):
        is_composito = MagicMock(return_value=False)
        expander = BoMComponentExpander(is_composito_fn=is_composito)
        row = _make_composito_row(articolo_id="ART-X")

        expander.expand(row)
        expander.expand(row)
        expander.expand(row)

        is_composito.assert_called_once_with("ART-X")

    # Scopo: O2 — quantita_padre None -> pass-through, no lookup composito.
    def test_quantita_padre_zero_pass_through_o2(self):
        is_composito = MagicMock()
        expander = BoMComponentExpander(is_composito_fn=is_composito)
        row = _make_composito_row(quantita=None)

        result = expander.expand(row)

        self.assertEqual(result, [row])
        is_composito.assert_not_called()

    # Scopo: O2 — quantita_padre Decimal('0') -> pass-through.
    def test_quantita_padre_decimal_zero_pass_through_o2(self):
        is_composito = MagicMock()
        expander = BoMComponentExpander(is_composito_fn=is_composito)
        row = _make_composito_row(quantita=Decimal("0"))

        result = expander.expand(row)

        self.assertEqual(result, [row])
        is_composito.assert_not_called()

    # Scopo: integrazione — HandlerPreventivi con BoMComponentExpander
    # iniettato produce N righe in commesse_attivita via snapshot loader.
    # Verifica end-to-end: fetch -> expand -> batch_upsert con N input.
    def test_handler_default_invoca_bom_expander(self):
        snapshot_loader = MagicMock(return_value=[
            _make_snapshot_componente(
                componente_id="cmp-A",
                coeff_qta_snapshot=Decimal("2"),
                prezzo_unitario=Decimal("7"),
            ),
            _make_snapshot_componente(
                componente_id="cmp-B",
                coeff_qta_snapshot=Decimal("3"),
                prezzo_unitario=Decimal("4"),
            ),
        ])
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
        )
        repo = _mock_repo(inserted=2)
        repo.fetch_pushable_rows.return_value = [
            _make_composito_row(quantita=Decimal("10"), riga_sorgente_id=42),
        ]
        handler = HandlerPreventivi(repo, bom_expander=expander)

        result = handler.run()

        self.assertEqual(result.created, 2)
        inputs = repo.batch_upsert_attivita.call_args[0][0]
        self.assertEqual(len(inputs), 2)
        # segment_key differenziati con suffix componente.
        keys = sorted(inp.segment_key for inp in inputs)
        self.assertTrue(all("#CMP:" in k for k in keys))
        # quantita moltiplicate dal coeff_qta (10*2=20, 10*3=30).
        quantita = sorted(inp.quantita for inp in inputs)
        self.assertEqual(quantita, [Decimal("20"), Decimal("30")])


# ============================================================
# BoM integrazione end-to-end — BE-2 (sviluppo-listini-v5 §14.4.3)
# ============================================================

def _make_bom_expander(componenti: list[dict] | None = None, is_composito: bool = True) -> BoMComponentExpander:
    """Helper per creare un BoMComponentExpander pronto-all'uso nei test
    (path snapshot, modello unificato post cleanup 2026-05-14)."""
    snapshot = componenti or [
        _make_snapshot_componente(
            componente_id="cmp-X", coeff_qta_snapshot=Decimal("2"),
        ),
        _make_snapshot_componente(
            componente_id="cmp-Y", coeff_qta_snapshot=Decimal("3"),
        ),
    ]
    return BoMComponentExpander(
        is_composito_fn=MagicMock(return_value=is_composito),
        componenti_loader=MagicMock(return_value=snapshot),
    )


class BoMHandlerIntegrationTests(TestCase):

    # Scopo: regression sui 5 handler — tutti devono funzionare con
    #        BoMComponentExpander iniettato e produrre N righe per composito.
    #        Garantisce che la signature comune (repo, bom_expander) sia
    #        rispettata e che il pattern di espansione si applichi
    #        uniformemente. HandlerConsumi escluso: ha override _expand_rows.
    def test_tutti_5_handler_supportano_bom_expander_iniettato(self):
        for handler_cls in [HandlerPreventivi, HandlerOrdini, HandlerContratti, HandlerDdt]:
            with self.subTest(handler=handler_cls.__name__):
                expander = _make_bom_expander()
                repo = _mock_repo(inserted=2)
                # `riga_sorgente_id` valorizzato: snapshot loader viene
                # invocato e l'expander espande 2 componenti (vedi
                # `_make_bom_expander` default).
                repo.fetch_pushable_rows.return_value = [
                    _make_composito_row(riga_sorgente_id=1),
                ]
                handler = handler_cls(repo, bom_expander=expander)

                result = handler.run()

                self.assertEqual(result.created, 2, f"{handler_cls.__name__} deve produrre 2 righe componente")
                self.assertEqual(result.errors, [])
                inputs = repo.batch_upsert_attivita.call_args[0][0]
                self.assertEqual(len(inputs), 2)

    # Scopo: HandlerConsumi ha _expand_rows override (fan-out consumi).
    # L'override prevale sulla logica BoM: il bom_expander iniettato NON
    # deve essere mai invocato per Consumi.
    def test_handler_consumi_override_prevale_su_bom(self):
        snapshot_loader = MagicMock()
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
        )
        repo = _mock_repo(inserted=2)
        # Riga consumo con articolo_id=None (default per consumi pre fan-out).
        repo.fetch_pushable_rows.return_value = [
            _make_row(articolo_id=None, prezzo_snapshot=None, segment_key="CONS:uid-1")
        ]
        handler = HandlerConsumi(repo, bom_expander=expander)
        # Stub fan-out consumi: 2 componenti.
        handler._fetch_componenti = MagicMock(return_value=[
            ComponenteConsumabile(codice="A", articolo_id="art-A", quantita=Decimal("1"), prezzo=Decimal("5"), uom_id=1),
            ComponenteConsumabile(codice="B", articolo_id="art-B", quantita=Decimal("2"), prezzo=Decimal("3"), uom_id=2),
        ])

        result = handler.run()

        self.assertEqual(result.created, 2)
        # BoM non invocata: HandlerConsumi.expand_rows ha sostituito il default.
        snapshot_loader.assert_not_called()
        # segment_key con suffix consumi (`:COMP:`), non BoM (`#CMP:`).
        inputs = repo.batch_upsert_attivita.call_args[0][0]
        keys = sorted(inp.segment_key for inp in inputs)
        self.assertTrue(all(":COMP:" in k for k in keys))
        self.assertFalse(any("#CMP:" in k for k in keys))

    # Scopo: scenario realistico di un preventivo con 1 articolo composito
    # (2 componenti via snapshot) + 1 articolo semplice → batch finale ha 3
    # input (2 componenti + 1 riga semplice pass-through). Verifica che
    # l'espansione si applichi solo dove serve.
    def test_misto_riga_composita_e_riga_semplice_stesso_run(self):
        snapshot_loader = MagicMock(return_value=[
            _make_snapshot_componente(componente_id="cmp-A", coeff_qta_snapshot=Decimal("2")),
            _make_snapshot_componente(componente_id="cmp-B", coeff_qta_snapshot=Decimal("1")),
        ])
        # is_composito_fn ritorna True solo per "art-composito", False per "art-semplice".
        is_composito = MagicMock(side_effect=lambda art_id: art_id == "art-composito")
        expander = BoMComponentExpander(
            is_composito_fn=is_composito,
            componenti_loader=snapshot_loader,
        )
        repo = _mock_repo(inserted=3)
        repo.fetch_pushable_rows.return_value = [
            _make_composito_row(
                articolo_id="art-composito",
                segment_key="PREV:uid-1:R:1",
                sorgente_uid="uid-1",
                riga_sorgente_id=11,
            ),
            _make_composito_row(
                articolo_id="art-semplice",
                segment_key="PREV:uid-1:R:2",
                sorgente_uid="uid-1",
                riga_sorgente_id=12,
            ),
        ]
        handler = HandlerPreventivi(repo, bom_expander=expander)

        result = handler.run()

        self.assertEqual(result.created, 3)
        inputs = repo.batch_upsert_attivita.call_args[0][0]
        self.assertEqual(len(inputs), 3)
        keys = sorted(inp.segment_key for inp in inputs)
        # Verifica: 2 componenti BoM + 1 riga semplice pass-through.
        self.assertEqual(keys, [
            "PREV:uid-1:R:1#CMP:cmp-A",
            "PREV:uid-1:R:1#CMP:cmp-B",
            "PREV:uid-1:R:2",
        ])

    # Scopo: idempotenza pipeline. Re-run dell'handler con stesso snapshot
    # e stessa riga sorgente deve produrre identiche segment_key (input per
    # upsert idempotente).
    def test_idempotenza_re_run_segment_key_stabili(self):
        # Run 1
        expander1 = _make_bom_expander([
            _make_snapshot_componente(componente_id="c1"),
            _make_snapshot_componente(componente_id="c2"),
        ])
        repo1 = _mock_repo(inserted=2)
        repo1.fetch_pushable_rows.return_value = [
            _make_composito_row(segment_key="PREV:uid-X:R:7", riga_sorgente_id=7),
        ]
        handler1 = HandlerPreventivi(repo1, bom_expander=expander1)
        handler1.run()
        keys_run1 = sorted(inp.segment_key for inp in repo1.batch_upsert_attivita.call_args[0][0])

        # Run 2 — stessa sorgente, stesso snapshot, expander nuovo.
        expander2 = _make_bom_expander([
            _make_snapshot_componente(componente_id="c1"),
            _make_snapshot_componente(componente_id="c2"),
        ])
        repo2 = _mock_repo(updated=2)
        repo2.fetch_pushable_rows.return_value = [
            _make_composito_row(segment_key="PREV:uid-X:R:7", riga_sorgente_id=7),
        ]
        handler2 = HandlerPreventivi(repo2, bom_expander=expander2)
        handler2.run()
        keys_run2 = sorted(inp.segment_key for inp in repo2.batch_upsert_attivita.call_args[0][0])

        self.assertEqual(keys_run1, keys_run2,
            "Le segment_key del re-run devono essere identiche per idempotenza upsert")


# ============================================================
# Cache modulo-level is_composito — O1 (post-review Sprint C)
# ============================================================


class BoMModuleCacheIsCompositoTests(TestCase):
    """Verifica della cache L2 modulo-level su _default_is_composito.

    La cache L2 e' cross-istanza: due BoMComponentExpander differenti che
    interrogano lo stesso articolo eseguono UNA SOLA query DB nel TTL.
    Setup: invalida la cache prima di ogni test per isolamento.
    """

    def setUp(self):
        invalidate_is_composito_module_cache()
        self.addCleanup(invalidate_is_composito_module_cache)

    # Scopo: O1 — due istanze di BoMComponentExpander interrogano lo stesso
    #        articolo (stesso processo) -> 1 sola query DB grazie alla cache
    #        modulo-level. Mock di connection.cursor per contare le call.
    def test_default_is_composito_usa_cache_modulo(self):
        cursor_mock = MagicMock()
        cursor_mock.fetchone.return_value = (True,)
        cursor_ctx = MagicMock()
        cursor_ctx.__enter__ = MagicMock(return_value=cursor_mock)
        cursor_ctx.__exit__ = MagicMock(return_value=False)

        with patch(
            "apps.vendite.services.commesse_source_handlers.connection.cursor",
            return_value=cursor_ctx,
        ) as mock_cursor:
            # Prima istanza: miss -> query DB
            BoMComponentExpander._default_is_composito("art-cached")
            self.assertEqual(mock_cursor.call_count, 1)

            # Seconda istanza (cross-istanza): hit -> NO query
            BoMComponentExpander._default_is_composito("art-cached")
            self.assertEqual(mock_cursor.call_count, 1, "cache modulo deve evitare seconda query")

            # Articolo diverso: miss -> nuova query
            cursor_mock.fetchone.return_value = (False,)
            BoMComponentExpander._default_is_composito("art-altro")
            self.assertEqual(mock_cursor.call_count, 2)

    # Scopo: O1 — invalidate_is_composito_module_cache() forza re-query.
    #        Pattern: chiamata post refactor catalogo / switch tenant.
    def test_invalidate_module_cache_forza_re_query(self):
        cursor_mock = MagicMock()
        cursor_mock.fetchone.return_value = (True,)
        cursor_ctx = MagicMock()
        cursor_ctx.__enter__ = MagicMock(return_value=cursor_mock)
        cursor_ctx.__exit__ = MagicMock(return_value=False)

        with patch(
            "apps.vendite.services.commesse_source_handlers.connection.cursor",
            return_value=cursor_ctx,
        ) as mock_cursor:
            BoMComponentExpander._default_is_composito("art-X")
            BoMComponentExpander._default_is_composito("art-X")
            self.assertEqual(mock_cursor.call_count, 1)

            invalidate_is_composito_module_cache()

            BoMComponentExpander._default_is_composito("art-X")
            self.assertEqual(mock_cursor.call_count, 2,
                "post invalidate la query DB deve essere ri-eseguita")
