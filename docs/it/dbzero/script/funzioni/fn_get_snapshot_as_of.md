{% include-markdown "it/dbzero/script/manual/fn_get_snapshot_as_of.md" %}
# ⚙️ Funzione `fn_get_snapshot_as_of`

```sql
CREATE FUNCTION fn_get_snapshot_as_of(p_schema text, p_table text, p_id text, p_fk_col text, p_as_of timestamp with time zone)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_snapshot_as_of(p_schema text, p_table text, p_id text, p_fk_col text, p_as_of timestamp with time zone)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
 DECLARE
   v_snapshot    JSONB;
   v_pk_type     TEXT;
   v_id_col      TEXT := 'id';                   -- colonna PK originaria
   v_hist_schema TEXT := 'storico';
   v_hist_table  TEXT := p_table;
   v_full_table  TEXT := format('%I.%I', v_hist_schema, v_hist_table);
 BEGIN
   -- -----------------------------------------------------
   -- Input
   -- p_schema: schema della tabella originaria
   -- p_table: nome della tabella originaria (e storica)
   -- p_id: PK del record originario, passato come TEXT
   -- p_fk_col: nome della colonna FK in storico (es. 'soggetto_id')
   -- p_as_of: istante di validita' desiderato (timestamptz, rev 20260920-05:
   --          prima era timestamp e il corpo lo castava col fuso di sessione)
   -- Output
   -- v_snapshot: JSONB del record al momento p_as_of
   -- Se non esiste, restituisce NULL
   -- Se non trova il record, solleva un'eccezione
   -- Altrimenti viene restituito il JSONB del record o dalla tabella originaria
   -- o dalla tabella storica, se esiste.
   -- -----------------------------------------------------

   -- Verifica che esista la tabella di storico
    SELECT format_type(a.atttypid, a.atttypmod)
     INTO v_pk_type
     FROM pg_attribute a
     JOIN pg_class c ON a.attrelid = c.oid
     JOIN pg_namespace n ON c.relnamespace = n.oid
     WHERE n.nspname = v_hist_schema
       AND c.relname = v_hist_table
       AND a.attname = p_fk_col
       AND a.attnum > 0
       AND NOT a.attisdropped;

     -- se la tabella non esiste o non trovo colonne → sollevo errore
   IF v_pk_type IS NULL THEN
     PERFORM script.fn_log_and_raise_error(
       'database',
       'fn_get_snapshot_as_of',
       'E_QUERY_FAILED_SCHEMA_TABLE',
       jsonb_build_object('table', v_full_table),
       NULL::uuid,
       p_schema, p_table
     );
   END IF;


   -------------------------------
   -- 1) Prova a leggere dallo storico
   -------------------------------
   BEGIN
     EXECUTE format(
       'SELECT snapshot
         FROM  %I.%I
         WHERE %I = $1::%s
           AND valid_from <= $2
           AND (valid_to > $2 OR valid_to IS NULL)
         ORDER BY valid_from DESC
         LIMIT 1',
      v_hist_schema, v_hist_table, p_fk_col, v_pk_type
     )
     INTO v_snapshot
     USING p_id, p_as_of;
   EXCEPTION WHEN OTHERS THEN
     PERFORM script.fn_log_and_raise_error(
       'database',
       'fn_get_snapshot_as_of',
       'E_QUERY_FAILED',
       jsonb_build_object(
         'table',       v_full_table,
         'fk_column',   p_fk_col,
         'id',          p_id,
         'as_of',       p_as_of,
         'error',       SQLERRM,
         'SQLSTATE', SQLSTATE
       ),
       NULL::uuid,
        p_schema, p_table, SQLSTATE
     );
   END;

   IF v_snapshot IS NOT NULL THEN
     RETURN v_snapshot;
   END IF;

   -------------------------------
   -- 2) Fallback: serializzo la riga corrente
   -------------------------------
   BEGIN
     EXECUTE format(
       'SELECT to_jsonb(t) - %L
         FROM %I.%I AS t
         WHERE %I = $1::%s',
       v_id_col,
       p_schema, p_table,
       v_id_col,
       v_pk_type            -- tipo dinamico
     )
     INTO v_snapshot
     USING p_id;
   EXCEPTION WHEN OTHERS THEN
     PERFORM script.fn_log_and_raise_error(
       'database',
       'fn_get_snapshot_as_of',
       'E_QUERY_FAILED',
       jsonb_build_object(
         'schema',     p_schema,
         'table',      p_table,
         'id_column',  v_id_col,
         'id',         p_id,
         'error',      SQLERRM,
         'SQLSTATE', SQLSTATE
       ),
       NULL::uuid,
       p_schema, p_table, SQLSTATE
     );
   END;

   RETURN v_snapshot;
 END;
 $function$

COMMENT ON FUNCTION script.fn_get_snapshot_as_of(p_schema text, p_table text, p_id text, p_fk_col text, p_as_of timestamp with time zone)
IS 'Restituisce il JSONB di un record al momento p_as_of: 1) dallo storico se esiste,
    2) altrimenti serializza la riga corrente. In caso di errore nelle query, chiama
    fn_log_and_raise_error con dettagli contestuali. ⭐ rev 2026-09-20 (20260920-05):
    p_as_of e'' timestamptz — prima era timestamp e il corpo lo castava col TimeZone
    della sessione chiamante, cosi'' la stessa domanda fatta dal backend (UTC) e da
    psql (Europe/Rome) leggeva due istanti diversi. Documento
    valutazione-modello-di-dominio-db, V-3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
