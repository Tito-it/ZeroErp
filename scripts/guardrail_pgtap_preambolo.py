#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
# Scopo: presidiare le invarianti di PREAMBOLO dei test pgTAP.
#   Guida: docs/it/guide/pgtap-come-si-scrive-un-test.md
#   Storia: docs/it/dev/work-done/brief-db-pgtap-runner-rls-baseline.md
#
# COSA PRESIDIA, e perche' proprio queste. Sono le tre righe che costano tre
# giorni quando mancano, e che si verificano con un grep — cioe' le uniche
# adatte a un cancello:
#
#   A) BEGIN;                       -> senza, un fallimento a meta' lascia
#      residui che rompono la corsa successiva, che vede un rosso non suo;
#   B) SET CONSTRAINTS ALL IMMEDIATE-> senza, i 365 vincoli DIFFERITI non
#      scattano mai (il COMMIT non arriva): verde per sottrazione;
#   C) contesto applicativo         -> senza, con la RLS attiva le SELECT della
#      fixture leggono ZERO righe e le asserzioni finiscono nei rami `skip`.
#
# ⚠️ Le esclusioni esistono, e devono essere DICHIARATE nel file — non spiegate
# in prosa e basta. Una ragione in prosa non e' leggibile da un cancello, e
# soprattutto non distingue «escluso apposta» da «dimenticato»:
#     -- pgtap-contesto: escluso — <perche>
#     -- pgtap-differiti: escluso — <perche>
# E' lo stesso schema del marcatore `pgtap-runner`, per la stessa ragione:
# l'eccezione sta accanto al test e porta la sua motivazione.
#
# ⛔ COSA NON PRESIDIA, ed e' deliberato:
#
#   * `LIMIT 1` senza `ORDER BY` — meta' delle occorrenze sono su temp table
#     costruite dal test, dove il LIMIT non sceglie niente. Un cancello con
#     quel tasso di falsi positivi si impara a disattivare. Resta una LENTE:
#     scripts/censimento_limit1.py;
#   * la correttezza delle asserzioni — non e' greppabile, e fingere di
#     presidiarla darebbe una falsa sicurezza.
#
# ⚠️ IL DEBITO SI PRESIDIA A SOGLIA, NON A DIVIETO. `throws_ok(sql, NULL, NULL)`
# accetta qualunque errore ed e' un difetto vero (misurato il 2026-08-07: tre
# test VERDI collaudavano una cosa diversa da quella che dichiaravano). Ma sono
# 137 occorrenze: vietarle oggi renderebbe il cancello rosso al primo giro, e un
# cancello rosso il primo giorno non nasce mai. Quindi si chiude il RUBINETTO —
# la soglia puo' solo CALARE — che e' lo stesso schema usato per i codici fuori
# convenzione (57 -> 1) e per il registro delle policy (141 -> 0).
#
# Uso:
#   python3 scripts/guardrail_pgtap_preambolo.py          # esito + dettaglio
#   python3 scripts/guardrail_pgtap_preambolo.py --soglia # ristampa la soglia
#
# Exit: 0 tutto a posto · 1 almeno una violazione
# ------------------------------------------------------------
import re
import sys
import pathlib

RADICE = pathlib.Path(__file__).resolve().parent.parent / "db" / "pgtap"

# Soglia del debito: numero di `throws_ok` senza discriminante ammessi.
# ⚠️ Si abbassa quando se ne sana uno. NON si alza mai: se questo numero deve
#    crescere per far passare la CI, il difetto e' nel test nuovo.
SOGLIA_THROWS_SENZA_DISCRIMINANTE = 131

RX_BEGIN = re.compile(r"^\s*BEGIN\s*;", re.M)
RX_SETC = re.compile(r"SET\s+CONSTRAINTS\s+ALL\s+IMMEDIATE", re.I)
RX_CTX = re.compile(r"fn_pgtap_set_contesto_operatore\s*\(")
RX_CTX_ESCL = re.compile(r"^--\s*pgtap-contesto:\s*escluso\b", re.M)
RX_DIF_ESCL = re.compile(r"^--\s*pgtap-differiti:\s*escluso\b", re.M)
RX_MARK = re.compile(r"^--\s*pgtap-runner:\s*owner\s*$", re.M)
RX_MOTIVO = re.compile(r"^--\s*pgtap-runner-motivo:\s*\S", re.M)
RX_THROWS = re.compile(r"\bthrows_ok\s*\(")


# Scopo: azzerare commenti, stringhe e dollar-quote preservando gli offset,
#   cosi' un `BEGIN;` dentro un commento non conta come transazione aperta.
def maschera(t: str) -> str:
    out = list(t)
    i, n = 0, len(t)

    def blank(a, b):
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        if t.startswith("--", i):
            j = t.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
        elif t[i] == "'":
            j = i + 1
            while j < n:
                if t[j] == "'":
                    if j + 1 < n and t[j + 1] == "'":
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            blank(i, j)
            i = j
        elif t[i] == "$":
            m = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", t[i:])
            if m:
                tag = m.group(0)
                j = t.find(tag, i + len(tag))
                j = n if j < 0 else j + len(tag)
                blank(i, j)
                i = j
            else:
                i += 1
        else:
            i += 1
    return "".join(out)


