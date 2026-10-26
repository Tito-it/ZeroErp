{% include-markdown "it/dbzero/dbops/manual/fn_non_editable_fields.md" %}
# ⚙️ Funzione `fn_non_editable_fields`

```sql
CREATE FUNCTION fn_non_editable_fields(p_schema text, p_table text, p_record_id text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_non_editable_fields(p_schema text, p_table text, p_record_id text)
 RETURNS text[]
 LANGUAGE plpgsql
AS $function$
-- Scopo: ritorna l'array deduplicato e ordinato dei campi non editabili
-- per (p_schema, p_table) per la riga identificata da p_record_id.
-- Unisce:
--   1. Lock statici da dbops.vw_non_editable_fields
--   2. Lock condizionali da dbops.lock_columns_conditional
--      valutati dinamicamente: EXECUTE 'SELECT (' || condition_expr || ')'
--      USING p_record_id. Il $1 nell'espressione e' parametrico
--      (sicuro per injection); il cast al tipo target e' a carico
--      di condition_expr (es. prodotto_id = $1::uuid).
DECLARE
    v_result text[] := ARRAY[]::text[];
    v_match  boolean;
    r        record;
BEGIN
    -- 1. Lock statici (incondizionati)
    SELECT array_agg(column_name ORDER BY column_name)
      INTO v_result
      FROM dbops.vw_non_editable_fields
     WHERE target_schema = p_schema
       AND target_table  = p_table;

    IF v_result IS NULL THEN
        v_result := ARRAY[]::text[];
    END IF;

    -- 2. Lock condizionali: valuta ogni regola abilitata
    FOR r IN
        SELECT column_name, condition_expr
          FROM dbops.lock_columns_conditional
         WHERE schema_name = p_schema
           AND table_name  = p_table
           AND enabled     IS TRUE
         ORDER BY column_name
    LOOP
        v_match := false;
        -- Concatenazione diretta: evita ambiguita' di % con format().
        -- $1 e' parametrico (USING): nessun rischio injection su p_record_id.
        EXECUTE 'SELECT (' || r.condition_expr || ')'
           USING p_record_id
            INTO v_match;

        IF v_match IS TRUE THEN
            v_result := array_append(v_result, r.column_name);
        END IF;
    END LOOP;

    -- 3. Deduplicazione e ordinamento finali
    RETURN ARRAY(
        SELECT DISTINCT col
          FROM unnest(v_result) t(col)
         ORDER BY col
    );
END;
$function$

COMMENT ON FUNCTION dbops.fn_non_editable_fields(p_schema text, p_table text, p_record_id text)
IS 'Ritorna i campi non editabili per (schema, tabella, id_riga). Unisce: lock statici (vw_non_editable_fields) + lock condizionali (lock_columns_conditional) valutati su p_record_id via EXECUTE USING. VOLATILE (legge stato corrente DB). SECURITY INVOKER (rispetta RLS). p_record_id = id come text; condition_expr casta $1 al tipo target. rev 2026-05-22.';
```

</div>

---
{% include-markdown "signature-core.md" %}
