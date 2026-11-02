#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU AGPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
import os

# Calcola la root del repository e poi la cartella docs
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DOCS_ROOT = os.path.join(BASE_DIR, 'docs')

print(f"[DEBUG] Base dir: {BASE_DIR}")
print(f"[DEBUG] Docs root: {DOCS_ROOT}")

if not os.path.isdir(DOCS_ROOT):
    print(f"ERRORE: cartella docs non trovata in {DOCS_ROOT}\nVerifica il percorso e rilancia lo script.")
    exit(1)

# Semplice check su substring dei file di firma
def is_signature_line(line: str) -> bool:
    return 'signature-core.md' in line or 'signature.md' in line

# Itera ricorsivamente la cartella docs
for dirpath, _dirnames, filenames in os.walk(DOCS_ROOT):
    # Esclude cartelle manual
    if 'manual' in dirpath.replace('\\', '/').split('/'):
        continue

    for fname in filenames:
        lower = fname.lower()
        # Solo file .md e non index/signature stessi
        if not lower.endswith('.md') or lower in ('index.md', 'signature-core.md', 'signature.md'):
            continue

        fullpath = os.path.join(dirpath, fname)
        print(f"[DEBUG] Controllo file: {fullpath}")
        with open(fullpath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Rimuove ogni linea che contiene il nome dei file di firma
        new_lines = [line for line in lines if not is_signature_line(line)]
        if len(new_lines) != len(lines):
            print(f"[INFO] Rimuovo include da: {fullpath}")
            with open(fullpath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

print("[INFO] Operazione completata.")
