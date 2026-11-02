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

# Root dei tuoi documenti
DOCS_ROOT = 'docs'

# Includiamo la firma core
INCLUDE_CORE = '{% include-markdown "signature-core.md" %}'
FOOTER = f"\n---\n{INCLUDE_CORE}\n"

#INCLUDE_PERSONAL = '{% include-markdown "./signature.md" ignore missing %}'
#FOOTER = f"\n---\n{INCLUDE_CORE}\n\n{INCLUDE_PERSONAL}\n"

for dirpath, _dirnames, filenames in os.walk(DOCS_ROOT):
    # Salta completamente qualsiasi cartella "manual"
    if 'manual' in dirpath.replace('\\', '/').split('/'):
        continue

    for fname in filenames:
        lower = fname.lower()
        # Solo i Markdown, non index.md
        
        if not lower.endswith('.md') or lower in ('index.md','signature-core.md','signature.md','license.md'):
            continue

        fullpath = os.path.join(dirpath, fname)
        with open(fullpath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Se il file NON ha già l’include, appendilo
        if INCLUDE_CORE not in content:
            #print(f"✔ Firmo: {fullpath}")
            with open(fullpath, 'a', encoding='utf-8') as f:
                f.write(FOOTER)