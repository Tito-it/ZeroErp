# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: i lock di colonna che il backend NON ripete piu' nei suoi gap li
#        dichiara davvero `dbops.vw_non_editable_fields`, sul database vero
#        (BE2 di brief-db-revisione-dbops).
# Note: ⛔ Perche' esiste (2026-11-09). Dal giro 10a (D25) la vista legge il
#        lock VIVO, cioe' i trigger di lock montati; per questo
#        `catalogo.articoli.codice` e `anagrafiche.emittenti_fiscali.codice`
#        sono usciti dai gap Python di catalogo ed emittenti. I test unitari
#        di quei service mockano la vista: se il DB smettesse di dichiarare
#        uno dei due lock, il form tornerebbe a lasciarlo modificare senza
#        che nessuno di loro se ne accorga. Qui si legge il CONTRATTO (i
#        trigger del seed), non una popolazione.
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_le_colonne_uscite_dai_gap_le_dichiara_il_db
     `codice` di articoli ed emittenti e' nella vista; per l'articolo, che il
     dettaglio legge PER RECORD, anche nel ramo `fn_non_editable_fields`.
2. test_ogni_colonna_una_volta
     l'elenco del repository non ripete una colonna (`DISTINCT`).
"""

from __future__ import annotations

from unittest import TestCase

from apps.core.db.lock_columns_repository import LockColumnsRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto

_LOGGER_REPO = "apps.core.db.lock_columns_repository"

# Le colonne che il backend ha smesso di dichiarare da se' (BE2, 2026-11-09).
# Il quarto campo e' l'id con cui il service legge il ramo PER RECORD, o None
# se il service legge solo i lock statici (l'emittente:
# `compute_non_editable_fields` senza record).
# ⛔ L'id e' FABBRICATO, non letto dalla tabella: il lock statico non dipende
#    dal record, e una riga presa con `LIMIT 1` farebbe passare il test a vuoto
#    (con uno skip) su un DB ricostruito da zero, cioe' in CI. Un uuid che non
#    esiste spegne ogni lock condizionale e lascia in vista solo gli statici.
_USCITE_DAI_GAP: tuple[tuple[str, str, str, str | None], ...] = (
    ("catalogo", "articoli", "codice", "00000000-0000-0000-0000-000000000000"),
    ("anagrafiche", "emittenti_fiscali", "codice", None),
    # Il soggetto non ha mai avuto il gap: la sua lista non lo diceva affatto
    # fino al 2026-11-09, quando e' passata dal BB (S-BE-3). Stesso presidio.
    # Dal 2026-11-09 il dettaglio legge PER RECORD (CF e P.IVA sono lock
    # condizionali del DB): il ramo per record deve portare anche `codice`.
    ("anagrafiche", "soggetti", "codice", "00000000-0000-0000-0000-000000000000"),
)


class LockColumnsVivoDbTests(TestCase):
    """La vista del lock vivo copre cio' che i gap Python non coprono piu'."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("dbops.fn_non_editable_fields(text,text,text)")

    def setUp(self) -> None:
        LockColumnsRepository.cache_clear()
        self.addCleanup(LockColumnsRepository.cache_clear)

    def test_le_colonne_uscite_dai_gap_le_dichiara_il_db(self) -> None:
        for schema, tabella, colonna, record_id in _USCITE_DAI_GAP:
            with self.subTest(tabella=f"{schema}.{tabella}"):
                self.assertIn(
                    colonna, LockColumnsRepository.list_non_editable(schema, tabella),
                )
                if record_id is None:
                    continue
                # Il dettaglio dell'articolo legge il ramo per record: deve
                # portare anche lui i lock statici.
                # ⚠️ `assertNoLogs`: se `fn_non_editable_fields` fallisce il
                #    repository RICADE sui lock statici e logga, e l'asserzione
                #    sotto passerebbe lo stesso — verde per il fallback.
                with self.assertNoLogs(_LOGGER_REPO, level="WARNING"):
                    colonne = LockColumnsRepository.list_non_editable_for_record(
                        schema, tabella, record_id,
                    )
                self.assertIn(colonna, colonne)

    def test_ogni_colonna_una_volta(self) -> None:
        for schema, tabella, *_ in _USCITE_DAI_GAP:
            with self.subTest(tabella=f"{schema}.{tabella}"):
                colonne = LockColumnsRepository.list_non_editable(schema, tabella)
                self.assertEqual(len(colonne), len(set(colonne)))
