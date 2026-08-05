# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
# NOTE:
# - DB_DOCS_MODE=ci (o DOCS_MODE=ci) genera doc "minimal": solo include manuale,
#   senza sorgenti SQL, per evitare link rotti in CI.
# - In locale, se DB_DOCS_MODE non e' impostato, la generazione resta completa.
# ------------------------------------------------------------ 

#!/usr/bin/env python3
import os, re
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor

# Directory del file script e root del progetto
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))

# Carica variabili d'ambiente
load_dotenv(dotenv_path=os.path.join(BASE_DIR, "internal.env"), override=True)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, "git.env"), override=False)

# Costruisci DSN
dsn_env = os.getenv("DATABASE_DSN")
if dsn_env and "<" not in dsn_env:
    DB_DSN = dsn_env
else:
    host = os.getenv("DB_HOST", "")
    port = os.getenv("DB_PORT", "")
    dbname = os.getenv("DB_NAME", "")
    user = os.getenv("POSTGRESQL_USER", "")
    pwd = os.getenv("POSTGRESQL_PWD", "")
    DB_DSN = f"host={host} port={port} dbname={dbname} user={user} password={pwd}"

# Schemi da documentare
db_schemas = os.getenv("DB_DOC_SCHEMAS", "")
schemas = [s.strip() for s in db_schemas.split(",") if s.strip()]

# Percorsi
DOCS_DIR = os.getenv("DB_DOCS_OUT_DIR", "").strip() or os.path.join(BASE_DIR, "docs")
OUT_DIR = os.path.join(DOCS_DIR, "it", "dbzero")

DOCS_MODE = (os.getenv("DB_DOCS_MODE") or os.getenv("DOCS_MODE") or "").strip().lower()
DOCS_MINIMAL = DOCS_MODE in {"ci", "minimal", "manual"}


# Include manuale
def include_manual(schema, kind, name):
    manual_path = os.path.join(OUT_DIR, schema, "manual", f"{name}.md")
    if os.path.isfile(manual_path):
        rel = os.path.relpath(manual_path, start=DOCS_DIR).replace('\\', '/')
        return f"{{% include-markdown \"{rel}\" %}}\n"
    return ""


def sql_literal(value):
    """Escape SQL string literal for generated COMMENT statements."""
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"

# Genera Markdown tabella con colonne, vincoli, indici, trigger
def gen_table_md(schema, table, cur):
    if DOCS_MINIMAL:
        return ""
    lines = [f"# 📚 Tabella `{table}`\n"]
    # Colonne
    cur.execute(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s
        ORDER BY ordinal_position
        """, (schema, table)
    )
    cols = cur.fetchall()
    lines += ["## 🗂️ Campi principali", "| Colonna | Tipo | Nullable | Default |", "|---------|------|----------|---------|"]
    for col in cols:
        default = col.get("column_default") or ""
        lines.append(f"| {col['column_name']} | {col['data_type']} | {col['is_nullable']} | {default} |")
    # Vincoli
    cur.execute(
        """
        SELECT tc.constraint_type,
               tc.constraint_name,
               string_agg(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) AS columns
        FROM information_schema.table_constraints tc
        LEFT JOIN (
            SELECT DISTINCT constraint_schema,
                            constraint_name,
                            table_schema,
                            table_name,
                            column_name,
                            ordinal_position
            FROM information_schema.key_column_usage
        ) kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.constraint_schema = kcu.constraint_schema
         AND tc.table_schema = kcu.table_schema
         AND tc.table_name = kcu.table_name
        WHERE tc.table_schema=%s AND tc.table_name=%s
        AND NOT (tc.constraint_type = 'CHECK' AND 
                tc.constraint_name LIKE '%%_not_null') 
        GROUP BY tc.constraint_type, tc.constraint_name
        ORDER BY tc.constraint_type, tc.constraint_name
        """, (schema, table)
    )
    constraints = cur.fetchall()
    if constraints:
        lines += ["", "## 🔒 Vincoli", "| Tipo | Nome | Colonne |", "|------|------|---------|"]
        for con in constraints:
            lines.append(f"| {con['constraint_type']} | {con['constraint_name']} | {con['columns'] or ''} |")
    # Indici
    cur.execute(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = %s AND tablename = %s
        ORDER BY indexname
        """, (schema, table)
    )
    indexes = cur.fetchall()
    if indexes:
        lines += ["", "## 📑 Indici", "| Nome | Definizione |", "|------|-------------|"]
        for idx in indexes:
            lines.append(f"| {idx['indexname']} | `{idx['indexdef']}` |")
    # Trigger
    cur.execute(
        """
        SELECT trigger_name, action_timing, event_manipulation,
               action_statement
        FROM information_schema.triggers
        WHERE trigger_schema = %s AND event_object_table = %s
        ORDER BY trigger_name
        """, (schema, table)
    )
    triggers = cur.fetchall()
    if triggers:
        lines += ["", "## 🚨 Trigger", "| Nome | Timing | Evento | Azione |", "|------|--------|--------|--------|"]
        for trg in triggers:
            lines.append(f"| {trg['trigger_name']} | {trg['action_timing']} | {trg['event_manipulation']} | `{trg['action_statement']}` |")
    return "\n".join(lines)

