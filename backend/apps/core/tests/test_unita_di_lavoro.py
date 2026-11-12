# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il registro degli endpoint A_PASSI (`UnitaDiLavoro`, BE-2 di
#        brief-be-verifica-documentazione-api §I.7.2). Analisi statica: ogni
#        `handle_post_json(..., unita_di_lavoro=UnitaDiLavoro.A_PASSI)` deve
#        stare in una view del registro, e ogni view del registro deve
#        dichiararlo.
# Note: ⭐ A cricchetto nei due versi. Una view a passi che PERDE la
#       dichiarazione torna ATOMICA: in modalita' forte finirebbe in un
#       `atomic` solo, perdendo i commit intermedi e la scrittura dell'errore
#       fuori dallo step. Una view che la ACQUISTA spegne la ripresa delle sue
#       key orfane: deve essere una scelta scritta qui, col motivo nel
#       commento della view.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) RegistroAPassiTests.test_le_view_a_passi_sono_quelle_del_registro
"""
from __future__ import annotations

import ast
from unittest import TestCase

from apps.core.tests._repo import repo_root

_APPS = repo_root() / "backend/apps"

# (file relativo ad apps/, classe della view). Il PERCHE' lavora a passi non
# sta qui: sta nel commento `⭐ A_PASSI` accanto alla chiamata, una sede sola
# (una frase ricopiata qui divergerebbe dalla sua al primo ritocco).
REGISTRO_A_PASSI: frozenset[tuple[str, str]] = frozenset({
    ("vendite/api/views.py", "ApiRunLottoPipeline"),
    ("vendite/api/views.py", "ApiRunLottoPipelineUntilDone"),
    ("vendite/api/views.py", "ApiFatturazioneNumeraLotto"),
    ("vendite/api/views.py", "ApiRunCommessePush"),
})


# Scopo: True se la chiamata e' `handle_post_json(..., unita_di_lavoro=<x>.A_PASSI)`.
def _dichiara_a_passi(call: ast.Call) -> bool:
    nome = call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", None)
    if nome != "handle_post_json":
        return False
    return any(
        kw.arg == "unita_di_lavoro"
        and isinstance(kw.value, ast.Attribute)
        and kw.value.attr == "A_PASSI"
        for kw in call.keywords
    )


def _view_a_passi() -> set[tuple[str, str]]:
    trovate: set[tuple[str, str]] = set()
    for path in _APPS.rglob("*.py"):
        if "tests" in path.parts:
            continue
        sorgente = path.read_text(encoding="utf-8")
        if "A_PASSI" not in sorgente:
            continue
        for classe in ast.walk(ast.parse(sorgente)):
            if not isinstance(classe, ast.ClassDef):
                continue
            if any(isinstance(n, ast.Call) and _dichiara_a_passi(n) for n in ast.walk(classe)):
                trovate.add((path.relative_to(_APPS).as_posix(), classe.name))
    return trovate


class RegistroAPassiTests(TestCase):
    def test_le_view_a_passi_sono_quelle_del_registro(self) -> None:
        trovate = _view_a_passi()
        nuove = trovate - REGISTRO_A_PASSI
        perse = REGISTRO_A_PASSI - trovate
        self.assertFalse(
            nuove,
            f"View A_PASSI fuori registro (aggiungile a REGISTRO_A_PASSI, col motivo nel "
            f"commento della view): {sorted(nuove)}",
        )
        self.assertFalse(
            perse,
            f"View del registro che non dichiarano piu' A_PASSI: {sorted(perse)}",
        )
