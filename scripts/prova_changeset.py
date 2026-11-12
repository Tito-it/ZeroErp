#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Prova l'SQL ESTRATTO da uno o piu' changeSet in una transazione
#        che finisce in ROLLBACK, sullo scratch, da solo o in testa a un
#        pgTAP. Non applica niente e non scrive nel databasechangelog.
#
# ── PERCHE' ESISTE ───────────────────────────────────────────────────
#   Una prova che ricopia a mano l'SQL di un changeSet prova la copia: si
#   ricopia la DDL e si saltano `COMMENT ON`, `GRANT`, i blocchi `DO`, cioe'
#   i pezzi su cui il migrate poi si ferma. Qui i blocchi `changes[].sql`
#   si leggono dallo YAML e si eseguono interi, nell'ordine dato.
#
#   La transazione non si compone a mano nella shell. Un `echo BEGIN;` in
#   una pipe perde il `;`, la transazione non si apre e la DDL va in
#   autocommit senza che nessun errore lo dica. Il file si scrive su disco,
#   se ne controlla la prima istruzione e si lancia con ON_ERROR_STOP.
#
# ── COSA FA, NELL'ORDINE ─────────────────────────────────────────────
#   1. legge gli YAML: i change `sql` diventano l'estratto; ogni altro
#      tipo di change (`createTable`, `addColumn`, `loadUpdateData`, ...)
#      viene DICHIARATO come non coperto, e l'esito e' «prova parziale»;
#   2. esegue le `sqlCheck` delle preConditions in sola lettura e ne
#      confronta il risultato con `expectedResult` (vedi il limite sotto);
#   3. controlla che sul database non ci siano altre sessioni: l'estratto
#      tiene lock di catalogo fino al ROLLBACK, e una corsa di pgTAP in
#      volo puo' restare ferma o morire di deadlock;
#   4. fotografa il catalogo, lancia la prova, lo rifotografa: se e'
#      cambiato, qualcosa e' stato committato (dalla prova o da una
#      migrazione arrivata nel frattempo) e lo dice;
#   5. con `--pgtap`, per ogni file fa due corse — SENZA e CON l'estratto —
#      e confronta gli `ok` / `not ok`: il verdetto e' la differenza.
#
# ── COME E' FATTA LA TRANSAZIONE DI PROVA ────────────────────────────
#   BEGIN;
#   SET LOCAL myapp.logconn = '';                -- il log degli errori via
#   SET LOCAL myapp.dblink_log_connection = '';  -- dblink apre una seconda
#       -- sessione: con una DDL o un upsert sui registri degli errori in
#       -- questa transazione le due si aspettano a vicenda, per sempre.
#   SET CONSTRAINTS ALL DEFERRED;   -- come Liquibase: un UPDATE che accoda
#       -- trigger differiti seguito da un ALTER TABLE deve fallire qui,
#       -- non all'apply.
#   <estratto>
#   ROLLBACK;
#   In testa a un pgTAP l'estratto entra subito dopo la riga `BEGIN;` del
#   test, che deve essere UNA sola (un `-- BEGIN; ...` in un commento non
#   conta, ed e' il motivo per cui si cerca la riga intera).
#
# ── ⚠️ I LIMITI, DA DICHIARARE NEL BRIEF ─────────────────────────────
#   * Gira da OWNER: la DDL lo pretende. Da owner la row security non si
#     applica, quindi i test di perimetro sono rossi per costruzione nelle
#     due corse. L'esito come applicazione arriva dopo l'apply.
#   * Le preConditions si leggono sul database della prova. Quella che
#     conta e' la risposta del database che incontrera' il changeSet: se
#     lo scratch e' a un punto diverso, la risposta puo' differire.
#   * Su uno scratch vuoto un confronto prima/dopo sui dati e' a zero per
#     sottrazione: l'equivalenza di un corpo nuovo si prova coi casi
#     costruiti in un pgTAP.
#   * Un `loadUpdateData` non ha SQL da estrarre: la sua prova e' il render
#     offline di Liquibase, che questo script non fa.
#   * Un upsert COMPLETO di un CSV dei registri degli errori non si prova
#     insieme a un pgTAP: va in una corsa sua.
#
# Uso:
#   scripts/prova_changeset.py db/changelog/migrations_v2/20_code/x/2026…yaml
#   scripts/prova_changeset.py a.yaml b.yaml --pgtap db/pgtap/x/test-y.sql
#   scripts/prova_changeset.py a.yaml --solo-estratto      # stampa e basta
#   scripts/prova_changeset.py a.yaml --env db/internal.env  # altro database
#
# Codici di uscita: 0 verde · 1 rosso · 2 prova parziale o non lanciata.
# ------------------------------------------------------------

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _yaml_veloce import carica as carica_yaml

