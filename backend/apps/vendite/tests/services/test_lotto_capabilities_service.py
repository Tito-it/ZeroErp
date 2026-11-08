"""
Indice test eseguiti:
1) LottoCapabilitiesServiceTests.test_dettaglio_include_blob_capability
2) LottoCapabilitiesServiceTests.test_capability_letta_dopo_il_cancello_di_scope
3) LottoCapabilitiesServiceTests.test_capability_non_letta_su_lotto_fuori_scope
4) LottoCapabilitiesServiceTests.test_capability_rotta_non_impedisce_la_lettura
5) LottoCapabilitiesServiceTests.test_lotto_non_trovato_solleva_404
"""

from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.vendite_service import fn_get_lotto

_TESTATA = {
    "id": 42,
    "codice": "LOT-000042",
    "tipo_lotto": "MASSIVO",
    "stato_lotto": "COMPLETATO",
    "stato_doc_fiscale_codice": "EMESSA",
}

_BLOB = {
    "available_actions": [
        {
            "key": "numera",
            "target_state": "DEFINITIVA",
            "label_key": "vendite.lotti.azione_numera",
            "enabled": True,
            "reasons": [],
        },
        {
            "key": "riporta_a_draft",
            "target_state": "DRAFT",
            "label_key": "vendite.lotti.azione_riporta_a_draft",
            "enabled": False,
            "reasons": [
                {
                    "codice": "E_LOTTO_FATTURE_NUMERATE",
                    "reason": "FATTURE_NUMERATE",
                    "reason_key": "vendite.lotti.azione_reason.fatture_numerate",
                    "dettaglio": 3,
                },
            ],
        },
    ],
    "can_change_state": True,
    "stato_codice": "EMESSA",
    "tipo_lotto": "MASSIVO",
}


class LottoCapabilitiesServiceTests(SimpleTestCase):
    # Scopo: prepara il repository mockato condiviso dai casi (nessun DB reale:
    #        il test gira anche in CI, dove il DB non e' raggiungibile).
    def setUp(self):
        self.repo = MagicMock()
        self.repo.get_lotto.return_value = dict(_TESTATA)
        self.repo.get_available_actions_lotto.return_value = dict(_BLOB)
        patcher = patch(
            "apps.vendite.services.vendite_service.VenditeRepository", autospec=True,
            return_value=self.repo,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    # Scopo: il dettaglio porta il blob capability accanto alla testata — e'
    #        cio' che permette al drawer di NON ricalcolare le condizioni — e
    #        lo porta SOTTO `capabilities`, intatto (api.md §«Il blob sta SOTTO
    #        `capabilities`»): nessuna sua chiave sale nella testata.
    def test_dettaglio_include_blob_capability(self):
        result = fn_get_lotto(lotto_id=42, auth_user_id=7)
        self.assertEqual(result["codice"], "LOT-000042")
        self.assertEqual(result["capabilities"], self.repo.get_available_actions_lotto.return_value)
        self.assertEqual(len(result["capabilities"]["available_actions"]), 2)
        self.assertTrue(result["capabilities"]["can_change_state"])
        self.assertEqual(result["capabilities"]["stato_codice"], "EMESSA")
        self.assertNotIn("available_actions", result)
        self.assertNotIn("can_change_state", result)
        self.assertNotIn("stato_codice", result)

    # Scopo: ORDINE DI LETTURA — la capability si legge DOPO la testata, che e'
    #        l'unico cancello di scope (`fn_available_actions_lotto` non filtra
    #        per emittente). Invertire l'ordine esporrebbe le capability di un
    #        lotto che l'operatore non puo' vedere.
    def test_capability_letta_dopo_il_cancello_di_scope(self):
        manager = MagicMock()
        manager.attach_mock(self.repo.get_lotto, "get_lotto")
        manager.attach_mock(self.repo.get_available_actions_lotto, "capabilities")
        fn_get_lotto(lotto_id=42, auth_user_id=7)
        self.assertEqual(
            [c[0] for c in manager.mock_calls],
            ["get_lotto", "capabilities"],
        )

    # Scopo: su lotto fuori scope (repo → None) la capability non deve nemmeno
    #        essere interrogata: si esce con 404 prima.
    def test_capability_non_letta_su_lotto_fuori_scope(self):
        self.repo.get_lotto.return_value = None
        with self.assertRaises(ServiceError):
            fn_get_lotto(lotto_id=42, auth_user_id=7)
        self.repo.get_available_actions_lotto.assert_not_called()

    # Scopo: capability layer rotto → il lotto si legge lo stesso, col blob
    #        VUOTO (la chiave c'e' sempre: la forma non dipende dall'esito).
    #        Il drawer degrada a sola consultazione invece di mostrare un
    #        errore criptico (pattern offerte/contratti).
    def test_capability_rotta_non_impedisce_la_lettura(self):
        self.repo.get_available_actions_lotto.side_effect = DatabaseError("boom")
        result = fn_get_lotto(lotto_id=42, auth_user_id=7)
        self.assertEqual(result["codice"], "LOT-000042")
        self.assertEqual(result["capabilities"], {})

    # Scopo: lotto inesistente o fuori scope → stesso codice (no leak).
    def test_lotto_non_trovato_solleva_404(self):
        self.repo.get_lotto.return_value = None
        with self.assertRaises(ServiceError) as exc:
            fn_get_lotto(lotto_id=42, auth_user_id=7)
        self.assertEqual(exc.exception.code, "E_LOTTO_NON_TROVATO")
