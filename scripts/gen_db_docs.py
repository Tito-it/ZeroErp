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
import psycopg
from psycopg.rows import dict_row

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


def _descrizione_md(commento):
    """Il COMMENT dell'oggetto, reso leggibile in cima alla sua pagina.

    ⚠️ PERCHE' ESISTE (2026-08-08). Il generatore leggeva `obj_description`
    soltanto per `pg_proc`. Le pagine di TABELLE e VISTE mostravano colonne,
    vincoli e indici — e nemmeno una riga su *cosa sia* l'oggetto. Misurato
    prima di scriverlo: **347 tabelle e 79 viste** hanno un COMMENT, per circa
    **73.000 caratteri** di spiegazione gia' scritta, leggibile da psql (`\\d+`)
    e da nessuna parte nella documentazione — che e' proprio il posto dove la
    regola di casa manda a guardare per prima cosa («doc auto-gen first»).
    La ragione c'era, ma non dove passa il lettore.

    ⚠️ `<` e `>` vanno neutralizzati. Markdown lascia passare l'HTML grezzo, e
    **29 commenti** contengono forme come `identita_digitale <-> scope`: senza
    escape il renderer se le mangia come se fossero tag, e la frase arriva
    monca senza che nulla protesti. Verificato che il resto non serve: nessun
    commento contiene `&` (quindi non c'e' l'ordine di escape da rispettare),
    nessuno ha `#` a inizio riga, nessuno ha righe vuote — i 9 con a-capo sono
    un unico paragrafo, ed e' la resa giusta.

    Blockquote e non sezione: la mediana e' 74 caratteri, cioe' quasi sempre una
    riga sola, e segue la forma gia' usata in questa pagina per le note
    sull'oggetto (`> 🔒 Opzioni di sicurezza`, `> 🧊 Vista materializzata`).
    """
    if not commento:
        return []
    testo = str(commento).replace("<", "&lt;").replace(">", "&gt;")
    righe = [f"> {r}" if r.strip() else ">" for r in testo.splitlines()]
    return ["> 📝 **Descrizione**", ">"] + righe + [""]


