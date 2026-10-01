# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari ApiPermessiAudit — endpoint audit trail permessi.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_admin_can_view_other_user
 2) test_operativo_can_view_self
 3) test_operativo_denied_other_user
 4) test_tabella_invalida_rejected
 5) test_page_size_capped_at_200
 6) test_empty_audit_returns_empty_list
 7) test_events_mapped_correctly
 8) test_filter_data_da
 9) test_filter_tabella
10) test_pagination
11) test_dept_tables_excluded_without_uo
12) test_override_oggetti_incluso_senza_filtro   (3.2 v2)
13) test_filtro_tabella_override_oggetti         (3.2 v2)
14) test_whitelist_include_user_override_oggetti (3.2 v2)
15) test_filter_data_a_include_il_giorno          (F-4)
16) test_page_zero_rifiutata                      (F-4)
"""

import math
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.db.permissions_audit_repository import PermissionsAuditRepository

# ⚠️ Dal 2026-09-28 la pagina passa da `fetch_paged_with_total`: si sostituisce
#    la `connection` del BB, e il cursore porta i NOMI delle colonne, come il
#    DB vero (il BB legge le righe per nome).
_CONN = "apps.core.db._helpers.connection"
_DESCRIZIONE = [
    SimpleNamespace(name=c) for c in (
        "tabella", "valid_from", "tipo_operazione", "user_insert",
        "snapshot", "tx_id", "total_count",
    )
]


def _mock_request(
    method: str = "GET",
    user_id: int = 1,
    is_superuser: bool = False,
    query_params: dict | None = None,
) -> MagicMock:
    """Scopo: Crea un mock DRF request per i test audit."""
    request = MagicMock()
    request.method = method
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = True
    user.is_superuser = is_superuser
    request.user = user
    request.query_params = query_params or {}
    return request


class PermissionsAuditRepositoryTests(TestCase):
    """Test per PermissionsAuditRepository."""

    def setUp(self) -> None:
        self.repo = PermissionsAuditRepository()

    # Scopo: Senza UO, le tabelle reparto non compaiono nella query.
    @patch(_CONN)
    def test_dept_tables_excluded_without_uo(self, mock_conn):
        ts = datetime(2026, 2, 28, 10, 30, 0, tzinfo=timezone.utc)
        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = [
            ("user_override_aree", ts, 2, "admin", {"livello": "TUTTO"}, "tx-1", 1),
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = self.repo.list_audit_events(
            auth_user_id=5, uo_id=None, data_da=None, data_a=None,
            tabella=None, page=1, page_size=50,
        )

        sql = mock_cursor.execute.call_args[0][0]
        # Senza uo_id le 3 tabelle dept (profili_accesso_*) NON compaiono.
        self.assertNotIn("profili_accesso_aree", sql)
        self.assertNotIn("profili_accesso_azioni", sql)
        self.assertNotIn("profili_accesso_bindings", sql)
        # Modello legacy droppato: nessun riferimento residuo.
        self.assertNotIn("profili_reparto", sql)
        self.assertEqual(len(result["events"]), 1)

    # Scopo: Query vuota restituisce risultato vuoto.
    @patch(_CONN)
    def test_empty_audit_returns_empty_list(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = self.repo.list_audit_events(
            auth_user_id=5, uo_id=None, data_da=None, data_a=None,
            tabella=None, page=1, page_size=50,
        )

        self.assertEqual(result["count"], 0)
        self.assertEqual(result["events"], [])
        self.assertEqual(result["total_pages"], 0)

    # Scopo: Verifica mapping tipo_operazione e struttura evento.
    @patch(_CONN)
    def test_events_mapped_correctly(self, mock_conn):
        ts = datetime(2026, 2, 28, 10, 30, 0, tzinfo=timezone.utc)
        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = [
            ("user_override_aree", ts, 1, "setup", {"livello": "TUTTO"}, "tx-a", 3),
            ("identita_digitali", ts, 2, "admin", {"ruolo_applicativo": "OPERATORE"}, "tx-b", 3),
            ("user_emittenti_fiscali", ts, 3, "admin", {"emittente_id": 7}, "tx-c", 3),
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = self.repo.list_audit_events(
            auth_user_id=5, uo_id=None, data_da=None, data_a=None,
            tabella=None, page=1, page_size=50,
        )

        self.assertEqual(result["count"], 3)
        self.assertEqual(len(result["events"]), 3)

        ev0 = result["events"][0]
        self.assertEqual(ev0["tabella"], "user_override_aree")
        self.assertEqual(ev0["tipo_operazione"], "INIZIALE")
        self.assertEqual(ev0["user_modifica"], "setup")
        self.assertEqual(ev0["snapshot"], {"livello": "TUTTO"})
        self.assertEqual(ev0["tx_id"], "tx-a")

        self.assertEqual(result["events"][1]["tipo_operazione"], "MODIFICA")
        self.assertEqual(result["events"][2]["tipo_operazione"], "ELIMINAZIONE")

    # Scopo: Filtro data_da viene aggiunto alla query.
    @patch(_CONN)
    def test_filter_data_da(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        self.repo.list_audit_events(
            auth_user_id=5, uo_id=None, data_da="2026-01-01", data_a=None,
            tabella=None, page=1, page_size=50,
        )

        sql = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]
        self.assertIn("valid_from >= %s", sql)
        self.assertIn("2026-01-01", params)

    # Scopo: `data_a` e' un giorno e lo include tutto: `[da, a + 1 giorno)`.
    # Il vecchio `valid_from <= a::timestamptz` si fermava alla mezzanotte
    # d'inizio e perdeva gli eventi del giorno indicato (F-4).
    @patch(_CONN)
    def test_filter_data_a_include_il_giorno(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        self.repo.list_audit_events(
            auth_user_id=5, uo_id=None, data_da=None, data_a="2026-01-31",
            tabella=None, page=1, page_size=50,
        )

        sql = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]
        self.assertIn("valid_from < %s::date + interval '1 day'", sql)
        self.assertNotIn("valid_from <=", sql)
        self.assertIn("2026-01-31", params)

    # Scopo: Filtro tabella riduce le sub-query UNION.
    @patch(_CONN)
    def test_filter_tabella(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        self.repo.list_audit_events(
            auth_user_id=5, uo_id=10, data_da=None, data_a=None,
            tabella="user_override_aree", page=1, page_size=50,
        )

        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("user_override_aree", sql)
        self.assertNotIn("user_override_oggetti", sql)
        # Filtro tabella esclude le altre dept (profili_accesso_*).
        self.assertNotIn("profili_accesso_aree", sql)
        self.assertNotIn("profili_accesso_azioni", sql)
        self.assertNotIn("profili_accesso_bindings", sql)
        self.assertNotIn("profili_reparto", sql)

    # Scopo: Paginazione page/page_size applicata correttamente.
    @patch(_CONN)
    def test_pagination(self, mock_conn):
        ts = datetime(2026, 2, 28, 10, 0, 0, tzinfo=timezone.utc)
        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = [
            ("user_override_aree", ts, 1, "admin", {}, "tx-1", 25),
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = self.repo.list_audit_events(
            auth_user_id=5, uo_id=None, data_da=None, data_a=None,
            tabella=None, page=3, page_size=10,
        )

        params = mock_cursor.execute.call_args[0][1]
        self.assertIn(10, params)   # page_size (LIMIT)
        self.assertIn(20, params)   # offset = (3-1)*10

        self.assertEqual(result["page"], 3)
        self.assertEqual(result["page_size"], 10)
        self.assertEqual(result["count"], 25)
        self.assertEqual(result["total_pages"], math.ceil(25 / 10))


class PermissionsAuditRepositoryOggettiTests(TestCase):
    """Test che verificano la copertura di user_override_oggetti (task 3.2 v2)."""

    def setUp(self) -> None:
        self.repo = PermissionsAuditRepository()

    # Scopo: Senza filtro tabella, la query include user_override_oggetti nel UNION ALL.
    @patch(_CONN)
    def test_override_oggetti_incluso_senza_filtro(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        self.repo.list_audit_events(auth_user_id=5, uo_id=None)

        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("user_override_oggetti", sql)

    # Scopo: Filtro tabella=user_override_oggetti esclude tutte le altre tabelle.
    @patch(_CONN)
    def test_filtro_tabella_override_oggetti(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        self.repo.list_audit_events(
            auth_user_id=5, uo_id=None, tabella="user_override_oggetti"
        )

        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("user_override_oggetti", sql)
        self.assertNotIn("user_override_aree", sql)
        self.assertNotIn("user_override_azioni", sql)
        self.assertNotIn("user_emittenti_fiscali", sql)

    # Scopo: La whitelist accetta user_override_oggetti come valore valido per il filtro.
    def test_whitelist_include_user_override_oggetti(self):
        self.assertIn(
            "user_override_oggetti",
            PermissionsAuditRepository._VALID_TABLE_NAMES,
        )


class ApiPermessiAuditViewTests(TestCase):
    """Test per la view ApiPermessiAudit (authorization check)."""

    # Scopo: ADMIN puo' vedere audit di un altro utente.
    @patch("apps.core.api.views.PermissionResolver")
    @patch("apps.core.api.views.get_user_model")
    @patch(_CONN)
    def test_admin_can_view_other_user(self, mock_conn, mock_get_user, mock_resolver):
        from apps.core.api.views import ApiPermessiAudit

        mock_resolver.is_super_admin.return_value = True
        mock_resolver.get_unita_organizzativa_id.return_value = 10

        target = MagicMock()
        target.id = 99
        mock_get_user.return_value.objects.get.return_value = target

        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request(user_id=1)
        view = ApiPermessiAudit()
        response = view.get(request, user_id=99)

        self.assertEqual(response.status_code, 200)

    # Scopo: OPERATIVO puo' vedere il proprio audit.
    @patch("apps.core.api.views.PermissionResolver")
    @patch("apps.core.api.views.get_user_model")
    @patch(_CONN)
    def test_operativo_can_view_self(self, mock_conn, mock_get_user, mock_resolver):
        from apps.core.api.views import ApiPermessiAudit

        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_unita_organizzativa_id.return_value = None

        target = MagicMock()
        target.id = 5
        mock_get_user.return_value.objects.get.return_value = target

        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request(user_id=5)
        view = ApiPermessiAudit()
        response = view.get(request, user_id=5)

        self.assertEqual(response.status_code, 200)

    # Scopo: OPERATIVO non puo' vedere audit di altri utenti.
    @patch("apps.core.api.views.PermissionResolver")
    def test_operativo_denied_other_user(self, mock_resolver):
        from apps.core.api.views import ApiPermessiAudit
        from apps.core.services.service_errors import ServiceError

        mock_resolver.is_super_admin.return_value = False

        request = _mock_request(user_id=5)
        view = ApiPermessiAudit()

        with self.assertRaises(ServiceError) as ctx:
            view.get(request, user_id=99)

        self.assertEqual(ctx.exception.code, "E_PERMESSO_NEGATO")

    # Scopo: Tabella non valida restituisce errore di validazione.
    @patch("apps.core.api.views.PermissionResolver")
    @patch("apps.core.api.views.get_user_model")
    def test_tabella_invalida_rejected(self, mock_get_user, mock_resolver):
        from apps.core.api.views import ApiPermessiAudit
        from apps.core.services.service_errors import ServiceError

        mock_resolver.is_super_admin.return_value = True

        target = MagicMock()
        target.id = 5
        mock_get_user.return_value.objects.get.return_value = target

        request = _mock_request(user_id=1, query_params={"tabella": "tabella_inventata"})
        view = ApiPermessiAudit()

        with self.assertRaises(ServiceError) as ctx:
            view.get(request, user_id=5)

        self.assertEqual(ctx.exception.code, "E_CORE_VALIDATION")

    # Scopo: `page=0` e' rifiutata prima del DB (400 E_VALIDATION_INPUT via
    # `ValueError`): dava un OFFSET negativo, cioe' un errore del DB (F-4).
    @patch("apps.core.api.views.PermissionResolver")
    @patch("apps.core.api.views.get_user_model")
    @patch(_CONN)
    def test_page_zero_rifiutata(self, mock_conn, mock_get_user, mock_resolver):
        from apps.core.api.views import ApiPermessiAudit

        mock_resolver.is_super_admin.return_value = True
        target = MagicMock()
        target.id = 5
        mock_get_user.return_value.objects.get.return_value = target

        for qp, atteso in (({"page": "0"}, "page_invalid"), ({"page_size": "0"}, "page_size_invalid")):
            with self.subTest(qp=qp), self.assertRaises(ValueError) as ctx:
                ApiPermessiAudit().get(_mock_request(user_id=1, query_params=qp), user_id=5)
            self.assertEqual(str(ctx.exception), atteso)
        mock_conn.cursor.assert_not_called()

    # Scopo: page_size viene limitato a 200 anche se il client passa un valore piu' alto.
    @patch("apps.core.api.views.PermissionResolver")
    @patch("apps.core.api.views.get_user_model")
    @patch(_CONN)
    def test_page_size_capped_at_200(self, mock_conn, mock_get_user, mock_resolver):
        from apps.core.api.views import ApiPermessiAudit

        mock_resolver.is_super_admin.return_value = True
        mock_resolver.get_unita_organizzativa_id.return_value = None

        target = MagicMock()
        target.id = 5
        mock_get_user.return_value.objects.get.return_value = target

        mock_cursor = MagicMock()
        mock_cursor.description = _DESCRIZIONE
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request(user_id=1, query_params={"page_size": "9999"})
        view = ApiPermessiAudit()
        view.get(request, user_id=5)

        params = mock_cursor.execute.call_args[0][1]
        # Il LIMIT deve essere 200, non 9999
        self.assertIn(200, params)
