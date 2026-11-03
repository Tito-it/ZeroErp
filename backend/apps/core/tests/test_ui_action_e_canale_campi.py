# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL PRESIDIO C2 — «la `ui_action` promessa e il canale che la
#        realizza». Ogni codice errore porta a catalogo una promessa
#        all'interfaccia (`ui_action`), e `highlight_form_fields` promette che
#        a video si accende un input. Ma il campo non lo accende `ui_action`:
#        lo accende un ALTRO canale (`error.fields` -> `campiErrati`), che il
#        punto di sollevamento valorizza — o no — per conto suo. Promessa e
#        comportamento viaggiano su due binari e possono divergere in silenzio:
#        un override `highlight_form_fields` con nessun sito che manda il nome
#        del campo e' un toast senza campo rosso, e nessun test lo vede. Brief:
#        `docs/it/dev/work-done/brief-be-presidio-ui-action-e-canale-campi.md`
#        (§2 la regola, §4-bis.1 il contratto della vista come costruito).
#
#        DUE META', UNA SEDE PER CIASCUNA (guida presidi §6.3). I siti PL/pgSQL
#        li classifica il database in `dbops.vw_punti_canale_campo`, letta qui
#        sul DB provvisto (`richiedi_db_provvisto`) e NON rifatta: il context in
#        una variabile, il codice in una variabile, la risalita alle `fn_check_*`
#        del primo motivo sono cose che una regex sul corpo non regge, e la
#        vista le segue. I siti Python li legge questo file con l'AST,
#        risolvendo le costanti di modulo (un codice passato per NOME di
#        costante non si vede con un grep). ⚠️ Qui serve il SITO che solleva
#        col suo canale campo, quindi la risoluzione resta; il gemello
#        `test_error_codes_declared_guardrail` dal 2026-10-07 guarda invece
#        ogni literal `E_*` (E-2), e non risolve piu' nulla.
#
#        ⚠️ RICHIEDE IL DB VERO, stessa opt-in `ZEROERP_TEST_DB_E2E=1` del
#        cancello del terzo lato (accesa in CI da `ci-validate.yaml`). Non
#        scrive nulla: legge la vista, il catalogo BE e i sorgenti Python.
# ------------------------------------------------------------

"""Indice test previsti (tutti opt-in `ZEROERP_TEST_DB_E2E=1`).

 1) test_ogni_promessa_highlight_ha_un_sito_che_manda_il_campo
       VERSO 1, IL CANCELLO — per ogni codice vivo con `ui_action =
       highlight_form_fields` esiste ALMENO UN sito (Python o PL/pgSQL) che
       valorizza il canale del campo. Rosso sulla promessa vuota, salvo
       esenzione motivata in `_ESENZIONI[(codice, 1)]`.
 2) test_il_registro_delle_esenzioni_si_ritira
       IL VERSO DI RITIRO, nei due versi — una riga di `_ESENZIONI` il cui
       codice ora soddisfa la regola (verso 1) o non manda piu' il campo da
       ogni sito (verso 2) e' rossa: l'eccezione non serve piu' e va tolta.
       Rosso anche su una riga che nomina un codice ritirato o inesistente.
 3) test_verso_2_e_solo_misurato
       VERSO 2, LA PROMESSA CHE NON DECIDE — codici con un'ALTRA `ui_action`
       i cui siti mandano TUTTI il campo: a video l'input si accende comunque,
       quindi e' una decisione di interfaccia da confermare, non un difetto.
       ✅ Deciso da Tid il 21-09 (decisione 1): SOLO MISURATO. Il test lo
       riporta come skip parlante, con l'elenco: non blocca, non e' un verde.
 4) test_la_misura_non_e_degradata
       sanity — la vista risponde, il perimetro esiste, i sorgenti sono stati
       letti, e gli strumenti del criterio funzionano su casi COSTRUITI.
       Senza, i versi sopra sarebbero verdi per sottrazione.

IL CRITERIO PYTHON, scritto qui perche' un verde va letto sapendo cosa copre.
Un «sito» e' un punto dei `.py` non di test di `backend/apps` che nomina il
codice (letterale, o costante di modulo anche IMPORTATA) in una di queste forme,
e «manda il campo» quando:

  * `code=` / `error_code=` su una chiamata (`ServiceError`, `ErrorManager.
    require`, `raise_error`, …): la stessa chiamata porta `context={...,
    "field": <nome>}` oppure `fields=` (non `None`);
  * `PayloadValidator(validation_code=...)`: il BB mette `field` da se' nei
    metodi che estraggono dal payload -> conta come sito CON campo
    (semplificazione dichiarata: i cinque metodi che non lo mandano lo fanno
    per ragione, brief §2.3);
  * la tupla `(codice, messaggio[, campo])` delle mappe di `map_integrity_error`
    / `translate_db_errors` / `make_db_errors_translator`: campo se c'e' il
    terzo elemento;
  * `fallback_code=` di una traduzione: e' un sito SENZA campo — il codice lo
    sceglie il Python, il campo (se arriva) lo decide il database;
  * `_CAMPO_PER_CODICE_DB` (`pratiche_service`): il campo dichiarato per un
    codice che il DB solleva senza `COLUMN` — un sito CON campo;
  * IL SALTO SULL'HELPER LOCALE: una `def` dello stesso modulo che solleva
    `code=<un suo parametro>` con il campo (`_parse_motivo(payload, *,
    code=...)` -> `require(code=code, context={"field": "motivo"})`) mantiene
    la promessa PER CONTO di chi la chiama: `_parse_motivo(payload,
    code="E_X")` e' un sito CON campo per `E_X`, e una chiamata senza `code=`
    lo e' per il default del parametro. Un salto, nello stesso modulo — e'
    la forma Python del `PRIMO_MOTIVO` della vista (il codice lo sceglie il
    chiamante, il campo lo mette chi solleva).

⛔ NON sono siti le tuple dei marker di traduzione (`*_MARKERS`: `(codice,
   frammento)`): li' il codice lo ha gia' scelto il database, e il campo
   viaggia in `diag.fields` — la promessa la mantiene (o no) il sito PL/pgSQL,
   che la vista vede. Contarli come «sito senza campo» farebbe rosso sul
   traduttore per una colpa del guard.

⚠️ LIMITI DICHIARATI: un `context` costruito in una variabile e passato per
   nome non si vede (a differenza della vista, che segue `IN_VARIABILE`); un
   codice scelto a runtime (`code=variabile`) non si vede; le forme sopra sono
   quelle del catalogo BB al 21-09 — una forma NUOVA che porta il campo va
   aggiunta qui, non dichiarata esente.
"""

