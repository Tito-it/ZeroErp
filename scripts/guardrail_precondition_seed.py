#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Guardrail CI — una `preCondition` di `00_schema`/`20_code` non interroga
#                il CONTENUTO di `80_data`
#   Regola: docs/it/linee-guida-sql.md §11.4
#
# COSA PRESIDIA, in una riga:
#   «un changeSet di schema o di codice non puo' pretendere che una riga di
#    seed esista gia': la corsa che la introduce e' esattamente quella in cui
#    la preCondition non la trova».
#
# IL MECCANISMO. `changelog-master-v2.yaml` esegue in quest'ordine:
#   vecchia storia -> `changelog-autogen.yaml` (00_schema + 20_code, mescolati
#   per numero) -> `80_data` -> `85_pgagent` -> `90_end`.
# Quindi un `sqlCheck` che chiede «esiste la riga X in config.sorgenti?» dentro
# `20_code` viene valutato quando `80_data` non e' ancora passato. Su un
# database di sviluppo la riga c'e' gia' da settimane e la preCondition passa;
# in CI il database nasce vuoto a ogni build e il migrate muore con
#   «SQL Precondition failed. Expected '1' got '0'».
# ⚠️ Non e' un caso di bordo: e' l'UNICO modo in cui un seed nuovo puo'
# arrivare in un database ricostruito da zero.
#
# PERCHE' SERVE UN CANCELLO E NON BASTAVA LA REGOLA. Perche' l'errore *sembra
# prudenza* — «verifico che il codice errore esista prima di creare la funzione
# che lo solleva» — e chi lo scrive lo prova su una macchina dove il seed c'e'.
# Il 2026-09-02, ripartita la CI dopo giorni di fermo, il migrate si e' fermato
# su `20260820-12-update-fn-available-actions-reso-accrediti`, e dietro c'erano
# altre QUATTORDICI mine identiche gia' committate: una build ciascuna per
# scoprirle a mano.
#
# COSA RESTA LEGITTIMO, e percio' non viene segnalato:
#   * le preCondition su cio' che viene PRIMA — `tableExists`, `columnExists`,
#     `viewExists`, `pg_proc`/`pg_trigger`/`pg_views`, l'arita' di una funzione:
#     quelle guardano lo SCHEMA, che a quel punto c'e';
#   * un `sqlCheck` con `expectedResult: 0`, cioe' «nessuna riga cattiva»: un
#     database vuoto lo soddisfa, e il senso e' proprio quello;
#   * ⭐ un `onFail` diverso da `HALT` — `MARK_RAN`, `CONTINUE`, `WARN`. Li' il
#     fallimento e' il comportamento VOLUTO: e' la forma dei backfill del
#     pregresso, che su un database nuovo non hanno niente da fare e si
#     segnano da soli. Non fermano la build, quindi non sono una mina;
#   * il verso opposto, che anzi va tenuto: un changeSet di `80_data` DEVE
#     precondizionare su `tableExists`.
#
# ⚠️ LIMITE DICHIARATO: riconosce le tabelle scritte **qualificate**
# (`schema.tabella`) dopo `FROM`/`JOIN`. Un riferimento non qualificato che si
# appoggia al `search_path` gli sfugge — ed e' comunque da non scrivere.
# ⚠️ I letterali fra apici vengono tolti PRIMA di cercare le tabelle: un
# `position('DELETE FROM vendite.fatture_righe' in p.prosrc)` interroga
# `pg_proc`, non `vendite.fatture_righe`, e senza questo passo sarebbe un falso
# positivo — e un cancello che accusa i sani viene spento dopo due segnalazioni.
#
# Uso (read-only, nessun database):
#   python scripts/guardrail_precondition_seed.py
# Exit 0 se pulito, 1 se trova violazioni.
# ------------------------------------------------------------

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# ⭐ Il parser YAML in C dove c'e', quello in puro Python dove non c'e'.
#   Il 99% del costo di questo cancello e' il parsing (misurato il
#   2026-09-10): ~14x. Stesso risultato, provato su tutti i changelog del
#   repo — vedi scripts/_yaml_veloce.py.
#   ⚠️ `yaml` resta importato: serve per `yaml.YAMLError` nei rami di errore.
from _yaml_veloce import carica as carica_yaml

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "db" / "changelog" / "migrations_v2"
FASI_PRESIDIATE = ("00_schema", "20_code", "70_dati_sistema")
FILENAME_RE = re.compile(r"^\d{8}-\d{2}.*\.(ya?ml)$", re.IGNORECASE)

# Schemi di sistema: leggerli e' leggere lo SCHEMA, non il seed.
SCHEMI_DI_SISTEMA = frozenset({"pg_catalog", "information_schema"})

TABELLA_RE = re.compile(
    r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)", re.IGNORECASE
)

# Letterali a quote singole: dentro non c'e' una tabella, c'e' del testo.
LETTERALE_RE = re.compile(r"'(?:[^']|'')*'")

# Solo `HALT` ferma la build. Con `MARK_RAN`/`CONTINUE`/`WARN` il fallimento
# della preCondition e' il comportamento voluto (backfill del pregresso).
ONFAIL_CHE_FERMA = frozenset({"HALT"})

