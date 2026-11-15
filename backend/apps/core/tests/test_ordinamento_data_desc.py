# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La CATENA che realizza la regola di Tid del 2026-09-02 — «gli
#        ordinamenti per DATA hanno sempre default DESC» — dal catalogo fino
#        all'intestazione cliccata.
#
#        ⭐ PERCHE' NON BASTA IL CODICE CHE LA APPLICA. La regola non e' scritta
#        da nessuna parte come elenco di colonne: `<ListaConfigurabile>` chiede
#        al CATALOGO quali colonne sono date (`ui.lista_colonna.tipo_dato`), che
#        e' la sede giusta — un elenco di nomi nel frontend sarebbe una seconda
#        verita' che diverge alla prima colonna aggiunta. Il prezzo di quella
#        scelta e' una catena a tre anelli:
#
#            seed (tipo_dato)  ->  catalogo API  ->  verso del primo click
#
#        ⛔ E il difetto che presidia e' SILENZIOSO in tutti e tre i punti: se
#        un anello si rompe, `campiCronologici` resta un insieme VUOTO. Nessun
#        errore, nessun warning — semplicemente le date tornano a partire ASC, e
#        se ne accorge solo chi si ricorda che dovevano partire DESC.
#
# ⚠️ NON SERVE IL DATABASE: si leggono il CSV del seed (che e' la sede di
#    `80_data`, mirror `runOnChange`) e i sorgenti. La query vera la esercita
#    gia' `test_lista_proiezione_campo_sorgente` contro il database.
# ------------------------------------------------------------
"""Indice test (0..N):

0. test_il_catalogo_espone_il_tipo_dato
   L'anello di mezzo: la query del catalogo colonne proietta `tipo_dato`.
   Senza, il frontend non puo' sapere quale colonna e' una data.

1. test_il_frontend_deriva_il_verso_dal_tipo_dato
   L'anello finale, e insieme il divieto: il verso si deriva dal `tipo_dato`
   del catalogo, non da un elenco di nomi scritto nel frontend.

2. test_il_primo_click_gira_solo_sulla_colonna_nuova
   Il click successivo NON si gira, o la colonna diventerebbe non invertibile:
   il secondo click ripeterebbe il primo.

2-bis. test_la_memoria_sopravvive_allo_stato_senza_ordinamento
   ⛔ `removable-sort` ha un TERZO stato in cui il campo applicato torna `null`:
   senza memoria, il click dopo sembra un primo click e l'ASC diventa
   irraggiungibile. Difetto trovato in collaudo sui DDT.

2-ter. test_lo_stato_senza_ordinamento_non_dichiara_una_direzione
   Nello stesso terzo stato la direzione e' `null`: dichiararla `desc` teneva
   la freccia disallineata dai dati.

3. test_esiste_almeno_una_colonna_data_ordinabile_a_catalogo
   Il verso che rende la regola ESIGIBILE: se nessuna colonna data fosse
   ordinabile, i test qui sopra sarebbero verdi su una regola che non tocca
   nessuno — verdi per sottrazione.
"""

from __future__ import annotations

import inspect
import unittest

from apps.ui.db.ui_repository import UiRepository
from apps.core.tests._repo import repo_root
from apps.core.tests._seed_csv import seed_ui

_TIPI_CRONOLOGICI = ("date", "datetime")


def _sorgente_lista_configurabile() -> str:
    percorso = (
        repo_root() / "frontend/src/core/components/ListaConfigurabile.vue"
    )
    return percorso.read_text(encoding="utf-8")


