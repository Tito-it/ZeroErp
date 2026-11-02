# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'ordinamento di una lista di note (`pagina_note`) sul DB vero, coi
#        casi COSTRUITI: ordinando per posizione (o per ambito) il pareggio e'
#        l'ordine della nota (`seq`), poi l'id — lo stesso del preset
#        (`posizione`, `seq`).
# Note: ⛔ PERCHE' ESISTE. Fino al 2026-10-31 «ordina per posizione» passava dal
#       BB `sql_order_clause` con il solo spareggio `x.id`: due note HEADER
#       uscivano nell'ordine in cui erano state scritte, non in `seq`. Il caso
#       si costruisce scrivendo PRIMA la nota con `seq` piu' alto.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1`; tutto in una transazione annullata.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) NoteOrdineDbTests.test_per_posizione_il_pareggio_e_seq
2) NoteOrdineDbTests.test_calando_si_inverte_anche_seq
3) NoteOrdineDbTests.test_per_ambito_valgono_posizione_e_seq
4) NoteOrdineDbTests.test_senza_ordine_vale_il_preset
"""
from __future__ import annotations

import unittest

from django.db import connection

from apps.core.tests.db_e2e import (
    apri_contesto_operatore,
    apri_transazione_annullata,
    richiedi_db_provvisto,
)
from apps.vendite.db.note_repositories import NOTE_REPO_PREVENTIVO


class NoteOrdineDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: un preventivo con tre note di testata, scritte in quest'ordine:
    #        HEADER seq 2, HEADER seq 1, FOOTER seq 1. L'ordine atteso
    #        crescendo e' FOOTER, HEADER 1, HEADER 2 (posizione, poi seq).
    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT preventivo_id FROM dbops.fn_pgtap_crea_preventivo('ordine note')")
            self.preventivo_id = cur.fetchone()[0]
            apri_contesto_operatore(cur)
            cur.execute("SELECT id FROM config.note_stili WHERE attivo ORDER BY id LIMIT 1")
            stile = cur.fetchone()[0]

        def nota(posizione: str, seq: int) -> int:
            return NOTE_REPO_PREVENTIVO.create(self.preventivo_id, {
                "anchor_tipo": "DOCUMENTO", "posizione": posizione, "seq": seq,
                "id_stile": stile, "testo": f"Nota {posizione} {seq}",
            })

        header_2 = nota("HEADER", 2)
        header_1 = nota("HEADER", 1)
        footer_1 = nota("FOOTER", 1)
        self.crescente = [footer_1, header_1, header_2]

    def _ordine(self, order_by: str | None, order_dir: str | None) -> list[int]:
        righe, _ = NOTE_REPO_PREVENTIVO.list(
            self.preventivo_id, order_by=order_by, order_dir=order_dir, limit=200,
        )
        return [r["id"] for r in righe]

    def test_per_posizione_il_pareggio_e_seq(self) -> None:
        self.assertEqual(self._ordine("posizione", "asc"), self.crescente)

    # Le chiavi che seguono vanno nel verso della colonna, come lo spareggio.
    def test_calando_si_inverte_anche_seq(self) -> None:
        self.assertEqual(self._ordine("posizione", "desc"), self.crescente[::-1])

    # Tutte le note sono DOCUMENTO: a parita' di ambito decidono posizione e seq.
    def test_per_ambito_valgono_posizione_e_seq(self) -> None:
        self.assertEqual(self._ordine("anchor_tipo", "asc"), self.crescente)

    def test_senza_ordine_vale_il_preset(self) -> None:
        self.assertEqual(self._ordine(None, None), self.crescente)
