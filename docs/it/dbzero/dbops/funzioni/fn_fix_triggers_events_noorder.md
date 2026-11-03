{% include-markdown "it/dbzero/dbops/manual/fn_fix_triggers_events_noorder.md" %}
# ⚙️ Funzione `fn_fix_triggers_events_noorder`

```sql
CREATE FUNCTION fn_fix_triggers_events_noorder(p_dry_run boolean, p_schema text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_fix_triggers_events_noorder(p_dry_run boolean DEFAULT true, p_schema text DEFAULT NULL::text)
 RETURNS TABLE(schema_name text, table_name text, old_name text, new_name text, action text, notes text, sql text)
 LANGUAGE plpgsql
AS $function$
DECLARE
  r record;
  v_def         text;
  v_evt_raw     text;
  v_evt         text;        
  v_aft_seg     text;        
  v_order_seg   text;        
  v_purpose_src text;        
  v_purpose     text;
  v_new_base    text;
  v_new         text;
  v_sql         text;
  v_suffix      int;
BEGIN
  FOR r IN
    SELECT n.nspname AS schema_name,
          c.relname AS table_name,
          t.tgname  AS old_name,
          t.oid     AS tg_oid,
          t.tgfoid  AS tgfn_oid
    FROM pg_trigger t
    JOIN pg_class c     ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE NOT t.tgisinternal
      AND n.nspname NOT IN ('public','topology')
      AND (p_schema IS NULL OR n.nspname = p_schema)
      AND (
          t.tgname ILIKE 'trg_%'
        OR t.tgname ILIKE 'ins_%'
        OR t.tgname ILIKE 'upd_%'
        OR t.tgname ILIKE 'del_%'
        OR t.tgname ILIKE 'dlt_%'
      )
    ORDER BY 1,2,3
  LOOP
    v_def := pg_get_triggerdef(r.tg_oid, true);

    
    v_evt_raw := coalesce(
      substring(v_def from '(?i)(?:before|after|instead\s+of)\s+(.+?)\s+on'),
      ''
    );
    v_evt_raw := lower(v_evt_raw);

    
    v_evt := array_to_string(ARRAY[
              CASE WHEN v_evt_raw ~* '\minsert\M' THEN 'ins' END,
              CASE WHEN v_evt_raw ~* '\mupdate\M' THEN 'upd' END,
              CASE WHEN v_evt_raw ~* '\mdelete\M' THEN 'dlt' END
            ]::text[], '_');

    IF coalesce(v_evt,'') = '' THEN
      
      v_evt := 'upd';
    END IF;

    
    v_aft_seg := CASE WHEN v_def ~* '(^|\s)AFTER(\s|$)' THEN '_aft' ELSE '' END;

    
    v_order_seg := '';
    IF r.old_name ~* '(_a[0-9]{2}_)' THEN
      v_order_seg := lower(regexp_replace(r.old_name, '.*(_a[0-9]{2}_).*', '\1'));
    ELSIF r.old_name ~* '(_z[0-9]{2}_)' THEN
      v_order_seg := lower(regexp_replace(r.old_name, '.*(_z[0-9]{2}_).*', '\1'));
    END IF;

    
    SELECT proname INTO v_purpose_src
    FROM pg_proc WHERE oid = r.tgfn_oid;

    IF coalesce(v_purpose_src,'') = '' THEN
      v_purpose_src := r.old_name;
    END IF;

    v_purpose := lower(v_purpose_src);

    
    v_purpose := regexp_replace(v_purpose, '[^a-z0-9_]+', '_', 'g');

    
    v_purpose := regexp_replace(v_purpose, '(^|_)trgfn(?=_)', '\1', 'gi');
    v_purpose := regexp_replace(v_purpose, '(^|_)trg(?=_)',   '\1', 'gi');
    v_purpose := regexp_replace(v_purpose, '(^|_)fn(?=_)',    '\1', 'gi');

    
    v_purpose := regexp_replace(v_purpose, '(^|_)'||r.table_name||'(?=(_|$))', '\1', 'gi');
    v_purpose := regexp_replace(v_purpose, '(^|_)'||r.table_name||'(?=(_|$))', '\1', 'gi');

    
    v_purpose := regexp_replace(v_purpose, '(_a[0-9]{2}_|_z[0-9]{2}_)', '_', 'gi');
    v_purpose := regexp_replace(
                  v_purpose,
                  '(^|_)(ins|upd|del|dlt|ins_upd|ins_dlt|upd_dlt|ins_upd_dlt)(?=(_|$))',
                  '\1', 'gi');

    
    v_purpose := regexp_replace(v_purpose, '(^|_)aft(?=(_|$))', '\1', 'gi');
    v_purpose := regexp_replace(v_purpose, '(^|_)(create|trigger|function|proc)(?=(_|$))', '\1', 'gi');

    
    v_purpose := regexp_replace(v_purpose, '_+', '_', 'g');
    v_purpose := trim(both '_' from v_purpose);
    IF v_purpose = '' THEN v_purpose := 'renamed'; END IF;

    
    v_new_base := format('trg_%s%s_%s%s_%s',
                        r.table_name,
                        coalesce(v_order_seg, ''),
                        v_evt,
                        v_aft_seg,
                        v_purpose);

    
    v_new_base := regexp_replace(v_new_base, '_+', '_', 'g');
    v_new_base := regexp_replace(v_new_base, '_$', '');

      
      IF v_new_base = r.old_name THEN
        
        v_new := r.old_name;
        v_suffix := 1;
      ELSE
        v_new := v_new_base; 
        v_suffix := 1;

        WHILE EXISTS (
          SELECT 1
          FROM pg_trigger t2
          WHERE t2.tgrelid = (
                  SELECT oid 
                  FROM pg_class 
                  WHERE relname = r.table_name
                    AND relnamespace = (
                          SELECT oid FROM pg_namespace WHERE nspname = r.schema_name
                    )
                )
            AND t2.tgname = v_new
            AND t2.oid <> r.tg_oid    
        ) LOOP
          v_suffix := v_suffix + 1;
          v_new := v_new_base || '_' || v_suffix::text;
        END LOOP;
      END IF;

    
    IF length(v_new) > 63 THEN
      IF v_suffix > 1 THEN
        v_new := substring(v_new_base for (63 - 1 - length(v_suffix::text))) || '_' || v_suffix::text;
      ELSE
        v_new := substring(v_new_base for 63);
      END IF;
    END IF;

    
    IF v_new = r.old_name THEN
      schema_name := r.schema_name; table_name := r.table_name;
      old_name := r.old_name; new_name := v_new;
      action := 'SKIP'; notes := v_def; sql := NULL;
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
      action := 'PREVIEW'; RETURN NEXT;
    ELSE
      BEGIN
        EXECUTE v_sql; action := 'RENAMED'; RETURN NEXT;
      EXCEPTION WHEN OTHERS THEN
        action := 'ERROR'; notes := SQLERRM; RETURN NEXT;
      END;
    END IF;
  END LOOP;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
