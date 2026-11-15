# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: CANCELLO della copertura della doc API: ogni rotta servita ha una
#        pagina in `docs/it/backend` che la nomina («scoperte» = 0), e nessuna
#        pagina nomina un path che nessuna rotta serve («fantasmi» = 0).
#
#        ⭐ PERCHE' ESISTE (2026-11-15). Fino a quel giorno la copertura aveva
#        un presidio sulla MISURA (`test_copertura_doc_api.py`, casi costruiti)
#        e nessuno sullo ZERO: la si rileggeva a mano. I due giri BE/FE di
#        `anagrafiche` del 2026-11-15 hanno aggiunto quattro rotte senza pagina,
#        e la CI era verde. La rilettura degli indicatori
#        (docs/it/dev/qualita-be-fe-indicatori.md §2) scriveva «presidiata»:
#        lo era il conto, non il risultato.
#
#        ⚠️ Legge la doc VERA, al contrario del presidio della misura: e' il suo
#        mestiere. Il calcolo e' quello del comando (`copertura_doc_api.misura`),
#        non una copia: un cancello che misura diversamente dal comando che si
#        lancia a mano da' due verita'.
#
# Note: Nessun DB: l'URLconf e' gia' importato dai system check del runner.
#       ⚠️ La CI lo lancia anche quando cambia solo `docs/it/backend/**`
#       (trigger di ci-validate.yaml): una pagina riscritta puo' scoprire una
#       rotta quanto una rotta nuova.
#       Rosso? `./manage-env.sh copertura_doc_api --dettaglio` elenca le righe;
#       si documenta la rotta nella pagina del suo dominio, o si corregge il
#       path fantasma. ⛔ Non si «copre» una rotta con una citazione generica:
#       la misura le scarta apposta (trappola 8 del comando).
# ------------------------------------------------------------

"""
Indice test (0..N):
 0. test_la_misura_vede_le_rotte_di_tutte_le_aree
 1. test_ogni_rotta_ha_la_sua_pagina
 2. test_nessuna_pagina_nomina_una_rotta_che_non_esiste
"""

from __future__ import annotations

from functools import lru_cache

from django.test import SimpleTestCase

from apps.core.management.commands import copertura_doc_api as cmd


# Scopo: la misura si calcola UNA volta per i tre test: legge tutta la doc.
@lru_cache(maxsize=1)
def _misura() -> tuple[list[cmd.MisuraArea], dict[str, set[str]]]:
    return cmd.misura()


class CoperturaDocApiCancelloTests(SimpleTestCase):

    # Scopo: il cancello non e' verde per il motivo sbagliato: una misura che
    #        non trova le rotte, o non trova la doc, darebbe zero scoperte.
    def test_la_misura_vede_le_rotte_di_tutte_le_aree(self):
        misure, assolute = _misura()
        aree = {m.area for m in misure}
        for attesa in ("anagrafiche", "core", "vendite"):
            self.assertIn(attesa, aree)
        self.assertGreater(sum(len(m.rotte) for m in misure), 500)
        self.assertTrue(cmd.DOCS.is_dir(), f"manca la doc: {cmd.DOCS}")
        self.assertGreater(len(assolute), 100)

    # Scopo: zero rotte servite senza una pagina che le nomini.
    def test_ogni_rotta_ha_la_sua_pagina(self):
        misure, _ = _misura()
        scoperte = [
            f"{','.join(m.rotte[p][1]) or '?'} {m.rotte[p][0]}"
            for m in misure for p in m.scoperte
        ]
        self.assertEqual(
            scoperte, [],
            "Rotte senza documentazione in docs/it/backend: va scritta la pagina "
            "del dominio (./manage-env.sh copertura_doc_api --dettaglio).",
        )

    # Scopo: zero path nominati dalla doc senza una rotta che li serva.
    def test_nessuna_pagina_nomina_una_rotta_che_non_esiste(self):
        misure, assolute = _misura()
        fantasmi = [
            f"{p} <- {', '.join(sorted(assolute[p]))}"
            for m in misure for p in m.fantasmi
        ]
        self.assertEqual(
            fantasmi, [],
            "Path citati dalla doc che nessuna rotta serve: si corregge il path, "
            "o la riga diventa una lapide (⛔ … ritirato).",
        )
