# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Liquibase changelog per Zero ERP
# Copyright (C) 2025 Tid (Michele Carlo Titini) 
#
# Rilasciato sotto GNU GPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------

## Autogenerazione della documentazione delle tabelle e delle funzioni

#1. Si collega al tuo database PostgreSQL  
#2. Estrae da `information_schema.columns` i campi di ogni tabella  
#3. Estrae da `information_schema.routines` (e `pg_get_function_identity_arguments` / `pg_get_functiondef`) le signature delle funzioni  
#4. Produce per ciascuna tabella un file Markdown con la sezione “Campi principali” e per ciascuna funzione un file con “Signature” e “Descrizione”

#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor

# Directory del file script e root del progetto
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))

# 1) Carica internal.env dal root (privato, non committato)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, "internal.env"), override=True)

# 2) Carica git.env dal root (committato)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, "git.env"), override=False)

# Costruiamo la stringa di connessione completa (DSN)
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

# Lista degli schemi da documentare
db_schemas = os.getenv("DB_DOC_SCHEMAS", "")
schemas = [s.strip() for s in db_schemas.split(",") if s.strip()]

# Directory di output dei file markdown (path assoluto)
OUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "docs", "it", "dbzero"))

def gen_table_md(schema, table, cur):
    cur.execute(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s
        ORDER BY ordinal_position
        """, (schema, table)
    )
    cols = cur.fetchall()
    md = [f"# Tabella `{table}`\n",
          "| Colonna | Tipo | Nullable | Default |",
          "|---------|------|----------|---------|"]
    for col in cols:
        default = col.get("column_default") or ""
        md.append(f"| {col['column_name']} | {col['data_type']} | {col['is_nullable']} | {default} |")
    return "\n".join(md)

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
    md = [f"# Funzione `{row['proname']}`\n",
          "```sql",
          f"CREATE FUNCTION {row['proname']}({row['args']})",
          "```",
          "\n**Definizione completa:**\n",
          "```sql",
          row.get("defn", "").strip(),
          "```"]
    return "\n".join(md)

def write_index(schema_dir, schema):
    # Genera index.md per uno schema
    index_path = os.path.join(schema_dir, 'index.md')
    tables_dir = os.path.join(schema_dir, 'tabelle')
    funcs_dir = os.path.join(schema_dir, 'funzioni')
    lines = [f"# Schema `{schema}`\n"]
    # Elenco tabelle
    if os.path.isdir(tables_dir):
        lines.append('## Tabelle')
        for fname in sorted(os.listdir(tables_dir)):
            if fname.endswith('.md'):
                name = os.path.splitext(fname)[0]
                lines.append(f"- [{name}](tabelle/{fname})")
        lines.append('')
    # Elenco funzioni
    if os.path.isdir(funcs_dir):
        lines.append('## Funzioni')
        for fname in sorted(os.listdir(funcs_dir)):
            if fname.endswith('.md'):
                name = os.path.splitext(fname)[0]
                lines.append(f"- [{name}](funzioni/{fname})")
        lines.append('')
    # Scrivi file
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def main():
    conn = psycopg2.connect(dsn=DB_DSN, cursor_factory=DictCursor)
    cur = conn.cursor()

    for schema in schemas:
        schema_dir = os.path.join(OUT_DIR, schema)
        os.makedirs(os.path.join(schema_dir, "tabelle"), exist_ok=True)
        os.makedirs(os.path.join(schema_dir, "funzioni"), exist_ok=True)

        # Tabelle
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type='BASE TABLE'
            """, (schema,)
        )
        for r in cur.fetchall():
            tbl = r.get("table_name")
            md = gen_table_md(schema, tbl, cur)
            path = os.path.join(schema_dir, "tabelle", f"{tbl}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)

        # Funzioni
        cur.execute(
            """
            SELECT routine_name
            FROM information_schema.routines
            WHERE specific_schema = %s
            """, (schema,)
        )
        for r in cur.fetchall():
            fn = r.get("routine_name")
            md = gen_function_md(schema, fn, cur)
            path = os.path.join(schema_dir, "funzioni", f"{fn}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)

        # Genera index.md nello schema
        write_index(schema_dir, schema)

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
