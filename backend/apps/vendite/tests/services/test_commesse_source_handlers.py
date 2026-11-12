# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari handler sorgente commesse.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CommesseSourceHandlersTests.test_handler_ordini_sorgente_codice_ordine_vendita
2) CommesseSourceHandlersTests.test_process_rows_crea_commessa_e_upsert
2b) CommesseSourceHandlersTests.test_process_rows_propaga_condizioni_pagamento_alla_commessa
2c) CommesseSourceHandlersTests.test_cache_commessa_separa_per_termine_di_pagamento
2d) CommesseSourceHandlersTests.test_cache_commessa_riusa_a_parita_di_termine
3) CommesseSourceHandlersTests.test_process_rows_dry_run_skippa_upsert
4) CommesseSourceHandlersTests.test_process_rows_extract_tipo_commessa_da_meta
5) CommesseSourceHandlersTests.test_process_rows_extract_policy_fatturazione_da_meta
6) CommesseSourceHandlersTests.test_process_rows_default_priorita_operativa_normale
7) CommesseSourceHandlersTests.test_process_rows_default_prezzo_da_riallineare_false
8) CommesseSourceHandlersTests.test_process_rows_default_stato_approvazione_bozza
8b) CommesseSourceHandlersTests.test_process_rows_onere_porta_la_causale
9) CommesseSourceHandlersTests.test_process_rows_isolamento_errori_per_riga
10) CommesseSourceHandlersTests.test_handler_contratti_esiste
10b) CommesseSourceHandlersTests.test_contratto_apre_la_commessa_senza_periodo
10c) CommesseSourceHandlersTests.test_sorgente_a_evento_tiene_il_periodo_nella_chiave
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
38b) BoMComponentExpanderTests.test_snapshot_loader_esposizione_default_nascosto_se_assente
39) BoMComponentExpanderTests.test_snapshot_loader_vuoto_fallback_resolver
40) BoMComponentExpanderTests.test_snapshot_loader_skip_se_riga_sorgente_id_none

Snapshot pricing v5 al push (F2-BE-12 / analisi-commesse §4.3 #2):
41) PricingAuditSnapshotTests.test_audit_snapshot_popolato_da_resolver
42) PricingAuditSnapshotTests.test_prezzo_snapshot_negoziato_non_sovrascritto
43) PricingAuditSnapshotTests.test_audit_best_effort_resolver_errore_non_blocca
44) PricingAuditSnapshotTests.test_origine_prezzo_da_meta_prevale_su_resolver
45) PricingAuditSnapshotTests.test_audit_skip_se_uom_none_nessuna_chiamata_resolver
46) PricingAuditSnapshotTests.test_audit_cache_dedup_stesso_contesto_un_solo_resolve

Fan-out compositi modello unico per sorgenti ≠ preventivo (analisi-commesse §4.3 #3):
47) CompositiFanOutWiringTests.test_factory_preventivi_ritorna_repo_componenti
48) CompositiFanOutWiringTests.test_factory_ordini_ritorna_repo_componenti
49) CompositiFanOutWiringTests.test_factory_contratti_ritorna_repo_componenti
50) CompositiFanOutWiringTests.test_factory_ddt_ritorna_repo_componenti
51) CompositiFanOutWiringTests.test_default_expander_ha_componenti_loader_per_documento
52) CompositiFanOutWiringTests.test_consumi_nessuna_factory_componenti
53) CompositiFanOutWiringTests.test_ordini_default_fanout_compositi_da_componenti
54) PricingAuditSnapshotTests.test_audit_origine_fuori_check_diventa_null

Hook fasi di lavorazione (scaffolding §6):
55) PreCommessaHookTests.test_hook_default_identity
56) PreCommessaHookTests.test_hook_override_applicato_al_push