# ⭐ ECCEZIONI, con la motivazione accanto. Si entra qui solo se la riga
#    interrogata e' popolata PRIMA di `80_data` — cioe' in `00_schema` — e la
#    motivazione deve dire dove.
ECCEZIONI: dict[tuple[str, str], str] = {
    (
        "20_code/dbops/20260722-10-fix-fn-get-or-create-session-tx-id-disciplina-v1-mctit.yaml",
        "dbops.sec_functions_owner",
    ): (
        "il registro e' seminato in "
        "00_schema/dbops/20251123-02-seed-sec-functions-owner-mctit.yaml, "
        "quindi la riga c'e' gia' quando questa preCondition la cerca"
    ),
}


# Scopo: elenca i `sqlCheck` di una preCondition, ovunque siano annidati.
def _sql_check(nodo) -> list[dict]:
    trovati: list[dict] = []
    if isinstance(nodo, dict):
        valore = nodo.get("sqlCheck")
        if isinstance(valore, dict):
            trovati.append(valore)
        for v in nodo.values():
            trovati.extend(_sql_check(v))
    elif isinstance(nodo, list):
        for v in nodo:
            trovati.extend(_sql_check(v))
    return trovati


# Scopo: l'`onFail` dichiarato dal blocco preConditions (default: HALT).
def _on_fail(pre) -> str:
    if isinstance(pre, list):
        for voce in pre:
            if isinstance(voce, dict) and "onFail" in voce:
                return str(voce["onFail"]).strip().upper()
    elif isinstance(pre, dict) and "onFail" in pre:
        return str(pre["onFail"]).strip().upper()
    return "HALT"


# Scopo: le tabelle applicative citate da una query di preCondition.
def _tabelle_applicative(sql: str) -> set[str]:
    sql = LETTERALE_RE.sub("''", sql)
    return {
        f"{schema.lower()}.{tabella.lower()}"
        for schema, tabella in TABELLA_RE.findall(sql)
        if schema.lower() not in SCHEMI_DI_SISTEMA
        and not tabella.lower().startswith("pg_")
    }


# Scopo: elenca le violazioni (file, changeSet, tabella, query) nelle fasi
#   presidiate.
def trova_violazioni() -> list[tuple[str, str, str, str]]:
    fuori: list[tuple[str, str, str, str]] = []
    for fase in FASI_PRESIDIATE:
        radice = BASE / fase
        if not radice.is_dir():
            continue
        for p in sorted(radice.rglob("*")):
            if not p.is_file() or not FILENAME_RE.match(p.name):
                continue
            testo = p.read_text(encoding="utf-8")
            if "sqlCheck" not in testo:
                continue
            try:
                doc = carica_yaml(testo)
            except yaml.YAMLError as exc:
                print(f"⚠️  YAML non parsabile, saltato: {p} ({exc})", file=sys.stderr)
                continue
            if not isinstance(doc, dict):
                continue
            rel = p.relative_to(BASE).as_posix()
            for blocco in doc.get("databaseChangeLog", []) or []:
                if not isinstance(blocco, dict) or "changeSet" not in blocco:
                    continue
                cs = blocco["changeSet"] or {}
                cs_id = str(cs.get("id", "<senza id>"))
                pre = cs.get("preConditions")
                if _on_fail(pre) not in ONFAIL_CHE_FERMA:
                    continue
                for check in _sql_check(pre):
                    atteso = str(check.get("expectedResult", "")).strip().strip("'\"")
                    # `expectedResult: 0` = «nessuna riga cattiva»: un database
                    # vuoto lo soddisfa, ed e' proprio il senso del controllo.
                    if atteso == "0":
                        continue
                    sql = " ".join(str(check.get("sql", "")).split())
                    for tabella in sorted(_tabelle_applicative(sql)):
                        if (rel, tabella) in ECCEZIONI:
                            continue
                        fuori.append((rel, cs_id, tabella, sql[:120]))
    return fuori


# Scopo: eseguire il controllo e tradurre l'esito in exit code per la CI.
def main() -> int:
    violazioni = trova_violazioni()
    if not violazioni:
        print(
            "✅ guardrail preCondition/seed: nessuna preCondition interroga il "
            f"contenuto di 80_data in {' / '.join(FASI_PRESIDIATE)}"
        )
        return 0

    print(
        f"❌ guardrail preCondition/seed: {len(violazioni)} preCondition "
        "interrogano righe che arrivano DOPO, con 80_data.\n"
        "   In CI il database nasce vuoto: il migrate morira' con\n"
        "   «SQL Precondition failed. Expected '1' got '0'».\n",
        file=sys.stderr,
    )
    for rel, cs_id, tabella, sql in violazioni:
        print(f"  · {rel}", file=sys.stderr)
        print(f"      changeSet: {cs_id}", file=sys.stderr)
        print(f"      tabella  : {tabella}", file=sys.stderr)
        print(f"      sql      : {sql}", file=sys.stderr)
    print(
        "\n   Rimedio: togliere la preCondition. Il seed e' un fatto di RUNTIME —\n"
        "   un codice errore, un tipo, una sorgente si nominano come STRINGA e si\n"
        "   risolvono quando la funzione viene chiamata, cioe' quando 80_data e'\n"
        "   passato da un pezzo. Cio' che il cancello voleva difendere («se il\n"
        "   codice_interno cambiasse, il CASE smetterebbe di agganciarsi in\n"
        "   silenzio») e' un presidio pgTAP, non un cancello di migrate.\n"
        "   Regola: docs/it/linee-guida-sql.md §11.4",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
