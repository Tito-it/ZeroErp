# ⚙️ Funzione `trgfn_child_requires_active_parent`

```sql
CREATE FUNCTION trgfn_child_requires_active_parent()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_child_requires_active_parent()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_parent_schema     text := TG_ARGV[0];
  v_parent_table      text := TG_ARGV[1];
  v_parent_attivo_col text := COALESCE(TG_ARGV[2],'attivo');
  v_fk_col            text := TG_ARGV[3];
  v_fk_val            text;
  v_sql               text;
  v_active            boolean;
BEGIN
  -- Estrai dinamicamente il valore della FK dal record NEW
  EXECUTE format('SELECT ($1).%I::text', v_fk_col) INTO v_fk_val USING NEW;

  -- Se il figlio non è / non resta attivo, niente controllo
  IF TG_OP='INSERT' THEN
    IF COALESCE(NEW.attivo,FALSE) IS NOT TRUE THEN
      RETURN NEW;
    END IF;
  ELSE
    IF COALESCE(NEW.attivo,FALSE) IS NOT TRUE THEN
      RETURN NEW;
    END IF;
  END IF;

  -- Leggi lo stato attivo del padre
  v_sql := format('SELECT %I FROM %I.%I WHERE id=$1', v_parent_attivo_col, v_parent_schema, v_parent_table);
  EXECUTE v_sql INTO v_active USING v_fk_val;

  IF NOT COALESCE(v_active,FALSE) THEN
    RAISE EXCEPTION 'Parent %.% (id=%) non attivo: impossibile avere figlio attivo',
      v_parent_schema, v_parent_table, v_fk_val
      USING ERRCODE='23514';
  END IF;

  RETURN NEW;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