# Genera Markdown tabella con colonne, vincoli, indici, trigger
def gen_table_md(schema, table, cur):
    if DOCS_MINIMAL:
        return ""
    lines = [f"# 📚 Tabella `{table}`\n"]
    # Il COMMENT della tabella: sta in pg_class, non in information_schema.
    cur.execute(
        """
        SELECT obj_description(c.oid, 'pg_class') AS commento
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relname = %s AND c.relkind = 'r'
        """, (schema, table)
    )
    cmt_row = cur.fetchone()
    lines += _descrizione_md(cmt_row["commento"] if cmt_row else None)
    # Colonne
    # Il tipo si prende da format_type(atttypid, atttypmod) e NON da
    # information_schema.columns.data_type, che toglie il typmod: «numeric» per
    # numeric(18,6) e numeric(15,2), «character varying» senza lunghezza,
    # «USER-DEFINED» per un enum, «ARRAY» per un array. La scala di un numeric
    # e' contratto: chi copia un valore da una colonna all'altra deve vederla
    # (2026-10-04, la quota del plafond calcolata a 6 decimali e scritta a 2).
    cur.execute(
        """
        SELECT c.column_name,
               format_type(a.atttypid, a.atttypmod) AS data_type,
               c.is_nullable, c.column_default
        FROM information_schema.columns c
        JOIN pg_attribute a
          ON a.attrelid = format('%%I.%%I', c.table_schema, c.table_name)::regclass
         AND a.attname = c.column_name
        WHERE c.table_schema=%s AND c.table_name=%s
        ORDER BY c.ordinal_position
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
# Avvolge un blocco di codice in un riquadro escluso dalla ricerca. Zensical
# indicizza ogni sezione come un solo campo e rifiuta quelli oltre 16 KB
# (zensical 0.0.71): il corpo intero di una funzione o di una vista lo supera e
# ferma la build. Il testo della pagina resta cercabile, il codice no.
# ⚠️ Serve l'estensione `md_in_html` in mkdocs.yml: senza, il riquadro e' HTML
#   grezzo e il blocco di codice dentro non viene interpretato.
def _fuori_dalla_ricerca(lines):
    return ["<div data-search-exclude markdown>", ""] + lines + ["", "</div>"]

def gen_function_md(schema, func, cur):
    # ⚠️ UNA PAGINA PER NOME, UN BLOCCO PER FIRMA (2026-10-14). Prima la query
    #   chiudeva con `LIMIT 1` e senza `ORDER BY`: di due firme dello stesso
    #   nome ne usciva una sola, e nemmeno sempre la stessa. Il caso che l'ha
    #   mostrato: `maintenance.proc_apply_fk_index_policy_job` ha `()` e
    #   `(p_populate boolean)`, il job pgAgent chiama la seconda e la pagina
    #   mostrava la prima. Con una firma sola l'output e' identico a prima.
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
        ORDER BY pg_get_function_identity_arguments(p.oid)
    """, (schema, func))
    rows = cur.fetchall()
    if not rows:
        return ""

    def _blocco(row):
        kind_verb = "PROCEDURE" if row["prokind"] == "p" else "FUNCTION"
        lines = [
            "```sql",
            f"CREATE {kind_verb} {row['proname']}({row['args']})",
            "```",
            "\n**Definizione completa:**\n",
        ]
        corpo = [
            "```sql",
            (row.get("defn") or "").strip(),
        ]
        obj_comment = row.get("obj_comment")
        if obj_comment:
            corpo += [
                "",
                f"COMMENT ON {kind_verb} {schema}.{row['proname']}({row['args']})",
                f"IS {sql_literal(obj_comment)};"
            ]
        corpo += ["```"]
        return lines + _fuori_dalla_ricerca(corpo)

    kind_label = "Procedura" if rows[0]["prokind"] == "p" else "Funzione"
    lines = [f"# ⚙️ {kind_label} `{rows[0]['proname']}`\n"]
    if len(rows) == 1:
        lines += _blocco(rows[0])
    else:
        lines += [
            f"> ⚠️ **{len(rows)} firme** con lo stesso nome: ognuna ha il suo "
            "blocco qui sotto, in ordine di argomenti.",
            "",
        ]
        for row in rows:
            lines += [f"## Firma `({row['args']})`\n"] + _blocco(row) + [""]
    return "\n".join(lines).rstrip("\n")

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
               c.relispopulated,
               -- Il COMMENT della vista: spesso e' l'unico posto dove sta
               -- scritto COME si usa (le query canoniche, i limiti della
               -- misura). Fino al 2026-08-08 non arrivava in pagina.
               obj_description(c.oid, 'pg_class') AS commento
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
        if o.startswith(('security_invoker', 'security_barrier'))
    ]
    with_clause = f"\nWITH ({', '.join(sec_opts)})" if sec_opts else ""

    lines = [f"# 🔍 {'Materialized view' if is_matview else 'View'} `{view}`\n"]
    # Prima cosa dopo il titolo: che cos'e'. Le note su sicurezza e
    # materializzazione vengono dopo — sono qualificazioni, non l'identita'.
    lines += _descrizione_md(row.get("commento"))
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

    corpo = ["```sql"]
    if is_matview:
        corpo.append(f"CREATE MATERIALIZED VIEW {schema}.{view} AS")
    else:
        corpo.append(f"CREATE OR REPLACE VIEW {schema}.{view}{with_clause} AS")
    corpo.append(definition.strip())
    corpo.append("```")
    lines.extend(_fuori_dalla_ricerca(corpo))
    lines.append("")

    if is_matview:
        lines.extend(_matview_indexes_md(schema, view, cur))
    # include manual se esiste
    #manual = include_manual(schema, 'views', view)
    #return manual + "\n".join(lines)
    return "\n".join(lines)
 
