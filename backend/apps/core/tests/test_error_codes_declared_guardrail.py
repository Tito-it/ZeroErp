# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#        DAL 2026-08-07 HA UN SECONDO VERSO. Il modulo generato porta anche i
#        codici RITIRATI a catalogo (`CODICI_RITIRATI`), che prima il backend non
#        poteva conoscere: quindi ora si controlla anche che nessun punto di
#        chiamata ne usi uno. Un codice ritirato risolve ancora, ma solo perche'
#        il diario deve restare leggibile — non perche' sia ancora buono.
#
#        DAL 2026-10-07 GUARDA OGNI LITERAL, non solo `code=`/`error_code=`
#        (E-2 di analisi-be-difetti-emersi-verifica-doc-api-core). Il criterio
#        dei soli keyword aveva tre punti ciechi, ed e' da li' che E-1 era
#        passato: le costanti IMPORTATE (`E_ANAG_CONTO_NOT_FOUND` da
#        `error_codes.py`), le costanti assegnate da un ATTRIBUTO
#        (`E_INVITO_PORTALE = PORTA_PORTALE.codice_invito`), e i codici che non
#        passano da una keyword (argomento posizionale di `_json_error`, dizionari
#        `{"code": ...}` scritti in una colonna). Ora vale una regola sola: OGNI
#        stringa che e' per intero un codice `E_*` nel codice di produzione e' un
#        codice, e va dichiarata. Il literal sta sempre da qualche parte — nella
#        costante, nel keyword del costruttore, nel dizionario — quindi non serve
#        risolvere import e attributi. Restano fuori le docstring (prosa) e i
#        quattro moduli del registro (sono la dichiarazione, non l'uso). Codici
#        costruiti a runtime (f-string) non si vedono: e' il limite dichiarato.
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

# Un codice: la stringa INTERA, non un frammento (`"E_"` o `"E_NOTA_"` di uno
# `startswith` non lo sono — un prefisso finisce con `_`, un codice no — e
# nemmeno una frase che ne nomina uno).
_CODICE_RE = re.compile(r"E_[A-Z0-9]+(?:_[A-Z0-9]+)*")

# I moduli del registro: elencano i codici perche' li DICHIARANO (classe, gesto,
# frase di ripiego), compresi i ritirati. Non sono punti d'uso.
_MODULI_REGISTRO = frozenset({
    "apps/core/services/error_policies_generated.py",
    "apps/core/services/error_policies.py",
    "apps/core/services/error_messages_fallback.py",
    "apps/core/services/error_ui_overrides.py",
})

# Codici ammessi pur non essendo dichiarati. Vuota per scelta: ogni voce va
# motivata in una riga, altrimenti il guardrail diventa un elenco di deroghe.
_ALLOWLIST: dict[str, str] = {}

# ⚠️ IL DEBITO, che NON e' l'allowlist: codici usati e non (ancora) in pari,
# ciascuno con la richiesta che lo chiude. Deve calare: una voce che e' tornata
# in pari fa fallire `test_debito_non_pagato` finche' non la si toglie.
_DEBITO: dict[str, str] = {}


# Scopo: raccoglie i codici dichiarati come chiave di `CLASSE_PER_CODICE`.
#        Lettura testuale e non import del modulo: il guardrail deve poter
#        girare anche se Django non e' configurato.
#        ⚠️ E non e' solo una preferenza: `error_policies_generated` sta dentro
#        `apps.core.services`, e importarlo eseguirebbe l'`__init__` del
#        pacchetto — che tira dentro il translator, quindi le settings Django.
def _codici_dichiarati() -> set[str]:
    testo = _POLICIES.read_text(encoding="utf-8")
    return set(re.findall(r'"(E_[A-Z0-9_]+)":\s*"[A-Z_]+",', testo))


# Scopo: i codici che il catalogo ha RITIRATO, dalla coda del modulo generato.
#        Stessa lettura testuale, stessa ragione.
def _codici_ritirati() -> set[str]:
    testo = _POLICIES.read_text(encoding="utf-8")
    _, _, coda = testo.partition("CODICI_RITIRATI")
    return set(re.findall(r'"([A-Z0-9_]+)",', coda))


# Scopo: le docstring di un albero (prosa: nominano codici senza usarli).
def _docstring(tree: ast.Module) -> set[int]:
    nodi: set[int] = set()
    for nodo in ast.walk(tree):
        if not isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        primo = nodo.body[0] if nodo.body else None
        if isinstance(primo, ast.Expr) and isinstance(primo.value, ast.Constant):
            nodi.add(id(primo.value))
    return nodi