I componenti del kit dal LISTINO (D-2 (c), brief-db-contratto-righe-periodiche-in-commessa §7.2):
57) BoMComponentExpanderTests.test_kit_senza_riga_legge_i_componenti_dal_listino
58) BoMComponentExpanderTests.test_kit_aderito_snapshot_vuoto_legge_il_listino
59) BoMComponentExpanderTests.test_componenti_negoziati_il_listino_non_si_legge
60) CompositiFanOutWiringTests.test_solo_il_contratto_legge_i_kit_dal_listino
61) CompositiFanOutWiringTests.test_kit_dal_listino_una_lettura_per_pezzo
"""

import dataclasses
from contextlib import nullcontext
from datetime import date
from decimal import Decimal
from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.vendite.db.commesse_repository import (
    BatchUpsertResult, CommesseRepository, ErroreBatchAttivita, PushableRow,
)
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
    defaults: dict[str, Any] = {
        "billing_account_id": 1,
        "utility_id": 2,
        "emittente_soggetto_ruolo_id": 3,
        "competenza_dal": date(2026, 6, 1),
        "competenza_al": date(2026, 6, 30),
        "fatturazione_immediata": False,
        "sorgente_tipo_id": 5,
        "sorgente_chiave": "uid-001",
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

    # Scopo: Happy path — una riga → get_or_create_commessa + batch_upsert. Il
    #        link della sorgente NON lo scrive il backend: lo scrive la madre DB
    #        delle righe (D-13), quindi il repository non ha piu' il metodo.
    def test_process_rows_crea_commessa_e_upsert(self):
        repo = _mock_repo()
        row = _make_row()
        repo.fetch_pushable_rows.return_value = [row]
        handler = HandlerPreventivi(repo)

        result = handler.run()

        self.assertEqual(result.created, 1)
        self.assertEqual(result.errors, [])
        repo.get_or_create_commessa.assert_called_once()
        self.assertFalse(hasattr(CommesseRepository, "link_sorgente"))
        repo.batch_upsert_attivita.assert_called_once()
        inputs = repo.batch_upsert_attivita.call_args[0][0]
        self.assertEqual(len(inputs), 1)
        # ⛔ L'emittente NON si ri-passa al database: dal 2026-08-26 si deriva
        #    dal billing account e la funzione DB non ha piu' il parametro
        #    (`20260826-52`). Qui il repository e' un mock e accetterebbe
        #    qualunque chiave: senza questa riga la reintroduzione passerebbe
        #    i test e morirebbe al primo push vero, con «funzione inesistente».
        self.assertNotIn(
            "emittente_soggetto_ruolo_id",
            repo.get_or_create_commessa.call_args.kwargs,
        )

    # Scopo: PROPAGAZIONE — il termine del documento sorgente arriva alla
    #        commessa. E' la meta' visibile del difetto del 2026-08-03:
    #        ORD0004786 dichiarava 2 rate a 30/60, la fattura 2263 e' uscita
    #        con 1 rata a 30 gg perche' la commessa nasceva senza termine e la
    #        catena ripiegava sul cliente.
    def test_process_rows_propaga_condizioni_pagamento_alla_commessa(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [
            _make_row(termine_pagamento_id=3, modalita_pagamento_id=5)
        ]
        HandlerPreventivi(repo).run()

        kwargs = repo.get_or_create_commessa.call_args.kwargs
        self.assertEqual(kwargs["termine_pagamento_id"], 3)
        self.assertEqual(kwargs["modalita_pagamento_id"], 5)

    # Scopo: ⚠️ IL TEST CHE CONTA — le condizioni sono DIMENSIONI DI CHIAVE
    #        (D-R), quindi due righe identiche in tutto tranne il termine
    #        devono aprire DUE commesse. Se la `cache_key` locale non le
    #        include, la seconda riga riusa l'id della prima e ne eredita il
    #        termine: un difetto piu' insidioso di quello che si e' appena
    #        tolto, perche' la commessa esiste, e' popolata e sembra giusta.
    def test_cache_commessa_separa_per_termine_di_pagamento(self):
        repo = _mock_repo()
        repo.get_or_create_commessa.side_effect = [10, 11]
        repo.fetch_pushable_rows.return_value = [
            _make_row(segment_key="K:1", sorgente_chiave="uid-1", termine_pagamento_id=3),
            _make_row(segment_key="K:2", sorgente_chiave="uid-2", termine_pagamento_id=7),
        ]
        HandlerPreventivi(repo).run()

        self.assertEqual(repo.get_or_create_commessa.call_count, 2)
        termini = [c.kwargs["termine_pagamento_id"]
                   for c in repo.get_or_create_commessa.call_args_list]
        self.assertEqual(termini, [3, 7])

    # Scopo: simmetrico — a parita' di termine la cache continua a fare il suo
    #        mestiere: due righe con lo STESSO termine restano UNA commessa.
    #        Senza questo, il test sopra si potrebbe soddisfare disattivando
    #        la cache, che e' un altro modo di sbagliare.
    def test_cache_commessa_riusa_a_parita_di_termine(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [
            _make_row(segment_key="K:1", sorgente_chiave="uid-1", termine_pagamento_id=3),
            _make_row(segment_key="K:2", sorgente_chiave="uid-2", termine_pagamento_id=3),
        ]
        HandlerPreventivi(repo).run()

        self.assertEqual(repo.get_or_create_commessa.call_count, 1)

    # Scopo: regressione review 2026-07-23 — le segment_key FALLITE nel batch
    #        vanno ESCLUSE dalla risoluzione id post-upsert. Per gli UPDATE
    #        falliti la riga preesistente esiste ancora a DB: senza il filtro
    #        il ponte la approverebbe (BOZZA→APPROVATA) coi valori STALI
    #        mentre il report la segna in errore.
    def test_process_rows_esclude_segment_key_fallite_dalla_risoluzione_id(self):
        repo = _mock_repo()
        riga_ok = _make_row(segment_key="TEST:uid-001:R:1")
        riga_ko = _make_row(sorgente_chiave="uid-002", segment_key="TEST:uid-002:R:1")
        repo.fetch_pushable_rows.return_value = [riga_ok, riga_ko]
        repo.batch_upsert_attivita.return_value = BatchUpsertResult(
            total_rows=2, inserted=1, updated=0,
            errors=[ErroreBatchAttivita(
                index=1, segment_key="TEST:uid-002:R:1", error="guard KO",
                sqlstate="P0001", codice="E_UOM_MISSING", campo="uom_operativa_id",
            )],
        )
        handler = HandlerPreventivi(repo)

        result = handler.run()

        # Solo la coppia riuscita arriva alla risoluzione id.
        coppie = repo.list_attivita_ids_by_segments.call_args[0][0]
        self.assertEqual([c[1] for c in coppie], ["TEST:uid-001:R:1"])
        # L'errore resta visibile nel report.
        self.assertEqual(result.skipped, 1)
        # Il report porta il codice di dominio del rifiuto (BE30).
        self.assertIn(
            "Errore batch segment_key=TEST:uid-002:R:1 [E_UOM_MISSING]: guard KO", result.errors,
        )

    # Scopo: sorgente_id valorizzato → propagato a fetch_pushable_rows del repo.
    # Assicura che il push singolo UI-driven filtri davvero a livello DB.
    def test_run_propaga_sorgente_id_al_fetch_pushable_rows(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerPreventivi(repo)

        handler.run(sorgente_id=42)

        repo.fetch_pushable_rows.assert_called_once()
        kwargs = repo.fetch_pushable_rows.call_args.kwargs
        self.assertEqual(kwargs["sorgente_id"], 42)

    # Scopo: sorgente_id omesso → fetch_pushable_rows riceve None
    # (regressione: comportamento batch invariato).
    def test_run_senza_sorgente_id_passa_none(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerPreventivi(repo)

        handler.run()

        kwargs = repo.fetch_pushable_rows.call_args.kwargs
        self.assertIsNone(kwargs["sorgente_id"])

    # Scopo: righe_ids valorizzato (smistamento selettivo) → propagato a
    # fetch_pushable_rows; omesso → None (push completo invariato).
    def test_run_propaga_righe_ids_al_fetch_pushable_rows(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerPreventivi(repo)

        handler.run(sorgente_id=42, righe_ids=[7, 9])

        kwargs = repo.fetch_pushable_rows.call_args.kwargs
        self.assertEqual(kwargs["righe_ids"], [7, 9])

        repo.fetch_pushable_rows.reset_mock()
        handler.run(sorgente_id=42)
        kwargs = repo.fetch_pushable_rows.call_args.kwargs
        self.assertIsNone(kwargs["righe_ids"])

    # Scopo: dry_run=True → nessuna chiamata batch_upsert, ma commessa risolta.
    def test_process_rows_dry_run_skippa_upsert(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row()]
        handler = HandlerPreventivi(repo)

        result = handler.run(dry_run=True)

        self.assertEqual(result.created, 1)
        repo.get_or_create_commessa.assert_called_once()
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

    # Scopo: la riga ONERE di un ordine porta la sua causale fino all'input del
    #        batch (brief-db-addebito-trasporto-ordine §9.3): la madre vuole
    #        ONERE <=> causale, e senza la riga e' rifiutata.
    def test_process_rows_onere_porta_la_causale(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [
            _make_row(tipo_movimento="ONERE", causale_onere_id=6),
        ]
        handler = HandlerOrdini(repo)

        handler.run()

        inp = repo.batch_upsert_attivita.call_args[0][0][0]
        self.assertEqual(inp.tipo_movimento, "ONERE")
        self.assertEqual(inp.causale_onere_id, 6)

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

    # Scopo: G-6 (brief-db-contratto-righe-periodiche-in-commessa) — due pezzi
    #        di canone dello stesso contratto, con periodi diversi, vanno nella
    #        STESSA commessa, aperta senza periodo. Col periodo nella chiave il
    #        secondo pezzo aprirebbe un'altra commessa, e la madre DB lo
    #        rifiuterebbe (`E_COMMESSA_SORGENTE_ALTRA_COMMESSA`, D-12).
    def test_contratto_apre_la_commessa_senza_periodo(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [
            _make_row(segment_key="CONTRATTO:uid-1:R:1:M:2026-06", sorgente_chiave="uid-1",
                      competenza_dal=date(2026, 6, 1), competenza_al=date(2026, 6, 30)),
            _make_row(segment_key="CONTRATTO:uid-1:R:1:M:2026-07", sorgente_chiave="uid-1",
                      competenza_dal=date(2026, 7, 1), competenza_al=date(2026, 7, 31)),
        ]
        HandlerContratti(repo).run()

        repo.get_or_create_commessa.assert_called_once()
        kwargs = repo.get_or_create_commessa.call_args.kwargs
        self.assertIsNone(kwargs["competenza_dal"])
        self.assertIsNone(kwargs["competenza_al"])
        # Il periodo non sparisce: resta sulla riga di commessa.
        inputs = repo.batch_upsert_attivita.call_args[0][0]
        self.assertEqual(
            [(i.competenza_dal, i.competenza_al) for i in inputs],
            [(date(2026, 6, 1), date(2026, 6, 30)), (date(2026, 7, 1), date(2026, 7, 31))],
        )

    # Scopo: simmetrico — le sorgenti a evento tengono il periodo nella chiave:
    #        senza, il test sopra si soddisferebbe togliendo il periodo a tutti.
    def test_sorgente_a_evento_tiene_il_periodo_nella_chiave(self):
        repo = _mock_repo()
        repo.get_or_create_commessa.side_effect = [10, 11]
        repo.fetch_pushable_rows.return_value = [
            _make_row(segment_key="K:1", sorgente_chiave="uid-1",
                      competenza_dal=date(2026, 6, 1), competenza_al=date(2026, 6, 30)),
            _make_row(segment_key="K:2", sorgente_chiave="uid-2",
                      competenza_dal=date(2026, 7, 1), competenza_al=date(2026, 7, 31)),
        ]
        HandlerPreventivi(repo).run()

        self.assertEqual(repo.get_or_create_commessa.call_count, 2)
        self.assertEqual(
            [c.kwargs["competenza_dal"] for c in repo.get_or_create_commessa.call_args_list],
            [date(2026, 6, 1), date(2026, 7, 1)],
        )

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
            segment_key="ATTIVITA_CONSUMI:uid-001",
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
        handler._fetch_componenti = MagicMock(return_value=componenti)  # type: ignore[method-assign]

        result = handler.run()

        self.assertEqual(result.created, 2)
        repo.batch_upsert_attivita.assert_called_once()
        # Verifica segment_key espanso nel batch.
        inputs = repo.batch_upsert_attivita.call_args[0][0]
        self.assertEqual(len(inputs), 2)
        keys = [inp.segment_key for inp in inputs]
        self.assertIn("ATTIVITA_CONSUMI:uid-001:COMP:COMP_A", keys)
        self.assertIn("ATTIVITA_CONSUMI:uid-001:COMP:COMP_B", keys)

    # Scopo: due righe con stessi parametri commessa → get_or_create_commessa chiamata una sola volta (cache).
    def test_process_rows_cache_commessa_evita_chiamate_ripetute(self):
        repo = _mock_repo(inserted=2)
        # Due righe con stessi parametri commessa ma segment_key diverso.
        row1 = _make_row(segment_key="TEST:uid-001:R:1", sorgente_chiave="uid-001")
        row2 = _make_row(segment_key="TEST:uid-002:R:1", sorgente_chiave="uid-002")
        repo.fetch_pushable_rows.return_value = [row1, row2]
        handler = HandlerPreventivi(repo)

        result = handler.run()

        self.assertEqual(result.created, 2)
        # Cache: get_or_create_commessa chiamata 1 volta, non 2.
        repo.get_or_create_commessa.assert_called_once()
        # Batch upsert: 1 sola chiamata con 2 input.
        repo.batch_upsert_attivita.assert_called_once()
        self.assertEqual(len(repo.batch_upsert_attivita.call_args[0][0]), 2)

    # Scopo: ⚠️ LA CACHE NON SI AVVELENA — se una riga cade DOPO aver risolto la
    #        commessa, il rollback del suo savepoint annulla la commessa nel
    #        database ma non toccherebbe un dizionario Python. Se l'id restasse
    #        in cache, la riga gemella successiva lo riuserebbe e fallirebbe
    #        anch'essa su una commessa inesistente: un errore che si propaga da
    #        solo. La registrazione avviene a savepoint rilasciato
    #        (`run_fan_out(on_success=...)`), quindi la seconda riga torna al
    #        database e atterra.
    def test_cache_commessa_non_avvelenata_da_riga_caduta(self):
        repo = _mock_repo(inserted=1)
        # Stessa chiave commessa: senza la protezione, la 2a riuserebbe l'id
        # della 1a (annullata dal rollback).
        row1 = _make_row(segment_key="TEST:uid-001:R:1", sorgente_chiave="uid-001")
        row2 = _make_row(segment_key="TEST:uid-002:R:1", sorgente_chiave="uid-002")
        repo.fetch_pushable_rows.return_value = [row1, row2]
        # La 1a riga cade DOPO get_or_create_commessa (che ha gia' popolato la
        # cache nella vecchia forma), nella costruzione del suo input; la 2a passa.
        handler = HandlerPreventivi(repo)
        build_vero = handler._build_attivita_input
        chiamate = {"n": 0}

        def _build_che_cade_la_prima_volta(commessa_id, row):
            chiamate["n"] += 1
            if chiamate["n"] == 1:
                raise RuntimeError("riga ko")
            return build_vero(commessa_id, row)

        with patch.object(
            handler, "_build_attivita_input", side_effect=_build_che_cade_la_prima_volta,
        ):
            result = handler.run()

        # La 2a riga NON ha riusato la cache: e' tornata al database.
        self.assertEqual(repo.get_or_create_commessa.call_count, 2)
        # Ed e' atterrata: un solo errore (la prima), una sola riga nel batch.
        self.assertEqual(len(result.errors), 1)
        self.assertIn("uid-001", result.errors[0])
        repo.batch_upsert_attivita.assert_called_once()
        self.assertEqual(len(repo.batch_upsert_attivita.call_args[0][0]), 1)
        # La commessa della riga caduta non e' tracciata (niente id fantasma).
        self.assertEqual(result.created, 1)

    # Scopo: Verifica distinzione created vs updated da BatchUpsertResult.
    def test_process_rows_batch_created_vs_updated(self):
        repo = _mock_repo(inserted=1, updated=1)
        row1 = _make_row(segment_key="NEW:row1", sorgente_chiave="uid-001")
        row2 = _make_row(segment_key="UPD:row2", sorgente_chiave="uid-002")
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
    defaults: dict[str, Any] = {
        "billing_account_id": 100,
        "utility_id": 5,
        "emittente_soggetto_ruolo_id": 200,
        "competenza_dal": date(2026, 6, 1),
        "competenza_al": date(2026, 6, 30),
        "fatturazione_immediata": False,
        "sorgente_tipo_id": 7,
        "sorgente_chiave": "uid-preventivo-001",
        "segment_key": "PREVENTIVO:uid-preventivo-001:R:42",
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
        "esposizione_in_fattura": "DESCRITTIVO",
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
    # pre-popolati. Modello unificato 2026-05-13: `esposizione_in_fattura`
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
                "esposizione_in_fattura": "VALORIZZATO",
            },
            {
                "componente_id": "cmp-02",
                "uom_operativa_id": 43,
                "prezzo_unitario": Decimal("75.00"),
                "coeff_qta_snapshot": Decimal("4"),
                "origine_prezzo": "MANUALE",
                "esposizione_in_fattura": "NASCOSTO",
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
        self.assertEqual(result[0].meta["esposizione"], "VALORIZZATO")
        self.assertEqual(result[0].meta["componente_di"], str(row.articolo_id))
        self.assertEqual(result[1].meta["esposizione"], "NASCOSTO")
        # origine_prezzo propagato in meta per audit downstream
        self.assertEqual(result[0].meta["origine_prezzo"], "LISTINO_BUNDLE")
        self.assertEqual(result[1].meta["origine_prezzo"], "MANUALE")
        # Il modo e' il CODICE letto dalla distinta, non un booleano
        # (dal 2026-10-01), e nessuna vecchia chiave resta nel meta.
        self.assertNotIn("esposto_in_fattura", result[0].meta)

    # Scopo: snapshot senza `esposizione_in_fattura` (LEFT JOIN sulla
    # distinta) → il default della colonna, NASCOSTO.
    def test_snapshot_loader_esposizione_default_nascosto_se_assente(self):
        snapshot_loader = MagicMock(return_value=[
            {
                "componente_id": "cmp-01",
                "uom_operativa_id": 42,
                "prezzo_unitario": Decimal("100.00"),
                "coeff_qta_snapshot": Decimal("1"),
                "origine_prezzo": "MANUALE",
                # Nessuna esposizione_in_fattura
            },
        ])
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
        )
        row = _make_composito_row(riga_sorgente_id=42)

        result = expander.expand(row)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].meta["esposizione"], "NASCOSTO")

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

    # ── I componenti dal LISTINO (D-2 (c), brief-db-contratto-righe-
    #    periodiche-in-commessa §7.2): il kit che il documento non negozia ──

    # Scopo: la quota fissa di un kit arriva senza riga sorgente: i
    # componenti li da' il secondo lettore, che riceve la riga intera.
    def test_kit_senza_riga_legge_i_componenti_dal_listino(self):
        snapshot_loader = MagicMock()
        listino_loader = MagicMock(return_value=[
            _make_snapshot_componente(componente_id="cmp-01", coeff_qta_snapshot=Decimal("2")),
            _make_snapshot_componente(componente_id="cmp-02", coeff_qta_snapshot=Decimal("1")),
        ])
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
            componenti_listino_loader=listino_loader,
        )
        row = _make_composito_row(riga_sorgente_id=None)

        result = expander.expand(row)

        snapshot_loader.assert_not_called()
        listino_loader.assert_called_once_with(row)
        self.assertEqual([r.articolo_id for r in result], ["cmp-01", "cmp-02"])
        self.assertEqual([r.quantita for r in result], [Decimal("6"), Decimal("3")])

    # Scopo: l'ADESIONE su un kit ha la riga ma nessun componente suo: dopo
    # lo snapshot vuoto, il listino.
    def test_kit_aderito_snapshot_vuoto_legge_il_listino(self):
        snapshot_loader = MagicMock(return_value=[])
        listino_loader = MagicMock(return_value=[_make_snapshot_componente(componente_id="cmp-01")])
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=snapshot_loader,
            componenti_listino_loader=listino_loader,
        )
        row = _make_composito_row(riga_sorgente_id=42)

        result = expander.expand(row)

        snapshot_loader.assert_called_once_with(42)
        listino_loader.assert_called_once_with(row)
        self.assertEqual([r.articolo_id for r in result], ["cmp-01"])

    # Scopo: i componenti negoziati vincono: il listino non si legge.
    def test_componenti_negoziati_il_listino_non_si_legge(self):
        listino_loader = MagicMock()
        expander = BoMComponentExpander(
            is_composito_fn=MagicMock(return_value=True),
            componenti_loader=MagicMock(return_value=[_make_snapshot_componente()]),
            componenti_listino_loader=listino_loader,
        )

        expander.expand(_make_composito_row(riga_sorgente_id=42))

        listino_loader.assert_not_called()

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
    # BA, utility, sorgente_chiave, emittente, competenza, fatturazione_immediata)
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
            sorgente_chiave="SRC-abc",
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
        self.assertEqual(componente.sorgente_chiave, "SRC-abc")
        self.assertEqual(componente.emittente_soggetto_ruolo_id, 333)
        self.assertEqual(componente.competenza_mese, date(2026, 9, 1))
        self.assertTrue(componente.fatturazione_immediata)

    # Scopo: DEC-6 — meta componente arricchito con `esposizione`,
    # `componente_di` (audit inverso), `coeff_qta`, `origine_prezzo`.
    # Preserva meta padre.
    def test_snapshot_meta_arricchito(self):
        snapshot_loader = MagicMock(return_value=[
            _make_snapshot_componente(
                componente_id="cmp-01",
                esposizione_in_fattura="DESCRITTIVO",
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

        self.assertEqual(result[0].meta["esposizione"], "DESCRITTIVO")
        self.assertEqual(result[0].meta["componente_di"], "art-parent")
        self.assertEqual(result[0].meta["coeff_qta"], "2")
        self.assertEqual(result[0].meta["origine_prezzo"], "MANUALE")
        # Quantita' e UoM della riga PADRE (R-BE-B2): la fattura le congela
        # sulla riga del kit. Il padre qui e' 3 in uom 42; il componente 3 x 2.
        self.assertEqual(result[0].meta["qta_padre"], "3")
        self.assertEqual(result[0].meta["uom_padre_id"], 42)
        self.assertEqual(result[0].quantita, Decimal("6"))
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
            _make_row(articolo_id=None, prezzo_snapshot=None, segment_key="ATTIVITA_CONSUMI:uid-1")
        ]
        handler = HandlerConsumi(repo, bom_expander=expander)
        # Stub fan-out consumi: 2 componenti.
        handler._fetch_componenti = MagicMock(return_value=[  # type: ignore[method-assign]
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
                segment_key="PREVENTIVO:uid-1:R:1",
                sorgente_chiave="uid-1",
                riga_sorgente_id=11,
            ),
            _make_composito_row(
                articolo_id="art-semplice",
                segment_key="PREVENTIVO:uid-1:R:2",
                sorgente_chiave="uid-1",
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
            "PREVENTIVO:uid-1:R:1#CMP:cmp-A",
            "PREVENTIVO:uid-1:R:1#CMP:cmp-B",
            "PREVENTIVO:uid-1:R:2",
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
            _make_composito_row(segment_key="PREVENTIVO:uid-X:R:7", riga_sorgente_id=7),
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
            _make_composito_row(segment_key="PREVENTIVO:uid-X:R:7", riga_sorgente_id=7),
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


class PricingAuditSnapshotTests(TestCase):
    """Snapshot pricing v5 (F2-BE-12 / analisi-commesse §4.3 #2): il push popola
    gli 8 campi audit di derivazione del prezzo via PricingService, senza
    sovrascrivere il prezzo negoziato (autoritativo)."""

    @staticmethod
    def _handler(repo, pricing_service):
        # is_composito_fn=False → expand pass-through senza query DB; resolver iniettato.
        return HandlerPreventivi(
            repo,
            bom_expander=BoMComponentExpander(is_composito_fn=lambda _aid: False),
            pricing_service=pricing_service,
        )

    @staticmethod
    def _resolver_full() -> MagicMock:
        ps = MagicMock()
        ps.resolve_prezzo.return_value = {
            "prezzo_base_snapshot": Decimal("30.00"),
            "origine": "CONTRATTO_LISTINO",
            "tipo_variazione_applicata": "PERCENTUALE",
            "valore_variazione_applicata": Decimal("-10.00"),
            "promo_id": None,
            "contratto_id": 77,
            "categoria_cliente_id_snapshot": 5,
            "classe_utenza_id_snapshot": None,
            "listino_versione_id": 404,
            "listino_riga_id": 505,
        }
        return ps

    @staticmethod
    def _atomic_noop():
        # transaction.atomic → no-op context (test unitario senza DB).
        return patch(
            "apps.vendite.services.commesse_source_handlers.transaction.atomic",
            side_effect=lambda *a, **k: nullcontext(),
        )

    # Scopo: i 8 campi audit del resolver atterrano sul CommessaAttivitaInput.
    def test_audit_snapshot_popolato_da_resolver(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row(uom_id=9)]
        ps = self._resolver_full()
        handler = self._handler(repo, ps)

        with self._atomic_noop():
            handler.run()

        inp = repo.batch_upsert_attivita.call_args[0][0][0]
        self.assertEqual(inp.prezzo_base_snapshot, Decimal("30.00"))
        self.assertEqual(inp.origine_prezzo, "CONTRATTO_LISTINO")
        self.assertEqual(inp.tipo_variazione_applicata, "PERCENTUALE")
        self.assertEqual(inp.valore_variazione_applicata, Decimal("-10.00"))
        self.assertIsNone(inp.promo_id)
        self.assertEqual(inp.contratto_id, 77)
        self.assertEqual(inp.categoria_cliente_id_snapshot, 5)
        self.assertIsNone(inp.classe_utenza_id_snapshot)
        # ⭐ 2026-10-08: anche la versione di listino, o il guard «versione
        #    cambiata» di riallinea confronta con NULL e non scatta mai.
        self.assertEqual(inp.listino_versione_id, 404)
        # ⛔ 2026-10-09 (decisione B): la riga di listino NO, anche se il
        #    resolver la restituisce. Il prezzo e' del documento: citarla
        #    renderebbe «propagata» una riga di listino che non l'ha dato.
        self.assertIsNone(inp.listino_riga_id)
        ps.resolve_prezzo.assert_called_once()

    # Scopo: il prezzo negoziato alla sorgente NON viene sovrascritto dal resolver.
    def test_prezzo_snapshot_negoziato_non_sovrascritto(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [
            _make_row(uom_id=9, prezzo_snapshot=Decimal("27.00"))
        ]
        handler = self._handler(repo, self._resolver_full())

        with self._atomic_noop():
            handler.run()

        inp = repo.batch_upsert_attivita.call_args[0][0][0]
        self.assertEqual(inp.prezzo_snapshot, Decimal("27.00"))

    # Scopo: errore resolver → audit a None ma la riga e' comunque upsertata.
    def test_audit_best_effort_resolver_errore_non_blocca(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row(uom_id=9)]
        ps = MagicMock()
        ps.resolve_prezzo.side_effect = RuntimeError("resolver down")
        handler = self._handler(repo, ps)

        with self._atomic_noop():
            result = handler.run()

        self.assertEqual(result.created, 1)
        inp = repo.batch_upsert_attivita.call_args[0][0][0]
        self.assertIsNone(inp.prezzo_base_snapshot)
        self.assertIsNone(inp.contratto_id)

    # Scopo: per i componenti BoM, origine_prezzo negoziato (meta) prevale.
    def test_origine_prezzo_da_meta_prevale_su_resolver(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [
            _make_row(
                uom_id=9,
                meta={
                    "tipo_commessa": "AUTO",
                    "policy_fatturazione": "DA_DOCUMENTO",
                    "origine_prezzo": "PROMO",
                },
            )
        ]
        handler = self._handler(repo, self._resolver_full())

        with self._atomic_noop():
            handler.run()

        inp = repo.batch_upsert_attivita.call_args[0][0][0]
        self.assertEqual(inp.origine_prezzo, "PROMO")

    # Scopo: uom None → resolver non chiamato (guard), audit a None.
    def test_audit_skip_se_uom_none_nessuna_chiamata_resolver(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row(uom_id=None)]
        ps = MagicMock()
        handler = self._handler(repo, ps)

        handler.run()

        ps.resolve_prezzo.assert_not_called()
        inp = repo.batch_upsert_attivita.call_args[0][0][0]
        self.assertIsNone(inp.prezzo_base_snapshot)

    # Scopo: due righe stesso contesto pricing → una sola risoluzione (cache).
    def test_audit_cache_dedup_stesso_contesto_un_solo_resolve(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [
            _make_row(uom_id=9, segment_key="S:1", sorgente_chiave="u1"),
            _make_row(uom_id=9, segment_key="S:2", sorgente_chiave="u2"),
        ]
        ps = self._resolver_full()
        handler = self._handler(repo, ps)

        with self._atomic_noop():
            handler.run()

        self.assertEqual(ps.resolve_prezzo.call_count, 1)


class CompositiFanOutWiringTests(TestCase):
    """Fan-out compositi via modello unico `*_righe_componenti` per sorgenti
    ≠ preventivo (analisi-commesse §4.3 #3): ordini/contratti/DDT riusano lo
    stesso BoMComponentExpander + loader snapshot di preventivi."""

    # Scopo: la factory preventivi punta alla tabella componenti del preventivo.
    def test_factory_preventivi_ritorna_repo_componenti(self):
        repo = HandlerPreventivi._componenti_repo_factory()
        self.assertEqual(repo._componenti_table_name, "vendite.preventivi_righe_componenti")
        self.assertEqual(repo._componenti_fk_riga, "riga_preventivo_id")
        self.assertTrue(hasattr(repo, "list_componenti_riga"))

    # Scopo: la factory ordini punta a ordini_righe_componenti.
    def test_factory_ordini_ritorna_repo_componenti(self):
        repo = HandlerOrdini._componenti_repo_factory()
        self.assertEqual(repo._componenti_table_name, "vendite.ordini_righe_componenti")
        self.assertEqual(repo._componenti_fk_riga, "riga_ordine_id")

    # Scopo: la factory contratti punta a contratti_righe_componenti.
    def test_factory_contratti_ritorna_repo_componenti(self):
        repo = HandlerContratti._componenti_repo_factory()
        self.assertEqual(repo._componenti_table_name, "vendite.contratti_righe_componenti")
        self.assertEqual(repo._componenti_fk_riga, "riga_contratto_id")

    # Scopo: la factory DDT punta a ddt_righe_componenti.
    def test_factory_ddt_ritorna_repo_componenti(self):
        repo = HandlerDdt._componenti_repo_factory()
        self.assertEqual(repo._componenti_table_name, "vendite.ddt_righe_componenti")
        self.assertEqual(repo._componenti_fk_riga, "riga_ddt_id")

    # Scopo: l'expander di default dei 4 handler documento ha un componenti_loader
    #        (il fan-out compositi NON e' piu' esclusiva dei preventivi).
    def test_default_expander_ha_componenti_loader_per_documento(self):
        for cls in (HandlerPreventivi, HandlerOrdini, HandlerContratti, HandlerDdt):
            handler = cls(_mock_repo())
            self.assertIsNotNone(
                handler._bom_expander._componenti_loader,
                f"{cls.__name__}: atteso loader componenti nel default expander",
            )

    # Scopo: il secondo lettore (i componenti dal listino, D-2 (c)) ce l'ha
    #        solo il contratto; legge alla data del pezzo, col contratto della
    #        riga (`sorgente_chiave`, col suo tipo).
    def test_solo_il_contratto_legge_i_kit_dal_listino(self):
        for cls in (HandlerPreventivi, HandlerOrdini, HandlerDdt):
            self.assertIsNone(cls(_mock_repo())._bom_expander._componenti_listino_loader)
        comp_repo = MagicMock()
        comp_repo.list_componenti_kit_dal_listino.return_value = ["c1"]
        loader = HandlerContratti._componenti_listino_loader(comp_repo)
        row = _make_composito_row(sorgente_chiave="uid-ctr", data_attivita=date(2026, 7, 1))

        self.assertEqual(loader(row), ["c1"])
        comp_repo.list_componenti_kit_dal_listino.assert_called_once_with(
            sorgente_tipo_id=row.sorgente_tipo_id, contratto_chiave="uid-ctr",
            articolo_padre_id=row.articolo_id, data=date(2026, 7, 1),
        )

    # Scopo: una lettura per (contratto, kit, data) nel giro; un'altra data
    #        e' un'altra lettura (il listino puo' cambiare versione).
    def test_kit_dal_listino_una_lettura_per_pezzo(self):
        comp_repo = MagicMock()
        comp_repo.list_componenti_kit_dal_listino.return_value = ["c1"]
        loader = HandlerContratti._componenti_listino_loader(comp_repo)
        luglio = _make_composito_row(sorgente_chiave="uid-ctr", data_attivita=date(2026, 7, 1))
        agosto = _make_composito_row(sorgente_chiave="uid-ctr", data_attivita=date(2026, 8, 1))

        loader(luglio)
        loader(luglio)
        self.assertEqual(comp_repo.list_componenti_kit_dal_listino.call_count, 1)
        loader(agosto)
        self.assertEqual(comp_repo.list_componenti_kit_dal_listino.call_count, 2)

    # Scopo: i consumi NON usano il modello unico (decomposizione tariffaria a
    #        parte, rinviata) → nessuna factory componenti.
    def test_consumi_nessuna_factory_componenti(self):
        self.assertIsNone(HandlerConsumi._componenti_repo_factory)
        handler = HandlerConsumi(_mock_repo())
        self.assertIsNone(handler._bom_expander._componenti_loader)

    # Scopo: integrazione — un ordine con articolo composito fa fan-out in N
    #        righe leggendo i componenti negoziati (default expander + factory).
    def test_ordini_default_fanout_compositi_da_componenti(self):
        repo = _mock_repo()
        row = _make_row(uom_id=9, articolo_id="art-comp", riga_sorgente_id=55)
        repo.fetch_pushable_rows.return_value = [row]

        comp_repo = MagicMock()
        comp_repo.list_componenti_riga.return_value = [
            {"componente_id": "c1", "uom_operativa_id": 9,
             "prezzo_unitario": Decimal("5.00"), "coeff_qta_snapshot": "1",
             "esposizione_in_fattura": "DESCRITTIVO", "origine_prezzo": "CONTRATTO_LISTINO"},
            {"componente_id": "c2", "uom_operativa_id": 9,
             "prezzo_unitario": Decimal("3.00"), "coeff_qta_snapshot": "2",
             "esposizione_in_fattura": "NASCOSTO", "origine_prezzo": "CONTRATTO_LISTINO"},
        ]
        ps = MagicMock()
        ps.resolve_prezzo.return_value = {}  # audit best-effort, non rilevante qui

        with patch.object(HandlerOrdini, "_componenti_repo_factory",
                          staticmethod(lambda: comp_repo)), \
             patch(
                 "apps.vendite.services.commesse_source_handlers."
                 "BoMComponentExpander._default_is_composito", return_value=True), \
             patch(
                 "apps.vendite.services.commesse_source_handlers.transaction.atomic",
                 side_effect=lambda *a, **k: nullcontext()):
            handler = HandlerOrdini(repo, pricing_service=ps)
            handler.run()

        comp_repo.list_componenti_riga.assert_called_once_with(55)
        inputs = repo.batch_upsert_attivita.call_args[0][0]
        self.assertEqual(len(inputs), 2, "articolo composito → 2 righe componente")
        segment_keys = {i.segment_key for i in inputs}
        self.assertTrue(all("#CMP:" in sk for sk in segment_keys))


class _OrigineFuoriCheckTests(TestCase):
    """Regressione: il resolver puo' restituire origine fuori dal CHECK
    (es. 'LISTINO_BUNDLE') → deve diventare NULL, non far fallire l'upsert."""

    # Scopo: origine resolver fuori set → origine_prezzo NULL, riga salvata.
    def test_audit_origine_fuori_check_diventa_null(self):
        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [_make_row(uom_id=9)]
        ps = MagicMock()
        ps.resolve_prezzo.return_value = {
            "prezzo_base_snapshot": Decimal("12.00"),
            "origine": "LISTINO_BUNDLE",  # NON nel CHECK
            "tipo_variazione_applicata": "NESSUNA",
            "valore_variazione_applicata": None,
            "promo_id": None,
            "contratto_id": None,
            "categoria_cliente_id_snapshot": None,
            "classe_utenza_id_snapshot": None,
        }
        handler = HandlerPreventivi(
            repo,
            bom_expander=BoMComponentExpander(is_composito_fn=lambda _aid: False),
            pricing_service=ps,
        )
        with patch(
            "apps.vendite.services.commesse_source_handlers.transaction.atomic",
            side_effect=lambda *a, **k: nullcontext(),
        ):
            result = handler.run()

        self.assertEqual(result.created, 1)
        inp = repo.batch_upsert_attivita.call_args[0][0][0]
        self.assertIsNone(inp.origine_prezzo, "origine fuori CHECK deve essere NULL")
        self.assertEqual(inp.prezzo_base_snapshot, Decimal("12.00"))
        self.assertEqual(inp.tipo_variazione_applicata, "NESSUNA")


class PreCommessaHookTests(TestCase):
    """Hook scaffolding fasi di lavorazione (§6): default identity, override
    applicato per riga prima della creazione commessa."""

    # Scopo: default = identity (ritorna la stessa riga).
    def test_hook_default_identity(self):
        row = _make_row()
        handler = HandlerOrdini(_mock_repo())
        self.assertIs(handler._pre_commessa_hook(row), row)

    # Scopo: un override del hook altera la riga usata dal push (meta arricchito).
    def test_hook_override_applicato_al_push(self):
        class _HandlerConFase(HandlerOrdini):
            def _pre_commessa_hook(self, row):
                meta = {**(row.meta or {}), "fase_lavorazione_id": 99}
                return dataclasses.replace(row, meta=meta)

        repo = _mock_repo()
        repo.fetch_pushable_rows.return_value = [
            _make_row(meta={"tipo_commessa": "AUTO", "policy_fatturazione": "DA_DOCUMENTO"})
        ]
        handler = _HandlerConFase(repo)
        handler.run()

        inp = repo.batch_upsert_attivita.call_args[0][0][0]
        self.assertEqual(inp.meta.get("fase_lavorazione_id"), 99)
