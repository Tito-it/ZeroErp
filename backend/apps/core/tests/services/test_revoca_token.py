# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del building block `revoca_token`, nei due casi che le
#        view di revoca sessioni (testate in `test_sessioni_view`) non
#        esercitano: la revoca di TUTTI i token (cambio password,
#        disattivazione operatore) e l'errore di scrittura che deve propagare.
#        Mock dei modelli SimpleJWT: compatibile CI.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) BloccaTuttiTests.test_senza_filtro_blocca_anche_illeggibili_e_salta_i_gia_bloccati
2) BloccaTuttiTests.test_errore_di_scrittura_propaga
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.revoca_token import blocca_token_sessioni

_MOD = "apps.core.services.revoca_token"


def _ot(token_id: int, token: str) -> MagicMock:
    ot = MagicMock()
    ot.id = token_id
    ot.token = token
    return ot


class BloccaTuttiTests(TestCase):

    # 1) Con `vale_sid=None` non si decodifica: anche il token illeggibile
    #    viene bloccato, e quello gia' in blacklist conta ma non si riscrive.
    @patch(f"{_MOD}.BlacklistedToken")
    @patch(f"{_MOD}.OutstandingToken")
    def test_senza_filtro_blocca_anche_illeggibili_e_salta_i_gia_bloccati(
        self, MockOutstanding, MockBlacklisted
    ):
        MockOutstanding.objects.filter.return_value = [
            _ot(1, "non-e-un-jwt"),
            _ot(2, "altro"),
            _ot(3, "gia-bloccato"),
        ]
        MockBlacklisted.objects.filter.return_value.values_list.return_value = [3]

        self.assertEqual(blocca_token_sessioni(42), 3)

        MockOutstanding.objects.filter.assert_called_once_with(user_id=42)
        scritti = MockBlacklisted.objects.bulk_create.call_args.args[0]
        self.assertEqual(len(scritti), 2)

    # 2) ⛔ Una revoca fallita non e' «best-effort»: la copia della
    #    disattivazione operatore la ingoiava, e l'operatore disattivato
    #    restava con le sessioni vive senza traccia.
    @patch(f"{_MOD}.BlacklistedToken")
    @patch(f"{_MOD}.OutstandingToken")
    def test_errore_di_scrittura_propaga(self, MockOutstanding, MockBlacklisted):
        MockOutstanding.objects.filter.return_value = [_ot(1, "t")]
        MockBlacklisted.objects.filter.return_value.values_list.return_value = []
        MockBlacklisted.objects.bulk_create.side_effect = RuntimeError("db giu'")

        with self.assertRaises(RuntimeError):
            blocca_token_sessioni(42)
