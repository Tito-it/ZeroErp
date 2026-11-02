# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test degli helper di ordinamento SQL (`apps/core/db/_helpers.py`):
#        `sql_order_direction` (verso + NULLS) e `sql_tiebreak_direction`
#        (verso del tiebreak, allineato alla colonna primaria).
#
#        Perche' esistono: entrambi gli helper decidono un pezzo di ORDER BY
#        interpolato in ~30 query. Un difetto qui non rompe nulla in modo
#        visibile — produce un ELENCO ORDINATO MALE, che e' il tipo di bug che
#        si scopre solo guardando una lista vera e chiedendosi perche' i
#        documenti dello stesso giorno sono al contrario.
#
# Indice test (0..N):
#   0. direzione_desc_mette_i_null_in_coda
#   1. direzione_asc_mette_i_null_in_testa
#   2. direzione_default_e_asc_salvo_default_desc
#   3. direzione_case_insensitive_e_tollera_spazi
#   4. tiebreak_segue_la_direzione
#   5. tiebreak_non_porta_mai_i_nulls
#   6. tiebreak_da_direzione_grezza
#   6a. direzione_estranea_e_value_error            (decisione Tid 2026-09-26)
#   6b. direzione_assente_prende_il_default           (None, vuota, soli spazi)
#   6c. order_dir_ammessa_e_la_stessa_regola
#   6d. tiebreak_rifiuta_una_direzione_estranea
#   7. repository_produce_order_by_col_tiebreak_allineato (end-to-end)
#   8. repository_asc_produce_tiebreak_asc (end-to-end)
#   9. nessun_call_site_incolla_nulls_alla_direzione (presidio statico)
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.db._helpers import (
    order_dir_ammessa,
    sql_order_direction,
    sql_tiebreak_direction,
)


class SqlOrderDirectionTests(TestCase):
    """Verso della colonna primaria + posizione dei NULL."""

    # 0-1. I NULL vanno dove starebbe lo zero, in entrambi i versi: e' la
    #      correzione del 2026-07-19 (il default PostgreSQL e' l'opposto e
    #      portava i campi vuoti in cima proprio ordinando dal piu' recente).
    def test_direzione_desc_mette_i_null_in_coda(self) -> None:
        self.assertEqual(sql_order_direction("desc"), "DESC NULLS LAST")

    def test_direzione_asc_mette_i_null_in_testa(self) -> None:
        self.assertEqual(sql_order_direction("asc"), "ASC NULLS FIRST")

    # 2. Senza indicazione si sale, salvo le liste che nascono dal piu' recente.
    def test_direzione_default_e_asc_salvo_default_desc(self) -> None:
        self.assertEqual(sql_order_direction(None), "ASC NULLS FIRST")
        self.assertEqual(sql_order_direction(""), "ASC NULLS FIRST")
        self.assertEqual(
            sql_order_direction(None, default_desc=True), "DESC NULLS LAST",
        )

    # 3. Il valore arriva da query string: maiuscole e spazi non devono
    #    cambiare l'esito (silenziosamente sarebbe un ordine sbagliato).
    def test_direzione_case_insensitive_e_tollera_spazi(self) -> None:
        for grezzo in ("DESC", " desc ", "Desc", "DeSc\n"):
            with self.subTest(valore=grezzo):
                self.assertEqual(sql_order_direction(grezzo), "DESC NULLS LAST")