RADICE = Path(__file__).resolve().parent.parent
ENV_SCRATCH = "db/internal.ruoli.env"
TESTA = (
    "SET LOCAL myapp.logconn = '';\n"
    "SET LOCAL myapp.dblink_log_connection = '';\n"
    "SET CONSTRAINTS ALL DEFERRED;\n"
)
RIGA_BEGIN = re.compile(r"^BEGIN;[ \t]*$", re.M)
RIGA_ROLLBACK = re.compile(r"^ROLLBACK;[ \t]*$", re.M)
# Impronta del catalogo: cambia se una qualunque riga di questi cataloghi e'
# stata scritta e committata fra le due letture.
IMPRONTA = """
SELECT md5(string_agg(t, '|' ORDER BY t)) FROM (
  SELECT 'proc:'  || count(*) || ':' || coalesce(max(xmin::text::bigint), 0) AS t FROM pg_proc
  UNION ALL SELECT 'class:' || count(*) || ':' || coalesce(max(xmin::text::bigint), 0) FROM pg_class
  UNION ALL SELECT 'attr:'  || count(*) || ':' || coalesce(max(xmin::text::bigint), 0) FROM pg_attribute
  UNION ALL SELECT 'trg:'   || count(*) || ':' || coalesce(max(xmin::text::bigint), 0) FROM pg_trigger
  UNION ALL SELECT 'pol:'   || count(*) || ':' || coalesce(max(xmin::text::bigint), 0) FROM pg_policy
  UNION ALL SELECT 'con:'   || count(*) || ':' || coalesce(max(xmin::text::bigint), 0) FROM pg_constraint
  UNION ALL SELECT 'desc:'  || count(*) || ':' || coalesce(max(xmin::text::bigint), 0) FROM pg_description
  UNION ALL SELECT 'log:'   || count(*) FROM databasechangelog
) s
"""
ALTRE_SESSIONI = """
SELECT pid || ' ' || usename || ' ' || state || ' ' || left(regexp_replace(query, '\\s+', ' ', 'g'), 70)
  FROM pg_stat_activity
 WHERE datname = current_database() AND pid <> pg_backend_pid()
   AND backend_type = 'client backend' AND state <> 'idle'
"""


def leggi_env(percorso: Path) -> dict[str, str]:
    env = {}
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if riga and not riga.startswith("#") and "=" in riga:
            k, v = riga.split("=", 1)
            env[k.removeprefix("export ").strip()] = v.strip().strip("'\"")
    return env


def psql(env: dict[str, str], *args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["psql", "--no-psqlrc", "-X", "-At", "-v", "ON_ERROR_STOP=1", *args],
        env=env, capture_output=True, text=True, timeout=timeout,
    )


def _sql_check(nodo, trovate: list[dict]) -> None:
    """Raccoglie le sqlCheck a qualunque profondita' (dentro and / or / not)."""
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            if k == "sqlCheck" and isinstance(v, dict):
                trovate.append(v)
            else:
                _sql_check(v, trovate)
    elif isinstance(nodo, list):
        for x in nodo:
            _sql_check(x, trovate)


def estrai(percorso: Path) -> tuple[str, list[dict], list[str], list[str]]:
    """Ritorna (estratto, sqlCheck, change non coperti, avvisi) di un file."""
    doc = carica_yaml(percorso.read_text(encoding="utf-8")) or {}
    pezzi, checks, scoperti, avvisi = [], [], [], []
    for voce in doc.get("databaseChangeLog", []):
        cs = voce.get("changeSet") if isinstance(voce, dict) else None
        if not cs:
            continue
        ident = cs.get("id", "?")
        if cs.get("runInTransaction") is False:
            avvisi.append(f"{ident}: runInTransaction false — in transazione non si prova com'e'")
        _sql_check(cs.get("preConditions"), checks)
        for change in cs.get("changes") or []:
            for tipo, corpo in change.items():
                if tipo == "sql":
                    testo = corpo.get("sql") if isinstance(corpo, dict) else corpo
                    if not isinstance(testo, str) or not testo.strip():
                        scoperti.append(f"{ident}: change sql senza testo")
                        continue
                    testo = testo.rstrip()
                    if not testo.endswith(";"):
                        testo += ";"
                    pezzi.append(f"-- ── {ident} ──\n{testo}\n")
                else:
                    scoperti.append(f"{ident}: {tipo}")
    return "\n".join(pezzi), checks, scoperti, avvisi


