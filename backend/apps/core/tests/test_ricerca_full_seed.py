# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio del contratto fra il catalogo liste (`ui.lista_colonna`,
#        flag `ricercabile_full`) e le dichiarazioni `RicercaFull` con cui i
#        repository dicono cosa SANNO cercare. Test senza DB: legge i CSV di
#        seed e le costanti del codice (la lettura del catalogo a runtime e'
#        mockata), quindi gira in CI. Il gemello sul DB vero e'
#        `apps/core/tests/db/test_ricerca_full_db`.
# ------------------------------------------------------------
"""Indice test:

1. test_la_dichiarazione_copre_il_seed
   Per ogni lista registrata in `_RICERCHE`, ogni colonna `ricercabile_full = t`
   attiva del seed e' una colonna che la dichiarazione sa cercare (⊇). Se ne
   manca una, il catalogo la accende e il BB la ignora: e' il difetto di
   Preventivi e Offerte del 2026-09-23 (codice BA e id fiscale), spostato di un
   posto. Una colonna IN PIU' nella dichiarazione non e' un errore: e' una
   capacita' che il catalogo puo' accendere.

2. test_la_dichiarazione_nomina_la_sua_lista
   La `RicercaFull` registrata per la lista X porta `lista_codice = X`. Un
   codice sbagliato leggerebbe a runtime le colonne di un'altra lista: la
   ricerca girerebbe, sulle colonne sbagliate, senza nessun errore.

3. test_ogni_lista_ricercabile_e_registrata_o_in_debito
   Ogni lista del seed con almeno una colonna `ricercabile_full = t` sta in
   `_RICERCHE` oppure nel registro di debito `_DEBITO_RICERCA_A_MANO`. Una lista
   nuova che non passa dal BB fa rosso qui, invece di nascere con la sua copia.

4. test_il_debito_non_cresce
   `_DEBITO_RICERCA_A_MANO` puo' solo calare: una lista convertita va tolta, e
   una voce che nomina una lista senza colonne ricercabili e' rimasta senza
   motivo.

5. test_bb_*
   Il comportamento del BB, con la lettura del catalogo mockata:
   intersezione, colonne accese ma non dichiarate (warning), nessuna colonna
   (`FALSE`), soglia (senza leggere il catalogo), escape, mappa, alias
   invalido (esplode anche a lista aperta senza ricerca).

6. test_dichiarazione_invalida_esplode_alla_costruzione
   Un nome sbagliato esce quando il modulo si importa, non al primo operatore
   che cerca. Compresa la stringa scambiata per tupla (`("numero")`).

7. test_dichiarazione_congelata_sulla_copia
   Validata alla costruzione, la dichiarazione non cambia dopo: ne' da chi
   modifica la mappa passata, ne' scrivendoci dentro.
"""

import importlib
import unittest
from unittest.mock import patch

from apps.core.db._helpers import RicercaFull, add_ricerca_full_condition
from apps.core.tests.test_liste_configurabili_seed import (
    _colonne_attive,
    _seed,
)

_LETTURA = "apps.core.db._helpers._colonne_ricerca_accese"


# Scopo: la dichiarazione di una lista, letta dal simbolo che il repository
#        PASSA al BB (non da uno che gli somiglia per nome).
def _da_costante(modulo: str, costante: str):
    def risolvi() -> RicercaFull:
        return getattr(importlib.import_module(modulo), costante)

    return risolvi


# Scopo: le due code resi hanno la dichiarazione dentro `_CODA_META`, per vista.
def _da_coda_resi(vista: str):
    def risolvi() -> RicercaFull:
        from apps.vendite.db import resi_repository as m

        return m._CODA_META[vista]["ricerca"]

    return risolvi


_V = "apps.vendite.db."

