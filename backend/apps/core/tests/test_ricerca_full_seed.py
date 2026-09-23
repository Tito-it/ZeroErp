# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio del contratto fra il catalogo liste (`ui.lista_colonna`,
#        flag `ricercabile_full`) e le colonne su cui i repository fanno la
#        ricerca libera col BB `add_ricerca_full_condition`. Test senza DB:
#        legge i CSV di seed e le costanti del codice, quindi gira in CI.
# ------------------------------------------------------------
"""Indice test:

1. test_colonne_cercate_uguali_al_catalogo
   Per ogni lista registrata in `_RICERCHE`, le colonne che il repository passa
   al BB sono ESATTAMENTE le `ricercabile_full = t` attive del seed. Una colonna
   che manca non si trova (il difetto di Preventivi e Offerte del 2026-09-23:
   il catalogo dichiarava codice BA e id fiscale, il repository no); una in piu'
   da' risultati che l'operatore non sa spiegare.

2. test_ogni_lista_ricercabile_e_registrata_o_in_debito
   Ogni lista del seed con almeno una colonna `ricercabile_full = t` sta in
   `_RICERCHE` oppure nel registro di debito `_DEBITO_RICERCA_A_MANO`. Una lista
   nuova che non passa dal BB fa rosso qui, invece di nascere con la sua copia.

3. test_il_debito_non_cresce
   `_DEBITO_RICERCA_A_MANO` e `_DIVERGENZE_NOTE` possono solo calare: una lista
   convertita o riallineata va tolta, e una voce che nomina una lista che non
   ha piu' colonne ricercabili e' un'eccezione rimasta senza motivo.

4. test_bb_costruisce_la_condizione
   Il comportamento del BB: OR di `::text ILIKE`, termine escapato, soglia.
"""

import importlib
import unittest

from apps.core.db._helpers import add_ricerca_full_condition
from apps.core.tests.test_liste_configurabili_seed import (
    _colonne_attive,
    _seed,
)


# Scopo: le colonne di ricerca di una lista, lette dal simbolo che il
#        repository PASSA al BB (non da uno che gli somiglia per nome).
def _da_costante(modulo: str, costante: str):
    def risolvi() -> set[str]:
        return set(getattr(importlib.import_module(modulo), costante))

    return risolvi


# Scopo: le due code resi hanno le colonne dentro `_CODA_META`, per vista.
def _da_coda_resi(vista: str):
    def risolvi() -> set[str]:
        from apps.vendite.db import resi_repository as m

        return set(m._CODA_META[vista]["search_cols"])

    return risolvi


_V = "apps.vendite.db."

# Registro delle liste la cui ricerca libera passa dal BB:
# `codice lista` -> risolutore delle colonne passate ad `add_ricerca_full_condition`.
# ⚠️ Chi converte una lista del debito la AGGIUNGE qui e la TOGLIE dal debito.
_RICERCHE: tuple[tuple[str, object], ...] = (
    ("vendite.preventivi", _da_costante(_V + "preventivi_repository", "_RICERCA_COLS_PREVENTIVI")),
    ("vendite.offerte", _da_costante(_V + "offerte_repository", "_RICERCA_COLS_OFFERTE")),
    ("vendite.ordini", _da_costante(_V + "ordini_repository", "_RICERCA_COLS_ORDINI")),
    ("vendite.ddt", _da_costante(_V + "ddt_repository", "_RICERCA_COLS_DDT")),
    ("vendite.fatture", _da_costante(_V + "fatture_repository", "_RICERCA_COLS_FATTURE")),
    ("vendite.contratti", _da_costante(_V + "contratti_repository", "_RICERCA_COLS_CONTRATTI")),
    ("vendite.resi", _da_costante(_V + "resi_repository", "_RICERCA_COLS_RESI")),
    ("vendite.resi_da_accreditare", _da_coda_resi("vendite.vw_resi_da_accreditare")),
    ("vendite.resi_da_riconsegnare", _da_coda_resi("vendite.vw_resi_da_riconsegnare")),
    ("vendite.famiglie_documento", _da_costante(_V + "famiglie_repository", "_RICERCA_COLS")),
)

# Divergenze NOTE fra codice e catalogo: `codice lista` -> colonne cercate dal
# repository che il catalogo NON dichiara `ricercabile_full`.
# ⛔ Registro di debito, non lista di eccezioni: si chiude o accendendo il flag
#    a catalogo (seed del team DB) o togliendo la colonna dal repository.
_DIVERGENZE_NOTE: dict[str, frozenset[str]] = {
    # Si cercava gia' prima del BB (2026-09-23). Da decidere: il numero del DDT
    # di origine e' una ricerca voluta → flag a catalogo; altrimenti si toglie.
    "vendite.resi": frozenset({"ddt_origine_numero"}),
}