# Scopo: Cancella dalla cartella auto-generata i .md che non corrispondono a
#        nessun oggetto vivo — le "doc orfane" di oggetti droppati.
#
#   ⚠️ PERCHE' SERVE, ed e' costato una misura sbagliata il 2026-08-07.
#   Fino a quel giorno questo generatore SCRIVEVA soltanto: un oggetto droppato
#   lasciava la sua pagina in `docs/it/dbzero/<schema>/<tipo>/` per sempre. E
#   siccome `.codex/AGENTS.md` dice — giustamente — di prendere le definizioni
#   dalla doc auto-generata perche' «riflette l'oggetto VIVO nel DB», quelle
#   pagine mentivano nel modo peggiore: erano corrette nel contenuto e false
#   nell'esistenza. Dieci funzioni droppate fra il 4 e il 5 agosto avevano
#   ancora la loro pagina, e leggendole si concludeva che i loro codici errore
#   fossero ancora sollevati da qualcuno.
#
#   ⚠️ GUARDIA: si pota SOLO se l'insieme degli oggetti vivi non e' vuoto. Una
#   query che fallisce o un permesso mancante producono zero righe, e senza
#   questa guardia una cartella intera sparirebbe in silenzio. Meglio una doc
#   orfana in piu' che l'intera documentazione di uno schema in meno.
#
#   ⚠️ NON tocca mai `manual/`: quella la scrivono le persone.
def _pota_orfani(dir_path, vivi, etichetta):
    if not vivi:
        return  # guardia: vedi sopra
    if not os.path.isdir(dir_path):
        return
    for nome_file in sorted(os.listdir(dir_path)):
        if not nome_file.endswith(".md"):
            continue
        if nome_file[:-3] not in vivi:
            os.remove(os.path.join(dir_path, nome_file))
            print(f"  🗑️  doc orfana rimossa ({etichetta}): {nome_file}")


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
    tabelle_vive = set()
    for r in cur.fetchall():
        tbl = r['table_name']
        tabelle_vive.add(tbl)
        path = os.path.join(schema_dir, "tabelle", f"{tbl}.md")
        content = include_manual(schema, 'tabelle', tbl) + gen_table_md(schema, tbl, cur)
        # Aggiungi firma core in fondo
        content += FOOTER
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    
    # Funzioni (SOLO function, niente procedure qui)
    cur.execute(
        """
        SELECT DISTINCT routine_name
        FROM information_schema.routines
        WHERE specific_schema = %s
        AND routine_type = 'FUNCTION'
        ORDER BY routine_name;
        """,
        (schema,)
    )
    funzioni_vive = set()
    for r in cur.fetchall():
        fn = r['routine_name']
        funzioni_vive.add(fn)
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
        funzioni_vive.add(proc)  # procedure e funzioni condividono la cartella
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
    viste_vive = set()
    for r in cur.fetchall():
        vw = r['view_name']
        viste_vive.add(vw)
        path = os.path.join(schema_dir, "views", f"{vw}.md")
        content = include_manual(schema, 'views', vw) + gen_view_md(schema, vw, cur)
        # Aggiungi firma core in fondo
        content += FOOTER
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    # Pota le doc di oggetti che non esistono piu'. DEVE stare qui, dopo tutte
    # le scritture e PRIMA degli indici: l'indice si costruisce leggendo le
    # cartelle, quindi potare dopo significherebbe indicizzare gli orfani.
    _pota_orfani(os.path.join(schema_dir, "tabelle"), tabelle_vive, f"{schema}/tabelle")
    _pota_orfani(os.path.join(schema_dir, "funzioni"), funzioni_vive, f"{schema}/funzioni")
    _pota_orfani(os.path.join(schema_dir, "views"), viste_vive, f"{schema}/views")

    # Genera indice includendo tabelle, funzioni e view
    write_index(schema_dir, schema)
    # Genera indice CI con solo contenuti manuali
    write_index_ci(schema_dir, schema)

# Dove l'index cerca il bersaglio di un link relativo della descrizione.
# `index.md` linka le pagine generate, `index.ci.md` le pagine manuali: sono due
# indici che vivono nella stessa cartella e puntano a due posti diversi.
_SOTTOCARTELLE_INDEX = ('funzioni', 'views', 'tabelle')
_SOTTOCARTELLE_INDEX_CI = ('manual',)