# Genera Markdown funzione
# Assicurati che OUT_DIR sia definito (come nel tuo script)
# OUT_DIR = os.path.join(BASE_DIR, "docs", "it", "dbzero")
# Genera Markdown funzione
def gen_function_md(schema, func, cur):
    if DOCS_MINIMAL:
        return ""
    cur.execute("""
        SELECT p.proname,
               p.prokind,  -- 'f' function, 'p' procedure
               pg_get_function_identity_arguments(p.oid) AS args,
               pg_get_functiondef(p.oid) AS defn,
               obj_description(p.oid, 'pg_proc') AS obj_comment
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = %s AND p.proname = %s
        LIMIT 1
    """, (schema, func))
    row = cur.fetchone()
    if not row:
        return ""
    kind = row["prokind"]
    kind_label = "Procedura" if kind == "p" else "Funzione"
    kind_verb  = "PROCEDURE" if kind == "p" else "FUNCTION"

    lines = [
        f"# ⚙️ {kind_label} `{row['proname']}`\n",
        "```sql",
        f"CREATE {kind_verb} {row['proname']}({row['args']})",
        "```",
        "\n**Definizione completa:**\n",
        "```sql",
        (row.get("defn") or "").strip(),
    ]
    obj_comment = row.get("obj_comment")
    if obj_comment:
        lines += [
            "",
            f"COMMENT ON {kind_verb} {schema}.{row['proname']}({row['args']})",
            f"IS {sql_literal(obj_comment)};"
        ]
    lines += ["```"]
    return "\n".join(lines)

def gen_function_md_V1(schema, func, cur):
    cur.execute(
        """
        SELECT p.proname,
               pg_get_function_identity_arguments(p.oid) AS args,
               pg_get_functiondef(p.oid) AS defn
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = %s AND p.proname = %s
        """, (schema, func)
    )
    row = cur.fetchone()
    if not row:
        return ""
    lines = [f"# ⚙️ Funzione `{row['proname']}`\n", "```sql", f"CREATE FUNCTION {row['proname']}({row['args']})", "```", "\n**Definizione completa:**\n", "```sql", row.get("defn", "").strip(), "```"]
    return "\n".join(lines)


# NUOVA: Genera Markdown per view
def _matview_indexes_md(schema, view, cur):
    """Indici di una materializzata.

    Non e' un dettaglio da appassionati: senza almeno un indice UNIQUE su tutte
    le righe, PostgreSQL rifiuta `REFRESH MATERIALIZED VIEW CONCURRENTLY` e
    l'unico aggiornamento possibile prende un lock esclusivo, cioe' blocca chi
    sta leggendo. Chi consulta questa pagina per capire come si aggiorna la
    vista deve trovarci la risposta, non doverla cercare in pg_index.
    """
    cur.execute(
        """
        SELECT i.relname AS nome,
               idx.indisunique AS unico,
               pg_get_indexdef(idx.indexrelid) AS definizione
        FROM pg_index idx
        JOIN pg_class i ON i.oid = idx.indexrelid
        JOIN pg_class c ON c.oid = idx.indrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relname = %s
        ORDER BY i.relname
        """,
        (schema, view)
    )
    rows = cur.fetchall()
    out = ["## Indici\n"]
    if not rows:
        out.append(
            "Nessun indice. ⚠️ Senza un indice **UNIQUE** su tutte le righe, "
            "`REFRESH MATERIALIZED VIEW CONCURRENTLY` non e' utilizzabile: "
            "l'aggiornamento prende un lock esclusivo e blocca le letture.\n"
        )
        return out

    out.append("| Indice | Unico | Definizione |")
    out.append("| --- | --- | --- |")
    for r in rows:
        out.append(f"| `{r['nome']}` | {'✅' if r['unico'] else '—'} | `{r['definizione']}` |")
    out.append("")

    if any(r['unico'] for r in rows):
        unici = ", ".join(f"`{r['nome']}`" for r in rows if r['unico'])
        out.append(
            f"> ✅ L'indice unico ({unici}) abilita "
            "`REFRESH MATERIALIZED VIEW CONCURRENTLY`, che aggiorna senza "
            "bloccare chi legge. Toglierlo non romperebbe le query, ma "
            "renderebbe ogni aggiornamento bloccante — un guasto che si "
            "manifesta in esercizio e non in sviluppo.\n"
        )
    else:
        out.append(
            "> ⚠️ Nessuno degli indici e' UNIQUE, quindi "
            "`REFRESH MATERIALIZED VIEW CONCURRENTLY` non e' utilizzabile e "
            "l'aggiornamento blocca le letture.\n"
        )
    return out


