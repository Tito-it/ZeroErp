# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test service anagrafiche.categorie_clienti_listini. Mock del
#        repository (nessun accesso DB), verifica validazione FK, coerenza
#        tipo/valore variazione, date range, immutabilita' dimensioni,
#        mapping IntegrityError/ExclusionViolation su codici parlanti.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_default_params                      — delega repo con default order valido_dal desc
 2) test_list_invalid_order_by                    — order_by non whitelisted -> VALIDAZIONE
 3) test_list_propaga_filtri                      — filtri dimensionali passati al repo
 4) test_get_ok                                   — get ritorna dict dal repo
 5) test_get_not_found                            — repo None -> NOT_FOUND
 6) test_get_id_non_positivo                      — id <= 0 -> VALIDAZIONE
 7) test_create_minimo_ok                         — payload con 4 FK + valido_dal ok
 8) test_create_con_variazione_percentuale_ok     — tipo_variazione + valore_variazione coerenti
 9) test_create_con_classe_utenza_ok              — classe_utenza_id opzionale valorizzato
10) test_create_senza_classe_utenza_ok_null       — classe_utenza_id NULL = fallback generico
11) test_create_missing_categoria                 — manca categoria_cliente_id -> VALIDAZIONE
12) test_create_missing_valido_dal                — manca valido_dal -> VALIDAZIONE
13) test_create_unknown_key                       — chiave extra -> VALIDAZIONE
14) test_create_fk_zero                           — utility_id=0 -> VALIDAZIONE
15) test_create_tipo_variazione_invalido          — enum non ammesso -> VALIDAZIONE
16) test_create_tipo_senza_valore                 — tipo_variazione ma valore_variazione assente -> VALIDAZIONE
17) test_create_valore_senza_tipo                 — valore_variazione ma tipo assente -> VALIDAZIONE
18) test_create_delega_ordine_date_al_db         — valido_al < valido_dal arriva al DB (guard comune)
19) test_create_valido_dal_formato_invalido       — data non ISO -> VALIDAZIONE
20) test_create_valore_non_numerico               — valore_variazione string non numerica -> VALIDAZIONE
21) test_create_duplicate_overlap                 — ExclusionViolation -> E_ANAG_MATRICE_OVERLAP
22) test_create_fk_inesistente                    — ForeignKeyViolation -> E_ANAG_FK
23) test_update_mutabile_ok                       — PATCH su campi mutabili OK
24) test_update_immutabile_categoria_rifiutato    — categoria_cliente_id nel PATCH -> VALIDAZIONE
25) test_update_immutabile_utility_rifiutato      — utility_id nel PATCH -> VALIDAZIONE
26) test_update_immutabile_emittente_rifiutato    — emittente nel PATCH -> VALIDAZIONE
27) test_update_immutabile_classe_rifiutato       — classe_utenza_id nel PATCH -> VALIDAZIONE
28) test_update_variazione_reset_coerente         — PATCH tipo=None + valore=None ammesso
29) test_update_variazione_incoerente_rifiutato   — PATCH solo tipo senza valore -> VALIDAZIONE
30) test_update_payload_vuoto                     — PATCH senza campi mutabili -> VALIDAZIONE
31) test_update_not_found                         — repo update=False -> NOT_FOUND
32) test_update_attivo_null_rifiutato             — PATCH attivo=None -> VALIDAZIONE
"""

from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError

from apps.anagrafiche.services.categorie_clienti_listini_service import (
    CategorieClientiListiniService,
)
from apps.core.services.service_errors import ServiceError


_REPO_PATH = (
    "apps.anagrafiche.services.categorie_clienti_listini_service."
    "CategorieClientiListiniRepository"
)


def _base_payload(**overrides):
    """Payload minimo valido per create."""
    data = {
        "categoria_cliente_id": 1,
        "utility_id": 2,
        "emittente_soggetto_ruolo_id": 3,
        "listino_id": 4,
        "valido_dal": "2026-01-01",
    }
    data.update(overrides)
    return data


class TestList(TestCase):
    """Test metodo list_matrice."""

    @patch(_REPO_PATH, autospec=True)
    def test_list_default_params(self, mock_repo_cls):
        mock_repo_cls.return_value.list_matrice.return_value = ([], 0)
        svc = CategorieClientiListiniService()
        results, total = svc.list_matrice()
        self.assertEqual(results, [])
        self.assertEqual(total, 0)
        kwargs = mock_repo_cls.return_value.list_matrice.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "valido_dal")
        self.assertEqual(kwargs["order_dir"], "desc")

    @patch(_REPO_PATH, autospec=True)
    def test_list_invalid_order_by(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.list_matrice(order_by="not_a_column")
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_list_propaga_filtri(self, mock_repo_cls):
        mock_repo_cls.return_value.list_matrice.return_value = ([], 0)
        svc = CategorieClientiListiniService()
        svc.list_matrice(
            search="std",
            attivo=True,
            categoria_cliente_id=5,
            utility_id=7,
            emittente_soggetto_ruolo_id=9,
            listino_id=11,
            valid_at=date(2026, 6, 1),
        )
        kwargs = mock_repo_cls.return_value.list_matrice.call_args.kwargs
        self.assertEqual(kwargs["search"], "std")
        self.assertTrue(kwargs["attivo"])
        self.assertEqual(kwargs["categoria_cliente_id"], 5)
        self.assertEqual(kwargs["utility_id"], 7)
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 9)
        self.assertEqual(kwargs["listino_id"], 11)
        self.assertEqual(kwargs["valid_at"], date(2026, 6, 1))


class TestGet(TestCase):
    """Test metodo get_matrice."""

    @patch(_REPO_PATH, autospec=True)
    def test_get_ok(self, mock_repo_cls):
        # Fase 4: get_matrice arricchisce la response con non_editable_fields.
        mock_repo_cls.return_value.get_matrice.return_value = {"id": 3}
        svc = CategorieClientiListiniService()
        result = svc.get_matrice(3)
        self.assertEqual(result["id"], 3)
        self.assertIn("non_editable_fields", result)
        self.assertIn("categoria_cliente_id", result["non_editable_fields"])

    @patch(_REPO_PATH, autospec=True)
    def test_get_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.get_matrice.return_value = None
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.get_matrice(999)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(_REPO_PATH, autospec=True)
    def test_get_id_non_positivo(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.get_matrice(0)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


class TestCreate(TestCase):
    """Test metodo create_matrice (scenari validi e validazione)."""

    @patch(_REPO_PATH, autospec=True)
    def test_create_minimo_ok(self, mock_repo_cls):
        mock_repo_cls.return_value.create_matrice.return_value = 10
        mock_repo_cls.return_value.get_matrice.return_value = {"id": 10}
        svc = CategorieClientiListiniService()
        result = svc.create_matrice(_base_payload())
        self.assertEqual(result["id"], 10)
        data = mock_repo_cls.return_value.create_matrice.call_args.args[0]
        self.assertEqual(data["categoria_cliente_id"], 1)
        self.assertEqual(data["valido_dal"], date(2026, 1, 1))
        self.assertIsNone(data["classe_utenza_id"])
        self.assertNotIn("tipo_variazione", data)

    @patch(_REPO_PATH, autospec=True)
    def test_create_con_variazione_percentuale_ok(self, mock_repo_cls):
        mock_repo_cls.return_value.create_matrice.return_value = 1
        mock_repo_cls.return_value.get_matrice.return_value = {"id": 1}
        svc = CategorieClientiListiniService()
        svc.create_matrice(_base_payload(
            tipo_variazione="PERCENTUALE",
            valore_variazione="5.25",
        ))
        data = mock_repo_cls.return_value.create_matrice.call_args.args[0]
        self.assertEqual(data["tipo_variazione"], "PERCENTUALE")
        self.assertEqual(data["valore_variazione"], Decimal("5.25"))

    @patch(_REPO_PATH, autospec=True)
    def test_create_con_classe_utenza_ok(self, mock_repo_cls):
        mock_repo_cls.return_value.create_matrice.return_value = 1
        mock_repo_cls.return_value.get_matrice.return_value = {"id": 1}
        svc = CategorieClientiListiniService()
        svc.create_matrice(_base_payload(classe_utenza_id=7))
        data = mock_repo_cls.return_value.create_matrice.call_args.args[0]
        self.assertEqual(data["classe_utenza_id"], 7)

    @patch(_REPO_PATH, autospec=True)
    def test_create_senza_classe_utenza_ok_null(self, mock_repo_cls):
        mock_repo_cls.return_value.create_matrice.return_value = 1
        mock_repo_cls.return_value.get_matrice.return_value = {"id": 1}
        svc = CategorieClientiListiniService()
        svc.create_matrice(_base_payload(classe_utenza_id=None))
        data = mock_repo_cls.return_value.create_matrice.call_args.args[0]
        self.assertIsNone(data["classe_utenza_id"])

    @patch(_REPO_PATH, autospec=True)
    def test_create_missing_categoria(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        payload = _base_payload()
        del payload["categoria_cliente_id"]
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(payload)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_missing_valido_dal(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        payload = _base_payload()
        del payload["valido_dal"]
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(payload)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_unknown_key(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(_base_payload(colonna_ignota=1))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_fk_zero(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(_base_payload(utility_id=0))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_tipo_variazione_invalido(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(_base_payload(
                tipo_variazione="NON_VALIDO",
                valore_variazione="1.0",
            ))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        # ⭐ Dal 2026-09-18 (BB `optional_enum`) il rifiuto NOMINA il campo: la
        #    copia locale scriveva `{"tipo_variazione": tipo}` e il form non
        #    accendeva niente. E un tipo non-stringa e' un 400, non un 500.
        self.assertEqual(ctx.exception.context["field"], "tipo_variazione")
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(_base_payload(tipo_variazione=3, valore_variazione="1.0"))
        self.assertEqual(ctx.exception.context["field"], "tipo_variazione")

    @patch(_REPO_PATH, autospec=True)
    def test_create_tipo_senza_valore(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(_base_payload(tipo_variazione="PERCENTUALE"))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_valore_senza_tipo(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(_base_payload(valore_variazione="1.0"))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    # L'ordine delle date NON lo giudica il service: il guard comune del DB
    # risponde E_DATA_AL_MINORE_DAL col campo (provato sul DB vero in
    # apps/core/tests/db/test_date_validita_guard_comune_db).
    @patch(_REPO_PATH, autospec=True)
    def test_create_delega_ordine_date_al_db(self, mock_repo_cls):
        mock_repo_cls.return_value.create_matrice.return_value = 10
        mock_repo_cls.return_value.get_matrice.return_value = {"id": 10}
        svc = CategorieClientiListiniService()
        svc.create_matrice(_base_payload(
            valido_dal="2026-06-01",
            valido_al="2026-01-01",
        ))
        data = mock_repo_cls.return_value.create_matrice.call_args.args[0]
        self.assertEqual(
            (data["valido_dal"], data["valido_al"]),
            (date(2026, 6, 1), date(2026, 1, 1)),
        )

    @patch(_REPO_PATH, autospec=True)
    def test_create_valido_dal_formato_invalido(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(_base_payload(valido_dal="non-valida"))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_valore_non_numerico(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(_base_payload(
                tipo_variazione="PERCENTUALE",
                valore_variazione="abc",
            ))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_duplicate_overlap(self, mock_repo_cls):
        mock_repo_cls.return_value.create_matrice.side_effect = IntegrityError(
            'conflicting key value violates exclusion constraint '
            '"ex_categ_cli_listini_no_overlap"'
        )
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(_base_payload())
        self.assertEqual(ctx.exception.code, "E_ANAG_MATRICE_OVERLAP")

    @patch(_REPO_PATH, autospec=True)
    def test_create_fk_inesistente(self, mock_repo_cls):
        mock_repo_cls.return_value.create_matrice.side_effect = IntegrityError(
            'insert or update on table violates foreign key constraint '
            '"fk_categ_cli_listini_listino"'
        )
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice(_base_payload())
        self.assertEqual(ctx.exception.code, "E_ANAG_FK")


class TestUpdate(TestCase):
    """Test metodo update_matrice."""

    @patch(_REPO_PATH, autospec=True)
    def test_update_mutabile_ok(self, mock_repo_cls):
        mock_repo_cls.return_value.update_matrice.return_value = True
        mock_repo_cls.return_value.get_matrice.return_value = {"id": 3}
        svc = CategorieClientiListiniService()
        result = svc.update_matrice(3, {"listino_id": 99, "attivo": False})
        self.assertEqual(result["id"], 3)
        data = mock_repo_cls.return_value.update_matrice.call_args.args[1]
        self.assertEqual(data["listino_id"], 99)
        self.assertFalse(data["attivo"])

    @patch(_REPO_PATH, autospec=True)
    def test_update_immutabile_categoria_rifiutato(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_matrice(3, {"categoria_cliente_id": 5})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_update_immutabile_utility_rifiutato(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_matrice(3, {"utility_id": 5})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_update_immutabile_emittente_rifiutato(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_matrice(3, {"emittente_soggetto_ruolo_id": 5})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_update_immutabile_classe_rifiutato(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_matrice(3, {"classe_utenza_id": 5})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_update_variazione_reset_coerente(self, mock_repo_cls):
        mock_repo_cls.return_value.update_matrice.return_value = True
        mock_repo_cls.return_value.get_matrice.return_value = {"id": 3}
        svc = CategorieClientiListiniService()
        svc.update_matrice(3, {"tipo_variazione": None, "valore_variazione": None})
        data = mock_repo_cls.return_value.update_matrice.call_args.args[1]
        self.assertIsNone(data["tipo_variazione"])
        self.assertIsNone(data["valore_variazione"])

    @patch(_REPO_PATH, autospec=True)
    def test_update_variazione_incoerente_rifiutato(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_matrice(3, {"tipo_variazione": "PERCENTUALE"})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_update_payload_vuoto(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_matrice(3, {})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_update_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.update_matrice.return_value = False
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_matrice(999, {"listino_id": 7})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(_REPO_PATH, autospec=True)
    def test_update_attivo_null_rifiutato(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiListiniService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_matrice(3, {"attivo": None})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


# =================================================================
# Fase 4 — lookup statici + non_editable_fields
# =================================================================


class TestListTipiVariazione(TestCase):
    """Lookup statico dei tipi di variazione (Fase 4 — A7)."""

    def test_list_tipi_variazione_ok(self):
        # 2 codici nell'ordine canonico "default-first" (PERCENTUALE primo).
        svc = CategorieClientiListiniService()
        result = svc.list_tipi_variazione()
        self.assertEqual(len(result), 2)
        codici = [r["codice"] for r in result]
        self.assertEqual(codici, ["PERCENTUALE", "VALORE_FISSO"])
        for row in result:
            self.assertTrue(row["descrizione"])
            self.assertIsInstance(row["ordering"], int)

    def test_list_tipi_variazione_coverage(self):
        # Difesa coerenza enum/descrizioni: il lookup statico copre l'enum
        # validation usato in create/update.
        from apps.anagrafiche.services import categorie_clienti_listini_service as svc_mod
        descritti = {codice for codice, _, _ in svc_mod._TIPI_VARIAZIONE_DESCRIZIONI}
        self.assertEqual(descritti, svc_mod._TIPI_VARIAZIONE)


class TestNonEditableFieldsCategorie(TestCase):
    """non_editable_fields per matrice categorie/listini (Fase 4 — A9)."""

    @patch("apps.core.services.non_editable_fields_helper.LockColumnsRepository.list_non_editable", autospec=True)
    def test_get_non_editable_fields_include_dimensions(self, mock_list):
        # Le 4 dimensioni (categoria, utility, emittente, classe_utenza) sono
        # esposte come metadata immutabili anche se il registro DB non le ha
        # ancora registrate (gap dominio).
        mock_list.return_value = ()  # registro DB vuoto
        svc = CategorieClientiListiniService()
        result = svc.get_non_editable_fields()
        self.assertEqual(set(result), {
            "categoria_cliente_id", "utility_id",
            "emittente_soggetto_ruolo_id", "classe_utenza_id",
        })