# Link markdown a un .md RELATIVO e senza cartella: `[testo](nome.md)` con
# eventuale ancora. Esclusi http(s), assoluti, `../` e le ancore pure.
_LINK_MD_NUDO_RE = re.compile(
    r"\]\((?!https?://|/|\.\./|#)([A-Za-z0-9_][A-Za-z0-9_.-]*\.md)(#[^)]*)?\)"
)


# Scopo: ⛔ RISCRIVE I LINK RELATIVI DELLA DESCRIZIONE COPIATA DA `manual/`.
#
#   Lo «Scopo Principale» viene preso da `<schema>/manual/<nome>.md` e incollato
#   **verbatim** in `<schema>/index.md`, che sta **una cartella piu' su**. Dentro
#   `manual/` un link `[fn_pubblica_definizione](fn_pubblica_definizione.md)` e'
#   CORRETTO — le due pagine sono sorelle — ma issato nell'index punta a una
#   cartella dove quel file non c'e'.
#
# ⚠️ Il difetto e' silenzioso: il link della VOCE viene prefissato dal
#   generatore (`funzioni/<nome>.md`), quello dentro la FRASE no. Solo il build
#   della doc se ne accorge, come warning, e nessuno lo lega alla sua causa —
#   segnalato nel brief fan-out il 2026-08-10 come «residuo preesistente, si
#   corregge nel generatore, una volta per tutti gli schemi». Misurato il
#   2026-08-26: **4 link morti**, tutti in `pratiche/index.md` e nel gemello
#   `index.ci.md`.
#
# ⚠️ Un nome non risolvibile si lascia **com'e'**: il generatore non inventa una
#   destinazione. Meglio un link che il build segnala di uno che punta altrove.
def _riscrivi_link_relativi(scopo, schema_dir, sottocartelle):
    if not scopo or not schema_dir or not sottocartelle:
        return scopo

    def _sub(m):
        fname, ancora = m.group(1), m.group(2) or ""
        for sub in sottocartelle:
            if os.path.isfile(os.path.join(schema_dir, sub, fname)):
                return f"]({sub}/{fname}{ancora})"
        return m.group(0)

    return _LINK_MD_NUDO_RE.sub(_sub, scopo)


# `schema_dir` + `sottocartelle` sono opzionali e la riscrittura vive QUI, non
# nei quattro punti che chiamano: la lettura dello «Scopo» e' una sola, e quattro
# copie della stessa riscrittura sarebbero quattro occasioni di divergere.
def extract_scopo(text, schema_dir=None, sottocartelle=()):
    m = re.search(
        r"###\s*(?:🎯\s*)?(?:Scopo Principale|Scopo principale)\s*(.+?)(?=(?:\r?\n###|$))",
        text,
        flags=re.DOTALL
    )
    if not m:
        return ""
    full_scopo = m.group(1).strip()
    paragraph = full_scopo.split('\n\n', 1)[0]
    return _riscrivi_link_relativi(
        paragraph.replace('\n', ' '), schema_dir, sottocartelle
    )


def add_entries_from_dir(dir_path, title, link_prefix, manual_dir, lines, schema_dir=None):
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
                scopo = extract_scopo(fh.read(), schema_dir, _SOTTOCARTELLE_INDEX)
            if scopo:
                entry += f" — {scopo}"
        lines.append(entry)
    lines.append('')

# La pagina dei job pgAgent (generata in locale, vedi gen_job_pgagent_md) si
# linka da ENTRAMBI gli indici: in CI la pagina non si rigenera (pgAgent non
# c'e'), ma quella committata resta ed e' autosufficiente.
def _link_job_pgagent(schema_dir, lines):
    if os.path.isfile(os.path.join(schema_dir, JOB_PGAGENT_FILE)):
        lines += ["## ⏰ Job pgAgent",
                  f"- [I job pgAgent]({JOB_PGAGENT_FILE}) — quali lavori a orario "
                  "esistono, quando partono e che cosa chiamano", ""]