# Registro delle liste la cui ricerca libera passa dal BB:
# `codice lista` -> risolutore della `RicercaFull` passata ad `add_ricerca_full_condition`.
# ⚠️ Chi converte una lista del debito la AGGIUNGE qui e la TOGLIE dal debito.
_RICERCHE: tuple[tuple[str, object], ...] = (
    ("vendite.preventivi", _da_costante(_V + "preventivi_repository", "_RICERCA_PREVENTIVI")),
    ("vendite.offerte", _da_costante(_V + "offerte_repository", "_RICERCA_OFFERTE")),
    ("vendite.ordini", _da_costante(_V + "ordini_repository", "_RICERCA_ORDINI")),
    ("vendite.ddt", _da_costante(_V + "ddt_repository", "_RICERCA_DDT")),
    ("vendite.fatture", _da_costante(_V + "fatture_repository", "_RICERCA_FATTURE")),
    ("vendite.contratti", _da_costante(_V + "contratti_repository", "_RICERCA_CONTRATTI")),
    ("vendite.resi", _da_costante(_V + "resi_repository", "_RICERCA_RESI")),
    ("vendite.resi_da_accreditare", _da_coda_resi("vendite.vw_resi_da_accreditare")),
    ("vendite.resi_da_riconsegnare", _da_coda_resi("vendite.vw_resi_da_riconsegnare")),
    ("vendite.famiglie_documento", _da_costante(_V + "famiglie_repository", "_RICERCA")),
)

# Liste con colonne `ricercabile_full = t` la cui ricerca e' ancora scritta a
# mano (o assente) e non passa dal BB. Fotografia del 2026-09-23: PUO' SOLO
# CALARE (test 4). Il piano per svuotarlo:
# docs/it/dev/work-in-progress/brief-be-ricerca-full-liste-residue.md
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


# Scopo: chiama il BB con la lettura del catalogo sostituita da `accese`.
def _condizione(termine, ricerca, accese, **kwargs):
    conditions: list[str] = []
    params: list = []
    with patch(_LETTURA, return_value=list(accese)) as lettura:
        add_ricerca_full_condition(conditions, params, termine, ricerca, **kwargs)
    return conditions, params, lettura


