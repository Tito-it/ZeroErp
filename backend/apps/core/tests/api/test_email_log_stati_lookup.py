# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il lookup degli stati del log email (`GET /core/email/log/stati/`):
#        la forma della risposta, l'ordine dichiarato, e che si apra a chi apre
#        la lista — senza livello d'area.
# Note: Nessun DB: il vocabolario e' statico. Il confronto col CHECK del
#       database sta in `core/tests/db/test_email_log_stati_guardrail.py`.
#       ⚠️ Nato il 2026-09-26, quando il vocabolario e' sceso da `amm_software`
#       a `core`: raccoglie i test che stavano la' (service + API).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_il_lookup_torna_l_envelope_results
   `{"data": {"results": [...]}}`, non la lista nuda (api.md).
2) test_l_ordine_di_uscita_e_quello_dichiarato
   I codici escono nell'ordine di `ordering`, SENT per primo; ogni riga ha la
   sua descrizione.
3) test_si_apre_senza_nessun_livello_d_area
   Stessa porta della lista del log: un operatore con tutto BLOCCATO lo apre.
"""

import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.api.email_views import EmailLogStatiLookupView
from apps.core.api.permissions import ZeroERPPermission
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.services.email_constants import STATI_EMAIL_LOG, STATI_EMAIL_LOG_DESCRIZIONI
from apps.core.tests.api.test_permissions import _mock_request


class EmailLogStatiLookupTests(SimpleTestCase):

    # Scopo: la risposta della view, gia' decodificata.
    def _risposta(self) -> dict:
        view = EmailLogStatiLookupView()
        return json.loads(view.get(MagicMock()).content)

    # 1. ⭐ La forma, non solo lo status: un `results` mancante e' una tendina
    #    vuota senza errore (api.md, «L'envelope di un lookup»).
    def test_il_lookup_torna_l_envelope_results(self):
        corpo = self._risposta()
        self.assertIsInstance(corpo["data"], dict)
        self.assertIsInstance(corpo["data"]["results"], list)

    # 2. L'atteso si DERIVA dalla sede unica, non si ricopia.
    def test_l_ordine_di_uscita_e_quello_dichiarato(self):
        righe = self._risposta()["data"]["results"]
        codici = [r["codice"] for r in righe]
        atteso = [c for c, _d, _o in sorted(STATI_EMAIL_LOG_DESCRIZIONI, key=lambda r: r[2])]
        self.assertEqual(codici, atteso)
        self.assertEqual(codici[0], "SENT", "default-first: SENT resta il primo")
        self.assertEqual(set(codici), STATI_EMAIL_LOG)
        for riga in righe:
            self.assertTrue(riga["descrizione"])

    # 3. Chi apre la lista deve poter filtrare: nessun livello d'area chiesto.
    @patch("apps.core.api.permissions.PermissionResolver")
    def test_si_apre_senza_nessun_livello_d_area(self, mock_resolver):
        mock_resolver.get_ruolo_applicativo.return_value = RUOLO_APPLICATIVO_OPERATORE
        mock_resolver.is_super_admin.return_value = False
        mock_resolver.get_livello_area.return_value = "BLOCCATO"
        self.assertTrue(
            ZeroERPPermission().has_permission(_mock_request(method="GET"), EmailLogStatiLookupView())
        )
        mock_resolver.get_livello_area.assert_not_called()