# Front matter degli indici di schema: fuori dalla ricerca. Zensical indicizza
# ogni sezione `##` come un solo campo e rifiuta quelli oltre 16 KB (zensical
# 0.0.71): l'elenco «Funzioni» di uno schema grande lo supera e ferma la build.
# Il contenuto dell'indice e' solo navigazione: lo scopo di ogni oggetto e' gia'
# cercabile nella sua pagina.
_INDEX_FRONT_MATTER = "---\nsearch:\n  exclude: true\n---\n"

# Scrive index.md per schema
def write_index(schema_dir, schema):
    index_path  = os.path.join(schema_dir, 'index.md')
    tables_dir  = os.path.join(schema_dir, 'tabelle')
    funcs_dir   = os.path.join(schema_dir, 'funzioni')
    manual_dir  = os.path.join(schema_dir, 'manual')
    views_dir   = os.path.join(schema_dir, 'views')

    lines = [_INDEX_FRONT_MATTER, f"# Schema `{schema}`\n"]

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
                scopo = extract_scopo(text, schema_dir, _SOTTOCARTELLE_INDEX)
                if scopo:
                    entry += f" — {scopo}"
            lines.append(entry)
        lines.append('')
    # Uso per funzioni
    add_entries_from_dir(funcs_dir, "## ⚙️ Funzioni", "funzioni", manual_dir, lines, schema_dir)

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
                scopo = extract_scopo(text, schema_dir, _SOTTOCARTELLE_INDEX)
                if scopo:
                    entry += f" — {scopo}"
            lines.append(entry)
        lines.append('')

    _link_job_pgagent(schema_dir, lines)

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

def write_index_ci(schema_dir, schema):
    index_path = os.path.join(schema_dir, 'index.ci.md')
    tables_dir = os.path.join(schema_dir, 'tabelle')
    funcs_dir = os.path.join(schema_dir, 'funzioni')
    views_dir = os.path.join(schema_dir, 'views')
    manual_dir = os.path.join(schema_dir, 'manual')

    lines = [_INDEX_FRONT_MATTER, f"# Schema `{schema}`\n"]

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
                    scopo = extract_scopo(fh.read(), schema_dir, _SOTTOCARTELLE_INDEX_CI)
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
    _link_job_pgagent(schema_dir, lines)

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))



# ── I job pgAgent ────────────────────────────────────────────────────────────
# ⭐ PERCHE' ESISTE (2026-10-14, brief-db-ruoli-di-sistema). Lo schema `pgagent`
#   e' dell'estensione, e documentarne la STRUTTURA non dice niente: le sue
#   tabelle sono sempre le stesse. Cio' che serve e' il CONTENUTO — quali job
#   esistono, se sono accesi, quando partono, che cosa chiama ogni step — che
#   finora si leggeva solo da `postgres` o dai changeSet di 85_pgagent, dove
#   stanno anche le versioni storiche dei job.
# ⚠️ NIENTE ULTIMA/PROSSIMA CORSA. Cambiano a ogni giro: ogni rigenerazione
#   farebbe un diff falso. Lo stato vivo sta in dbops.vw_processi_programmazione.
# ⚠️ L'ORARIO e' quello di pgAgent, cioe' del server del database.
JOB_PGAGENT_SCHEMA = "maintenance"
JOB_PGAGENT_FILE = "job_pgagent.md"

_GIORNI = ["domenica", "lunedi'", "martedi'", "mercoledi'", "giovedi'", "venerdi'", "sabato"]
_MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


def _accesi(flags):
    """Gli indici a TRUE. ⚠️ Per pgAgent un array tutto FALSE vuol dire
    «nessun vincolo», come uno tutto TRUE: si rendono entrambi con None."""
    idx = [i for i, v in enumerate(flags or []) if v]
    if not idx or len(idx) == len(flags):
        return None
    return idx


