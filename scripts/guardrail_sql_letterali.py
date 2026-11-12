#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Guardrail CI — letterali SQL non chiusi nei changeSet Liquibase
#
# COSA PRESIDIA, in una riga:
#   «un apostrofo singolo dentro una stringa SQL la CHIUDE, e da li' in poi il
#    changeSet non e' piu' quello che sembra».
#
# PERCHE' ESISTE. Il 2026-08-25 un migrate e' morto su questo:
#
#     COMMENT ON COLUMN vendite.registri_fatturazione_progressivi.ultima_data
#       IS '... un max(data) letto la' sotto un perimetro ristretto ...';
#                                    ^
#   Nel testo italiano scritto senza accenti — `e'`, `gia'`, `piu'`, `perche'`,
#   `la'`, `cioe'`, `puo'`, `pero'`, `cosi'`, `attivita'`, `meta'` — ogni
#   apostrofo va RADDOPPIATO dentro un letterale a quote singole. In quel
#   COMMENT lo erano tutti tranne uno, e Liquibase ha risposto «Unterminated
#   string literal» su un blocco di 1600 caratteri, dove l'occhio non la trova.
#
#   ⚠️ Il difetto vive quasi sempre nei `COMMENT ON` e nei `GRANT`, cioe' nei
#   pezzi che «non sembrano codice» e che una prova a mano ricopia per ultimi —
#   o non ricopia affatto. Vedi la lezione gemella: si verifica l'SQL ESTRATTO
#   dallo YAML, non una copia riscritta.
#
# COME FUNZIONA. Cammina il testo di ogni blocco `sql:` (in `changes` e in
# `rollback`) tenendo conto di:
#   · dollar-quoting  `$function$ ... $function$`  (li' l'apostrofo e' innocuo);
#   · commenti di riga `--`  (li' non conta);
#   · commenti a blocco `/* ... */`, che in PostgreSQL SI ANNIDANO;
#   · raddoppio `''` dentro un letterale.
# Se un letterale `'` non si chiude entro la fine del blocco, e' una violazione.
#
# ⚠️ I COMMENTI A BLOCCO NON SONO UN DETTAGLIO. La prima stesura non li
#   gestiva, «tanto nei blocchi sql non compaiono»: falso, e misurato subito —
#   `20251026-01-create-fn-guard-sorgente-polimorfa` si apre con un `/* ... */`
#   che contiene `l'esistenza`. Quell'apostrofo apriva un letterale fantasma,
#   il tokenizer perdeva il passo per 3900 caratteri e accusava un COMMENT
#   perfettamente sano 120 righe piu' in basso. ⛔ Un cancello che sbaglia cosi'
#   viene spento dopo due segnalazioni, e un presidio spento e' peggio di uno
#   assente.
#
# ⚠️ COSA NON PRESIDIA, e va detto perche' non dia falsa sicurezza:
#   · un letterale chiuso ma nel punto SBAGLIATO (`'e' cosi''` si chiude subito
#     e il resto diventa sintassi): quello lo prende solo il parser di
#     PostgreSQL, cioe' eseguire il blocco in una transazione con ROLLBACK;
#   · le stringhe con escape `E'...\\''`, che nel repo non si usano;
#   · tutto cio' che non e' un blocco `sql:` (loadData, addColumn, ...).
#   Resta un cancello a costo zero che prende LA classe che ha rotto un migrate.
#
# Uso (read-only, nessun database):
#   python scripts/guardrail_sql_letterali.py            # tutto migrations_v2
#   python scripts/guardrail_sql_letterali.py <path>...  # solo questi file
# Exit 0 se pulito, 1 se trova letterali non chiusi.
# ------------------------------------------------------------

from __future__ import annotations

import sys
from pathlib import Path

import yaml

# ⭐ Il parser YAML in C dove c'e', quello in puro Python dove non c'e'.
#   Il 99% del costo di questo cancello e' il parsing (misurato il
#   2026-09-10): ~14x. Stesso risultato, provato su tutti i changelog del
#   repo — vedi scripts/_yaml_veloce.py.
#   ⚠️ `yaml` resta importato: serve per `yaml.YAMLError` nei rami di errore.
# ⭐ Lettura dei changelog e primitive lessicali in un posto solo
#   (scripts/_guardrail_comune.py).
import _guardrail_comune as gc


