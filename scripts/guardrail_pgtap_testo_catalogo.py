#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Rilasciato sotto GNU AGPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
# Guardrail CI — un pgTAP non cerca un nome qualificato nel testo che PostgreSQL ricostruisce
#   Guida: docs/it/guide/pgtap-come-si-scrive-un-test.md,
#          §«Il testo di un oggetto di catalogo dipende da chi legge»
#
# COSA PRESIDIA, in una riga:
#   «un letterale con `<schema>.` non si cerca (`~`, `LIKE`, `position`,
#    `strpos`, `replace`, `matches`…) in un testo che PostgreSQL ricostruisce, e
#    non si confronta con un `x::regclass::text`, quando quello schema sta nel
#    search_path di chi esegue il test».
#
# PERCHE'. Il testo ricostruito toglie lo schema quando lo schema e' nel
# search_path di chi legge. L'applicazione, che e' il runner di default, ha nel
# percorso django, public, config, dbops, script, anagrafiche; l'owner no. La
# stessa vista si stampa `script.fn_x(…)` da owner e `fn_x(…)` da app: il
# confronto con 'script.fn_x' e' verde nella prova da owner e rosso alla corsa
# del runner, e una negazione (`!~ 'config\.x'`) e' verde per sottrazione.
# La regola era scritta nella guida, e il difetto e' tornato almeno nove volte
# fra il 2026-09-25 e il 2026-11-27: per questo c'e' il cancello.
#
# CHE COSA RICOSTRUISCE IL TESTO, e che cosa no (provato come app su dbdev,
# 2026-11-27). E' la ragione delle tre classi qui sotto:
#   * RICOSTRUITO, schema tolto: pg_get_viewdef, pg_get_function_sqlbody, il
#     corpo di una `BEGIN ATOMIC` in pg_get_functiondef, pg_get_expr e quindi
#     pg_policies.qual/with_check, pg_get_constraintdef, pg_get_ruledef,
#     format_type e i tipi di pg_get_function_arguments/_result, e ogni
#     `x::regclass` / `::regproc` / `::regprocedure` / `::regtype` reso testo;
#   * MISTO: pg_get_triggerdef e pg_get_indexdef scrivono SEMPRE la tabella con
#     lo schema (`ON anagrafiche.soggetti`), ma tolgono lo schema alla funzione
#     (`EXECUTE FUNCTION trgfn_x()`) e alle espressioni;
#   * VERBATIM: il corpo di una plpgsql (o di una sql col corpo fra apici) in
#     pg_get_functiondef e prosrc, cioe' il testo com'e' stato scritto. Lì un
#     `LIKE '%script.fn_x(%'` e' corretto, e il cancello lo lascia passare.
#
# COME DECIDE:
#   * l'unita' e' l'istruzione, fino al `;`, anche dentro un corpo `$$…$$`;
#   * classe R (un `::reg*` reso testo): conta ogni letterale qualificato,
#     tranne la descrizione dell'asserzione;
#   * classe T (testo ricostruito, e pg_get_functiondef di una funzione che il
#     changelog definisce `BEGIN ATOMIC`): conta il letterale che sta in una
#     posizione di RICERCA (RX_OPERATORE, position, strpos, replace, regexp_*, o il secondo argomento di
#     matches/alike/doesnt_match/unalike…), o in un `=` / `<>` / `IN (`;
#   * classe M (triggerdef, indexdef): come T, ma non il nome dopo `ON`;
#   * pg_get_functiondef di una funzione che non si risolve dal testo (un
#     `p.oid` in un giro su pg_proc) conta come T solo se fra i nomi citati
#     nell'istruzione ce n'e' una `BEGIN ATOMIC`. Un giro su tutte le funzioni
#     cerca quasi sempre una forma senza schema, e il cancello non lo insegue;
#   * il search_path in vigore e' quello dell'app, letto dalla sua sede
#     (scripts/sql/provision_zeroerp.sql), o «$user», public per un file
#     `-- pgtap-runner: owner`. Lo cambiano un `SET [LOCAL] search_path`, un
#     `RESET`, un `set_config('search_path', …)`, e la clausola
#     `SET search_path` di una funzione per il suo corpo. Sotto `pg_catalog` non
#     sparisce niente, e passa tutto;
#   * non contano: la descrizione di un'asserzione pgTAP (l'ultimo argomento, se
#     e' un letterale), un letterale che diventa un oggetto
#     (`'config.x'::regclass`, `to_regclass('config.x')`, `has_*_privilege`),
#     lo schema scritto facoltativo (`(config\.)?`).
#
# ⛔ COSA NON VEDE, ed e' deliberato: un nome composto a pezzi
# ('config' || '.x'); un confronto con una colonna di temp table riempita
# prima; un confronto fra due nomi composti dal catalogo
# (`nspname || '.' || proname`), che e' corretto e lo resta. Fingere di
# prenderli costerebbe falsi positivi, e un cancello che grida a vuoto si
# impara a spegnere.
#
# ⚠️ L'eccezione voluta si dichiara accanto all'istruzione, con la ragione:
#     -- pgtap-testo-catalogo: voluto — <perche'>
# Deve stare nelle righe fra l'istruzione precedente e il letterale (per
# esempio, un test che prova proprio la differenza fra owner e app).
#
# Uso:
#   python3 scripts/guardrail_pgtap_testo_catalogo.py             # tutti i pgTAP
#   python3 scripts/guardrail_pgtap_testo_catalogo.py <file.sql>…  # solo quelli
#
# Exit: 0 nessuna violazione · 1 almeno una
# ------------------------------------------------------------
import pathlib
import re
import sys