def gen_view_md(schema, view, cur):
    if DOCS_MINIMAL:
        return ""
    # ⚠️ La definizione si prende da pg_class/pg_get_viewdef e NON da pg_views.
    #    pg_views contiene solo le viste normali: le MATERIALIZZATE stanno in
    #    pg_matviews, quindi con la query precedente `mv_ddt_ordini` tornava
    #    riga vuota e la sua pagina non veniva mai scritta. pg_get_viewdef
    #    funziona per entrambe, e relkind ci dice quale DDL stampare.
    cur.execute(
        """
        SELECT c.relkind,
               -- Senza il flag "pretty": e' la forma che usa pg_views, quindi
               -- le pagine delle 49 viste gia' esistenti restano identiche al
               -- byte. Con pretty=true la definizione e' molto piu' leggibile
               -- (spariscono i (((...))) annidati) ma cambierebbero 98 file in
               -- un colpo: e' un miglioramento a se', non da infilare qui.
               pg_get_viewdef(c.oid) AS definition,
               c.relispopulated
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relname = %s AND c.relkind IN ('v', 'm')
        """,
        (schema, view)
    )
    row = cur.fetchone()
    if not row:
        return ""
    definition = row['definition']
    is_matview = (row['relkind'] == 'm')
    is_populated = row['relispopulated']

    # Reloptions della vista (security_invoker / security_barrier) NON compaiono
    # in pg_get_viewdef / pg_views.definition: sono opzioni dell'oggetto,
    # memorizzate in pg_class.reloptions. Le estraiamo e le ripristiniamo sia
    # nella clausola WITH (...) del CREATE sia in una nota, cosi' la doc non
    # nasconde piu' il fatto che la vista gira in security_invoker (RLS).
    cur.execute(
        """
        SELECT c.reloptions
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relname = %s AND c.relkind IN ('v', 'm')
        """,
        (schema, view)
    )
    opt_row = cur.fetchone()
    reloptions = (opt_row['reloptions'] if opt_row else None) or []
    sec_opts = [
        o for o in reloptions
        if o.startswith('security_invoker') or o.startswith('security_barrier')
    ]
    with_clause = f"\nWITH ({', '.join(sec_opts)})" if sec_opts else ""

    lines = [f"# 🔍 {'Materialized view' if is_matview else 'View'} `{view}`\n"]
    if sec_opts:
        lines.append(
            f"> 🔒 **Opzioni di sicurezza**: `{', '.join(sec_opts)}` — "
            "reloption non visibile in `pg_get_viewdef`, riportata qui "
            "esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE "
            "VIEW`, altrimenti PostgreSQL la azzera.\n"
        )

    if is_matview:
        # Una materializzata e' dato fermo: chi la legge deve sapere che il
        # contenuto ha una data, e da cosa dipende il fatto che sia aggiornato.
        lines.append(
            "> 🧊 **Vista MATERIALIZZATA**: il contenuto e' una copia salvata su "
            "disco, non una query eseguita al momento. Risponde veloce ma "
            "risponde con quello che c'era all'ultimo `REFRESH`: se il dato "
            "sottostante e' cambiato dopo, qui non si vede ancora. Non si "
            "modifica con `CREATE OR REPLACE` — va cancellata e ricreata.\n"
        )
        if not is_populated:
            lines.append(
                "> ⚠️ **Attualmente NON popolata** (`WITH NO DATA`): ogni "
                "interrogazione fallisce finche' non viene eseguito un "
                "`REFRESH MATERIALIZED VIEW`.\n"
            )

    lines.append("```sql")
    if is_matview:
        lines.append(f"CREATE MATERIALIZED VIEW {schema}.{view} AS")
    else:
        lines.append(f"CREATE OR REPLACE VIEW {schema}.{view}{with_clause} AS")
    lines.append(definition.strip())
    lines.append("```\n")

    if is_matview:
        lines.extend(_matview_indexes_md(schema, view, cur))
    # include manual se esiste
    #manual = include_manual(schema, 'views', view)
    #return manual + "\n".join(lines)
    return "\n".join(lines)
 
