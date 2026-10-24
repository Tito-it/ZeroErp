# ⚙️ Funzione `fn_cleanup_triggers_suffix_2`

```sql
CREATE FUNCTION fn_cleanup_triggers_suffix_2(p_dry_run boolean, p_schema text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_cleanup_triggers_suffix_2(p_dry_run boolean DEFAULT true, p_schema text DEFAULT NULL::text)
 RETURNS TABLE(schema_name text, table_name text, old_name text, new_name text, action text, notes text, sql text)
 LANGUAGE plpgsql
AS $function$
  DECLARE
    r record;
    v_relid     oid;
    v_base_oid  oid;
    v_def_sfx   text;
    v_def_base  text;
    v_sql       text;
  BEGIN
    FOR r IN
      SELECT n.nspname  AS schema_name,
            c.relname  AS table_name,
            t.tgname   AS old_name,
            regexp_replace(t.tgname, '_2$', '') AS base_name,
            t.oid      AS tg_oid
      FROM pg_trigger t
      JOIN pg_class c     ON c.oid = t.tgrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal
        AND t.tgname ~ '.*_2$'
        AND (p_schema IS NULL OR n.nspname = p_schema)
      ORDER BY 1,2,3
    LOOP
      
      SELECT c.oid INTO v_relid
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE c.relname = r.table_name AND n.nspname = r.schema_name;

      
      SELECT t2.oid INTO v_base_oid
      FROM pg_trigger t2
      WHERE t2.tgrelid = v_relid
        AND t2.tgname  = r.base_name;

      IF v_base_oid IS NOT NULL THEN
        
        SELECT regexp_replace(lower(pg_get_triggerdef(r.tg_oid, true)),   '\s+', ' ', 'g') INTO v_def_sfx;
        SELECT regexp_replace(lower(pg_get_triggerdef(v_base_oid, true)), '\s+', ' ', 'g') INTO v_def_base;

        IF v_def_sfx = v_def_base THEN
          
          v_sql := format('DROP TRIGGER %I ON %I.%I;', r.old_name, r.schema_name, r.table_name);

          schema_name := r.schema_name;
          table_name  := r.table_name;
          old_name    := r.old_name;
          new_name    := NULL;
          notes       := 'Base trigger presente con definizione identica: '||r.base_name;

          IF p_dry_run THEN
            action := 'PREVIEW_DROP'; sql := v_sql; RETURN NEXT;
          ELSE
            BEGIN
              EXECUTE v_sql; action := 'DROPPED'; sql := v_sql; RETURN NEXT;
            EXCEPTION WHEN OTHERS THEN
              action := 'SKIP_ERROR'; notes := notes||' | '||SQLERRM; sql := v_sql; RETURN NEXT;
            END;
          END IF;

        ELSE
          
          schema_name := r.schema_name;
          table_name  := r.table_name;
          old_name    := r.old_name;
          new_name    := r.base_name;
          action      := 'SKIP_CONFLICT';
          notes       := 'Esiste già '||r.base_name||' con definizione diversa; nessuna azione.';
          sql         := NULL;
          RETURN NEXT;
        END IF;

      ELSE
        
        IF length(r.base_name) > 63 THEN
          schema_name := r.schema_name;
          table_name  := r.table_name;
          old_name    := r.old_name;
          new_name    := r.base_name;
          action      := 'SKIP_ERROR';
          notes       := 'Nome base supera 63 caratteri: rinomina manuale richiesta.';
          sql         := NULL;
          RETURN NEXT;
        END IF;

        v_sql := format('ALTER TRIGGER %I ON %I.%I RENAME TO %I;',
                        r.old_name, r.schema_name, r.table_name, r.base_name);

        schema_name := r.schema_name;
        table_name  := r.table_name;
        old_name    := r.old_name;
        new_name    := r.base_name;
        notes       := 'Base non presente: rinomina a nome base.';

        IF p_dry_run THEN
          action := 'PREVIEW_RENAME'; sql := v_sql; RETURN NEXT;
        ELSE
          BEGIN
            EXECUTE v_sql; action := 'RENAMED'; sql := v_sql; RETURN NEXT;
          EXCEPTION WHEN OTHERS THEN
            action := 'SKIP_ERROR'; notes := notes||' | '||SQLERRM; sql := v_sql; RETURN NEXT;
          END;
        END IF;

      END IF;
    END LOOP;
  END;
  $function$
```

</div>

---
{% include-markdown "signature-core.md" %}
