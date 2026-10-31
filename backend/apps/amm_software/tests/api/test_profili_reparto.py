# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API profili reparto modulo Amm. Software.
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_reparti — GET lista reparti con conteggi
 2) test_list_reparti_empty — GET lista reparti vuota
 2b) test_list_reparti_parametri_di_lista — search/order/pagina al repository
 2c) test_ordina_per_alias_della_cte — whitelist sugli alias della CTE
 2d) test_default_e_fuori_whitelist — ripiego su descrizione ASC
 3) test_get_profilo_reparto — GET profilo reparto (aree + azioni)
 4) test_get_profilo_reparto_empty — GET profilo vuoto
 5) test_put_profilo_reparto — PUT salva profilo e ritorna aggiornato
 6) test_put_profilo_invalidates_cache — PUT invalida cache reparto
 6b) test_put_profilo_porta_il_segno_del_secondo_fattore — T-3 del brief sicurezza
 6c) test_put_profilo_segno_non_booleano_rifiutato — niente stringhe «true»
 7) test_lookup_aree — GET lookup aree funzionali
 8) test_lookup_azioni — GET lookup azioni processo
 9) test_lookup_emittenti — GET lookup emittenti fiscali
10) test_profili_permission_denied — OPERATIVO non puo' accedere
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.views import (
    LookupAreeView,
    LookupAzioniView,
    LookupEmittentiView,
    RepartiListView,
    RepartoProfiloView,
)


SAMPLE_REPARTO = {
    "id": 1, "codice": "AMM", "nome": "Amministrazione", "attivo": True,
    "profilo_aree_count": 5, "profilo_azioni_count": 3, "operatori_count": 10,
}

SAMPLE_PROFILO = {
    "aree": [
        {"id": 1, "area_id": 2, "area_codice": "vendite",
         "area_descrizione": "Vendite", "livello": "TUTTO"},
    ],
    "azioni": [
        {"id": 1, "azione_id": 3, "permission_codename": "genera_fatture_lotti",
         "azione_descrizione": "Genera fatture lotti", "area_codice": "vendite",
         "abilitata": True},
    ],
}


def _make_request(method: str = "GET", data: dict | None = None) -> MagicMock:
    request = MagicMock()
    request.method = method
    request.user = MagicMock(is_authenticated=True, is_superuser=True, id=1)
    request.data = data or {}
    request.query_params = {}
    return request


class TestRepartiListView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_list_reparti(self, mock_repo_cls):
        """GET lista reparti: envelope paginato standard, parametri al repository."""
        mock_repo = MagicMock()
        mock_repo.list_reparti.return_value = ([SAMPLE_REPARTO], 1)
        mock_repo_cls.return_value = mock_repo

        view = RepartiListView()
        response = view.get(_make_request())

        data = json.loads(response.content)["data"]
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["nome"], "Amministrazione")
        self.assertEqual(data["results"][0]["operatori_count"], 10)
        self.assertEqual(
            (data["count"], data["page"], data["page_size"], data["total_pages"]),
            (1, 1, 25, 1),
        )
        mock_repo.list_reparti.assert_called_once_with(
            search=None, order_by="descrizione", order_dir=None, limit=25, offset=0,
        )

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_list_reparti_empty(self, mock_repo_cls):
        """GET lista reparti vuota."""
        mock_repo = MagicMock()
        mock_repo.list_reparti.return_value = ([], 0)
        mock_repo_cls.return_value = mock_repo

        view = RepartiListView()
        response = view.get(_make_request())

        data = json.loads(response.content)
        self.assertEqual(data["data"]["results"], [])
        self.assertEqual(data["data"]["count"], 0)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_list_reparti_parametri_di_lista(self, mock_repo_cls):
        """Ricerca, ordinamento e pagina arrivano al repository come li manda la lista."""
        mock_repo = MagicMock()
        mock_repo.list_reparti.return_value = ([SAMPLE_REPARTO], 30)
        mock_repo_cls.return_value = mock_repo

        request = _make_request()
        request.query_params = {
            "search": "am", "order_by": "operatori_count", "order_dir": "desc",
            "limit": "10", "offset": "20",
        }
        data = json.loads(RepartiListView().get(request).content)["data"]

        self.assertEqual((data["count"], data["page"], data["total_pages"]), (30, 3, 3))
        mock_repo.list_reparti.assert_called_once_with(
            search="am", order_by="operatori_count", order_dir="desc", limit=10, offset=20,
        )


