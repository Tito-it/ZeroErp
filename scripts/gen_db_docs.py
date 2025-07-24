# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
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
DOCS_DIR = os.path.join(BASE_DIR, "docs")
OUT_DIR = os.path.join(DOCS_DIR, "it", "dbzero")


# Include manuale
def include_manual(schema, kind, name):
    manual_path = os.path.join(OUT_DIR, schema, "manual", f"{name}.md")
    if os.path.isfile(manual_path):
        rel = os.path.relpath(manual_path, start=DOCS_DIR).replace('\\', '/')
        return f"{{% include-markdown \"{rel}\" %}}\n"
    return ""

# Genera Markdown tabella con colonne, vincoli, indici, trigger
def gen_table_md(schema, table, cur):
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
        SELECT tc.constraint_type, tc.constraint_name,
               string_agg(kcu.column_name, ', ') AS columns
        FROM information_schema.table_constraints tc
        LEFT JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
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
def gen_view_md(schema, view, cur):
    # Ottiene la definizione della view
    cur.execute(
        "SELECT definition FROM pg_views WHERE schemaname=%s AND viewname=%s",
        (schema, view)
    )
    row = cur.fetchone()
    if not row:
        return ""
    definition = row['definition']
    lines = [f"# 🔍 View `{view}`\n"]
    lines.append("```sql")
    lines.append(f"CREATE OR REPLACE VIEW {schema}.{view} AS")
    lines.append(definition.strip())
    lines.append("```\n")
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

    # Tabelle
    cur.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_type='BASE TABLE'",
        (schema,)
    )
    for r in cur.fetchall():
        tbl = r['table_name']
        path = os.path.join(schema_dir, "tabelle", f"{tbl}.md")
        content = include_manual(schema, 'tabelle', tbl) + gen_table_md(schema, tbl, cur)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    # Funzioni
    cur.execute(
        "SELECT routine_name FROM information_schema.routines WHERE specific_schema=%s",
        (schema,)
    )
    for r in cur.fetchall():
        fn = r['routine_name']
        path = os.path.join(schema_dir, "funzioni", f"{fn}.md")
        content = include_manual(schema, 'funzioni', fn) + gen_function_md(schema, fn, cur)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    # Views
    cur.execute(
        "SELECT table_name as view_name FROM information_schema.views WHERE table_schema=%s",
        (schema,)
    )
    for r in cur.fetchall():
        vw = r['view_name']
        path = os.path.join(schema_dir, "views", f"{vw}.md")
        content = include_manual(schema, 'views', vw) + gen_view_md(schema, vw, cur)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    # Genera indice includendo tabelle, funzioni e view
    write_index(schema_dir, schema)

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
                m = re.search(
                    r"### 🎯 Scopo Principale\s*(.+?)(?=(?:\r?\n###|$))",
                    text,
                    flags=re.DOTALL
                )
                if m:
                    full_scopo = m.group(1).strip()
                    # prendi il primo paragrafo
                    paragraph = full_scopo.split('\n\n', 1)[0]
                    scopo = paragraph.replace('\n', ' ')
                    entry += f" — {scopo}"
            lines.append(entry)
        lines.append('')

    # 2. Funzioni con Scopo Principale
    if os.path.isdir(funcs_dir):
        lines.append('## ⚙️ Funzioni')
        for fname in sorted(os.listdir(funcs_dir)):
            if not fname.endswith('.md'):
                continue
            name  = os.path.splitext(fname)[0]
            entry = f"- [{name}](funzioni/{fname})"

            # Cerca il file manuale corrispondente
            manual_file = os.path.join(manual_dir, f"{name}.md")
            if os.path.isfile(manual_file):
                text = open(manual_file, encoding='utf-8').read()
                # Regex che cattura fino alla prossima intestazione o fine file,
                # gestendo sia \n che \r\n
                m = re.search(
                    r"### 🎯 Scopo Principale\s*(.+?)(?=(?:\r?\n###|$))",
                    text,
                    flags=re.DOTALL
                )
                if m:
                    # Prendi la prima riga (fino al primo newline) per il sommario
                    #scopo = m.group(1).strip().splitlines()[0]
                    full_scopo = m.group(1).strip()
                    # estrai il primo paragrafo (fino alla riga vuota)
                    paragraph = full_scopo.split('\n\n', 1)[0]
                    # unisci le righe di quel paragrafo in un’unica stringa
                    scopo = paragraph.replace('\n', ' ')
                    entry += f" — {scopo}"
            lines.append(entry)
        lines.append('')

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
                # Regex che cattura fino alla prossima intestazione o fine file,
                # gestendo sia \n che \r\n
                m = re.search(
                    r"### 🎯 Scopo Principale\s*(.+?)(?=(?:\r?\n###|$))",
                    text,
                    flags=re.DOTALL
                )
                if m:
                    # Prendi la prima riga (fino al primo newline) per il sommario
                    #scopo = m.group(1).strip().splitlines()[0]
                    full_scopo = m.group(1).strip()
                    # estrai il primo paragrafo (fino alla riga vuota)
                    paragraph = full_scopo.split('\n\n', 1)[0]
                    # unisci le righe di quel paragrafo in un’unica stringa
                    scopo = paragraph.replace('\n', ' ')
                    entry += f" — {scopo}"
            lines.append(entry)
        lines.append('')



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