def _quando(sch):
    minuti, ore = _accesi(sch["jscminutes"]), _accesi(sch["jschours"])
    giorni, mesi = _accesi(sch["jscweekdays"]), _accesi(sch["jscmonths"])
    giorni_mese = _accesi(sch["jscmonthdays"])

    if minuti is None and ore is None:
        orario = "ogni minuto"
    elif ore is None:
        orario = "ogni ora, al minuto " + ", ".join(f"{m:02d}" for m in minuti)
    elif minuti is None:
        orario = "ogni minuto delle ore " + ", ".join(f"{h:02d}" for h in ore)
    else:
        orario = "alle " + ", ".join(f"{h:02d}:{m:02d}" for h in ore for m in minuti)

    parti = [orario]
    if giorni is not None:
        parti.append("di " + ", ".join(_GIORNI[g] for g in giorni))
    if giorni_mese is not None:
        # l'indice 31 e' «l'ultimo giorno del mese»
        parti.append("il giorno " + ", ".join(
            "ultimo" if d == 31 else str(d + 1) for d in giorni_mese))
    if mesi is not None:
        parti.append("in " + ", ".join(_MESI[m] for m in mesi))
    if giorni is None and giorni_mese is None and mesi is None and ore is not None:
        parti.append("ogni giorno")
    return ", ".join(parti)


_CALL_PROC_RE = re.compile(r"^\s*CALL\s+([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)\s*\(", re.I)


def gen_job_pgagent_md(cur):
    """La pagina dei job pgAgent, o None se l'estensione non c'e'.

    ⛔ Se l'estensione c'e' ma l'utente non la puo' leggere, la generazione si
    FERMA: una pagina vuota sarebbe identica a «nessun job», cioe' la
    sottrazione silenziosa che `verifica_visibilita` rifiuta per i vincoli."""
    cur.execute("SELECT to_regclass('pgagent.pga_job') IS NOT NULL AS presente")
    if not cur.fetchone()["presente"]:
        return None
    cur.execute("SELECT has_schema_privilege('pgagent', 'USAGE') "
                "AND has_table_privilege('pgagent.pga_job', 'SELECT') "
                "AND has_table_privilege('pgagent.pga_schedule', 'SELECT') "
                "AND has_table_privilege('pgagent.pga_jobstep', 'SELECT') AS ok, "
                "current_user AS utente")
    r = cur.fetchone()
    if not r["ok"]:
        raise SystemExit(
            f"\n⛔ Documentazione NON generata: l'utente «{r['utente']}» non legge "
            f"lo schema pgagent, e la pagina dei job nascerebbe vuota — identica a "
            f"un database senza job. Rigenerare con l'utente proprietario del "
            f"database.\n")

    cur.execute("""
        SELECT j.jobid, j.jobname, j.jobdesc, j.jobenabled,
               (SELECT string_agg(p.codice, ', ' ORDER BY p.codice)
                  FROM dbops.processi p
                 WHERE p.jobname_pgagent = j.jobname) AS processi
          FROM pgagent.pga_job j
         ORDER BY j.jobname
    """)
    jobs = cur.fetchall()
    cur.execute("""
        SELECT jscjobid, jscname, jscenabled, jscminutes, jschours,
               jscweekdays, jscmonthdays, jscmonths
          FROM pgagent.pga_schedule
         ORDER BY jscjobid, jscname
    """)
    schedules = cur.fetchall()
    cur.execute("""
        SELECT jstjobid, jstname, jstenabled, jstkind, jstcode, jstdbname
          FROM pgagent.pga_jobstep
         ORDER BY jstjobid, jstname
    """)
    steps = cur.fetchall()

    def _codice(code):
        code = (code or "").strip()
        m = _CALL_PROC_RE.match(code)
        if m and m.group(1) == JOB_PGAGENT_SCHEMA and "\n" not in code:
            return f"[`{code}`](funzioni/{m.group(2)}.md)"
        if "\n" in code or "|" in code:
            return "vedi sotto"
        return f"`{code}`"

    lines = [
        "# ⏰ Job pgAgent\n",
        "> 📝 **Descrizione**",
        ">",
        "> I lavori a orario che pgAgent esegue in questo database: se sono accesi, "
        "quando partono (ora del server del database), che cosa chiama ogni step e "
        "quale processo di `dbops.processi` registrano. Pagina generata dalle tabelle "
        "di `pgagent`; l'ultima e la prossima corsa non ci sono apposta (cambiano a "
        "ogni giro): lo stato vivo e' in `dbops.vw_processi_programmazione`.",
        "",
        "| Job | Acceso | Quando | Processo |",
        "| --- | --- | --- | --- |",
    ]
    for j in jobs:
        quando = "; ".join(
            _quando(s) + ("" if s["jscenabled"] else " (spento)")
            for s in schedules if s["jscjobid"] == j["jobid"]) or "nessun orario"
        lines.append(
            f"| `{j['jobname']}` | {'si' if j['jobenabled'] else '**no**'} | {quando} | "
            f"{('`' + j['processi'] + '`') if j['processi'] else '**nessuno**'} |")
    lines.append("")

    for j in jobs:
        lines.append(f"## `{j['jobname']}`\n")
        if j["jobdesc"]:
            lines.append(str(j["jobdesc"]).replace("<", "&lt;").replace(">", "&gt;") + "\n")
        lines += ["| Step | Acceso | Tipo | Database | Chiama |",
                  "| --- | --- | --- | --- | --- |"]
        propri = [s for s in steps if s["jstjobid"] == j["jobid"]]
        for s in propri:
            tipo = "SQL" if s["jstkind"] == "s" else "batch"
            lines.append(
                f"| `{s['jstname']}` | {'si' if s['jstenabled'] else '**no**'} | {tipo} | "
                f"{s['jstdbname'] or '—'} | {_codice(s['jstcode'])} |")
        lines.append("")
        for s in propri:
            if _codice(s["jstcode"]) == "vedi sotto":
                lines += [f"Step `{s['jstname']}`:\n", "```sql",
                          (s["jstcode"] or "").strip(), "```", ""]
    return "\n".join(lines).rstrip("\n") + "\n"