class SqlTiebreakDirectionTests(TestCase):
    """Il tiebreak segue la colonna primaria (decisione Tid 2026-08-03)."""

    # 4. Il punto della modifica: prima era inchiodato ad ASC, quindi a parita'
    #    di data l'elenco si ribaltava dentro il giorno.
    def test_tiebreak_segue_la_direzione(self) -> None:
        self.assertEqual(
            sql_tiebreak_direction(sql_order_direction("desc")), "DESC",
        )
        self.assertEqual(
            sql_tiebreak_direction(sql_order_direction("asc")), "ASC",
        )

    # 5. Niente NULLS sul tiebreak: e' una chiave tecnica non nullable (`id`),
    #    e un `NULLS` di troppo qui sarebbe SQL valido ma ridondante — mentre
    #    su una colonna nullable reintrodurrebbe i vuoti in cima in DESC. E'
    #    il motivo per cui il tiebreak dev'essere `id` e non `numero`.
    def test_tiebreak_non_porta_mai_i_nulls(self) -> None:
        for order_dir in ("asc", "desc", None):
            with self.subTest(order_dir=order_dir):
                verso = sql_tiebreak_direction(sql_order_direction(order_dir))
                self.assertNotIn("NULLS", verso)
                self.assertIn(verso, ("ASC", "DESC"))

    # 6. Accetta anche una direzione grezza (i repository che la calcolano
    #    inline invece di passare da sql_order_direction).
    def test_tiebreak_da_direzione_grezza(self) -> None:
        self.assertEqual(sql_tiebreak_direction("DESC"), "DESC")
        self.assertEqual(sql_tiebreak_direction("asc"), "ASC")
        self.assertEqual(sql_tiebreak_direction(" desc nulls last "), "DESC")

    # 6d. ⛔ Fino al 2026-09-26 «qualunque cosa non-DESC vale ASC»: era proprio
    #     il terzo stato silenzioso, solo scritto come se non lo fosse.
    def test_tiebreak_rifiuta_una_direzione_estranea(self) -> None:
        for grezzo in ("qualsiasi", "", "   ", "DESCENDING", "ASCx NULLS FIRST"):
            with self.subTest(valore=grezzo), self.assertRaises(RuntimeError):
                sql_tiebreak_direction(grezzo)


class DirezioneEstraneaTests(TestCase):
    """⛔ Una direzione INDICATA e non riconosciuta e' rifiutata, non ASC.

    Decisione Tid 2026-09-26. Prima `giu` diventava ASC in silenzio: la lista
    rispondeva 200, ordinata al contrario di come era stata chiesta.
    """

    # 6a. Il messaggio e' il token della convenzione dei parametri di query
    #     (`qp_int_optional` & C.): e' cio' che il 400 `E_VALIDATION_INPUT`
    #     porta al client quando nessun service ha validato prima.
    def test_direzione_estranea_e_value_error(self) -> None:
        for grezzo in ("giu", "sideways", "desc;", "ASC NULLS LAST", "descending", "1"):
            for default_desc in (False, True):
                with self.subTest(valore=grezzo, default_desc=default_desc):
                    with self.assertRaisesRegex(ValueError, "^order_dir_invalid$"):
                        sql_order_direction(grezzo, default_desc=default_desc)

    # 6b. L'ASSENZA resta ammessa e prende il default: si rifiuta solo cio' che
    #     e' stato indicato. Soli spazi = assente (e' cio' che `qp_str` fa).
    def test_direzione_assente_prende_il_default(self) -> None:
        for assente in (None, "", "   ", "\n"):
            with self.subTest(valore=assente):
                self.assertEqual(sql_order_direction(assente), "ASC NULLS FIRST")
                self.assertEqual(
                    sql_order_direction(assente, default_desc=True), "DESC NULLS LAST",
                )

    # 6c. Il predicato che il service usa per il suo 400 di dominio
    #     (`PayloadValidator.validate_order_by`) e' LO STESSO del BB: dice si'
    #     esattamente dove il BB non solleva.
    def test_order_dir_ammessa_e_la_stessa_regola(self) -> None:
        for valore in (None, "", "  ", "asc", "DESC", " Desc ", "giu", "desc;", "ASC NULLS LAST"):
            with self.subTest(valore=valore):
                try:
                    sql_order_direction(valore)
                    solleva = False
                except ValueError:
                    solleva = True
                self.assertEqual(order_dir_ammessa(valore), not solleva)