from __future__ import annotations

import ast
import unittest
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from unittest import TestCase

from apps.core.tests._repo import repo_root
from apps.core.tests.db_e2e import richiedi_db_provvisto

_VISTA = "dbops.vw_punti_canale_campo"
_CHANGESET_VISTA = "20260921-42"
_RADICE_APPS = "backend/apps"
_OVERRIDES = "apps/core/services/error_ui_overrides.py"

_HIGHLIGHT = "highlight_form_fields"

# La vista: i siti che SOLLEVANO il codice (le altre due `via` non lo sono —
# `MOTIVO` e' la check che lo emette, `NOMINATO` un letterale mai sollevato con
# l'helper), e i due `canale` che valgono come «mantenuta» (§4-bis.1).
_VIA_SITO = ("DIRETTO", "PRIMO_MOTIVO")
_CANALE_OK = ("IN_CHIAMATA", "IN_VARIABILE")

# Keyword che veicolano un codice verso ErrorManager / ServiceError, piu' il
# fallback delle traduzioni.
_CODE_KWARGS = ("code", "error_code")
_FALLBACK_KWARGS = ("fallback_code",)


# ══════════════════════════════════════════════════════════════════════
#  IL REGISTRO DELLE ESENZIONI — (codice, verso) -> ragione
# ══════════════════════════════════════════════════════════════════════
#
# Qui, e non in `error_ui_overrides.py`: quel file porta la ragione della
# SCELTA di interfaccia, questo la ragione dell'ECCEZIONE al presidio.
# Mescolarle farebbe di ogni riga una sede doppia (brief §2.4).
#
# Verso 1: un codice `highlight_form_fields` di cui NESSUN sito manda il campo,
#          e che si vuole tenere cosi' lo stesso. ⛔ Vuoto per costruzione: la
#          decisione 5 di Tid («sanare prima») ha svuotato la lista prima che
#          il test nascesse — 29 codici dal lato Python (§3-ter), 37 dal lato
#          DB (§4-bis.3). Una riga qui e' una promessa vuota tenuta apposta, e
#          la ragione deve dire perche' non si sana e non si toglie l'override.
# Verso 2: un codice con un'altra `ui_action` i cui siti mandano TUTTI il
#          campo, e la scelta e' confermata. Il verso non blocca (decisione 1),
#          ma la riga viene RITIRATA se smette di essere vera.
# ⭐ Vuoto dal 2026-10-09: l'unica riga (`E_EMITTENTE_NON_RISOLTO`, verso 2)
#    si e' ritirata da sola quando la bozza email ha preso quel codice senza
#    campo — il rimedio e' la combo dell'emittente in alto, non un input
#    (brief-db-codici-non-trovato-email-e-permessi §9.2).
# ⭐ Di nuovo vuoto dal 2026-11-03: la riga di verso 1 di
#    `E_DOC_EMITTENTE_BA_INCOERENTE` (codice passato da TG_ARGV a un BB trigger,
#    sito che la vista non sapeva leggere) si e' ritirata quando la vista ha
#    imparato a leggere gli argomenti del trigger (D24, 20261103-01/-02).
_ESENZIONI: dict[tuple[str, int], str] = {}


