{% include-markdown "it/dbzero/dbops/manual/trgfn_prevent_deactivate_if_children.md" %}
# ⚙️ Funzione `trgfn_prevent_deactivate_if_children`

```sql
CREATE FUNCTION trgfn_prevent_deactivate_if_children()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_prevent_deactivate_if_children()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
  DECLARE
    v_child_schema text := TG_ARGV[0];
    v_child_table  text := TG_ARGV[1];
    v_fk_col       text := TG_ARGV[2];
    v_exists       boolean;
    v_sql          text;
  BEGIN
    IF TG_OP='UPDATE' AND OLD.attivo IS TRUE AND NEW.attivo IS FALSE THEN
      v_sql := format('SELECT EXISTS (SELECT 1 FROM %I.%I WHERE %I=$1)', v_child_schema, v_child_table, v_fk_col);
      EXECUTE v_sql INTO v_exists USING OLD.id;
      IF v_exists THEN
        RAISE EXCEPTION 'Non è possibile disattivare %.% (id=%): esistono righe figlio in %.%',
          TG_TABLE_SCHEMA, TG_TABLE_NAME, OLD.id, v_child_schema, v_child_table
          USING ERRCODE='23503';
      END IF;
    END IF;
    RETURN NEW;
  END;
  $function$
```

---
{% include-markdown "signature-core.md" %}
