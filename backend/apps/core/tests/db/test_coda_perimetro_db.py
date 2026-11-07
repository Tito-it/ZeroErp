# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il PERIMETRO della coda lavori in SQL (`_filtro_perimetro`,
#        `_espr_nel_perimetro` del repository) sul DB vero: un lavoro è di chi
#        ha la sua azienda nel perimetro (BE10 a / anticipo di BE9 di
#        brief-db-revisione-dbops, 2026-11-07).
# Note: ⛔ I test coi mock vedono i kwargs, non l'SQL: un `ANY(%s)` con una
#        lista vuota senza `::bigint[]` è un errore di PostgreSQL che nessun mock
#        solleva, e un `is_mio` scritto al contrario è un 200 con la bandiera
#        sbagliata. Qui si confronta il repository con un conteggio diretto
#        della tabella, azienda per azienda: vale su qualunque contenuto della
#        coda (anche vuota), senza scrivere righe.
# ------------------------------------------------------------
"""Indice test (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_filtro_per_azienda_come_conteggio_diretto
     `count_per_stato(owner_emittenti=[E])` = le righe di E, per ogni azienda.
2. test_perimetro_vuoto_e_nessun_filtro
     `[]` non vede niente (fail-closed), None vede tutto.
3. test_is_mio_segue_il_perimetro
     `is_mio` vero sulle righe delle aziende del chiamante e solo su quelle;
     None (admin globale) = ogni lavoro con un'azienda; vuoto = nessuno.
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection

from apps.core.services.coda_lavori.repository import CodaLavoriRepository
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


def _righe_per_azienda() -> dict[int | None, int]:
    with connection.cursor() as cur:
        cur.execute(
            "SELECT emittente_fiscale_id, COUNT(*)::int FROM dbops.coda_lavori GROUP BY 1"
        )
        return {r[0]: int(r[1]) for r in cur.fetchall()}


class CodaPerimetroDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = CodaLavoriRepository()

    # 1. ⭐ Azienda per azienda, il filtro del repository conta quello che
    #    conta la tabella.
    def test_filtro_per_azienda_come_conteggio_diretto(self) -> None:
        for azienda, attese in _righe_per_azienda().items():
            if azienda is None:
                continue
            with self.subTest(azienda=azienda):
                visti = self.repo.count_per_stato(owner_emittenti=[azienda])
                self.assertEqual(sum(visti.values()), attese)

    # 2. ⛔ Un perimetro vuoto non vede niente (non è «nessun filtro»), e
    #    l'SQL regge la lista vuota.
    def test_perimetro_vuoto_e_nessun_filtro(self) -> None:
        self.assertEqual(self.repo.count_per_stato(owner_emittenti=[]), {})
        self.assertEqual(
            sum(self.repo.count_per_stato(owner_emittenti=None).values()),
            sum(_righe_per_azienda().values()),
        )

    # 3. `is_mio` dice la stessa cosa del filtro: è la stessa regola.
    def test_is_mio_segue_il_perimetro(self) -> None:
        righe = _righe_per_azienda()
        aziende = [a for a in righe if a is not None]
        if not aziende:
            self.skipTest("coda senza lavori operatore su questo DB")
        mia = aziende[0]
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id, emittente_fiscale_id FROM dbops.coda_lavori ORDER BY id DESC LIMIT 50"
            )
            campione = cur.fetchall()
        for item_id, azienda in campione:
            with self.subTest(item_id=item_id):
                det = self.repo.get_dettaglio(item_id, caller_emittenti=[mia])
                assert det is not None
                self.assertEqual(det["is_mio"], azienda == mia)
                admin = self.repo.get_dettaglio(item_id, caller_emittenti=None)
                assert admin is not None
                self.assertEqual(admin["is_mio"], azienda is not None)
                nessuno = self.repo.get_dettaglio(item_id)
                assert nessuno is not None
                self.assertFalse(nessuno["is_mio"])
