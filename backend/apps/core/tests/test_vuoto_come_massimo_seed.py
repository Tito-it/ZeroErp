# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio di «dove va il vuoto quando una lista ordina»
#        (brief-db-lista-colonna-vuoto-in-ordine, §5.4; decisioni di Tid del
#        2026-11-24): l'eccezione «vuoto come il massimo» si DICHIARA nel
#        catalogo (`ui.lista_colonna.vuoto_ordinato_come_massimo`) e la applica
#        il BB dell'ordinamento. Una colonna dichiarata che il backend ordina
#        senza la dichiarazione e' rossa; un'eccezione scritta a mano in una
#        whitelist anche.
# Note: ⭐ Senza DB: legge il seed CSV, le rotte dell'URLconf e i sorgenti. La
#       catena sul DB vero e' in `core/tests/db/test_vuoto_come_massimo_db.py`.
#       ⚠️ Il seed e' cio' che il software dichiara; una colonna creata
#       dall'installazione col flag (dal drawer non si puo', D-1) la vede il
#       presidio del DB su `valido_al` (D-2), non questo.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_ogni_lista_che_dichiara_e_servita_da_una_view_con_lista_codice
   La dichiarazione arriva al BB SOLO dalla base view, che conosce la lista:
   una lista dichiarata senza una view con quel `lista_codice` ordinerebbe il
   vuoto come il minimo, senza errore.
2) test_nessuna_whitelist_scrive_il_vuoto_come_massimo_a_mano
   Niente `COALESCE(col, <sentinella>)` nelle whitelist: era l'eccezione
   scritta fuori dal catalogo, e le whitelist che se ne dimenticavano
   ordinavano il vuoto al contrario (tre, censite il 2026-11-24).
3) test_la_scansione_vede_le_tre_forme_della_sentinella
   La prova che il 2 non e' verde a vuoto.
4) test_il_debito_della_sentinella_si_chiude_con_la_dichiarazione
   `_DEBITO_SENTINELLA` e' un registro di debito: quando il seed dichiara la
   colonna, la sentinella deve uscire (e la voce con lei).
5) test_nessun_order_by_compone_la_direzione_senza_la_lista
   La direzione di un `ORDER BY` composto a mano passa da
   `sql_order_direction_lista`, che sa quale colonna ordina e ne legge la
   dichiarazione: una chiamata diretta a `sql_order_direction` ordina il vuoto
   come il minimo anche sulla colonna dichiarata, senza errore (cinque punti,
   corretti dalla `/verifica` del 2026-11-24).
6) test_la_scansione_della_direzione_distingue_il_bb_di_lista
   La prova che il 5 non e' verde a vuoto.