def conta_tap(testo: str) -> tuple[int, int, list[str]]:
    ok = len(re.findall(r"^ok \d+", testo, re.M))
    rossi = re.findall(r"^not ok \d+.*$", testo, re.M)
    return ok, len(rossi), rossi


def lancia(env, sql: str, cartella: Path, nome: str) -> tuple[subprocess.CompletedProcess, Path]:
    f = cartella / nome
    f.write_text(sql, encoding="utf-8")
    # Si controlla il file che si sta per eseguire, non l'intenzione.
    prima = next((r.strip() for r in sql.splitlines()
                  if r.strip() and not r.strip().startswith("--")), "")
    if prima != "BEGIN;":
        raise SystemExit(f"⛔ {f}: la prima istruzione non e' BEGIN; ({prima[:40]!r}). Non lancio.")
    if not RIGA_ROLLBACK.search(sql):
        raise SystemExit(f"⛔ {f}: manca la riga ROLLBACK;. Non lancio.")
    return psql(env, "-f", str(f)), f


def coda(testo: str, n: int = 25) -> str:
    righe = [r for r in testo.strip().splitlines() if r.strip()]
    return "\n".join("    " + r for r in righe[-n:])


def main() -> int:
    ap = argparse.ArgumentParser(description="Prova l'SQL estratto di uno o piu' changeSet, in ROLLBACK.")
    ap.add_argument("changeset", nargs="+", type=Path, help="file YAML, nell'ordine di esecuzione")
    ap.add_argument("--pgtap", action="append", default=[], type=Path, help="pgTAP da correre senza e con l'estratto")
    ap.add_argument("--env", default=ENV_SCRATCH, help=f"env file del database (default {ENV_SCRATCH})")
    ap.add_argument("--solo-estratto", action="store_true", help="stampa l'estratto e le preConditions, non lancia")
    ap.add_argument("--anche-se-occupato", action="store_true", help="lancia anche con altre sessioni attive")
    ap.add_argument("--tieni", action="store_true", help="non cancella i file di prova")
    a = ap.parse_args()

    estratti, checks, scoperti, avvisi = [], [], [], []
    for p in a.changeset:
        if not p.is_file():
            print(f"⛔ {p}: file non trovato", file=sys.stderr)
            return 2
        e, c, s, w = estrai(p)
        estratti.append(e)
        checks += [(p.name, x) for x in c]
        scoperti += s
        avvisi += w
    estratto = "\n".join(x for x in estratti if x)

    for w in avvisi:
        print(f"⚠️  {w}")
    if scoperti:
        print("⚠️  Change NON coperti da questa prova (non sono SQL da estrarre):")
        for s in scoperti:
            print(f"     {s}")
    if not estratto:
        print("⛔ Nessun change `sql` da provare.")
        return 2

    if a.solo_estratto:
        print(estratto)
        for nome, c in checks:
            print(f"-- preCondition di {nome} — attesa {c.get('expectedResult')!r}:\n{c.get('sql')}")
        return 2 if scoperti else 0

    env_file = RADICE / a.env
    if not env_file.is_file():
        print(f"⛔ env file {a.env} assente", file=sys.stderr)
        return 2
    env = {**os.environ, **leggi_env(env_file), "PGCONNECT_TIMEOUT": "8"}

    chi = psql(env, "-c", "SELECT current_database() || ' come ' || current_user", timeout=30)
    if chi.returncode != 0:
        print(f"⛔ database non raggiungibile: {chi.stderr.strip()}", file=sys.stderr)
        return 2
    print(f"Database: {chi.stdout.strip()}  (env {a.env})")
    if a.env != ENV_SCRATCH:
        print("⚠️  NON e' lo scratch: la transazione finisce in ROLLBACK, ma i lock di catalogo "
              "restano presi per tutta la prova.")

    rosso = False
    if checks:
        print(f"preConditions ({len(checks)} sqlCheck) lette su questo database:")
    for nome, c in checks:
        atteso = str(c.get("expectedResult"))
        r = psql(env, "-c", "BEGIN READ ONLY", "-c", str(c.get("sql")), "-c", "ROLLBACK", timeout=120)
        avuto = [x for x in r.stdout.strip().splitlines() if x not in ("BEGIN", "ROLLBACK")]
        avuto = avuto[-1] if avuto else ""
        if r.returncode != 0:
            print(f"  ⛔ {nome}: errore — {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else '?'}")
            rosso = True
        elif avuto == atteso:
            print(f"  ✅ {nome}: {avuto}")
        else:
            print(f"  ⚠️  {nome}: attesa {atteso!r}, avuto {avuto!r} — qui il changeSet NON girerebbe "
                  f"(da leggere sul database che lo incontrera')")

    occ = psql(env, "-c", ALTRE_SESSIONI, timeout=30)
    if occ.stdout.strip():
        print("Altre sessioni attive sul database:")
        print(coda(occ.stdout))
        if not a.anche_se_occupato:
            print("⛔ Non lancio: l'estratto tiene lock di catalogo fino al ROLLBACK. "
                  "Si aspetta, o --anche-se-occupato.")
            return 2

    prima = psql(env, "-c", IMPRONTA, timeout=60).stdout.strip()

    with tempfile.TemporaryDirectory(prefix="prova_changeset_") as tmp:
        cartella = Path(tmp)
        if a.tieni:
            cartella = Path(tempfile.mkdtemp(prefix="prova_changeset_"))
            print(f"File di prova in {cartella}")

        r, _ = lancia(env, f"BEGIN;\n{TESTA}\n{estratto}\nROLLBACK;\n", cartella, "estratto.sql")
        if r.returncode != 0:
            rosso = True
            print("⛔ ESTRATTO: errore")
            print(coda(r.stderr or r.stdout))
        else:
            print("✅ ESTRATTO: eseguito per intero, poi ROLLBACK")
            avv = [x for x in r.stderr.splitlines() if "WARNING" in x or "ATTENZIONE" in x]
            if avv:
                print(f"   {len(avv)} avvisi, i primi:")
                print(coda("\n".join(avv[:5])))

        for t in a.pgtap:
            if not t.is_file():
                print(f"⛔ pgTAP {t}: file non trovato")
                rosso = True
                continue
            testo = t.read_text(encoding="utf-8")
            trovati = RIGA_BEGIN.findall(testo)
            if len(trovati) != 1:
                print(f"⛔ pgTAP {t.name}: {len(trovati)} righe `BEGIN;` — ne serve una sola. Non lo lancio.")
                rosso = True
                continue
            m = RIGA_BEGIN.search(testo)
            con = testo[:m.end()] + "\n" + TESTA + "\n" + estratto + "\n" + testo[m.end():]
            rs, _ = lancia(env, testo, cartella, f"senza__{t.name}")
            rc, _ = lancia(env, con, cartella, f"con__{t.name}")
            ok_s, ko_s, rossi_s = conta_tap(rs.stdout)
            ok_c, ko_c, rossi_c = conta_tap(rc.stdout)
            morto_s, morto_c = rs.returncode != 0, rc.returncode != 0
            nuovi = [x for x in rossi_c if x not in rossi_s]
            esito = "✅" if not nuovi and not morto_c and ok_c >= ok_s else "⛔"
            print(f"{esito} pgTAP {t.name}: senza {ok_s} ok / {ko_s} not ok"
                  f"{' (interrotto)' if morto_s else ''} → con {ok_c} ok / {ko_c} not ok"
                  f"{' (interrotto)' if morto_c else ''}")
            if esito == "⛔":
                rosso = True
                for x in nuovi[:15]:
                    print(f"     nuovo rosso: {x}")
                if morto_c:
                    print("   La corsa CON l'estratto si e' interrotta:")
                    print(coda(rc.stderr, 12))
            if ko_s and not nuovi:
                print(f"   ⚠️  {ko_s} rossi gia' presenti senza l'estratto: da owner i test di "
                      f"perimetro lo sono per costruzione, gli altri vanno spiegati.")

    dopo = psql(env, "-c", IMPRONTA, timeout=60).stdout.strip()
    if prima != dopo:
        rosso = True
        print("⛔ Il CATALOGO e' cambiato durante la prova. O la prova ha committato qualcosa, "
              "o e' arrivata una migrazione: si legge il databasechangelog e si rileggono "
              "gli oggetti toccati prima di fidarsi di questo esito.")
    else:
        print("Catalogo identico prima e dopo: niente e' rimasto sul database.")

    if rosso:
        return 1
    if scoperti:
        print("Esito: PROVA PARZIALE — i change elencati in testa non sono stati provati.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