class OrderByEndToEndTests(TestCase):
    """L'ORDER BY che arriva davvero al database, da un repository reale.

    Gli unit sugli helper non bastano: il difetto stava nei TEMPLATE SQL, dove
    il tiebreak era scritto a mano. Questi due test guardano la stringa
    eseguita, che e' il punto in cui il difetto si manifestava.
    """

    # Scopo: cursor finto che cattura la SQL eseguita.
    def _repo_con_cursor(self):
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = (0,)
        cursor.fetchall.return_value = []
        cursor.description = []
        return cursor

    # 7. Ordinando DESC, a parita' di valore vince l'id piu' ALTO (il record
    #    piu' recente): e' cio' che l'operatore si aspetta guardando una lista
    #    ordinata dal piu' recente.
    def test_repository_produce_order_by_col_tiebreak_allineato(self) -> None:
        from apps.anagrafiche.db.categorie_clienti_repository import (
            CategorieClientiRepository,
        )

        cursor = self._repo_con_cursor()
        with patch(
            "apps.anagrafiche.db.categorie_clienti_repository.connection.cursor",
            return_value=cursor,
        ):
            CategorieClientiRepository().list_categorie(
                order_by="descrizione", order_dir="desc",
            )
        sql = cursor.execute.call_args_list[-1][0][0]
        self.assertIn("ORDER BY cc.descrizione DESC NULLS LAST, cc.id DESC", sql)

    # 8. Simmetrico in salita: il tiebreak non resta inchiodato al verso
    #    opposto (che era il difetto).
    def test_repository_asc_produce_tiebreak_asc(self) -> None:
        from apps.anagrafiche.db.categorie_clienti_repository import (
            CategorieClientiRepository,
        )

        cursor = self._repo_con_cursor()
        with patch(
            "apps.anagrafiche.db.categorie_clienti_repository.connection.cursor",
            return_value=cursor,
        ):
            CategorieClientiRepository().list_categorie(
                order_by="descrizione", order_dir="asc",
            )
        sql = cursor.execute.call_args_list[-1][0][0]
        self.assertIn("ORDER BY cc.descrizione ASC NULLS FIRST, cc.id ASC", sql)


class NullsIncollatiAllaDirezioneTests(TestCase):
    """⛔ Nessun call-site deve aggiungere `NULLS ...` dopo `{direction}`.

    🔴 **Questo presidio nasce da un difetto vero, trovato il 2026-08-18**:
    `list_dash_competenza_errori` interpolava
    `ORDER BY {sort_col} {direction} NULLS LAST`, e siccome `direction` porta
    gia' la clausola (`ASC NULLS FIRST` / `DESC NULLS LAST`) l'SQL usciva
    `ASC NULLS FIRST NULLS LAST`: PostgreSQL lo rifiuta, e la lista
    «Competenza — errori vivi» rispondeva **500 su ogni click di
    intestazione**, su tutte e cinque le colonne ordinabili.

    ⚠️ **Nessun presidio esistente poteva vederlo**, ed e' il motivo per cui
    questo e' statico: il controllo sul seed confronta catalogo e whitelist
    (non esegue SQL), e i test dei repository mockano `_query_paged_view`,
    quindi la query al database non arriva mai. Il difetto si vedeva solo
    cliccando una freccia — o provando un ORDER BY vero, che e' come e' saltato
    fuori.

    Il residuo veniva dall'unificazione dei 29 call-site in
    `sql_order_direction` (2026-07-19): la sua docstring dichiara che «3
    avevano un NULLS LAST fisso incollato al template», e su quel call-site il
    pezzo vecchio non era stato tolto.
    """

    # Scopo: sorgenti Python del backend, esclusi i test.
    def _sorgenti(self):
        from pathlib import Path

        radice = Path(__file__).resolve()
        while not (radice / "apps").is_dir():
            radice = radice.parent
        for percorso in (radice / "apps").rglob("*.py"):
            if "/tests/" not in str(percorso):
                yield percorso

    def test_nessun_call_site_incolla_nulls_alla_direzione(self) -> None:
        import re

        # ⚠️ SOLO `{direction}`, e non e' pigrizia: e' il nome con cui **tutti**
        #    i 35 call-site chiamano il risultato di `sql_order_direction`
        #    (misurato). Il segnaposto `{dir}` di `coda_lavori/repository.py` e
        #    `pipeline_repository.py` portava invece la direzione NUDA, e li'
        #    `{dir} NULLS LAST` era scritto giusto — ritirato il 2026-09-26: le
        #    due code passano da `sql_order_clause(rifiuta_fuori_whitelist=True)`.
        #    La prima stesura di questo presidio li segnalava tutti e sei: un
        #    presidio che da' falsi positivi viene disattivato dal primo che ci
        #    sbatte, e con lui se ne va la parte che serviva.
        sospetto = re.compile(r"\{direction\}\s+NULLS", re.I)
        colpevoli = [
            f"{percorso.name}:{n}"
            for percorso in self._sorgenti()
            for n, riga in enumerate(
                percorso.read_text(encoding="utf-8").splitlines(), 1
            )
            if sospetto.search(riga)
        ]
        self.assertEqual(
            colpevoli, [],
            "`NULLS ...` incollato dopo la direzione: `sql_order_direction` la "
            "porta gia', e l'SQL risultante e' sintatticamente invalido — la "
            "lista risponde 500 su ogni ordinamento. Togliere il pezzo fisso: "
            + "; ".join(colpevoli),
        )
