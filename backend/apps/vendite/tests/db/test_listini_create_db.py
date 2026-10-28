# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le scritture di CREAZIONE di `ListiniRepository` sul DATABASE
#        PROVVISTO, dopo il passaggio al BB `execute_dynamic_insert`
#        (2026-09-26): `create_listino`, `create_versione`, `create_riga` e la
#        testata di `clone_versione`. Le righe nascono davvero e i valori
#        riletti sono quelli scritti: stringhe strippate, `meta` dict ->
#        `::jsonb` riletto come oggetto, `valido_al` None -> NULL (questi
#        metodi NON usano `skip_none`: None scrive NULL), colonne omesse ->
#        DEFAULT (`attivo`, `stato` BOZZA), whitelist RIGIDA (chiave estranea
#        -> RuntimeError, nessuna riga).
# Note: ⚠️ Il mondo si COSTRUISCE (regola zero): azienda, operatore e cliente
#       da `dbops.fn_pgtap_crea_mondo_cliente` (apre il contesto: il guard
#       emittente_scope del listino lo vuole), la TIPOLOGIA ammessa per la
#       utility da `dbops.fn_pgtap_crea_listino` (se ne usa solo la
#       tipologia), l'articolo da `fn_pgtap_crea_articolo` con la tipologia
#       del listino (`trgfn_listini_righe_guard_tipologia`).
#       Transazione SEMPRE annullata. Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) CreateListiniDbTests.test_listino_versione_riga_e_clone_nascono_coi_valori_scritti
2) CreateListiniDbTests.test_una_colonna_fuori_whitelist_e_rifiutata
"""
from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.listini_repository import ListiniRepository

_META_L = {"test_scope": "be_create_listini_db", "livello": "listino"}
_META_V = {"test_scope": "be_create_listini_db", "livello": "versione", "n": [1, 2]}
_META_R = {"test_scope": "be_create_listini_db", "livello": "riga", "annidato": {"k": True}}

_FIXTURE: tuple[str, ...] = (
    "CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('create listini db')",
    "CREATE TEMP TABLE _lst AS SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _mondo), 'create listini db')",
    # L'articolo nasce della tipologia del listino: e' struttura, si sceglie alla nascita.
    "CREATE TEMP TABLE _art AS SELECT dbops.fn_pgtap_crea_articolo('LSART-' || %(sfx)s, false,"
    " p_listino_tipologia_id => (SELECT tipologia_id FROM _lst)) AS articolo_id",
)


class CreateListiniDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: esegue `azione(cur, mondo)` nel mondo costruito, in una
    #        transazione SEMPRE annullata.
    def _nel_mondo(self, azione) -> None:
        sfx = uuid4().hex[:8].upper()
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    for passo in _FIXTURE:
                        cur.execute(passo, {"sfx": sfx})
                    cur.execute(
                        "SELECT m.utility_id, m.emittente_soggetto_ruolo_id, l.tipologia_id,"
                        "       a.articolo_id::text AS articolo_id, ar.uom_id"
                        "  FROM _mondo m, _lst l, _art a"
                        "  JOIN catalogo.articoli ar ON ar.id = a.articolo_id"
                    )
                    mondo = row_to_dict(cur)
                    assert mondo is not None
                    mondo["sfx"] = sfx
                    azione(cur, mondo)
            finally:
                transaction.set_rollback(True)

    def test_listino_versione_riga_e_clone_nascono_coi_valori_scritti(self):
        def _prova(cur, m):
            repo = ListiniRepository()
            # ── create_listino: il payload di `_extract_listino_payload` ──
            listino_id = repo.create_listino({
                "codice": f"  LSBE-{m['sfx']}  ",
                "descrizione": " Listino create BE ",
                "utility_id": m["utility_id"],
                "tipologia_id": m["tipologia_id"],
                "emittente_soggetto_ruolo_id": m["emittente_soggetto_ruolo_id"],
                "meta": _META_L,
            })
            cur.execute(
                "SELECT codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id,"
                "       attivo, meta, jsonb_typeof(meta) AS meta_tipo"
                "  FROM vendite.listini WHERE id = %s",
                [listino_id],
            )
            r = row_to_dict(cur)
            self.assertIsNotNone(r, "il listino creato non si rilegge (RLS?)")
            assert r is not None
            self.assertEqual(r["codice"], f"LSBE-{m['sfx']}")
            self.assertEqual(r["descrizione"], "Listino create BE")
            self.assertEqual(r["utility_id"], m["utility_id"])
            self.assertEqual(r["tipologia_id"], m["tipologia_id"])
            self.assertEqual(r["emittente_soggetto_ruolo_id"], m["emittente_soggetto_ruolo_id"])
            self.assertIs(r["attivo"], True)  # omesso -> DEFAULT
            self.assertEqual(r["meta_tipo"], "object")
            # Il jsonb arriva decodificato dal lettore comune (`row_to_dict`).
            self.assertEqual(r["meta"], _META_L)

            # ── create_versione: `valido_al` None esplicito (nullable) ──
            versione_id = repo.create_versione(listino_id, {
                "codice_versione": "  V001  ",
                "valido_dal": date(2083, 1, 1),
                "valido_al": None,
                "meta": _META_V,
            })
            cur.execute(
                "SELECT listino_id, codice_versione, valido_dal, valido_al, stato, attivo,"
                "       meta, jsonb_typeof(meta) AS meta_tipo"
                "  FROM vendite.listini_versioni WHERE id = %s",
                [versione_id],
            )
            v = row_to_dict(cur)
            self.assertIsNotNone(v)
            assert v is not None
            self.assertEqual(v["listino_id"], listino_id)
            self.assertEqual(v["codice_versione"], "V001")
            self.assertEqual(v["valido_dal"], date(2083, 1, 1))
            self.assertIsNone(v["valido_al"])
            self.assertEqual(v["stato"], "BOZZA")  # DEFAULT
            self.assertIs(v["attivo"], True)
            self.assertEqual(v["meta_tipo"], "object")
            self.assertEqual(v["meta"], _META_V)

            # ── create_riga: articolo come stringa UUID, prezzo Decimal ──
            riga_id = repo.create_riga(versione_id, {
                "articolo_id": m["articolo_id"],
                "uom_id": m["uom_id"],
                "prezzo": Decimal("12.34"),
                "meta": _META_R,
            })
            cur.execute(
                "SELECT listino_versione_id, articolo_id::text AS articolo_id, uom_id, prezzo,"
                "       attivo, meta, jsonb_typeof(meta) AS meta_tipo"
                "  FROM vendite.listini_righe WHERE id = %s",
                [riga_id],
            )
            rr = row_to_dict(cur)
            self.assertIsNotNone(rr)
            assert rr is not None
            self.assertEqual(rr["listino_versione_id"], versione_id)
            self.assertEqual(rr["articolo_id"], m["articolo_id"])
            self.assertEqual(rr["uom_id"], m["uom_id"])
            self.assertEqual(rr["prezzo"], Decimal("12.34"))
            self.assertIs(rr["attivo"], True)
            self.assertEqual(rr["meta_tipo"], "object")
            self.assertEqual(rr["meta"], _META_R)

            # ── clone_versione: il payload di `fn_clone_versione`
            #    (solo `clonable_fields`), testata forzata BOZZA ──
            clone_id = repo.clone_versione(
                listino_id=listino_id,
                src_versione_id=versione_id,
                target_data={
                    "codice_versione": " V002 ",
                    "valido_dal": date(2083, 6, 1),
                    "valido_al": date(2083, 12, 31),
                },
            )
            self.assertNotEqual(clone_id, versione_id)
            cur.execute(
                "SELECT listino_id, codice_versione, valido_dal, valido_al, stato, attivo, meta"
                "  FROM vendite.listini_versioni WHERE id = %s",
                [clone_id],
            )
            c = row_to_dict(cur)
            self.assertIsNotNone(c)
            assert c is not None
            self.assertEqual(c["listino_id"], listino_id)
            self.assertEqual(c["codice_versione"], "V002")
            self.assertEqual(c["valido_dal"], date(2083, 6, 1))
            self.assertEqual(c["valido_al"], date(2083, 12, 31))
            self.assertEqual(c["stato"], "BOZZA")
            self.assertIs(c["attivo"], True)
            # `meta` NON si clona: DEFAULT del DB.
            self.assertEqual(c["meta"], {})
            cur.execute(
                "SELECT articolo_id::text, uom_id, prezzo, attivo"
                "  FROM vendite.listini_righe WHERE listino_versione_id = %s",
                [clone_id],
            )
            self.assertEqual(
                cur.fetchall(), [(m["articolo_id"], m["uom_id"], Decimal("12.34"), True)],
            )

        self._nel_mondo(_prova)

    # Scopo: whitelist RIGIDA — una chiave estranea e' RuntimeError PRIMA
    #        dell'INSERT (nessuna riga, nessun errore di database), anche sulla
    #        testata del clone (attivo/meta non si clonano).
    def test_una_colonna_fuori_whitelist_e_rifiutata(self):
        def _prova(cur, m):
            repo = ListiniRepository()
            codice = f"LSBAD-{m['sfx']}"
            with self.assertRaisesRegex(RuntimeError, "colonne non ammesse: stato"):
                repo.create_listino({
                    "codice": codice,
                    "descrizione": "x",
                    "utility_id": m["utility_id"],
                    "tipologia_id": m["tipologia_id"],
                    "emittente_soggetto_ruolo_id": m["emittente_soggetto_ruolo_id"],
                    "stato": "ATTIVA",
                })
            cur.execute("SELECT count(*) FROM vendite.listini WHERE codice = %s", [codice])
            self.assertEqual(cur.fetchone()[0], 0)
            with self.assertRaisesRegex(RuntimeError, "colonne non ammesse: stato"):
                repo.create_versione(0, {"codice_versione": "V", "valido_dal": date(2083, 1, 1),
                                         "stato": "ATTIVA"})
            with self.assertRaisesRegex(RuntimeError, "colonne non ammesse: meta"):
                repo.clone_versione(
                    listino_id=0, src_versione_id=0,
                    target_data={"codice_versione": "V", "valido_dal": date(2083, 1, 1),
                                 "meta": {}},
                )

        self._nel_mondo(_prova)
