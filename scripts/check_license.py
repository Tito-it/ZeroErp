#!/usr/bin/env python3
import itertools
import os
import re
import subprocess
import sys

REQUIRED = "Copyright (C)"
EXTS = re.compile(r".*\.(py|js|vue|ya?ml)$")
EXCLUDE = re.compile(r"^docs/")

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
DIFF_FILTER = "--diff-filter=AC"


# Scopo: Ricava l'elenco dei file AGGIUNTI da controllare, e da DOVE lo ha
#        ricavato — il secondo valore serve a stampare cosa e' stato misurato,
#        perche' un verde che non dice su cosa e' un verde illeggibile.
#
# 🔴 PERCHE' QUESTA FUNZIONE ESISTE (2026-09-09). Fino a oggi l'elenco veniva
#    SOLO da `git diff --cached`, cioe' dall'indice staged, e lo script non
#    leggeva mai `sys.argv`. In CI un indice staged NON esiste: dopo un checkout
#    pulito `git diff --cached` e' vuoto per costruzione.
#    ⇒ `ci-validate.yaml` lancia `pre-commit run --from-ref … --to-ref …`, quindi
#    l'hook riceveva i nomi dei file cambiati e li IGNORAVA, vedeva zero file e
#    passava. **E' stato verde in ogni corsa di CI da sempre, per il motivo
#    sbagliato** — provato sul commit `693e4b258`, che aggiunge
#    `frontend/src/core/composables/useSelezioneToggle.js` senza header: Passed.
#    ⭐ E' il §6 punto 5 della guida sui presidi: *un cancello che passa perche'
#    non ha misurato niente e' peggio di un cancello assente*.
def elenco_da_controllare() -> tuple[list[str], str]:
    # 1) Modalita' RANGE — e' quella della CI. pre-commit esporta le due
    #    variabili SOLO quando riceve `--from-ref`/`--to-ref` (verificato nel suo
    #    `commands/run.py`), quindi la loro presenza e' un discriminante
    #    affidabile e non un'euristica sul contesto.
    frm = os.environ.get("PRE_COMMIT_FROM_REF")
    to = os.environ.get("PRE_COMMIT_TO_REF")
    if frm and to:
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", DIFF_FILTER, frm, to],
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            # ⚠️ Non dovrebbe accadere: pre-commit risolve lo stesso range per
            #    costruire l'elenco dei file, quindi se fosse irrisolvibile
            #    fallirebbe prima lui. Se accade, si DICHIARA invece di passare
            #    in silenzio — che e' il difetto che questa funzione ripara.
            print(
                f"⚠️  Header di licenza: range {frm}..{to} non risolvibile — "
                "il controllo NON ha misurato niente.",
                file=sys.stderr,
            )
            return [], "range non risolvibile"
        return out.decode().splitlines(), f"range {frm[:8]}..{to[:8]}"

    # 2) Modalita' COMMIT — quella per cui l'hook e' nato, invariata.
    out = subprocess.check_output(["git", "diff", "--cached", "--name-only", DIFF_FILTER])
    return out.decode().splitlines(), "indice staged"


aggiunti, origine = elenco_da_controllare()

# ⭐ Intersezione con cio' che pre-commit ci passa, quando ce lo passa.
#    Non e' ridondanza: rispetta il filtro `files:` della configurazione e
#    l'eventuale `--files` esplicito, senza MAI allargare il perimetro — restano
#    i soli AGGIUNTI, che e' cio' che il cricchetto deve guardare.
#    ⛔ Non si usa `sys.argv` come sorgente PRIMARIA proprio per questo: pre-commit
#    passa gli aggiunti E i modificati, e fidarsi di quell'elenco riporterebbe
#    dentro la `M` che il 2026-08-26 e' stata tolta apposta.
passati = [a for a in sys.argv[1:] if not a.startswith("-")]
if passati:
    consentiti = set(passati)
    aggiunti = [f for f in aggiunti if f in consentiti]

files = [f for f in aggiunti if EXTS.match(f) and not EXCLUDE.match(f)]

status = 0
for f in files:
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

# ⭐ Anche il verde dice su COSA: senza questa riga «Passed» copre allo stesso
#    modo «ho guardato dodici file nuovi» e «non ho guardato niente», che e'
#    esattamente come il difetto e' rimasto invisibile per mesi.
# ⚠️ «in questo lotto» non e' pignoleria: pre-commit spezza l'elenco dei file in
#    piu' invocazioni, quindi lo script gira N volte e ogni riga conta il PROPRIO
#    lotto. Uno zero qui non significa «non ho controllato niente»: significa che
#    in quel lotto non c'erano file aggiunti da controllare.
# ⚠️ E la riga si vede solo con `verbose: true` sull'hook (pre-commit nasconde lo
#    stdout di cio' che passa) — per questo la configurazione lo dichiara.
print(f"Header di licenza: {len(files)} file nuovi controllati in questo lotto ({origine}).")
sys.exit(0)
