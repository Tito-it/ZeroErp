# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: PRESIDIO — nei test del backend ogni patch di un REPOSITORY ha
#        `autospec=True`: la classe intera (`patch("…XRepository")`, anche
#        tramite una costante del file, e `patch.object(modulo,
#        "XRepository")`) e il singolo metodo (`patch.object(XRepository,
#        "metodo")` e `patch("…XRepository.metodo")`), con `patch` scritto
#        in qualunque forma (`patch`, `mock.patch`, `unittest.mock.patch`).
# Note: ⛔ Perche'. Un mock libero accetta qualunque metodo e qualunque
#        parametro: il test resta verde il giorno in cui il metodo viene
#        rinominato o tolto, e `assert_not_called()` su un nome inesistente
#        passa a vuoto. Col mock `autospec` il nome sbagliato e' un
#        `AttributeError`, il parametro sbagliato un `TypeError`. Il giro del
#        2026-11-08 (nato dai mock di `PraticheRepository` nel §8.16 di
#        brief-db-sorgente-documento-e-riga, poi esteso a tutta la suite) ha messo
#        `autospec` a 2034 patch e ha scoperto 14 test che verificavano a vuoto
#        (metodi spariti, repository sbagliato): questo presidio impedisce che
#        le patch nuove nascano di nuovo senza. Nello stesso giro la
#        scansione e' stata estesa a `patch("…XRepository.metodo")` e a
#        `unittest.mock.patch`, che prima non vedeva: altre 47 patch, fra cui
#        il mock dei fatti degli obblighi ripatchato sopra quello della base
#        `JwtMockedApiTest` (ora la base espone `mock_fatti_obblighi`).
#        ⚠️ Il mock `autospec` di un METODO registra anche `self`: negli
#        `assert_called_*` il primo argomento e' `mock.ANY`.
#        Esenti, perche' `autospec` li' non si puo' mettere: la patch che passa
#        gia' l'oggetto sostitutivo (`new` posizionale o `new=`, `new_callable=`)
#        e quella che dichiara un altro `spec` / `spec_set`.
#        ⚠️ Una patch di classe con `return_value=<finto>` controlla col solo
#        `autospec` il costruttore: il finto nasce da
#        `create_autospec(XRepository, instance=True)`, non da `MagicMock()`
#        (il presidio non lo vede: e' una regola di chi scrive il test).
#        Scansione col parser di Python (`ast`): vede le chiamate su piu'
#        righe e le costanti del file; un bersaglio composto a runtime gli
#        sfugge. La controprova prova che vede le forme che conosce.
# ------------------------------------------------------------
"""Indice test.

1. test_ogni_patch_di_repository_ha_autospec
2. test_la_scansione_vede_le_forme_vietate (controprova)
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

_SUFFISSO = "Repository"
# Le parole chiave che rendono `autospec` impossibile o superfluo.
_ESENTI = frozenset({"new", "new_callable", "spec", "spec_set"})


def _nome_chiamata(nodo: ast.expr) -> str:
    """`patch`, `mock.patch`, `patch.object`, `mock.patch.object` → nome puntato."""
    if isinstance(nodo, ast.Name):
        return nodo.id
    if isinstance(nodo, ast.Attribute):
        return f"{_nome_chiamata(nodo.value)}.{nodo.attr}"
    return ""


def _testo_finale(nodo: ast.expr) -> str | None:
    """Il testo di una stringa, o la sua coda letterale se e' una f-string."""
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    if isinstance(nodo, ast.JoinedStr) and nodo.values:
        ultimo = nodo.values[-1]
        if isinstance(ultimo, ast.Constant) and isinstance(ultimo.value, str):
            return ultimo.value
    return None


def _e_percorso_repository(testo: str) -> bool:
    """La classe (`…XRepository`) o un suo metodo (`…XRepository.metodo`)."""
    segmenti = testo.split(".")
    return any(seg.endswith(_SUFFISSO) for seg in segmenti[-2:])


def _costanti_repository(albero: ast.AST) -> set[str]:
    """I nomi assegnati, in qualunque punto del file, a un percorso di repository."""
    nomi: set[str] = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Assign):
            bersagli, valore = nodo.targets, nodo.value
        elif isinstance(nodo, ast.AnnAssign) and nodo.value is not None:
            bersagli, valore = [nodo.target], nodo.value
        else:
            continue
        testo = _testo_finale(valore)
        if testo is None or not _e_percorso_repository(testo):
            continue
        for bersaglio in bersagli:
            if isinstance(bersaglio, ast.Name):
                nomi.add(bersaglio.id)
            elif isinstance(bersaglio, ast.Attribute):
                nomi.add(bersaglio.attr)
    return nomi


def _punta_a_repository(nodo: ast.expr, costanti: set[str]) -> bool:
    testo = _testo_finale(nodo)
    if testo is not None:
        return _e_percorso_repository(testo)
    if isinstance(nodo, ast.Name):
        return nodo.id in costanti
    if isinstance(nodo, ast.Attribute):
        return nodo.attr in costanti
    return False


