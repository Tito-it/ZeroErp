# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio della forma unica dell'envelope di una lista (D-1 di
#        brief-be-fe-BB-audit, Tid 2026-11-24): una pagina e' `{count,
#        results}` e la costruisce SOLO il BB `pagina_con_totale` (o
#        `collezione_completa`, per una collezione consegnata per intero).
#        Fino a quel giorno le forme erano tre, e quella corta era scritta a
#        mano in una dozzina di punti di sei domini.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_nessun_letterale_count_results_fuori_dal_bb — un dizionario con le
   chiavi "count" e "results" fuori da `list_helpers` e' una copia del BB,
   salvo le eccezioni dichiarate (ognuna col suo motivo)
2) test_nessuna_chiave_della_forma_lunga — "page_size" e "total_pages" non
   escono piu' da nessuna risposta, senza eccezioni
3) test_le_eccezioni_esistono_ancora — un'eccezione il cui file non ha piu' il
   letterale si toglie dall'elenco (altrimenti copre la copia successiva)
4) test_bb_forma — `pagina_con_totale` conta il totale della query, non le righe
"""

from __future__ import annotations

import ast
from pathlib import Path

from django.test import SimpleTestCase

from apps.core.services.list_helpers import collezione_completa, pagina_con_totale
from apps.core.tests._repo import repo_root

# ⭐ La sede del BB: l'unico file dove il letterale e' la regola.
_SEDE = "backend/apps/core/services/list_helpers.py"

# Le nature DIVERSE da una pagina, che portano le stesse due chiavi per un
# motivo loro. ⛔ Un'eccezione si aggiunge col motivo, mai per far passare il
# test: «e' una lista paginata» non e' un motivo, e' il caso del BB.
_ECCEZIONI: dict[str, str] = {
    # Collezioni intere col conteggio di CONTROLLO da una query sua: il `count`
    # non impagina, dichiara quante righe esistono perche' il client verifichi
    # di averle tutte (`troncamentoSospetto` di `<ListaConfigurabile>` in
    # modalita' `paginata: false`).
    "backend/apps/ui/services/lista_colonna_admin_service.py": "conteggio di controllo",
    "backend/apps/ui/services/lista_colonna_permesso_admin_service.py": "conteggio di controllo",
    "backend/apps/ui/services/lista_preset_admin_service.py": "conteggio di controllo",
    "backend/apps/ui/services/lista_definizione_admin_service.py": "conteggio di controllo",
    # Lookup con un tetto: `count` accanto a `troncato` (BB `fetch_con_sonda`),
    # e il tool AI che ne riporta la stessa forma.
    "backend/apps/catalogo/services/catalogo_service.py": "lookup con troncato",
    "backend/apps/ai_assistant/tools/catalogo_tools.py": "lookup con troncato",
}


# Scopo: I file Python applicativi del backend (fuori dai test e dalle
#        migrazioni), con il percorso relativo alla radice del repo.
def _sorgenti() -> list[tuple[str, Path]]:
    radice = repo_root()
    apps = radice / "backend" / "apps"
    file = [
        (str(p.relative_to(radice)), p)
        for p in sorted(apps.rglob("*.py"))
        if "/tests/" not in str(p) and "/migrations/" not in str(p)
    ]
    # ⛔ Mai a vuoto: se la radice si sposta, zero file farebbero passare tutto.
    assert len(file) > 100, f"trovati solo {len(file)} file sotto {apps}"
    return file


# Scopo: Vero se il valore e' la DESCRIZIONE di un campo nello schema OpenAPI
#        (`serializers.IntegerField()`, `inline_serializer(...)`, un dict JSON
#        Schema): quei dizionari dichiarano la forma, non la costruiscono.
def _e_schema(valore: ast.expr) -> bool:
    if isinstance(valore, ast.Dict):
        return True
    if isinstance(valore, ast.Call):
        f = valore.func
        nome = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        return nome.endswith(("Field", "Serializer", "serializer"))
    return False


# Scopo: Le chiavi stringa costanti di ogni dizionario letterale del file che
#        COSTRUISCE dati (gli schemi OpenAPI sono esclusi).
def _chiavi_dei_dizionari(percorso: Path) -> list[tuple[int, set[str]]]:
    albero = ast.parse(percorso.read_text(), filename=str(percorso))
    esito = []
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.Dict):
            continue
        coppie = [
            (k.value, v) for k, v in zip(nodo.keys, nodo.values, strict=True)
            if isinstance(k, ast.Constant) and isinstance(k.value, str)
        ]
        if any(_e_schema(v) for _, v in coppie):
            continue
        esito.append((nodo.lineno, {k for k, _ in coppie}))
    return esito


class EnvelopeListaFormaUnicaTests(SimpleTestCase):

    def test_nessun_letterale_count_results_fuori_dal_bb(self) -> None:
        copie = [
            f"{rel}:{riga}"
            for rel, p in _sorgenti()
            if rel != _SEDE and rel not in _ECCEZIONI
            for riga, chiavi in _chiavi_dei_dizionari(p)
            if {"count", "results"} <= chiavi
        ]
        self.assertEqual(
            copie, [],
            "Envelope di lista scritto a mano: si usa `pagina_con_totale` (o "
            "`collezione_completa`) di apps.core.services.list_helpers.",
        )

    def test_nessuna_chiave_della_forma_lunga(self) -> None:
        trovate = [
            f"{rel}:{riga}"
            for rel, p in _sorgenti()
            for riga, chiavi in _chiavi_dei_dizionari(p)
            if chiavi & {"page_size", "total_pages"}
        ]
        self.assertEqual(trovate, [], "La forma lunga dell'envelope e' ritirata (D-1, 2026-11-24).")

    def test_le_eccezioni_esistono_ancora(self) -> None:
        radice = repo_root()
        for rel in _ECCEZIONI:
            with self.subTest(file=rel):
                p = radice / rel
                self.assertTrue(p.exists(), f"{rel} non esiste piu': si toglie dalle eccezioni")
                self.assertTrue(
                    any({"count", "results"} <= c for _, c in _chiavi_dei_dizionari(p)),
                    f"{rel} non scrive piu' il letterale: si toglie dalle eccezioni",
                )

    def test_bb_forma(self) -> None:
        self.assertEqual(pagina_con_totale([{"id": 1}], 42), {"count": 42, "results": [{"id": 1}]})
        self.assertEqual(pagina_con_totale([], 0), {"count": 0, "results": []})
        self.assertEqual(collezione_completa([{"id": 1}, {"id": 2}])["count"], 2)