# Scopo: contare i `throws_ok` che non discriminano — secondo e terzo argomento
#   entrambi NULL, cioe' «va bene qualunque errore».
def throws_senza_discriminante(testo: str, mascherato: str) -> int:
    n = 0
    for mo in RX_THROWS.finditer(mascherato):
        depth, start, args = 0, mo.end(), []
        i = mo.end() - 1
        while i < len(mascherato):
            c = mascherato[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    args.append(testo[start:i])
                    break
            elif c == "," and depth == 1:
                args.append(testo[start:i])
                start = i + 1
            i += 1
        if len(args) >= 3:
            if args[1].strip().upper() == "NULL" and args[2].strip().upper() == "NULL":
                n += 1
    return n


# Scopo: togliere SOLO i commenti di riga. Serve per cercare cose che vivono
#   DENTRO un dollar-quote — la riga di contesto e' `DO $ctx$ BEGIN PERFORM
#   ...; END $ctx$;`, quindi la maschera piena la cancellerebbe. Ci sono cascato
#   scrivendo questo cancello: la prima versione dichiarava 426 file senza
#   contesto quando ce l'hanno tutti tranne 13.
def senza_commenti(t: str) -> str:
    out = []
    for riga in t.split("\n"):
        i = riga.find("--")
        out.append(riga if i < 0 else riga[:i])
    return "\n".join(out)


def main() -> int:
    # ⚠️ `rglob` e non `glob("*/*.sql")`: il glob a un livello solo lasciava
    #   fuori le sottocartelle di schema — al 2026-08-24 erano 16 file, che per
    #   questo non avevano mai ricevuto lo standard di preambolo del
    #   2026-08-07 (contesto operatore) e fallivano tutti sulla RLS senza che
    #   nessun presidio lo dicesse. Stesso difetto, nello stesso giorno, anche
    #   in scripts/pgtap-baseline.sh.
    file = sorted(RADICE.rglob("*.sql"))
    viol, debito = [], 0

    for f in file:
        t = f.read_text(encoding="utf-8", errors="replace")
        m = maschera(t)
        rel = str(f.relative_to(RADICE.parent.parent))

        if not RX_BEGIN.search(m):
            viol.append((rel, "manca `BEGIN;`: un fallimento a meta' lascia residui"))
        if not RX_SETC.search(senza_commenti(t)) and not RX_DIF_ESCL.search(t):
            viol.append((rel, "manca `SET CONSTRAINTS ALL IMMEDIATE`: i vincoli differiti non scattano"))
        if not RX_CTX.search(senza_commenti(t)) and not RX_CTX_ESCL.search(t):
            viol.append((rel, "manca il contesto applicativo, e non dichiara `-- pgtap-contesto: escluso`"))
        # Il marcatore lo pretende gia' il runner a tempo di esecuzione; qui e'
        # statico, cosi' si vede in PR invece che al primo lancio.
        if RX_MARK.search(t) and not RX_MOTIVO.search(t):
            viol.append((rel, "`pgtap-runner: owner` senza `pgtap-runner-motivo`"))

        debito += throws_senza_discriminante(t, m)

    if "--soglia" in sys.argv:
        print(f"throws_ok senza discriminante oggi: {debito} (soglia {SOGLIA_THROWS_SENZA_DISCRIMINANTE})")
        return 0

    print(f"pgTAP preambolo — {len(file)} file esaminati")
    if viol:
        print(f"\n❌ {len(viol)} violazioni:")
        for rel, perche in viol:
            print(f"   {rel}\n      → {perche}")
    else:
        print("✅ preambolo: tutte le invarianti rispettate")

    print(f"\nDebito `throws_ok` senza discriminante: {debito} (soglia {SOGLIA_THROWS_SENZA_DISCRIMINANTE})")
    sforato = debito > SOGLIA_THROWS_SENZA_DISCRIMINANTE
    if sforato:
        print("❌ il debito e' CRESCIUTO. Un throws_ok nuovo deve dichiarare lo SQLSTATE")
        print("   ('P0001' per un errore di dominio) o usare throws_like sulla frase.")
    elif debito < SOGLIA_THROWS_SENZA_DISCRIMINANTE:
        print(f"✅ il debito e' CALATO di {SOGLIA_THROWS_SENZA_DISCRIMINANTE - debito}:")
        print(f"   abbassa SOGLIA_THROWS_SENZA_DISCRIMINANTE a {debito} in questo file.")

    return 1 if (viol or sforato) else 0


if __name__ == "__main__":
    sys.exit(main())
