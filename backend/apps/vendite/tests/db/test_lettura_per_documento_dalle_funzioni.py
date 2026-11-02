# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I QUATTRO PUNTI del backend che leggono la merce PER DOCUMENTO dalle
#        funzioni con la chiusura dentro (giro 1-2 di
#        `brief-db-partita-merce-per-documento`, richieste BE §8.4 e §9.4):
#        `list_partite_merce`, `list_situazione_merce_ordine`,
#        `list_situazione_merce_accrediti` e `ResiRepository.list_da_accreditare`.
#
#        UN TEST PER PUNTO, ed e' la regola: i BB (`sorgente_per_documento`
#        per le funzioni, `lettura_coda_per_documento` per le code) unificano
#        la SCELTA della forma, non il TRASPORTO — che l'espressione
#        finisca nel `FROM`, che il vecchio `WHERE` sul documento sia sparito,
#        che i parametri della sorgente stiano PRIMA di quelli del filtro (anche
#        nel COUNT di ripiego) resta scritto in ciascun punto, e ciascun punto
#        ha il suo modo di sbagliare senza errore: un array sbagliato risponde
#        le righe di un altro documento con la stessa forma; un parametro
#        fuori ordine risponde la coda di un altro DDT.
#
#        Due meta': i punti col cursor mockato (la forma dell'SQL e l'ordine dei
#        parametri, senza DB), e la traversata sul DB VERO degli otto rami
#        (4 punti x DDT/ordine) — perche' un contratto dichiarato si prova per
#        intero: un `%s` in piu', un cast mancante o una colonna della vista che
#        la funzione non ha e' un 500, non un test rosso.
#
#        ⚠️ La meta' e2e RICHIEDE IL DB VERO (`ZEROERP_TEST_DB_E2E=1`) e non
#        lascia niente: sole letture, in transazione annullata. Usa un id
#        qualunque (anche inesistente): il contratto si attraversa lo stesso —
#        zero righe con le colonne giuste e' una risposta, un errore SQL no.
# ------------------------------------------------------------

