# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Guardrail anti-ricaduta sul registro codici errore (risposta DB al
#        brief `brief-db-seed-messaggi-errore-mancanti.md`, §9.6). Analisi
#        statica AST: fallisce se un codice `E_*` passato a un punto di chiamata
#        (`code=` / `error_code=`) non e' dichiarato in `error_policies.py`.
#
#        PERCHE' SUI PUNTI DI CHIAMATA E NON SULLE DICHIARAZIONI. Il confronto
#        naturale — `error_policies.py` contro il catalogo `config.messaggi_errore`
#        — e' cieco proprio dove serve: `E_PIPELINE_DRIVER_MAX_ITER` finiva nel
#        log senza essere dichiarato da nessuna parte, e quel confronto lo
#        avrebbe dato per verde. Cio' che arriva a `dbops.error_log` e' cio' che
#        si CHIAMA, non cio' che si dichiara: il guardrail guarda quello. Al
#        primo giro (2026-08-04) ha trovato 28 codici sfilati, fra cui un
#        segnaposto mai sostituito e quattro usi di un generico `E_NOT_FOUND`.
#
#        E' il gemello lato BE del check che il team DB tiene sul proprio lato
#        (codici sollevati dalle funzioni vive contro `messaggi_errore.csv`): i
#        due registri si sfilano per vie diverse e servono entrambi.
#
#        Se questo test fallisce su un codice NUOVO: dichiaralo in
#        `error_policies_generated.py` dandogli la sua CLASSE (e chiedi al team
#        DB il seed a catalogo con la stessa classe, altrimenti
#        il log lo degrada a `MESSAGGIO_NON_DEFINITO`), oppure correggi il punto
#        di chiamata se il codice e' un residuo. L'ALLOWLIST e' per i casi
#        deliberati, con motivazione scritta.
#
#        Gira SENZA database (SimpleTestCase + AST): compatibile CI.
# ------------------------------------------------------------

from __future__ import annotations

import ast
import re
from pathlib import Path
from unittest import TestCase

# Radice backend: .../backend/apps/core/tests/<file> -> parents[3] = backend.
_BACKEND = Path(__file__).resolve().parents[3]
_APPS = _BACKEND / "apps"
# Dal 2026-08-07 i codici dichiarati non stanno piu' in `error_policies.py` (che
# ora contiene le REGOLE: classe -> status, ui_action) ma nella mappa
# `codice -> classe` del modulo destinato a essere generato dal DB. E' quello
# l'elenco di cio' che il backend dichiara di conoscere.
_POLICIES = _APPS / "core" / "services" / "error_policies_generated.py"

# Keyword che veicolano un codice errore verso ErrorManager / ServiceError.
_CODE_KWARGS = ("code", "error_code")

# Codici ammessi pur non essendo dichiarati. Vuota per scelta: ogni voce va
# motivata in una riga, altrimenti il guardrail diventa un elenco di deroghe.
_ALLOWLIST: dict[str, str] = {}


# Scopo: raccoglie i codici dichiarati come chiave di `CLASSE_PER_CODICE`.
#        Lettura testuale e non import del modulo: il guardrail deve poter
#        girare anche se Django non e' configurato.
def _codici_dichiarati() -> set[str]:
    testo = _POLICIES.read_text(encoding="utf-8")
    return set(re.findall(r'"(E_[A-Z0-9_]+)":\s*"[A-Z_]+",', testo))


# Scopo: costanti di modulo che valorizzano un codice (`E_GIRO_PAYLOAD =
#        "E_FATTURAZIONE_GIRO_PAYLOAD"`). Senza risolverle il guardrail
#        perderebbe i moduli che le usano — cioe' quasi tutti gli handler.
def _costanti_modulo(tree: ast.Module) -> dict[str, str]:
    costanti: dict[str, str] = {}
    for nodo in ast.walk(tree):
        if not isinstance(nodo, ast.Assign):
            continue
        valore = nodo.value
        if not (isinstance(valore, ast.Constant) and isinstance(valore.value, str)):
            continue
        if not valore.value.startswith("E_"):
            continue
        for target in nodo.targets:
            if isinstance(target, ast.Name):
                costanti[target.id] = valore.value
    return costanti


# Scopo: tutti i codici `E_*` passati a un punto di chiamata, con il file e la
#        riga del primo uso (serve al messaggio di fallimento: un elenco di
#        codici senza posizione non e' azionabile).
def _codici_usati() -> dict[str, str]:
    usati: dict[str, str] = {}
    for file in sorted(_APPS.rglob("*.py")):
        if "/tests/" in file.as_posix() or file.name.startswith("test_"):
            continue
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover — file non parsabile: non e' compito nostro
            continue
        costanti = _costanti_modulo(tree)
        for nodo in ast.walk(tree):
            if not isinstance(nodo, ast.Call):
                continue
            for kw in nodo.keywords:
                if kw.arg not in _CODE_KWARGS:
                    continue
                codice = None
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    codice = kw.value.value
                elif isinstance(kw.value, ast.Name):
                    codice = costanti.get(kw.value.id)
                if codice and codice.startswith("E_"):
                    posizione = f"{file.relative_to(_BACKEND)}:{nodo.lineno}"
                    usati.setdefault(codice, posizione)
    return usati


class ErrorCodesDeclaredGuardrail(TestCase):
    # Scopo: ogni codice che il backend puo' far arrivare al log deve avere una
    #        policy. Senza, `script.fn_log_error_only` lo degrada a
    #        `MESSAGGIO_NON_DEFINITO` e l'errore diventa non attribuibile.
    def test_ogni_codice_usato_e_dichiarato(self):
        dichiarati = _codici_dichiarati()
        self.assertGreater(len(dichiarati), 300, "estrazione policy fallita: registro sospetto")

        mancanti = {
            codice: posizione
            for codice, posizione in _codici_usati().items()
            if codice not in dichiarati and codice not in _ALLOWLIST
        }
        if mancanti:
            righe = "\n".join(f"  - {c}  ({p})" for c, p in sorted(mancanti.items()))
            self.fail(
                f"{len(mancanti)} codici errore usati ma non dichiarati in "
                f"error_policies_generated.py:\n{righe}\n\n"
                "Dichiarali con la loro classe (e chiedi al team DB il seed in "
                "config.codici_errore + config.messaggi_errore), oppure correggi "
                "il punto di chiamata se sono residui."
            )

    # Scopo: l'allowlist non deve diventare la discarica del guardrail — ogni
    #        voce esige una motivazione non vuota.
    def test_allowlist_motivata(self):
        for codice, motivo in _ALLOWLIST.items():
            self.assertTrue(motivo.strip(), f"allowlist senza motivazione: {codice}")