@dataclass(frozen=True)
class SitoPython:
    """Un punto Python che nomina un codice, e se manda il campo."""

    dove: str  # file:riga, solo per il messaggio di un rosso
    forma: str  # raise · PayloadValidator · tupla · fallback · campo_per_codice_db
    con_campo: bool


# Scopo: le costanti di modulo che valorizzano un codice (`E_GIRO_PAYLOAD =
#        "E_FATTURAZIONE_GIRO_PAYLOAD"`).
def _costanti_locali(tree: ast.Module) -> dict[str, str]:
    costanti: dict[str, str] = {}
    for nodo in ast.walk(tree):
        nomi, valore = _assegnamento(nodo)
        if not (isinstance(valore, ast.Constant) and isinstance(valore.value, str)):
            continue
        if not valore.value.startswith("E_"):
            continue
        for nome in nomi:
            costanti[nome] = valore.value
    return costanti


# Scopo: i nomi assegnati e il valore di un assegnamento, sia `X = ...` sia
#        `X: tipo = ...`. ⚠️ I due sono nodi DIVERSI (`Assign` / `AnnAssign`),
#        e i registri che contano qui sono tutti annotati
#        (`_KNOWN_DB_ERROR_MARKERS: tuple[...] = (`, `_CAMPO_PER_CODICE_DB:
#        dict[...] = {`): la prima stesura guardava il solo `Assign` e li
#        perdeva entrambi — il marker contava come sito, il campo per codice
#        non contava affatto (rosso su `E_TEMPLATE_CODICE_DUPLICATO`, 21-09).
#        Per questo il caso costruito scrive i registri nella forma annotata.
def _assegnamento(nodo: ast.AST) -> tuple[set[str], ast.AST | None]:
    if isinstance(nodo, ast.Assign):
        return {t.id for t in nodo.targets if isinstance(t, ast.Name)}, nodo.value
    if isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name) and nodo.value is not None:
        return {nodo.target.id}, nodo.value
    return set(), None


# Scopo: un dizionario letterale `{"chiave": ...}` contiene la chiave `field`?
def _dict_con_field(nodo: ast.AST | None) -> bool:
    return isinstance(nodo, ast.Dict) and any(
        isinstance(k, ast.Constant) and k.value == "field" for k in nodo.keys
    )


# Scopo: il kwarg `fields=` c'e' e non e' il `None` letterale?
def _fields_valorizzato(kws: dict[str, ast.AST]) -> bool:
    nodo = kws.get("fields")
    if nodo is None:
        return False
    return not (isinstance(nodo, ast.Constant) and nodo.value is None)


# Scopo: le `def` del modulo che sollevano `code=<proprio parametro>` CON il
#        campo: `nome -> (parametro, default)`, dove `default` e' il codice
#        `E_*` del parametro se ne ha uno. E' il salto sull'helper locale del
#        criterio in testa al file: un salto, nello stesso modulo, per nome.
#        ⚠️ Solo il parametro che arriva al `code=` della chiamata che manda
#        il campo: un helper che solleva senza campo non e' un helper «con
#        campo», e chi lo chiama non mantiene niente.
def _helper_con_campo(tree: ast.Module) -> dict[str, tuple[str, str | None]]:
    helper: dict[str, tuple[str, str | None]] = {}
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        argomenti = fn.args
        parametri = [a.arg for a in argomenti.posonlyargs + argomenti.args + argomenti.kwonlyargs]
        # I default, allineati in coda: `defaults` copre gli ultimi N
        # posizionali, `kw_defaults` e' uno per kwonly (None = senza default).
        default: dict[str, str | None] = dict.fromkeys(parametri)
        posizionali = argomenti.posonlyargs + argomenti.args
        for a, d in zip(posizionali[len(posizionali) - len(argomenti.defaults):], argomenti.defaults, strict=True):
            if isinstance(d, ast.Constant) and isinstance(d.value, str) and d.value.startswith("E_"):
                default[a.arg] = d.value
        for a, d in zip(argomenti.kwonlyargs, argomenti.kw_defaults, strict=True):
            if isinstance(d, ast.Constant) and isinstance(d.value, str) and d.value.startswith("E_"):
                default[a.arg] = d.value
        for nodo in ast.walk(fn):
            if not isinstance(nodo, ast.Call):
                continue
            kws = {k.arg: k.value for k in nodo.keywords if k.arg}
            for kw in _CODE_KWARGS:
                valore = kws.get(kw)
                if not (isinstance(valore, ast.Name) and valore.id in parametri):
                    continue
                if _dict_con_field(kws.get("context")) or _fields_valorizzato(kws):
                    helper[fn.name] = (valore.id, default[valore.id])
    return helper


