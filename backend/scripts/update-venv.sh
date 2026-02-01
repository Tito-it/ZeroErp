# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------       


#!/usr/bin/env bash

# come Eseguire 
#./update-venv.sh

# Aggiorna tutti i pacchetti nella venv, esegue 'pip check' e,
# se non ci sono conflitti, scrive requirements.txt

# Aggiorna tutti i pacchetti nella venv, esegue 'pip check' e,
# se non ci sono conflitti, scrive requirements.txt

# In alternativa usare questi comandi manualmente:

# python -m pip install --upgrade pip
# python -m pip list --outdated --format=json
# python -m pip install --upgrade <package_name>
# python -m pip check
# pip list --outdated --format=columns | ForEach-Object { if ($_ -match '^\S+') { pip install --upgrade $matches[0] } } -- aggiorna tutto
# python -m pip freeze > requirements.txt

#  Utilizzo
#cd backend
#source .venv/bin/activate
#./update-venv.sh



#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

IN="../requirements.in"
OUT="../requirements.txt"

[[ -f "$IN" ]] || { echo "Missing $IN"; exit 1; }
[[ -n "${VIRTUAL_ENV:-}" ]] || { echo "Activate venv first"; exit 1; }

python -m pip install -U pip

# aggiorna SOLO i pacchetti esplicitati in requirements.in (ignora commenti/blank)
pkgs=$(grep -Ehv '^\s*($|#|-r )' "$IN" | sed 's/[<=>!~].*$//' | tr '\n' ' ')
[[ -n "${pkgs// }" ]] && python -m pip install -U $pkgs

python -m pip install -r "$IN"
python -m pip check

# freeze "pulito": solo pacchetti installati che appartengono al grafo deps di requirements.in

export REQ_IN="$IN"
export REQ_OUT="$OUT"

python - <<'PY' > "$OUT"
import re, sys, subprocess ,os
from importlib.metadata import distributions

req_in = os.environ["REQ_IN"]
req_out = os.environ["REQ_OUT"]


# top-level richiesti da requirements.in
req = []
for line in open(req_in, "r", encoding="utf-8"):
    line=line.strip()
    if not line or line.startswith("#") or line.startswith("-r "): 
        continue
  
    name = re.split(r'[<=>!~\[]', line, maxsplit=1)[0].strip()

    if name: req.append(name.lower())

# mappa dipendenze installate
deps = {}
name_of = {}
for d in distributions():
    n = (d.metadata.get("Name") or "").strip()
    if not n: 
        continue
    nl = n.lower()
    name_of[nl] = n
    requires = d.requires or []
    deps[nl] = [re.split(r'[ ;(<=>!~\[]', r, maxsplit=1)[0].strip().lower() for r in requires if r.strip()]

# closure deps
seen=set()
stack=list(req)
while stack:
    n=stack.pop()
    if n in seen: 
        continue
    seen.add(n)
    for ch in deps.get(n, []):
        if ch and ch not in seen:
            stack.append(ch)

# output pinned from `pip freeze` but filtered to seen set
freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True).splitlines()
for line in freeze:
    pkg = line.split("==", 1)[0].strip().lower()
    if pkg in seen:
        print(line)
PY

echo "OK -> $OUT updated"
