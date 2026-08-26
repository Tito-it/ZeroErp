#!/usr/bin/env python3
import sys, subprocess, re, itertools


REQUIRED = "Copyright (C)"
EXTS = re.compile(r".*\.(py|js|vue|ya?ml)$")
EXCLUDE = re.compile(r"^docs/")

# Prendi i file in staging.
# ⛔ `AC` (aggiunti, copiati) e NON `ACM` — corretto il 2026-08-26, il giorno in
#    cui questo hook ha girato per la PRIMA volta (`pre-commit` non era
#    installato su nessuna macchina, quindi la configurazione esisteva e non
#    presidiava niente).
#    Con la `M` l'hook chiedeva l'header a ogni file TOCCATO, cioe' applicava
#    retroattivamente una regola che AGENTS.md scrive per i file NUOVI:
#    «Per ogni nuovo file Python … aggiungere l'header standard».
#    ⚠️ E la differenza non e' teorica: misurati lo stesso giorno, **2042 file
#    su 5189** non hanno l'header — il 39% del repo, e **579 su 605** sotto
#    `frontend/src`. Con la `M` qualunque lavoro sul frontend sarebbe stato
#    bloccato dal primo commit, e la reazione ovvia sarebbe stata spegnere
#    l'hook: un presidio che blocca tutto viene disattivato, e allora non
#    presidia piu' nemmeno i casi per cui era nato.
#    ⭐ Cosi' invece resta un CRICCHETTO: i file nuovi nascono in regola, il
#    pregresso non blocca nessuno. Quei 2042 sono un registro del debito, e
#    come tutti i registri deve calare — ma per decisione, non per attrito.
files = subprocess.check_output(
    ["git", "diff", "--cached", "--name-only", "--diff-filter=AC"]
).decode().splitlines()

status = 0
for f in files:
    if not EXTS.match(f): 
        continue
    if EXCLUDE.match(f): 
        continue
    try:
        with open(f, encoding="utf-8") as fp:
            head = list(itertools.islice(fp, 10))
    except FileNotFoundError:
        continue
    if not any(REQUIRED in line for line in head):
        print(f" Errore: manca l’header di licenza in {f}")
        status = 1

if status:
    print("\nCommit annullato: aggiungi l’header di licenza ai file indicati.")
    sys.exit(1)
sys.exit(0)
