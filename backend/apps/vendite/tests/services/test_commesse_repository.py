# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari CommesseRepository.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CommesseRepositoryUnitTests.test_get_or_create_commessa_returns_int
1b) CommesseRepositoryUnitTests.test_get_or_create_commessa_propaga_condizioni_pagamento
1c) CommesseRepositoryUnitTests.test_get_or_create_commessa_condizioni_assenti_passano_null
1d) CommesseRepositoryUnitTests.test_get_or_create_commessa_non_passa_emittente
2) CommesseRepositoryUnitTests.test_get_commessa_viva_by_sorgente_legge_la_funzione_db
2b) CommesseRepositoryUnitTests.test_get_commessa_viva_by_sorgente_none_senza_commessa_aperta
2c) CommesseRepositoryUnitTests.test_get_commessa_viva_by_sorgente_codice_sconosciuto_raises
3) CommesseRepositoryUnitTests.test_upsert_attivita_returns_result
4) CommesseRepositoryUnitTests.test_upsert_attivita_uses_defaults
5) CommesseRepositoryUnitTests.test_emit_attivita_fatturabili_maps_result
6) CommesseRepositoryUnitTests.test_emit_attivita_fatturabili_dry_run_zero_writes
7) CommesseRepositoryUnitTests.test_get_commessa_stato_maps_contatori
8) CommesseRepositoryUnitTests.test_get_commessa_stato_returns_none_when_not_found
9) CommesseRepositoryUnitTests.test_start_push_run_apre_il_giro
9b) CommesseRepositoryUnitTests.test_close_push_run_chiude_il_giro
10) CommesseRepositoryUnitTests.test_get_push_log_maps_row
11) CommesseRepositoryUnitTests.test_get_push_log_returns_none_when_not_found
12) CommesseRepositoryUnitTests.test_fetch_pushable_rows_calls_correct_fn
13) CommesseRepositoryUnitTests.test_fetch_pushable_rows_unknown_sorgente_raises
13b) CommesseRepositoryUnitTests.test_fetch_pushable_rows_righe_ids_preventivo
13c) CommesseRepositoryUnitTests.test_fetch_pushable_rows_righe_ids_sorgente_non_supportata
14) CommesseRepositoryUnitTests.test_fetch_pushable_rows_maps_shared_columns
14b) CommesseRepositoryUnitTests.test_fetch_pushable_rows_maps_causale_onere
15) CommesseRepositoryUnitTests.test_get_or_create_commessa_uses_defaults
16) CommesseRepositoryUnitTests.test_validate_sorgente_map_ok
17) CommesseRepositoryUnitTests.test_validate_sorgente_map_missing_in_map
18) CommesseRepositoryUnitTests.test_list_commesse_emittibili_returns_ids
19) CommesseRepositoryUnitTests.test_list_commesse_emittibili_empty
20) CommesseRepositoryUnitTests.test_list_commessa_attivita_maps_rows
21) CommesseRepositoryUnitTests.test_list_commessa_attivita_empty
22) CommesseRepositoryUnitTests.test_list_active_push_sources
23) CommesseRepositoryUnitTests.test_batch_upsert_attivita_maps_result
24) CommesseRepositoryUnitTests.test_batch_upsert_attivita_empty_list
25) CommesseRepositoryUnitTests.test_upsert_attivita_passes_snapshot_v5_params
26) CommesseRepositoryUnitTests.test_inp_to_jsonb_row_includes_snapshot_v5_keys
26b) CommesseRepositoryUnitTests.test_inp_to_jsonb_row_porta_la_causale_onere
27) DiagnosticaGruppiTernePronteTests.test_terne_pronte_stringa_json_viene_decodificata
28) DiagnosticaGruppiTernePronteTests.test_terne_pronte_vuote_restano_lista_vuota
29) DiagnosticaGruppiTernePronteTests.test_terne_pronte_gia_lista_passa_intatta
"""

from datetime import UTC, date, datetime, timezone
from decimal import Decimal
from inspect import signature
from unittest import TestCase
from unittest.mock import patch

from apps.vendite.db.commesse_repository import (
    BatchUpsertResult,
    CommessaAttivitaInput,
    CommesseRepository,
    PushableRow,
    UpsertAttivitaResult,
    _SORGENTE_FN_MAP,
)
from apps.core.services.service_errors import ServiceError
from apps.vendite.tests._helpers.mock_cursor import mock_cursor as _mock_cursor


# Colonne restituite da fn_list_ordini_da_pushare (31 totali: 3 source + 28
# shared — contratto rev 2026-08-03, changeset 20260803-02: le fn espongono
# anche termine_pagamento_id e modalita_pagamento_id del documento).
# ⚠️ Questa lista DEVE specchiare il contratto REALE della fn: e' cio' che
# decide se `col_map` vede una colonna. La prima stesura del binding e' stata
# «confermata» da un mock fermo a 29 colonne mentre la whitelist
# `_PUSHABLE_SHARED_COLS` non era stata estesa — verde su un comportamento
# inesistente (feedback_whitelist_dal_percorso_reale), scoperto dallo smoke.
_ORDINI_COLS = [
    ("ordine_id",), ("ordine_uid",), ("riga_id",),
    ("billing_account_id",), ("utility_id",), ("emittente_soggetto_ruolo_id",),
    ("competenza_dal",), ("competenza_al",), ("fatturazione_immediata",),
    ("sorgente_tipo_id",), ("sorgente_chiave",), ("segment_key",),
    ("articolo_id",), ("istanza_utility_id",), ("data_attivita",),
    ("uom_id",), ("quantita",), ("qta_operativa",),
    ("uom_operativa_id",), ("factor_to_base",), ("competenza_mese",),
    ("prezzo_snapshot",), ("prezzo_bloccato",), ("pricing_mode",),
    ("tipo_movimento",), ("valuta_id",),
    ("meta",), ("tipo_doc_fiscale_id",),
    ("termine_pagamento_id",), ("modalita_pagamento_id",),
    # La causale della riga ONERE, in coda (20261103-38).
    ("causale_onere_id",),
]

# Tupla di test che simula una riga ordine.
_ORDINI_ROW = (
    # 3 source-specific
    100, "uid-ordine-001", 200,
    # 27 shared (tipo_consumo ritirato, DB 20261013-60…-67)
    1, 2, 3,
    date(2026, 6, 1), date(2026, 6, 30), False,
    6, "uid-ordine-001", "ORDINE_VENDITA:uid-ordine-001:R:200",
    "art-uuid-001", 4, date(2026, 6, 1),
    None, Decimal("10.0"), Decimal("10.0"),
    None, Decimal("1"), date(2026, 6, 1),
    Decimal("22.50"), True, "FIXED",
    "NORMALE", 1,
    {"tipo_commessa": "AUTO", "policy_fatturazione": "DA_DOCUMENTO"},
    7,   # tipo_doc_fiscale_id
    3,   # termine_pagamento_id (le condizioni del DOCUMENTO)
    5,   # modalita_pagamento_id
    None,  # causale_onere_id (riga di merce)
)


class CommesseRepositoryUnitTests(TestCase):

    # Scopo: Verifica che get_or_create_commessa chiami la funzione DB e restituisca int.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_or_create_commessa_returns_int(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(42,))
        repo = CommesseRepository()
        result = repo.get_or_create_commessa(
            billing_account_id=1,
            utility_id=2,
            tipo_commessa="AUTO",
            policy_fatturazione="DA_DOCUMENTO",
            fatturazione_immediata=False,
            priorita_operativa="NORMALE",
            competenza_dal=date(2026, 6, 1),
            competenza_al=date(2026, 6, 30),
        )
        self.assertEqual(result, 42)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_get_or_create_commessa", sql)

    # Scopo: PROPAGAZIONE CONDIZIONI DI PAGAMENTO (2026-08-03). Il termine del
    #        documento sorgente deve arrivare a `fn_get_or_create_commessa`:
    #        e' da li' che la catena lo porta in fattura (D-R). Il difetto che
    #        questo test blocca e' costato una fattura reale — ORD0004786
    #        dichiarava 2 rate a 30/60 e la 2263 e' uscita con 1 rata a 30 gg,
    #        perche' il BE non passava i due parametri che la fn accettava gia'.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_or_create_commessa_propaga_condizioni_pagamento(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(77,))
        repo = CommesseRepository()
        repo.get_or_create_commessa(
            billing_account_id=1,
            utility_id=2,
            competenza_dal=date(2026, 8, 1),
            competenza_al=date(2026, 8, 31),
            termine_pagamento_id=3,
            modalita_pagamento_id=5,
        )
        sql, args = mock_cursor_factory.return_value.execute.call_args[0]
        # I due parametri devono essere NOMINATI nella chiamata: la chiamata
        # e' per nome, quindi un posizionale sbagliato non e' rilevabile
        # guardando i soli valori. ⛔ Quante siano le colonne non si scrive
        # qui: e' un fatto del database, e un numero copiato in un commento
        # invecchia senza che niente lo segnali (era «13» fino al 2026-08-26).
        self.assertIn("p_termine_pagamento_id", sql)
        self.assertIn("p_modalita_pagamento_id", sql)
        self.assertEqual(args[-2:], [3, 5])

    # Scopo: senza condizioni si passano NULL, non si omettono: la fn ha una
    #        firma fissa e un argomento in meno la renderebbe irrisolvibile.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_or_create_commessa_condizioni_assenti_passano_null(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(78,))
        CommesseRepository().get_or_create_commessa(billing_account_id=1)
        args = mock_cursor_factory.return_value.execute.call_args[0][1]
        self.assertEqual(args[-2:], [None, None])

    # Scopo: Verifica che get_or_create_commessa accetti i default (#7).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_or_create_commessa_uses_defaults(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(1,))
        repo = CommesseRepository()
        result = repo.get_or_create_commessa(billing_account_id=1)
        self.assertEqual(result, 1)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        # Verifica default: tipo_commessa="AUTO", priorita_operativa="NORMALE"
        self.assertEqual(params[2], "AUTO")
        self.assertEqual(params[5], "NORMALE")

    # Scopo: L'EMITTENTE NON SI PASSA PIU', e questo test e' il cancello che
    #        impedisce di rimetterlo. Dal 2026-08-26 il parametro non esiste
    #        piu' nella funzione DB (changeSet `20260826-52`): la chiamata e'
    #        per NOME, quindi ri-aggiungerlo non darebbe uno shift posizionale
    #        silenzioso — darebbe un «funzione inesistente» su OGNI push.
    #        ⚠️ I due lati vanno guardati ENTRAMBI, e non e' ridondanza: la
    #        firma Python che lo riaccettasse senza spedirlo lo farebbe
    #        ignorare in silenzio, l'SQL che lo spedisse senza averlo in firma
    #        romperebbe il push. Sono due difetti diversi.
    #        ⛔ Non si asserisce il NUMERO dei parametri: e' un fatto che vive
    #        nel database, e scriverlo qui lo duplicherebbe in un posto che
    #        invecchia da solo. Cio' che questo test puo' provare da se' e'
    #        che segnaposti e valori si CORRISPONDONO — se divergono la
    #        chiamata e' irrisolvibile, e guardando i soli nomi non si
    #        vedrebbe (stesso idioma di `test_fatturazione_job_helpers`).
    #        Piano: `brief-db-emittente-commessa-invariante` (D-2, lotto L5).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_or_create_commessa_non_passa_emittente(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(79,))
        CommesseRepository().get_or_create_commessa(billing_account_id=1, utility_id=2)
        sql, args = mock_cursor_factory.return_value.execute.call_args[0]
        self.assertNotIn("p_emittente_soggetto_ruolo_id", sql)
        self.assertNotIn(
            "emittente_soggetto_ruolo_id",
            signature(CommesseRepository.get_or_create_commessa).parameters,
        )
        self.assertEqual(sql.count("%s"), len(args))

    # Scopo: La commessa APERTA di un documento la dice il DB
    #        (`fn_commessa_viva_di_sorgente`), non una SELECT propria su
    #        `commesse_sorgenti`: con i link di storia (D-12) una `LIMIT 1`
    #        senza stato poteva dare la commessa annullata.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_commessa_viva_by_sorgente_legge_la_funzione_db(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(99,))
        result = CommesseRepository().get_commessa_viva_by_sorgente(
            sorgente_codice="PREVENTIVO", sorgente_uid="uuid-001",
        )
        self.assertEqual(result, 99)
        sql, args = mock_cursor_factory.return_value.execute.call_args[0]
        self.assertIn("vendite.fn_commessa_viva_di_sorgente", sql)
        self.assertNotIn("commesse_sorgenti", sql)
        # Le due chiavi del documento, nell'ordine della firma: per il
        # preventivo l'id e' NULL e l'uid porta la chiave (BE-C.2-a).
        self.assertEqual(args, [None, "uuid-001", "PREVENTIVO"])
        self.assertEqual(sql.count("%s"), len(args))

    # Scopo: Nessuna commessa aperta → la funzione torna NULL → None.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_commessa_viva_by_sorgente_none_senza_commessa_aperta(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(None,))
        self.assertIsNone(CommesseRepository().get_commessa_viva_by_sorgente(
            sorgente_codice="PREVENTIVO", sorgente_uid="uuid-001",
        ))

    # Scopo: Codice sorgente assente da config.sorgenti (nessuna riga) → errore
    #        col suo codice, NON None: un codice sbagliato non deve sembrare
    #        «nessuna commessa aperta» e far saltare l'aggancio in silenzio.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_commessa_viva_by_sorgente_codice_sconosciuto_raises(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=None)
        with self.assertRaises(ServiceError) as ctx:
            CommesseRepository().get_commessa_viva_by_sorgente(
                sorgente_codice="SCONOSCIUTO", sorgente_uid="uuid-001",
            )
        self.assertEqual(ctx.exception.code, "E_COMMESSA_SORGENTE_SCONOSCIUTA")

    # Scopo: Verifica che upsert_attivita chiami la fn DB e restituisca UpsertAttivitaResult.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_upsert_attivita_returns_result(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(77, True))
        repo = CommesseRepository()
        inp = CommessaAttivitaInput(
            commessa_id=10,
            segment_key="10_2026-06_BASE",
            quantita=Decimal("2.0"),
            competenza_mese=date(2026, 6, 1),
            articolo_id=1,
            prezzo_snapshot=Decimal("22.10"),
            uom_id=1,
            tipo_doc_fiscale_id=1,
            valuta_id=1,
            prezzo_bloccato=True,
            stato_approvazione="APPROVATA",
        )
        result = repo.upsert_attivita(inp)
        self.assertIsInstance(result, UpsertAttivitaResult)
        self.assertEqual(result.attivita_id, 77)
        self.assertTrue(result.is_new)
        sql, args = mock_cursor_factory.return_value.execute.call_args[0]
        self.assertIn("fn_upsert_commessa_attivita", sql)
        self.assertEqual(sql.count("%s"), len(args))

    # Scopo: Verifica default di CommessaAttivitaInput (#3, #4, #5, #10).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_upsert_attivita_uses_defaults(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(1, False))
        repo = CommesseRepository()
        inp = CommessaAttivitaInput(
            commessa_id=10,
            segment_key="seg",
            quantita=Decimal("1"),
            competenza_mese=date(2026, 6, 1),
            articolo_id=None,
            prezzo_snapshot=None,
        )
        # Verifica default dei campi ristrutturati.
        self.assertIsNone(inp.uom_id)
        self.assertIsNone(inp.tipo_doc_fiscale_id)
        self.assertFalse(inp.prezzo_da_riallineare)
        self.assertEqual(inp.stato_approvazione, "BOZZA")
        self.assertEqual(inp.stato_emissione, "NON_EMESSA")
        self.assertEqual(inp.tipo_movimento, "NORMALE")
        # `tipo_consumo` ritirato (DB 20261013-60…-67): l'input non lo porta piu'.
        self.assertFalse(hasattr(inp, "tipo_consumo"))
        repo.upsert_attivita(inp)

    # Scopo: Verifica mapping CommessaEmitResult da fn_emit_attivita_fatturabili_da_commessa.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_emit_attivita_fatturabili_maps_result(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(5, 3, 2))
        repo = CommesseRepository()
        result = repo.emit_attivita_fatturabili(commessa_id=10)
        self.assertEqual(result["total_candidate"], 5)
        self.assertEqual(result["inserted_rows"], 3)
        self.assertEqual(result["updated_rows"], 2)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_emit_attivita_fatturabili_da_commessa", sql)

    # Scopo: Verifica che dry_run=True venga passato e non produca righe scritte.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_emit_attivita_fatturabili_dry_run_zero_writes(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(3, 3, 0))
        repo = CommesseRepository()
        result = repo.emit_attivita_fatturabili(commessa_id=10, dry_run=True)
        self.assertEqual(result["total_candidate"], 3)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        # Firma a 3 parametri (commessa_id, only_approved, dry_run): dry_run = params[2].
        self.assertTrue(params[2])
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertNotIn("p_lotto_attivita_id", sql)

    # Scopo: Verifica mapping CommessaStatoResult da fn_get_commessa_stato
    #        (stato + flag governance + tutti i contatori). Colonne nell'ordine
    #        del RETURNS TABLE (senza commessa_id, non selezionato).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_commessa_stato_maps_contatori(self, mock_cursor_factory):
        # stato_commessa_id, stato_commessa, chiude, emittibile, modificabile,
        # policy, fatt_immediata, priorita, ba_id, utility_id, emittente_id,
        # total_attivita, total_approvate, total_non_approvate, total_emesse,
        # total_non_emesse, total_prezzo_da_riallineare, last_update,
        # commessa_codice, cliente_display (E-DB-4)
        mock_cursor_factory.return_value = _mock_cursor(
            fetchone=(
                4, "PRONTA_FATTURAZIONE", False, True, True,
                "DA_DOCUMENTO", False, None, 1001, 2, 555,
                10, 8, 2, 6, 4, 1, None,
                "COMM-0042", "Rossi Mario SRL",
            )
        )
        repo = CommesseRepository()
        result = repo.get_commessa_stato(commessa_id=10)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["stato_commessa"], "PRONTA_FATTURAZIONE")
        self.assertTrue(result["emittibile"])
        self.assertTrue(result["modificabile"])
        self.assertFalse(result["chiude_commessa"])
        self.assertEqual(result["total_attivita"], 10)
        self.assertEqual(result["total_approvate"], 8)
        self.assertEqual(result["total_non_approvate"], 2)
        self.assertEqual(result["total_emesse"], 6)
        self.assertEqual(result["total_non_emesse"], 4)
        self.assertEqual(result["total_prezzo_da_riallineare"], 1)
        self.assertIsNone(result["last_update"])
        self.assertEqual(result["commessa_codice"], "COMM-0042")
        self.assertEqual(result["cliente_display"], "Rossi Mario SRL")

    # Scopo: Verifica che get_commessa_stato restituisca None quando la commessa non esiste.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_commessa_stato_returns_none_when_not_found(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=None)
        repo = CommesseRepository()
        result = repo.get_commessa_stato(commessa_id=999)
        self.assertIsNone(result)

    # Scopo: l'APERTURA del giro chiama fn_start_commessa_push_run e restituisce
    #        l'id che il chiamante conservera' per la chiusura.
    #
    # ⚠️ `fn_log_commessa_push_run` NON esiste piu': il changeSet 69 l'ha
    #    DROPpata quando la riga ha smesso di nascere a fine corsa (BE-3b).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_start_push_run_apre_il_giro(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(55,))
        repo = CommesseRepository()
        result = repo.start_push_run(
            dry_run=False,
            source_types=["PREVENTIVO"],
            correlation_id="0199a0f0-0000-7000-8000-000000000000",
        )
        self.assertEqual(result, 55)
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_start_commessa_push_run", sql)
        # Il filo del giro arriva a DB: senza, la colonna resterebbe NULL e il
        # giro non si cucirebbe con nient'altro.
        self.assertIn(
            "0199a0f0-0000-7000-8000-000000000000",
            mock_cursor_factory.return_value.execute.call_args[0][1],
        )

    # Scopo: la CHIUSURA chiama fn_close_commessa_push_run con l'id del giro e
    #        il suo esito finale.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_close_push_run_chiude_il_giro(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=None)
        repo = CommesseRepository()
        repo.close_push_run(
            push_log_id=55,
            stato="COMPLETATO",
            risultato={"handlers": {"HandlerPreventivi": {"created": 3}}},
            durata_ms=1200,
            source_types=["PREVENTIVO"],
        )
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_close_commessa_push_run", sql)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        self.assertEqual(params[0], 55)
        self.assertEqual(params[1], "COMPLETATO")

    # Scopo: Verifica mapping CommessaPushLogRow da SELECT commesse_push_log.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_push_log_maps_row(self, mock_cursor_factory):
        ts = datetime(2026, 2, 24, 10, 0, 0, tzinfo=timezone.utc)
        mock_cursor_factory.return_value = _mock_cursor(
            fetchone=(
                55, ts, False,
                ["PREVENTIVO", "ORDINE_VENDITA"],
                '{"HandlerPreventivi": {"created": 3}}',
                "COMPLETATO", 1200,
            )
        )
        repo = CommesseRepository()
        result = repo.get_push_log(55)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["id"], 55)
        self.assertEqual(result["stato"], "COMPLETATO")
        self.assertEqual(result["durata_ms"], 1200)
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["source_types"], ["PREVENTIVO", "ORDINE_VENDITA"])
        self.assertIn("HandlerPreventivi", result["risultato"] or {})

    # Scopo: Verifica che get_push_log restituisca None quando il log non esiste.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_get_push_log_returns_none_when_not_found(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=None)
        repo = CommesseRepository()
        result = repo.get_push_log(999)
        self.assertIsNone(result)

    # Scopo: Verifica che fetch_pushable_rows chiami la fn SQL corretta per ogni sorgente.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_fetch_pushable_rows_calls_correct_fn(self, mock_cursor_factory):
        for codice, fn_expected in _SORGENTE_FN_MAP.items():
            cur = _mock_cursor(fetchall=[], description=_ORDINI_COLS)
            mock_cursor_factory.return_value = cur
            repo = CommesseRepository()
            repo.fetch_pushable_rows(codice)
            sql = cur.execute.call_args[0][0]
            self.assertIn(fn_expected, sql, f"fn per {codice} non trovata nel SQL")

    # Scopo: Verifica che sorgente_codice sconosciuto lanci errore.
    def test_fetch_pushable_rows_unknown_sorgente_raises(self):
        # ⛔ `assertRaises(Exception)` accetterebbe QUALUNQUE errore — anche un
        #    TypeError da una firma cambiata sotto, cioe' proprio il difetto che
        #    questo test dovrebbe scoprire. E' la stessa regola gia' scritta per
        #    i pgTAP (`throws_ok(sql, NULL, NULL)` accetta tutto: si passa
        #    sempre lo SQLSTATE): qui si pretendono il TIPO e il CODICE.
        repo = CommesseRepository()
        with self.assertRaises(ServiceError) as ctx:
            repo.fetch_pushable_rows("SCONOSCIUTO")
        self.assertEqual(ctx.exception.code, "E_COMMESSA_SORGENTE_SCONOSCIUTA")

    # Scopo: righe_ids valorizzato su sorgente PREVENTIVO → chiamata fn a 5
    # parametri con p_righe_ids in coda (smistamento selettivo, brief
    # smistamento C). righe_ids=None → resta la chiamata a 4 parametri.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_fetch_pushable_rows_righe_ids_preventivo(self, mock_cursor_factory):
        cur = _mock_cursor(fetchall=[], description=_ORDINI_COLS)
        mock_cursor_factory.return_value = cur
        repo = CommesseRepository()
        repo.fetch_pushable_rows("PREVENTIVO", sorgente_id=42, righe_ids=[7, 9])
        sql, params = cur.execute.call_args[0]
        self.assertIn("%s, %s, %s, %s, %s::bigint[]", sql)
        self.assertEqual(params, [None, None, None, 42, [7, 9]])

    # Scopo: righe_ids su sorgente che non lo supporta (fn a 4 parametri) →
    # errore esplicito, niente chiamata SQL malformata.
    def test_fetch_pushable_rows_righe_ids_sorgente_non_supportata(self):
        repo = CommesseRepository()
        with self.assertRaises(ServiceError) as ctx:
            repo.fetch_pushable_rows(
                "ORDINE_VENDITA", sorgente_id=42, righe_ids=[7],
            )
        # ⚠️ Il codice distingue QUESTO rifiuto da quello del test sopra: senza,
        #    i due test proverebbero la stessa cosa e uno dei due rami potrebbe
        #    sparire senza che nessuno se ne accorga.
        self.assertEqual(ctx.exception.code, "E_COMMESSA_VALIDATION")

    # Scopo: Verifica mapping colonne condivise in PushableRow.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_fetch_pushable_rows_maps_shared_columns(self, mock_cursor_factory):
        cur = _mock_cursor(
            fetchall=[_ORDINI_ROW],
            description=_ORDINI_COLS,
        )
        mock_cursor_factory.return_value = cur
        repo = CommesseRepository()
        rows = repo.fetch_pushable_rows("ORDINE_VENDITA")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIsInstance(row, PushableRow)
        self.assertEqual(row.billing_account_id, 1)
        self.assertEqual(row.utility_id, 2)
        self.assertEqual(row.segment_key, "ORDINE_VENDITA:uid-ordine-001:R:200")
        self.assertIsNone(row.uom_id)
        self.assertEqual(row.quantita, Decimal("10.0"))
        self.assertEqual(row.prezzo_snapshot, Decimal("22.50"))
        self.assertTrue(row.prezzo_bloccato)
        self.assertEqual(row.tipo_doc_fiscale_id, 7)
        self.assertEqual(row.meta["tipo_commessa"], "AUTO")
        # Le condizioni di pagamento del documento devono ATTRAVERSARE il
        # binding: prova di mutazione — togliere i due nomi da
        # `_PUSHABLE_SHARED_COLS` rende rosse queste due righe (e' il difetto
        # reale del 2026-08-03, non un caso ipotetico).
        self.assertEqual(row.termine_pagamento_id, 3)
        self.assertEqual(row.modalita_pagamento_id, 5)
        self.assertIsNone(row.causale_onere_id)

    # Scopo: la causale della riga ONERE attraversa il binding. Prova di
    #        mutazione: togliere `causale_onere_id` da `_PUSHABLE_SHARED_COLS`
    #        la lascia None in silenzio, e la madre rifiuta la riga ONERE
    #        (brief-db-addebito-trasporto-ordine §9.3).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_fetch_pushable_rows_maps_causale_onere(self, mock_cursor_factory):
        riga_onere = _ORDINI_ROW[:24] + ("ONERE",) + _ORDINI_ROW[25:-1] + (6,)
        mock_cursor_factory.return_value = _mock_cursor(
            fetchall=[riga_onere], description=_ORDINI_COLS,
        )
        row = CommesseRepository().fetch_pushable_rows("ORDINE_VENDITA")[0]
        self.assertEqual(row.tipo_movimento, "ONERE")
        self.assertEqual(row.causale_onere_id, 6)

    # Scopo: Verifica validate_sorgente_map senza warning quando DB e map allineati.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_validate_sorgente_map_ok(self, mock_cursor_factory):
        cur = _mock_cursor(fetchall=[
            ("PREVENTIVO",), ("ORDINE_VENDITA",), ("ATTIVITA_CONSUMI",),
            ("CONTRATTO",), ("DDT_VENDITA",),
        ])
        mock_cursor_factory.return_value = cur
        warnings = CommesseRepository.validate_sorgente_map()
        self.assertEqual(warnings, [])

    # Scopo: Verifica warning quando DB ha sorgente non presente nella map.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_validate_sorgente_map_missing_in_map(self, mock_cursor_factory):
        cur = _mock_cursor(fetchall=[
            ("PREVENTIVO",), ("ORDINE_VENDITA",), ("ATTIVITA_CONSUMI",),
            ("CONTRATTO",), ("DDT_VENDITA",), ("NUOVA_SORGENTE",),
        ])
        mock_cursor_factory.return_value = cur
        warnings = CommesseRepository.validate_sorgente_map()
        self.assertEqual(len(warnings), 1)
        self.assertIn("NUOVA_SORGENTE", warnings[0])

    # Scopo: Verifica che list_active_push_sources restituisca codici attivi ordinati per id.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_active_push_sources(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(
            fetchall=[("PREVENTIVO",), ("ORDINE_VENDITA",), ("CONTRATTO",)]
        )
        result = CommesseRepository.list_active_push_sources()
        self.assertEqual(result, ["PREVENTIVO", "ORDINE_VENDITA", "CONTRATTO"])
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("PUSH_COMMESSA", sql)
        self.assertIn("attivo", sql)
        self.assertIn("ORDER BY id", sql)

    # Scopo: Verifica che list_commesse_emittibili chiami la fn DB e restituisca list[int].
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_commesse_emittibili_returns_ids(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchall=[(10,), (20,), (30,)])
        repo = CommesseRepository()
        result = repo.list_commesse_emittibili(
            competenza_mese=date(2026, 6, 1),
            billing_account_id=1,
            utility_id=2,
            emittente_soggetto_ruolo_id=3,
        )
        self.assertEqual(result, [10, 20, 30])
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_list_commesse_emittibili", sql)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        self.assertEqual(params[0], date(2026, 6, 1))
        self.assertEqual(params[1], 1)
        self.assertEqual(params[2], 2)
        self.assertEqual(params[3], 3)
        self.assertIsNone(params[4])  # fatturazione_immediata (default: nessun filtro)
        self.assertEqual(params[5], 1000)  # default limit
        self.assertIn("p_fatturazione_immediata", sql)

    # Scopo: Verifica che list_commesse_emittibili restituisca lista vuota se nessun risultato.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_commesse_emittibili_empty(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchall=[])
        repo = CommesseRepository()
        result = repo.list_commesse_emittibili()
        self.assertEqual(result, [])

    # Scopo: Verifica che list_emittibili_lane mappi le terne (emittente, tipo_doc, utility,
    # competenza, conteggio), incluso il gruppo emittente NULL, passando il filtro corsia.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_emittibili_lane(self, mock_cursor_factory):
        # Colonne nell'ordine della RETURNS TABLE (rev 2026-08-15):
        # (emittente, tipo_doc, utility, competenza, total, gruppi_coperti)
        mock_cursor_factory.return_value = _mock_cursor(fetchall=[
            (5, 3, 9, date(2026, 6, 1), 4, ["PREVENTIVO:aa", "MAN:42"]),
            (5, 7, 9, date(2026, 5, 1), 1, ["ORDINE_VENDITA:bb"]),
            # NULL difensivo sull'array → lista vuota, mai None a valle.
            (None, 3, 9, date(2026, 6, 1), 2, None),
        ])
        repo = CommesseRepository()
        result = repo.list_emittibili_lane(
            competenza_mese=date(2026, 6, 1),
            utility_id=9,
            fatturazione_immediata=True,
        )
        self.assertEqual(result, [
            {"emittente_soggetto_ruolo_id": 5, "tipo_doc_fiscale_id": 3, "utility_id": 9,
             "competenza_mese": date(2026, 6, 1), "total_candidate": 4,
             "gruppi_coperti": ["PREVENTIVO:aa", "MAN:42"]},
            {"emittente_soggetto_ruolo_id": 5, "tipo_doc_fiscale_id": 7, "utility_id": 9,
             "competenza_mese": date(2026, 5, 1), "total_candidate": 1,
             "gruppi_coperti": ["ORDINE_VENDITA:bb"]},
            {"emittente_soggetto_ruolo_id": None, "tipo_doc_fiscale_id": 3, "utility_id": 9,
             "competenza_mese": date(2026, 6, 1), "total_candidate": 2,
             "gruppi_coperti": []},
        ])
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("gruppi_coperti", sql)
        self.assertIn("fn_list_emittibili_lane", sql)
        self.assertIn("utility_id", sql)
        self.assertIn("p_fatturazione_immediata", sql)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        self.assertIs(params[4], True)  # fatturazione_immediata

    # Scopo: Verifica che list_commessa_attivita chiami count + fn DB e mappa le righe in dict.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_commessa_attivita_maps_rows(self, mock_cursor_factory):
        import uuid
        from datetime import datetime
        _art_id = uuid.uuid4()
        _row = (
            100, 1, "SEG:001", _art_id,
            None, date(2026, 2, 1), 5, Decimal("10.00"),
            date(2026, 2, 1), date(2026, 2, 1), date(2026, 2, 28),
            Decimal("22.50"), True, False,
            "APPROVATA", "NON_EMESSA", 3,
            "PREVENTIVO", {"note": "test"}, datetime(2026, 2, 26, 10, 0, 0, tzinfo=UTC),
            True,  # fatturata (in coda, changeset 20260724-07)
            # Sette colonne del changeSet 20260816-04, nell'ordine della
            # RETURNS TABLE. ⚠️ `fatturata_il` e' un istante DIVERSO dal
            # `data_update` qui sopra, ed e' il punto della colonna: e'
            # `fatture_righe.data_insert`, che nessuna modifica successiva
            # all'attivita' puo' spostare.
            datetime(2026, 3, 2, 9, 30, 0, tzinfo=UTC),      # fatturata_il
            77, 210, "DEFINITIVA",               # fattura_id, _numero, _stato
            "019fc716-7386-7b0d-9c26-0a4d30f3a022",  # sorgente_uid
            True, 100,                           # sorgente_apribile, _documento_id
            # Cinque colonne del changeSet 20260820-05, in coda alla RETURNS
            # TABLE: la riga dice COSA e' e DA DOVE VIENE.
            "NORMALE",                           # tipo_movimento
            "ART001", "Articolo di prova",       # articolo_codice, _descrizione
            "ORD0000227",                        # sorgente_documento_numero
            "ORDINE_VENDITA:019fc716-7386-7b0d-9c26-0a4d30f3a022",  # gruppo_key
            "Ordine",                            # sorgente_etichetta (20261021-20)
        )
        # Due execute: 1) COUNT → fetchone, 2) data → fetchall.
        mock_cursor_factory.return_value = _mock_cursor(
            fetchone=(5,), fetchall=[_row],
        )
        repo = CommesseRepository()
        result = repo.list_commessa_attivita(
            1, stato_emissione="NON_EMESSA", limit=50, offset=0,
            order_by="data_attivita", order_dir="desc",
        )
        self.assertEqual(result["count"], 5)  # total count, non len(rows)
        row = result["results"][0]
        self.assertEqual(row["id"], 100)
        self.assertEqual(row["segment_key"], "SEG:001")
        self.assertEqual(row["articolo_id"], str(_art_id))
        # Le cinque colonne nuove arrivano al posto giusto: la mappatura e'
        # POSIZIONALE su `_ATTIVITA_COLS`, quindi un ordine sbagliato non
        # solleverebbe — scriverebbe il valore di una colonna dentro un'altra.
        self.assertEqual(row["tipo_movimento"], "NORMALE")
        self.assertEqual(row["articolo_codice"], "ART001")
        self.assertEqual(row["articolo_descrizione"], "Articolo di prova")
        self.assertEqual(row["sorgente_documento_numero"], "ORD0000227")
        self.assertEqual(
            row["gruppo_key"],
            "ORDINE_VENDITA:019fc716-7386-7b0d-9c26-0a4d30f3a022",
        )
        self.assertEqual(row["stato_emissione"], "NON_EMESSA")
        self.assertEqual(row["meta"], {"note": "test"})
        self.assertIs(row["fatturata"], True)  # colonna in coda (20260724-07)
        # Sette colonne del 20260816-04: quando, quale fattura, quale sorgente.
        # `fatturata_il` serializzata come le altre date (isoformat) e DISTINTA
        # da `data_update`: se un giorno qualcuno la ricablasse su quest'ultima
        # il test lo direbbe, che e' l'unico modo di accorgersene.
        self.assertEqual(row["fatturata_il"], "2026-03-02T09:30:00+00:00")
        self.assertNotEqual(row["fatturata_il"], row["data_update"])
        self.assertEqual(row["fattura_id"], 77)
        self.assertEqual(row["fattura_numero"], 210)
        self.assertEqual(row["fattura_stato"], "DEFINITIVA")
        self.assertIs(row["sorgente_apribile"], True)
        self.assertEqual(row["sorgente_documento_id"], 100)
        # §13.6 (20261021-20): il codice IMMUTABILE della sorgente, e l'etichetta
        # in coda — posizionale, come le altre.
        self.assertEqual(row["sorgente_codice_interno"], "PREVENTIVO")
        self.assertNotIn("sorgente_codice", row)
        self.assertEqual(row["sorgente_etichetta"], "Ordine")
        # Seconda execute (data query) contiene fn_list_commessa_attivita.
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_list_commessa_attivita", sql)
        self.assertIn("p_order_by", sql)
        self.assertIn("p_order_dir", sql)
        params = mock_cursor_factory.return_value.execute.call_args[0][1]
        self.assertEqual(params[0], 1)  # commessa_id
        self.assertEqual(params[1], "NON_EMESSA")  # stato_emissione
        self.assertEqual(params[6], "data_attivita")  # order_by → p_order_by
        self.assertEqual(params[7], "desc")  # order_dir → p_order_dir
        # Prima execute (count query) verifica.
        count_sql = mock_cursor_factory.return_value.execute.call_args_list[0][0][0]
        self.assertIn("COUNT(*)", count_sql)

    # Scopo: Verifica che list_commessa_attivita restituisca count=0 se nessun risultato.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_list_commessa_attivita_empty(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(
            fetchone=(0,), fetchall=[],
        )
        repo = CommesseRepository()
        result = repo.list_commessa_attivita(1)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["results"], [])

    # Scopo: Verifica mapping BatchUpsertResult da fn_batch_upsert_commessa_attivita.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_batch_upsert_attivita_maps_result(self, mock_cursor_factory):
        errors_json = '[{"index": 0, "segment_key": "SEG:001", "error": "duplicate"}]'
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(3, 2, 1, errors_json))
        repo = CommesseRepository()
        inp = CommessaAttivitaInput(
            commessa_id=10, segment_key="SEG:001",
            quantita=Decimal("1"), competenza_mese=date(2026, 6, 1),
            articolo_id=None, prezzo_snapshot=None,
        )
        result = repo.batch_upsert_attivita([inp])
        self.assertIsInstance(result, BatchUpsertResult)
        self.assertEqual(result.total_rows, 3)
        self.assertEqual(result.inserted, 2)
        self.assertEqual(result.updated, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0]["segment_key"], "SEG:001")
        sql = mock_cursor_factory.return_value.execute.call_args[0][0]
        self.assertIn("fn_batch_upsert_commessa_attivita", sql)

    # Scopo: Verifica che batch_upsert con lista vuota non chiami il DB.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_batch_upsert_attivita_empty_list(self, mock_cursor_factory):
        repo = CommesseRepository()
        result = repo.batch_upsert_attivita([])
        self.assertEqual(result.total_rows, 0)
        self.assertEqual(result.inserted, 0)
        self.assertEqual(result.updated, 0)
        self.assertEqual(result.errors, [])
        mock_cursor_factory.return_value.execute.assert_not_called()

    # Scopo: F2-BE-11 — upsert_attivita passa i 7 parametri snapshot pricing v5
    #        alla fn DB (posizionali nell'ordine della firma).
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_upsert_attivita_passes_snapshot_v5_params(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchone=(55, True))
        repo = CommesseRepository()
        inp = CommessaAttivitaInput(
            commessa_id=1,
            segment_key="seg",
            quantita=Decimal("1"),
            competenza_mese=date(2026, 6, 1),
            articolo_id=None,
            prezzo_snapshot=Decimal("30"),
            prezzo_base_snapshot=Decimal("25"),
            origine_prezzo="CONTRATTO_LISTINO",
            tipo_variazione_applicata="PERCENTUALE",
            valore_variazione_applicata=Decimal("20"),
            promo_id=None,
            contratto_id=99,
            categoria_cliente_id_snapshot=3,
            classe_utenza_id_snapshot=None,
        )
        repo.upsert_attivita(inp)
        sql, params = mock_cursor_factory.return_value.execute.call_args[0]
        self.assertIn("p_prezzo_base_snapshot", sql)
        self.assertIn("p_origine_prezzo", sql)
        self.assertIn("p_tipo_variazione_applicata", sql)
        self.assertIn("p_valore_variazione_applicata", sql)
        self.assertIn("p_promo_id", sql)
        self.assertIn("p_contratto_id", sql)
        self.assertIn("p_categoria_cliente_id_snapshot", sql)
        self.assertIn("p_classe_utenza_id_snapshot", sql)
        self.assertIn(Decimal("25"), params)
        self.assertIn("CONTRATTO_LISTINO", params)
        self.assertIn(99, params)
        self.assertIn(3, params)

    # Scopo: F2-BE-11 — _inp_to_jsonb_row serializza le 8 chiavi snapshot
    #        pricing v5 (dipendenza: wrapper batch DB deve estrarle).
    def test_inp_to_jsonb_row_includes_snapshot_v5_keys(self):
        inp = CommessaAttivitaInput(
            commessa_id=1,
            segment_key="seg",
            quantita=Decimal("1"),
            competenza_mese=date(2026, 6, 1),
            articolo_id=None,
            prezzo_snapshot=Decimal("30"),
            prezzo_base_snapshot=Decimal("25.0000"),
            origine_prezzo="PROMO",
            tipo_variazione_applicata="VALORE_FISSO",
            valore_variazione_applicata=Decimal("5"),
            promo_id=7,
            contratto_id=None,
            categoria_cliente_id_snapshot=None,
            classe_utenza_id_snapshot=4,
            listino_riga_id=301,
        )
        row = CommesseRepository._inp_to_jsonb_row(inp)
        self.assertEqual(row["prezzo_base_snapshot"], "25.0000")
        self.assertEqual(row["origine_prezzo"], "PROMO")
        self.assertEqual(row["tipo_variazione_applicata"], "VALORE_FISSO")
        self.assertEqual(row["valore_variazione_applicata"], "5")
        self.assertEqual(row["promo_id"], 7)
        self.assertIsNone(row["contratto_id"])
        self.assertIsNone(row["categoria_cliente_id_snapshot"])
        self.assertEqual(row["classe_utenza_id_snapshot"], 4)
        # La chiave che il batch passa a `p_listino_riga_id` (2026-10-09).
        self.assertEqual(row["listino_riga_id"], 301)
        # Riga non ONERE: la causale viaggia come null esplicito.
        self.assertIsNone(row["causale_onere_id"])

    # Scopo: la causale dell'onere arriva al wrapper batch, che dal 20261103-49
    #        la passa a `p_causale_onere_id`. E' il percorso del push.
    def test_inp_to_jsonb_row_porta_la_causale_onere(self):
        inp = CommessaAttivitaInput(
            commessa_id=1, segment_key="seg", quantita=Decimal("1"),
            competenza_mese=date(2026, 6, 1), articolo_id=None,
            prezzo_snapshot=Decimal("30"), tipo_movimento="ONERE",
            causale_onere_id=6,
        )
        row = CommesseRepository._inp_to_jsonb_row(inp)
        self.assertEqual(row["tipo_movimento"], "ONERE")
        self.assertEqual(row["causale_onere_id"], 6)


class DiagnosticaGruppiTernePronteTests(TestCase):
    """`terne_pronte` è jsonb, e su questa connessione arriva come STRINGA.

    Difetto misurato sul DB vero il 2026-08-16: scritto `list(valore or [])`
    la stringa `'[]'` diventa `['[', ']']` — due elementi finti dove il DB
    diceva «nessuna corsia». I test con mock non potevano vederlo, perché un
    mock consegna già una lista: per questo il caso stringa è asserito qui
    esplicitamente.
    """

    _COLS = (
        "ORDINE_VENDITA:aa", 1, "CMM-1", "BOZZA", "Bozza", False,
        5, 0, 0, 0, 0, 0, 5,
    )

    # Scopo: il caso reale — jsonb consegnato come stringa JSON: va decodificato.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_terne_pronte_stringa_json_viene_decodificata(self, mock_cursor_factory):
        corsia = '[{"emittente_soggetto_ruolo_id": 3, "tipo_doc_fiscale_id": 1, "utility_id": 9}]'
        mock_cursor_factory.return_value = _mock_cursor(
            fetchall=[(*self._COLS, corsia)],
        )
        righe = CommesseRepository().diagnostica_gruppi(gruppi=["ORDINE_VENDITA:aa"])
        self.assertEqual(
            righe[0]["terne_pronte"],
            [{"emittente_soggetto_ruolo_id": 3, "tipo_doc_fiscale_id": 1,
              "utility_id": 9}],
        )

    # Scopo: il caso che produceva `['[', ']']` — `'[]'` deve dare lista VUOTA.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_terne_pronte_vuote_restano_lista_vuota(self, mock_cursor_factory):
        mock_cursor_factory.return_value = _mock_cursor(fetchall=[(*self._COLS, "[]")])
        righe = CommesseRepository().diagnostica_gruppi(gruppi=["ORDINE_VENDITA:aa"])
        self.assertEqual(righe[0]["terne_pronte"], [])

    # Scopo: se un giorno la connessione decodificasse da se', il valore passa intatto.
    @patch("apps.vendite.db.commesse_repository.connection.cursor")
    def test_terne_pronte_gia_lista_passa_intatta(self, mock_cursor_factory):
        gia = [{"emittente_soggetto_ruolo_id": 3, "tipo_doc_fiscale_id": 1,
                "utility_id": 9}]
        mock_cursor_factory.return_value = _mock_cursor(fetchall=[(*self._COLS, gia)])
        righe = CommesseRepository().diagnostica_gruppi(gruppi=["ORDINE_VENDITA:aa"])
        self.assertEqual(righe[0]["terne_pronte"], gia)
