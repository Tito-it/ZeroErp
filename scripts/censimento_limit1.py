#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Rilasciato sotto GNU AGPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
# Scopo: censire i `LIMIT 1` senza `ORDER BY` nelle fixture pgTAP.
#   Brief: docs/it/dev/work-done/brief-db-pgtap-runner-rls-baseline.md §27
#   Regola: memoria `feedback_pgtap_limit1_senza_orderby`
#
# LENTE, NON CANCELLO — come `scripts/sql/check_*`. Non va in CI: un `LIMIT 1`
# senza `ORDER BY` non e' sempre un difetto (su una temp table costruita dal
# test con una riga sola non sceglie niente), e un cancello che sbaglia si
# impara a ignorare. Si rilancia quando si apre un lotto.
#
# ⚠️ IL PUNTO DELICATO, e l'unico: `ORDER BY` va cercato ALLO STESSO LIVELLO
# DI ANNIDAMENTO del `LIMIT`. Un `ORDER BY` in una sottoquery, o nella query
# che contiene quella col `LIMIT`, non ordina la scelta che interessa — e un
# analizzatore che lo ignora dichiara «a posto» siti che non lo sono.
#
# COME LEGGERE L'ESITO. «ALTO» = nessun `WHERE`, oppure un `WHERE` che filtra
# un insieme senza individuare una riga (`attivo = true`, `IS NOT NULL`).
# ⚠️ Prima di tagliare, separare gli ALTO su tabelle TEMPORANEE del test
# stesso (dove il LIMIT non sceglie niente di rischioso) da quelli su tabelle
# vere del dominio: al 2026-08-07 erano 50 contro 66, cioe' meta' del lavoro
# sarebbe finita su siti innocui.
#
# Uso:
#   python3 scripts/censimento_limit1.py            # solo il riepilogo
#   python3 scripts/censimento_limit1.py out.tsv    # + dettaglio file/riga/tabella
# ------------------------------------------------------------

import re, sys, pathlib, collections

def maschera(t: str) -> str:
    """Sostituisce con spazi commenti, stringhe e dollar-quote, preservando
    lunghezza e a-capo: gli offset restano validi sul testo originale."""
    out = list(t); i = 0; n = len(t)
    def blank(a, b):
        for k in range(a, b):
            if out[k] != '\n': out[k] = ' '
    while i < n:
        if t.startswith('--', i):
            j = t.find('\n', i);  j = n if j < 0 else j
            blank(i, j); i = j
        elif t.startswith('/*', i):
            j = t.find('*/', i+2); j = n if j < 0 else j+2
            blank(i, j); i = j
        elif t[i] == "'":
            j = i+1
            while j < n:
                if t[j] == "'":
                    if j+1 < n and t[j+1] == "'": j += 2; continue
                    j += 1; break
                j += 1
            blank(i, j); i = j
        elif t[i] == '$':
            m = re.match(r'\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$', t[i:])
            if m:
                tag = m.group(0)
                j = t.find(tag, i+len(tag))
                j = n if j < 0 else j+len(tag)
                blank(i, j); i = j
            else: i += 1
        else: i += 1
    return ''.join(out)

def inizio_query(m: str, pos: int) -> int:
    """Risale bilanciando le parentesi fino alla `(` aperta piu' vicina non
    chiusa, o al `;` precedente. Ritorna l'offset d'inizio del perimetro."""
    depth = 0
    for k in range(pos-1, -1, -1):
        c = m[k]
        if c == ')': depth += 1
        elif c == '(':
            if depth == 0: return k+1
            depth -= 1
        elif c == ';' and depth == 0: return k+1
    return 0

def stesso_livello(m: str, a: int, b: int, pattern) -> bool:
    """Cerca `pattern` fra a e b, contando solo le occorrenze a depth 0."""
    depth = 0
    for mo in re.finditer(r'\(|\)|' + pattern, m[a:b], re.I):
        s = mo.group(0)
        if s == '(': depth += 1
        elif s == ')': depth -= 1
        elif depth == 0: return True
    return False

RX_LIMIT = re.compile(r'\bLIMIT\s+1\b', re.I)
RX_FROM  = re.compile(r'\bFROM\s+([A-Za-z_][\w.]*)', re.I)

righe = []
# ⚠️ `rglob` e non `glob('*/*.sql')`: il glob a un livello solo salta le
#   sottocartelle di schema. Stesso difetto trovato il 2026-08-24 in
#   pgtap-baseline.sh e guardrail_pgtap_preambolo.py — un censimento che
#   non guarda in un ramo non dice «pulito», dice «non ho guardato».
for f in sorted(pathlib.Path('db/pgtap').rglob('*.sql')):
    t = f.read_text(encoding='utf-8', errors='replace')
    m = maschera(t)
    for mo in RX_LIMIT.finditer(m):
        a = inizio_query(m, mo.start()); b = mo.start()
        perimetro = m[a:b]
        ha_order = stesso_livello(m, a, b, r'ORDER\s+BY')
        if ha_order: continue
        # dentro EXISTS(...) il LIMIT non sceglie niente: si esclude
        pre = m[max(0, a-40):a]
        if re.search(r'\bEXISTS\s*\($', pre, re.I): continue
        ha_where = stesso_livello(m, a, b, r'\bWHERE\b')
        tab = RX_FROM.search(perimetro)
        tab = tab.group(1) if tab else '?'
        # rischio: ALTO = nessun WHERE, o WHERE che filtra un insieme
        if not ha_where: rischio = 'ALTO'
        else:
            w = perimetro[re.search(r'\bWHERE\b', perimetro, re.I).start():]
            debole = re.fullmatch(
                r"[\sA-Za-z_.\"']*\b(attiv[oa]|is\s+not\s+null|is\s+null|true|false)\b[\s\w.=<>'\"]*",
                w.strip(), re.I)
            rischio = 'ALTO' if debole else 'medio'
        righe.append((str(f), t[:mo.start()].count('\n')+1, tab, rischio))

schemi = collections.Counter(); alti = collections.Counter(); files = collections.defaultdict(set)
for f, _ln, _tab, r in righe:
    s = f.split('/')[2]; schemi[s] += 1; files[s].add(f)
    if r == 'ALTO': alti[s] += 1
print(f"{'schema':<14}{'LIMIT 1 senza ORDER BY':>24}{'di cui ALTO':>13}{'file':>7}")
for s in sorted(schemi, key=lambda x: -schemi[x]):
    print(f"{s:<14}{schemi[s]:>24}{alti[s]:>13}{len(files[s]):>7}")
print(f"{'TOTALE':<14}{sum(schemi.values()):>24}{sum(alti.values()):>13}"
      f"{len({f for f,_,_,_ in righe}):>7}  su {len(list(pathlib.Path('db/pgtap').rglob('*.sql')))} file")
print()
tabelle = collections.Counter(tab for _, _, tab, r in righe if r == 'ALTO')
print("Tabelle piu' pescate a caso (rischio ALTO):")
for tab, n in tabelle.most_common(8): print(f"   {tab:<42}{n:>4}")
with open(sys.argv[1] if len(sys.argv) > 1 else '/dev/null', 'w') as fh:
    for f, ln, tab, r in righe: fh.write(f"{f}\t{ln}\t{tab}\t{r}\n")
