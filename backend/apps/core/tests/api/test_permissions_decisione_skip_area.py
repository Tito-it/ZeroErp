# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Fissa la decisione del 2026-09-12 sulle view in cui `skip_area_check`
#        era MUTO (dichiaravano anche `area_funzionale`), provandola dal
#        PERCORSO REALE: le classi vere passate a `ZeroERPPermission`, non un
#        mock con gli attributi giusti.
#
#        - `pagamenti` (saldo, rate, sistemazioni, export): vale lo SKIP. Un
#          operatore SENZA nessun livello su `pagamenti` le apre — e' cio' che
#          il commento su quelle view prometteva da mesi senza che fosse vero.
#        - outbox email: vale l'AREA `config`. Leggere vuole LETTURA, spedire
#          vuole TUTTO (i livelli sono TUTTO / LETTURA / BLOCCATO): senza, 403.
#          Nessuno skip la apre.
#        - il LOG email (`EmailLogOperatoreListView`, sola lettura): vale lo
#          SKIP dal 2026-09-26 (Tid) — chi vede quale mail lo decide la RLS per
#          ambito, e un livello d'area sopra sarebbe una seconda regola. Le
#          bozze restano sotto `config` finche' non esiste `invia_email`.
#        - `RuoliConfigResolverView`: vale lo SKIP, come i lookup soggetti di
#          cui e' la configurazione — la apre chi apre un drawer, da qualunque
#          dominio, senza livello su `anagrafiche`.
#
#        `test_skip_area_check_registro.py` guarda gli ATTRIBUTI (nessuna view
#        li dichiara entrambi); qui si guarda il COMPORTAMENTO, perche' un
#        attributo tolto e' una promessa e la catena e' chi la mantiene.
# Note: Database MOCKATO (`PermissionResolver` intero): si prova cio' che la
#       catena DECIDE dato un livello, non come il livello viene risolto.
# ------------------------------------------------------------

"""
Indice test (0..N):
 0. test_il_saldo_fattura_si_apre_senza_nessun_livello_su_pagamenti
 1. test_le_quattro_view_pagamenti_non_chiedono_mai_il_livello_d_area
 2. test_leggere_l_outbox_vuole_lettura_su_config
 3. test_spedire_una_mail_vuole_scrittura_su_config
 4. test_la_configurazione_del_resolver_soggetti_si_apre_senza_anagrafiche
 5. test_il_log_email_si_legge_senza_nessun_livello_su_config
"""

from unittest.mock import ANY, MagicMock, patch

from django.test import SimpleTestCase

from apps.anagrafiche.api.views_ruoli_config import RuoliConfigResolverView
from apps.core.api.email_views import (
    EmailLogOperatoreListView,
    EmailOutboxListView,
    EmailOutboxSendView,
)
from apps.core.api.permissions import ZeroERPPermission
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.tests.api.test_permissions import _mock_request
from apps.pagamenti.api.views import (
    ApiFatturaRateSaldo,
    ApiFatturaSaldo,
    ApiFatturaSistemazioni,
    ApiFatturaSistemazioniExport,
)

_VIEW_PAGAMENTI = (
    ApiFatturaSaldo,
    ApiFatturaRateSaldo,
    ApiFatturaSistemazioni,
    ApiFatturaSistemazioniExport,
)


# Scopo: il resolver mockato come lo vede la catena: operatore, non super
#        admin, con il livello d'area dato su QUALUNQUE area.
def _resolver(mock_resolver: MagicMock, livello: str) -> None:
    mock_resolver.get_ruolo_applicativo.return_value = RUOLO_APPLICATIVO_OPERATORE
    mock_resolver.is_super_admin.return_value = False
    mock_resolver.get_livello_area.return_value = livello
    mock_resolver.has_profilo_applicabile_per_area.return_value = True


