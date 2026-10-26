{% include-markdown "it/dbzero/script/manual/fn_get_record_id_as_of.md" %}
# ⚙️ Funzione `fn_get_record_id_as_of`

```sql
CREATE FUNCTION fn_get_record_id_as_of(p_schema text, p_table text, p_id text, p_fk_col text, p_as_of timestamp with time zone)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_record_id_as_of(p_schema text, p_table text, p_id text, p_fk_col text, p_as_of timestamp with time zone)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_id           TEXT;
  v_pk_type      TEXT;
  v_id_hist      TEXT := 'id';                  -- colonna PK storico
  v_hist_schema  TEXT := 'storico';
  v_hist_table   TEXT := p_table;
  v_full_table   TEXT := format('%I.%I', v_hist_schema, v_hist_table);
BEGIN
------------------------------------------------------
-- Input
-- p_schema: schema della tabella originaria
-- p_table: nome della tabella originaria (e storica)
-- p_id: PK del record originario, passato come TEXT
-- p_fk_col: nome della colonna FK in storico (es. 'soggetto_id')
-- p_as_of: istante di validita' desiderato (timestamptz, rev 20260920-06:
--          prima era timestamp castato col fuso di sessione)
-- Output
-- v_id: ID TEXT del record valido a p_as_of, cercato solo nello storico
-- Se non esiste snapshot valido, restituisce NULL
-- --------------------------------------------------

  -- 0) Verifica esistenza e tipo della colonna FK in storico
  SELECT format_type(a.atttypid, a.atttypmod)
    INTO v_pk_type
  FROM pg_attribute a
  JOIN pg_class c        ON a.attrelid   = c.oid
  JOIN pg_namespace n    ON c.relnamespace = n.oid
  WHERE n.nspname = v_hist_schema
    AND c.relname = v_hist_table
    AND a.attname = p_fk_col
    AND a.attnum > 0 AND NOT a.attisdropped;

  -- se la tabella non esiste o non trovo colonne → sollevo errore
  IF v_pk_type IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'fn_get_record_id_as_of',
      'E_QUERY_FAILED_SCHEMA_TABLE',
      jsonb_build_object('table', v_full_table, 'fk_column', p_fk_col),
      NULL::uuid,
       v_full_table, p_fk_col
    );
  END IF;

  -- 1) Cerca l'id nello storico valido per la data
  BEGIN
    EXECUTE format(
      'SELECT %I::text
        FROM %I.%I
        WHERE %I = $1::%s
          AND valid_from <= $2
          AND (valid_to > $2 OR valid_to IS NULL)
        ORDER BY valid_from DESC
        LIMIT 1',
      v_id_hist, v_hist_schema, v_hist_table, p_fk_col, v_pk_type
    )
    INTO v_id
    USING p_id, p_as_of;

  -- Se non trovato, v_id rimane NULL
  -- Se errore, loggo e rilancio
  EXCEPTION WHEN OTHERS THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'fn_get_record_id_as_of',
      'E_QUERY_FAILED',
      jsonb_build_object(
        'table',     v_full_table,
        'id_column', v_id_hist,
        'fk_column', p_fk_col,
        'id',        p_id,
        'as_of',     p_as_of,
        'error',     SQLERRM,
        'state',     SQLSTATE
      ),
      NULL::uuid,
      p_schema, p_table, SQLSTATE
    );
  END;

  -- 2) Se non trovato, restituisci NULL (no fallback)
  RETURN v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_record_id_as_of(p_schema text, p_table text, p_id text, p_fk_col text, p_as_of timestamp with time zone)
IS 'Restituisce l''ID TEXT di un record valido a p_as_of esclusivamente dallo storico;
  se non esiste snapshot valido, restituisce NULL. ⭐ rev 2026-09-20 (20260920-06):
  p_as_of e'' timestamptz — prima era timestamp castato col TimeZone della sessione
  chiamante (gemella di fn_get_snapshot_as_of, 20260920-05). Documento
  valutazione-modello-di-dominio-db, V-3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
