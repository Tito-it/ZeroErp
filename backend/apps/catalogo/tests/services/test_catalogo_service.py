# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari funzioni catalogo_service per Fasi 1-2 articoli/UoM.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CatalogoServiceTests.test_fn_list_articoli_ok
2) CatalogoServiceTests.test_fn_list_articoli_invalid_order
4) CatalogoServiceTests.test_fn_get_articolo_ok
5) CatalogoServiceTests.test_fn_get_articolo_not_found
6) CatalogoServiceTests.test_fn_lookup_articoli_ok
7) CatalogoServiceTests.test_fn_lookup_articoli_invalid_limit
8) CatalogoServiceTests.test_fn_lookup_unita_misura_ok
9) CatalogoServiceTests.test_fn_lookup_unita_misura_invalid_limit
10) CatalogoServiceTests.test_fn_create_articolo_ok
11) CatalogoServiceTests.test_fn_create_articolo_missing_codice
11b) CatalogoServiceTests.test_fn_create_articolo_missing_uom_id
12) CatalogoServiceTests.test_fn_create_articolo_duplicate_codice
13) CatalogoServiceTests.test_fn_update_articolo_ok
14) CatalogoServiceTests.test_fn_update_articolo_codice_immutabile
14b) CatalogoServiceTests.test_fn_update_articolo_uom_id_immutabile
15) CatalogoServiceTests.test_fn_disattiva_articolo_ok
16) CatalogoServiceTests.test_fn_disattiva_articolo_already_inactive
17) CatalogoServiceTests.test_fn_create_articolo_unknown_key
18) CatalogoServiceTests.test_fn_update_articolo_float_fk_invalid
19) CatalogoServiceTests.test_fn_create_uom_operativa_ok
20) CatalogoServiceTests.test_fn_update_uom_operativa_not_found
21) CatalogoServiceTests.test_fn_create_componente_ok
22) CatalogoServiceTests.test_fn_update_componente_immutabile
23) CatalogoServiceTests.test_fn_create_nota_articolo_ok
24) CatalogoServiceTests.test_fn_create_nota_articolo_default_documento_header
25) CatalogoServiceTests.test_fn_create_nota_componente_default_riga_after
26) CatalogoServiceTests.test_fn_create_nota_articolo_anchor_riga_inconsistency
27) CatalogoServiceTests.test_fn_update_nota_not_found
28) CatalogoServiceTests.test_fn_create_componente_self_reference
26) CatalogoServiceTests.test_fn_create_articolo_listino_tipologia_id_ok
27) CatalogoServiceTests.test_fn_update_articolo_listino_tipologia_id_invalid
27b) CatalogoServiceTests.test_fn_create_articolo_natura_vendita_id_ok
27c) CatalogoServiceTests.test_fn_update_articolo_natura_vendita_id_null_invalid
28) CatalogoServiceTests.test_fn_create_componente_esposto_in_fattura_ok
29) CatalogoServiceTests.test_fn_list_uom_rounding_modes_ok
30) CatalogoServiceTests.test_fn_list_uom_rounding_modes_coverage
31) CatalogoServiceTests.test_fn_create_componente_valido_dal_fallback_today
40) CatalogoServiceTests.test_fn_create_uom_operativa_valido_dal_fallback_today
41) CatalogoServiceTests.test_fn_create_conversione_valido_dal_fallback_today
42) CatalogoServiceTests.test_fn_get_articolo_includes_non_editable_fields
43) CatalogoServiceTests.test_fn_list_uom_operative_envelope_non_editable_fields
44) CatalogoServiceTests.test_fn_get_conversione_includes_non_editable_fields
45) CatalogoServiceTests.test_fn_list_articoli_proietta_capability_bom
46) CatalogoServiceTests.test_fn_list_uom_operative_proietta_capability_eliminabile
47) CatalogoServiceTests.test_fn_riattiva_articolo_ok
48) CatalogoServiceTests.test_fn_riattiva_articolo_already_active
49) CatalogoServiceTests.test_fn_riattiva_articolo_not_found
50) CatalogoServiceTests.test_fn_update_articolo_rifiuta_attivo
51) CatalogoServiceTests.test_fn_get_articolo_form_defaults_ok
52) CatalogoServiceTests.test_fn_get_articolo_form_defaults_missing_param
53) CatalogoServiceTests.test_fn_get_articolo_form_defaults_malformed_param
"""

from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError

from apps.core.services.service_errors import ServiceError


class CatalogoServiceTests(TestCase):
    # Scopo: Lista articoli valida -> envelope paginato coerente.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_list_articoli_ok(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_list_articoli

        mock_repo_cls.return_value.list_articoli.return_value = (
            [{"id": 1, "codice": "ART-001", "descrizione": "Articolo demo"}],
            1,
        )

        results, total = fn_list_articoli(search="art", limit=25, offset=0, order_by="codice")

        self.assertEqual(total, 1)
        self.assertEqual(results[0]["codice"], "ART-001")

    # Scopo: order_by fuori whitelist -> ServiceError validazione.
    def test_fn_list_articoli_invalid_order(self):
        from apps.catalogo.services.catalogo_service import fn_list_articoli

        with self.assertRaises(ServiceError) as ctx:
            fn_list_articoli(order_by="nome")
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: Dettaglio articolo trovato -> dict ritornato senza trasformazioni.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_get_articolo_ok(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_get_articolo

        mock_repo_cls.return_value.get_articolo.return_value = {
            "id": 7,
            "codice": "ART-007",
            "is_composito": True,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = [{"id": 1, "uom_codice": "PZ"}]
        mock_bom_repo_cls.return_value.list_componenti.return_value = [{"id": "comp-1"}]
        # Shape allineata al pattern partizionato vendite (2026-05-22):
        # le note ritornano `id`/`testo_md` senza prefisso `nota_`.
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = [{"id": 9}]

        result = fn_get_articolo(7)

        self.assertEqual(result["id"], 7)
        self.assertEqual(result["codice"], "ART-007")
        self.assertEqual(result["uom_operative"][0]["uom_codice"], "PZ")
        self.assertEqual(result["componenti"][0]["id"], "comp-1")
        self.assertEqual(result["note"][0]["id"], 9)

    # Scopo: Dettaglio articolo assente -> not found uniforme.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_get_articolo_not_found(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_get_articolo

        mock_repo_cls.return_value.get_articolo.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            fn_get_articolo(999)
        self.assertEqual(ctx.exception.code, "E_CATALOGO_ARTICOLO_NOT_FOUND")

    # Scopo: Lookup articoli valido -> count e results coerenti.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_lookup_articoli_ok(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_lookup_articoli

        mock_repo_cls.return_value.lookup_articoli.return_value = [
            {"id": 1, "codice": "ART-001"}
        ]

        result = fn_lookup_articoli(search="art")

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["id"], 1)

    # Scopo: il filtro natura (escludi_destinazione_tipi) è inoltrato al
    # repository invariato (passthrough, filtro applicato in SQL).
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_lookup_articoli_escludi_destinazione(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_lookup_articoli

        mock_repo_cls.return_value.lookup_articoli.return_value = []

        fn_lookup_articoli(search="art", escludi_destinazione_tipi=["CONTRATTO"])

        kwargs = mock_repo_cls.return_value.lookup_articoli.call_args.kwargs
        self.assertEqual(kwargs["escludi_destinazione_tipi"], ["CONTRATTO"])

    # Scopo: limit lookup articoli fuori range -> ServiceError.
    def test_fn_lookup_articoli_invalid_limit(self):
        from apps.catalogo.services.catalogo_service import fn_lookup_articoli

        with self.assertRaises(ServiceError) as ctx:
            fn_lookup_articoli(limit=0)
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: Lookup UoM valido -> count e risultati coerenti.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_lookup_unita_misura_ok(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_lookup_unita_misura

        mock_repo_cls.return_value.lookup_unita_misura.return_value = [
            {"id": 3, "codice": "PZ"}
        ]

        result = fn_lookup_unita_misura(search="pez")

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["codice"], "PZ")

    # Scopo: limit lookup UoM fuori range -> ServiceError.
    def test_fn_lookup_unita_misura_invalid_limit(self):
        from apps.catalogo.services.catalogo_service import fn_lookup_unita_misura

        with self.assertRaises(ServiceError) as ctx:
            fn_lookup_unita_misura(limit=250)
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: Create articolo valido -> insert + dettaglio finale.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_articolo_ok(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        repo = mock_repo_cls.return_value
        repo.create_articolo.return_value = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "ART-001",
            "descrizione": "Articolo demo",
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_componenti.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_create_articolo(
            {"codice": "ART-001", "descrizione": "Articolo demo", "uom_id": 1}
        )

        self.assertEqual(result["codice"], "ART-001")
        repo.create_articolo.assert_called_once_with(
            {"codice": "ART-001", "descrizione": "Articolo demo", "uom_id": 1}
        )

    # Scopo: codice mancante in create -> ServiceError validazione.
    def test_fn_create_articolo_missing_codice(self):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_create_articolo({"descrizione": "Articolo demo", "uom_id": 1})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: uom_id mancante in create -> ServiceError validazione (NOT NULL DDL).
    def test_fn_create_articolo_missing_uom_id(self):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_create_articolo({"codice": "ART-001", "descrizione": "Articolo demo"})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("uom_id", ctx.exception.detail or "")

    # Scopo: duplicate codice -> traduzione IntegrityError in validazione catalogo.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_articolo_duplicate_codice(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        mock_repo_cls.return_value.create_articolo.side_effect = IntegrityError("uq_articoli_codice")

        with self.assertRaises(ServiceError) as ctx:
            fn_create_articolo(
                {"codice": "ART-001", "descrizione": "Articolo demo", "uom_id": 1}
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertEqual(ctx.exception.message, "Codice articolo gia' esistente.")

    # Scopo: update articolo valido -> update delta e dettaglio riletto.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_update_articolo_ok(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        repo = mock_repo_cls.return_value
        repo.update_articolo.return_value = True
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "ART-001",
            "descrizione": "Aggiornato",
            "descrizione_breve": None,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_componenti.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_update_articolo(
            "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            {"descrizione": "Aggiornato", "descrizione_breve": ""},
        )

        self.assertEqual(result["descrizione"], "Aggiornato")
        repo.update_articolo.assert_called_once_with(
            "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            {"descrizione": "Aggiornato", "descrizione_breve": None},
        )

    # Scopo: tentativo di update codice -> errore per immutabilita'.
    def test_fn_update_articolo_codice_immutabile(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d", {"codice": "NEW"})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: tentativo di update uom_id -> errore per immutabilita' (lock_columns DDL).
    def test_fn_update_articolo_uom_id_immutabile(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d", {"uom_id": 99})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("uom_id", ctx.exception.detail or "")

    # Scopo: disattiva articolo -> update attivo=false e dettaglio finale.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_disattiva_articolo_ok(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_disattiva_articolo

        repo = mock_repo_cls.return_value
        repo.deactivate_articolo.return_value = True
        repo.get_articolo.side_effect = [
            {
                "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                "codice": "ART-001",
                "attivo": True,
            },
            {
                "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                "codice": "ART-001",
                "attivo": False,
            },
        ]
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_componenti.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_disattiva_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d")

        self.assertFalse(result["attivo"])
        repo.deactivate_articolo.assert_called_once_with("019bbee2-5f6a-704f-bbd0-34ed84db252d")

    # Scopo: articolo gia' inattivo -> risposta idempotente senza secondo update.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_disattiva_articolo_already_inactive(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_disattiva_articolo

        repo = mock_repo_cls.return_value
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "ART-001",
            "attivo": False,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_componenti.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_disattiva_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d")

        self.assertFalse(result["attivo"])
        repo.deactivate_articolo.assert_not_called()

    # Scopo: riattiva articolo inattivo -> chiama fn DB e restituisce dettaglio attivo.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_riattiva_articolo_ok(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_riattiva_articolo

        repo = mock_repo_cls.return_value
        repo.get_articolo.side_effect = [
            {"id": "019bbee2-5f6a-704f-bbd0-34ed84db252d", "codice": "ART-001", "attivo": False},
            {"id": "019bbee2-5f6a-704f-bbd0-34ed84db252d", "codice": "ART-001", "attivo": True},
        ]
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_componenti.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_riattiva_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d")

        self.assertTrue(result["attivo"])
        repo.reactivate_articolo.assert_called_once_with("019bbee2-5f6a-704f-bbd0-34ed84db252d")

    # Scopo: articolo gia' attivo -> idempotente, fn DB non chiamata.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_riattiva_articolo_already_active(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_riattiva_articolo

        repo = mock_repo_cls.return_value
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "ART-001",
            "attivo": True,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_componenti.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_riattiva_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d")

        self.assertTrue(result["attivo"])
        repo.reactivate_articolo.assert_not_called()

    # Scopo: riattiva articolo inesistente -> NOT_FOUND uniforme dal pre-flight.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_riattiva_articolo_not_found(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_riattiva_articolo

        mock_repo_cls.return_value.get_articolo.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            fn_riattiva_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d")
        self.assertEqual(ctx.exception.code, "E_CATALOGO_ARTICOLO_NOT_FOUND")
        mock_repo_cls.return_value.reactivate_articolo.assert_not_called()

    # Scopo: PATCH articolo con `attivo` -> rifiutato (Fase 7: solo endpoint dedicati).
    def test_fn_update_articolo_rifiuta_attivo(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo(
                "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                {"attivo": False},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("attivo", ctx.exception.detail or "")

    # Scopo: form-defaults articolo casta DEFAULT_IVA_ID a int (Fase 8).
    @patch("apps.catalogo.services.catalogo_service.ParameterService")
    def test_fn_get_articolo_form_defaults_ok(self, mock_ps_cls):
        from apps.catalogo.services.catalogo_service import fn_get_articolo_form_defaults

        mock_ps_cls.return_value.get_defaults.return_value = {"DEFAULT_IVA_ID": "42"}

        result = fn_get_articolo_form_defaults()

        self.assertEqual(result, {"default_iva_id": 42})
        mock_ps_cls.return_value.get_defaults.assert_called_once_with(
            ["DEFAULT_IVA_ID"],
            django_user_id=None,
            group_ids=None,
            emittente_fiscale_id=None,
        )

    # Scopo: parametro mancante -> default_iva_id a None (best-effort, no raise).
    @patch("apps.catalogo.services.catalogo_service.ParameterService")
    def test_fn_get_articolo_form_defaults_missing_param(self, mock_ps_cls):
        from apps.catalogo.services.catalogo_service import fn_get_articolo_form_defaults

        mock_ps_cls.return_value.get_defaults.return_value = {}

        result = fn_get_articolo_form_defaults()

        self.assertEqual(result, {"default_iva_id": None})

    # Scopo: parametro malformato -> default_iva_id a None (best-effort, no raise).
    @patch("apps.catalogo.services.catalogo_service.ParameterService")
    def test_fn_get_articolo_form_defaults_malformed_param(self, mock_ps_cls):
        from apps.catalogo.services.catalogo_service import fn_get_articolo_form_defaults

        mock_ps_cls.return_value.get_defaults.return_value = {"DEFAULT_IVA_ID": "non-numerico"}

        result = fn_get_articolo_form_defaults()

        self.assertEqual(result, {"default_iva_id": None})

    # Scopo: campi sconosciuti nel payload -> errore esplicito, non ignorati.
    def test_fn_create_articolo_unknown_key(self):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_create_articolo(
                {"codice": "ART-001", "descrizione": "Articolo demo", "descrizionee": "typo"}
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: FK float in PATCH -> errore, niente cast implicito a int.
    def test_fn_update_articolo_float_fk_invalid(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d", {"uom_id": 1.2})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: create UoM operativa -> insert e rilettura riga arricchita.
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_uom_operativa_ok(self, mock_repo_cls, mock_uom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_uom_operativa

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        uom_repo = mock_uom_repo_cls.return_value
        uom_repo.create_uom_operativa.return_value = 11
        uom_repo.get_uom_operativa.return_value = {"id": 11, "uom_id": 3, "uom_codice": "PZ"}

        result = fn_create_uom_operativa("art-1", {"uom_id": 3, "factor_to_base": "1"})

        self.assertEqual(result["id"], 11)
        uom_repo.create_uom_operativa.assert_called_once()

    # Scopo: update UoM su riga assente -> 404 dominio catalogo.
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_update_uom_operativa_not_found(self, mock_repo_cls, mock_uom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_update_uom_operativa

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        mock_uom_repo_cls.return_value.update_uom_operativa.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            fn_update_uom_operativa("art-1", 77, {"factor_to_base": "2"})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_UOM_NOT_FOUND")

    # Scopo: create componente -> insert e rilettura riga arricchita.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_componente_ok(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_componente

        comp_id = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.create_componente.return_value = comp_id
        bom_repo.get_componente.return_value = {"id": comp_id, "coeff_qta": 1}

        result = fn_create_componente(
            "art-1",
            {"componente_id": comp_id, "coeff_qta": "1", "valido_dal": "2026-01-01"},
        )

        self.assertEqual(result["id"], comp_id)

    # Scopo: tentativo di update componente_id -> errore per immutabilita'.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_update_componente_immutabile(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_update_componente

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        with self.assertRaises(ServiceError) as ctx:
            fn_update_componente(
                "art-1",
                "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                {"componente_id": "00000000-0000-0000-0000-000000000000"},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: create nota articolo -> insert e rilettura nota arricchita.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_nota_articolo_ok(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_nota_articolo

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.create_nota_articolo.return_value = 5
        # Shape allineata al pattern partizionato vendite (2026-05-22):
        # alias senza prefisso `nota_` (id/testo invece di nota_id/nota_testo).
        bom_repo.get_nota_articolo.return_value = {"id": 5, "testo": "Demo"}

        result = fn_create_nota_articolo("art-1", {"id_stile": 1, "testo": "Demo"})

        self.assertEqual(result["id"], 5)

    # Scopo: create nota articolo senza target_riga_id -> anchor_tipo/posizione
    # default DOCUMENTO/HEADER applicati dal service (allineamento col pattern
    # vendite PartitionedNoteService). Verifica che il payload passato al repo
    # contenga i default — senza questi i NOT NULL DB su anchor_tipo/posizione
    # rifiuterebbero l'INSERT (regression check per il bug E_CATALOGO_VALIDATION
    # rilevato durante lo smoke Fase 2.B del refactor UI drawer).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_nota_articolo_default_documento_header(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_nota_articolo

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.create_nota.return_value = 5
        bom_repo.get_nota_articolo.return_value = {"id": 5}

        fn_create_nota_articolo("art-1", {"id_stile": 1, "testo_md": "Demo"})

        # Verifica argomento `data` passato al repo: deve contenere i default.
        bom_repo.create_nota.assert_called_once()
        _, _, data_arg = bom_repo.create_nota.call_args.args
        self.assertEqual(data_arg["anchor_tipo"], "DOCUMENTO")
        self.assertEqual(data_arg["posizione"], "HEADER")

    # Scopo: create nota componente con target_riga_id -> anchor_tipo/posizione
    # default RIGA/AFTER applicati dal service.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    def test_fn_create_nota_componente_default_riga_after(self, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_nota_componente

        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.create_nota.return_value = 7
        bom_repo.get_nota_componente.return_value = {"id": 7}

        riga_uuid = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        fn_create_nota_componente(
            "comp-1",
            {"id_stile": 1, "testo_md": "Demo", "target_riga_id": riga_uuid},
        )

        bom_repo.create_nota.assert_called_once()
        _, _, data_arg = bom_repo.create_nota.call_args.args
        self.assertEqual(data_arg["anchor_tipo"], "RIGA")
        self.assertEqual(data_arg["posizione"], "AFTER")
        self.assertEqual(str(data_arg["target_riga_id"]), riga_uuid)

    # Scopo: create nota con coppia incoerente anchor_tipo='DOCUMENTO' +
    # target_riga_id valorizzato -> errore E_CATALOGO_VALIDATION (guard
    # defense-in-depth simmetrica a vendite).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_nota_articolo_anchor_riga_inconsistency(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_nota_articolo

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        del mock_bom_repo_cls  # repo non viene mai chiamato

        riga_uuid = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        with self.assertRaises(ServiceError) as ctx:
            fn_create_nota_articolo(
                "art-1",
                {
                    "id_stile": 1,
                    "testo_md": "Demo",
                    "anchor_tipo": "DOCUMENTO",
                    "target_riga_id": riga_uuid,
                },
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: update nota inesistente -> 404 dominio catalogo.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    def test_fn_update_nota_not_found(self, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_update_nota

        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.resolve_nota.return_value = []

        with self.assertRaises(ServiceError) as ctx:
            fn_update_nota(999, {"testo": "Aggiornata"})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_NOTA_NOT_FOUND")

    # Scopo: create componente self-reference -> errore anticipato senza delega al DB.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_componente_self_reference(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_componente

        article_id = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        mock_repo_cls.return_value.get_articolo.return_value = {
            "id": article_id,
            "codice": "ART-001",
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_create_componente(
                article_id,
                {"componente_id": article_id, "coeff_qta": "1", "valido_dal": "2026-01-01"},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: create articolo con listino_tipologia_id -> campo propagato al repo (pricing v5).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_articolo_listino_tipologia_id_ok(
        self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls
    ):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        repo = mock_repo_cls.return_value
        repo.create_articolo.return_value = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "ART-001",
            "descrizione": "Articolo demo",
            "listino_tipologia_id": 3,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_componenti.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        fn_create_articolo(
            {
                "codice": "ART-001",
                "descrizione": "Articolo demo",
                "uom_id": 1,
                "listino_tipologia_id": 3,
            }
        )

        repo.create_articolo.assert_called_once_with(
            {
                "codice": "ART-001",
                "descrizione": "Articolo demo",
                "uom_id": 1,
                "listino_tipologia_id": 3,
            }
        )

    # Scopo: update articolo con listino_tipologia_id non intero -> validazione.
    def test_fn_update_articolo_listino_tipologia_id_invalid(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo(
                "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                {"listino_tipologia_id": 1.5},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("listino_tipologia_id", ctx.exception.detail or "")

    # Scopo: create articolo con natura_vendita_id -> campo propagato al repo
    # (modello split per natura: instradamento ordine/commessa/contratto).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_articolo_natura_vendita_id_ok(
        self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls
    ):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        repo = mock_repo_cls.return_value
        repo.create_articolo.return_value = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "SERV-001",
            "descrizione": "Servizio una tantum demo",
            "natura_vendita_id": 2,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_componenti.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        fn_create_articolo(
            {
                "codice": "SERV-001",
                "descrizione": "Servizio una tantum demo",
                "uom_id": 1,
                "natura_vendita_id": 2,
            }
        )

        repo.create_articolo.assert_called_once_with(
            {
                "codice": "SERV-001",
                "descrizione": "Servizio una tantum demo",
                "uom_id": 1,
                "natura_vendita_id": 2,
            }
        )

    # Scopo: update articolo con natura_vendita_id null -> validazione (colonna
    # NOT NULL: la natura si puo' cambiare ma mai azzerare).
    def test_fn_update_articolo_natura_vendita_id_null_invalid(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo(
                "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                {"natura_vendita_id": None},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("natura_vendita_id", ctx.exception.detail or "")

    # Scopo: create componente con esposto_in_fattura -> flag propagato al repo (BoM v5).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_componente_esposto_in_fattura_ok(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_componente

        comp_id = "019bbee2-5f6a-704f-bbd0-34ed84db252e"
        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.create_componente.return_value = comp_id
        bom_repo.get_componente.return_value = {"id": comp_id, "esposto_in_fattura": True}

        fn_create_componente(
            "art-1",
            {
                "componente_id": comp_id,
                "coeff_qta": "1",
                "valido_dal": "2026-01-01",
                "esposto_in_fattura": True,
            },
        )

        args, _ = bom_repo.create_componente.call_args
        self.assertEqual(args[1]["esposto_in_fattura"], True)

    # Scopo: lookup statico rounding modes -> 5 codici nell'ordine canonico
    # con descrizione popolata. Niente DB: la funzione e' pura.
    def test_fn_list_uom_rounding_modes_ok(self):
        from apps.catalogo.services.catalogo_service import fn_list_uom_rounding_modes

        result = fn_list_uom_rounding_modes()

        self.assertEqual(len(result), 5)
        codici = [r["codice"] for r in result]
        self.assertEqual(codici, ["HALF_UP", "HALF_DOWN", "HALF_EVEN", "UP", "DOWN"])
        for row in result:
            self.assertTrue(row["descrizione"])
            self.assertIsInstance(row["ordering"], int)

    # Scopo: difesa coerenza enum/descrizioni. Se in futuro qualcuno aggiunge
    # un codice a `_ROUNDING_MODE_VALIDI` senza aggiornare la mappa descrizioni,
    # il test della funzione fallisce con messaggio chiaro (ErrorManager.require).
    def test_fn_list_uom_rounding_modes_coverage(self):
        from apps.catalogo.services import catalogo_service as svc

        descritti = {codice for codice, _desc, _ord in svc._ROUNDING_MODE_DESCRIZIONI}
        self.assertEqual(descritti, svc._ROUNDING_MODE_VALIDI)

    # =================================================================
    # Fase 4 — fallback valido_dal=today lato service (DB declined)
    # =================================================================

    # Scopo: payload create componente senza valido_dal -> service applica
    # date.today() prima del repository call. Il DDL DB non ha
    # DEFAULT CURRENT_DATE, il fallback vive nel service (Fase 4 BE-only).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_componente_valido_dal_fallback_today(self, mock_repo_cls, mock_bom_repo_cls):
        from datetime import date

        from apps.catalogo.services.catalogo_service import fn_create_componente

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1"}
        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.create_componente.return_value = "comp-1"
        bom_repo.get_componente.return_value = {"id": "comp-1"}

        # Payload SENZA valido_dal: il service deve applicare today.
        fn_create_componente(
            "art-1",
            {"componente_id": "019bbee2-5f6a-704f-bbd0-34ed84db252f", "coeff_qta": "1"},
        )

        args = bom_repo.create_componente.call_args.args
        self.assertEqual(args[1]["valido_dal"], date.today())

    # Scopo: payload create UoM operativa senza valido_dal -> service applica today.
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_uom_operativa_valido_dal_fallback_today(self, mock_repo_cls, mock_uom_repo_cls):
        from datetime import date

        from apps.catalogo.services.catalogo_service import fn_create_uom_operativa

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1"}
        uom_repo = mock_uom_repo_cls.return_value
        uom_repo.create_uom_operativa.return_value = 99
        uom_repo.get_uom_operativa.return_value = {"id": 99}

        # Payload SENZA valido_dal.
        fn_create_uom_operativa("art-1", {"uom_id": 1, "factor_to_base": "1"})

        args = uom_repo.create_uom_operativa.call_args.args
        self.assertEqual(args[1]["valido_dal"], date.today())

    # Scopo: payload create conversione UoM senza valido_dal -> service applica today.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_create_conversione_valido_dal_fallback_today(self, mock_repo_cls):
        from datetime import date

        from apps.catalogo.services.catalogo_service import fn_create_conversione

        repo = mock_repo_cls.return_value
        repo.create_conversione.return_value = 42
        repo.get_conversione.return_value = {"id": 42}

        # Payload SENZA valido_dal.
        fn_create_conversione({"uom_from_id": 1, "uom_to_id": 2, "fattore": "10"})

        args = repo.create_conversione.call_args.args
        self.assertEqual(args[0]["valido_dal"], date.today())

    # =================================================================
    # Fase 5 — non_editable_fields nei detail (cross-vista DB + gap Python)
    # =================================================================

    # Scopo: detail articolo include non_editable_fields. Almeno "codice" e
    # "uom_id" devono essere presenti (dal gap Python; DB potrebbe arricchire).
    # Mock LockColumnsRepository per evitare query DB reali sul testbed.
    @patch("apps.catalogo.services.catalogo_service.LockColumnsRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_get_articolo_includes_non_editable_fields(
        self, mock_repo_cls, mock_uom_cls, mock_bom_cls, mock_lock_cls,
    ):
        from apps.catalogo.services.catalogo_service import fn_get_articolo

        mock_repo_cls.return_value.get_articolo.return_value = {"id": 1, "is_composito": False}
        mock_uom_cls.return_value.list_uom_operative.return_value = []
        mock_bom_cls.return_value.list_note_articolo.return_value = []
        # DB vuoto: il gap Python e' l'unica fonte.
        mock_lock_cls.list_non_editable.return_value = ()

        result = fn_get_articolo(1)

        self.assertIn("non_editable_fields", result)
        # Gap Python copre "codice"; DB esprime "uom_id" via vista (qui mock vuoto).
        self.assertIn("codice", result["non_editable_fields"])

    # Scopo: lista UoM operative espone non_editable_fields envelope-level.
    @patch("apps.catalogo.services.catalogo_service.LockColumnsRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_list_uom_operative_envelope_non_editable_fields(
        self, mock_repo_cls, mock_uom_cls, mock_lock_cls,
    ):
        from apps.catalogo.services.catalogo_service import fn_list_uom_operative

        mock_repo_cls.return_value.get_articolo.return_value = {"id": 1}
        mock_uom_cls.return_value.list_uom_operative.return_value = []
        mock_lock_cls.list_non_editable.return_value = ()

        result = fn_list_uom_operative(1)

        self.assertEqual(result["non_editable_fields"], ["uom_id"])

    # Scopo: detail conversione UoM include non_editable_fields (uom_from_id, uom_to_id).
    @patch("apps.catalogo.services.catalogo_service.LockColumnsRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_get_conversione_includes_non_editable_fields(self, mock_repo_cls, mock_lock_cls):
        from apps.catalogo.services.catalogo_service import fn_get_conversione

        mock_repo_cls.return_value.get_conversione.return_value = {"id": 7}
        mock_lock_cls.list_non_editable.return_value = ()

        result = fn_get_conversione(7)

        self.assertEqual(result["non_editable_fields"], ["uom_from_id", "uom_to_id"])

    # Scopo: lista articoli propaga capability BoM dalla vista DB (Fase 6).
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_list_articoli_proietta_capability_bom(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_list_articoli

        mock_repo_cls.return_value.list_articoli.return_value = (
            [
                {
                    "id": 1,
                    "codice": "ART-COMP",
                    "is_composito": True,
                    "is_solo_componente": False,
                    "puo_gestire_bom": True,
                    "motivo_non_gestibile_bom": None,
                },
                {
                    "id": 2,
                    "codice": "ART-FOGLIA",
                    "is_composito": False,
                    "is_solo_componente": False,
                    "puo_gestire_bom": False,
                    "motivo_non_gestibile_bom": "ARTICOLO_NON_COMPOSITO",
                },
            ],
            2,
        )

        results, total = fn_list_articoli(limit=25, offset=0)

        self.assertEqual(total, 2)
        self.assertTrue(results[0]["puo_gestire_bom"])
        self.assertIsNone(results[0]["motivo_non_gestibile_bom"])
        self.assertFalse(results[1]["puo_gestire_bom"])
        self.assertEqual(results[1]["motivo_non_gestibile_bom"], "ARTICOLO_NON_COMPOSITO")

    # Scopo: lista UoM operative propaga capability eliminazione dalla vista DB (Fase 6).
    @patch("apps.catalogo.services.catalogo_service.LockColumnsRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository")
    def test_fn_list_uom_operative_proietta_capability_eliminabile(
        self, mock_repo_cls, mock_uom_cls, mock_lock_cls,
    ):
        from apps.catalogo.services.catalogo_service import fn_list_uom_operative

        mock_repo_cls.return_value.get_articolo.return_value = {"id": 1}
        mock_uom_cls.return_value.list_uom_operative.return_value = [
            {
                "id": 10,
                "uom_codice": "PZ",
                "is_base": True,
                "puo_eliminarsi": False,
                "motivo_non_eliminabile": "UOM_BASE_NON_ELIMINABILE",
            },
            {
                "id": 11,
                "uom_codice": "CT",
                "is_base": False,
                "puo_eliminarsi": True,
                "motivo_non_eliminabile": None,
            },
        ]
        mock_lock_cls.list_non_editable.return_value = ()

        result = fn_list_uom_operative(1)

        rows = result["results"]
        self.assertFalse(rows[0]["puo_eliminarsi"])
        self.assertEqual(rows[0]["motivo_non_eliminabile"], "UOM_BASE_NON_ELIMINABILE")
        self.assertTrue(rows[1]["puo_eliminarsi"])
        self.assertIsNone(rows[1]["motivo_non_eliminabile"])