class OrdinamentoDataDescTests(unittest.TestCase):
    """La regola «le date partono DESC», presidiata anello per anello."""

    def test_il_catalogo_espone_il_tipo_dato(self) -> None:
        # ⚠️ Si legge il sorgente della QUERY, non il suo risultato: il
        #    risultato vorrebbe il database, e questo modulo esiste apposta per
        #    girare anche senza. E' l'anello in cui la rottura sarebbe piu'
        #    silenziosa — una colonna tolta da una `SELECT` non fa fallire
        #    niente, produce solo una chiave che non arriva piu'.
        sql = inspect.getsource(UiRepository.list_colonne_by_codice)
        self.assertIn(
            "tipo_dato",
            sql,
            "la query del catalogo colonne non proietta piu' `tipo_dato`: il "
            "frontend non puo' sapere quale colonna e' una data, e gli "
            "ordinamenti per data tornano a partire ASC senza dirlo",
        )

    def test_il_frontend_deriva_il_verso_dal_tipo_dato(self) -> None:
        src = _sorgente_lista_configurabile()
        self.assertIn(
            "TIPI_DATO_CRONOLOGICI",
            src,
            "`ListaConfigurabile` non dichiara piu' i tipi cronologici: la "
            "regola «le date partono DESC» non ha piu' un posto in cui vivere",
        )
        # ⛔ La regola si legge dal CATALOGO. Un elenco di `campo_sorgente`
        #    scritto qui sarebbe una seconda verita' accanto a
        #    `ui.lista_colonna.tipo_dato`, e divergerebbe alla prima colonna
        #    data aggiunta a una qualunque delle liste.
        self.assertIn(
            "TIPI_DATO_CRONOLOGICI.has(c.tipo_dato)",
            src,
            "il verso non si deriva piu' dal `tipo_dato` del catalogo",
        )

    def test_il_primo_click_gira_solo_sulla_colonna_nuova(self) -> None:
        src = _sorgente_lista_configurabile()
        # La guardia che distingue il PRIMO click dai successivi: senza, una
        # colonna data resterebbe DESC a ogni click, cioe' NON INVERTIBILE.
        self.assertRegex(
            src,
            r"event\.sortField\s*!==\s*campoPrecedente",
            "manca la guardia sul PRIMO click: girando anche i click "
            "successivi una colonna data non si potrebbe piu' invertire — il "
            "secondo click ripeterebbe il primo",
        )
        self.assertRegex(
            src,
            r"sortOrder:\s*-1",
            "il verso di partenza non e' piu' DESC",
        )

    def test_la_memoria_sopravvive_allo_stato_senza_ordinamento(self) -> None:
        # 🔴 IL DIFETTO CHE QUESTO TEST PRESIDIA E' COSTATO UN COLLAUDO.
        #    `removable-sort` alterna asc -> desc -> NIENTE, e nel terzo stato
        #    il `sortField` applicato torna `null`. Confrontando il click
        #    successivo con le sole `props`, la stessa colonna sembrava NUOVA e
        #    veniva girata di nuovo a DESC: il ciclo si chiudeva su
        #    desc -> niente -> desc e l'ASC non si raggiungeva piu'.
        #    Trovato da Tid sulla lista DDT il 2026-09-02.
        src = _sorgente_lista_configurabile()
        self.assertIn(
            "ultimoCampoOrdinato",
            src,
            "manca la memoria del campo su cui si sta ciclando: senza, lo "
            "stato «ordinamento rimosso» cancella l'informazione e una colonna "
            "data non torna piu' crescente",
        )
        # ⛔ ANCORATO A `campoPrecedente`, cioe' alla riga che DECIDE — non a
        #    una qualunque riga che nomini la memoria. La prima stesura di
        #    questo test cercava `props.sortField ?? ultimoCampoOrdinato` e
        #    trovava la riga che AGGIORNA la memoria in `onSort`: tolta la
        #    memoria dalla decisione, il test restava verde. Provato per
        #    mutazione, ed e' cosi' che si e' visto.
        self.assertRegex(
            src,
            r"campoPrecedente\s*=\s*props\.sortField\s*\?\?\s*ultimoCampoOrdinato",
            "il campo precedente non si legge piu' dalla memoria quando le "
            "`props` non ce l'hanno: e' proprio il caso dello stato intermedio",
        )

    def test_lo_stato_senza_ordinamento_non_dichiara_una_direzione(self) -> None:
        # ⛔ Con l'ordinamento RIMOSSO la direzione e' `null`, non `desc`.
        #    Scriverla `desc` teneva la prop `sortOrder` a -1 mentre il campo
        #    era sparito: al click seguente la prop non cambiava valore, il
        #    watcher di PrimeVue non scattava, e la freccia diceva una cosa
        #    mentre i dati ne dicevano un'altra.
        percorso = (
            repo_root() / "frontend/src/core/composables/useSearchTable.js"
        )
        src = percorso.read_text(encoding="utf-8")
        self.assertNotRegex(
            src,
            r"order_dir\s*=\s*event\.sortOrder\s*===\s*1\s*\?\s*'asc'\s*:\s*'desc'",
            "lo stato «ordinamento rimosso» torna a dichiarare `desc`: la "
            "freccia si desincronizza dai dati al click successivo",
        )
        self.assertRegex(
            src,
            r"store\.filters\.order_dir\s*=\s*event\.sortField",
            "la direzione non e' piu' condizionata alla PRESENZA del campo: "
            "senza campo non c'e' nessuna direzione da dichiarare",
        )

    def test_esiste_almeno_una_colonna_data_ordinabile_a_catalogo(self) -> None:
        colonne = seed_ui("lista_colonna.csv")
        cronologiche = [
            c for c in colonne
            if c["attivo"] == "t"
            and c["ordinabile"] == "t"
            and c["tipo_dato"] in _TIPI_CRONOLOGICI
        ]
        # ⭐ Il verso che ARMA il presidio. Senza questo, il giorno in cui
        #    nessuna colonna data fosse piu' ordinabile i tre test qui sopra
        #    resterebbero verdi presidiando una regola che non tocca nessuna
        #    lista — verdi per sottrazione, che e' il modo in cui un presidio
        #    smette di presidiare senza dirlo.
        self.assertTrue(
            cronologiche,
            "nessuna colonna `date`/`datetime` ordinabile in tutto il "
            "catalogo: la regola «le date partono DESC» non ha piu' niente su "
            "cui applicarsi, e i test di questo modulo sono verdi a vuoto",
        )
        # E i `tipo_dato` del seed devono restare quelli che il frontend cerca:
        # un rename dell'ENUM a database renderebbe la regola muta.
        tipi = {c["tipo_dato"] for c in colonne if c["attivo"] == "t"}
        self.assertTrue(
            set(_TIPI_CRONOLOGICI) & tipi,
            f"i tipi cronologici attesi {_TIPI_CRONOLOGICI} non compaiono piu' "
            f"nel seed (tipi presenti: {sorted(tipi)}): o l'ENUM e' cambiato, o "
            "questo modulo cerca una parola che non esiste piu'",
        )