def write_docs_for_schema(schema, cur):
    schema_dir = os.path.join(OUT_DIR, schema)
    os.makedirs(os.path.join(schema_dir, "tabelle"), exist_ok=True)
    os.makedirs(os.path.join(schema_dir, "funzioni"), exist_ok=True)
    os.makedirs(os.path.join(schema_dir, "views"), exist_ok=True)
    os.makedirs(os.path.join(schema_dir, "manual"), exist_ok=True)
    
    SIGNATURE_INCLUDE = '{% include-markdown "signature-core.md" %}'
    FOOTER = f"\n\n---\n{SIGNATURE_INCLUDE}\n"


    # Tabelle
    cur.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_type='BASE TABLE'",
        (schema,)
    )
    for r in cur.fetchall():
        tbl = r['table_name']
        path = os.path.join(schema_dir, "tabelle", f"{tbl}.md")
        content = include_manual(schema, 'tabelle', tbl) + gen_table_md(schema, tbl, cur)
        # Aggiungi firma core in fondo
        content += FOOTER
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    
    # Funzioni (SOLO function, niente procedure qui)
    cur.execute(
        """
        SELECT routine_name
        FROM information_schema.routines
        WHERE specific_schema = %s
        AND routine_type = 'FUNCTION'
        ORDER BY routine_name;
        """,
        (schema,)
    )
    for r in cur.fetchall():
        fn = r['routine_name']
        path = os.path.join(schema_dir, "funzioni", f"{fn}.md")
        content = include_manual(schema, 'funzioni', fn) + gen_function_md(schema, fn, cur)
        content += FOOTER
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
    # 👇 AGGIUNGI SUBITO QUI IL BLOCCO PER LE PROCEDURE
    # (le salviamo comunque in funzioni/, manual flat in /<schema>/manual)
    cur.execute("""
        SELECT DISTINCT p.proname AS procedure_name
        FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = %s
        AND p.prokind = 'p'          -- 'p' = procedure (PG >= 11)
        ORDER BY 1;
    """, (schema,))

    for r in cur.fetchall():
        proc = r["procedure_name"]
        path = os.path.join(schema_dir, "funzioni", f"{proc}.md")

        # Manuale: rimane flat in /<schema>/manual, come per le funzioni
        content = include_manual(schema, 'funzioni', proc) + gen_function_md(schema, proc, cur)
        content += FOOTER

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    # ☝️ FINE BLOCCO PROCEDURE
    # Views — normali E materializzate.
    # ⚠️ information_schema.views NON contiene le materializzate: non sono
    #    nello standard SQL, sono un'estensione PostgreSQL. Con la query
    #    precedente l'unica materializzata del database (vendite.mv_ddt_ordini)
    #    non veniva mai scoperta e la sua pagina non e' mai esistita — senza
    #    che nulla segnalasse la mancanza. Si interroga pg_class, dove
    #    relkind 'v' = vista, 'm' = materializzata.
    cur.execute(
        """
        SELECT c.relname AS view_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relkind IN ('v', 'm')
        ORDER BY c.relname
        """,
        (schema,)
    )
    for r in cur.fetchall():
        vw = r['view_name']
        path = os.path.join(schema_dir, "views", f"{vw}.md")
        content = include_manual(schema, 'views', vw) + gen_view_md(schema, vw, cur)
        # Aggiungi firma core in fondo
        content += FOOTER
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    # Genera indice includendo tabelle, funzioni e view
    write_index(schema_dir, schema)
    # Genera indice CI con solo contenuti manuali
    write_index_ci(schema_dir, schema)

