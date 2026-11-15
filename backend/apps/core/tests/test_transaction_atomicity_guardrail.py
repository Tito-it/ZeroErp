# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Guardrail anti-regressione atomicità (piano analisi-fix-transazioni §4,
#        "Rete di prevenzione"). Analisi statica AST: fallisce se un metodo
#        compone 2+ scritture DB (cursor.execute INSERT/UPDATE/DELETE, o SELECT
#        fn_ di mutazione) senza racchiuderle tutte in un `transaction.atomic()`.
#        Impedisce di re-introdurre la classe di bug "scrittura1 committa, poi
#        scrittura2 fallisce -> stato parziale" sanata sui 17 finding del piano.
#
#        v1 (conservativo, zero-rumore): rileva SOLO `cursor.execute(...)` con SQL
#        di scrittura — segnale preciso, immune ai falsi positivi da dict.update()
#        o create_*() su variabili locali. La composizione a livello SERVICE (2+
#        chiamate a metodi-write del repository senza atomic) e' un follow-up v2:
#        richiede euristiche receiver-aware (quali attributi sono repository) per
#        non generare rumore. Il v1 copre la composizione a livello REPOSITORY.
#
#        Conteggio compositional: rami if/else -> max (mutuamente esclusivi),
#        sequenziale -> somma, `with ...atomic()` -> le scritture nel body sono
#        "protette". `_map_db_errors`/`_db_errors` NON contano come atomic (sono
#        solo mapper di eccezioni).
#
#        Se questo test fallisce su un NUOVO metodo: o racchiudi le 2+ scritture
#        in `with transaction.atomic()`, oppure — se la non-atomicità e'
#        deliberata (saga con side-effect esterno, protocollo idempotency, ...) —
#        aggiungi la voce all'ALLOWLIST con una motivazione esplicita.
# ------------------------------------------------------------

from __future__ import annotations

import ast
import re
from pathlib import Path
from unittest import TestCase

from apps.core.tests._repo import repo_root

_BACKEND = repo_root() / "backend"
_APPS = _BACKEND / "apps"

# Sottocartelle scandite (layer che eseguono SQL diretto o orchestrano scritture).
_SCANNED_SUBDIRS = ("services", "db", "repositories")

# SQL di scrittura passato a cursor.execute(...): DML esplicito oppure SELECT su
# funzioni madre di mutazione (fn_create/update/delete/upsert/insert/push/genera/
# crea/invalida/set_). Le fn di lettura (fn_get/list/check/resolve) non matchano.
_EXEC_WRITE_SQL_RE = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE)\b"
    r"|\bfn_(create|update|delete|upsert|insert|push|genera|crea|invalida|set_)",
    re.IGNORECASE,
)

# Metodi deliberatamente non-atomici (2+ scritture per scelta di design).
# Chiave: (path relativo da backend/, nome qualificato Classe.metodo). Valore: motivo.
# ⭐ Vuota dal 2026-10-24: l'unica voce era `IdempotencyStore.claim_or_replay`,
#    che scriveva col suo SQL; la prenotazione e' passata a
#    `dbops.fn_idempotency_prenota` (BE-1 di brief-be-verifica-documentazione-api).
ALLOWLIST: dict[tuple[str, str], str] = {}


def _is_atomic_with(node: ast.With) -> bool:
    """True se il `with` apre un `transaction.atomic()` (o `<x>.atomic()`)."""
    for item in node.items:
        expr = item.context_expr
        if (
            isinstance(expr, ast.Call)
            and isinstance(expr.func, ast.Attribute)
            and expr.func.attr == "atomic"
        ):
            return True
    return False