class TestRepartiListRepository(TestCase):

    @patch("apps.amm_software.db.amm_software_repository.fetch_paged_with_total")
    def test_ordina_per_alias_della_cte(self, mock_fetch):
        """I conteggi ordinano per alias fuori dalla CTE; spareggio sull'id."""
        from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository

        mock_fetch.return_value = ([], 0)
        AmmSoftwareRepository().list_reparti(order_by="profilo_aree_count", order_dir="desc", limit=25)

        sql, params = mock_fetch.call_args.args
        self.assertIn("WITH reparti AS (", sql)
        self.assertIn("ORDER BY rp.profilo_aree_count DESC NULLS LAST, rp.id DESC", sql)
        self.assertIn("uo.attivo = true", sql)
        self.assertEqual(params, [25, 0])
        self.assertIn("uo.attivo = true", mock_fetch.call_args.kwargs["fallback_count_sql"])

    @patch("apps.amm_software.db.amm_software_repository.fetch_paged_with_total")
    def test_default_e_fuori_whitelist(self, mock_fetch):
        """Senza ordinamento: descrizione ASC. Uno sconosciuto: 400 (dal 2026-10-20)."""
        from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository

        mock_fetch.return_value = ([], 0)
        repo = AmmSoftwareRepository()
        repo.list_reparti(order_by=None)
        self.assertIn(
            "ORDER BY rp.descrizione ASC NULLS FIRST, rp.id ASC", mock_fetch.call_args.args[0],
        )
        mock_fetch.reset_mock()
        with self.assertRaisesRegex(ValueError, "order_by_invalid"):
            repo.list_reparti(order_by="uo.id; DROP TABLE x")
        mock_fetch.assert_not_called()


class TestRepartoProfiloView(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_get_profilo_reparto(self, mock_repo_cls):
        """GET profilo reparto ritorna aree e azioni."""
        mock_repo = MagicMock()
        mock_repo.get_profilo_reparto.return_value = SAMPLE_PROFILO
        mock_repo_cls.return_value = mock_repo

        view = RepartoProfiloView()
        response = view.get(_make_request(), uo_id=1)

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["aree"]), 1)
        self.assertEqual(len(data["data"]["azioni"]), 1)
        self.assertEqual(data["data"]["aree"][0]["livello"], "TUTTO")

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_get_profilo_reparto_empty(self, mock_repo_cls):
        """GET profilo vuoto per reparto senza configurazione."""
        mock_repo = MagicMock()
        mock_repo.get_profilo_reparto.return_value = {"aree": [], "azioni": []}
        mock_repo_cls.return_value = mock_repo

        view = RepartoProfiloView()
        response = view.get(_make_request(), uo_id=99)

        data = json.loads(response.content)
        self.assertEqual(data["data"]["aree"], [])
        self.assertEqual(data["data"]["azioni"], [])

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    @patch("apps.amm_software.services.amm_software_service.invalidate_department")
    def test_put_profilo_reparto(self, mock_invalidate, mock_repo_cls):
        """PUT salva profilo e ritorna aggiornato."""
        mock_repo = MagicMock()
        mock_repo.get_profilo_reparto.return_value = SAMPLE_PROFILO
        mock_repo_cls.return_value = mock_repo

        aree = [{"area_id": 2, "livello": "TUTTO"}]
        azioni = [{"azione_id": 3, "abilitata": True}]
        request = _make_request("PUT", {"aree": aree, "azioni": azioni})

        view = RepartoProfiloView()
        response = view.put(request, uo_id=1)

        # Senza il segno nel corpo: None = il valore resta quello che c'e'.
        mock_repo.put_profilo_reparto.assert_called_once_with(
            1, aree, azioni, richiede_secondo_fattore=None,
        )
        data = json.loads(response.content)
        self.assertIn("aree", data["data"])

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    @patch("apps.amm_software.services.amm_software_service.invalidate_department")
    def test_put_profilo_porta_il_segno_del_secondo_fattore(self, _invalidate, mock_repo_cls):
        """Il segno «richiede secondo fattore» arriva al repository."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_profilo_reparto.return_value = SAMPLE_PROFILO
        RepartoProfiloView().put(
            _make_request("PUT", {"aree": [], "azioni": [], "richiede_secondo_fattore": True}), uo_id=1,
        )
        mock_repo.put_profilo_reparto.assert_called_once_with(1, [], [], richiede_secondo_fattore=True)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    @patch("apps.amm_software.services.amm_software_service.invalidate_department")
    def test_put_profilo_segno_non_booleano_rifiutato(self, _invalidate, mock_repo_cls):
        """Un segno che non e' un booleano non si scrive."""
        from apps.core.services.service_errors import ServiceError

        with self.assertRaises(ServiceError) as ctx:
            RepartoProfiloView().put(
                _make_request("PUT", {"aree": [], "azioni": [], "richiede_secondo_fattore": "true"}), uo_id=1,
            )
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        mock_repo_cls.return_value.put_profilo_reparto.assert_not_called()

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    @patch("apps.amm_software.services.amm_software_service.invalidate_department")
    def test_put_profilo_voci_validate_prima_del_repository(self, _invalidate, mock_repo_cls):
        """⛔ Le voci si validano prima di scrivere (2026-10-21, §B5): una chiave
        mancante era un `KeyError` nel repository (500), e una lista ASSENTE
        diventava `[]` e svuotava il profilo con un 200."""
        from apps.core.services.service_errors import ServiceError

        for nome, corpo, campo in (
            ("area senza livello", {"aree": [{"area_id": 2}], "azioni": []}, "livello"),
            ("azione senza abilitata", {"aree": [], "azioni": [{"azione_id": 3}]}, "abilitata"),
            ("voce non oggetto", {"aree": [7], "azioni": []}, "aree"),
            ("aree assente", {"azioni": []}, "aree"),
            ("azioni assente", {"aree": []}, "azioni"),
        ):
            with self.subTest(caso=nome), self.assertRaises(ServiceError) as ctx:
                RepartoProfiloView().put(_make_request("PUT", corpo), uo_id=1)
            self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
            self.assertEqual(ctx.exception.context.get("field"), campo)
        mock_repo_cls.return_value.put_profilo_reparto.assert_not_called()

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    @patch("apps.amm_software.services.amm_software_service.invalidate_department")
    def test_put_profilo_invalidates_cache(self, mock_invalidate, mock_repo_cls):
        """PUT invalida cache reparto dopo modifica."""
        mock_repo = MagicMock()
        mock_repo.get_profilo_reparto.return_value = {"aree": [], "azioni": []}
        mock_repo_cls.return_value = mock_repo

        view = RepartoProfiloView()
        view.put(_make_request("PUT", {"aree": [], "azioni": []}), uo_id=5)

        mock_invalidate.assert_called_once_with(5)


