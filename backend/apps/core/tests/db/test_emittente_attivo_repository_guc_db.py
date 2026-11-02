# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le letture dello scope di DIRITTO di `EmittenteAttivoRepository`
#        lasciano la GUC dell'emittente attivo com'era — anche dentro una
#        transazione gia' aperta, che e' il caso di ogni GET
#        (`SolaLetturaMiddleware`).
# Note: ⛔ Il difetto non dava errore: in `/me/` la GUC restava vuota dopo la
#        lettura del nome dell'emittente, e `perimetro_multi_emittente` diceva
#        «tutti gli emittenti» a chi ne aveva scelto uno (2026-10-28). Il caso
#        si COSTRUISCE con un blocco atomico esterno: senza, `SET LOCAL` si
#        annulla da se' e il test sarebbe verde senza provare niente.
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_dentro_il_blocco_la_guc_e_vuota
     il cursore di `_cursore_scope_di_diritto` legge la GUC vuota.
2. test_list_selezionabili_ripristina_la_guc
     dentro una transazione esterna, dopo la lettura la GUC e' quella di prima.
3. test_is_scelta_valida_ripristina_la_guc
     idem per la validazione della scelta.
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection, transaction

from apps.core.db.emittente_attivo_repository import (
    EmittenteAttivoRepository,
    _cursore_scope_di_diritto,
)
from apps.core.tests.db_e2e import richiedi_db_provvisto

# Un valore qualunque: si prova la GUC, non l'emittente.
_EMITTENTE = "987654321"


class _AnnullaTransazione(Exception):
    """Chiude il blocco esterno con un rollback: il test non lascia tracce."""


def _guc() -> str:
    with connection.cursor() as cur:
        cur.execute("SELECT current_setting('app.current_emittente_id', true)")
        return cur.fetchone()[0]


class EmittenteAttivoRepositoryGucDbTests(TestCase):
    """La GUC dell'emittente attivo sopravvive alle letture di diritto."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Esegue `azione` dentro una transazione esterna con la GUC valorizzata
    # in LOCAL, come la imposta una richiesta, e restituisce la GUC di dopo.
    def _guc_dopo(self, azione) -> str:
        letta = None
        try:
            with transaction.atomic():
                with connection.cursor() as cur:
                    cur.execute(
                        "SELECT set_config('app.current_emittente_id', %s, true)",
                        [_EMITTENTE],
                    )
                azione()
                letta = _guc()
                raise _AnnullaTransazione
        except _AnnullaTransazione:
            pass
        return letta

    # 1. Lo scope di diritto: dentro il blocco la GUC e' vuota.
    def test_dentro_il_blocco_la_guc_e_vuota(self) -> None:
        dentro = []

        def azione() -> None:
            with _cursore_scope_di_diritto() as cur:
                cur.execute("SELECT current_setting('app.current_emittente_id', true)")
                dentro.append(cur.fetchone()[0])

        self.assertEqual(self._guc_dopo(azione), _EMITTENTE)
        self.assertEqual(dentro, [""])

    # 2. ⭐ Il caso di `/me/`: il nome dell'emittente attivo si legge da qui.
    def test_list_selezionabili_ripristina_la_guc(self) -> None:
        guc = self._guc_dopo(
            lambda: EmittenteAttivoRepository().list_selezionabili(0, solo_id=int(_EMITTENTE))
        )
        self.assertEqual(guc, _EMITTENTE)

    # 3. La validazione della scelta, stesso cursore.
    def test_is_scelta_valida_ripristina_la_guc(self) -> None:
        guc = self._guc_dopo(
            lambda: EmittenteAttivoRepository().is_scelta_valida(0, int(_EMITTENTE))
        )
        self.assertEqual(guc, _EMITTENTE)