"""
from __future__ import annotations

import re
from pathlib import Path

from django.test import SimpleTestCase

from apps.core.api.rotte import classi_view
from apps.core.tests._repo import repo_root, sorgente_senza_commenti
from apps.core.tests._seed_csv import seed_ui

# Una voce di whitelist il cui valore e' un `COALESCE` su una SENTINELLA: la
# data infinita (scritta o dalla costante) o il massimo di `integer`.
_VOCE_CON_SENTINELLA = re.compile(
    r'"(?P<chiave>\w+)"\s*:\s*f?"COALESCE\((?P<argomenti>[^"]*?'
    r"(?:'-?infinity'|_SQL_DATE_INFINITY|_SQL_GIORNI_SENZA_SCADENZA)[^\"]*)\)\"",
)

# ⚠️ REGISTRO DI DEBITO, deve calare (brief-db-lista-colonna-vuoto-in-ordine
#    §8, 2026-11-24): `giorni_alla_scadenza` e' nel catalogo (liste 27 e 112),
#    ma il seed non la dichiara ancora. La richiesta e' al team DB; quando il
#    seed la dichiara, la sentinella esce da `listini_repository.py`.
#    (file relativo a `backend/`, chiave) -> le liste del seed che la portano.
_DEBITO_SENTINELLA: dict[tuple[str, str], tuple[str, ...]] = {
    ("apps/vendite/db/listini_repository.py", "giorni_alla_scadenza"): (
        "vendite.listini", "vendite.listini_versioni",
    ),
}

_BACKEND = Path(__file__).resolve().parents[3]


def _liste_seed() -> dict[str, str]:
    return {r["id"]: r["codice"] for r in seed_ui("lista_definizione.csv") if r["id"]}


# Scopo: le colonne ACCESE e ORDINABILI che il seed dichiara, per lista.
def _dichiarate() -> dict[str, set[str]]:
    liste = _liste_seed()
    dichiarate: dict[str, set[str]] = {}
    for r in seed_ui("lista_colonna.csv"):
        if (
            r["vuoto_ordinato_come_massimo"] == "t"
            and r["ordinabile"] == "t"
            and r["attivo"] == "t"
        ):
            dichiarate.setdefault(liste[r["lista_id"]], set()).add(str(r["campo_sorgente"]))
    return dichiarate


def _voci_con_sentinella(testo: str) -> list[str]:
    return [m.group("chiave") for m in _VOCE_CON_SENTINELLA.finditer(sorgente_senza_commenti(testo))]


# La direzione composta SENZA il BB di lista. `\b...\(` non prende
# `sql_order_direction_lista(`: dopo il nome viene `_`, non `(`.
_DIREZIONE_DIRETTA = re.compile(r"\bsql_order_direction\(")
# L'unica sede ammessa: il BB stesso, che la chiama con `vuoto_massimo`.
_SEDE_DEL_BB = "apps/core/db/_helpers.py"


def _sorgenti() -> list[Path]:
    return [
        p for p in (_BACKEND / "apps").rglob("*.py")
        if "tests" not in p.relative_to(_BACKEND).parts
    ]


class VuotoComeMassimoSeedTests(SimpleTestCase):
    def test_ogni_lista_che_dichiara_e_servita_da_una_view_con_lista_codice(self) -> None:
        dichiarate = _dichiarate()
        # Un seed letto senza la colonna farebbe passare tutto: lo si dice prima.
        self.assertTrue(dichiarate, "nessuna colonna dichiarata nel seed: la lettura non la vede")
        servite = {
            getattr(cls, "lista_codice", None) for cls in classi_view(anche_condizionali=True)
        }
        scoperte = sorted(set(dichiarate) - servite)
        self.assertEqual(
            scoperte, [],
            "liste che dichiarano colonne «vuoto come il massimo» senza una view "
            "con quel `lista_codice`: la dichiarazione non arriva al BB "
            f"dell'ordinamento → {scoperte}",
        )

    def test_nessuna_whitelist_scrive_il_vuoto_come_massimo_a_mano(self) -> None:
        trovate: set[tuple[str, str]] = set()
        for percorso in _sorgenti():
            for chiave in _voci_con_sentinella(percorso.read_text(encoding="utf-8")):
                trovate.add((percorso.relative_to(_BACKEND).as_posix(), chiave))
        fuori_registro = sorted(trovate - set(_DEBITO_SENTINELLA))
        self.assertEqual(
            fuori_registro, [],
            "whitelist con l'eccezione «vuoto come il massimo» scritta a mano: "
            "si dichiara nel catalogo (`ui.lista_colonna.vuoto_ordinato_come_massimo`) "
            f"e la applica il BB dell'ordinamento → {fuori_registro}",
        )
        # Il registro non resta piu' grande del vero.
        stantie = sorted(set(_DEBITO_SENTINELLA) - trovate)
        self.assertEqual(stantie, [], f"voci di `_DEBITO_SENTINELLA` gia' chiuse: toglile → {stantie}")

    def test_la_scansione_vede_le_tre_forme_della_sentinella(self) -> None:
        campione = (
            '    "a": "COALESCE(v.a, \'infinity\'::date)",\n'
            '    "b": "COALESCE(v.b, \'-infinity\'::date)",\n'
            '    "c": f"COALESCE(x.c, {_SQL_DATE_INFINITY})",\n'
            '    "d": f"COALESCE(s.d, {_SQL_GIORNI_SENZA_SCADENZA})",\n'
            '    "e": "COALESCE(v.e, 0)",\n'
            "    # \"f\": \"COALESCE(v.f, 'infinity'::date)\",\n"
        )
        self.assertEqual(_voci_con_sentinella(campione), ["a", "b", "c", "d"])

    def test_il_debito_della_sentinella_si_chiude_con_la_dichiarazione(self) -> None:
        dichiarate = _dichiarate()
        for (file, chiave), liste in _DEBITO_SENTINELLA.items():
            for lista in liste:
                with self.subTest(lista=lista, chiave=chiave):
                    self.assertNotIn(
                        chiave, dichiarate.get(lista, set()),
                        f"il seed dichiara `{lista}.{chiave}`: togli la sentinella da "
                        f"{file} e la voce da `_DEBITO_SENTINELLA`",
                    )
        self.assertTrue((repo_root() / "backend").is_dir())

    def test_nessun_order_by_compone_la_direzione_senza_la_lista(self) -> None:
        fuori: list[str] = []
        for percorso in _sorgenti():
            rel = percorso.relative_to(_BACKEND).as_posix()
            if rel == _SEDE_DEL_BB:
                continue
            testo = sorgente_senza_commenti(percorso.read_text(encoding="utf-8"))
            if _DIREZIONE_DIRETTA.search(testo):
                fuori.append(rel)
        self.assertEqual(
            sorted(fuori), [],
            "`sql_order_direction` chiamata fuori dal BB: la direzione di una "
            "lista passa da `sql_order_direction_lista(order_by, order_dir, "
            "colonne=..., default=..., default_desc=...)`, che legge dove va il "
            f"vuoto dal catalogo → {sorted(fuori)}",
        )

    def test_la_scansione_della_direzione_distingue_il_bb_di_lista(self) -> None:
        self.assertTrue(_DIREZIONE_DIRETTA.search("d = sql_order_direction(order_dir)"))
        self.assertFalse(_DIREZIONE_DIRETTA.search("d = sql_order_direction_lista(k, d, colonne=c)"))
        self.assertFalse(_DIREZIONE_DIRETTA.search("from x import sql_order_direction\n"))
