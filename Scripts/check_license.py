#!/usr/bin/env python3
import sys, subprocess, re, itertools

REQUIRED = "Copyright (C)"
EXTS = re.compile(r".*\.(py|js|vue|ya?ml)$")
EXCLUDE = re.compile(r"^docs/")

# Prendi i file in staging
files = subprocess.check_output(
    ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
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