def extract_scopo(text):
    m = re.search(
        r"###\s*(?:🎯\s*)?(?:Scopo Principale|Scopo principale)\s*(.+?)(?=(?:\r?\n###|$))",
        text,
        flags=re.DOTALL
    )
    if not m:
        return ""
    full_scopo = m.group(1).strip()
    paragraph = full_scopo.split('\n\n', 1)[0]
    return paragraph.replace('\n', ' ')


def add_entries_from_dir(dir_path, title, link_prefix, manual_dir, lines):
    if not os.path.isdir(dir_path):
        return
    lines.append(title)
    for fname in sorted(os.listdir(dir_path)):
        if not fname.endswith('.md'):
            continue
        name = os.path.splitext(fname)[0]
        entry = f"- [{name}]({link_prefix}/{fname})"

        manual_file = os.path.join(manual_dir, f"{name}.md")
        if os.path.isfile(manual_file):
            with open(manual_file, encoding='utf-8') as fh:
                scopo = extract_scopo(fh.read())
            if scopo:
                entry += f" — {scopo}"
        lines.append(entry)
    lines.append('')

# Scrive index.md per schema
def write_index(schema_dir, schema):
    index_path  = os.path.join(schema_dir, 'index.md')
    tables_dir  = os.path.join(schema_dir, 'tabelle')
    funcs_dir   = os.path.join(schema_dir, 'funzioni')
    manual_dir  = os.path.join(schema_dir, 'manual')
    views_dir   = os.path.join(schema_dir, 'views')

    lines = [f"# Schema `{schema}`\n"]

    # 1. Tabelle con Scopo Principale
    if os.path.isdir(tables_dir):
        lines.append('## 📚 Tabelle')
        for fname in sorted(os.listdir(tables_dir)):
            if not fname.endswith('.md'):
                continue
            name  = os.path.splitext(fname)[0]
            entry = f"- [{name}](tabelle/{fname})"

            # cerca manual/<schema>/manual/<name>.md
            manual_file = os.path.join(manual_dir, f"{name}.md")
            if os.path.isfile(manual_file):
                text = open(manual_file, encoding='utf-8').read()
                scopo = extract_scopo(text)
                if scopo:
                    entry += f" — {scopo}"
            lines.append(entry)
        lines.append('')
    # Uso per funzioni
    add_entries_from_dir(funcs_dir, "## ⚙️ Funzioni", "funzioni", manual_dir, lines)

    # Uso per procedure (se stessa cartella, puoi filtrare per nome se serve)
    #add_entries_from_dir(funcs_dir, "## ⚙️ Procedura", "funzioni", manual_dir, lines)
    # 2. Funzioni con Scopo Principale
    #if os.path.isdir(funcs_dir):
    #    lines.append('## ⚙️ Funzioni')
    #    for fname in sorted(os.listdir(funcs_dir)):
    #        if not fname.endswith('.md'):
    #            continue
    #        name  = os.path.splitext(fname)[0]
    #        entry = f"- [{name}](funzioni/{fname})"

            # Cerca il file manuale corrispondente
    #        manual_file = os.path.join(manual_dir, f"{name}.md")
    #        if os.path.isfile(manual_file):
    #            text = open(manual_file, encoding='utf-8').read()
                # Regex che cattura fino alla prossima intestazione o fine file,
                # gestendo sia \n che \r\n
    #            m = re.search(
    #                r"### 🎯 Scopo Principale\s*(.+?)(?=(?:\r?\n###|$))",
    #                text,
    #                flags=re.DOTALL
    #            )
    #            if m:
                    # Prendi la prima riga (fino al primo newline) per il sommario
                    #scopo = m.group(1).strip().splitlines()[0]
    #                full_scopo = m.group(1).strip()
                    # estrai il primo paragrafo (fino alla riga vuota)
    #                paragraph = full_scopo.split('\n\n', 1)[0]
                    # unisci le righe di quel paragrafo in un’unica stringa
    #                scopo = paragraph.replace('\n', ' ')
    #                entry += f" — {scopo}"
    #        lines.append(entry)
    #    lines.append('')

    # 3. Views con Scopo Principale
    if os.path.isdir(views_dir):
        lines.append('## 🔍 Views')
        for fname in sorted(os.listdir(views_dir)):
            if not fname.endswith('.md'):
                continue
            name = os.path.splitext(fname)[0]
            entry = f"- [{name}](views/{fname})"
            # come per tabelle/funzioni, estrai lo Scopo Principale dal manuale se esiste
            # Cerca il file manuale corrispondente
            manual_file = os.path.join(manual_dir, f"{name}.md")
            if os.path.isfile(manual_file):
                text = open(manual_file, encoding='utf-8').read()
                scopo = extract_scopo(text)
                if scopo:
                    entry += f" — {scopo}"
            lines.append(entry)
        lines.append('')



    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

