#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Guardrail CI — niente DDL INCONDIZIONATA su un trigger che lo crea `ci_apply`
#   Regola: docs/it/linee-guida-sql.md §11.5
#
# COSA PRESIDIA, in una riga:
#   «un changeSet di schema o di codice non puo' dare per scontato un trigger
#    che nasce dalle automazioni: quelle girano DOPO, nella seconda invocazione
#    di Liquibase».
#
# DUE FACCE, e la seconda e' arrivata dopo:
#   (A) DDL incondizionata su quei trigger — `ALTER TRIGGER … RENAME`,
#       `DROP TRIGGER` senza `IF EXISTS`;
#   (B) una preCondition `sqlCheck` che li CONTA in `pg_trigger` e ne pretende
#       un numero. Il 2026-09-02 `20260831-71` chiedeva «i sei guard di
#       disattivazione sono montati»: su un database ricostruito da zero non ce
#       n'e' nemmeno uno, `string_agg` su zero righe da' NULL e il migrate muore
#       con «SQL Precondition failed. Expected '1' got '0'».
#       ⭐ Ed era un DOPPIONE del test 6 del suo pgTAP, che fa la stessa
#       identica query — ma gira a `ci_apply` avvenuto.
#
# IL MECCANISMO. I trigger di audit, `tx_id` e storico non li scrive nessun
# changeSet: li genera il framework delle automazioni, che gira con
# `--contexts=ci_apply` — in CI la SECONDA invocazione di Liquibase, sul
# migrate manuale il pgagent la sera. Quindi durante la prima passata una
# tabella creata poche centinaia di changeSet prima **non li ha ancora**.
# Un `ALTER TRIGGER … RENAME` o un `DROP TRIGGER` senza `IF EXISTS` su uno di
# quei nomi passa su un database di sviluppo — dove esistono da settimane — e
# uccide il migrate su un database ricostruito da zero:
#   ERROR: trigger "trg_<vecchio>_audit_data_user_upd" for table "<t>" does not exist
#
# ⭐ E quasi sempre, in quel mondo, l'operazione NON SERVIVA: le automazioni
# lavorano per pattern, quindi alla loro passata genereranno gia' il nome
# giusto. L'operazione e' legittimamente CONDIZIONALE — «rinomina se c'e'» —
# e il modo di dirlo e' un changeSet suo con `onFail: MARK_RAN`.
#
# PERCHE' SERVE UN CANCELLO E NON BASTAVA LA REGOLA. Perche' il changeSet che
# ha rotto la CI il 2026-09-02
# (`20260822-25-rename-compensazioni-in-sistemazioni`) aveva il fatto SCRITTO
# nella propria intestazione — «una tabella nuova non ha i trigger di audit e
# tx_id finche' non passa ci_apply» — due paragrafi sopra il difetto. Sapere la
# regola non basta: mentre si scrive la rinomina si guarda il database che si
# ha davanti, e li' il trigger c'e'.
#
# ⛔ NON si risolve con una preCondition sul changeSet intero: `HALT` sposta
# solo il punto in cui la CI si ferma, e `MARK_RAN` salterebbe anche la
# rinomina della TABELLA, lasciando il database sul nome vecchio in silenzio.
# La forma giusta e' un changeSet per trigger, che fa una cosa sola.
#
# COSA NON VIENE SEGNALATO, e percio' e' la via d'uscita:
#   * un `onFail` diverso da `HALT` (`MARK_RAN`, `CONTINUE`, `WARN`): li' il
#     salto e' la risposta voluta;
#   * `DROP TRIGGER IF EXISTS`;
#   * l'SQL dentro un commento (`--` oppure `/* … */`): il 2026-01-30 un
#     changeSet ha lasciato apposta il blocco commentato, ed e' sano.
#
# ⚠️ LIMITI DICHIARATI:
#   * guarda `changes` e `preConditions`, non i `rollback`: un rollback si
#     esegue a mano e raramente, e il rumore costerebbe piu' della copertura;
#   * riconosce i trigger da due elenchi — i suffissi dei nomi generati e le
#     funzioni-trigger montate dalle automazioni. Un'automazione nuova va
#     aggiunta a `SUFFISSI_AUTOMAZIONE` e/o a `TRGFN_AUTOMAZIONE`, e finche' non
#     la si aggiunge non e' guardata: sono gli elenchi a fare da perimetro;
#
#   * ⛔ `_audit_data_user_INS_upd` NON e' nell'elenco, E NON DEVE ENTRARCI.
#     Chi conta i trigger nel database trova 301 `_audit_data_user_upd` e 12
#     `_audit_data_user_ins_upd`, e la lettura ovvia — «l'elenco e' indietro di
#     dodici» — e' sbagliata. Quei dodici non nascono da `ci_apply`: li scrive
#     A MANO un changeSet, uno per tabella (dbops.processi, coda_lavori,
#     rls_perimetro_debito, sei `vendite.*_componenti`, …), e fanno di piu' del
#     template — INSERT+UPDATE invece del solo UPDATE. Il framework si fa da
#     parte apposta (`exist_strat = BY_FUNCTION`: se un trigger su quella
#     funzione c'e' gia', non ne monta un secondo), ed e' il motivo per cui
#     nessuno dei dodici ha il gemello `_upd`. ⇒ Nascendo da un changeSet,
#     su un database ricostruito da zero ESISTONO GIA' quando qualcuno
#     potrebbe dropparli: il guasto che questo cancello presidia li' non
#     esiste, e allargare l'elenco lo farebbe suonare su un caso legittimo —
#     cioe' la strada per farlo spegnere. Verificato il 2026-09-10.
#   * la faccia (B) segnala solo cio' che interroga `pg_trigger`. Una
#     preCondition che chiedesse le stesse cose per un'altra via — poniamo
#     `pg_get_triggerdef` su un oid gia' noto — le sfuggirebbe. ⛔ NON si e'
#     allargata a «qualunque changeSet che NOMINA una trgfn di automazione»:
#     misurato il 2026-09-02, sarebbero 100+ file, quasi tutti legittimi (chi
#     monta un trigger a mano su quelle funzioni, o chi le scrive). Un cancello
#     con quel tasso di falsi positivi si impara a disattivare.
#
# Uso (read-only, nessun database):
#   python scripts/guardrail_ddl_su_trigger_automazione.py
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
FASI_PRESIDIATE = ("00_schema", "20_code")
FILENAME_RE = re.compile(r"^\d{8}-\d{2}.*\.(ya?ml)$", re.IGNORECASE)

