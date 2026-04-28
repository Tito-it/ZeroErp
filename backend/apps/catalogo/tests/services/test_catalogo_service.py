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
24) CatalogoServiceTests.test_fn_update_nota_not_found
25) CatalogoServiceTests.test_fn_create_componente_self_reference
26) CatalogoServiceTests.test_fn_create_articolo_listino_tipologia_id_ok
27) CatalogoServiceTests.test_fn_update_articolo_listino_tipologia_id_invalid
28) CatalogoServiceTests.test_fn_create_componente_esposto_in_fattura_ok
29) CatalogoServiceTests.test_fn_list_uom_rounding_modes_ok
30) CatalogoServiceTests.test_fn_list_uom_rounding_modes_coverage
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
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = [{"nota_id": 9}]

        result = fn_get_articolo(7)

        self.assertEqual(result["id"], 7)
        self.assertEqual(result["codice"], "ART-007")
        self.assertEqual(result["uom_operative"][0]["uom_codice"], "PZ")
        self.assertEqual(result["componenti"][0]["id"], "comp-1")
        self.assertEqual(result["note"][0]["nota_id"], 9)

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
        bom_repo.get_nota_articolo.return_value = {"nota_id": 5, "nota_testo": "Demo"}

        result = fn_create_nota_articolo("art-1", {"id_stile": 1, "testo": "Demo"})

        self.assertEqual(result["nota_id"], 5)

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