def _ha_autospec_o_e_esente(chiamata: ast.Call) -> bool:
    for kw in chiamata.keywords:
        if kw.arg in _ESENTI:
            return True
        if kw.arg == "autospec":
            return isinstance(kw.value, ast.Constant) and kw.value.value is True
    return False


def patch_senza_autospec(sorgente: str) -> Iterator[tuple[int, str]]:
    """(riga, forma) di ogni patch di repository senza `autospec=True`."""
    albero = ast.parse(sorgente)
    costanti = _costanti_repository(albero)
    for nodo in ast.walk(albero):
        if not isinstance(nodo, ast.Call):
            continue
        # Qualunque prefisso del modulo: `patch`, `mock.patch`,
        # `unittest.mock.patch` (e lo stesso per `.object`).
        nome = _nome_chiamata(nodo.func)
        if nome == "patch" or nome.endswith(".patch"):
            # Il secondo posizionale e' `new`: l'oggetto sostitutivo e' gia' dato.
            if len(nodo.args) != 1 or not _punta_a_repository(nodo.args[0], costanti):
                continue
            forma = "patch(<repository>)"
        elif nome == "patch.object" or nome.endswith(".patch.object"):
            # Il terzo posizionale e' `new`.
            if len(nodo.args) != 2:
                continue
            classe, attributo = nodo.args
            nome_classe = classe.attr if isinstance(classe, ast.Attribute) else (
                classe.id if isinstance(classe, ast.Name) else "")
            testo_attributo = _testo_finale(attributo)
            if nome_classe.endswith(_SUFFISSO):
                forma = f"patch.object({nome_classe}, …)"          # un metodo
            elif testo_attributo is not None and testo_attributo.endswith(_SUFFISSO):
                forma = f"patch.object(<modulo>, {testo_attributo!r})"  # la classe
            else:
                continue
        else:
            continue
        if not _ha_autospec_o_e_esente(nodo):
            yield nodo.lineno, forma


def _file_di_test() -> Iterator[Path]:
    apps = Path(settings.BASE_DIR) / "apps"
    for percorso in sorted(apps.glob("*/tests/**/*.py")):
        yield percorso


class PresidioAutospecRepositoryTests(SimpleTestCase):

    # 1. Il presidio: nessuna patch di repository senza `autospec=True`.
    def test_ogni_patch_di_repository_ha_autospec(self) -> None:
        base = Path(settings.BASE_DIR)
        trovate = [
            f"{percorso.relative_to(base)}:{riga} {forma}"
            for percorso in _file_di_test()
            for riga, forma in patch_senza_autospec(percorso.read_text(encoding="utf-8"))
        ]
        self.assertEqual(
            trovate, [],
            "Patch di repository senza autospec=True (un mock libero accetta "
            "metodi e parametri che il repository non ha; per un metodo, negli "
            "assert il primo argomento e' mock.ANY, cioe' self):\n" + "\n".join(trovate),
        )

    # 2. La controprova: la scansione vede le forme vietate e lascia stare le
    #    ammesse. Senza, il test 1 potrebbe essere verde perche' cieco.
    def test_la_scansione_vede_le_forme_vietate(self) -> None:
        vietate = '''
_REPO = "apps.x.services.y.OrdiniRepository"
_METODO = "apps.x.db.y.OrdiniRepository.get_ordine"
_ALTRO = f"{_MOD}.PraticheRepository"
@patch("apps.x.services.y.OrdiniRepository")
@patch(_REPO)
@patch(_ALTRO, return_value=None)
@patch.object(OrdiniRepository, "get_ordine")
@patch.object(vs.VenditeRepository, "list_x", return_value=[])
@patch.object(pagamenti_service, "PagamentiRepository", return_value=repo)
@patch("apps.x.services.y.OrdiniRepository", autospec=False)
def f(): pass
with mock.patch(
    "apps.x.services.y.OrdiniRepository",
) as cls:
    pass
@patch("apps.x.db.y.OrdiniRepository.get_ordine")
@patch(_METODO, return_value=None)
@unittest.mock.patch("apps.x.services.y.OrdiniRepository")
@unittest.mock.patch.object(OrdiniRepository, "get_ordine")
def g(): pass
'''
        ammesse = '''
_REPO = "apps.x.services.y.OrdiniRepository"
@patch("apps.x.services.y.OrdiniRepository", autospec=True)
@patch(_REPO, autospec=True)
@patch.object(OrdiniRepository, "get_ordine", autospec=True, return_value=1)
@patch("apps.x.services.y.OrdiniRepository", finto)
@patch("apps.x.services.y.OrdiniRepository", new=finto)
@patch.object(OrdiniRepository, "get_ordine", finto)
@patch.object(pagamenti_service, "PagamentiRepository", autospec=True, return_value=repo)
@patch.object(modulo, "OrdiniService")
@patch("apps.x.services.y.OrdiniService")
@patch("apps.x.db.y.OrdiniRepository.get_ordine", autospec=True)
@patch("apps.x.services.y.OrdiniService.get_ordine")
@unittest.mock.patch("apps.x.services.y.OrdiniRepository", autospec=True)
def f(): pass
'''
        self.assertEqual(len(list(patch_senza_autospec(vietate))), 12)
        self.assertEqual(list(patch_senza_autospec(ammesse)), [])
