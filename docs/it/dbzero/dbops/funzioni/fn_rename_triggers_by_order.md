{% include-markdown "it/dbzero/dbops/manual/fn_rename_triggers_by_order.md" %}
# ⚙️ Funzione `fn_rename_triggers_by_order`

```sql
CREATE FUNCTION fn_rename_triggers_by_order(p_order_token text, p_dry_run boolean, p_schema text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_rename_triggers_by_order(p_order_token text, p_dry_run boolean DEFAULT true, p_schema text DEFAULT NULL::text)
 RETURNS TABLE(schema_name text, table_name text, old_name text, new_name text, action text, notes text, sql text)
 LANGUAGE plpgsql
AS $function$
DECLARE
  r record;
  v_def     text;
  v_evt     text;
  v_is_aft  boolean;
  v_of_cols text;
  v_of_seg  text;
  v_aft_seg text;
  v_purpose text;
  v_new     text;
  v_new_base text;
  v_sql     text;
  v_suffix  int;
  v_len     int;
  v_ord     text;

BEGIN

  
  
  
  
  
  
  


  
  IF p_order_token IS NULL THEN
    RETURN; 
  END IF;

  v_ord := lower(p_order_token);

  
  IF v_ord !~ '^[az][0-9]{2}$' THEN
    
    RETURN;
  END IF;

  FOR r IN
    SELECT n.nspname AS schema_name, c.relname AS table_name, t.tgname AS old_name, t.oid AS tg_oid
    FROM pg_trigger t
    JOIN pg_class c     ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE NOT t.tgisinternal
      AND t.tgname LIKE format('trg_%s_%s', v_ord, '%')  
      AND (p_schema IS NULL OR n.nspname = p_schema)
    ORDER BY n.nspname, c.relname, t.tgname
  LOOP
    v_def := pg_get_triggerdef(r.tg_oid, true);

    
    v_evt := CASE
      WHEN v_def ILIKE '% INSERT %' THEN 'ins'
      WHEN v_def ILIKE '% UPDATE %' THEN 'upd'
      WHEN v_def ILIKE '% DELETE %' THEN 'del'
      ELSE 'upd'
    END;

    
    v_is_aft := (v_def ILIKE 'AFTER%') OR (v_def ILIKE '% AFTER %');
    v_aft_seg := CASE WHEN v_is_aft THEN '_aft' ELSE '' END;

    
    IF v_evt = 'upd' AND v_def ~* 'UPDATE OF ' THEN
      v_of_cols := regexp_replace(v_def, '.*UPDATE OF\s+([a-zA-Z0-9_,"\s,]+)\s+ON.*', '\1', 1, 1, 'i');
      v_of_cols := regexp_replace(v_of_cols, '"', '', 'g');
      v_of_cols := trim(split_part(v_of_cols, ',', 1));
      v_of_seg  := CASE WHEN v_of_cols IS NOT NULL AND v_of_cols <> '' THEN '_of_'||v_of_cols ELSE '' END;
    ELSE
      v_of_seg := '';
    END IF;

    
    v_purpose := r.old_name;
    v_purpose := regexp_replace(v_purpose, '^trg_'||v_ord||'_', '');
    v_purpose := regexp_replace(v_purpose, '^(ins|upd|del)_', '');

    
    
    v_purpose := regexp_replace(
                  v_purpose,
                  '^' || r.table_name || '(_)?',
                      ''
                    );



    v_purpose := regexp_replace(v_purpose, '^of_[a-z0-9_]+_?', '', 'i');
    IF v_purpose IS NULL OR v_purpose = '' THEN
      v_purpose := 'renamed';
    END IF;

    
    v_new_base := format('trg_%s_%s_%s%s%s_%s',
                        r.table_name, v_ord, v_evt, v_of_seg, v_aft_seg, v_purpose);
    v_new := v_new_base;

    
    v_suffix := 1;
    WHILE EXISTS (
      SELECT 1
      FROM pg_trigger t2
      WHERE t2.tgrelid = (SELECT oid FROM pg_class WHERE relname=r.table_name AND relnamespace=(SELECT oid FROM pg_namespace WHERE nspname=r.schema_name))
        AND t2.tgname = v_new
    ) LOOP
      v_suffix := v_suffix + 1;
      v_new := v_new_base || '_'|| v_suffix::text;
    END LOOP;

    
    v_len := length(v_new);
    IF v_len > 63 THEN
      v_new := substring(v_new for 63);
    END IF;

    
    IF v_new = r.old_name THEN
      schema_name := r.schema_name; table_name := r.table_name;
      old_name := r.old_name; new_name := v_new; action := 'SKIP';
      notes := v_def; sql := NULL;
      RETURN NEXT; CONTINUE;
    END IF;

    v_sql := format('ALTER TRIGGER %I ON %I.%I RENAME TO %I;',
                    r.old_name, r.schema_name, r.table_name, v_new);

    schema_name := r.schema_name;
    table_name  := r.table_name;
    old_name    := r.old_name;
    new_name    := v_new;
    notes       := v_def;
    sql         := v_sql;

    IF p_dry_run THEN
      action := 'PREVIEW';
      RETURN NEXT;
    ELSE
      BEGIN
        EXECUTE v_sql;
        action := 'RENAMED';
        RETURN NEXT;
      EXCEPTION WHEN OTHERS THEN
        action := 'ERROR';
        notes  := SQLERRM;
        RETURN NEXT;
      END;
    END IF;
  END LOOP;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
