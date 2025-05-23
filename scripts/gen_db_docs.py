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


import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor


# 1) Carica .env (privato, non committato)
load_dotenv(dotenv_path="internal.env", override=True)

# 2) Carica .envgit (committato, fornisce DB_DOC_SCHEMAS e default DSN)
load_dotenv(dotenv_path="git.env", override=False)



# Dove generare i file
OUT_DIR = "docs/it/dbzero"

def gen_table_md(schema, table, cur):
    # Estrai i campi
    cur.execute("""
      SELECT column_name, data_type, is_nullable, column_default
      FROM information_schema.columns
      WHERE table_schema=%s AND table_name=%s
      ORDER BY ordinal_position
    """, (schema, table))
    cols = cur.fetchall()
    # Costruisci Markdown
    md = [f"# Tabella `{table}`\n",
          "| Colonna | Tipo | Nullable | Default |",
          "|---------|------|----------|---------|"]
    for col in cols:
        default = col["column_default"] or ""
        md.append(f"| {col['column_name']} | {col['data_type']} | {col['is_nullable']} | {default} |")
    return "\n".join(md)

def gen_function_md(schema, func, cur):
    # Estrai signature e definizione
    cur.execute("""
      SELECT p.proname,
             pg_get_function_identity_arguments(p.oid) AS args,
             pg_get_functiondef(p.oid) AS defn
      FROM pg_proc p
      JOIN pg_namespace n ON p.pronamespace = n.oid
      WHERE n.nspname = %s AND p.proname = %s
    """, (schema, func))
    row = cur.fetchone()
    if not row: return ""
    md = [f"# Funzione `{row['proname']}`\n",
          "```sql",
          f"CREATE FUNCTION {row['proname']}({row['args']})",
          "```",
          "\n**Definizione completa:**\n",
          "```sql",
          row["defn"].strip(),
          "```"]
    return "\n".join(md)

def main():
    conn = psycopg2.connect(dsn=DB_DSN, cursor_factory=DictCursor)
    cur = conn.cursor()

    # Lista schemi
    schemas = ["anagrafiche","config","dbops","script","storico","public","topology"]
    for schema in schemas:
        schema_dir = os.path.join(OUT_DIR, schema)
        os.makedirs(os.path.join(schema_dir, "tabelle"), exist_ok=True)
        os.makedirs(os.path.join(schema_dir, "funzioni"), exist_ok=True)

        # Tabelle
        cur.execute("""
          SELECT table_name
          FROM information_schema.tables
          WHERE table_schema = %s AND table_type='BASE TABLE'
        """, (schema,))
        for r in cur.fetchall():
            name = r["table_name"]
            md = gen_table_md(schema, name, cur)
            path = os.path.join(schema_dir, "tabelle", f"{name}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"Generata tabella: {schema}.tabelle.{name}")

        # Funzioni
        cur.execute("""
          SELECT routine_name
          FROM information_schema.routines
          WHERE specific_schema = %s
        """, (schema,))
        for r in cur.fetchall():
            name = r["routine_name"]
            md = gen_function_md(schema, name, cur)
            path = os.path.join(schema_dir, "funzioni", f"{name}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"Generata funzione: {schema}.funzioni.{name}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