def _exec_is_write(call: ast.Call) -> bool:
    if not call.args:
        return False
    a0 = call.args[0]
    if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
        return bool(_EXEC_WRITE_SQL_RE.search(a0.value))
    # SQL costruito via f-string / concat: euristica sul primo literal.
    if isinstance(a0, ast.JoinedStr) and a0.values:
        first = a0.values[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return bool(_EXEC_WRITE_SQL_RE.search(first.value))
    return False


def _is_mutation(call: ast.Call) -> bool:
    f = call.func
    return isinstance(f, ast.Attribute) and f.attr == "execute" and _exec_is_write(call)


def _count(node: ast.AST, depth: int) -> tuple[int, int]:
    """(total, unprotected) di scritture sul PEGGIOR path attraverso `node`.

    Rami if/else -> max (mutuamente esclusivi); sequenziale -> somma;
    `with ...atomic()` -> depth+1 (le scritture nel body sono protette).
    """
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return (0, 0)  # unità separata: conteggiata a se'
    if isinstance(node, ast.With):
        d2 = depth + (1 if _is_atomic_with(node) else 0)
        t = u = 0
        for item in node.items:
            a, b = _count(item.context_expr, depth); t += a; u += b
        for stmt in node.body:
            a, b = _count(stmt, d2); t += a; u += b
        return (t, u)
    if isinstance(node, ast.If):
        tt, tu = _count(node.test, depth)
        bt = bu = et = eu = 0
        for stmt in node.body:
            a, b = _count(stmt, depth); bt += a; bu += b
        for stmt in node.orelse:
            a, b = _count(stmt, depth); et += a; eu += b
        return (tt + max(bt, et), tu + max(bu, eu))
    t = u = 0
    if isinstance(node, ast.Call) and _is_mutation(node):
        t, u = 1, (1 if depth == 0 else 0)
    for child in ast.iter_child_nodes(node):
        a, b = _count(child, depth); t += a; u += b
    return (t, u)


def _scan_file(path: Path) -> list[tuple[str, int]]:
    """Ritorna [(nome_qualificato, lineno)] dei metodi in violazione nel file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[tuple[str, int]] = []
    stack: list[str] = []

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.ClassDef):
            stack.append(node.name)
            for c in node.body:
                visit(c)
            stack.pop()
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total = unprot = 0
            for stmt in node.body:
                a, b = _count(stmt, 0); total += a; unprot += b
            if total >= 2 and unprot >= 1:
                out.append((".".join(stack + [node.name]), node.lineno))
        else:
            for c in ast.iter_child_nodes(node):
                visit(c)

    visit(tree)
    return out


def _scan_repo() -> dict[tuple[str, str], int]:
    """Mappa {(path_relativo, nome_qualificato): lineno} di tutte le violazioni."""
    found: dict[tuple[str, str], int] = {}
    for app_dir in sorted(_APPS.iterdir()):
        if not app_dir.is_dir():
            continue
        for sub in _SCANNED_SUBDIRS:
            sub_dir = app_dir / sub
            if not sub_dir.is_dir():
                continue
            for path in sorted(sub_dir.rglob("*.py")):
                if "test" in path.name or path.name == "__init__.py":
                    continue
                for qname, line in _scan_file(path):
                    rel = path.relative_to(_BACKEND).as_posix()
                    found[(rel, qname)] = line
    return found


class TransactionAtomicityGuardrailTest(TestCase):
    """Rete di prevenzione: nessuna nuova composizione 2+ write senza atomic."""

    def test_no_unallowlisted_multiwrite_without_atomic(self) -> None:
        found = _scan_repo()
        unexpected = {k: found[k] for k in found if k not in ALLOWLIST}
        if unexpected:
            lines = "\n".join(
                f"  - {rel}:{line}  {qname}"
                for (rel, qname), line in sorted(unexpected.items())
            )
            self.fail(
                "Guardrail atomicità: metodo/i con 2+ scritture DB (cursor.execute "
                "INSERT/UPDATE/DELETE o SELECT fn_ di mutazione) NON tutte dentro un "
                "`transaction.atomic()`:\n"
                f"{lines}\n\n"
                "Rimedio: racchiudi le scritture in `with transaction.atomic()`. "
                "Se la non-atomicità e' deliberata (saga con SMTP, protocollo "
                "idempotency, ...) aggiungi la voce all'ALLOWLIST in "
                "apps/core/tests/test_transaction_atomicity_guardrail.py con una "
                "motivazione esplicita."
            )

    def test_allowlist_ha_solo_voci_ancora_violate(self) -> None:
        """Evita suppressioni stantie: una voce allowlist che non e' piu' una
        violazione (metodo corretto o rimosso) va tolta."""
        found = _scan_repo()
        stale = {k: reason for k, reason in ALLOWLIST.items() if k not in found}
        if stale:
            lines = "\n".join(f"  - {rel}  {qname}" for (rel, qname) in sorted(stale))
            self.fail(
                "Voci ALLOWLIST non piu' in violazione (rimuovile):\n" + lines
            )