"""Indice test previsti.

Mock cursor (nessun DB):
 1) test_partite_merce_per_ddt_e_per_ordine
 2) test_situazione_merce_ordine_per_ddt_e_per_ordine
 3) test_coda_accrediti_del_pannello_legge_la_funzione_senza_predicato
 4) test_coda_riconsegne_del_pannello_resta_sulla_vista_col_predicato
 5) test_coda_di_lavoro_accrediti_con_documento_legge_la_funzione
 6) test_coda_di_lavoro_accrediti_senza_documento_resta_sulla_vista
 7) test_coda_di_lavoro_conteggio_di_ripiego_porta_i_parametri_della_sorgente
 8) test_coda_di_lavoro_riconsegne_resta_sul_predicato

DB vero (opt-in `ZEROERP_TEST_DB_E2E=1`):
 9) test_gli_otto_rami_attraversano_il_db
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.vendite.db.resi_repository import ResiRepository
from apps.vendite.db.vendite_repository import VenditeRepository

_FN_PARTITE = "vendite.fn_partite_merce"
_FN_SITUAZIONE = "vendite.fn_situazione_merce_ordine"
_FN_ACCREDITI = "vendite.fn_resi_da_accreditare"
_VW_ACCREDITI = "vendite.vw_resi_da_accreditare"
_VW_RICONSEGNE = "vendite.vw_resi_da_riconsegnare"

_PER_DDT = "(ARRAY[%s]::bigint[], NULL)"
_PER_ORDINE = "(NULL, ARRAY[%s]::bigint[])"


# Scopo: cursor mockato senza righe: qui conta l'SQL eseguito, non il risultato.
def _cursor_vuoto() -> MagicMock:
    cursor = MagicMock()
    cursor.description = []
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = (0,)
    return cursor


# Scopo: aggancia il cursor al context manager di `connection.cursor()` del
#        modulo indicato (ogni repository importa `connection` per suo conto).
def _patch_connection(modulo: str, cursor: MagicMock):
    patcher = patch(f"{modulo}.connection")
    conn = patcher.start()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return patcher


# Scopo: SQL normalizzato (spazi) e parametri dell'ultima `execute`.
def _ultima_execute(cursor: MagicMock) -> tuple[str, list]:
    sql, params = cursor.execute.call_args.args
    return " ".join(sql.split()), list(params)


# ⚠️ `SimpleTestCase`, non `unittest.TestCase`: qui OGNI accesso al database
#    e' mockato, e la classe di Django e' l'unica che lo pretende — un mock
#    dimenticato fallisce con `DatabaseOperationForbidden` invece di parlare
#    col DB di sviluppo e restare verde raccontando una cosa che in CI non
#    succede (AGENTS.md §Regole test Django). La classe e2e sotto invece il DB
#    vero lo vuole, e resta `unittest.TestCase`.
class LetturaPerDocumentoDalleFunzioniTests(SimpleTestCase):
    """La forma dell'SQL nei quattro punti, col cursor mockato."""

    def setUp(self) -> None:
        self.cursor = _cursor_vuoto()
        self.addCleanup(_patch_connection("apps.vendite.db.vendite_repository", self.cursor).stop)
        self.addCleanup(_patch_connection("apps.vendite.db.resi_repository", self.cursor).stop)
        # `fetch_paged_with_total` vive in core: la sua `connection` e' un'altra.
        self.addCleanup(_patch_connection("apps.core.db._helpers", self.cursor).stop)

    # Scopo: le due asserzioni comuni a ogni punto sulla funzione: la sorgente
    #        e' nel FROM con l'array giusto, e non c'e' piu' un WHERE sul
    #        documento (la vista e il predicato vecchio sono spariti).
    def _assert_legge_la_funzione(
        self, sql: str, params: list, *, funzione: str, ramo: str, id_atteso: int, vista: str
    ) -> None:
        self.assertIn(f"FROM {funzione}{ramo}", sql)
        self.assertNotIn(vista, sql)
        for predicato_vecchio in ("ddt_id = %s", "ordine_id = %s", "EXISTS ("):
            self.assertNotIn(predicato_vecchio, sql)
        self.assertEqual(params[0], id_atteso)

    # Scopo: punto 1 — le partite. Per DDT il primo array, per ordine il
    #        secondo; il resto della query (join di decodifica, ORDER BY) resta.
    def test_partite_merce_per_ddt_e_per_ordine(self) -> None:
        repo = VenditeRepository()
        repo.list_partite_merce(ddt_id=140)
        sql, params = _ultima_execute(self.cursor)
        self._assert_legge_la_funzione(
            sql, params, funzione=_FN_PARTITE, ramo=_PER_DDT, id_atteso=140, vista="vw_partite_merce"
        )
        self.assertEqual(params, [140])
        self.assertIn("ORDER BY d.data, p.ddt_id, dr.riga_nr, p.ddt_riga_id", sql)

        repo.list_partite_merce(ordine_id=240)
        sql, params = _ultima_execute(self.cursor)
        self._assert_legge_la_funzione(
            sql, params, funzione=_FN_PARTITE, ramo=_PER_ORDINE, id_atteso=240, vista="vw_partite_merce"
        )
        with self.assertRaises(ValueError):
            repo.list_partite_merce()

    # Scopo: punto 2 — la situazione per riga d'ordine. Per DDT NON c'e' piu'
    #        l'`EXISTS` sul fulfillment scritto qui: lo fa la funzione.
    def test_situazione_merce_ordine_per_ddt_e_per_ordine(self) -> None:
        repo = VenditeRepository()
        repo.list_situazione_merce_ordine(ordine_id=240)
        sql, params = _ultima_execute(self.cursor)
        self._assert_legge_la_funzione(
            sql, params, funzione=_FN_SITUAZIONE, ramo=_PER_ORDINE, id_atteso=240,
            vista="vw_situazione_merce_ordine",
        )
        self.assertEqual(params, [240])
        self.assertIn("ORDER BY s.ordine_id, s.riga_nr, s.ordine_riga_id", sql)

        repo.list_situazione_merce_ordine(ddt_id=140)
        sql, params = _ultima_execute(self.cursor)
        self._assert_legge_la_funzione(
            sql, params, funzione=_FN_SITUAZIONE, ramo=_PER_DDT, id_atteso=140,
            vista="vw_situazione_merce_ordine",
        )
        self.assertNotIn("ordini_righe_fulfillment", sql)
        with self.assertRaises(ValueError):
            repo.list_situazione_merce_ordine(ordine_id=1, ddt_id=2)

    # Scopo: punto 3 — la coda accrediti DEL PANNELLO: funzione nel FROM,
    #        nessun WHERE (il predicato del BB non serve piu' qui).
    def test_coda_accrediti_del_pannello_legge_la_funzione_senza_predicato(self) -> None:
        repo = VenditeRepository()
        repo.list_situazione_merce_accrediti(ddt_id=140)
        sql, params = _ultima_execute(self.cursor)
        self._assert_legge_la_funzione(
            sql, params, funzione=_FN_ACCREDITI, ramo=_PER_DDT, id_atteso=140, vista=_VW_ACCREDITI
        )
        self.assertNotIn("WHERE", sql)
        self.assertEqual(params, [140])
        self.assertIn("v.etichetta", sql)

        repo.list_situazione_merce_accrediti(ordine_id=240)
        sql, params = _ultima_execute(self.cursor)
        self._assert_legge_la_funzione(
            sql, params, funzione=_FN_ACCREDITI, ramo=_PER_ORDINE, id_atteso=240, vista=_VW_ACCREDITI
        )

    # Scopo: 🔴 la coda RI-CONSEGNE del pannello NON cambia: la vista non
    #        legge la partita, non ha una funzione, e il predicato del BB resta
    #        (§9.4). E' il punto che una sostituzione «a tappeto» avrebbe rotto.
    def test_coda_riconsegne_del_pannello_resta_sulla_vista_col_predicato(self) -> None:
        repo = VenditeRepository()
        repo.list_situazione_merce_riconsegne(ordine_id=240)
        sql, params = _ultima_execute(self.cursor)
        self.assertIn(f"FROM {_VW_RICONSEGNE} v", sql)
        self.assertIn("WHERE EXISTS (", sql)
        self.assertIn("ordini_righe_fulfillment", sql)
        self.assertEqual(params, [240])
        self.assertNotIn("fn_resi_da", sql)

    # Scopo: punto 4 — la coda DI LAVORO accrediti col documento: funzione nel
    #        FROM, il documento NON e' nel WHERE (lo filtra la funzione), e i
    #        parametri della sorgente stanno PRIMA di quelli dei filtri.
    def test_coda_di_lavoro_accrediti_con_documento_legge_la_funzione(self) -> None:
        repo = ResiRepository()
        repo.list_da_accreditare(
            ddt_id=140, etichetta="DOVUTA", billing_account_id=9, limit=50, offset=0
        )
        sql, params = _ultima_execute(self.cursor)
        self.assertIn(f"FROM {_FN_ACCREDITI}{_PER_DDT} v", sql)
        self.assertNotIn(_VW_ACCREDITI, sql)
        self.assertNotIn("v.ddt_id = %s", sql)
        self.assertIn("v.billing_account_id = %s", sql)
        self.assertIn("v.etichetta = %s", sql)
        # sorgente, poi i filtri nell'ordine del WHERE, poi LIMIT/OFFSET
        self.assertEqual(params, [140, 9, "DOVUTA", 50, 0])

        repo.list_da_accreditare(ordine_id=240, limit=50, offset=0)
        sql, params = _ultima_execute(self.cursor)
        self.assertIn(f"FROM {_FN_ACCREDITI}{_PER_ORDINE} v", sql)
        self.assertNotIn("EXISTS (", sql)
        self.assertEqual(params, [240, 50, 0])

    # Scopo: senza documento la coda di lavoro resta sulla VISTA: e' la coda
    #        aperta a mano, «tutte», ed e' `fn(NULL, NULL)` per costruzione.
    def test_coda_di_lavoro_accrediti_senza_documento_resta_sulla_vista(self) -> None:
        ResiRepository().list_da_accreditare(limit=50, offset=0)
        sql, params = _ultima_execute(self.cursor)
        self.assertIn(f"FROM {_VW_ACCREDITI} v", sql)
        self.assertNotIn("fn_resi_da_accreditare", sql)
        self.assertEqual(params, [50, 0])

    # Scopo: 🔴 IL PUNTO PIU' FACILE DA SBAGLIARE SENZA ERRORE. Pagina oltre
    #        l'ultima (0 righe, offset > 0): `fetch_paged_with_total` esegue il
    #        COUNT di ripiego, che deve leggere la STESSA sorgente con gli
    #        STESSI parametri nello stesso ordine — un COUNT sulla vista
    #        direbbe il totale di TUTTI i DDT a chi guarda la coda di uno.
    def test_coda_di_lavoro_conteggio_di_ripiego_porta_i_parametri_della_sorgente(self) -> None:
        ResiRepository().list_da_accreditare(
            ddt_id=140, billing_account_id=9, limit=50, offset=100
        )
        self.assertEqual(self.cursor.execute.call_count, 2, "atteso il COUNT di ripiego")
        count_sql, count_params = _ultima_execute(self.cursor)
        self.assertTrue(count_sql.startswith("SELECT COUNT(*) FROM "))
        self.assertIn(f"FROM {_FN_ACCREDITI}{_PER_DDT} v", count_sql)
        self.assertIn("WHERE v.billing_account_id = %s", count_sql)
        self.assertEqual(count_params, [140, 9])

    # Scopo: la coda di lavoro RI-CONSEGNE non cambia (stesso motivo del punto
    #        del pannello): vista + predicato del BB.
    def test_coda_di_lavoro_riconsegne_resta_sul_predicato(self) -> None:
        ResiRepository().list_da_riconsegnare(ddt_id=140, limit=50, offset=0)
        sql, params = _ultima_execute(self.cursor)
        self.assertIn(f"FROM {_VW_RICONSEGNE} v", sql)
        self.assertIn("v.ddt_id = %s", sql)
        self.assertEqual(params, [140, 50, 0])