def write_job_pgagent(cur):
    """Scrive (o pota) la pagina dei job sotto lo schema dei job."""
    if DOCS_MINIMAL or JOB_PGAGENT_SCHEMA not in schemas:
        return
    path = os.path.join(OUT_DIR, JOB_PGAGENT_SCHEMA, JOB_PGAGENT_FILE)
    contenuto = gen_job_pgagent_md(cur)
    if contenuto is None:
        # Senza l'estensione la pagina non descrive piu' niente di questo
        # database: si toglie, come gli orfani.
        if os.path.isfile(path):
            os.remove(path)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(contenuto + "\n---\n{% include-markdown \"signature-core.md\" %}\n")


def verifica_visibilita(cur):
    """Fallisce se l'utente collegato non vede tutto quello che deve scrivere.

    ⚠️ IL DIFETTO CHE PRESIDIA, misurato il 2026-08-08. `information_schema` NON
    e' il catalogo: e' una vista **filtrata dai permessi**. Le sue tabelle
    `table_constraints`, `triggers` e `columns` mostrano solo cio' su cui
    l'utente collegato ha un privilegio. Generando la doc con `zeroerp_app`
    (che su alcune tabelle ha il solo SELECT) **11 tabelle perdevano l'INTERA
    sezione «Vincoli»** — `maintenance.job_run_log` ha 8 vincoli in
    `pg_constraint` e zero in `information_schema` — e il generatore usciva **0**,
    scrivendo pagine mutilate senza dire niente.

    ⚠️ E' la stessa forma di guasto contro cui e' costruito mezzo progetto: non
    un errore, una **sottrazione silenziosa**. Peggio che altrove, perche' la
    regola di casa dice di fidarsi di queste pagine invece che degli YAML: una
    pagina a cui manca la sezione vincoli non si distingue da una tabella che
    vincoli non ne ha.

    Il confronto e' con `pg_constraint`, che e' il catalogo vero e NON e'
    filtrato dai permessi. Se i due non concordano, la doc non si scrive.

    ⚠️ Un secondo effetto dello stesso genere non e' un errore ma va conosciuto:
    `information_schema.triggers.action_statement` qualifica il nome della
    funzione secondo il **search_path** di chi interroga. Con `script` e `dbops`
    nel path, `script.trgfn_audit_data_user_generic()` diventa
    `trgfn_audit_data_user_generic()` e 3264 righe di doc cambiano senza che
    nulla sia cambiato nel database. La doc committata e' fatta con
    `search_path = public`: chi rigenera deve usare lo stesso, o produce un diff
    enorme e finto.
    """
    cur.execute(
        """
        WITH t AS (
            SELECT n.nspname AS sch, c.relname AS tab, c.oid
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r' AND n.nspname = ANY(%s)
        )
        SELECT t.sch, t.tab,
               (SELECT count(*) FROM pg_constraint k WHERE k.conrelid = t.oid) AS reali
        FROM t
        WHERE EXISTS (SELECT 1 FROM pg_constraint k WHERE k.conrelid = t.oid)
          AND NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                WHERE tc.table_schema = t.sch AND tc.table_name = t.tab)
        ORDER BY 1, 2
        """, (schemas,)
    )
    ciechi = cur.fetchall()
    if not ciechi:
        return
    # Per nome, non per posizione: con `dict_row` uno spacchettamento
    # `a, b = riga` restituisce le CHIAVI, non i valori, e non da' errore.
    cur.execute("SELECT current_user AS utente, current_setting('search_path') AS spath")
    r = cur.fetchone()
    utente, spath = r["utente"], r["spath"]
    esempi = "\n  ".join(
        f"{r['sch']}.{r['tab']} — {r['reali']} vincoli nel catalogo, 0 visibili"
        for r in ciechi[:8]
    )
    raise SystemExit(
        f"\n⛔ Documentazione NON generata: l'utente «{utente}» non vede tutto.\n\n"
        f"{len(ciechi)} tabelle hanno vincoli in pg_constraint e ZERO in "
        f"information_schema, che e' filtrato dai permessi. Le loro pagine "
        f"nascerebbero senza la sezione «Vincoli», identiche a quelle di una "
        f"tabella che vincoli non ne ha — una sottrazione silenziosa, non un "
        f"errore.\n\n  {esempi}\n\n"
        f"Rigenerare con l'utente proprietario del database.\n"
        f"(Il search_path lo fissa gia' main() a «public», ora e' «{spath}»: "
        f"quello non e' piu' un problema tuo.)\n"
    )