# Scopo: il nome della funzione chiamata (`PayloadValidator`, `raise_error`).
def _nome_chiamata(nodo: ast.Call) -> str:
    if isinstance(nodo.func, ast.Name):
        return nodo.func.id
    if isinstance(nodo.func, ast.Attribute):
        return nodo.func.attr
    return ""


class _SorgentiPython:
    """I `.py` non di test di `backend/apps`, letti UNA volta per la classe.

    `siti[codice]` e' la lista dei punti che nominano quel codice nelle forme
    del criterio in testa al file. Le costanti si risolvono anche se importate
    (`from apps.anagrafiche.error_codes import E_CONTATTO_INCOMPLETO`), quindi
    la lettura e' in due passate: prima le costanti di ogni modulo, poi i siti.
    """

    # Scopo: legge, risolve le costanti e raccoglie i siti.
    def __init__(self, radice: Path) -> None:
        self.siti: dict[str, list[SitoPython]] = defaultdict(list)
        self.n_file = 0
        moduli: dict[Path, ast.Module] = {}
        for percorso in sorted(radice.rglob("*.py")):
            posix = percorso.as_posix()
            if "/tests/" in posix or percorso.name.startswith("test_"):
                continue
            # ⚠️ Solo l'AST, niente testo: tuple, chiamate e assegnamenti
            #    `_CAMPO_PER_CODICE_DB` si leggono dall'albero, dove una
            #    docstring non e' mai un assegnamento. Fino al 2026-09-28 qui
            #    si calcolava anche il sorgente «senza docstring», per una
            #    ricerca per nome nel testo che nessuno faceva (ruff B007).
            moduli[percorso] = ast.parse(percorso.read_text(encoding="utf-8"))
        self.n_file = len(moduli)

        # Passata 1: le costanti locali di ogni modulo, per nome di modulo.
        self._radice = radice
        locali = {self._nome_modulo(p): _costanti_locali(t) for p, t in moduli.items()}

        # Passata 2: i siti, con le costanti importate risolte.
        for percorso, tree in moduli.items():
            costanti = dict(locali[self._nome_modulo(percorso)])
            for nodo in ast.walk(tree):
                if isinstance(nodo, ast.ImportFrom) and nodo.module:
                    sorgente = locali.get(nodo.module, {})
                    for alias in nodo.names:
                        if alias.name in sorgente:
                            costanti[alias.asname or alias.name] = sorgente[alias.name]
            rel = percorso.relative_to(radice.parent).as_posix()
            self._raccogli(rel, tree, costanti)

    # Scopo: `apps.pratiche.services.pratiche_service` da un percorso.
    def _nome_modulo(self, percorso: Path) -> str:
        return ".".join(percorso.relative_to(self._radice.parent).with_suffix("").parts)

    # Scopo: risolve un nodo a un codice `E_*`: letterale, nome di costante, o
    #        attributo (`error_codes.E_X`). `None` se non e' un codice.
    @staticmethod
    def _codice(nodo: ast.AST | None, costanti: dict[str, str]) -> str | None:
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            return nodo.value if nodo.value.startswith("E_") else None
        if isinstance(nodo, ast.Name):
            return costanti.get(nodo.id)
        if isinstance(nodo, ast.Attribute):
            return costanti.get(nodo.attr)
        return None

    # Scopo: i siti di un modulo, nelle forme del criterio.
    def _raccogli(self, rel: str, tree: ast.Module, costanti: dict[str, str]) -> None:
        # Le tuple dentro un assegnamento `*_MARKERS` sono traduzioni, non siti.
        # E `_CAMPO_PER_CODICE_DB` e' la forma «campo per codice DB»: ogni sua
        # chiave e' un sito CON campo.
        tuple_marker: set[int] = set()
        for nodo in ast.walk(tree):
            nomi, valore = _assegnamento(nodo)
            if valore is None:
                continue
            if any(n.endswith("_MARKERS") for n in nomi):
                tuple_marker.update(id(t) for t in ast.walk(valore) if isinstance(t, ast.Tuple))
            if "_CAMPO_PER_CODICE_DB" in nomi and isinstance(valore, ast.Dict):
                for chiave in valore.keys:
                    codice = self._codice(chiave, costanti)
                    if codice:
                        self.siti[codice].append(
                            SitoPython(f"{rel}:{nodo.lineno}", "campo_per_codice_db", True)
                        )

        helper = _helper_con_campo(tree)

        for nodo in ast.walk(tree):
            if isinstance(nodo, ast.Call):
                kws = {k.arg: k.value for k in nodo.keywords if k.arg}
                dove = f"{rel}:{nodo.lineno}"
                nome = _nome_chiamata(nodo)
                if nome in helper:
                    # (a-bis) il salto sull'helper locale: il codice del
                    # chiamante, il campo dell'helper. Senza `code=` vale il
                    # default. ⚠️ E la chiamata NON e' anche un sito «raise»
                    # senza campo: conterebbe due volte, e la seconda farebbe
                    # del codice un «non sempre col campo» nel verso 2.
                    parametro, default = helper[nome]
                    codice = self._codice(kws.get(parametro), costanti) if parametro in kws else default
                    if codice:
                        self.siti[codice].append(SitoPython(dove, "helper", True))
                else:
                    # (a) il punto di sollevamento: code= / error_code=
                    for kw in _CODE_KWARGS:
                        codice = self._codice(kws.get(kw), costanti)
                        if codice:
                            con_campo = _dict_con_field(kws.get("context")) or _fields_valorizzato(kws)
                            self.siti[codice].append(SitoPython(dove, "raise", con_campo))
                # (b) il fallback di una traduzione: il campo lo decide il DB
                for kw in _FALLBACK_KWARGS:
                    codice = self._codice(kws.get(kw), costanti)
                    if codice:
                        self.siti[codice].append(SitoPython(dove, "fallback", False))
                # (c) PayloadValidator(validation_code=...)
                if nome == "PayloadValidator":
                    codice = self._codice(kws.get("validation_code"), costanti)
                    if codice:
                        self.siti[codice].append(SitoPython(dove, "PayloadValidator", True))
            elif isinstance(nodo, ast.Tuple) and len(nodo.elts) >= 2 and id(nodo) not in tuple_marker:
                # (d) la tupla (codice, messaggio[, campo]) delle mappe vincolo
                codice = self._codice(nodo.elts[0], costanti)
                messaggio = nodo.elts[1]
                if codice and isinstance(messaggio, ast.Constant) and isinstance(messaggio.value, str):
                    con_campo = (
                        len(nodo.elts) >= 3
                        and isinstance(nodo.elts[2], ast.Constant)
                        and isinstance(nodo.elts[2].value, str)
                    )
                    self.siti[codice].append(SitoPython(f"{rel}:{nodo.lineno}", "tupla", con_campo))