# Scopo: tutti i codici `E_*` del codice di produzione — ogni stringa che e'
#        per intero un codice, ovunque stia — con il file e la riga del primo
#        uso (serve al messaggio di fallimento: un elenco di codici senza
#        posizione non e' azionabile).
def _codici_usati() -> dict[str, str]:
    usati: dict[str, str] = {}
    for file in sorted(_APPS.rglob("*.py")):
        relativo = file.relative_to(_BACKEND).as_posix()
        if "/tests/" in relativo or file.name.startswith("test_") or relativo in _MODULI_REGISTRO:
            continue
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover — file non parsabile: non e' compito nostro
            continue
        docstring = _docstring(tree)
        for nodo in ast.walk(tree):
            if (
                isinstance(nodo, ast.Constant)
                and isinstance(nodo.value, str)
                and id(nodo) not in docstring
                and _CODICE_RE.fullmatch(nodo.value)
            ):
                usati.setdefault(nodo.value, f"{relativo}:{nodo.lineno}")
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
            if codice not in dichiarati and codice not in _ALLOWLIST and codice not in _DEBITO
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

    # Scopo: ⭐ IL VERSO NUOVO (2026-08-07, dopo la prima generazione). Un codice
    #        che il catalogo ha RITIRATO non deve comparire in un punto di
    #        chiamata: non e' un errore che «funziona lo stesso», e' un errore
    #        che risolve ancora **solo perche' il diario deve restare leggibile**.
    #        Chi lo usa oggi sta scrivendo righe nuove sotto un nome che il team
    #        DB ha dichiarato superato — e le ritrovera' il giorno in cui quel
    #        nome sparira' davvero.
    #
    #        ⚠️ Questo verso e' nato APPENA e' diventato calcolabile: prima del
    #        B-5 il backend non sapeva quali codici fossero ritirati, perche'
    #        `obsoleto_dal` stava lato DB e nel registro non arrivava. Misurato
    #        alla nascita: **0 su 213** codici usati. Nasce in pari, e da qui puo'
    #        solo restare tale.
    def test_nessun_codice_usato_e_ritirato(self):
        ritirati = _codici_ritirati()
        self.assertGreater(len(ritirati), 50, "estrazione dei ritirati fallita: misura sospetta")

        usati_ritirati = {
            codice: posizione
            for codice, posizione in _codici_usati().items()
            if codice in ritirati and codice not in _ALLOWLIST and codice not in _DEBITO
        }
        if usati_ritirati:
            righe = "\n".join(f"  - {c}  ({p})" for c, p in sorted(usati_ritirati.items()))
            self.fail(
                f"{len(usati_ritirati)} codici errore RITIRATI a catalogo sono "
                f"usati da un punto di chiamata:\n{righe}\n\n"
                "Usare il codice che li ha sostituiti (o chiedere al team DB di "
                "riattivarne uno, se il ritiro era sbagliato). Un codice ritirato "
                "risolve ancora solo per non rompere il diario."
            )

    # Scopo: l'allowlist non deve diventare la discarica del guardrail — ogni
    #        voce esige una motivazione non vuota.
    def test_allowlist_motivata(self):
        for codice, motivo in _ALLOWLIST.items():
            self.assertTrue(motivo.strip(), f"allowlist senza motivazione: {codice}")

    # Scopo: il debito cala. Una voce il cui codice e' ora dichiarato (e non
    #        ritirato), o che nessuno usa piu', e' debito pagato: va tolta, o il
    #        registro torna a nascondere il prossimo codice sfilato.
    def test_debito_non_pagato(self):
        dichiarati = _codici_dichiarati()
        ritirati = _codici_ritirati()
        usati = _codici_usati()
        pagati = sorted(
            codice for codice in _DEBITO
            if codice not in usati or (codice in dichiarati and codice not in ritirati)
        )
        self.assertEqual(pagati, [], "voci di _DEBITO pagate: toglierle dal registro")
        for codice, motivo in _DEBITO.items():
            self.assertTrue(motivo.strip(), f"debito senza motivazione: {codice}")

    # Scopo: i tre punti ciechi del criterio per keyword (E-2) restano visti.
    #        Senza questo, un ritorno al vecchio criterio sarebbe verde.
    def test_vede_import_attributo_e_posizionale(self):
        usati = _codici_usati()
        # costante definita in un modulo e importata altrove
        self.assertIn("E_ANAG_CONTO_NOT_FOUND", usati)
        # keyword del costruttore di una porta, letta poi come attributo
        self.assertIn("E_INVITO_PORTALE", usati)
        # argomento posizionale di `_json_error`
        self.assertIn("E_GUC_RESET_FAILED", usati)

    # Scopo: un prefisso (`"E_NOTA_"` di uno `startswith`) non e' un codice: il
    #        literal finisce con `_`, e contarlo darebbe un rosso falso.
    def test_prefisso_non_e_un_codice(self):
        self.assertIsNone(_CODICE_RE.fullmatch("E_NOTA_"))
        self.assertIsNone(_CODICE_RE.fullmatch("E_"))
        self.assertIsNotNone(_CODICE_RE.fullmatch("E_NOTA_FK"))