class TestLookupViews(TestCase):

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_lookup_aree(self, mock_repo_cls):
        """GET lookup aree funzionali."""
        mock_repo = MagicMock()
        mock_repo.list_aree_funzionali.return_value = [
            {"id": 1, "codice": "vendite", "descrizione": "Vendite", "ordinamento": 1},
        ]
        mock_repo_cls.return_value = mock_repo

        view = LookupAreeView()
        response = view.get(_make_request())

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_lookup_azioni(self, mock_repo_cls):
        """GET lookup azioni processo."""
        mock_repo = MagicMock()
        mock_repo.list_azioni_processo.return_value = [
            {"id": 1, "permission_codename": "genera_fatture_lotti",
             "descrizione": "Genera fatture", "pericolosa": False,
             "area_id": 2, "area_codice": "vendite", "livello_minimo_area": "TUTTO"},
        ]
        mock_repo_cls.return_value = mock_repo

        view = LookupAzioniView()
        response = view.get(_make_request())

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)
        # Il tetto d'area viaggia fino al client (editor profilo reparto).
        self.assertEqual(data["data"]["results"][0]["livello_minimo_area"], "TUTTO")

    @patch("apps.amm_software.services.amm_software_service.AmmSoftwareRepository")
    def test_lookup_emittenti(self, mock_repo_cls):
        """GET lookup emittenti fiscali."""
        mock_repo = MagicMock()
        mock_repo.list_emittenti_fiscali.return_value = [
            {"id": 1, "denominazione": "Azienda Test", "partita_iva": "12345678901"},
        ]
        mock_repo_cls.return_value = mock_repo

        view = LookupEmittentiView()
        response = view.get(_make_request())

        data = json.loads(response.content)
        self.assertEqual(len(data["data"]["results"]), 1)


class TestProfiliPermissionDenied(TestCase):

    @patch("apps.core.api.permissions.PermissionResolver")
    @patch("apps.core.api.permissions.ZeroERPPermission._get_cache", return_value={})
    @patch("apps.core.api.permissions.ZeroERPPermission._save_cache_to_redis")
    def test_profili_permission_denied(self, mock_save, mock_cache, mock_resolver):
        """OPERATIVO non puo' accedere ai profili reparto."""
        mock_resolver.is_super_admin.return_value = False

        from apps.core.api.permissions import IsAdminZeroERP
        request = _make_request()
        request.user = MagicMock(is_authenticated=True, is_superuser=False, id=2)
        request.path = "/api/v1/amm-software/reparti/"

        perm = IsAdminZeroERP()
        self.assertFalse(perm.has_permission(request, RepartiListView()))
