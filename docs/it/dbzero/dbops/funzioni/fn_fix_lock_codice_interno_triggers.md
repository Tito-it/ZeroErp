{% include-markdown "it/dbzero/dbops/manual/fn_fix_lock_codice_interno_triggers.md" %}
# ⚙️ Funzione `fn_fix_lock_codice_interno_triggers`

```sql
CREATE FUNCTION fn_fix_lock_codice_interno_triggers(p_target_schema text, p_dry_run boolean, p_drop_old boolean, p_align_with_first_arg boolean, p_force_update_column text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_fix_lock_codice_interno_triggers(p_target_schema text DEFAULT NULL::text, p_dry_run boolean DEFAULT true, p_drop_old boolean DEFAULT true, p_align_with_first_arg boolean DEFAULT true, p_force_update_column text DEFAULT NULL::text)
 RETURNS TABLE(object_schema text, object_table text, old_trigger text, new_trigger text, update_column text, action text, sql text)
 LANGUAGE plpgsql
AS $function$
  DECLARE
      r record;
      v_fn_call   text;    -- es: script.trgfn_lock_columns('codice_interno','MSG')
      v_fn_name   text;    -- es: script.trgfn_lock_columns
      v_fn_args   text;    -- es: 'codice_interno','MSG'
      v_first_arg text;    -- colonna dedotta dal 1° argomento
      v_upd_col   text;    -- colonna effettiva da usare per UPDATE OF
      v_new_trigger text;  -- nuovo nome
      v_create    text;
      v_drop      text;
  BEGIN
      FOR r IN
          SELECT
              n.nspname  AS schema_name,
              c.relname  AS table_name,
              t.tgname   AS trigger_name,
              pg_get_triggerdef(t.oid, true) AS trigger_def
          FROM pg_trigger t
          JOIN pg_class   c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
          WHERE NOT t.tgisinternal
            AND (t.tgname ILIKE '%upd_lock_codiceinterno%' OR t.tgname ILIKE '%codice_interno%')
            AND pg_get_triggerdef(t.oid, true) ILIKE '%trgfn_lock_columns%'
            AND (p_target_schema IS NULL OR n.nspname = p_target_schema)
          ORDER BY n.nspname, c.relname, t.tgname
      LOOP
          -- Estrai "EXECUTE FUNCTION nome(args)"
          v_fn_call := regexp_replace(r.trigger_def, '.*EXECUTE FUNCTION\s+([^(]+\([^)]*\)).*', '\1');
          v_fn_name := NULL;
          v_fn_args := NULL;

          IF v_fn_call IS NOT NULL THEN
              v_fn_name := regexp_replace(v_fn_call, '^\s*([^(]+)\s*\(.*$', '\1');
              v_fn_args := regexp_replace(v_fn_call, '^[^(]*\(\s*(.*)\s*\)\s*$', '\1');
          END IF;

          -- Deduci la 1ª colonna passata a trgfn_lock_columns (se testuale: 'colonna' o E'colonna')
          v_first_arg := NULL;
          IF v_fn_args IS NOT NULL THEN
              -- cerca prima una stringa singola quotata
              v_first_arg := regexp_replace(v_fn_args, '^\s*E?''([^'']+)''.*$', '\1');
              -- se non era una stringa ma un identificatore non quotato (raro): "colonna, ..."
              IF v_first_arg IS NULL OR v_first_arg = v_fn_args THEN
                  v_first_arg := regexp_replace(v_fn_args, '^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(,.*)?$', '\1');
                  -- se l'intera v_fn_args coincide, prova ancora con identificatore tra doppi apici
                  IF v_first_arg = v_fn_args THEN
                      v_first_arg := regexp_replace(v_fn_args, '^\s*"([^"]+)"\s*(,.*)?$', '\1');
                  END IF;
              END IF;
          END IF;

          -- Decidi la colonna su cui legare l'UPDATE OF
          IF p_align_with_first_arg AND v_first_arg IS NOT NULL AND v_first_arg <> '' THEN
              v_upd_col := v_first_arg;
          ELSIF p_force_update_column IS NOT NULL AND p_force_update_column <> '' THEN
              v_upd_col := p_force_update_column;
          ELSE
              -- fallback sicuro: prova 'codice_interno', altrimenti mantieni comportamento "generico" (UPDATE senza OF)
              v_upd_col := 'codice_interno';
          END IF;

          -- Nome nuovo trigger standard
          v_new_trigger := format('trg_a10_upd_%s_lock_%s',
                                  r.table_name,
                                  replace(lower(v_upd_col), '"', ''));

          -- Costruisci DDL CREATE con UPDATE OF <col>
          v_create := format(
              'CREATE TRIGGER %I BEFORE UPDATE OF %I ON %I.%I
              FOR EACH ROW
              WHEN (OLD.%I IS DISTINCT FROM NEW.%I)
              EXECUTE FUNCTION %s(%s);',
              v_new_trigger, v_upd_col, r.schema_name, r.table_name,
              v_upd_col, v_upd_col, COALESCE(v_fn_name,'script.trgfn_lock_columns'),
              COALESCE(v_fn_args,'')
            );

          v_drop := format('DROP TRIGGER IF EXISTS %I ON %I.%I;', r.trigger_name, r.schema_name, r.table_name);

          IF p_dry_run THEN
              IF p_drop_old THEN
                  object_schema := r.schema_name;
                  object_table  := r.table_name;
                  old_trigger   := r.trigger_name;
                  new_trigger   := v_new_trigger;
                  update_column := v_upd_col;
                  action        := 'DROP_OLD';
                  sql           := v_drop;
                  RETURN NEXT;
              END IF;

              object_schema := r.schema_name;
              object_table  := r.table_name;
              old_trigger   := r.trigger_name;
              new_trigger   := v_new_trigger;
              update_column := v_upd_col;
              action        := 'CREATE_NEW';
              sql           := v_create;
              RETURN NEXT;
          ELSE
              IF p_drop_old THEN
                  EXECUTE v_drop;
                  object_schema := r.schema_name;
                  object_table  := r.table_name;
                  old_trigger   := r.trigger_name;
                  new_trigger   := v_new_trigger;
                  update_column := v_upd_col;
                  action        := 'DROPPED';
                  sql           := v_drop;
                  RETURN NEXT;
              END IF;

              EXECUTE v_create;
              object_schema := r.schema_name;
              object_table  := r.table_name;
              old_trigger   := r.trigger_name;
              new_trigger   := v_new_trigger;
              update_column := v_upd_col;
              action        := 'CREATED';
              sql           := v_create;
              RETURN NEXT;
          END IF;
      END LOOP;

      RETURN;
  END;
  $function$
```

</div>

---
{% include-markdown "signature-core.md" %}
