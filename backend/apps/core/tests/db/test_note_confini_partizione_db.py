# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il `target_tipo` che il backend scrive in una nota e' il CONFINE della
#        partizione in cui la nota deve finire: per ogni istanza di
#        `PartitionedNoteRepository` (vendite) e per i due bersagli delle note
#        di catalogo.
#
# ⛔ PERCHE' ESISTE. Il codice del tipo e' scritto due volte: nel confine della
#    partizione (`FOR VALUES IN (...)`, a DB) e nell'istanza del repository (nel
#    backend). Se divergono non c'e' nessun errore all'avvio: la prima scrittura
#    di una nota finisce senza partizione (23514 del routing) e la lista resta
#    vuota. E' successo col lotto 3 di brief-db-grammatica-unica-documenti
#    (2026-10-25): `DDT` -> `DDT_VENDITA`, `ARTICOLI` -> `ARTICOLO`. I test del
#    service sono mockati e non vedono la giuntura.
#
# ⭐ SI LEGGE LA STRUTTURA, non i dati: `pg_inherits` + `relpartbound` delle
#    partizioni, cioe' il progetto scritto. Vale anche su un database ricostruito
#    da zero.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    Solo letture.
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

0. test_ogni_repository_di_vendita_nomina_il_confine_della_sua_partizione
1. test_i_bersagli_delle_note_di_catalogo_sono_confini_di_partizione
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection

from apps.catalogo.db.catalogo_bom_repository import (
    NOTA_TARGET_ARTICOLO,
    NOTA_TARGET_COMPONENTE,
)
from apps.core.db.partitioned_note_repository import PartitionedNoteRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db import note_repositories

# Il confine di ogni partizione di una tabella note, per nome qualificato della
# partizione. `pg_get_expr` stampa `FOR VALUES IN ('DDT_VENDITA')`.
# ⚠️ Il nome si compone da `pg_namespace`, non da `oid::regclass::text`: quel
#    cast omette lo schema quando e' nel `search_path`, e il confronto con
#    `partition_table` dipenderebbe dalla configurazione della connessione.
_SQL_CONFINI = """
    SELECT n.nspname || '.' || p.relname,
           pg_get_expr(p.relpartbound, p.oid)
      FROM pg_inherits i
      JOIN pg_class p ON p.oid = i.inhrelid
      JOIN pg_namespace n ON n.oid = p.relnamespace
     WHERE i.inhparent = %s::regclass
"""


# Scopo: {partizione: confine} di una tabella note partizionata.
def _confini(padre: str) -> dict[str, str]:
    with connection.cursor() as cur:
        cur.execute(_SQL_CONFINI, [padre])
        return {r[0]: r[1] for r in cur.fetchall()}


class NoteConfiniPartizioneTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 0) Le istanze si raccolgono dal modulo, non da un elenco scritto qui: una
    #    partizione nuova cablata nel backend entra nel test da sola.
    def test_ogni_repository_di_vendita_nomina_il_confine_della_sua_partizione(self) -> None:
        repos = [
            v for v in vars(note_repositories).values()
            if isinstance(v, PartitionedNoteRepository)
        ]
        self.assertTrue(repos, "nessuna istanza in vendite.db.note_repositories")
        confini = _confini("vendite.note")
        for repo in repos:
            with self.subTest(partizione=repo.partition_table):
                self.assertIn(repo.partition_table, confini)
                self.assertEqual(
                    confini[repo.partition_table],
                    f"FOR VALUES IN ('{repo.target_tipo}')",
                )

    # 1) I due bersagli di catalogo, ognuno confine di una partizione.
    def test_i_bersagli_delle_note_di_catalogo_sono_confini_di_partizione(self) -> None:
        confini = set(_confini("catalogo.note").values())
        for codice in (NOTA_TARGET_ARTICOLO, NOTA_TARGET_COMPONENTE):
            with self.subTest(codice=codice):
                self.assertIn(f"FOR VALUES IN ('{codice}')", confini)