# I suffissi con cui le automazioni battezzano i trigger che generano.
# Misurati sul database il 2026-09-02: 309 audit, 300 tx_id, 121 storico.
SUFFISSI_AUTOMAZIONE = (
    "_audit_data_user_upd",
    "_gen_tx_id_ins_upd",
    "_z90_storico_upd_dlt",
    "_block_deact_upd",
)

# ⭐ Le funzioni-trigger che il framework MONTA, lette dalle `fn_run_automations_*`
# il 2026-09-02. Servono alla faccia (B): una preCondition non nomina il trigger,
# nomina la funzione che ci sta sotto — spesso dentro un `LIKE`, quindi senza il
# prefisso `trgfn_`.
# ⚠️ E' un elenco, quindi e' il perimetro: un'automazione nuova va aggiunta qui.
TRGFN_AUTOMAZIONE = (
    "audit_data_user_generic",
    "child_requires_active_parent",
    "lock_columns",
    "prevent_deactivate_if_children",
    "storico_generic",
    "tx_id_managed",
)

# `ALTER TRIGGER <nome>` e `DROP TRIGGER <nome>` (quest'ultimo solo senza
# IF EXISTS: con IF EXISTS l'assenza e' gia' contemplata).
ALTER_RE = re.compile(r"\bALTER\s+TRIGGER\s+([a-z_][a-z0-9_]*)", re.IGNORECASE)
DROP_RE = re.compile(
    r"\bDROP\s+TRIGGER\s+(?!IF\s+EXISTS\b)([a-z_][a-z0-9_]*)", re.IGNORECASE
)

BLOCCO_COMMENTO_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
RIGA_COMMENTO_RE = re.compile(r"--[^\n]*")

ONFAIL_CHE_FERMA = frozenset({"HALT"})


# Scopo: togliere i commenti, perche' l'SQL commentato non viene eseguito.
def _senza_commenti(sql: str) -> str:
    return RIGA_COMMENTO_RE.sub("", BLOCCO_COMMENTO_RE.sub("", sql))


# Scopo: l'`onFail` dichiarato dal blocco preConditions (default: HALT).
def _on_fail(pre) -> str:
    if isinstance(pre, list):
        for voce in pre:
            if isinstance(voce, dict) and "onFail" in voce:
                return str(voce["onFail"]).strip().upper()
    elif isinstance(pre, dict) and "onFail" in pre:
        return str(pre["onFail"]).strip().upper()
    return "HALT"


