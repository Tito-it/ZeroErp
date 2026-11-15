# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi sull'SQL del repository `pagamenti` — le tre cose che, se si
#        rompono, non danno un errore: danno un dato sbagliato.
# Note: ⚠️ Senza database: si guarda il TESTO dell'SQL e la composizione delle
#       clausole. Non sostituisce una prova sul campo, ma copre esattamente i
#       difetti che una prova sul campo scoprirebbe tardi — un elenco con le
#       righe doppie, un ordinamento invalido, un nome di colonna in chiaro
#       dentro un UPDATE.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LottiNonDuplicanoTests.test_i_lotti_si_aggregano_non_si_joinano
2) LottiNonDuplicanoTests.test_l_aggregazione_e_una_lateral
3) UpdateWhitelistTests.test_colonna_fuori_whitelist_rifiutata
4) UpdateWhitelistTests.test_colonna_in_whitelist_ammessa
5) UpdateWhitelistTests.test_meta_esce_castata_a_jsonb
6) UpdateWhitelistTests.test_la_riga_non_aggiorna_le_colonne_della_testata
7) CataloghiTests.test_gli_stati_richiedibili_esistono_a_catalogo
8) CataloghiTests.test_gli_stati_iniziali_esistono_a_catalogo
9) CataloghiTests.test_nessuno_stato_richiedibile_e_ritirato
10) OrdinamentiDichiaratiTests.test_le_colonne_delle_distinte_esistono
11) OrdinamentiDichiaratiTests.test_le_colonne_della_coda_esistono
12) OrdinamentiDichiaratiTests.test_le_colonne_delle_rate_esistono_nella_vista
13) OrdinamentiDichiaratiTests.test_la_coda_porta_la_sua_distinta
14) CataloghiTests.test_gli_stati_delle_code_esistono_a_catalogo
15) CataloghiTests.test_lo_stato_dell_abbinamento_esiste_a_catalogo
16) CataloghiTests.test_i_motivi_fuori_capienza_sono_quelli_della_vista
17) CataloghiTests.test_i_codici_errore_del_service_esistono_a_catalogo
18) EnteIncassoScrittureTests.test_regole_match_esce_castata_a_jsonb
19) EnteIncassoScrittureTests.test_regole_match_si_legge_come_oggetto
20) EnteIncassoScrittureTests.test_insert_colonna_fuori_whitelist_rifiutata
21) EnteIncassoScrittureTests.test_insert_passa_dal_bb_con_la_regola_jsonb
"""

import csv
import re
from unittest import TestCase
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apps.core.services.error_manager import ServiceError
from apps.pagamenti.db import pagamenti_repository as repo_mod
from apps.pagamenti.db.pagamenti_repository import (
    _COLONNE_DISTINTA_AGGIORNABILI,
    _COLONNE_ENTE_INCASSO_AGGIORNABILI,
    _COLONNE_ENTE_INCASSO_INSERIBILI,
    _JSONB_COLS,
    _COLONNE_RIGA_AGGIORNABILI,
    DISTINTE_SORT_COLUMNS,
    RATE_FUORI_CAPIENZA_SORT_COLUMNS,
    RIGHE_SORT_COLUMNS,
    PagamentiRepository,
)
from apps.pagamenti.services import pagamenti_service
from apps.core.tests._repo import repo_root

_SEED = (
    repo_root()
    / "db/changelog/migrations_v2/80_data/sql/pagamenti"
)


# Scopo: Legge un catalogo di stato dal CSV di seed (non dal database: cosi' il
#        presidio vale anche in CI, dove il DB non c'e').
def _catalogo(nome_file: str) -> dict[str, dict[str, str]]:
    with (_SEED / nome_file).open(encoding="utf-8") as f:
        return {r["codice_interno"]: r for r in csv.DictReader(f)}


class LottiNonDuplicanoTests(TestCase):
    """🔴 Il difetto trovato in revisione, e il presidio che lo tiene chiuso."""

    # Scopo: L'unico su `vendite_contabili_lotti` e' `(lotto_id, contabile_id)`
    #        e NON il solo `contabile_id`: una distinta puo' appartenere a piu'
    #        lotti. Un `LEFT JOIN` diretto DUPLICA la riga nell'elenco — e con
    #        essa sbaglia il conteggio totale, che e' il modo silenzioso di
    #        rompersi: la lista sembra piu' lunga e nessuno se ne accorge.
    def test_i_lotti_si_aggregano_non_si_joinano(self):
        self.assertNotIn(
            "LEFT JOIN pagamenti.vendite_contabili_lotti",
            repo_mod._DISTINTA_SELECT,
            "il JOIN diretto sui lotti duplica le distinte: va aggregato",
        )

    # Scopo: E l'aggregazione e' una LATERAL con `array_agg`, cioe' una riga
    #        sola per distinta qualunque sia il numero di lotti.
    def test_l_aggregazione_e_una_lateral(self):
        self.assertIn("array_agg(l.lotto_id", repo_mod._DISTINTA_SELECT)
        self.assertIn("LEFT JOIN LATERAL", repo_mod._DISTINTA_SELECT)


class UpdateWhitelistTests(TestCase):
    """⛔ Nessun nome di colonna entra in SQL senza passare dalla whitelist."""

    # Scopo: E' l'ULTIMO cancello prima che una chiave finisca dentro una
    #        stringa SQL. Il giorno in cui qualcuno chiamasse questi metodi con
    #        chiavi che arrivano da un payload, la differenza fra avere e non
    #        avere questo controllo sarebbe una SQL injection.
    def test_colonna_fuori_whitelist_rifiutata(self):
        with self.assertRaises(ServiceError):
            PagamentiRepository._set_clause(
                {"stato_id = 4, codice": "x"},
                _COLONNE_DISTINTA_AGGIORNABILI,
                "update_distinta",
            )

    def test_colonna_in_whitelist_ammessa(self):
        clause, params = PagamentiRepository._set_clause(
            {"importo_dichiarato": 10}, _COLONNE_DISTINTA_AGGIORNABILI, "x"
        )
        self.assertEqual(clause, "importo_dichiarato = %s")
        self.assertEqual(params, [10])

    # Scopo: `meta` e' jsonb e va castata, o l'UPDATE fallisce sul tipo.
    def test_meta_esce_castata_a_jsonb(self):
        clause, _ = PagamentiRepository._set_clause(
            {"meta": "{}"}, _COLONNE_DISTINTA_AGGIORNABILI, "x"
        )
        self.assertEqual(clause, "meta = %s::jsonb")

    # Scopo: Le due whitelist sono DUE: la testata non ha `importo`, la riga
    #        non ha `importo_dichiarato`. Confonderle scriverebbe su una
    #        colonna che non esiste, ma solo a runtime.
    def test_la_riga_non_aggiorna_le_colonne_della_testata(self):
        self.assertNotIn("importo_dichiarato", _COLONNE_RIGA_AGGIORNABILI)
        self.assertNotIn("importo", _COLONNE_DISTINTA_AGGIORNABILI)


class EnteIncassoScrittureTests(TestCase):
    """🔴 `regole_match` e' jsonb NOT NULL: una regola sola per scriverla e leggerla.

    Fino al 2026-09-26 l'INSERT la castava con un'eccezione scritta a mano,
    l'UPDATE no, e la lettura la serviva come STRINGA (il driver restituisce
    jsonb come testo e `_shape` non la decodificava). Nessun errore: un
    contratto che in ingresso vuole un oggetto e in uscita da' una stringa.
    Dal 2026-10-28 la lettura la decodifica il lettore comune (`rows_to_list`,
    dal tipo della colonna): `_shape` e' ritirato.
    """

    def test_regole_match_esce_castata_a_jsonb(self):
        clause, params = PagamentiRepository._set_clause(
            {"regole_match": '{"a": 1}'}, _COLONNE_ENTE_INCASSO_AGGIORNABILI, "x"
        )
        self.assertEqual(clause, "regole_match = %s::jsonb")
        self.assertEqual(params, ['{"a": 1}'])

    # Il dettaglio del canale col cursore come lo da' il driver: le due colonne
    # jsonb (tipo 3802) come testo.
    def test_regole_match_si_legge_come_oggetto(self):
        cursore = MagicMock()
        cursore.description = [
            SimpleNamespace(name="id", type_code=20),
            SimpleNamespace(name="regole_match", type_code=3802),
            SimpleNamespace(name="meta", type_code=3802),
        ]
        cursore.fetchall.return_value = [(7, '{"a": 1}', "{}")]
        with patch.object(repo_mod, "connection") as conn:
            conn.cursor.return_value.__enter__.return_value = cursore
            riga = PagamentiRepository().get_ente_incasso(7)
        assert riga is not None
        self.assertEqual(riga["regole_match"], {"a": 1})
        self.assertEqual(riga["meta"], {})

    # ⛔ L'INSERT passa dallo stesso cancello dell'UPDATE: prima componeva le
    #    colonne da `list(campi)` senza whitelist nel repository.
    def test_insert_colonna_fuori_whitelist_rifiutata(self):
        with patch.object(repo_mod, "execute_dynamic_insert") as bb:
            with self.assertRaises(ServiceError):
                PagamentiRepository().create_ente_incasso(
                    {"codice": "X", "codice_interno": "Y"}
                )
            bb.assert_not_called()

    def test_insert_passa_dal_bb_con_la_regola_jsonb(self):
        with patch.object(repo_mod, "execute_dynamic_insert", return_value={"id": 9}) as bb:
            esito = PagamentiRepository().create_ente_incasso({"codice": "X"})
        self.assertEqual(esito, 9)
        kwargs = bb.call_args.kwargs
        self.assertEqual(kwargs["allowed"], _COLONNE_ENTE_INCASSO_INSERIBILI)
        self.assertEqual(kwargs["jsonb"], _JSONB_COLS)
        self.assertIn("regole_match", _JSONB_COLS)


class CataloghiTests(TestCase):
    """⭐ I codici di stato scritti nel service esistono davvero a catalogo."""

    # Scopo: `STATI_DISTINTA_RICHIEDIBILI` e i suoi gemelli sono stringhe
    #        scritte a mano nel backend: dicono che cosa una PERSONA puo'
    #        chiedere, ed e' una policy legittima. ⚠️ Ma se un `codice_interno`
    #        cambiasse a catalogo, quelle stringhe smetterebbero di risolvere e
    #        il gesto fallirebbe a runtime. Questo presidio le lega al CSV.
    def test_gli_stati_richiedibili_esistono_a_catalogo(self):
        distinta = _catalogo("vendite_contabili_stati.csv")
        riga = _catalogo("vendite_contabili_righe_stati.csv")
        for codice in pagamenti_service.STATI_DISTINTA_RICHIEDIBILI:
            self.assertIn(codice, distinta, f"stato distinta {codice} non a catalogo")
        for codice in pagamenti_service.STATI_RIGA_RICHIEDIBILI:
            self.assertIn(codice, riga, f"stato riga {codice} non a catalogo")

    # Scopo: Idem per i due stati in cui gli oggetti NASCONO.
    def test_gli_stati_iniziali_esistono_a_catalogo(self):
        self.assertIn(
            pagamenti_service.STATO_DISTINTA_INIZIALE,
            _catalogo("vendite_contabili_stati.csv"),
        )
        self.assertIn(
            pagamenti_service.STATO_RIGA_SENZA_DESTINAZIONE,
            _catalogo("vendite_contabili_righe_stati.csv"),
        )

    # Scopo: Gli stati che compongono le DUE CODE del riconciliatore. Sono
    #        scritti a mano nel service (e' una policy: quali righe sono
    #        «lavoro da fare»), ma se un `codice_interno` cambiasse a catalogo
    #        la coda si svuoterebbe **senza errore** — e una coda vuota si
    #        legge come «non c'e' niente da fare».
    def test_gli_stati_delle_code_esistono_a_catalogo(self):
        catalogo = _catalogo("vendite_contabili_righe_stati.csv")
        for coda, stati in pagamenti_service.CODE_RIGHE.items():
            for codice in stati:
                self.assertIn(codice, catalogo, f"coda {coda}: {codice} non a catalogo")

    # Scopo: E lo stato in cui l'abbinamento porta la riga.
    def test_lo_stato_dell_abbinamento_esiste_a_catalogo(self):
        catalogo = _catalogo("vendite_contabili_righe_stati.csv")
        self.assertIn(pagamenti_service.STATO_RIGA_ABBINATA, catalogo)
        # ⭐ E deve essere POSTABILE: e' il senso dell'abbinamento — la riga
        #    diventa denaro pronto a essere registrato.
        self.assertEqual(
            catalogo[pagamenti_service.STATO_RIGA_ABBINATA]["is_postabile"], "true"
        )

    # Scopo: I due motivi per cui una rata esce dalla banda sono scritti nel
    #        service e prodotti da un `CASE` dentro la vista: due sedi per lo
    #        stesso vocabolario. ⚠️ Un refuso qui darebbe una lista vuota — la
    #        risposta piu' rassicurante possibile su un elenco che serve a NON
    #        far sparire del denaro.
    def test_i_motivi_fuori_capienza_sono_quelli_della_vista(self):
        vista = (
            repo_root()
            / "docs/it/dbzero/pagamenti/views/vw_rate_fuori_capienza.md"
        ).read_text(encoding="utf-8")
        for motivo in pagamenti_service.MOTIVI_FUORI_CAPIENZA:
            self.assertIn(motivo, vista, f"motivo {motivo} assente dalla vista")

    # Scopo: I codici errore che il service solleva DA SE' devono esistere a
    #        catalogo. ⚠️ Un codice non registrato non fallisce: `resolve()` lo
    #        manda su `E_GENERICO` -> **500**, cioe' un errore di dominio a 400
    #        diventa un errore di server. E' successo al passaggio da
    #        `E_VALIDATION_INPUT` al codice di dominio (2026-08-25).
    def test_i_codici_errore_del_service_esistono_a_catalogo(self):
        import csv as _csv

        catalogo = {
            r["codice"]
            for r in _csv.DictReader(
                (
                    repo_root()
                    / "db/changelog/migrations_v2/80_data/sql/config/codici_errore.csv"
                ).open(encoding="utf-8")
            )
        }
        for codice in (
            pagamenti_service.E_VALIDAZIONE,
            pagamenti_service.E_DISTINTA_NON_TROVATA,
            pagamenti_service.E_RIGA_NON_TROVATA,
            pagamenti_service.E_STATO_NON_CONFIGURATO,
        ):
            self.assertIn(codice, catalogo, f"{codice} non e' a catalogo")

    # Scopo: 🔴 Uno stato RITIRATO non si propone piu' a nessuno. `STORNATA` e'
    #        stata ritirata il 2026-08-21, e rimetterla in un menu riaprirebbe
    #        una porta che il lotto 2 ha chiuso.
    def test_nessuno_stato_richiedibile_e_ritirato(self):
        distinta = _catalogo("vendite_contabili_stati.csv")
        riga = _catalogo("vendite_contabili_righe_stati.csv")
        ritirati = [
            codice
            for catalogo, codici in (
                (distinta, pagamenti_service.STATI_DISTINTA_RICHIEDIBILI),
                (riga, pagamenti_service.STATI_RIGA_RICHIEDIBILI),
            )
            for codice in codici
            if (catalogo[codice].get("obsoleto_dal") or "").strip()
        ]
        self.assertEqual(ritirati, [], "stati ritirati proposti a chi lavora")


# I nomi che una SELECT rende disponibili all'ORDER BY esterno: gli alias
# `AS nome` piu' le colonne prese nude (`c.origine` -> `origine`).
def _nomi_esposti(frammento_sql: str) -> set[str]:
    alias = set(re.findall(r"\bAS\s+([a-z_][a-z0-9_]*)", frammento_sql, re.I))
    nude = set(re.findall(r"^\s*[a-z]{1,4}\.([a-z_][a-z0-9_]*),?\s*$",
                          frammento_sql, re.I | re.M))
    return {n.lower() for n in alias | nude}


class OrdinamentiDichiaratiTests(TestCase):
    """🔴 Ogni colonna che il contratto dichiara ordinabile deve ESISTERE.

    Il difetto che questo presidio chiude e' costato un 500: la coda dichiarava
    di saper ordinare per `distinta`, ma quella colonna non era nel SELECT — e
    l'ordinamento finisce in una clausola SQL, quindi non e' un valore
    sbagliato: e' una query che non parte. ⚠️ Un ordinamento si prova solo
    chiedendolo, e nessun test lo chiedeva TUTTO.
    """

    # Scopo: Le sei colonne ordinabili della lista distinte.
    def test_le_colonne_delle_distinte_esistono(self):
        esposti = _nomi_esposti(repo_mod._DISTINTA_SELECT) | _nomi_esposti(
            repo_mod._TOTALI_LATERAL
        )
        mancanti = sorted(
            col for col in DISTINTE_SORT_COLUMNS.values() if col not in esposti
        )
        self.assertEqual(mancanti, [], "colonne dichiarate ordinabili e assenti")

    # Scopo: Le quattro della coda del riconciliatore.
    def test_le_colonne_della_coda_esistono(self):
        esposti = _nomi_esposti(repo_mod._RIGA_CODA_SELECT)
        mancanti = sorted(
            col for col in RIGHE_SORT_COLUMNS.values() if col not in esposti
        )
        self.assertEqual(mancanti, [], "colonne dichiarate ordinabili e assenti")

    # Scopo: Le cinque delle rate fuori capienza, contro la definizione della
    #        VISTA — che e' doc auto-generata dal database, non una copia.
    # ⚠️ Questo controllo e' piu' debole degli altri due: cerca il nome nel
    #    testo della vista, quindi prende i refusi (il caso vero) ma non un
    #    nome che esiste in un altro punto della definizione.
    # ⭐ Un valore della whitelist puo' essere un COSTRUTTORE DI RIGA —
    #    `(fattura_numero, serie)` per il numero parlante (P-1-bis, 2026-09-17):
    #    si ordina per la coppia, non per il testo. Il presidio lo scompone e
    #    cerca OGNI colonna: escludere l'espressione lo renderebbe cieco proprio
    #    sul valore piu' facile da scrivere male.
    def test_le_colonne_delle_rate_esistono_nella_vista(self):
        vista = (
            repo_root()
            / "docs/it/dbzero/pagamenti/views/vw_rate_fuori_capienza.md"
        ).read_text(encoding="utf-8")
        colonne = {
            parte.strip()
            for espressione in RATE_FUORI_CAPIENZA_SORT_COLUMNS.values()
            for parte in espressione.strip("()").split(",")
        }
        mancanti = sorted(
            col for col in colonne if not re.search(rf"\b{re.escape(col)}\b", vista)
        )
        self.assertEqual(mancanti, [], "colonne assenti dalla vista")

    # Scopo: ⭐ E la promessa che ne era la ragione: una riga cross-distinta
    #        senza il documento da cui viene non si lavora — chi la guarda in
    #        coda deve poterci tornare.
    def test_la_coda_porta_la_sua_distinta(self):
        esposti = _nomi_esposti(repo_mod._RIGA_CODA_SELECT)
        for colonna in ("contabile_codice", "contabile_data", "contabile_origine"):
            self.assertIn(colonna, esposti)
