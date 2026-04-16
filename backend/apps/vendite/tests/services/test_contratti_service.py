# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari ContrattiService (F2-BE-05).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) list_contratti_applies_default_data_da
2) list_contratti_invalid_order
3) list_contratti_invalid_ambito
4) get_contratto_not_found
5) get_contratto_ok
6) create_contratto_modalita_A_ok
7) create_contratto_modalita_C_ok
8) create_contratto_modalita_C_con_variazione_fallisce
9) create_contratto_variazione_coppia_incompleta_fallisce
10) create_contratto_rifiuta_numero_in_payload
11) create_contratto_overlap_exclude_mappato
12) create_contratto_genera_numero_e_stato_draft
13) update_contratto_rifiuta_identificativi_immutabili
14) update_contratto_campi_vuoto_fallisce
15) update_contratto_ok_variazione
16) cambia_stato_codice_sconosciuto
17) cambia_stato_modalita_C_senza_righe_tradotto
18) cambia_stato_ok
19) create_riga_modalita_C_senza_prezzo_tradotto
20) create_riga_ok
21) update_riga_rifiuta_articolo_id
22) update_riga_ok
23) delete_riga_not_found
24) create_utility_tipo_classe_obbligatori_tradotto
25) create_utility_ok
26) update_utility_immutabili_rifiutati
27) update_contratto_modalita_B_con_listino_esistente_patch_solo_variazione (regressione review)
28) repository_create_contratto_usa_cast_jsonb_per_meta (regressione review)
"""

from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError, IntegrityError

from apps.core.services.service_errors import ServiceError


def _testata_default() -> dict[str, object]:
    """Factory riga testata per rilettura get_contratto post-mutazione."""
    return {
        "id": 1,
        "numero": "CNT0000001",
        "billing_account_id": 10,
        "istanza_utility_id": 20,
        "utility_id": 3,
        "stato_doc_contratto_id": 1,
        "listino_id": 100,
        "tipo_variazione_globale": "PERCENTUALE",
        "valore_variazione_globale": Decimal("-10"),
        "ambito": "COMMODITY",
    }


class ContrattiServiceTests(TestCase):
    # --- lista ---------------------------------------------------------

    # Scopo: senza data_da il service applica 1 gennaio (anno-1).
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_list_contratti_applies_default_data_da(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.list_contratti.return_value = ([], 0)

        ContrattiService().list_contratti()

        call = repo.list_contratti.call_args.kwargs
        self.assertEqual(call["data_da"], date(date.today().year - 1, 1, 1))

    # Scopo: order_by non whitelisted -> ServiceError.
    def test_list_contratti_invalid_order(self):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().list_contratti(order_by="haxxor")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: filtro ambito fuori whitelist -> ServiceError.
    def test_list_contratti_invalid_ambito(self):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().list_contratti(ambito="FANTASY")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # --- dettaglio -----------------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_get_contratto_not_found(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo_cls.return_value.get_contratto.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().get_contratto(42)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_get_contratto_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = {"id": 5}
        repo.list_righe.return_value = [{"id": 99}]

        result = ContrattiService().get_contratto(1)

        self.assertEqual(result["id"], 1)
        self.assertEqual(result["utility"], {"id": 5})
        self.assertEqual(result["righe"], [{"id": 99}])

    # --- create contratto ---------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_modalita_A_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.generate_numero.return_value = "CNT0000001"
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_contratto.return_value = 1
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        result = ContrattiService().create_contratto({
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
            "valido_al": "2026-12-31",
            "listino_id": 100,
            "tipo_variazione_globale": "percentuale",
            "valore_variazione_globale": "10",
        })

        self.assertEqual(result["id"], 1)
        args = repo.create_contratto.call_args.args[0]
        self.assertEqual(args["numero"], "CNT0000001")
        self.assertEqual(args["stato_doc_contratto_id"], 1)
        self.assertEqual(args["tipo_variazione_globale"], "PERCENTUALE")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_modalita_C_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.generate_numero.return_value = "CNT0000002"
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_contratto.return_value = 2
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
        })

        args = repo.create_contratto.call_args.args[0]
        self.assertNotIn("listino_id", args)
        self.assertNotIn("tipo_variazione_globale", args)

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_modalita_C_con_variazione_fallisce(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
                # Nessun listino -> modalita' C. Variazione NON ammessa.
                "tipo_variazione_globale": "PERCENTUALE",
                "valore_variazione_globale": "5",
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("modalita' C", ctx.exception.detail or "")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_variazione_coppia_incompleta_fallisce(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
                "listino_id": 100,
                "tipo_variazione_globale": "PERCENTUALE",
                # valore_variazione_globale mancante -> coppia incoerente.
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    def test_create_contratto_rifiuta_numero_in_payload(self):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "numero": "CNT9999999",
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_overlap_exclude_mappato(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.generate_numero.return_value = "CNT0000003"
        repo.get_stato_id_by_codice.return_value = 1
        repo.create_contratto.side_effect = IntegrityError(
            "duplicate key value violates exclusion constraint \"ex_contratti_no_overlap\""
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_contratto({
                "billing_account_id": 10,
                "istanza_utility_id": 20,
                "utility_id": 3,
                "valido_dal": "2026-01-01",
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_CONTRATTO_OVERLAP")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_contratto_genera_numero_e_stato_draft(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.generate_numero.return_value = "CNT0000077"
        repo.get_stato_id_by_codice.return_value = 42
        repo.create_contratto.return_value = 7
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().create_contratto({
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": "2026-01-01",
        })

        repo.generate_numero.assert_called_once_with()
        repo.get_stato_id_by_codice.assert_called_once_with("DRAFT")
        args = repo.create_contratto.call_args.args[0]
        self.assertEqual(args["numero"], "CNT0000077")
        self.assertEqual(args["stato_doc_contratto_id"], 42)

    # --- update contratto ---------------------------------------------

    def test_update_contratto_rifiuta_identificativi_immutabili(self):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {"numero": "CNT9999999"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_campi_vuoto_fallisce(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_contratto(1, {})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_ok_variazione(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.update_contratto.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().update_contratto(1, {
            "listino_id": 200,
            "tipo_variazione_globale": "VALORE_FISSO",
            "valore_variazione_globale": "5",
        })

        args = repo.update_contratto.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1]["listino_id"], 200)
        self.assertEqual(args[1]["tipo_variazione_globale"], "VALORE_FISSO")
        self.assertEqual(args[1]["valore_variazione_globale"], Decimal("5"))

    # --- cambio stato --------------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_codice_sconosciuto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo_cls.return_value.get_stato_id_by_codice.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().cambia_stato(1, codice_interno="ATTIVO")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_modalita_C_senza_righe_tradotto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 2
        repo.update_stato.side_effect = DatabaseError(
            "Contratto CNT0000001 modalita' C senza righe attive: non attivabile."
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().cambia_stato(1, codice_interno="ATTIVO")
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_MODALITA_C_SENZA_RIGHE")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_cambia_stato_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_stato_id_by_codice.return_value = 2
        repo.update_stato.return_value = True
        repo.get_contratto.return_value = _testata_default()
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []

        ContrattiService().cambia_stato(1, codice_interno="ATTIVO")

        repo.update_stato.assert_called_once_with(1, 2)

    # --- righe ---------------------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_modalita_C_senza_prezzo_tradotto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.create_riga.side_effect = DatabaseError(
            "Contratto CNT0001 riga 5 (articolo X): prezzo_unitario obbligatorio in modalita' C."
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_riga(
                1,
                {"articolo_id": "00000000-0000-0000-0000-000000000001"},
            )
        self.assertEqual(ctx.exception.code, "E_CONTRATTO_MODALITA_C_RIGA_SENZA_PREZZO")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_riga_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.create_riga.return_value = 77
        repo.get_riga.return_value = {"id": 77, "prezzo_unitario": Decimal("25.50")}

        result = ContrattiService().create_riga(
            1,
            {
                "articolo_id": "00000000-0000-0000-0000-000000000001",
                "prezzo_unitario": "25.50",
                "ordine": 10,
            },
        )

        self.assertEqual(result["id"], 77)
        args = repo.create_riga.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1]["prezzo_unitario"], Decimal("25.50"))

    def test_update_riga_rifiuta_articolo_id(self):
        from apps.vendite.services.contratti_service import ContrattiService

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_riga(77, {"articolo_id": "...".ljust(36, "0")})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_riga_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.update_riga.return_value = True
        repo.get_riga.return_value = {"id": 77, "prezzo_unitario": Decimal("30")}

        ContrattiService().update_riga(77, {"prezzo_unitario": "30"})

        args = repo.update_riga.call_args.args
        self.assertEqual(args[0], 77)
        self.assertEqual(args[1]["prezzo_unitario"], Decimal("30"))

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_delete_riga_not_found(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo_cls.return_value.delete_riga.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().delete_riga(77)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    # --- utility 1:1 ---------------------------------------------------

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_utility_tipo_classe_obbligatori_tradotto(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.create_utility.side_effect = DatabaseError(
            "Contratto utility GAS: tipo_utenza_id e classe_utenza_id sono obbligatori."
        )

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().create_utility(1, {})
        self.assertEqual(
            ctx.exception.code, "E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI"
        )

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_create_utility_ok(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_contratto.return_value = _testata_default()
        repo.create_utility.return_value = 9
        repo.get_utility.return_value = {
            "id": 9,
            "contratto_id": 1,
            "istanza_utility_id": 20,
            "utility_id": 3,
        }

        ContrattiService().create_utility(
            1,
            {"tipo_utenza_id": 2, "classe_utenza_id": 7},
        )

        args = repo.create_utility.call_args.args
        self.assertEqual(args[0], 1)
        # istanza e utility derivati dalla testata, non dal payload.
        self.assertEqual(args[1]["istanza_utility_id"], 20)
        self.assertEqual(args[1]["utility_id"], 3)
        self.assertEqual(args[1]["tipo_utenza_id"], 2)

    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_utility_immutabili_rifiutati(self, repo_cls):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        repo.get_utility.return_value = {
            "id": 9,
            "istanza_utility_id": 20,
            "utility_id": 3,
        }

        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().update_utility(1, {"utility_id": 999})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: REGRESSIONE review — patch solo sulla variazione globale, senza
    #        listino_id nel payload, su contratto modalita' A/B esistente: il
    #        validator modalita' deve leggere listino_id corrente dal DB, NON
    #        trattare l'assenza come "listino_id=NULL -> modalita' C".
    #        Bug trovato in review: `existing=None` passato sempre -> falso
    #        positivo "modalita' C: tipo/valore devono essere NULL".
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_update_contratto_modalita_B_con_listino_esistente_patch_solo_variazione(
        self, repo_cls
    ):
        from apps.vendite.services.contratti_service import ContrattiService

        repo = repo_cls.return_value
        # Contratto esistente modalita' B: listino presente, niente variazione.
        existing = {
            **_testata_default(),
            "listino_id": 100,
            "tipo_variazione_globale": None,
            "valore_variazione_globale": None,
        }
        repo.get_contratto.return_value = existing
        repo.get_utility.return_value = None
        repo.list_righe.return_value = []
        repo.update_contratto.return_value = True

        # Patch: aggiungo variazione globale (passaggio da B ad A).
        result = ContrattiService().update_contratto(1, {
            "tipo_variazione_globale": "PERCENTUALE",
            "valore_variazione_globale": "7",
        })

        self.assertEqual(result["id"], 1)
        args = repo.update_contratto.call_args.args
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1]["tipo_variazione_globale"], "PERCENTUALE")
        self.assertEqual(args[1]["valore_variazione_globale"], Decimal("7"))


# Scopo: REGRESSIONE review — il repository usa `%s::jsonb` per la colonna meta
#        (non `%s`) cosi' che driver senza auto-adattamento dict->jsonb non falliscano.
class ContrattiRepositoryJsonbTests(TestCase):
    @patch("apps.vendite.db.contratti_repository.connection")
    def test_repository_create_contratto_usa_cast_jsonb_per_meta(self, mock_connection):
        from apps.vendite.db.contratti_repository import ContrattiRepository

        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        mock_connection.cursor.return_value.__enter__.return_value = cursor

        ContrattiRepository().create_contratto({
            "numero": "CNT0000001",
            "billing_account_id": 10,
            "istanza_utility_id": 20,
            "utility_id": 3,
            "valido_dal": date(2026, 1, 1),
            "stato_doc_contratto_id": 1,
            "meta": {"note": "test"},
        })

        sql = cursor.execute.call_args[0][0]
        self.assertIn("%s::jsonb", sql)
        params = cursor.execute.call_args[0][1]
        # meta serializzato a JSON string (non dict).
        meta_param = next(p for p in params if isinstance(p, str) and p.startswith("{"))
        self.assertEqual(meta_param, '{"note": "test"}')


# Scopo: smoke che il repository genera il numero tramite fn_generate_codice
#        (verifica solo l'SQL parametrico — la DB call e' mockata).
class ContrattiRepositoryNumberTests(TestCase):
    @patch("apps.vendite.db.contratti_repository.connection")
    def test_generate_numero_calls_fn_generate_codice(self, mock_connection):
        from apps.vendite.db.contratti_repository import ContrattiRepository

        cursor = MagicMock()
        cursor.fetchone.return_value = ("CNT0000001",)
        mock_connection.cursor.return_value.__enter__.return_value = cursor

        result = ContrattiRepository().generate_numero()

        self.assertEqual(result, "CNT0000001")
        cursor.execute.assert_called_once_with(
            "SELECT script.fn_generate_codice(%s)", ["contratto"]
        )