@dataclass(frozen=True)
class SitoDb:
    """Una riga della vista per un codice: funzione, via, canale, e i conteggi."""

    funzione: str
    via: str
    canale: str | None
    chiave: str | None
    nome_in_chiave: str | None
    n_chiamate: int
    n_con_canale: int

    # Scopo: e' un sito che solleva il codice (non MOTIVO/NOMINATO)?
    @property
    def solleva(self) -> bool:
        return self.via in _VIA_SITO

    # Scopo: almeno una chiamata porta il canale (verso 1).
    @property
    def con_campo(self) -> bool:
        return self.solleva and self.canale in _CANALE_OK

    # Scopo: OGNI chiamata porta il canale (verso 2, §4-bis.1).
    @property
    def sempre_con_campo(self) -> bool:
        return self.con_campo and self.n_chiamate > 0 and self.n_con_canale == self.n_chiamate


# Scopo: legge la vista sul DB provvisto. FALLISCE — non salta — se lo schema
#        c'e' e la vista no: e' la stessa distinzione di
#        `test_error_codes_db_policy_guardrail` (ambiente vs difetto).
def _leggi_vista() -> dict[str, list[SitoDb]]:
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT to_regclass(%s) IS NOT NULL", [_VISTA])
        row = cur.fetchone()
        assert row is not None
        if not row[0]:
            raise AssertionError(
                f"schema Liquibase presente ma la misura del presidio C2 no: "
                f"{_VISTA} MANCANTE. Applicare il changeSet {_CHANGESET_VISTA} "
                "(brief-be-presidio-ui-action-e-canale-campi §4-bis)."
            )
        cur.execute(
            f"SELECT codice, funzione, via, canale, chiave, nome_in_chiave, "
            f"n_chiamate, n_con_canale FROM {_VISTA} WHERE codice IS NOT NULL"
        )
        righe = cur.fetchall()
    per_codice: dict[str, list[SitoDb]] = defaultdict(list)
    for codice, funzione, via, canale, chiave, nome_in_chiave, n_chiamate, n_con_canale in righe:
        per_codice[codice].append(
            SitoDb(funzione, via, canale, chiave, nome_in_chiave, n_chiamate or 0, n_con_canale or 0)
        )
    return per_codice