class DecisioneSkipAreaTests(SimpleTestCase):
    def setUp(self) -> None:
        self.perm = ZeroERPPermission()

    @patch("apps.core.api.permissions.PermissionResolver")
    def test_il_saldo_fattura_si_apre_senza_nessun_livello_su_pagamenti(self, mock_resolver):
        """Il venditore senza `pagamenti` vede se la fattura e' pagata."""
        _resolver(mock_resolver, "BLOCCATO")
        for view_cls in _VIEW_PAGAMENTI:
            with self.subTest(view=view_cls.__name__):
                self.assertTrue(self.perm.has_permission(_mock_request(method="GET"), view_cls()))

    @patch("apps.core.api.permissions.PermissionResolver")
    def test_le_quattro_view_pagamenti_non_chiedono_mai_il_livello_d_area(self, mock_resolver):
        """Lo skip e' ATTIVO: la catena non risolve nemmeno l'area.

        ⚠️ E' la differenza fra «passa perche' ha TUTTO» e «passa perche' non
        si guarda»: con l'area dichiarata il primo test sarebbe stato verde per
        un operatore largo e rosso per uno stretto, e questo lo avrebbe detto.
        """
        _resolver(mock_resolver, "TUTTO")
        for view_cls in _VIEW_PAGAMENTI:
            with self.subTest(view=view_cls.__name__):
                self.perm.has_permission(_mock_request(method="GET"), view_cls())
        mock_resolver.get_livello_area.assert_not_called()
        mock_resolver.get_livello_oggetto.assert_not_called()

    @patch("apps.core.api.permissions.PermissionResolver")
    def test_leggere_l_outbox_vuole_lettura_su_config(self, mock_resolver):
        """Nessuno skip apre l'outbox: senza livello su `config` e' 403."""
        _resolver(mock_resolver, "BLOCCATO")
        self.assertFalse(self.perm.has_permission(_mock_request(method="GET"), EmailOutboxListView()))
        _resolver(mock_resolver, "LETTURA")
        self.assertTrue(self.perm.has_permission(_mock_request(method="GET"), EmailOutboxListView()))
        # E l'area chiesta e' proprio `config`, non un'altra.
        mock_resolver.get_livello_area.assert_called_with(ANY, "config", cache=ANY)

    @patch("apps.core.api.permissions.PermissionResolver")
    def test_spedire_una_mail_vuole_scrittura_su_config(self, mock_resolver):
        """LETTURA non basta a spedire dall'account aziendale: serve TUTTO."""
        _resolver(mock_resolver, "LETTURA")
        self.assertFalse(self.perm.has_permission(_mock_request(method="POST"), EmailOutboxSendView()))
        _resolver(mock_resolver, "TUTTO")
        self.assertTrue(self.perm.has_permission(_mock_request(method="POST"), EmailOutboxSendView()))

    @patch("apps.core.api.permissions.PermissionResolver")
    def test_la_configurazione_del_resolver_soggetti_si_apre_senza_anagrafiche(self, mock_resolver):
        """Chi apre un drawer in vendite non ha bisogno di `anagrafiche` per il resolver."""
        _resolver(mock_resolver, "BLOCCATO")
        self.assertTrue(self.perm.has_permission(_mock_request(method="GET"), RuoliConfigResolverView()))
        mock_resolver.get_livello_area.assert_not_called()

    @patch("apps.core.api.permissions.PermissionResolver")
    def test_il_log_email_si_legge_senza_nessun_livello_su_config(self, mock_resolver):
        """Le proprie mail le legge chiunque: il perimetro lo tiene la RLS.

        ⚠️ Nello stesso test la controprova sull'outbox: aprire il log non deve
        aver aperto le bozze, che restano sotto `config`.
        """
        _resolver(mock_resolver, "BLOCCATO")
        self.assertTrue(self.perm.has_permission(_mock_request(method="GET"), EmailLogOperatoreListView()))
        mock_resolver.get_livello_area.assert_not_called()
        self.assertFalse(self.perm.has_permission(_mock_request(method="GET"), EmailOutboxListView()))
