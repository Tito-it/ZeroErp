# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test del BB `unisci_sintesi_lineage` (cursor finto, no DB) e
#        presidio del drawer «Passaggi» (`get_lineage_nodo`), dopo il ritiro di
#        `vendite.vw_documento_lineage` (brief-db-lineage-seminata-per-chiave B1).
#        Che le sette liste chiamino il BB col loro tipo lo presidia il
#        registro delle liste documento, `services/test_lineage_liste_be.py`
#        (test 5 e 6): un secondo elenco delle sette liste qui divergerebbe.
# ------------------------------------------------------------
"""
Indice test eseguiti:
— il BB —
1) test_righe_vuote_nessuna_query
2) test_colonne_del_grafo_unite_per_chiave_id
3) test_chiave_uid_per_preventivi_e_offerte
4) test_la_chiave_del_nodo_non_entra_nella_riga
5) test_la_colonna_della_vista_vince_sulla_sintesi
6) test_riga_senza_sintesi_ha_le_colonne_a_null
7) test_export_a_blocchi_di_500
8) test_sorgente_non_configurata_solleva
— il drawer —
9) test_il_drawer_legge_la_sintesi_e_non_la_vista_ritirata
"""

import inspect
from typing import Any
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.tests._repo import sorgente_senza_commenti
from apps.config.db.sorgenti_repository import SorgentiRepository
from apps.vendite.db import _lineage_sintesi
from apps.vendite.db._lineage_sintesi import BLOCCO_SINTESI, unisci_sintesi_lineage
from apps.vendite.db.vendite_repository import VenditeRepository

# Le colonne della sintesi che il test usa (un sottoinsieme basta: il BB non
# ne nomina nessuna, e il test lo verifica proprio non elencandole tutte).
_COLONNE = (
    "tipo_id", "uid", "codice", "fase", "frontiera_codice",
    "frontiera_tipo_codice_interno", "is_transitato", "n_discendenti_attivi",
)

_SORGENTE_ORDINE = {"id": 6, "codice": "ORDINE_VENDITA", "key_selector": "id", "target_table": "vendite.ordini"}
_SORGENTE_PREVENTIVO = {"id": 2, "codice": "PREVENTIVO", "key_selector": "uid", "target_table": "vendite.preventivi"}


class _Colonna:
    def __init__(self, nome: str) -> None:
        self.name = nome


# Cursor finto: per ogni chiamata restituisce un nodo di sintesi per ogni
# chiave del blocco, tranne quelle in `assenti` (il nodo che la sintesi non dà).
class _CursorFinto:
    def __init__(self, assenti: frozenset[str] = frozenset()) -> None:
        self.chiamate: list[list[Any]] = []
        self.assenti = assenti
        self.description = [_Colonna(c) for c in _COLONNE]
        self._righe: list[tuple[Any, ...]] = []

    def __enter__(self) -> "_CursorFinto":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, sql: str, params: list[Any]) -> None:
        assert "fn_documento_lineage_sintesi" in sql
        tipi, uids = params
        self.chiamate.append(params)
        self._righe = [
            (t, u, f"SINT-{u}", "SINTESI", f"FRONT-{u}", "DDT_VENDITA", True, 1)
            for t, u in zip(tipi, uids, strict=True)
            if u not in self.assenti
        ]

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._righe


class _Connessione:
    def __init__(self, cursor: _CursorFinto) -> None:
        self._cursor = cursor

    def cursor(self) -> _CursorFinto:
        return self._cursor


def _unisci(righe: list[dict[str, Any]], sorgente: dict[str, Any], cursor: _CursorFinto,
            tipo: str = "ORDINE_VENDITA") -> list[dict[str, Any]]:
    with patch.object(SorgentiRepository, "get_sorgente_attiva", return_value=sorgente), \
         patch.object(_lineage_sintesi, "connection", _Connessione(cursor)):
        unisci_sintesi_lineage(righe, tipo_codice_interno=tipo)
    return righe