RADICE_REPO = pathlib.Path(__file__).resolve().parent.parent
RADICE = RADICE_REPO / "db" / "pgtap"
CHANGELOG = RADICE_REPO / "db" / "changelog" / "migrations_v2"
PROVISION = RADICE_REPO / "scripts" / "sql" / "provision_zeroerp.sql"

RX_R = re.compile(r"::\s*reg(?!namespace\b|role\b)\w+\s*\)*\s*(::\s*(text|name|varchar|character\s+varying)\b|\|\|)", re.I)
RX_T = re.compile(
    r"\bpg_get_(viewdef|function_sqlbody|expr|constraintdef|ruledef|function_arguments"
    r"|function_identity_arguments|function_result|partkeydef|statisticsobjdef)\s*\("
    r"|\bformat_type\s*\("
    r"|\bpg_policies\b|\bpg_views\b|\bpg_matviews\b|\b(view|routine)_definition\b",
    re.I,
)
RX_M = re.compile(r"\bpg_get_(triggerdef|indexdef)\s*\(|\bpg_indexes\b", re.I)
RX_FUNCTIONDEF = re.compile(r"\bpg_get_functiondef\s*\(", re.I)
# Il bersaglio scritto: pg_get_functiondef('schema.nome(…)'::regprocedure) o ::regproc.
RX_BERSAGLIO = re.compile(r"\bpg_get_functiondef\s*\(\s*'(\w+\.\w+)", re.I)
RX_NOME_FUNZIONE = re.compile(r"\b(\w+\.\w+)\s*(?:\(|$)")

RX_DOPO_ON = re.compile(r"\bON\s+(ONLY\s+)?$", re.I)

# Un letterale che diventa un oggetto non e' un confronto di testo.
RX_DOPO_CAST = re.compile(r"\s*::\s*reg\w+", re.I)
RX_PRIMA_RISOLVE = re.compile(
    r"\b(to_reg\w+|has_\w+_privilege|pg_get_viewdef|pg_\w*relation_size|pg_\w*table_size"
    r"|dbops\.fn_nome_qualificato)\s*\(\s*(?:[^,()]*,\s*){0,2}$",
    re.I,
)
RX_SET_PATH = re.compile(
    r"^\s*SET\s+(?:LOCAL\s+|SESSION\s+)?search_path\s*(?:=|TO)\s*(.+?)\s*$", re.I | re.S)
RX_RESET_PATH = re.compile(r"^\s*RESET\s+(search_path|ALL)\s*$", re.I)
RX_SET_CONFIG = re.compile(r"\bset_config\s*\(\s*'search_path'\s*,\s*'([^']*)'", re.I)
RX_CLAUSOLA_PATH = re.compile(r"\bSET\s+search_path\s*(?:=|TO)\s*([\w\s,\"$]+?)\s*(?:\bAS\b|\bLANGUAGE\b|$)",
                              re.I)