# Scopo: raccoglie l'SQL dei `sqlCheck` delle preCondition, con l'atteso.
def _sql_check(pre) -> list[tuple[str, str]]:
    fuori: list[tuple[str, str]] = []

    def cammina(nodo) -> None:
        if isinstance(nodo, dict):
            valore = nodo.get("sqlCheck")
            if isinstance(valore, dict):
                atteso = str(valore.get("expectedResult", "")).strip().strip("'\"")
                fuori.append((str(valore.get("sql", "")), atteso))
            for v in nodo.values():
                cammina(v)
        elif isinstance(nodo, list):
            for v in nodo:
                cammina(v)

    cammina(pre)
    return fuori


# Scopo: raccoglie l'SQL delle `changes` di un changeSet.
def _sql_delle_changes(cs: dict) -> list[str]:
    fuori: list[str] = []
    for change in cs.get("changes", []) or []:
        if not isinstance(change, dict):
            continue
        blocco = change.get("sql")
        if isinstance(blocco, dict) and isinstance(blocco.get("sql"), str):
            fuori.append(blocco["sql"])
    return fuori


# Scopo: elenca le violazioni (file, changeSet, verbo, trigger).
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
            if "TRIGGER" not in testo.upper():
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
                # Un changeSet che si SEGNA invece di fallire ha gia' dichiarato
                # che l'oggetto puo' non esserci: e' la forma corretta.
                if _on_fail(cs.get("preConditions")) not in ONFAIL_CHE_FERMA:
                    continue
                cs_id = str(cs.get("id", "<senza id>"))
                for sql in _sql_delle_changes(cs):
                    pulito = _senza_commenti(sql)
                    for verbo, regex in (("ALTER TRIGGER", ALTER_RE),
                                         ("DROP TRIGGER", DROP_RE)):
                        for nome in regex.findall(pulito):
                            if nome.lower().endswith(SUFFISSI_AUTOMAZIONE):
                                fuori.append((rel, cs_id, verbo, nome))
                # (B) una preCondition che CONTA quei trigger e ne pretende un
                #     numero. `expectedResult: 0` resta lecito: un database senza
                #     automazioni applicate lo soddisfa.
                for sql, atteso in _sql_check(cs.get("preConditions")):
                    if atteso == "0":
                        continue
                    pulito = _senza_commenti(sql).lower()
                    if "pg_trigger" not in pulito:
                        continue
                    marcatori = [m for m in TRGFN_AUTOMAZIONE + SUFFISSI_AUTOMAZIONE
                                 if m in pulito]
                    if marcatori:
                        fuori.append((rel, cs_id, "preCondition sqlCheck",
                                      ", ".join(sorted(set(marcatori)))))
    return fuori


# Scopo: eseguire il controllo e tradurre l'esito in exit code per la CI.
def main() -> int:
    violazioni = trova_violazioni()
    if not violazioni:
        print(
            "✅ guardrail DDL/trigger-automazione: nessuna DDL incondizionata su "
            f"trigger generati da ci_apply in {' / '.join(FASI_PRESIDIATE)}"
        )
        return 0

    print(
        f"❌ guardrail DDL/trigger-automazione: {len(violazioni)} istruzioni "
        "toccano un trigger che nasce da ci_apply, senza contemplarne l'assenza.\n"
        "   Su un database ricostruito da zero quel trigger non esiste ancora e il\n"
        "   migrate muore con «trigger ... does not exist».\n",
        file=sys.stderr,
    )
    for rel, cs_id, verbo, nome in violazioni:
        print(f"  · {rel}", file=sys.stderr)
        print(f"      changeSet: {cs_id}", file=sys.stderr)
        print(f"      istruzione: {verbo} {nome}", file=sys.stderr)
    print(
        "\n   Rimedio (preCondition): TOGLIERLA. Cio' che voleva difendere e' un\n"
        "   presidio pgTAP, che gira a `ci_apply` avvenuto — spesso c'e' gia'.\n"
        "\n   Rimedio (DDL): portare QUELLA SOLA istruzione in un changeSet suo, con\n"
        "   `preConditions: onFail: MARK_RAN` + un `sqlCheck` su pg_trigger che\n"
        "   chiede se il trigger c'e'. Cosi' si rinomina dove serve e ci si segna\n"
        "   dove non serve.\n"
        "   ⛔ NON una preCondition sul changeSet intero: `MARK_RAN` salterebbe\n"
        "   anche il resto — la rinomina della tabella, per dire — in silenzio.\n"
        "   Un `DROP TRIGGER` puo' invece bastarsi con `IF EXISTS`.\n"
        "   Regola: docs/it/linee-guida-sql.md §11.5",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
