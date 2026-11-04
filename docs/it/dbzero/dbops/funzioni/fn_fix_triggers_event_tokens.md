{% include-markdown "it/dbzero/dbops/manual/fn_fix_triggers_event_tokens.md" %}
# ⚙️ Funzione `fn_fix_triggers_event_tokens`

```sql
CREATE FUNCTION fn_fix_triggers_event_tokens(p_default_order text, p_dry_run boolean, p_schema text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_fix_triggers_event_tokens(p_default_order text DEFAULT 'a10'::text, p_dry_run boolean DEFAULT true, p_schema text DEFAULT NULL::text)
 RETURNS TABLE(schema_name text, table_name text, old_name text, new_name text, action text, notes text, sql text)
 LANGUAGE plpgsql
AS $function$
  DECLARE
    r record;
    v_def      text;
    v_evt      text;        
    v_is_aft   boolean;
    v_of_cols  text;
    v_of_seg   text;
    v_aft_seg  text;
    v_ord      text;
    v_purpose  text;
    v_new      text;
    v_new_base text;
    v_sql      text;
    v_suffix   int;
    v_len      int;
    v_has_ins boolean;
    v_has_upd boolean;
    v_has_del boolean;
     v_evt_raw text;
  BEGIN
    v_has_ins := (v_def ILIKE '% INSERT %');
    v_has_upd := (v_def ILIKE '% UPDATE %');
    v_has_del := (v_def ILIKE '% DELETE %');

    v_evt_raw := lower(
                regexp_replace(v_def,
                  '.*(?:before|after)\s+(.+?)\s+on.*',  
                  '\1'
                )
              );

    
    IF p_default_order IS NULL OR lower(p_default_order) not in ('ins' , 'upd' , 'dlt') THEN
      RAISE EXCEPTION 'p_default_order deve essere aNN o zNN (es. a10, z07)';
    END IF;

    FOR r IN
      SELECT n.nspname AS schema_name,
            c.relname AS table_name,
            t.tgname  AS old_name,
            t.oid     AS tg_oid
      FROM pg_trigger t
      JOIN pg_class c     ON c.oid = t.tgrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal
        AND n.nspname NOT IN ('public','topology')
        AND (p_schema IS NULL OR n.nspname = p_schema)
        AND (
              
              t.tgname ILIKE 'trg_upd%' OR
              t.tgname ILIKE 'trg_ins%' OR
              t.tgname ILIKE 'trg_del%' OR
              t.tgname ILIKE 'trg_dlt%' OR
              
              (t.tgname ILIKE 'trg_%' AND
              t.tgname NOT ILIKE '%_ins_%' AND
              t.tgname NOT ILIKE '%_upd_%' AND
              t.tgname NOT ILIKE '%_del_%')
            )
      ORDER BY 1,2,3
    LOOP
      v_def := pg_get_triggerdef(r.tg_oid, true);

      
      
      
      
      
      
      


      
        v_evt := lower(
          regexp_replace(v_def, '.*(?:before|after)\s+(.+?)\s+on.*', '\1')  
        );
        v_evt := replace(v_evt, ' or ', '_');
        v_evt := replace(v_evt, 'insert', 'ins');
        v_evt := replace(v_evt, 'update', 'upd');
        v_evt := replace(v_evt, 'delete', 'dlt');
        v_evt := regexp_replace(v_evt, '_+', '_', 'g');
        v_evt := trim(both '_' from v_evt);
        IF v_evt IS NULL OR v_evt = '' THEN
          v_evt := 'upd';  
        END IF;



      
      
      
      
      
      v_purpose := regexp_replace(v_purpose,
        '^(ins|upd|del|dlt|ins_upd|ins_dlt|upd_dlt|ins_upd_dlt)_', '', 'i');

      
      v_is_aft := (v_def ILIKE 'AFTER%') OR (v_def ILIKE '% AFTER %');
      v_aft_seg := CASE WHEN v_def ~* '(^|\s)AFTER(\s|$)' THEN '_aft' ELSE '' END;

      

      
          IF v_evt = 'upd' AND v_def ~* 'UPDATE OF ' THEN
            v_of_cols := regexp_replace(v_def,'^.*UPDATE OF\s+([a-zA-Z0-9_,"\s,]+)\s+ON.*$', '\1', 1, 1, 'i');
            v_of_cols := regexp_replace(v_of_cols, '"', '', 'g');
            v_of_cols := trim(split_part(v_of_cols, ',', 1));
            v_of_seg  := CASE WHEN v_of_cols <> '' THEN '_of_'||v_of_cols ELSE '' END;
          ELSE
            v_of_seg := '';
          END IF;

      
      v_ord := lower(
        regexp_replace(r.old_name, '^.*?(^|_)(([az])[0-9]{2})(_|$).*', '\2')
      );
      IF v_ord IS NULL OR v_ord = r.old_name OR v_ord !~ '^[az][0-9]{2}$' THEN
        v_ord := lower(p_default_order);
      END IF;

      
      v_purpose := r.old_name;
      v_purpose := regexp_replace(v_purpose, '^trg_', '', 'i');
      v_purpose := regexp_replace(v_purpose, '^[az][0-9]{2}_', '', 'i');       
      v_purpose := regexp_replace(v_purpose, '^(ins|upd|del|dlt)_', '', 'i');  
      v_purpose := regexp_replace(v_purpose, '^'||r.table_name||'(_)?', '', 'i'); 
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
        WHERE t2.tgrelid = (SELECT oid
                            FROM pg_class
                            WHERE relname = r.table_name
                              AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = r.schema_name))
          AND t2.tgname = v_new
      ) LOOP
        v_suffix := v_suffix + 1;
        v_new := v_new_base || '_' || v_suffix::text;
      END LOOP;

      
      v_len := length(v_new);
      IF v_len > 63 THEN
        v_new := substring(v_new for 63);
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