# Liste con colonne `ricercabile_full = t` la cui ricerca e' ancora scritta a
# mano (o vive in una funzione DB) e non passa dal BB. Fotografia del
# 2026-09-23: PUO' SOLO CALARE (test 3).
_DEBITO_RICERCA_A_MANO: frozenset[str] = frozenset({
    "amm.processi",
    "anagrafiche.categorie_clienti",
    "anagrafiche.clienti",
    "anagrafiche.emittente_billing_account",
    "anagrafiche.emittenti_fiscali",
    "anagrafiche.fornitori",
    "anagrafiche.indirizzi",
    "anagrafiche.soggetti",
    "catalogo.conversioni_uom",
    "catalogo.unita_misura",
    "catalogo.uom_tipi",
    "config.tipi_ruolo_tipi_indirizzo",
    "config.utilities_tipi_ruolo",
    "magazzino.disponibilita",
    "magazzino.disponibilita_articoli",
    "magazzino.inventari",
    "magazzino.inventario_piano",
    "magazzino.inventario_righe",
    "magazzino.lotti",
    "magazzino.magazzini",
    "magazzino.movimenti",
    "magazzino.rettifica_righe",
    "magazzino.rettifiche",
    "magazzino.ubicazioni",
    "pagamenti.distinta_righe",
    "pagamenti.distinte",
    "pagamenti.eccedenze",
    "pagamenti.rate",
    "pagamenti.rate_fuori_capienza",
    "pagamenti.righe",
    "pratiche.pratiche",
    "vendite.registri_numerazione",
})


# Scopo: i `campo_sorgente` ricercabili e attivi di una lista, dal seed.
def _ricercabili(codice: str) -> set[str]:
    return {
        r["campo_sorgente"] for r in _colonne_attive(codice)
        if r["ricercabile_full"] == "t" and r["campo_sorgente"]
    }


# Scopo: codici delle liste che hanno almeno una colonna ricercabile attiva.
def _liste_ricercabili() -> set[str]:
    return {
        d["codice"] for d in _seed("lista_definizione.csv") if _ricercabili(d["codice"])
    }


class RicercaFullSeedTests(unittest.TestCase):
    def test_colonne_cercate_uguali_al_catalogo(self):
        for codice, risolvi in _RICERCHE:
            with self.subTest(lista=codice):
                cercate = risolvi()
                attese = _ricercabili(codice) | _DIVERGENZE_NOTE.get(codice, frozenset())
                self.assertEqual(
                    cercate, attese,
                    f"{codice}: mancano {sorted(attese - cercate)}, "
                    f"in piu' {sorted(cercate - attese)} rispetto al catalogo",
                )

    def test_ogni_lista_ricercabile_e_registrata_o_in_debito(self):
        registrate = {c for c, _ in _RICERCHE}
        scoperte = _liste_ricercabili() - registrate - _DEBITO_RICERCA_A_MANO
        self.assertFalse(
            scoperte,
            f"liste con colonne `ricercabile_full` senza BB e fuori dal debito: "
            f"{sorted(scoperte)} — cercare con `add_ricerca_full_condition` e "
            f"registrarle in `_RICERCHE`",
        )

    def test_il_debito_non_cresce(self):
        registrate = {c for c, _ in _RICERCHE}
        self.assertFalse(
            registrate & _DEBITO_RICERCA_A_MANO,
            "lista registrata e ancora in debito: toglierla da `_DEBITO_RICERCA_A_MANO`",
        )
        stantie = _DEBITO_RICERCA_A_MANO - _liste_ricercabili()
        self.assertFalse(stantie, f"debito su liste senza colonne ricercabili: {sorted(stantie)}")
        for codice, extra in _DIVERGENZE_NOTE.items():
            with self.subTest(lista=codice):
                chiuse = extra & _ricercabili(codice)
                self.assertFalse(
                    chiuse,
                    f"{codice}: {sorted(chiuse)} ora e' ricercabile a catalogo, "
                    f"toglierla da `_DIVERGENZE_NOTE`",
                )

    def test_bb_costruisce_la_condizione(self):
        conditions: list[str] = []
        params: list = []
        add_ricerca_full_condition(conditions, params, "  50%_x  ", colonne=("numero", "ba_codice"))
        self.assertEqual(conditions, ["(v.numero::text ILIKE %s OR v.ba_codice::text ILIKE %s)"])
        self.assertEqual(params, ["%50\\%\\_x%", "%50\\%\\_x%"])

        # Sotto soglia, vuoto o None: nessun filtro.
        for termine in (None, "", "   ", "ab"):
            conditions, params = [], []
            add_ricerca_full_condition(conditions, params, termine, colonne=("numero",))
            self.assertEqual((conditions, params), ([], []), termine)

        # Soglia abbassata dal chiamante; alias diverso.
        conditions, params = [], []
        add_ricerca_full_condition(conditions, params, "F", colonne=("codice",), alias="t", min_caratteri=1)
        self.assertEqual(conditions, ["(t.codice::text ILIKE %s)"])

        with self.assertRaises(ValueError):
            add_ricerca_full_condition([], [], "abc", colonne=("v.numero",))
        with self.assertRaises(ValueError):
            add_ricerca_full_condition([], [], "abc", colonne=())
        # La dichiarazione si controlla anche senza termine: un nome sbagliato
        # non deve aspettare il primo operatore che cerca.
        with self.assertRaises(ValueError):
            add_ricerca_full_condition([], [], None, colonne=("v.numero",))
