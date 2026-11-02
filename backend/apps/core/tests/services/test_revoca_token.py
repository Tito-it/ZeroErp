# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del building block `revoca_token`, nei due casi che le
#        view di revoca sessioni (testate in `test_sessioni_view`) non
#        esercitano: la revoca di TUTTI i token (cambio password, blocco della
#        credenziale), quella di UNA veste (D-5) e l'errore di scrittura che
#        deve propagare.
#        Mock dei modelli SimpleJWT: compatibile CI.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) BloccaTuttiTests.test_senza_filtro_blocca_anche_illeggibili_e_salta_i_gia_bloccati
2) BloccaTuttiTests.test_errore_di_scrittura_propaga
3) BloccaVesteTests.test_per_veste_blocca_solo_i_token_di_quella_veste
4) BloccaVesteTests.test_per_veste_e_sid_insieme
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


# Scopo: un refresh firmato con i claim dati, come lo legge il BB (senza
#        verificare la firma: la chiave qui non conta).
def _jwt(**claims) -> str:
    import jwt

    return jwt.encode(claims, "chiave-di-test-lunga-abbastanza-per-hs256-xxxxxxxx", algorithm="HS256")


class BloccaVesteTests(TestCase):

    # 3) D-5: spegnere una veste chiude le SUE sessioni. Il token di un'altra
    #    veste della stessa credenziale, quello senza claim e quello
    #    illeggibile restano fuori.
    @patch(f"{_MOD}.BlacklistedToken")
    @patch(f"{_MOD}.OutstandingToken")
    def test_per_veste_blocca_solo_i_token_di_quella_veste(
        self, MockOutstanding, MockBlacklisted
    ):
        MockOutstanding.objects.filter.return_value = [
            _ot(1, _jwt(identita_id=7, sid="a")),
            _ot(2, _jwt(identita_id=8, sid="b")),
            _ot(3, _jwt(sid="c")),
            _ot(4, "non-e-un-jwt"),
            _ot(5, _jwt(identita_id="7", sid="d")),
        ]
        MockBlacklisted.objects.filter.return_value.values_list.return_value = []

        self.assertEqual(blocca_token_sessioni(42, identita_id=7), 2)

        scritti = MockBlacklisted.objects.bulk_create.call_args.args[0]
        self.assertEqual(
            sorted(MockBlacklisted.call_args_list[i].kwargs["token"].id for i in range(len(scritti))),
            [1, 5],
        )

    # 4) I due filtri insieme: devono valere tutti e due.
    @patch(f"{_MOD}.BlacklistedToken")
    @patch(f"{_MOD}.OutstandingToken")
    def test_per_veste_e_sid_insieme(self, MockOutstanding, MockBlacklisted):
        MockOutstanding.objects.filter.return_value = [
            _ot(1, _jwt(identita_id=7, sid="a")),
            _ot(2, _jwt(identita_id=7, sid="b")),
            _ot(3, _jwt(identita_id=8, sid="a")),
        ]
        MockBlacklisted.objects.filter.return_value.values_list.return_value = []

        self.assertEqual(blocca_token_sessioni(42, lambda s: s == "a", identita_id=7), 1)