class UnisciSintesiLineageTests(SimpleTestCase):
    """Il BB che porta le colonne del grafo nelle righe delle liste."""

    # Scopo: pagina vuota = nessuna chiamata, nemmeno la sorgente.
    def test_righe_vuote_nessuna_query(self) -> None:
        with patch.object(SorgentiRepository, "get_sorgente_attiva") as sorgente:
            unisci_sintesi_lineage([], tipo_codice_interno="ORDINE_VENDITA")
        sorgente.assert_not_called()

    # Scopo: chiave `id` (ordini, contratti, DDT, resi, fatture): il tipo e la
    # chiave resa a testo vanno alla sintesi, e le colonne del grafo tornano
    # nella riga giusta, nello stesso ordine.
    def test_colonne_del_grafo_unite_per_chiave_id(self) -> None:
        cursor = _CursorFinto()
        righe = _unisci([{"id": 11, "codice": "ORD11"}, {"id": 12, "codice": "ORD12"}],
                        _SORGENTE_ORDINE, cursor)
        self.assertEqual(cursor.chiamate, [[[6, 6], ["11", "12"]]])
        self.assertEqual([r["frontiera_codice"] for r in righe], ["FRONT-11", "FRONT-12"])
        self.assertEqual(righe[0]["frontiera_tipo_codice_interno"], "DDT_VENDITA")
        self.assertIs(righe[0]["is_transitato"], True)
        self.assertEqual(righe[1]["n_discendenti_attivi"], 1)

    # Scopo: chiave `uid` (preventivi e offerte): la chiave e' il campo `uid`
    # della riga, non l'`id` — lo dice `config.sorgenti.key_selector`.
    def test_chiave_uid_per_preventivi_e_offerte(self) -> None:
        cursor = _CursorFinto()
        righe = _unisci([{"id": 5, "uid": "aaa-bbb"}], _SORGENTE_PREVENTIVO, cursor, "PREVENTIVO")
        self.assertEqual(cursor.chiamate, [[[2], ["aaa-bbb"]]])
        self.assertEqual(righe[0]["frontiera_codice"], "FRONT-aaa-bbb")

    # Scopo: `(tipo_id, uid)` e' la chiave del nodo, non un dato: su un ordine
    # `uid` sarebbe l'id reso a testo, e scriverlo nella riga mentirebbe.
    def test_la_chiave_del_nodo_non_entra_nella_riga(self) -> None:
        righe = _unisci([{"id": 11}], _SORGENTE_ORDINE, _CursorFinto())
        self.assertNotIn("tipo_id", righe[0])
        self.assertNotIn("uid", righe[0])

    # Scopo: regola D-B2 — dalla sintesi viene solo cio' che la vista non ha.
    # `codice` e `fase` sono della vista e restano i suoi.
    def test_la_colonna_della_vista_vince_sulla_sintesi(self) -> None:
        righe = _unisci([{"id": 11, "codice": "ORD11", "fase": "VISTA"}],
                        _SORGENTE_ORDINE, _CursorFinto())
        self.assertEqual(righe[0]["codice"], "ORD11")
        self.assertEqual(righe[0]["fase"], "VISTA")

    # Scopo: una riga che la sintesi non restituisce ha comunque tutte le
    # colonne, a NULL: la forma della riga non dipende dal contenuto, e il chip
    # e l'export leggono chiavi che ci sono sempre.
    def test_riga_senza_sintesi_ha_le_colonne_a_null(self) -> None:
        righe = _unisci([{"id": 11}, {"id": 12}], _SORGENTE_ORDINE,
                        _CursorFinto(assenti=frozenset({"12"})))
        self.assertEqual(righe[0]["frontiera_codice"], "FRONT-11")
        for colonna in ("frontiera_codice", "is_transitato", "n_discendenti_attivi"):
            self.assertIn(colonna, righe[1])
            self.assertIsNone(righe[1][colonna])

    # Scopo: l'export (D-B3) chiede la sintesi per TUTTE le righe, a blocchi
    # di `BLOCCO_SINTESI`, e ogni riga riceve la sua.
    def test_export_a_blocchi_di_500(self) -> None:
        n = 2 * BLOCCO_SINTESI + 1
        cursor = _CursorFinto()
        righe = _unisci([{"id": i} for i in range(1, n + 1)], _SORGENTE_ORDINE, cursor)
        self.assertEqual([len(c[1]) for c in cursor.chiamate], [BLOCCO_SINTESI, BLOCCO_SINTESI, 1])
        self.assertEqual(righe[-1]["frontiera_codice"], f"FRONT-{n}")
        self.assertTrue(all(r["frontiera_codice"] == f"FRONT-{r['id']}" for r in righe))

    # Scopo: un tipo senza sorgente e' un seed incoerente, cioe' un errore di
    # programmazione: si solleva, non si esce con le colonne vuote.
    def test_sorgente_non_configurata_solleva(self) -> None:
        with self.assertRaises(ValueError):
            _unisci([{"id": 1}], None, _CursorFinto(), "INESISTENTE")  # type: ignore[arg-type]


class DrawerSintesiLineageTests(SimpleTestCase):
    """Il drawer «Passaggi» legge la sintesi."""

    # Scopo: il drawer «Passaggi» legge la riga summary dalla sintesi seminata
    # sul documento. La vista `vw_documento_lineage` e' ritirata (20261011-98):
    # leggerla e' un errore SQL a ogni apertura.
    def test_il_drawer_legge_la_sintesi_e_non_la_vista_ritirata(self) -> None:
        sql = sorgente_senza_commenti(inspect.getsource(VenditeRepository.get_lineage_nodo))
        self.assertIn("vendite.fn_documento_lineage_sintesi(", sql)
        self.assertNotRegex(sql, r"vendite\.vw_documento_lineage\b(?!_)")
