# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio di `scripts/gen_indice_bb.py`, il generatore dell'indice dei
#        building block che una sessione BE/FE legge per intero (CLAUDE.md).
#        Un indice sbagliato non da' errore: nasconde un building block, o ne
#        inventa uno. Test senza DB (unittest.TestCase): il catalogo di prova
#        se lo costruiscono in una cartella temporanea.
# ------------------------------------------------------------
import importlib.util
import tempfile
import unittest
from pathlib import Path

from apps.core.tests._repo import repo_root


def _generatore():
    # Scopo: caricare lo script dalla sua sede, senza ricopiarne la logica.
    sorgente = repo_root() / "scripts" / "gen_indice_bb.py"
    spec = importlib.util.spec_from_file_location("_gen_indice_bb", sorgente)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossibile caricare {sorgente}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _indice_di(testo: str) -> str:
    # Scopo: l'indice che il generatore produce per un catalogo dato come testo.
    with tempfile.TemporaryDirectory() as cartella:
        catalogo = Path(cartella) / "catalogo-di-prova.md"
        catalogo.write_text(testo, encoding="utf-8")
        return _generatore().costruisci_indice(catalogo)


_CATALOGO = """# Catalogo di prova

## Sezione uno

| Building Block | File | Descrizione |
| --- | --- | --- |
| `primo_bb` | [a.py](a.py) | **Fa** la prima cosa |

Esempio d'uso:

```bash
# x
## non e' un titolo
| a | b |
| finta_voce | un file | una descrizione |
```

| Building Block | File | Descrizione |
| --- | --- | --- |
| `secondo_bb` | [b.py](b.py) | Fa la seconda cosa |
"""


class IndiceBuildingBlockTests(unittest.TestCase):
    def test_una_voce_per_riga_di_tabella_col_numero_di_riga(self):
        indice = _indice_di(_CATALOGO)
        self.assertIn("- L7 `primo_bb` — Fa la prima cosa", indice)
        self.assertIn("- L20 `secondo_bb` — Fa la seconda cosa", indice)
        self.assertIn("<!-- voci: 2 -->", indice)

    def test_il_blocco_di_codice_recintato_non_e_catalogo(self):
        indice = _indice_di(_CATALOGO)
        # Ne' titolo ne' voce da cio' che sta fra i recinti.
        self.assertNotIn("non e' un titolo", indice)
        self.assertNotIn("finta_voce", indice)
        self.assertNotIn("| a | b |", indice)

    def test_la_tabella_dopo_il_recinto_riparte_dall_intestazione(self):
        # Dopo un recinto la prima riga `|` e' di nuovo un'intestazione: se il
        # generatore la credesse una voce, «Building Block» finirebbe in indice.
        indice = _indice_di(_CATALOGO)
        self.assertNotIn("Building Block —", indice)
