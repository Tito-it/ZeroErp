# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il tipo di accesso che una chiamata chiede al livello d'area, e la
#        sua dichiarazione `<metodo>_accesso` (brief-db-area-funzionale-
#        assistente-ai §5.3 punti 1 e 2).
#
#        Il verbo HTTP dice come VIAGGIA una chiamata, non sempre cosa FA:
#        una domanda all'assistente e' una POST ed e' una lettura. La view lo
#        dichiara (`post_accesso = "view"`) e la catena lo applica, con la
#        stessa chiave di `<metodo>_permission`. Da qui si deriva anche
#        «questa chiamata scrive?» (`chiamata_in_scrittura`), sede unica per
#        la conferma dei tool, il livello sull'assistente e la sola lettura.
# Note: `PermissionResolver` mockato: si prova cio' che la catena DECIDE.
# ------------------------------------------------------------

"""
Indice test (0..N):
 0. test_senza_dichiarazione_decide_il_verbo
 1. test_la_dichiarazione_vince_sul_verbo
 2. test_un_valore_fuori_dai_quattro_tipi_nega
 3. test_una_post_dichiarata_lettura_entra_con_lettura
 4. test_accesso_esplicito_sostituisce_quello_della_chiamata
 5. test_accesso_esplicito_non_valido_nega
 6. test_chiamata_in_scrittura
 7. test_un_azione_non_rende_scrittura_una_get
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.api.base_views import DomainAPIView
from apps.core.api.permissions import (
    MotivoDiniego,
    ZeroERPPermission,
    chiamata_in_scrittura,
)
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova


class _Standard(DomainAPIView):
    area_funzionale = "pratiche"


class _PostCheLegge(DomainAPIView):
    area_funzionale = "pratiche"
    post_accesso = "view"


class _Refuso(DomainAPIView):
    area_funzionale = "pratiche"
    post_accesso = "lettura"


class _GetConAzione(DomainAPIView):
    area_funzionale = "pratiche"
    get_permission = "vede_cose_riservate"


# Scopo: il resolver come lo vede la catena: operatore, non super admin,
#        livello scelto dal test.
def _resolver(livello: str):
    mock = patch("apps.core.api.permissions.PermissionResolver").start()
    mock.get_ruolo_applicativo.return_value = RUOLO_APPLICATIVO_OPERATORE
    mock.is_super_admin.return_value = False
    mock.get_livello_area.return_value = livello
    return mock


class TipoAccessoTests(SimpleTestCase):

    def tearDown(self) -> None:
        patch.stopall()

    def test_senza_dichiarazione_decide_il_verbo(self) -> None:
        self.assertEqual(ZeroERPPermission.tipo_accesso(_Standard, method="GET"), "view")
        self.assertEqual(ZeroERPPermission.tipo_accesso(_Standard, method="POST"), "add")
        self.assertEqual(ZeroERPPermission.tipo_accesso(_Standard, method="PATCH"), "change")

    def test_la_dichiarazione_vince_sul_verbo(self) -> None:
        self.assertEqual(ZeroERPPermission.tipo_accesso(_PostCheLegge, method="POST"), "view")
        # Solo per il metodo dichiarato.
        self.assertEqual(ZeroERPPermission.tipo_accesso(_PostCheLegge, method="PATCH"), "change")

    # Un refuso non ricade sul default del metodo: nega.
    def test_un_valore_fuori_dai_quattro_tipi_nega(self) -> None:
        self.assertIsNone(ZeroERPPermission.tipo_accesso(_Refuso, method="POST"))
        _resolver("TUTTO")
        esito = ZeroERPPermission.valuta(operatore_di_prova(user_id=3), _Refuso, method="POST", cache={})
        self.assertFalse(esito.consentito)
        self.assertIs(esito.motivo, MotivoDiniego.AZIONE_SCONOSCIUTA)

    def test_una_post_dichiarata_lettura_entra_con_lettura(self) -> None:
        _resolver("LETTURA")
        self.assertTrue(
            ZeroERPPermission.valuta(operatore_di_prova(user_id=3), _PostCheLegge, method="POST", cache={}).consentito
        )
        self.assertFalse(
            ZeroERPPermission.valuta(operatore_di_prova(user_id=3), _Standard, method="POST", cache={}).consentito
        )

    # E' cio' che fa il filtro dei tool: chiede all'ingresso dell'assistente
    # il tipo del TOOL, non quello della POST.
    def test_accesso_esplicito_sostituisce_quello_della_chiamata(self) -> None:
        _resolver("LETTURA")
        self.assertFalse(
            ZeroERPPermission.valuta(
                operatore_di_prova(user_id=3), _PostCheLegge, method="POST", accesso="add", cache={},
            ).consentito
        )
        self.assertTrue(
            ZeroERPPermission.valuta(
                operatore_di_prova(user_id=3), _Standard, method="POST", accesso="view", cache={},
            ).consentito
        )

    def test_accesso_esplicito_non_valido_nega(self) -> None:
        _resolver("TUTTO")
        esito = ZeroERPPermission.valuta(
            operatore_di_prova(user_id=3), _Standard, method="GET", accesso="", cache={},
        )
        self.assertIs(esito.motivo, MotivoDiniego.AZIONE_SCONOSCIUTA)

    def test_chiamata_in_scrittura(self) -> None:
        self.assertFalse(chiamata_in_scrittura(_Standard, method="GET"))
        self.assertTrue(chiamata_in_scrittura(_Standard, method="POST"))
        self.assertFalse(chiamata_in_scrittura(_PostCheLegge, method="POST"))
        # Fail-closed: se la catena non sa dire il tipo, si tratta da scrittura.
        self.assertTrue(chiamata_in_scrittura(_Refuso, method="POST"))
        self.assertTrue(chiamata_in_scrittura(_Standard, method="TRACE"))

    # Un'azione decide CHI fa la chiamata, non COSA fa.
    def test_un_azione_non_rende_scrittura_una_get(self) -> None:
        self.assertFalse(chiamata_in_scrittura(_GetConAzione, method="GET"))
