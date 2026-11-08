# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test service anagrafiche.categorie_clienti. Mock del repository
#        (nessun accesso DB), verifica validazioni payload, coercizione
#        tipi e mapping IntegrityError -> codici errore parlanti.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_default_params — delega al repo con default
 2) test_list_invalid_order_by — order_by non whitelisted -> VALIDAZIONE
 3) test_list_propaga_filtri — filtri (attivo, partecipa_promo) passati al repo
 4) test_get_ok — get ritorna dict dal repo
 5) test_get_not_found — repo None -> NOT_FOUND
 6) test_get_id_non_positivo — id <= 0 -> VALIDAZIONE
 7) test_create_ok — payload valido -> repo.create + repo.get
 8) test_create_missing_codice — codice assente -> VALIDAZIONE
 9) test_create_missing_descrizione — descrizione assente -> VALIDAZIONE
10) test_create_unknown_key — chiave extra -> VALIDAZIONE
11) test_create_codice_troppo_lungo — codice > 32 char -> VALIDAZIONE
12) test_create_partecipa_promo_non_bool — int invece di bool -> VALIDAZIONE
13) test_create_ordinamento_fuori_range — > 32767 -> VALIDAZIONE
14) test_create_meta_json_invalido — string non-JSON -> VALIDAZIONE
15) test_create_duplicate_unique — IntegrityError UNIQUE -> DUPLICATO
16) test_update_ok — payload valido PATCH -> repo.update + repo.get
17) test_update_codice_rifiutato — codice immutabile -> VALIDAZIONE
18) test_update_payload_vuoto — nessun campo -> VALIDAZIONE
19) test_update_partecipa_promo_null — null esplicito rifiutato -> VALIDAZIONE
20) test_update_not_found — repo update=False -> NOT_FOUND
"""

from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError

from apps.anagrafiche.services.categorie_clienti_service import (
    CategorieClientiService,
)
from apps.core.services.service_errors import ServiceError


_REPO_PATH = (
    "apps.anagrafiche.services.categorie_clienti_service.CategorieClientiRepository"
)


class TestList(TestCase):
    """Test metodo list_categorie."""

    @patch(_REPO_PATH, autospec=True)
    def test_list_default_params(self, mock_repo_cls):
        mock_repo_cls.return_value.list_categorie.return_value = ([], 0)
        svc = CategorieClientiService()
        results, total = svc.list_categorie()
        self.assertEqual(results, [])
        self.assertEqual(total, 0)
        mock_repo_cls.return_value.list_categorie.assert_called_once()

    @patch(_REPO_PATH, autospec=True)
    def test_list_invalid_order_by(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.list_categorie(order_by="not_a_column")
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_list_propaga_filtri(self, mock_repo_cls):
        mock_repo_cls.return_value.list_categorie.return_value = ([], 0)
        svc = CategorieClientiService()
        svc.list_categorie(search="silv", attivo=True, partecipa_promo=False)
        kwargs = mock_repo_cls.return_value.list_categorie.call_args.kwargs
        self.assertEqual(kwargs["search"], "silv")
        self.assertTrue(kwargs["attivo"])
        self.assertFalse(kwargs["partecipa_promo"])


class TestGet(TestCase):
    """Test metodo get_categoria."""

    @patch(_REPO_PATH, autospec=True)
    def test_get_ok(self, mock_repo_cls):
        mock_repo_cls.return_value.get_categoria.return_value = {
            "id": 3, "codice": "SILVER", "descrizione": "Cliente silver",
        }
        svc = CategorieClientiService()
        result = svc.get_categoria(3)
        self.assertEqual(result["codice"], "SILVER")

    @patch(_REPO_PATH, autospec=True)
    def test_get_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.get_categoria.return_value = None
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.get_categoria(999)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(_REPO_PATH, autospec=True)
    def test_get_id_non_positivo(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.get_categoria(0)
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


class TestCreate(TestCase):
    """Test metodo create_categoria."""

    @patch(_REPO_PATH, autospec=True)
    def test_create_ok(self, mock_repo_cls):
        mock_repo_cls.return_value.create_categoria.return_value = 10
        mock_repo_cls.return_value.get_categoria.return_value = {
            "id": 10, "codice": "SILVER", "descrizione": "Cliente silver",
            "partecipa_promo": True, "ordinamento": 30, "attivo": True,
        }
        svc = CategorieClientiService()
        result = svc.create_categoria({
            "codice": "SILVER",
            "descrizione": "Cliente silver",
            "partecipa_promo": True,
            "ordinamento": 30,
        })
        self.assertEqual(result["id"], 10)
        mock_repo_cls.return_value.create_categoria.assert_called_once()
        # Verifica trim implicito
        args = mock_repo_cls.return_value.create_categoria.call_args.args
        self.assertEqual(args[0]["codice"], "SILVER")

    @patch(_REPO_PATH, autospec=True)
    def test_create_missing_codice(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_categoria({"descrizione": "X"})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_missing_descrizione(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_categoria({"codice": "X"})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_unknown_key(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_categoria({
                "codice": "X", "descrizione": "X", "colonna_ignota": 1,
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_codice_troppo_lungo(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_categoria({"codice": "X" * 33, "descrizione": "X"})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_partecipa_promo_non_bool(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_categoria({
                "codice": "X", "descrizione": "X", "partecipa_promo": 1,
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_ordinamento_fuori_range(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_categoria({
                "codice": "X", "descrizione": "X", "ordinamento": 50000,
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_meta_json_invalido(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_categoria({
                "codice": "X", "descrizione": "X", "meta": "not-valid-json{",
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_duplicate_unique(self, mock_repo_cls):
        mock_repo_cls.return_value.create_categoria.side_effect = IntegrityError(
            'duplicate key value violates unique constraint "uq_categorie_clienti_codice"'
        )
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_categoria({"codice": "STANDARD", "descrizione": "X"})
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")


class TestUpdate(TestCase):
    """Test metodo update_categoria."""

    @patch(_REPO_PATH, autospec=True)
    def test_update_ok(self, mock_repo_cls):
        mock_repo_cls.return_value.update_categoria.return_value = True
        mock_repo_cls.return_value.get_categoria.return_value = {
            "id": 3, "codice": "SILVER", "descrizione": "Cliente SILVER v2",
        }
        svc = CategorieClientiService()
        result = svc.update_categoria(3, {"descrizione": "Cliente SILVER v2"})
        self.assertEqual(result["descrizione"], "Cliente SILVER v2")
        mock_repo_cls.return_value.update_categoria.assert_called_once()

    @patch(_REPO_PATH, autospec=True)
    def test_update_codice_rifiutato(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_categoria(3, {"codice": "NUOVO"})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_update_payload_vuoto(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_categoria(3, {})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_update_partecipa_promo_null(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_categoria(3, {"partecipa_promo": None})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_update_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.update_categoria.return_value = False
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_categoria(999, {"descrizione": "X"})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")


class TestMetaSemantics(TestCase):
    """Test della semantica del campo meta (jsonb).

    Regole blindate:
    - chiave assente  -> non scrive (preserva valore DB)
    - meta = None     -> reset esplicito a {} (scrive)
    - meta = {}       -> scrive {}
    - meta = dict     -> scrive il dict
    - meta = str JSON -> parse + scrive dict
    - meta = str non-JSON -> E_ANAG_VALIDAZIONE
    - meta = lista/non-dict -> E_ANAG_VALIDAZIONE
    """

    @patch(_REPO_PATH, autospec=True)
    def test_create_meta_assente_non_passa_al_repo(self, mock_repo_cls):
        mock_repo_cls.return_value.create_categoria.return_value = 1
        mock_repo_cls.return_value.get_categoria.return_value = {"id": 1}
        svc = CategorieClientiService()
        svc.create_categoria({"codice": "X", "descrizione": "X"})
        data = mock_repo_cls.return_value.create_categoria.call_args.args[0]
        self.assertNotIn("meta", data)

    @patch(_REPO_PATH, autospec=True)
    def test_create_meta_null_esplicito_resetta_a_vuoto(self, mock_repo_cls):
        mock_repo_cls.return_value.create_categoria.return_value = 1
        mock_repo_cls.return_value.get_categoria.return_value = {"id": 1}
        svc = CategorieClientiService()
        svc.create_categoria({"codice": "X", "descrizione": "X", "meta": None})
        data = mock_repo_cls.return_value.create_categoria.call_args.args[0]
        self.assertEqual(data.get("meta"), {})

    @patch(_REPO_PATH, autospec=True)
    def test_create_meta_dict_preservato(self, mock_repo_cls):
        mock_repo_cls.return_value.create_categoria.return_value = 1
        mock_repo_cls.return_value.get_categoria.return_value = {"id": 1}
        svc = CategorieClientiService()
        svc.create_categoria({"codice": "X", "descrizione": "X",
                               "meta": {"nota": "test"}})
        data = mock_repo_cls.return_value.create_categoria.call_args.args[0]
        self.assertEqual(data["meta"], {"nota": "test"})

    @patch(_REPO_PATH, autospec=True)
    def test_create_meta_str_json_valida_parsed(self, mock_repo_cls):
        mock_repo_cls.return_value.create_categoria.return_value = 1
        mock_repo_cls.return_value.get_categoria.return_value = {"id": 1}
        svc = CategorieClientiService()
        svc.create_categoria({"codice": "X", "descrizione": "X",
                               "meta": '{"foo": 1}'})
        data = mock_repo_cls.return_value.create_categoria.call_args.args[0]
        self.assertEqual(data["meta"], {"foo": 1})

    @patch(_REPO_PATH, autospec=True)
    def test_create_meta_lista_rifiutata(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_categoria({"codice": "X", "descrizione": "X",
                                   "meta": [1, 2]})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_meta_str_json_non_dict_rifiutata(self, mock_repo_cls):
        # JSON valido ma non dict (es. array serializzato) deve essere rifiutato.
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_categoria({"codice": "X", "descrizione": "X",
                                   "meta": "[1, 2]"})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


class TestOrdinamentoBoundary(TestCase):
    """Test dei boundary di ordinamento (smallint 0..32767, niente negativi)."""

    @patch(_REPO_PATH, autospec=True)
    def test_create_ordinamento_zero_ammesso(self, mock_repo_cls):
        mock_repo_cls.return_value.create_categoria.return_value = 1
        mock_repo_cls.return_value.get_categoria.return_value = {"id": 1}
        svc = CategorieClientiService()
        svc.create_categoria({"codice": "X", "descrizione": "X",
                               "ordinamento": 0})
        data = mock_repo_cls.return_value.create_categoria.call_args.args[0]
        self.assertEqual(data["ordinamento"], 0)

    @patch(_REPO_PATH, autospec=True)
    def test_create_ordinamento_negativo_rifiutato(self, mock_repo_cls):
        del mock_repo_cls
        svc = CategorieClientiService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_categoria({"codice": "X", "descrizione": "X",
                                   "ordinamento": -1})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_REPO_PATH, autospec=True)
    def test_create_ordinamento_max_ammesso(self, mock_repo_cls):
        mock_repo_cls.return_value.create_categoria.return_value = 1
        mock_repo_cls.return_value.get_categoria.return_value = {"id": 1}
        svc = CategorieClientiService()
        svc.create_categoria({"codice": "X", "descrizione": "X",
                               "ordinamento": 32767})
        data = mock_repo_cls.return_value.create_categoria.call_args.args[0]
        self.assertEqual(data["ordinamento"], 32767)