RX_CREATE_FN = re.compile(r"\bCREATE\s+(OR\s+REPLACE\s+)?(FUNCTION|PROCEDURE)\b", re.I)
RX_OWNER = re.compile(r"^--\s*pgtap-runner:\s*owner\s*$", re.M)
RX_VOLUTO = re.compile(r"--\s*pgtap-testo-catalogo:\s*voluto\b\s*\S*\s*\S")

# Le asserzioni pgTAP: l'ultimo argomento letterale e' la descrizione.
ASSERZIONI = {
    "ok", "is", "isnt", "matches", "imatches", "doesnt_match", "doesnt_imatch", "alike", "ialike",
    "unalike", "unialike", "cmp_ok", "results_eq", "results_ne", "set_eq", "set_ne", "bag_eq",
    "bag_ne", "is_empty", "isnt_empty", "set_has", "set_hasnt", "bag_has", "bag_hasnt", "row_eq",
    "throws_ok", "throws_like", "throws_ilike", "throws_matching", "lives_ok", "is_deeply",
}
# Quelle il cui secondo argomento e' un modello cercato nel primo.
ASSERZIONI_RICERCA = {"matches", "imatches", "doesnt_match", "doesnt_imatch", "alike", "ialike",
                      "unalike", "unialike"}

PATH_OWNER = ["$user", "public"]


# Scopo: il search_path dell'app dalla sua sede (l'ALTER ROLE del provisioning).
def path_app() -> list[str]:
    mo = re.search(r"ALTER ROLE %I SET search_path = ([\w,]+)", PROVISION.read_text(encoding="utf-8"))
    if not mo:
        sys.exit(f"❌ search_path dell'app non trovato in {PROVISION.relative_to(RADICE_REPO)}: "
                 "il cancello non sa quali schemi spariscono dal testo")
    return [s.strip() for s in mo.group(1).split(",")]


def leggi_path(valore: str) -> list[str]:
    return [s.strip().strip("'\"").lower() for s in valore.split(",") if s.strip()]