# Main
def main():
    # ⚠️ autocommit: in una transazione unica ogni `::regclass` lascia un
    #   AccessShareLock su ogni tabella fino alla fine del giro, e un DDL
    #   concorrente (migrate, pgTAP) finisce in deadlock con lo script.
    conn = psycopg.connect(DB_DSN, row_factory=dict_row, autocommit=True)
    cur = conn.cursor()
    # ⚠️ Il search_path NON puo' dipendere da chi lancia lo script.
    #   `information_schema.triggers.action_statement` qualifica il nome della
    #   funzione secondo il search_path di chi interroga: con `script` e `dbops`
    #   nel path (come li ha zeroerp_app) `script.trgfn_audit_data_user_generic()`
    #   diventa `trgfn_audit_data_user_generic()`, e 3264 righe di doc cambiano
    #   senza che nel database sia cambiato niente. Un diff enorme e falso e' il
    #   modo piu' rapido per far smettere di leggere i diff della doc.
    #   Fissarlo qui rende l'output identico per chiunque lo esegua; `public`
    #   perche' e' la forma con cui la doc committata e' stata scritta.
    cur.execute("SET search_path = public")
    verifica_visibilita(cur)
    # Prima degli schemi: l'indice di `maintenance` la linka se esiste.
    write_job_pgagent(cur)
    for schema in schemas:
        write_docs_for_schema(schema, cur)
    cur.close()
    conn.close()

def main_v1():
    conn = psycopg.connect(DB_DSN, row_factory=dict_row)
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
