# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: lo scope emittente applicativo sulla lista offerte, in tutta la
#        catena — repository (la clausola), service (il trasporto), view
#        (lista ED export leggono lo stesso `get_scope_user_id`).
# Note: mock su connection.cursor / service — nessun DB (regola CI di AGENTS.md).
# ------------------------------------------------------------
"""⛔ PERCHE' QUESTO FILE ESISTE.
Fino al 2026-09-21 la lista offerte era l'UNICA lista di testata di `vendite`
senza il filtro applicativo di scope emittente — il «B1» dell'analisi RLS
(`work-done/analisi-attivazione-rls-operatori.md` §2.3), chiuso a suo tempo
dalla sola RLS e mai in Python. Preventivi e contratti, stesso dominio e
stessa colonna, lo avevano: un'asimmetria nel modello, non un caso.
⚠️ Un filtro di scope si prova nei DUE versi: che con un utente ristretto la
clausola ci sia E porti la whitelist risolta, e che con `None` (nessuna
restrizione) non ci sia. E si prova che lo leggano ENTRAMBE le porte — la
lista e l'export — perche' l'export e' quella piu' larga.
Indice test:
 1) test_where_con_utente_ristretto_filtra_sulla_pk_emittente
 2) test_where_senza_utente_non_filtra
 3) test_where_con_whitelist_vuota_e_fail_closed
 4) test_service_passa_lo_scope_a_righe_e_conteggio
 5) test_view_lista_passa_lo_scope_dell_utente
 6) test_view_export_passa_lo_scope_dell_utente
"""

import unittest
from unittest.mock import Mock, patch

from django.test import Client, SimpleTestCase

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.db.offerte_repository import OfferteRepository

_FETCH_SCOPE = "apps.core.db.emittente_scope_helpers.fetch_emittenti_scope_ids"
_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SVC = "apps.vendite.api.views_offerte.OfferteService"
_SCOPE_USER = "apps.vendite.api.views_offerte.get_scope_user_id"


# Scopo: la coppia (WHERE, params) del filter builder, con lo scope risolto
#        a `scope_ids` senza toccare il database.
def _where(*, auth_user_id, scope_ids):
    with patch(_FETCH_SCOPE, return_value=scope_ids):
        return OfferteRepository()._build_offerte_filters(
            billing_account_id=None, stato_codice_interno=None, utility_id=None,
            listino_id=None, validita_dal_min=None, validita_dal_max=None,
            search=None, solo_ultima_revisione=False, auth_user_id=auth_user_id,
        )


class OfferteScopeRepositoryTests(unittest.TestCase):
    # Scopo: 🔴 utente ristretto → la clausola c'e', sulla PK reale
    #        `emittente_fiscale_id` (convenzione `pk`, non `_sr_ids`), e i
    #        params portano la whitelist risolta.
    def test_where_con_utente_ristretto_filtra_sulla_pk_emittente(self):
        where, params = _where(auth_user_id=7, scope_ids=[3, 5])
        self.assertIn("v.emittente_fiscale_id = ANY(%s)", where)
        self.assertIn([3, 5], params)

    # Scopo: `None` = nessuna restrizione (superuser a livello API): nessuna
    #        clausola e nessun accesso al risolutore.
    def test_where_senza_utente_non_filtra(self):
        with patch(_FETCH_SCOPE) as fetch:
            where, params = OfferteRepository()._build_offerte_filters(
                billing_account_id=None, stato_codice_interno=None, utility_id=None,
                listino_id=None, validita_dal_min=None, validita_dal_max=None,
                search=None, solo_ultima_revisione=False, auth_user_id=None,
            )
        self.assertNotIn("emittente_fiscale_id", where)
        self.assertEqual(params, [])
        fetch.assert_not_called()

    # Scopo: ⛔ whitelist vuota = operatore senza emittenti: la clausola resta,
    #        con `ANY('{}')` che non matcha nulla (fail-closed, non fail-open).
    def test_where_con_whitelist_vuota_e_fail_closed(self):
        where, params = _where(auth_user_id=7, scope_ids=[])
        self.assertIn("v.emittente_fiscale_id = ANY(%s)", where)
        self.assertIn([], params)


class OfferteScopeServiceTests(SimpleTestCase):
    # Scopo: il service passa `auth_user_id` SIA alle righe SIA al conteggio:
    #        un `count` fuori perimetro direbbe «12» mostrandone 3.
    @patch("apps.vendite.services.offerte_service.OfferteRepository", autospec=True)
    def test_service_passa_lo_scope_a_righe_e_conteggio(self, repo_cls):
        from apps.vendite.services.offerte_service import OfferteService

        repo = repo_cls.return_value
        repo.list_offerte.return_value = []
        repo.count_offerte.return_value = 0
        OfferteService().list_offerte(auth_user_id=42)
        self.assertEqual(repo.list_offerte.call_args.kwargs["auth_user_id"], 42)
        self.assertEqual(repo.count_offerte.call_args.kwargs["auth_user_id"], 42)


class OfferteScopeViewTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: la lista legge lo scope dell'utente della richiesta.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE_USER, return_value=42)
    @patch(_SVC)
    def test_view_lista_passa_lo_scope_dell_utente(self, svc_cls, _scope, _auth) -> None:
        svc_cls.return_value.list_offerte.return_value = ([], 0)
        resp = self.client.get("/api/v1/vendite/offerte/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            svc_cls.return_value.list_offerte.call_args.kwargs["auth_user_id"], 42,
        )

    # Scopo: ⚠️ e l'export — la porta piu' larga — legge LO STESSO scope. Il
    #        tetto di righe fa fermare la view dopo la lettura (422), che qui
    #        basta: la chiamata al service e' gia' avvenuta.
    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE_USER, return_value=42)
    @patch(_SVC)
    def test_view_export_passa_lo_scope_dell_utente(self, svc_cls, _scope, _auth) -> None:
        # Un totale oltre il tetto: la view si ferma DOPO la lettura, con 422.
        svc_cls.return_value.list_offerte.return_value = ([], EXPORT_MAX_ROWS + 1)
        svc_cls.return_value.resolve_filtri_export_label.return_value = {}
        resp = self.client.get("/api/v1/vendite/offerte/export/?formato=csv")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(
            svc_cls.return_value.list_offerte.call_args.kwargs["auth_user_id"], 42,
        )
