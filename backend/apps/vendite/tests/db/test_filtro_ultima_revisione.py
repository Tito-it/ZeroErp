# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il filtro «solo l'ultima revisione» delle liste preventivi e offerte.
# Note: mock su connection.cursor — nessun DB (regola CI di AGENTS.md).
# ------------------------------------------------------------
"""⛔ PERCHE' QUESTO FILE ESISTE.

Fino al 2026-08-28 il filtro era `is_attiva IS TRUE`, e `is_attiva` rispondeva a
**due domande in un flag solo** — «e' l'ultima revisione?» E «non e' annullato?» —
in AND, quindi non piu' separabili da chi legge.

🔴 L'effetto misurato: 18 preventivi `ANNULLATO` su 18 avevano `is_attiva = false`,
e nella lista di default il filtro di stato «Annullato» **non poteva restituire
niente, mai**. Un'opzione di filtro che esiste nel menu e da' sempre zero — e
nessun test lo vedeva, perche' i test della lista mockano il repository e
provano solo che il parametro venga *propagato*, non quale SQL produca.

⭐ Qui si prova la CLAUSOLA. Un ritorno a `is_attiva` fa rosso.

⚠️ E si prova nei DUE VERSI: che ci sia `is_superata IS FALSE` **e** che NON ci
sia piu' `is_attiva IS TRUE`. Solo il primo passerebbe anche con entrambe le
condizioni in AND, che e' esattamente il difetto di partenza.

Indice test:

 1) test_preventivi_filtra_su_is_superata          — la clausola giusta c'e'
 2) test_preventivi_non_filtra_piu_su_is_attiva    — quella sbagliata non c'e'
 3) test_preventivi_storico_non_filtra             — toggle OFF: nessuna delle due
 4) test_offerte_filtra_su_is_superata             — idem sulla lista gemella
 5) test_offerte_non_filtra_piu_su_is_attiva       — idem
 6) test_offerte_storico_non_filtra                — idem
"""

import unittest
from unittest.mock import patch

from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.tests._helpers.mock_cursor import mock_cursor as _mock_cursor


def _sql_lista_preventivi(*, solo_ultima_revisione: bool) -> str:
    """Il SQL della lista preventivi, senza toccare il database.

    ⚠️ Si legge l'ULTIMA `execute`: la lista ne fa due (conteggio, poi pagina) e
    la clausola e' la stessa — prendere la prima proverebbe comunque, ma sul
    conteggio, cioe' non sulla query che produce le righe a video.
    """
    with patch("apps.vendite.db.preventivi_repository.connection.cursor") as fab:
        fab.return_value = _mock_cursor(fetchone=(0,), fetchall=[], description=[])
        PreventiviRepository().list_preventivi(
            solo_ultima_revisione=solo_ultima_revisione, limit=10, offset=0,
        )
        return fab.return_value.execute.call_args[0][0]


class FiltroUltimaRevisionePreventiviTests(unittest.TestCase):

    # Scopo: 🔴 La lista filtra sulla POSIZIONE nella catena delle revisioni.
    def test_preventivi_filtra_su_is_superata(self):
        self.assertIn("is_superata IS FALSE", _sql_lista_preventivi(solo_ultima_revisione=True))

    # Scopo: ⛔ E NON sullo stato del documento. Con `is_attiva` il filtro di
    #        stato «Annullato» tornava sempre vuoto: le due condizioni erano in
    #        AND e la prima aveva gia' escluso tutti gli annullati.
    def test_preventivi_non_filtra_piu_su_is_attiva(self):
        self.assertNotIn("is_attiva", _sql_lista_preventivi(solo_ultima_revisione=True))

    # Scopo: col toggle «Mostra storico revisioni» non si filtra affatto.
    def test_preventivi_storico_non_filtra(self):
        sql = _sql_lista_preventivi(solo_ultima_revisione=False)
        self.assertNotIn("is_superata", sql)
        self.assertNotIn("is_attiva", sql)


class FiltroUltimaRevisioneOfferteTests(unittest.TestCase):
    """⚠️ La lista gemella aveva lo STESSO difetto, e il commento di allora lo
    dichiarava senza vederlo: «predicato: stato NOT IN ('SUPERATA','ANNULLATA')».
    Due domande in un flag solo, scritte nero su bianco."""

    def _where(self, *, solo_ultima_revisione: bool) -> str:
        where, _params = OfferteRepository()._build_offerte_filters(
            billing_account_id=None, stato_codice_interno=None, utility_id=None,
            listino_id=None, validita_dal_min=None, validita_dal_max=None,
            search=None, solo_ultima_revisione=solo_ultima_revisione,
        )
        return where

    # Scopo: 🔴 Come i preventivi: si filtra sulla catena, non sullo stato.
    def test_offerte_filtra_su_is_superata(self):
        self.assertIn("is_superata IS FALSE", self._where(solo_ultima_revisione=True))

    # Scopo: ⛔ `is_attiva` non compare piu' nel filtro di lista.
    def test_offerte_non_filtra_piu_su_is_attiva(self):
        self.assertNotIn("is_attiva", self._where(solo_ultima_revisione=True))

    # Scopo: toggle storico: nessun filtro di revisione.
    def test_offerte_storico_non_filtra(self):
        where = self._where(solo_ultima_revisione=False)
        self.assertNotIn("is_superata", where)
        self.assertNotIn("is_attiva", where)