# Scopo: le funzioni la cui ULTIMA definizione nel changelog e' `BEGIN ATOMIC`.
#   I file si ordinano per nome, che comincia con l'id del changeSet (data e
#   progressivo): l'ultima definizione vince. Le righe di commento YAML non
#   contano.
RX_DEF = re.compile(r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(\w+\.\w+)\s*\(", re.I | re.M)
RX_CORPO = re.compile(r"\bBEGIN\s+ATOMIC\b|\bAS\s*(\$\w*\$|')", re.I)


def funzioni_atomic() -> set[str]:
    ultima = {}
    for f in sorted(CHANGELOG.rglob("*.yaml"), key=lambda p: p.name):
        testo = "\n".join(r for r in f.read_text(encoding="utf-8", errors="replace").split("\n")
                          if not r.lstrip().startswith("#"))
        defs = list(RX_DEF.finditer(testo))
        for k, mo in enumerate(defs):
            fine = defs[k + 1].start() if k + 1 < len(defs) else len(testo)
            corpo = RX_CORPO.search(testo, mo.end(), fine)
            if corpo:
                ultima[mo.group(1).lower()] = corpo.group(0).upper().startswith("BEGIN")
    return {nome for nome, atomic in ultima.items() if atomic}


# ------------------------------------------------------------
# Lessico: letterali, dollar-quote, commenti, parentesi, `;`.
# ------------------------------------------------------------
# Scopo: dividere il testo in token con il loro offset. Un dollar-quote che
#   contiene un `;` e' un corpo (DO, funzione): si apre e se ne leggono le
#   istruzioni. Uno senza `;` e' un letterale (una regex `$re$…$re$`, la query
#   di un `results_eq`): vale come letterale, e se ne leggono ANCHE i token.
def lessico(t: str, base: int = 0):
    tok = []  # (tipo, valore, inizio, fine)
    i, n = 0, len(t)
    while i < n:
        c = t[i]
        if t.startswith("--", i):
            j = t.find("\n", i)
            i = n if j < 0 else j
        elif t.startswith("/*", i):
            j = t.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c == "'" or (c in "eE" and i + 1 < n and t[i + 1] == "'" and (i == 0 or not t[i - 1].isalnum())):
            esc = c in "eE"
            j = i + (2 if esc else 1)
            buf = []
            while j < n:
                if esc and t[j] == "\\" and j + 1 < n:
                    buf.append(t[j:j + 2])
                    j += 2
                    continue
                if t[j] == "'":
                    if j + 1 < n and t[j + 1] == "'":
                        buf.append("'")
                        j += 2
                        continue
                    j += 1
                    break
                buf.append(t[j])
                j += 1
            tok.append(("str", "".join(buf), base + i, base + j))
            i = j
        elif c == "$":
            m = re.match(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$", t[i:])
            if not m:
                i += 1
                continue
            tag = m.group(0)
            fine = t.find(tag, i + len(tag))
            fine = n if fine < 0 else fine
            corpo = t[i + len(tag):fine]
            dentro = lessico(corpo, base + i + len(tag))
            if ";" in corpo:
                tok.append(("corpo_apre", tag, base + i, base + i + len(tag)))
                tok.extend(dentro)
                tok.append(("corpo_chiude", tag, base + fine, base + fine + len(tag)))
            else:
                tok.append(("str_dollar", corpo, base + i, base + fine + len(tag)))
                tok.extend(dentro)
            i = fine + len(tag)
        elif c in "(),;":
            tok.append((c, c, base + i, base + i + 1))
            i += 1
        elif c.isalpha() or c == "_":
            m = re.match(r"[A-Za-z_][\w.]*", t[i:])
            tok.append(("id", m.group(0), base + i, base + i + m.end()))
            i += m.end()
        else:
            i += 1
    return tok


# Scopo: il ruolo dei letterali negli argomenti delle asserzioni pgTAP —
#   la descrizione (l'ultimo argomento, se e' fatto solo di letterali) e il
#   modello cercato (il secondo argomento di matches, alike e affini).
def ruoli_asserzioni(tok) -> tuple[set[int], set[int]]:
    desc, modello = set(), set()
    for k, (tipo, val, _, _) in enumerate(tok):
        nome = val.lower().split(".")[-1] if tipo == "id" else ""
        if nome not in ASSERZIONI or k + 1 >= len(tok) or tok[k + 1][0] != "(":
            continue
        prof, args, corrente = 0, [], []
        for j in range(k + 1, len(tok)):
            tp = tok[j][0]
            if tp == "(":
                prof += 1
                if prof == 1:
                    continue
            elif tp == ")":
                prof -= 1
                if prof == 0:
                    args.append(corrente)
                    break
            elif tp == "," and prof == 1:
                args.append(corrente)
                corrente = []
                continue
            corrente.append(j)
        if len(args) >= 2 and args[-1] and all(tok[j][0] in ("str", "str_dollar") for j in args[-1]):
            desc.update(args[-1])
        if nome in ASSERZIONI_RICERCA and len(args) >= 2:
            modello.update(args[1])
    return desc, modello


# ------------------------------------------------------------
# Il soggetto di una ricerca: l'espressione in cui il letterale si cerca.
# ------------------------------------------------------------
# Scopo: il testo con il contenuto dei letterali fra apici sostituito da `x`,
#   offset invariati: le parentesi dentro una regex non contano piu'.
def mascherato(t: str, tok) -> str:
    out = list(t)
    for tp, _, a, b in tok:
        if tp == "str":
            for k in range(a + 1, max(a + 1, b - 1)):
                if out[k] != "\n":
                    out[k] = "x"
    return "".join(out)


RX_TERMINE = re.compile(r"[\w.:\[\]\"]")


# Scopo: l'espressione che finisce in `fine` (una chiamata, un cast, una colonna).
def indietro(mt: str, fine: int) -> tuple[int, int]:
    i = fine
    while i > 0 and mt[i - 1].isspace():
        i -= 1
    fine = i
    while i > 0:
        c = mt[i - 1]
        if c == ")":
            prof, k = 0, i - 1
            while k >= 0:
                if mt[k] == ")":
                    prof += 1
                elif mt[k] == "(":
                    prof -= 1
                    if prof == 0:
                        break
                k -= 1
            i = max(k, 0)
        elif c == "'":
            k = mt.rfind("'", 0, i - 1)
            i = max(k, 0)
        elif RX_TERMINE.match(c):
            i -= 1
        else:
            break
    return i, fine


# Scopo: l'espressione che comincia in `inizio`.
def avanti(mt: str, inizio: int) -> tuple[int, int]:
    i, n = inizio, len(mt)
    while i < n and mt[i].isspace():
        i += 1
    da = i
    while i < n:
        c = mt[i]
        if c == "(":
            prof, k = 0, i
            while k < n:
                if mt[k] == "(":
                    prof += 1
                elif mt[k] == ")":
                    prof -= 1
                    if prof == 0:
                        break
                k += 1
            i = k + 1
        elif RX_TERMINE.match(c):
            i += 1
        else:
            break
    return da, i


RX_OPERATORE = re.compile(
    r"(~\*?|!~\*?|\bNOT\s+I?LIKE|\bI?LIKE|\bSIMILAR\s+TO|=|<>|!=|\bNOT\s+IN\s*\(|\bIN\s*\()\s*$", re.I)
RX_POSITION = re.compile(r"\bposition\s*\(\s*$", re.I)
RX_ARGOMENTO = re.compile(
    r"\b(strpos|replace|regexp_\w+|split_part)\s*\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*,\s*$", re.I)
RX_QUANTIFICATO = re.compile(r"\b(ANY|ALL)\s*\(\s*(ARRAY\s*\[)?\s*$", re.I)
RX_VIRGOLA = re.compile(r",\s*$")


# Scopo: dove sta il letterale, e su che cosa si cerca.
#   -> (posizione, soggetto): posizione e' 'ricerca', 'uguale' o None;
#      soggetto e' lo span (inizio, fine) dell'espressione, o None.
def posizione(mt: str, a: int, b: int, j: int, modello: set[int]):
    prima = mt[max(0, a - 400):a]
    mo = RX_OPERATORE.search(prima)
    if mo:
        uguale = mo.group(1).lstrip("!<>=").upper() == "" or "IN" in mo.group(1).upper()
        sogg = indietro(mt, a - len(prima) + mo.start())
        return ("uguale" if uguale else "ricerca"), sogg
    if RX_POSITION.search(prima):
        mo = re.match(r"\s*IN\b", mt[b:])
        return "ricerca", (avanti(mt, b + mo.end()) if mo else None)
    if RX_ARGOMENTO.search(prima) or (j in modello and RX_VIRGOLA.search(prima)):
        return "ricerca", indietro(mt, a - len(RX_VIRGOLA.search(prima).group(0)))
    if RX_QUANTIFICATO.search(prima):
        return "ricerca", None
    return None, None


RX_COMPOSTO = re.compile(r"\b(nspname|relname|proname|conname|tgname)\b|\bformat\s*\(", re.I)
RX_HELPER = re.compile(r"\bpg_temp\.(\w+)\s*\(", re.I)
RX_HELPER_DEF = re.compile(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+pg_temp\.(\w+)\s*\(", re.I)


# Scopo: che testo legge un soggetto.
#   'verbatim' (prosrc, il corpo com'e' scritto), 'T' (ricostruito),
#   'M' (trigger o indice), 'R' (un ::reg* reso testo), None (non si sa).
def classifica(sogg: str | None, testo_sogg: str | None, atomic: set[str], helper: dict) -> str | None:
    if not sogg:
        return None
    if RX_R.search(sogg):
        return "R"
    if RX_T.search(sogg):
        return "T"
    if RX_M.search(sogg):
        return "M"
    if RX_FUNCTIONDEF.search(sogg):
        bersagli = {x.lower() for x in RX_BERSAGLIO.findall(testo_sogg or "")}
        if not bersagli:
            return None
        return "T" if bersagli & atomic else "verbatim"
    for nome in RX_HELPER.findall(sogg):
        if nome.lower() in helper:
            return helper[nome.lower()]
    if re.search(r"\bprosrc\b", sogg, re.I):
        return "verbatim"
    return None


# Scopo: che testo restituiscono gli helper pg_temp del file, dal loro corpo.
#   Un helper con `SET search_path = pg_catalog` e' la cura della guida: i nomi
#   escono qualificati, e quello che restituisce si confronta col nome intero.
def helper_del_file(t: str) -> dict:
    out = {}
    for mo in RX_HELPER_DEF.finditer(t):
        m = re.compile(r"\$\w*\$").search(t, mo.end())
        if not m:
            continue
        fine = t.find(m.group(0), m.end())
        corpo = t[m.end():fine if fine > 0 else len(t)]
        clausola = RX_CLAUSOLA_PATH.search(t[mo.end():m.start()])
        if clausola and not [x for x in leggi_path(clausola.group(1))
                             if x not in ("$user", "pg_catalog", "pg_temp")]:
            out[mo.group(1).lower()] = "verbatim"  # sotto pg_catalog ogni nome esce qualificato
        elif RX_R.search(corpo) or RX_T.search(corpo):
            out[mo.group(1).lower()] = "T"
        elif RX_M.search(corpo):
            out[mo.group(1).lower()] = "M"
        elif RX_FUNCTIONDEF.search(corpo):
            out[mo.group(1).lower()] = None
        elif re.search(r"\bprosrc\b", corpo, re.I):
            out[mo.group(1).lower()] = "verbatim"
    return {k: v for k, v in out.items() if v is not None}


def esamina(f: pathlib.Path, app: list[str], atomic: set[str]) -> list[tuple[int, str, str]]:
    t = f.read_text(encoding="utf-8", errors="replace")
    default = PATH_OWNER if RX_OWNER.search(t) else app
    tok = lessico(t)
    mt = mascherato(t, tok)
    desc, modello = ruoli_asserzioni(tok)
    helper = helper_del_file(t)
    viol = []

    stato = {"sessione": list(default)}
    pila_corpi = []        # il search_path in vigore dentro i corpi aperti
    stmt, inizio = [], [0]

    def chiudi(fine_offset):
        if not stmt:
            return
        da = tok[stmt[0]][2]
        testo = t[da:fine_offset]
        codice = re.sub(r"--[^\n]*", "", mt[da:fine_offset])
        if not pila_corpi:
            mo = RX_SET_PATH.match(testo)
            if mo:
                stato["sessione"] = leggi_path(mo.group(1))
            elif RX_RESET_PATH.match(testo):
                stato["sessione"] = list(default)
        mo = RX_SET_CONFIG.search(testo)
        if mo:
            stato["sessione"] = leggi_path(mo.group(1))
        path = pila_corpi[-1] if pila_corpi else stato["sessione"]
        schemi = [s for s in path if s not in ("$user", "pg_catalog", "pg_temp")]

        classe_r = bool(RX_R.search(codice))
        classe_t = bool(RX_T.search(codice))
        classe_m = bool(RX_M.search(codice))
        if RX_FUNCTIONDEF.search(codice):
            bersagli = {x.lower() for x in RX_BERSAGLIO.findall(testo)}
            citate = {tok[j][1].lower() for j in stmt if tok[j][0] == "str"}
            citate = {m.group(1).lower() for c in citate for m in RX_NOME_FUNZIONE.finditer(c)}
            classe_t = classe_t or bool((bersagli or citate) & atomic)
        if any(h in helper for h in (x.lower() for x in RX_HELPER.findall(codice))):
            classi = {helper[h.lower()] for h in RX_HELPER.findall(codice) if h.lower() in helper}
            classe_t = classe_t or "T" in classi
            classe_m = classe_m or "M" in classi
        stmt_corrente = list(stmt)
        stmt.clear()
        if not schemi or not (classe_r or classe_t or classe_m):
            return

        rx_nome = re.compile(r"(?<![\w.])(" + "|".join(map(re.escape, schemi)) + r")\s*\\?\.(?=\s*[\w\"])",
                             re.I)
        for j in stmt_corrente:
            tp, val, a, b = tok[j]
            if tp not in ("str", "str_dollar") or j in desc:
                continue
            if tp == "str_dollar" and re.search(r"\s", val):
                continue  # una query, non un nome: i suoi letterali li legge il lessico
            if RX_DOPO_CAST.match(t, b) or RX_PRIMA_RISOLVE.search(re.sub(r"\s+", " ", t[max(0, a - 300):a])):
                continue
            pos, span = posizione(mt, a, b, j, modello)
            # Un soggetto concatenato (`n.nspname || '.' || p.proname`) si legge intero.
            while span and re.search(r"\|\|\s*$", mt[max(0, span[0] - 20):span[0]]):
                k = mt.rindex("||", 0, span[0])
                span = (indietro(mt, k)[0], span[1])
            if span and RX_COMPOSTO.search(mt[span[0]:span[1]]) and not RX_R.search(mt[span[0]:span[1]]):
                continue  # un nome composto dal catalogo: e' sempre intero
            sogg = mt[span[0]:span[1]] if span else None
            testo_sogg = t[span[0]:span[1]] if span else None
            tipo = classifica(sogg, testo_sogg, atomic, helper)
            if tipo == "verbatim":
                continue
            if tipo is None:
                # Il soggetto non si ricava: decide l'istruzione.
                if not (classe_r or (pos and (classe_t or classe_m))):
                    continue
                tipo = "R" if classe_r else ("T" if classe_t else "M")
            elif not pos and tipo != "R":
                continue
            for mo in rx_nome.finditer(val):
                if val[:mo.start()].endswith("(") and re.match(r"\\?\.\)\?", val[mo.end(1):]):
                    continue  # (schema\.)? — lo schema e' facoltativo
                if tipo == "M" and RX_DOPO_ON.search(val[:mo.start()]):
                    continue  # trigger e indici scrivono sempre la tabella con lo schema
                if RX_VOLUTO.search(t[inizio[0]:a]):
                    break
                riga = t.count("\n", 0, a) + 1
                viol.append((riga, mo.group(1), val if len(val) <= 70 else val[:67] + "…"))
                break

    for j, (tp, _val, a, b) in enumerate(tok):
        if tp == "corpo_apre":
            prima = t[tok[stmt[0]][2]:a] if stmt else ""
            clausola = None
            if RX_CREATE_FN.search(prima):
                mo = RX_CLAUSOLA_PATH.search(prima)
                clausola = leggi_path(mo.group(1)) if mo else None
            chiudi(a)
            inizio[0] = b
            pila_corpi.append(clausola if clausola is not None else list(default))
            continue
        if tp == "corpo_chiude":
            chiudi(a)
            if pila_corpi:
                pila_corpi.pop()
            inizio[0] = b
            continue
        if tp == ";":
            chiudi(a)
            inizio[0] = b
            continue
        stmt.append(j)
    chiudi(len(t))
    return viol


def main() -> int:
    app = path_app()
    atomic = funzioni_atomic()
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    file = [pathlib.Path(a).resolve() for a in argv] if argv else sorted(RADICE.rglob("*.sql"))
    tutte = []
    for f in file:
        for riga, schema, val in esamina(f, app, atomic):
            tutte.append((f, riga, schema, val))

    print(f"pgTAP testo di catalogo — {len(file)} file esaminati "
          f"(search_path dell'app: {', '.join(app)}; {len(atomic)} funzioni BEGIN ATOMIC nel changelog)")
    if not tutte:
        print("✅ nessun nome qualificato cercato nel testo che PostgreSQL ricostruisce")
        return 0
    print(f"\n❌ {len(tutte)} ricerche di un nome qualificato nel testo ricostruito:")
    for f, riga, schema, val in tutte:
        try:
            rel = f.relative_to(RADICE_REPO)
        except ValueError:
            rel = f
        print(f"   {rel}:{riga}  '{val}'")
        print(f"      → `{schema}.` sparisce dal testo per chi ha `{schema}` nel search_path (l'app sì, l'owner no)")
    print("\n   Cura: «A legge B» con pg_depend sugli OID; un nome con format('%I.%I', nspname, relname)")
    print("   o il confronto per OID; in una regex lo schema facoltativo `(schema\\.)?`; o la lettura")
    print("   sotto `SET LOCAL search_path = pg_catalog`.")
    print("   Eccezione voluta: `-- pgtap-testo-catalogo: voluto — <perche'>` accanto all'istruzione.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
