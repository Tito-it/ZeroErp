# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il filtro `vivo` della lista dei processi (BE12 di
#        brief-db-revisione-dbops) dice cio' che dice il DB, sul database vero.
# Note: ⛔ Perche' esiste (2026-11-09). Fino al giro 9 il filtro era
#        `p.attivo`, ma il ritiro di un processo ha una sede sola,
#        `obsoleto_dal` (D11, Q2): un processo con la data raggiunta e
#        `attivo = true` usciva fra i vivi, mentre sveglia, roster e panorama
#        lo davano per spento. I tre casi si COSTRUISCONO su un processo del
#        seed, in una transazione annullata: data vuota, data futura (ritiro
#        programmato: ancora vivo), data raggiunta con `attivo` lasciato a
#        true (il caso che la copia vecchia sbagliava). Non si confronta la
#        popolazione di oggi.
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_il_filtro_vivo_segue_la_data_del_ritiro
     i tre casi del modello, con `vivo=True`, `vivo=False` e senza filtro;
     e la colonna `vivo` che lista e dettaglio proiettano dice lo stesso del
     filtro (una espressione sola, `_SQL_VIVO`).
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection

from apps.core.db.processi_repository import ProcessiRepository
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

# Un processo del SEED (contratto, non fotografia), di canale CODA: il CHECK
# dell'accensione non gli chiede niente, e la data del ritiro si sposta da sola.
_PROCESSO = "FATTURAZIONE_GIRO"


class FiltroVivoProcessiDbTests(TestCase):
    """`list_processi(vivo=...)` segue `script.fn_e_obsoleto`, non `attivo`."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # La sonda sul CHECK del giro 9: un DB indietro fallirebbe sull'attesa,
        # non sul prerequisito.
        richiedi_db_provvisto("script.fn_e_obsoleto(date)")
        cls.repo = ProcessiRepository()

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    def _ritira(self, espressione: str) -> None:
        with connection.cursor() as cur:
            # espressione e' una costante del test, mai input esterno
            cur.execute(
                f"UPDATE dbops.processi SET attivo = true, obsoleto_dal = {espressione}"
                " WHERE codice = %s",
                [_PROCESSO],
            )
            self.assertEqual(cur.rowcount, 1, f"{_PROCESSO} non e' nel seed")

    def _codici(self, vivo: bool | None) -> set[str]:
        righe, _ = self.repo.list_processi(vivo=vivo, search=_PROCESSO, limit=100)
        return {r["codice"] for r in righe}

    def test_il_filtro_vivo_segue_la_data_del_ritiro(self) -> None:
        casi = (
            ("mai ritirato", "NULL", True),
            ("ritiro programmato", "script.fn_data_operativa() + 1", True),
            ("ritiro raggiunto, attivo ancora true", "script.fn_data_operativa()", False),
        )
        for nome, espressione, vivo_atteso in casi:
            with self.subTest(caso=nome):
                self._ritira(espressione)
                self.assertIn(_PROCESSO, self._codici(None))
                self.assertEqual(_PROCESSO in self._codici(True), vivo_atteso)
                self.assertEqual(_PROCESSO in self._codici(False), not vivo_atteso)
                # La colonna che il client legge per il tag «ritirato».
                righe, _ = self.repo.list_processi(search=_PROCESSO, limit=100)
                riga = next(r for r in righe if r["codice"] == _PROCESSO)
                self.assertIs(riga["vivo"], vivo_atteso)
                self.assertIs(self.repo.get_processo(_PROCESSO)["vivo"], vivo_atteso)