# Scopo: la `ui_action` effettiva di un codice, letta dal REGISTRO — la stessa
#        derivazione che serve l'envelope (`ErrorPolicyRegistry._deriva`:
#        override, altrimenti default della classe), non una copia sua: una
#        copia sarebbe verde il giorno in cui la derivazione cambia e il
#        presidio misurerebbe un'altra cosa. `None` per un codice senza policy
#        servibile — le classi senza status (`AVVISO`: si scrive nel diario,
#        non si alza), che il registro rifiuta apposta con un'eccezione.
def _ui_action(codice: str) -> str | None:
    from apps.core.services.error_policies import (
        ClasseErroreSenzaStatus,
        ErrorPolicyRegistry,
    )

    if not ErrorPolicyRegistry.has(codice):
        return None
    try:
        return ErrorPolicyRegistry.resolve(codice).ui_action
    except ClasseErroreSenzaStatus:
        return None


class UiActionECanaleCampiTests(TestCase):
    """Il presidio C2: la promessa `highlight_form_fields` contro il canale `fields`.

    ⚠️ Salta se lo schema non c'e', FALLISCE se c'e' ma manca la vista.
    """

    vivi: list[str]
    db: dict[str, list[SitoDb]]
    py: _SorgentiPython

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        from apps.core.services.error_policies_generated import CLASSE_PER_CODICE, CODICI_RITIRATI

        # I ritirati escono dal perimetro PER COSTRUZIONE: l'override resta
        # perche' il diario deve continuare a risolvere, ma nessuno li solleva
        # piu' e una promessa a un codice morto non e' un difetto (brief §3).
        cls.vivi = sorted(c for c in CLASSE_PER_CODICE if c not in CODICI_RITIRATI)
        cls.db = _leggi_vista()
        cls.py = _SorgentiPython(repo_root() / _RADICE_APPS)

    # Scopo: il perimetro del verso 1.
    def _highlight(self) -> list[str]:
        return [c for c in self.vivi if _ui_action(c) == _HIGHLIGHT]

    # Scopo: il perimetro del verso 2.
    def _altri(self) -> list[str]:
        return [c for c in self.vivi if _ui_action(c) not in (None, _HIGHLIGHT)]

    # Scopo: i siti che sollevano il codice, sui due lati.
    def _siti(self, codice: str) -> tuple[list[SitoPython], list[SitoDb]]:
        return self.py.siti.get(codice, []), [s for s in self.db.get(codice, []) if s.solleva]

    # Scopo: verso 1 — almeno un sito manda il campo.
    def _promessa_mantenuta(self, codice: str) -> bool:
        py, db = self._siti(codice)
        return any(s.con_campo for s in py) or any(s.con_campo for s in db)

    # Scopo: verso 2 — c'e' almeno un sito, e OGNI sito manda il campo.
    def _sempre_col_campo(self, codice: str) -> bool:
        py, db = self._siti(codice)
        if not py and not db:
            return False
        return all(s.con_campo for s in py) and all(s.sempre_con_campo for s in db)

    # Scopo: la riga di diagnosi di un codice: cosa lo nomina, e come.
    def _diagnosi(self, codice: str) -> str:
        py, db = self._siti(codice)
        nominato = [s.funzione for s in self.db.get(codice, []) if s.via == "NOMINATO"]
        parti: list[str] = []
        for s in py:
            parti.append(f"py {s.forma} {s.dove}" + (" [campo]" if s.con_campo else ""))
        for s in db:
            extra = f" {s.canale}" + (f"={s.chiave}" if s.chiave else "")
            if s.nome_in_chiave:
                extra += f" (colonna come CHIAVE: {s.nome_in_chiave})"
            parti.append(f"db {s.via} {s.funzione}{extra} {s.n_con_canale}/{s.n_chiamate}")
        if not parti:
            if nominato:
                return "nominato ma mai sollevato con l'helper: " + ", ".join(nominato)
            return "NESSUN SITO: ne' Python ne' PL/pgSQL lo nomina"
        return "\n      ".join(parti)

    # Scopo: VERSO 1, IL CANCELLO. Un codice che promette il campo e nessun
    #        sito lo manda e' una promessa vuota: a video un toast e nessun
    #        input rosso. Non c'e' un `_DEBITO`: la lista e' stata svuotata
    #        PRIMA che il test nascesse (decisione 5), quindi il rubinetto si
    #        chiude sul primo.
    def test_ogni_promessa_highlight_ha_un_sito_che_manda_il_campo(self):
        vuote: list[str] = []
        for codice in self._highlight():
            if (codice, 1) in _ESENZIONI or self._promessa_mantenuta(codice):
                continue
            vuote.append(f"  - {codice}\n      {self._diagnosi(codice)}")
        if vuote:
            self.fail(
                f"{len(vuote)} promesse VUOTE: `ui_action = highlight_form_fields` "
                f"senza un sito che mandi il nome del campo:\n" + "\n".join(vuote) + "\n\n"
                "Due strade, e nessuna e' «lasciare cosi'» (brief §3-ter): A) il "
                "sito ha in mano il nome di un INPUT DELLA PAGINA -> lo manda "
                "(`context={\"field\": ...}` / `fields=` in Python, `'campo'` nel "
                "`jsonb_build_object` in PL/pgSQL); B) non c'e' un input da "
                f"accendere (id dall'URL, query string, parametro di firma, "
                f"invariante) -> l'override esce da {_OVERRIDES} e il codice torna "
                "al banner di classe. Una promessa vuota tenuta APPOSTA va in "
                "`_ESENZIONI[(codice, 1)]` con la ragione — e la ragione deve "
                "dire perche' non si sana e non si toglie l'override."
            )

    # Scopo: IL VERSO DI RITIRO, obbligatorio su ogni registro: una riga che
    #        non serve piu' e' rossa, altrimenti il registro cresce e basta.
    #        Verso 1: il codice ora soddisfa la regola. Verso 2: il codice non
    #        manda piu' il campo da ogni sito, o e' tornato `highlight`.
    #        E una riga su un codice ritirato/inesistente e' rossa in entrambi.
    def test_il_registro_delle_esenzioni_si_ritira(self):
        vivi = set(self.vivi)
        superate: list[str] = []
        for (codice, verso), ragione in _ESENZIONI.items():
            self.assertIn(verso, (1, 2), f"_ESENZIONI: verso {verso!r} sconosciuto su {codice}")
            self.assertTrue(ragione.strip(), f"_ESENZIONI: {codice} verso {verso} senza ragione")
            if codice not in vivi:
                superate.append(f"  - {codice} (verso {verso}): codice ritirato o non a catalogo")
            elif verso == 1 and (_ui_action(codice) != _HIGHLIGHT or self._promessa_mantenuta(codice)):
                superate.append(
                    f"  - {codice} (verso 1): ora "
                    + ("non promette piu' il campo" if _ui_action(codice) != _HIGHLIGHT
                       else "un sito manda il campo")
                )
            elif verso == 2 and (_ui_action(codice) == _HIGHLIGHT or not self._sempre_col_campo(codice)):
                superate.append(
                    f"  - {codice} (verso 2): ora "
                    + ("promette il campo" if _ui_action(codice) == _HIGHLIGHT
                       else "non ogni sito manda il campo")
                    + f"\n      {self._diagnosi(codice)}"
                )
        if superate:
            self.fail(
                f"{len(superate)} righe di `_ESENZIONI` che non servono piu':\n"
                + "\n".join(superate)
                + "\n\nToglierle: un'esenzione superata e' un debito che non cala."
            )

    # Scopo: VERSO 2, SOLO MISURATO (decisione 1 di Tid, 21-09). Un codice
    #        con un'altra `ui_action` i cui siti mandano tutti il campo non fa
    #        danno a video: il campo si accende, il banner c'e'. E' una promessa
    #        che non decide, non una che mente — una decisione di interfaccia
    #        da confermare (-> `_ESENZIONI[(codice, 2)]`) o da cambiare
    #        (-> override `highlight_form_fields`), non un difetto da sanare.
    #        Si riporta come SKIP parlante: non blocca, e non e' un verde.
    def test_verso_2_e_solo_misurato(self):
        sempre = [
            c for c in self._altri()
            if (c, 2) not in _ESENZIONI and self._sempre_col_campo(c)
        ]
        confermati = [c for c in self._altri() if (c, 2) in _ESENZIONI]
        if not sempre:
            return
        raise unittest.SkipTest(
            f"verso 2, solo misurato: {len(sempre)} codici con un'altra ui_action "
            f"i cui siti mandano TUTTI il campo ({len(confermati)} confermati in "
            f"_ESENZIONI): " + ", ".join(f"{c} [{_ui_action(c)}]" for c in sempre)
        )

    # Scopo: sanity della misura, e la prova degli strumenti su casi COSTRUITI.
    #        Una vista vuota, un perimetro vuoto o una scansione che non ha
    #        letto niente renderebbero il verso 1 verde per sottrazione; e una
    #        regola dell'AST rotta boccerebbe tutto o niente senza dirlo.
    def test_la_misura_non_e_degradata(self):
        n_righe = sum(len(v) for v in self.db.values())
        self.assertGreater(n_righe, 500, f"{_VISTA} sospetta: {n_righe} righe, la misura sembra degradata")
        self.assertGreater(len(self._highlight()), 50, "perimetro del verso 1 sospetto")
        self.assertGreater(len(self._altri()), 300, "perimetro del verso 2 sospetto")
        self.assertGreater(self.py.n_file, 100, "scansione dei sorgenti sospetta: troppo pochi `.py` letti")
        self.assertGreater(len(self.py.siti), 100, "troppo pochi codici con un sito Python: criterio rotto?")

        # Gli strumenti del criterio, su un modulo costruito: ogni forma, nei
        # due versi (con e senza campo), piu' la tupla di un marker che NON
        # deve contare e la costante importata che DEVE risolversi.
        radice = Path(self.id())  # solo un nome: il modulo costruito sta in memoria
        sorgenti = _SorgentiPython.__new__(_SorgentiPython)
        sorgenti.siti = defaultdict(list)
        sorgenti._radice = radice
        modulo = ast.parse(
            'E_A = "E_COSTRUITO_A"\n'
            'raise ServiceError(code=E_A, message="m", context={"field": "x"})\n'
            'ErrorManager.require(ok, code="E_COSTRUITO_B", message="m")\n'
            'raise_error(code="E_COSTRUITO_C", message="m", fields=tuple(m))\n'
            'raise_error(code="E_COSTRUITO_D", message="m", fields=None)\n'
            'PayloadValidator(validation_code="E_COSTRUITO_E")\n'
            'MAPPA = {"uq_x": ("E_COSTRUITO_F", "msg", "campo"), "fk_y": ("E_COSTRUITO_G", "msg")}\n'
            '_KNOWN_DB_ERROR_MARKERS: tuple[tuple[str, str], ...] = (("E_COSTRUITO_H", "frammento"),)\n'
            '_CAMPO_PER_CODICE_DB: dict[str, tuple[str, ...]] = {"E_COSTRUITO_I": ("codice",)}\n'
            'translate_db_errors(fallback_code="E_COSTRUITO_L")\n'
            'def _parse_motivo(payload, *, code="E_COSTRUITO_M"):\n'
            '    ErrorManager.require(ok, code=code, message="m", context={"field": "motivo"})\n'
            'def _senza_campo(payload, *, code):\n'
            '    ErrorManager.require(ok, code=code, message="m")\n'
            '_parse_motivo(p, code="E_COSTRUITO_N")\n'
            '_parse_motivo(p)\n'
            '_senza_campo(p, code="E_COSTRUITO_O")\n'
        )
        sorgenti._raccogli("costruito.py", modulo, _costanti_locali(modulo))
        atteso = {
            "E_COSTRUITO_A": [True],   # costante + context field
            "E_COSTRUITO_B": [False],  # require senza campo
            "E_COSTRUITO_C": [True],   # fields= valorizzato
            "E_COSTRUITO_D": [False],  # fields=None non conta
            "E_COSTRUITO_E": [True],   # PayloadValidator
            "E_COSTRUITO_F": [True],   # tupla a tre
            "E_COSTRUITO_G": [False],  # tupla a due
            "E_COSTRUITO_I": [True],   # _CAMPO_PER_CODICE_DB
            "E_COSTRUITO_L": [False],  # fallback_code
            "E_COSTRUITO_M": [True],   # helper chiamato senza code=: il default
            "E_COSTRUITO_N": [True],   # helper chiamato con code=
            "E_COSTRUITO_O": [False],  # helper SENZA campo: la chiamata e' un sito, senza campo
        }
        self.assertEqual({c: [s.con_campo for s in v] for c, v in sorgenti.siti.items()}, atteso)
        self.assertNotIn("E_COSTRUITO_H", sorgenti.siti, "la tupla di un *_MARKERS non e' un sito")

        # E la lettura della vista: un `NOMINATO` non solleva, un `NESSUNO`
        # non mantiene, `n_con_canale < n_chiamate` non e' «sempre».
        self.assertFalse(SitoDb("f", "NOMINATO", None, None, None, 0, 0).solleva)
        self.assertFalse(SitoDb("f", "DIRETTO", "NESSUNO", None, None, 1, 0).con_campo)
        self.assertFalse(SitoDb("f", "DIRETTO", "CHIAVE_NON_LETTA", None, "qta", 1, 0).con_campo)
        parziale = SitoDb("f", "DIRETTO", "IN_CHIAMATA", "campo", None, 3, 2)
        self.assertTrue(parziale.con_campo)
        self.assertFalse(parziale.sempre_con_campo)
        self.assertTrue(SitoDb("f", "PRIMO_MOTIVO", "IN_VARIABILE", "campo", None, 2, 2).sempre_con_campo)
