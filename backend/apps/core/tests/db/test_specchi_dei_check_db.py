# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL REGISTRO DEGLI SPECCHI. Un vocabolario chiuso che il database
#        possiede con un CHECK, e che il backend ricopia in una costante per
#        validare un filtro PRIMA della query, deve coincidere col suo CHECK.
#        Un test per costante, una riga per specchio.
# ⛔ Il difetto che uno specchio sbagliato produce e' MUTO in entrambi i versi:
#    un valore in meno nella costante e' un 400 su una domanda buona; uno in
#    piu' lascia passare un filtro che il DB non conosce, e la lista risponde
#    vuota. Per questo ogni costante-specchio si iscrive qui nel giorno in cui
#    nasce (2026-10-20, brief-be-verifica-documentazione-api §3).
# ⚠️ Gli specchi con un guardrail loro (`STATI_ESECUZIONE_*`,
#    `test_esito_esecuzione_lotto_guardrail`) restano li': quel test prova
#    anche l'invariante fra i due livelli, che qui non c'e'.
# ⭐ Uno specchio si TOGLIE quando il vocabolario diventa una tabella: allora il
#    filtro lo legge da li' (`richiedi_codice_a_vocabolario`) e non c'e' piu'
#    niente da confrontare. Cosi' `STATI_LOTTO` (stato del job del lotto, oggi
#    `config.stati_lotto_job`, 2026-10-27).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_ogni_specchio_coincide_col_suo_check — costante Python = valori del CHECK
"""

from __future__ import annotations

from unittest import TestCase

from apps.core.tests.db_e2e import richiedi_db_provvisto, valori_check
from apps.pagamenti.services.pagamenti_service import ORIGINI_VENDITA_CONTABILE
from apps.vendite.db.commesse_repository import (
    STATI_APPROVAZIONE_ATTIVITA,
    STATI_EMISSIONE_ATTIVITA,
    TIPO_MOVIMENTO_VALUES,
)
from apps.vendite.db.vendite_repository import FASI_DOCUMENTO


# (tabella, CHECK, costante) — una riga per specchio.
_SPECCHI: tuple[tuple[str, str, frozenset[str] | tuple[str, ...]], ...] = (
    ("vendite.commesse_attivita", "chk_commesse_attivita_stato_emissione", STATI_EMISSIONE_ATTIVITA),
    ("vendite.commesse_attivita", "chk_commesse_attivita_stato_approvazione", STATI_APPROVAZIONE_ATTIVITA),
    ("vendite.commesse_attivita", "chk_commesse_attivita_tipo_movimento", TIPO_MOVIMENTO_VALUES),
    ("pagamenti.vendite_contabili", "chk_vendite_contabili_origine", ORIGINI_VENDITA_CONTABILE),
    # La fase: lo stesso CHECK su ogni tabella di stati documento.
    *(
        (f"config.stati_doc_{t}", f"chk_stati_doc_{t}_fase", FASI_DOCUMENTO)
        for t in ("preventivi", "ordini", "ddt", "offerte", "contratti", "reso", "fiscale")
    ),
)


class SpecchiDeiCheckDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def test_ogni_specchio_coincide_col_suo_check(self) -> None:
        for tabella, conname, specchio in _SPECCHI:
            with self.subTest(check=conname):
                self.assertEqual(
                    set(specchio), valori_check(tabella, conname),
                    f"lo specchio Python di {conname} non coincide col CHECK: "
                    "un valore in meno rifiuta una domanda buona, uno in piu' "
                    "fa rispondere vuota una lista invece di un 400.",
                )