class LetturaPerDocumentoSulDbTests(TestCase):
    """Gli otto rami attraversano il DB vero: contratto provato per intero."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: ogni ramo esegue e risponde una lista con le colonne del contratto
    #        BE — cioe' le funzioni hanno la firma e le colonne che il
    #        repository presume. ⚠️ E il documento si sceglie fra quelli CHE
    #        HANNO partite (dalla vista, che e' `fn(NULL, NULL)`): cosi' il ramo
    #        deve rispondere ALMENO UNA riga, e un array riempito dalla parte
    #        sbagliata — che risponde zero righe con la forma giusta — e' rosso
    #        invece di verde. Senza partite a DB si attraversa con un id
    #        qualunque (contratto dell'SQL) e il «almeno una» non si pretende:
    #        e' un limite d'ambiente, dichiarato dal messaggio.
    def test_gli_otto_rami_attraversano_il_db(self) -> None:
        from django.db import connection, transaction

        with transaction.atomic():
            with connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute(
                    "SELECT ddt_id, ordine_id FROM vendite.vw_partite_merce "
                    "WHERE ordine_id IS NOT NULL ORDER BY ddt_id LIMIT 1"
                )
                riga = cur.fetchone()
            con_partite = riga is not None
            ddt_id, ordine_id = (int(riga[0]), int(riga[1])) if riga else (1, 1)

            vendite = VenditeRepository()
            resi = ResiRepository()
            attese = {
                "partite": {"ddt_riga_id", "ddt_numero", "ordine_numero", "stato", "sospetto_duplicato_ordine"},
                "situazione": {"ordine_riga_id", "articolo_codice", "uom_codice", "giorni_ritardo"},
                "accrediti_pannello": {"resi_riga_id", "accredito_dovuto", "etichetta", "motivo"},
                "accrediti_coda": {"resi_riga_id", "accredito_dovuto", "etichetta", "blocco_codice"},
            }
            for nome, chiamate in {
                "partite": (
                    lambda: vendite.list_partite_merce(ddt_id=ddt_id),
                    lambda: vendite.list_partite_merce(ordine_id=ordine_id),
                ),
                "situazione": (
                    lambda: vendite.list_situazione_merce_ordine(ddt_id=ddt_id),
                    lambda: vendite.list_situazione_merce_ordine(ordine_id=ordine_id),
                ),
                "accrediti_pannello": (
                    lambda: vendite.list_situazione_merce_accrediti(ddt_id=ddt_id),
                    lambda: vendite.list_situazione_merce_accrediti(ordine_id=ordine_id),
                ),
                "accrediti_coda": (
                    lambda: resi.list_da_accreditare(ddt_id=ddt_id, limit=5, offset=0)[0],
                    lambda: resi.list_da_accreditare(ordine_id=ordine_id, limit=5, offset=0)[0],
                ),
            }.items():
                for ramo, chiamata in zip(("ddt", "ordine"), chiamate, strict=True):
                    with self.subTest(punto=nome, ramo=ramo):
                        righe = chiamata()
                        self.assertIsInstance(righe, list)
                        for riga in righe:
                            self.assertTrue(attese[nome] <= set(riga), f"{nome}: colonne {set(riga)}")
                        # Le due letture della merce DEVONO rispondere sul
                        # documento scelto apposta; le code accrediti no (una
                        # partita senza reso e' il caso normale).
                        if con_partite and nome in ("partite", "situazione"):
                            self.assertGreater(
                                len(righe), 0,
                                f"{nome}/{ramo}: zero righe su un documento che HA partite — "
                                "e' riempito l'array sbagliato?",
                            )
            # E il COUNT di ripiego, sul DB: pagina oltre l'ultima con la sorgente.
            righe, totale = resi.list_da_accreditare(ddt_id=ddt_id, limit=5, offset=10_000)
            self.assertEqual(righe, [])
            self.assertIsInstance(totale, int)
            transaction.set_rollback(True)