def write_index_ci(schema_dir, schema):
    index_path = os.path.join(schema_dir, 'index.ci.md')
    tables_dir = os.path.join(schema_dir, 'tabelle')
    funcs_dir = os.path.join(schema_dir, 'funzioni')
    views_dir = os.path.join(schema_dir, 'views')
    manual_dir = os.path.join(schema_dir, 'manual')

    lines = [f"# Schema `{schema}`\n"]

    if not os.path.isdir(manual_dir):
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        return

    table_names = set()
    func_names = set()
    view_names = set()
    if os.path.isdir(tables_dir):
        table_names = {os.path.splitext(f)[0] for f in os.listdir(tables_dir) if f.endswith('.md')}
    if os.path.isdir(funcs_dir):
        func_names = {os.path.splitext(f)[0] for f in os.listdir(funcs_dir) if f.endswith('.md')}
    if os.path.isdir(views_dir):
        view_names = {os.path.splitext(f)[0] for f in os.listdir(views_dir) if f.endswith('.md')}

    manual_files = sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(manual_dir)
        if f.endswith('.md')
    )

    def add_manual_section(title, names):
        if not names:
            return
        lines.append(title)
        for name in sorted(names):
            manual_file = os.path.join(manual_dir, f"{name}.md")
            entry = f"- [{name}](manual/{name}.md)"
            if os.path.isfile(manual_file):
                with open(manual_file, encoding='utf-8') as fh:
                    scopo = extract_scopo(fh.read())
                if scopo:
                    entry += f" — {scopo}"
            lines.append(entry)
        lines.append('')

    add_manual_section("## 📚 Tabelle (manuale)", [n for n in manual_files if n in table_names])
    add_manual_section("## ⚙️ Funzioni (manuale)", [n for n in manual_files if n in func_names])
    add_manual_section("## 🔍 Views (manuale)", [n for n in manual_files if n in view_names])
    all_known = table_names | func_names | view_names
    add_manual_section(
        "## 📘 Altri contenuti manuali",
        [n for n in manual_files if n not in all_known],
    )

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


    
# Main
def main():
    conn = psycopg2.connect(dsn=DB_DSN, cursor_factory=DictCursor)
    cur = conn.cursor()
    for schema in schemas:
        write_docs_for_schema(schema, cur)
    cur.close()
    conn.close()

def main_v1():
    conn = psycopg2.connect(dsn=DB_DSN, cursor_factory=DictCursor)
    cur = conn.cursor()
    for schema in schemas:
        schema_dir = os.path.join(OUT_DIR, schema)
        os.makedirs(os.path.join(schema_dir, "tabelle"), exist_ok=True)
        os.makedirs(os.path.join(schema_dir, "funzioni"), exist_ok=True)
        os.makedirs(os.path.join(schema_dir, "manual"), exist_ok=True)

        # Tabelle
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type='BASE TABLE'
            """, (schema,)
        )
        for r in cur.fetchall():
            tbl = r['table_name']
            path = os.path.join(schema_dir, "tabelle", f"{tbl}.md")
            content = include_manual(schema, 'tabelle', tbl) + gen_table_md(schema, tbl, cur)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

        # Funzioni
        cur.execute(
            """
            SELECT routine_name
            FROM information_schema.routines
            WHERE specific_schema = %s
            """, (schema,)
        )
        for r in cur.fetchall():
            fn = r['routine_name']
            path = os.path.join(schema_dir, "funzioni", f"{fn}.md")
            content = include_manual(schema, 'funzioni', fn) + gen_function_md(schema, fn, cur)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

        write_index(schema_dir, schema)
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
