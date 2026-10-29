# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari funzioni listini_service.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) ListiniServiceTests.test_list_listini_invalid_order_by
2) ListiniServiceTests.test_get_listino_dettaglio_nests_children
3) ListiniServiceTests.test_create_listino_duplicate_code
4) ListiniServiceTests.test_get_versione_not_found
5) ListiniServiceTests.test_change_versione_state_solo_attivazione
6) ListiniServiceTests.test_change_versione_state_dry_run_stringa_400
7) ListiniServiceTests.test_create_riga_invalid_articolo_uom
8) ListiniServiceTests.test_test_resolver_requires_uom
9) ListiniServiceTests.test_create_riga_blocked_on_versione_attiva
10) ListiniServiceTests.test_update_riga_blocked_on_versione_chiusa
11) ListiniServiceTests.test_delete_riga_blocked_on_versione_attiva
13) ListiniServiceTests.test_update_versione_attiva_fine_rifiutata_dal_db
14) ListiniServiceTests.test_update_versione_regole_per_stato_del_db
15) ListiniServiceTests.test_clone_versione_d2_dal_db
16) ListiniServiceTests.test_clone_versione_dal_verbo
17) ListiniServiceTests.test_clone_versione_rifiuta_meta_attivo
18) ListiniServiceTests.test_change_state_dry_run_no_db_writes
18bis) ListiniServiceTests.test_change_state_dry_run_rifiuta_come_il_verbo
18ter) ListiniServiceTests.test_change_state_errore_db_senza_codice_resta_tecnico
19) ListiniServiceTests.test_change_state_attiva_dal_verbo
21) ListiniServiceTests.test_delete_versione_bozza_ok
22) ListiniServiceTests.test_delete_versione_regola_del_db
22bis) ListiniServiceTests.test_programma_chiusura_dal_verbo
22ter) ListiniServiceTests.test_programma_chiusura_corpo
22quater) ListiniServiceTests.test_programma_chiusura_rifiuto_del_db
24) ListiniServiceTests.test_delete_listino_orphan_ok
25) ListiniServiceTests.test_delete_listino_with_versioni_rejected
26) ListiniServiceTests.test_delete_listino_with_associazioni_rejected
28) ListiniServiceTests.test_variazione_pct_su_attiva_rifiutata
29) ListiniServiceTests.test_variazione_pct_su_chiusa_rifiutata
30) ListiniServiceTests.test_variazione_pct_fuori_range_alto_rifiutata
31) ListiniServiceTests.test_variazione_pct_meno_100_rifiutata
32) ListiniServiceTests.test_variazione_pct_dry_run_preview
33) ListiniServiceTests.test_variazione_pct_applica_ok
34) ListiniServiceTests.test_variazione_pct_con_filtro_articoli
35) ListiniServiceTests.test_variazione_pct_campo_obbligatorio_mancante
36) ListiniServiceTests.test_variazione_pct_arrotondamento_fuori_range
37) ListiniServiceTests.test_alert_scadenze_default_giorni
38) ListiniServiceTests.test_alert_scadenze_giorni_fuori_range
39) ListiniServiceTests.test_rettifica_controllata_su_bozza_rifiutata
40) ListiniServiceTests.test_rettifica_controllata_riga_propagata_rifiutata
41) ListiniServiceTests.test_rettifica_controllata_ok_non_propagata
42) ListiniServiceTests.test_rettifica_controllata_senza_motivo_rifiutata
42bis) ListiniServiceTests.test_rettifica_controllata_su_versione_scaduta_rifiutata
43) ListiniServiceTests.test_create_listino_missing_utility_id
44) ListiniServiceTests.test_create_listino_missing_tipologia_id
45) ListiniServiceTests.test_create_listino_invalid_tipologia_fk
46) ListiniServiceTests.test_update_listino_accepts_tipologia_id
47) ListiniServiceTests.test_list_listini_tipologia_id_invalid
48) ListiniServiceTests.test_list_listini_propaga_tipologia_id
49) ListiniServiceTests.test_list_tipologie_per_utility_invalid
50) ListiniServiceTests.test_list_tipologie_per_utility_ok
51) ListiniServiceTests.test_create_listino_tipologia_id_non_numeric
52) ListiniServiceTests.test_create_listino_tipologia_id_zero
53) ListiniServiceTests.test_create_listino_utility_id_bool
54) ListiniServiceTests.test_update_listino_tipologia_id_null
55) ListiniServiceTests.test_update_listino_empty_payload
56) ListiniServiceTests.test_translate_integrity_fk_tipologia
57) ListiniServiceTests.test_translate_integrity_fk_listrighe_comp_temporal
"""

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from django.db import DatabaseError, IntegrityError

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_error_fakes import make_db_error


class ListiniServiceTests(TestCase):
    # Scopo: Verifica validazione sort_by non ammesso.
    def test_list_listini_invalid_order_by(self):
        from apps.vendite.services.listini_service import fn_list_listini

        with self.assertRaises(ServiceError) as ctx:
            fn_list_listini(order_by="invalid")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica che il dettaglio listino includa versioni nidificate.
    #        F2-BE-13: rimosso il campo `associazioni` (tabella eliminata).
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_get_listino_dettaglio_nests_children(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_get_listino_dettaglio

        repo = mock_repo_cls.return_value
        repo.get_listino.return_value = {"id": 10, "codice": "LIST-UTILITY"}
        repo.list_versioni.return_value = [{"id": 101}]

        result = fn_get_listino_dettaglio(10)

        self.assertEqual(result["versioni"], [{"id": 101}])
        self.assertNotIn("associazioni", result)

    # Scopo: Verifica traduzione duplicate code su create listino.
    #        UNIQUE constraint → E_VENDITE_DUPLICATO (HTTP 409) via
    #        map_integrity_error.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_create_listino_duplicate_code(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_create_listino

        mock_repo_cls.return_value.create_listino.side_effect = IntegrityError(
            'duplicate key value violates unique constraint "uq_listini_codice"'
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_create_listino(
                {
                    "codice": "LIST-UTILITY",
                    "descrizione": "Listino Utility Base",
                    "utility_id": 1,
                    "tipologia_id": 1,
                    "emittente_soggetto_ruolo_id": 1,
                }
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_DUPLICATO")

    # Scopo: Verifica che create_listino richieda utility_id.
    def test_create_listino_missing_utility_id(self):
        from apps.vendite.services.listini_service import fn_create_listino

        with self.assertRaises(ServiceError) as ctx:
            fn_create_listino(
                {"codice": "LIST-X", "descrizione": "X", "tipologia_id": 1}
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica che create_listino richieda tipologia_id.
    def test_create_listino_missing_tipologia_id(self):
        from apps.vendite.services.listini_service import fn_create_listino

        with self.assertRaises(ServiceError) as ctx:
            fn_create_listino(
                {"codice": "LIST-X", "descrizione": "X", "utility_id": 1}
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica traduzione FK tipologia non valida dal DB.
    #        FK constraint → E_VENDITE_FK (HTTP 400) via map_integrity_error.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_create_listino_invalid_tipologia_fk(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_create_listino

        mock_repo_cls.return_value.create_listino.side_effect = IntegrityError(
            'insert or update on table "listini" violates foreign key constraint '
            '"listini_tipologia_id_fkey"'
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_create_listino(
                {
                    "codice": "LIST-X",
                    "descrizione": "X",
                    "utility_id": 1,
                    "tipologia_id": 999,
                    "emittente_soggetto_ruolo_id": 1,
                }
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_FK")

    # Scopo: Verifica update listino accetta tipologia_id (passaggio al repository).
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_update_listino_accepts_tipologia_id(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_update_listino

        repo = mock_repo_cls.return_value
        repo.update_listino.return_value = True
        repo.get_listino.return_value = {"id": 10, "codice": "L", "tipologia_id": 2}
        repo.list_versioni.return_value = []
        repo.list_associazioni.return_value = []

        fn_update_listino(10, {"tipologia_id": 2})

        repo.update_listino.assert_called_once()
        _, call_data = repo.update_listino.call_args[0]
        self.assertEqual(call_data.get("tipologia_id"), 2)

    # Scopo: Verifica che list_listini con tipologia_id invalido (<=0) lanci errore.
    def test_list_listini_tipologia_id_invalid(self):
        from apps.vendite.services.listini_service import fn_list_listini

        with self.assertRaises(ServiceError) as ctx:
            fn_list_listini(tipologia_id=0)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica che list_listini propaghi tipologia_id al repository.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_list_listini_propaga_tipologia_id(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_list_listini

        repo = mock_repo_cls.return_value
        repo.list_listini.return_value = ([], 0)

        fn_list_listini(tipologia_id=3)

        repo.list_listini.assert_called_once()
        kwargs = repo.list_listini.call_args.kwargs
        self.assertEqual(kwargs["tipologia_id"], 3)

    # Scopo: Verifica endpoint service tipologie-per-utility rifiuta utility_id invalido.
    def test_list_tipologie_per_utility_invalid(self):
        from apps.vendite.services.listini_service import fn_list_tipologie_per_utility

        with self.assertRaises(ServiceError) as ctx:
            fn_list_tipologie_per_utility(0)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica che fn_list_tipologie_per_utility chiami il repository.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_list_tipologie_per_utility_ok(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_list_tipologie_per_utility

        repo = mock_repo_cls.return_value
        repo.list_tipologie_per_utility.return_value = [
            {"id": 1, "codice": "CONSUMO", "descrizione": "Consumi"},
        ]

        result = fn_list_tipologie_per_utility(1)

        repo.list_tipologie_per_utility.assert_called_once_with(1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["codice"], "CONSUMO")

    # Scopo: Verifica che create_listino rifiuti tipologia_id non numerico con
    #        ServiceError E_VENDITE_VALIDATION (anziche' ValueError grezzo).
    def test_create_listino_tipologia_id_non_numeric(self):
        from apps.vendite.services.listini_service import fn_create_listino

        with self.assertRaises(ServiceError) as ctx:
            fn_create_listino(
                {
                    "codice": "L",
                    "descrizione": "X",
                    "utility_id": 1,
                    "tipologia_id": "abc",
                }
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica che create_listino rifiuti tipologia_id = 0 (non positivo).
    def test_create_listino_tipologia_id_zero(self):
        from apps.vendite.services.listini_service import fn_create_listino

        with self.assertRaises(ServiceError) as ctx:
            fn_create_listino(
                {
                    "codice": "L",
                    "descrizione": "X",
                    "utility_id": 1,
                    "tipologia_id": 0,
                }
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica che create_listino rifiuti utility_id bool (true/false).
    def test_create_listino_utility_id_bool(self):
        from apps.vendite.services.listini_service import fn_create_listino

        with self.assertRaises(ServiceError) as ctx:
            fn_create_listino(
                {
                    "codice": "L",
                    "descrizione": "X",
                    "utility_id": True,
                    "tipologia_id": 1,
                }
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica update rifiuta tipologia_id = None esplicito (non-nullable).
    def test_update_listino_tipologia_id_null(self):
        from apps.vendite.services.listini_service import fn_update_listino

        with self.assertRaises(ServiceError) as ctx:
            fn_update_listino(10, {"tipologia_id": None})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Verifica update con payload vuoto solleva E_VENDITE_VALIDATION
    #        invece di bubble-up generico.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_update_listino_empty_payload(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_update_listino

        with self.assertRaises(ServiceError) as ctx:
            fn_update_listino(10, {})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        mock_repo_cls.return_value.update_listino.assert_not_called()

    # Scopo: Verifica traduzione FK tipologia in messaggio applicativo.
    #        FK constraint → E_VENDITE_FK (HTTP 400) via map_integrity_error.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_translate_integrity_fk_tipologia(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_create_listino

        mock_repo_cls.return_value.create_listino.side_effect = IntegrityError(
            'insert or update on table "listini" violates foreign key constraint '
            '"listini_tipologia_id_fkey"'
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_create_listino(
                {
                    "codice": "L",
                    "descrizione": "X",
                    "utility_id": 1,
                    "tipologia_id": 999,
                    "emittente_soggetto_ruolo_id": 1,
                }
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_FK")
        self.assertIn("tipologia", (ctx.exception.message or "").lower())

    # Scopo: Verifica not found su dettaglio versione.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_get_versione_not_found(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_get_versione

        mock_repo_cls.return_value.get_versione.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            fn_get_versione(10, 101)
        self.assertEqual(ctx.exception.code, "E_VENDITE_LISTINO_VERSIONE_NOT_FOUND")

    # Scopo: Da qui si chiede solo l'attivazione, l'unico passaggio manuale
    #        della matrice (giro 12): la chiusura si programma con «Chiudi»
    #        (rotta `chiusura/`, §16.16) e la scrive il job. Il 400 e' sul campo, e il verbo non si chiama.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_change_versione_state_solo_attivazione(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_change_versione_state

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "ATTIVA"}

        with self.assertRaises(ServiceError) as ctx:
            fn_change_versione_state(10, 101, {"stato": "CHIUSA"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "stato")
        self.assertIn("chiusura/", ctx.exception.detail or "")
        repo.attiva_versione.assert_not_called()

    # Scopo: ⛔ `dry_run` e' un booleano JSON: la stringa `"true"` e' un 400 sul
    #        campo, non un `false` muto che eseguiva davvero il cambio stato a
    #        chi chiedeva l'anteprima (2026-10-21, §B4 del brief-be-verifica-
    #        documentazione-api).
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_change_versione_state_dry_run_stringa_400(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_change_versione_state

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101, "listino_id": 10, "stato": "BOZZA", "attivo": True,
        }
        with self.assertRaises(ServiceError) as ctx:
            fn_change_versione_state(10, 101, {"stato": "ATTIVA", "dry_run": "true"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        repo.attiva_versione.assert_not_called()

    # Scopo: Verifica blocco riga con articolo/UoM non coerenti.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_create_riga_invalid_articolo_uom(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_create_riga

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "BOZZA"}
        repo.get_articolo_uom_validation.return_value = {
            "articolo_attivo": True,
            "uom_attiva": True,
            "uom_compatibile": False,
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_create_riga(
                10,
                101,
                {
                    "articolo_id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                    "uom_id": 1,
                    "prezzo": "12.50",
                },
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: F1 - create_riga deve fallire se la versione non e' BOZZA.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_create_riga_blocked_on_versione_attiva(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_create_riga

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "ATTIVA"}

        with self.assertRaises(ServiceError) as ctx:
            fn_create_riga(
                10,
                101,
                {
                    "articolo_id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                    "uom_id": 1,
                    "prezzo": "12.50",
                },
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("BOZZA", ctx.exception.detail or "")
        # Verifica che la guard scatti PRIMA di toccare create_riga
        repo.create_riga.assert_not_called()

    # Scopo: F1 - update_riga deve fallire se la versione e' CHIUSA.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_update_riga_blocked_on_versione_chiusa(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_update_riga

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "CHIUSA"}

        with self.assertRaises(ServiceError) as ctx:
            fn_update_riga(10, 101, 555, {"prezzo": "9.99"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("CHIUSA", ctx.exception.detail or "")
        repo.update_riga.assert_not_called()

    # Scopo: F1 - delete_riga deve fallire se la versione e' ATTIVA.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_delete_riga_blocked_on_versione_attiva(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_delete_riga

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "ATTIVA"}

        with self.assertRaises(ServiceError) as ctx:
            fn_delete_riga(10, 101, 555)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        repo.delete_riga.assert_not_called()

    # Scopo: ⛔ La fine di una ATTIVA dal PATCH la rifiuta il DB (C-4 = a,
    #        §16.15: E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO, si passa da
    #        «Chiudi»): il service non aggiunge una regola di stato, trasporta
    #        il rifiuto col suo codice.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_update_versione_attiva_fine_rifiutata_dal_db(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_update_versione

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "ATTIVA"}
        repo.update_versione.side_effect = make_db_error(
            "La fine si cambia solo dal verbo.", codice="E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO",
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_update_versione(10, 101, {"valido_al": "2026-12-31"})
        self.assertEqual(ctx.exception.code, "E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO")
        repo.update_versione.assert_called_once()

    # Scopo: ⛔ Quali campi si cambiano in quale stato lo dice il DB (L-5,
    #        giro 12, E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE): il service non
    #        filtra per stato, passa la scrittura. Presidio contro il ritorno
    #        della copia (`_VERSIONE_PATCH_ALLOWED_BY_STATE`, ritirata).
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_update_versione_regole_per_stato_del_db(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_update_versione

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "CHIUSA"}
        repo.update_versione.return_value = True

        fn_update_versione(10, 101, {"codice_versione": "V001-bis"})

        repo.update_versione.assert_called_once_with(10, 101, {"codice_versione": "V001-bis"})

    # Scopo: ⛔ D2 la dice il verbo del DB (§16.16, BE-C1): il rifiuto arriva
    #        col suo codice (E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE); il
    #        service non confronta le decorrenze. Presidio contro il ritorno
    #        della copia (era `E_VENDITE_VALIDATION`).
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_clone_versione_d2_dal_db(self, mock_repo_cls, mock_atomic):
        del mock_atomic
        from apps.vendite.services.listini_service import fn_clone_versione

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101, "listino_id": 10, "stato": "ATTIVA", "valido_dal": date(2026, 4, 1),
        }
        repo.clone_versione.side_effect = make_db_error(
            "La copia comincia prima della sorgente.",
            codice="E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE",
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_clone_versione(10, 101, {"codice_versione": "V002", "valido_dal": "2026-03-31"})
        self.assertEqual(ctx.exception.code, "E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE")
        repo.clone_versione.assert_called_once()

    # Scopo: Il clone e' il verbo (da qualunque stato, C-1 = a: qui da una
    #        BOZZA), in una transazione; la risposta e' il dettaglio della
    #        versione nuova con i conteggi della copia.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_clone_versione_dal_verbo(self, mock_repo_cls, mock_atomic):
        from apps.vendite.services.listini_service import fn_clone_versione

        repo = mock_repo_cls.return_value
        # get_versione viene chiamata 2 volte: prima per sorgente, poi per dettaglio target
        repo.get_versione.side_effect = [
            {"id": 101, "listino_id": 10, "stato": "BOZZA", "valido_dal": date(2026, 1, 1)},
            {"id": 202, "listino_id": 10, "stato": "BOZZA", "codice_versione": "V002"},
        ]
        repo.clone_versione.return_value = {
            "versione_id": 202, "righe_copiate": 3, "componenti_copiati": 2, "componenti_saltati": 1,
        }

        result = fn_clone_versione(10, 101, {"codice_versione": "V002", "valido_dal": "2026-02-15"})

        self.assertEqual(result["id"], 202)
        self.assertEqual(
            (result["righe_copiate"], result["componenti_copiati"], result["componenti_saltati"]),
            (3, 2, 1),
        )
        mock_atomic.assert_called_once()
        repo.clone_versione.assert_called_once_with(
            101, codice_versione="V002", valido_dal=date(2026, 2, 15), valido_al=None,
        )
        self.assertEqual(repo.get_versione.call_args_list[1].args, (10, 202))

    # Scopo: D3 - dry_run passa dall'anteprima del repository (il verbo in un
    #        savepoint annullato) e restituisce le versioni che verrebbero
    #        chiuse, dal lettore del DB (lo stesso del verbo), nella forma che il
    #        dialogo legge. L'attivazione vera non si chiama.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_change_state_dry_run_no_db_writes(self, mock_repo_cls, mock_atomic):
        from apps.vendite.services.listini_service import fn_change_versione_state

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 202, "listino_id": 10, "stato": "BOZZA"}
        repo.anteprima_attivazione.return_value = [
            {
                "versione_id": 101,
                "codice_versione": "V001",
                "valido_dal": date(2026, 1, 1),
                "valido_al_prima": None,
                "valido_al_dopo": date(2026, 3, 31),
            },
        ]

        result = fn_change_versione_state(10, 202, {"stato": "ATTIVA", "dry_run": True})

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["nuovo_stato"], "ATTIVA")
        self.assertEqual(result["auto_close"], [{
            "id": 101,
            "codice_versione": "V001",
            "valido_dal": date(2026, 1, 1),
            "valido_al_prima": None,
            "valido_al_dopo": date(2026, 3, 31),
        }])
        repo.anteprima_attivazione.assert_called_once_with(202)
        # Niente scritture DB
        repo.attiva_versione.assert_not_called()
        mock_atomic.assert_not_called()

    # Scopo: L'anteprima rifiuta come il gesto: il rifiuto del verbo (qui la
    #        versione senza prezzi) arriva col codice del DB, non un elenco di
    #        versioni da chiudere per un'attivazione che non si farebbe.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_change_state_dry_run_rifiuta_come_il_verbo(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_change_versione_state

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 202, "listino_id": 10, "stato": "BOZZA"}
        repo.anteprima_attivazione.side_effect = make_db_error(
            "La versione non ha prezzi.", codice="E_LISTINO_VERSIONE_SENZA_RIGHE",
        )
        with self.assertRaises(ServiceError) as ctx:
            fn_change_versione_state(10, 202, {"stato": "ATTIVA", "dry_run": True})
        self.assertEqual(ctx.exception.code, "E_LISTINO_VERSIONE_SENZA_RIGHE")

    # Scopo: ⛔ Un errore del DB SENZA codice del catalogo (deadlock, timeout)
    #        non diventa un 400 «dato errato»: torna com'e' al middleware.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_change_state_errore_db_senza_codice_resta_tecnico(self, mock_repo_cls, mock_atomic):
        from apps.vendite.services.listini_service import fn_change_versione_state

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 202, "listino_id": 10, "stato": "BOZZA"}
        errore = make_db_error("deadlock detected", codice=None)
        repo.attiva_versione.side_effect = errore
        with self.assertRaises(DatabaseError) as ctx:
            fn_change_versione_state(10, 202, {"stato": "ATTIVA"})
        self.assertIs(ctx.exception, errore)

    # Scopo: D3 - l'attivazione reale e' il verbo del DB, in una transazione
    #        (chiusura delle precedenti e stato li fa lui), e la risposta e' il
    #        dettaglio riletto.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_change_state_attiva_dal_verbo(self, mock_repo_cls, mock_atomic):
        from apps.vendite.services.listini_service import fn_change_versione_state

        repo = mock_repo_cls.return_value
        repo.get_versione.side_effect = [
            {"id": 202, "listino_id": 10, "stato": "BOZZA"},
            {"id": 202, "listino_id": 10, "stato": "ATTIVA"},
        ]

        result = fn_change_versione_state(10, 202, {"stato": "ATTIVA"})

        self.assertEqual(result["stato"], "ATTIVA")
        repo.attiva_versione.assert_called_once_with(202)
        mock_atomic.assert_called_once()

    # Scopo: O1 - meta e attivo non si clonano: nel payload sono un 400, non
    #        valori ignorati in silenzio; il verbo non si chiama.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_clone_versione_rifiuta_meta_attivo(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_clone_versione

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "valido_dal": date(2026, 1, 1)}
        for chiave, valore in (("meta", {"note": "x"}), ("attivo", False)):
            corpo = {"codice_versione": "V003", "valido_dal": "2026-06-01", chiave: valore}
            with self.subTest(chiave=chiave), self.assertRaises(ServiceError) as ctx:
                fn_clone_versione(10, 101, corpo)
            self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        repo.clone_versione.assert_not_called()

    # Scopo: O2 - l'eliminazione e' il verbo del DB (§16.13, BE-E1), in una
    #        transazione: la risposta porta quante righe e componenti ha tolto.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_delete_versione_bozza_ok(self, mock_repo_cls, mock_atomic):
        from apps.vendite.services.listini_service import fn_delete_versione

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "BOZZA"}
        repo.delete_versione.return_value = {
            "versione_id": 101, "righe_eliminate": 3, "componenti_eliminati": 8,
        }

        result = fn_delete_versione(10, 101)

        self.assertEqual(
            result, {"deleted": True, "id": 101, "righe_eliminate": 3, "componenti_eliminati": 8},
        )
        repo.delete_versione.assert_called_once_with(101)
        mock_atomic.assert_called_once()

    # Scopo: O2 - si elimina solo una BOZZA non citata, ma lo dice il verbo
    #        (E_LISTINO_VERSIONE_NON_ELIMINABILE, E_LISTINO_VERSIONE_CITATA): il
    #        service non filtra per stato e trasporta il codice. Presidio
    #        contro il ritorno della copia.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_delete_versione_regola_del_db(self, mock_repo_cls, mock_atomic):
        del mock_atomic
        from apps.vendite.services.listini_service import fn_delete_versione

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "BOZZA"}
        repo.delete_versione.side_effect = make_db_error(
            "La versione e' usata da altri documenti.", codice="E_LISTINO_VERSIONE_CITATA",
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_delete_versione(10, 101)
        self.assertEqual(ctx.exception.code, "E_LISTINO_VERSIONE_CITATA")
        repo.delete_versione.assert_called_once_with(101)

    # Scopo: «Chiudi» e' il verbo del DB (§16.16, BE-C2), in una transazione,
    #        con la data del corpo; null toglie la chiusura. Nessuna regola di
    #        stato nel service.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_programma_chiusura_dal_verbo(self, mock_repo_cls, mock_atomic):
        from apps.vendite.services.listini_service import fn_programma_chiusura_versione

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "ATTIVA"}

        result = fn_programma_chiusura_versione(10, 101, {"valido_al": "2026-12-31"})
        self.assertEqual(result["id"], 101)
        repo.programma_chiusura.assert_called_once_with(101, date(2026, 12, 31))
        mock_atomic.assert_called_once()

        fn_programma_chiusura_versione(10, 101, {"valido_al": None})
        repo.programma_chiusura.assert_called_with(101, None)

    # Scopo: ⚠️ `valido_al` e' obbligatorio anche se null: un corpo vuoto e'
    #        un 400 sul campo, non una rimozione muta della chiusura. Chiavi
    #        estranee: 400.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_programma_chiusura_corpo(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_programma_chiusura_versione

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "ATTIVA"}
        for corpo in ({}, {"valido_al": "2026-12-31", "stato": "CHIUSA"}):
            with self.subTest(corpo=corpo), self.assertRaises(ServiceError) as ctx:
                fn_programma_chiusura_versione(10, 101, corpo)
            self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        repo.programma_chiusura.assert_not_called()

    # Scopo: Il rifiuto del verbo (fine nel passato, non attiva) arriva col
    #        codice del DB.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_programma_chiusura_rifiuto_del_db(self, mock_repo_cls, mock_atomic):
        del mock_atomic
        from apps.vendite.services.listini_service import fn_programma_chiusura_versione

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {"id": 101, "listino_id": 10, "stato": "ATTIVA"}
        repo.programma_chiusura.side_effect = make_db_error(
            "La fine non puo' essere prima di oggi.", codice="E_LISTINO_VERSIONE_FINE_NEL_PASSATO",
        )
        with self.assertRaises(ServiceError) as ctx:
            fn_programma_chiusura_versione(10, 101, {"valido_al": "2020-01-01"})
        self.assertEqual(ctx.exception.code, "E_LISTINO_VERSIONE_FINE_NEL_PASSATO")

    # Scopo: O3 - DELETE listino senza versioni e associazioni passa il guard.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_delete_listino_orphan_ok(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_delete_listino

        repo = mock_repo_cls.return_value
        repo.get_listino.return_value = {
            "id": 10,
            "codice": "TEST",
            "versioni_count": 0,
        }
        repo.delete_listino.return_value = True

        result = fn_delete_listino(10)

        self.assertEqual(result, {"deleted": True, "id": 10})
        repo.delete_listino.assert_called_once_with(10)

    # Scopo: O3 - DELETE listino con almeno una versione viene rifiutato.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_delete_listino_with_versioni_rejected(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_delete_listino

        repo = mock_repo_cls.return_value
        repo.get_listino.return_value = {
            "id": 10,
            "codice": "TEST",
            "versioni_count": 1,
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_delete_listino(10)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("attivo=false", ctx.exception.detail or "")
        repo.delete_listino.assert_not_called()

    # F2-BE-13: rimossi test `test_delete_listino_with_associazioni_rejected`
    # (tabella eliminata, solo `versioni_count` e' il check residuo) e
    # `test_test_resolver_requires_uom` (endpoint deprecato sostituito da
    # PricingService.resolve_prezzo in apps/vendite/services/pricing_service.py).

    # --- N8a: Variazione percentuale massa ---

    # Scopo: N8a - variazione su versione ATTIVA rifiutata (guard BOZZA).
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_variazione_pct_su_attiva_rifiutata(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_applica_variazione_percentuale

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "ATTIVA",
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_applica_variazione_percentuale(10, 101, {"variazione_percentuale": 3.0})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("BOZZA", ctx.exception.detail or "")
        repo.applica_variazione_percentuale.assert_not_called()

    # Scopo: N8a - variazione su versione CHIUSA rifiutata.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_variazione_pct_su_chiusa_rifiutata(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_applica_variazione_percentuale

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "CHIUSA",
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_applica_variazione_percentuale(10, 101, {"variazione_percentuale": 3.0})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: N8a - percentuale fuori range (+1500) rifiutata.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_variazione_pct_fuori_range_alto_rifiutata(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_applica_variazione_percentuale

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "BOZZA",
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_applica_variazione_percentuale(10, 101, {"variazione_percentuale": 1500})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("1000", ctx.exception.detail or "")

    # Scopo: N8a - percentuale -100% rifiutata (produrrebbe prezzo zero).
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_variazione_pct_meno_100_rifiutata(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_applica_variazione_percentuale

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "BOZZA",
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_applica_variazione_percentuale(10, 101, {"variazione_percentuale": -100})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: N8a - dry_run restituisce preview senza modifiche.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_variazione_pct_dry_run_preview(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_applica_variazione_percentuale

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "BOZZA",
        }
        repo.applica_variazione_percentuale.return_value = (
            2,
            [
                {"riga_id": 1, "articolo_codice": "ART001", "prezzo_attuale": "12.50", "prezzo_calcolato": "12.88"},
                {"riga_id": 2, "articolo_codice": "ART002", "prezzo_attuale": "100.00", "prezzo_calcolato": "103.00"},
            ],
        )

        result = fn_applica_variazione_percentuale(
            10, 101, {"variazione_percentuale": 3.0, "dry_run": True}
        )

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["righe_coinvolte"], 2)
        self.assertEqual(len(result["preview"]), 2)
        repo.applica_variazione_percentuale.assert_called_once()
        # Verifica che dry_run=True sia passato al repository
        call_kwargs = repo.applica_variazione_percentuale.call_args
        self.assertTrue(call_kwargs.kwargs.get("dry_run", call_kwargs[1].get("dry_run")))

    # Scopo: N8a - applicazione reale +3% su BOZZA eseguita con transaction.atomic.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_variazione_pct_applica_ok(self, mock_repo_cls, mock_atomic):
        from apps.vendite.services.listini_service import fn_applica_variazione_percentuale

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "BOZZA",
        }
        repo.applica_variazione_percentuale.return_value = (500, [])

        result = fn_applica_variazione_percentuale(
            10, 101, {"variazione_percentuale": 3.0, "arrotondamento_decimali": 4}
        )

        self.assertEqual(result["righe_aggiornate"], 500)
        self.assertEqual(result["variazione_percentuale"], "3.0")
        self.assertEqual(result["arrotondamento_decimali"], 4)
        mock_atomic.assert_called_once()

    # Scopo: N8a - variazione con filtro articoli passa array al repository.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_variazione_pct_con_filtro_articoli(self, mock_repo_cls, mock_atomic):
        from apps.vendite.services.listini_service import fn_applica_variazione_percentuale

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "BOZZA",
        }
        repo.applica_variazione_percentuale.return_value = (2, [])

        uuid_1 = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        uuid_2 = "019bbee2-5f6a-704f-bbd0-34ed84db253e"
        result = fn_applica_variazione_percentuale(
            10,
            101,
            {
                "variazione_percentuale": -5.0,
                "filtro_articoli": [uuid_1, uuid_2],
            },
        )

        self.assertEqual(result["righe_aggiornate"], 2)
        call_kwargs = repo.applica_variazione_percentuale.call_args
        self.assertIsNotNone(call_kwargs.kwargs.get("filtro_articoli", call_kwargs[1].get("filtro_articoli")))

    # Scopo: N8a - variazione_percentuale mancante rifiutata.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_variazione_pct_campo_obbligatorio_mancante(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_applica_variazione_percentuale

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "BOZZA",
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_applica_variazione_percentuale(10, 101, {})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: N8a - arrotondamento fuori range (15) rifiutato.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_variazione_pct_arrotondamento_fuori_range(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_applica_variazione_percentuale

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "BOZZA",
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_applica_variazione_percentuale(
                10, 101, {"variazione_percentuale": 3.0, "arrotondamento_decimali": 15}
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # --- N2: Alert scadenze ---

    # Scopo: N2 - alert scadenze con giorni default chiama il repository.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_alert_scadenze_default_giorni(self, mock_repo_cls):
        from apps.vendite.services.listini_service import fn_alert_scadenze

        repo = mock_repo_cls.return_value
        repo.listini_in_scadenza.return_value = [
            {"listino_id": 10, "listino_codice": "LIST-01", "giorni_rimanenti": 5}
        ]

        result = fn_alert_scadenze()

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["giorni"], 15)
        repo.listini_in_scadenza.assert_called_once_with(15)

    # Scopo: N2 - alert scadenze con giorni fuori range rifiutato.
    def test_alert_scadenze_giorni_fuori_range(self):
        from apps.vendite.services.listini_service import fn_alert_scadenze

        with self.assertRaises(ServiceError) as ctx:
            fn_alert_scadenze(giorni=0)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

        with self.assertRaises(ServiceError) as ctx:
            fn_alert_scadenze(giorni=400)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # --- N6: Rettifica controllata ---

    # Scopo: N6 - rettifica su versione BOZZA rifiutata (guard applicativo).
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_rettifica_controllata_su_bozza_rifiutata(self, mock_repo_cls):
        from datetime import timedelta

        from apps.vendite.services.listini_service import fn_rettifica_controllata_riga

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "BOZZA",
            "valido_dal": oggi_aziendale() - timedelta(days=1),
            "valido_al": None,
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_rettifica_controllata_riga(10, 101, 501, {"prezzo": 12.25, "motivo": "test"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("BOZZA", ctx.exception.message or "")

    # Scopo: N6 - rettifica su riga gia` propagata in commessa rifiutata. La
    #        regola e' del guard DB (`trgfn_listini_righe_guard_stato`, dal
    #        2026-10-09 senza copia in Python): qui il rifiuto arriva come
    #        DatabaseError dall'UPDATE e il service ne porta il codice.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_rettifica_controllata_riga_propagata_rifiutata(self, mock_repo_cls, mock_atomic):
        from datetime import timedelta

        from apps.vendite.services.listini_service import fn_rettifica_controllata_riga

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "ATTIVA",
            "valido_dal": oggi_aziendale() - timedelta(days=1),
            "valido_al": None,
        }
        repo.get_riga.return_value = {
            "id": 501,
            "prezzo": "12.5000000000",
            "meta": None,
        }
        repo.lock_riga_for_update.return_value = True
        repo.update_riga_prezzo_rettifica.side_effect = DatabaseError(
            "E_RIGA_LISTINO_PROPAGATA: la riga listino 501 e' gia' stata propagata a valle."
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_rettifica_controllata_riga(10, 101, 501, {"prezzo": 12.25, "motivo": "errore battitura"})
        self.assertEqual(ctx.exception.code, "E_RIGA_LISTINO_PROPAGATA")

    # Scopo: N6 - rettifica ammessa se riga non propagata.
    @patch("apps.vendite.services.listini_service.transaction.atomic")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_rettifica_controllata_ok_non_propagata(self, mock_repo_cls, mock_atomic):
        from datetime import timedelta

        from apps.vendite.services.listini_service import fn_rettifica_controllata_riga

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "ATTIVA",
            "valido_dal": oggi_aziendale() - timedelta(days=1),
            "valido_al": None,
        }
        repo.get_riga.return_value = {
            "id": 501,
            "prezzo": "12.5000000000",
            "meta": None,
        }
        repo.lock_riga_for_update.return_value = True
        repo.update_riga_prezzo_rettifica.return_value = True

        result = fn_rettifica_controllata_riga(
            10, 101, 501, {"prezzo": "12.25", "motivo": "errore di battitura al caricamento"}
        )

        self.assertEqual(result["prezzo_precedente"], "12.5000000000")
        self.assertEqual(result["prezzo_nuovo"], "12.25")
        self.assertEqual(result["motivo"], "errore di battitura al caricamento")
        repo.lock_riga_for_update.assert_called_once_with(101, 501)
        repo.update_riga_prezzo_rettifica.assert_called_once()

    # Scopo: N6 - rettifica senza motivo rifiutata.
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_rettifica_controllata_senza_motivo_rifiutata(self, mock_repo_cls):
        from datetime import timedelta

        from apps.vendite.services.listini_service import fn_rettifica_controllata_riga

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "ATTIVA",
            "valido_dal": oggi_aziendale() - timedelta(days=1),
            "valido_al": None,
        }
        repo.get_riga.return_value = {
            "id": 501,
            "prezzo": "12.5000000000",
            "meta": None,
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_rettifica_controllata_riga(10, 101, 501, {"prezzo": 12.25, "motivo": ""})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("motivo", (ctx.exception.detail or "").lower())

    # Scopo: N6 - rettifica su versione CHIUSA/scaduta rifiutata (guard data-driven).
    #        Verifica che il guard operativo (valido_al < oggi) scatti indipendente
    #        dallo stato persistito: anche se stato='ATTIVA' stantio, la versione
    #        scaduta non puo` essere rettificata (principio fail-safe).
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_rettifica_controllata_su_versione_scaduta_rifiutata(self, mock_repo_cls):
        from datetime import timedelta

        from apps.vendite.services.listini_service import fn_rettifica_controllata_riga

        repo = mock_repo_cls.return_value
        repo.get_versione.return_value = {
            "id": 101,
            "listino_id": 10,
            "stato": "ATTIVA",  # stato stantio: in realta` scaduta da ieri
            "valido_dal": oggi_aziendale() - timedelta(days=30),
            "valido_al": oggi_aziendale() - timedelta(days=1),
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_rettifica_controllata_riga(10, 101, 501, {"prezzo": 12.25, "motivo": "test"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("operativamente attive", ctx.exception.message or "")


class TranslateIntegrityErrorTests(TestCase):
    """Test diretti su `_translate_integrity_error` per i path FK temporal PG18."""

    # Scopo: Verifica che la temporal FK PG18 `fk_listrighe_comp_articoli_comp_temporal`
    #        (sostituisce guard 6 di `trgfn_listini_righe_comp_guard_coerenza_bom`,
    #        rimosso con migration 20260514-13) venga tradotta nel codice parlante
    #        `E_LISTINO_RIGA_COMP_BOM_INCOERENTE`, e non nel fallback FK generico.
    def test_translate_integrity_fk_listrighe_comp_temporal(self):
        from apps.vendite.services.listini_service import _translate_integrity_error

        exc = IntegrityError(
            'insert or update on table "listini_righe_componenti" violates foreign key constraint '
            '"fk_listrighe_comp_articoli_comp_temporal"'
        )
        with self.assertRaises(ServiceError) as ctx:
            _translate_integrity_error(exc, function_name="test", entity="bundle")
        self.assertEqual(ctx.exception.code, "E_LISTINO_RIGA_COMP_BOM_INCOERENTE")
        self.assertIn("distinta base", (ctx.exception.message or "").lower())

    # Scopo: Verifica che l'EXCLUDE parziale ripristinato 2026-06-02
    #        (`ex_listini_righe_comp_no_overlap`, migration 20260602-01) venga
    #        tradotto nel codice overlap dedicato `E_VENDITE_LISTINO_RIGA_COMP_OVERLAP`
    #        (409, simmetrico a PROMO/VERSIONE), non nel fallback E_VENDITE_VALIDATION.
    #        Prima del fix il vincolo era un indice-civetta: mapping = codice morto.
    def test_translate_integrity_exclude_righe_comp_overlap(self):
        from apps.vendite.services.listini_service import _translate_integrity_error

        exc = IntegrityError(
            'conflicting key value violates exclusion constraint '
            '"ex_listini_righe_comp_no_overlap"'
        )
        with self.assertRaises(ServiceError) as ctx:
            _translate_integrity_error(exc, function_name="test", entity="bundle")
        self.assertEqual(ctx.exception.code, "E_VENDITE_LISTINO_RIGA_COMP_OVERLAP")
        self.assertIn("sovrappost", (ctx.exception.message or "").lower())


class FnSaveBundleRowsTests(TestCase):
    # Scopo: ⛔ `rows` assente o non lista e' un 400, non «svuota il bundle»:
    #        il salvataggio sostituisce in blocco, e fino al 2026-10-21 la view
    #        trasformava l'assenza in `[]` cancellando ogni prezzo con un 200.
    @patch("apps.vendite.services.listini_service._assert_versione_bozza_for_riga_op")
    @patch("apps.vendite.services.listini_service._get_versione_or_raise")
    @patch("apps.vendite.services.listini_service._get_listino_or_raise")
    @patch("apps.vendite.services.listini_service.ListiniRepository")
    def test_rows_assente_o_non_lista_e_400(self, repo_cls, _listino, versione, _bozza):
        from apps.core.services.error_policies import ErrorPolicyRegistry
        from apps.vendite.services.listini_service import fn_save_bundle

        versione.return_value = {"valido_dal": "2026-01-01", "valido_al": None}
        for rows in (None, "x", {"a": 1}, [1]):
            with self.subTest(rows=rows), self.assertRaises(ServiceError) as ctx:
                fn_save_bundle(10, 101, "abc-uuid", rows)
            self.assertEqual(ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 400)
        self.assertEqual(repo_cls.return_value.method_calls, [])


class FnDeleteBundleTests(TestCase):
    """Wrapper DELETE prezzi bundle composito (tabula rasa idempotente).

    Verifica che `fn_delete_bundle` deleghi a `fn_save_bundle(rows=[])`
    riusando tutti i guard esistenti (BOZZA, listino/versione esistenti).
    """

    # Scopo: fn_delete_bundle e' un thin wrapper di fn_save_bundle(rows=[]).
    # Verifica che il payload passato sia effettivamente lista vuota.
    @patch("apps.vendite.services.listini_service.fn_save_bundle")
    def test_fn_delete_bundle_delega_a_save_bundle_con_rows_vuota(self, mock_save):
        from apps.vendite.services.listini_service import fn_delete_bundle

        mock_save.return_value = {"disattivati": 3, "inseriti": 0}

        result = fn_delete_bundle(10, 101, "abc-uuid")

        self.assertEqual(result, {"disattivati": 3, "inseriti": 0})
        mock_save.assert_called_once_with(10, 101, "abc-uuid", rows=[])

    # Scopo: idempotenza — composito senza prezzi bundle ritorna 0 disattivati,
    # nessuna eccezione. Pattern DELETE coerente.
    @patch("apps.vendite.services.listini_service.fn_save_bundle")
    def test_fn_delete_bundle_idempotente_zero_disattivati(self, mock_save):
        from apps.vendite.services.listini_service import fn_delete_bundle

        mock_save.return_value = {"disattivati": 0, "inseriti": 0}

        result = fn_delete_bundle(10, 101, "abc-uuid")

        self.assertEqual(result["disattivati"], 0)

    # Scopo: il guard BOZZA-only ereditato si propaga senza intercettazioni.
    # Versione ATTIVA → `fn_save_bundle` solleva, fn_delete_bundle propaga.
    @patch("apps.vendite.services.listini_service.fn_save_bundle")
    def test_fn_delete_bundle_propaga_guard_non_bozza(self, mock_save):
        from apps.vendite.services.listini_service import fn_delete_bundle

        mock_save.side_effect = ServiceError(
            code="E_LISTINO_VERSIONE_NON_BOZZA",
            message="Solo versioni BOZZA",
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_delete_bundle(10, 101, "abc-uuid")
        self.assertEqual(ctx.exception.code, "E_LISTINO_VERSIONE_NON_BOZZA")
