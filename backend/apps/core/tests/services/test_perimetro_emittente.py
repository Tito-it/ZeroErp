# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del building block `perimetro_emittente` — la domanda
#        «questa persona sta guardando un emittente solo, o piu' di uno?» e il
#        rifiuto che ne discende per le liste non certificate.
# Tutti i test usano mock — nessuna dipendenza da DB reale (CI-compatible).
#
# ⚠️ Il caso che si sbaglia scrivendo questi test e' lo scope a UN elemento:
#        e' quello del 99% degli utenti, quindi un file che provasse solo
#        «multi -> rifiuta» sarebbe verde anche se il cancello scattasse
#        sempre. I due versi si asseriscono entrambi.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) scope_universo_e_multi                    — None (tutti) -> True
 2) scope_due_emittenti_e_multi               — [a, b] -> True
 3) scope_singolo_non_e_multi                 — [a] -> False
 4) scope_vuoto_non_e_multi                   — [] (nessun accesso) -> False
 5) per_codice_non_legge_il_catalogo_se_lo_scope_e_singolo  — zero query
 6) per_codice_rifiuta_su_flag_falso          — codice e messaggio giusti
 7) per_codice_tace_su_flag_vero              — la lista certificata passa
 8) per_codice_lista_sconosciuta_e_errore_tecnico — non e' un rifiuto di perimetro
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services import perimetro_emittente as pe
from apps.core.services.service_errors import ServiceError

_SCOPE = "apps.core.services.perimetro_emittente.PermissionResolver.get_emittenti_pk_ids"
_CATALOGO = "apps.core.services.perimetro_emittente.fetch_multi_emittente"


def _user(user_id: int = 42):
    user = MagicMock()
    user.id = user_id
    user.is_authenticated = True
    return user


class ScopeMultiEmittenteTests(TestCase):
    """La cardinalita' dello scope, nei suoi tre stati."""

    @patch(_SCOPE, return_value=None)
    def test_scope_universo_e_multi(self, _m) -> None:
        """`None` = nessuna restrizione = TUTTI gli emittenti."""
        self.assertTrue(pe.scope_multi_emittente(_user()))

    @patch(_SCOPE, return_value=[72, 159])
    def test_scope_due_emittenti_e_multi(self, _m) -> None:
        self.assertTrue(pe.scope_multi_emittente(_user()))

    @patch(_SCOPE, return_value=[72])
    def test_scope_singolo_non_e_multi(self, _m) -> None:
        """Il caso normale: operatore, o super admin con emittente attivo."""
        self.assertFalse(pe.scope_multi_emittente(_user()))

    @patch(_SCOPE, return_value=[])
    def test_scope_vuoto_non_e_multi(self, _m) -> None:
        """`[]` = nessun accesso.

        ⚠️ Non e' un'ambiguita' da sciogliere: chi non vede niente non ha due
        emittenti fra cui scegliere, e il cancello gli offrirebbe una tendina
        vuota. Il suo problema — configurazione mancante, dopo P-2a — si vede
        dalla lista vuota e da `dbops.vw_operatori_senza_emittente`.
        """
        self.assertFalse(pe.scope_multi_emittente(_user()))


class GuardListaPerCodiceTests(TestCase):
    """La catena completa: perimetro, poi catalogo, poi rifiuto.

    ⚠️ Qui c'erano anche tre test su un helper interno che prendeva il flag
    gia' risolto. Sono stati tolti con l'helper: verificavano gli STESSI due
    versi (flag acceso -> passa, flag spento + perimetro multiplo -> rifiuta)
    che i test qui sotto coprono passando dalla porta vera. Un test in piu' su
    una funzione in meno non aggiungeva copertura: aggiungeva un secondo posto
    da cambiare.
    """

    @patch(_CATALOGO)
    @patch(_SCOPE, return_value=[72])
    def test_per_codice_non_legge_il_catalogo_se_lo_scope_e_singolo(
        self, _m_scope, m_catalogo
    ) -> None:
        """⭐ L'ordine delle due domande e' la ragione per cui la funzione esiste.

        Nel 99% dei casi il perimetro e' singolo e la query al catalogo NON
        deve nemmeno partire: invertire le due domande costerebbe un
        round-trip su ogni apertura di lista per un cancello che non scatta.
        """
        pe.guard_lista_per_codice(user=_user(), lista_codice="vendite.x")
        m_catalogo.assert_not_called()

    @patch(_CATALOGO, return_value=False)
    @patch(_SCOPE, return_value=None)
    def test_per_codice_rifiuta_su_flag_falso(self, _m_scope, m_catalogo) -> None:
        with self.assertRaises(ServiceError) as ctx:
            pe.guard_lista_per_codice(user=_user(), lista_codice="vendite.x")
        # ⚠️ Il codice si asserisce per NOME, non «un errore qualunque»: un
        # rifiuto generico verrebbe tradotto in 400 e direbbe all'operatore che
        # ha sbagliato a scrivere qualcosa.
        self.assertEqual(ctx.exception.code, "E_UI_LISTA_EMITTENTE_DA_SCEGLIERE")
        self.assertIn("emittente", ctx.exception.message.lower())
        m_catalogo.assert_called_once_with("vendite.x")

    @patch(_CATALOGO, return_value=True)
    @patch(_SCOPE, return_value=None)
    def test_per_codice_tace_su_flag_vero(self, _m_scope, _m_catalogo) -> None:
        pe.guard_lista_per_codice(user=_user(), lista_codice="vendite.x")

    @patch(_CATALOGO, return_value=None)
    @patch(_SCOPE, return_value=None)
    def test_per_codice_lista_sconosciuta_e_errore_tecnico(
        self, _m_scope, _m_catalogo
    ) -> None:
        """Una view che dichiara un `lista_codice` inesistente e' un difetto NOSTRO.

        ⚠️ Non si traduce in «scegli un emittente»: manderebbe l'operatore a
        risolvere un problema che non lo riguarda, e per giunta senza effetto.
        Non si tace nemmeno, o il presidio resterebbe spento in silenzio.
        """
        with self.assertRaises(ServiceError) as ctx:
            pe.guard_lista_per_codice(user=_user(), lista_codice="vendite.inesistente")
        self.assertEqual(ctx.exception.code, "E_UI_LISTA_NON_TROVATA")
