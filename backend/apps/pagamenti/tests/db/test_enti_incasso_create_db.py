# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `PagamentiRepository.create_ente_incasso` sul DATABASE PROVVISTO, dopo
#        il passaggio al BB `execute_dynamic_insert` (2026-09-26): il canale
#        nasce davvero in `pagamenti.enti_incasso` coi quattro guard del
#        database attivi, e i valori riletti sono quelli scritti.
#        Presidia cio' che un mock non vede:
#          · `regole_match`/`meta` arrivano GIA' SERIALIZZATI dal service
#            (`json.dumps`): il BB li casta `::jsonb` (parametro `jsonb`) e il
#            database li salva come OGGETTO — riletti dal repository sono un
#            dict, non una stringa (un doppio `json.dumps` salverebbe una
#            stringa JSON, e il test lo direbbe);
#          · stringhe strippate, `formato_flusso` None -> NULL, `attivo`
#            omesso -> DEFAULT true;
#          · una colonna fuori whitelist e' RIFIUTATA prima dell'INSERT.
# Note: ⚠️ Il mondo si COSTRUISCE (regola zero): azienda e operatore da
#       `dbops.fn_pgtap_crea_mondo_cliente` (apre il contesto: enti_incasso e'
#       sotto RLS e senza GUC la rilettura trova zero righe), la filiale da
#       `dbops.fn_pgtap_crea_filiale_bancaria`, poi conto e legame INCASSO
#       all'emittente — in DUE istruzioni, come in
#       `db/pgtap/pagamenti/test-sistemazioni-giro-completo.sql`: la policy
#       di `enti_incasso` chiede «esiste un conto TUO con questo id?», e nella
#       stessa CTE il legame non si vedrebbe.
#       Transazione SEMPRE annullata. Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) CreateEnteIncassoDbTests.test_il_canale_nasce_coi_valori_scritti
2) CreateEnteIncassoDbTests.test_una_colonna_fuori_whitelist_e_rifiutata
"""
from __future__ import annotations

import json
import unittest
from uuid import uuid4

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.services.error_manager import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.pagamenti.db.pagamenti_repository import PagamentiRepository

_REGOLE = {"causale_contiene": ["FATT", "NR"], "tolleranza": 0.01, "annidato": {"k": True}}
_META = {"test_scope": "be_create_ente_incasso_db"}

_FIXTURE: tuple[str, ...] = (
    "CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('create ente incasso db')",
    "CREATE TEMP TABLE _banca AS SELECT * FROM dbops.fn_pgtap_crea_filiale_bancaria('create ente incasso db')",
    """
    CREATE TEMP TABLE _conto AS
    WITH ins AS (
        INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, attivo, storicizza, meta)
        SELECT 'IT00BEENTEINC' || %(sfx)s, b.bank_branch_id, true, false,
               '{"test_scope": "be_create_ente_incasso_db"}'::jsonb
          FROM _banca b
        RETURNING id
    )
    SELECT id AS conto_id FROM ins
    """,
    """
    CREATE TEMP TABLE _legame AS
    WITH ins AS (
        INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
            (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, storicizza, meta)
        SELECT m.emittente_soggetto_ruolo_id, c.conto_id, 'INCASSO', false, false,
               '{"test_scope": "be_create_ente_incasso_db"}'::jsonb
          FROM _mondo m, _conto c
        RETURNING id
    )
    SELECT id AS legame_id FROM ins
    """,
)


class CreateEnteIncassoDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: esegue `azione(cur, mondo)` nel mondo costruito, in una
    #        transazione SEMPRE annullata.
    def _nel_mondo(self, azione) -> None:
        sfx = uuid4().hex[:10].upper()
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    for passo in _FIXTURE:
                        cur.execute(passo, {"sfx": sfx})
                    cur.execute(
                        "SELECT b.bank_branch_id, l.legame_id FROM _banca b, _legame l"
                    )
                    mondo = row_to_dict(cur)
                    assert mondo is not None
                    mondo["sfx"] = sfx
                    azione(cur, mondo)
            finally:
                transaction.set_rollback(True)

    # Scopo: i `campi` come li compone `enti_incasso_service._campi_dal_payload`
    #        (jsonb gia' serializzati).
    @staticmethod
    def _campi(m: dict) -> dict:
        return {
            "codice": f"  BEINC-{m['sfx']}  ",
            "descrizione": " Canale create BE ",
            "tipo": "BANCA",
            "bank_branch_id": m["bank_branch_id"],
            "soggetto_ruolo_conto_bancario_id": m["legame_id"],
            "formato_flusso": None,
            "regole_match": json.dumps(_REGOLE),
            "meta": json.dumps(_META),
        }

    def test_il_canale_nasce_coi_valori_scritti(self):
        def _prova(cur, m):
            repo = PagamentiRepository()
            ente_id = repo.create_ente_incasso(self._campi(m))

            cur.execute(
                "SELECT codice, descrizione, tipo, attivo, bank_branch_id, formato_flusso,"
                "       soggetto_ruolo_conto_bancario_id, jsonb_typeof(regole_match) AS regole_tipo,"
                "       jsonb_typeof(meta) AS meta_tipo"
                "  FROM pagamenti.enti_incasso WHERE id = %s",
                [ente_id],
            )
            r = row_to_dict(cur)
            self.assertIsNotNone(r, "il canale creato non si rilegge (RLS?)")
            assert r is not None
            self.assertEqual(r["codice"], f"BEINC-{m['sfx']}")
            self.assertEqual(r["descrizione"], "Canale create BE")
            self.assertEqual(r["tipo"], "BANCA")
            self.assertIs(r["attivo"], True)  # omesso -> DEFAULT
            self.assertEqual(r["bank_branch_id"], m["bank_branch_id"])
            self.assertIsNone(r["formato_flusso"])
            self.assertEqual(r["soggetto_ruolo_conto_bancario_id"], m["legame_id"])
            # Salvati come OGGETTO, non come stringa JSON.
            self.assertEqual(r["regole_tipo"], "object")
            self.assertEqual(r["meta_tipo"], "object")

            # La rilettura del repository (quella che il service restituisce).
            ente = repo.get_ente_incasso(ente_id)
            self.assertIsNotNone(ente)
            assert ente is not None
            self.assertIsInstance(ente["regole_match"], dict)
            self.assertEqual(ente["regole_match"], _REGOLE)
            self.assertIsInstance(ente["meta"], dict)
            self.assertEqual(ente["meta"], _META)

        self._nel_mondo(_prova)

    # Scopo: una colonna fuori whitelist (`codice_interno`: esiste nella
    #        tabella ma il canale non nasce con quella) e' rifiutata col codice
    #        del repository, PRIMA dell'INSERT: nessuna riga.
    def test_una_colonna_fuori_whitelist_e_rifiutata(self):
        def _prova(cur, m):
            campi = self._campi(m) | {"codice_interno": "NON_AMMESSO"}
            with self.assertRaises(ServiceError) as ctx:
                PagamentiRepository().create_ente_incasso(campi)
            self.assertEqual(ctx.exception.code, "E_PAGAMENTI_CHIAMATA_NON_VALIDA")
            self.assertIn("codice_interno", str(ctx.exception.detail))
            cur.execute(
                "SELECT count(*) FROM pagamenti.enti_incasso WHERE codice = %s",
                [f"BEINC-{m['sfx']}"],
            )
            self.assertEqual(cur.fetchone()[0], 0)

        self._nel_mondo(_prova)