class RicercaFullSeedTests(unittest.TestCase):
    def test_la_dichiarazione_copre_il_seed(self):
        for codice, risolvi in _RICERCHE:
            with self.subTest(lista=codice):
                dichiarate = set(risolvi().colonne)
                mancanti = _ricercabili(codice) - dichiarate
                self.assertFalse(
                    mancanti,
                    f"{codice}: il catalogo accende {sorted(mancanti)} ma la "
                    f"dichiarazione `RicercaFull` non le sa cercare",
                )

    def test_la_dichiarazione_nomina_la_sua_lista(self):
        for codice, risolvi in _RICERCHE:
            with self.subTest(lista=codice):
                self.assertEqual(risolvi().lista_codice, codice)

    def test_ogni_lista_ricercabile_e_registrata_o_in_debito(self):
        registrate = {c for c, _ in _RICERCHE}
        scoperte = _liste_ricercabili() - registrate - _DEBITO_RICERCA_A_MANO
        self.assertFalse(
            scoperte,
            f"liste con colonne `ricercabile_full` senza BB e fuori dal debito: "
            f"{sorted(scoperte)} — dichiarare una `RicercaFull`, cercare con "
            f"`add_ricerca_full_condition` e registrarle in `_RICERCHE`",
        )

    def test_il_debito_non_cresce(self):
        registrate = {c for c, _ in _RICERCHE}
        self.assertFalse(
            registrate & _DEBITO_RICERCA_A_MANO,
            "lista registrata e ancora in debito: toglierla da `_DEBITO_RICERCA_A_MANO`",
        )
        stantie = _DEBITO_RICERCA_A_MANO - _liste_ricercabili()
        self.assertFalse(stantie, f"debito su liste senza colonne ricercabili: {sorted(stantie)}")

    # --- Il BB --------------------------------------------------------------

    def test_bb_cerca_sull_intersezione_nell_ordine_della_dichiarazione(self):
        ricerca = RicercaFull("x.lista", ("numero", "ba_codice", "descrizione"))
        conditions, params, lettura = _condizione(
            "  50%_x  ", ricerca, ["descrizione", "numero"],
        )
        lettura.assert_called_once_with("x.lista")
        self.assertEqual(
            conditions, ["((v.numero)::text ILIKE %s OR (v.descrizione)::text ILIKE %s)"],
        )
        self.assertEqual(params, ["%50\\%\\_x%", "%50\\%\\_x%"])

    def test_bb_mappa_usa_le_espressioni_dichiarate(self):
        ricerca = RicercaFull("x.lista", {"ba_codice": "ba.codice", "fase": "COALESCE(p.a, p.b)"})
        conditions, _, _ = _condizione("abc", ricerca, ["ba_codice", "fase"], alias="ignorato")
        self.assertEqual(
            conditions, ["((ba.codice)::text ILIKE %s OR (COALESCE(p.a, p.b))::text ILIKE %s)"],
        )

    def test_bb_colonna_accesa_non_dichiarata_ignorata_con_warning(self):
        ricerca = RicercaFull("x.lista", ("numero",))
        with self.assertLogs("apps.core.db._helpers", level="WARNING") as log:
            conditions, params, _ = _condizione("abc", ricerca, ["numero", "segreta"])
        self.assertEqual(conditions, ["((v.numero)::text ILIKE %s)"])
        self.assertEqual(len(params), 1)
        self.assertIn("segreta", log.output[0])

    def test_bb_nessuna_colonna_accesa_non_trova_niente(self):
        ricerca = RicercaFull("x.lista", ("numero",))
        conditions, params, _ = _condizione("abc", ricerca, [])
        self.assertEqual((conditions, params), (["FALSE"], []))

    def test_bb_sotto_soglia_non_filtra_e_non_legge_il_catalogo(self):
        ricerca = RicercaFull("x.lista", ("numero",))
        for termine in (None, "", "   ", "ab"):
            with self.subTest(termine=termine):
                conditions, params, lettura = _condizione(termine, ricerca, ["numero"])
                self.assertEqual((conditions, params), ([], []))
                lettura.assert_not_called()
        conditions, _, _ = _condizione("F", ricerca, ["numero"], alias="t", min_caratteri=1)
        self.assertEqual(conditions, ["((t.numero)::text ILIKE %s)"])

    def test_bb_alias_invalido_esplode_anche_senza_termine(self):
        ricerca = RicercaFull("x.lista", ("numero",))
        for termine in (None, "abc"):
            with self.subTest(termine=termine), self.assertRaises(ValueError):
                _condizione(termine, ricerca, ["numero"], alias="v; DROP")

    def test_dichiarazione_congelata_sulla_copia(self):
        mappa = {"ba_codice": "ba.codice"}
        ricerca = RicercaFull("x.lista", mappa)
        mappa["intrusa"] = "1; --"
        self.assertEqual(set(ricerca.colonne), {"ba_codice"})
        with self.assertRaises(TypeError):
            ricerca.colonne["altra"] = "x"  # type: ignore[index]

    def test_dichiarazione_invalida_esplode_alla_costruzione(self):
        for kwargs in (
            {"lista_codice": "x.lista", "colonne": ("v.numero",)},
            {"lista_codice": "x.lista", "colonne": ()},
            {"lista_codice": "", "colonne": ("numero",)},
            {"lista_codice": "x.lista", "colonne": {"numero": "  "}},
            {"lista_codice": "x.lista", "colonne": {"Numero": "v.numero"}},
            # `("numero")` senza virgola e' una stringa: sei colonne di una lettera.
            {"lista_codice": "x.lista", "colonne": "numero"},
        ):
            with self.subTest(**{k: repr(v) for k, v in kwargs.items()}):
                with self.assertRaises(ValueError):
                    RicercaFull(**kwargs)
