{% include-markdown "it/dbzero/dbops/manual/fn_get_child_fk_col.md" %}
# ⚙️ Funzione `fn_get_child_fk_col`

```sql
CREATE FUNCTION fn_get_child_fk_col(p_conoid oid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_get_child_fk_col(p_conoid oid)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
  DECLARE
    v_child_oid oid;
    v_col smallint;
    v_name text;
  BEGIN
    SELECT c.conrelid, c.conkey[1] INTO v_child_oid, v_col
    FROM pg_constraint c
    WHERE c.oid = p_conoid;

    SELECT a.attname INTO v_name
    FROM pg_attribute a
    WHERE a.attrelid = v_child_oid
      AND a.attnum   = v_col;

    RETURN v_name;
  END;
  $function$

COMMENT ON FUNCTION dbops.fn_get_child_fk_col(p_conoid oid)
IS 'Il nome della colonna figlia di un vincolo di foreign key, dato l''OID del vincolo (pg_constraint.oid): legge conrelid e la prima colonna (conkey[1]) e risale a pg_attribute. Per una FK composta restituisce solo la colonna in posizione 1; NULL se l''OID non e'' un vincolo. La chiama dbops.fn_run_automations_attivo, che lavora sulle FK a una colonna. Legge solo i cataloghi di sistema, ma e'' dichiarata VOLATILE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