# Le forme tronche dell'italiano senza accento: sono la sorgente pratica del
# difetto, e nominarle nel messaggio d'errore fa risparmiare la ricerca.
TRONCHE = ("e'", "gia'", "piu'", "perche'", "cioe'", "puo'", "la'", "li'",
           "pero'", "cosi'", "gia'", "sara'", "meta'", "attivita'", "identita'",
           "verita'", "qualita'", "citta'", "puo'", "sta'")


# Scopo: estrae i blocchi SQL testuali di un changelog, con la loro provenienza
#        (changes | rollback) per poterla nominare nell'errore.
def blocchi_sql(percorso: Path) -> list[tuple[str, str]]:
    fuori: list[tuple[str, str]] = []
    for cs in gc.changeset(percorso):
        fuori.extend(gc.blocchi_sql(cs, ("changes", "rollback")))
    return fuori


def letterali_non_chiusi(sql: str) -> list[tuple[int, str]]:
    i, n = 0, len(sql)
    while i < n:
        if sql.startswith("--", i):  # commento di riga: fino a capo
            fine = sql.find("\n", i)
            i = n if fine < 0 else fine
            continue
        if sql.startswith("/*", i):
            # ⚠️ I commenti a blocco SI ANNIDANO, e dentro un commento un
            #    apostrofo non apre niente (gc.fine_commento_blocco).
            f = gc.fine_commento_blocco(sql, i)
            if not f.chiuso:
                return [(sql.count("\n", 0, i) + 1, "commento /* non chiuso")]
            i = f.pos
            continue
        if sql[i] == "$":
            dq = gc.dollar_quote(sql, i)
            if dq:
                tag, f = dq
                if not f.chiuso:
                    return [(sql.count("\n", 0, i) + 1, f"dollar-quote {tag} non chiuso")]
                i = f.pos
                continue
        if sql[i] == "'":
            f = gc.fine_letterale(sql, i)
            if not f.chiuso:
                return [(sql.count("\n", 0, i) + 1, "letterale ' aperto e mai chiuso")]
            i = f.pos
            continue
        i += 1
    return []


def main() -> int:
    percorsi = gc.file_changelog(sys.argv[1:], None)
    violazioni: list[tuple[str, str, int, str, str]] = []
    esaminati = 0

    for percorso in percorsi:
        try:
            blocchi = blocchi_sql(percorso)
        except yaml.YAMLError as exc:
            print(f"❌ YAML illeggibile: {percorso}\n   {exc}", file=sys.stderr)
            return 1
        esaminati += 1
        for sezione, sql in blocchi:
            for riga, motivo in letterali_non_chiusi(sql):
                righe = sql.split("\n")
                estratto = righe[riga - 1].strip() if riga <= len(righe) else ""
                rel = gc.rel(percorso)
                violazioni.append((rel, sezione, riga, motivo, estratto[:150]))

    if not violazioni:
        print(f"✅ guardrail letterali SQL: {esaminati} changelog esaminati, "
              "nessun letterale aperto e non chiuso")
        return 0

    print("❌ letterale SQL non chiuso in un changeSet\n", file=sys.stderr)
    for rel, sezione, riga, motivo, estratto in violazioni:
        print(f"  {rel}  [{sezione}]", file=sys.stderr)
        print(f"      riga ~{riga} del blocco sql: {motivo}", file=sys.stderr)
        print(f"      → {estratto}", file=sys.stderr)
    print(
        "\nDentro un letterale a quote singole ogni apostrofo va RADDOPPIATO.\n"
        "Nel testo italiano scritto senza accenti la sorgente e' quasi sempre\n"
        "una forma tronca: " + ", ".join(f"`{t}`" for t in sorted(set(TRONCHE))[:10]) + ", ...\n"
        "\n"
        "COSA FARE: cerca nel blocco l'apostrofo singolo e raddoppialo\n"
        "(`la'` -> `la''`). ⭐ Meglio ancora: riformula la frase in modo che\n"
        "l'apostrofo non ci sia — cosi' la trappola non si ripresenta al\n"
        "prossimo che rilegge.\n"
        "\n"
        "⚠️  Questo cancello prende SOLO il letterale che non si chiude mai.\n"
        "    Un letterale chiuso nel punto sbagliato lo vede solo PostgreSQL:\n"
        "    prima di consegnare, esegui l'SQL ESTRATTO dallo YAML (non una\n"
        "    copia riscritta a mano) dentro BEGIN; ... ROLLBACK; — e' l'unica\n"
        "    prova che copre anche COMMENT e GRANT.\n"
        "\n"
        "Storia: il migrate del 2026-08-25 e' morto su un `la'` dentro un\n"
        "COMMENT ON COLUMN di 1600 caratteri.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
