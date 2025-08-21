# ⚙️ Funzione `fn_name_from_template`

```sql
CREATE FUNCTION fn_name_from_template(p_template text, p_schema text, p_table text, p_parent text, p_child text, p_fk text, p_op text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_name_from_template(p_template text, p_schema text, p_table text, p_parent text DEFAULT NULL::text, p_child text DEFAULT NULL::text, p_fk text DEFAULT NULL::text, p_op text DEFAULT NULL::text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
  DECLARE
    s text;
  BEGIN
    -- ----------------------------------------------
    --  p_template → stringa modello, può contenere placeholder come 
    --  {schema}, {table}, {parent}, {child}, {fk}, {op}.
    --       es. {schema}.{table} → {schema}.{table}
    --   p_schema → nome dello schema di destinazione.
    --   p_table → nome della tabella di destinazione.
    --   p_parent → nome della tabella padre (per FK).
    --   p_child → nome della tabella figlia (per FK).
    --   p_fk → nome della foreign key.
    --    p_op → operazione (INS, UPD, DEL, ecc.).
    ----------------------------------------------

    s := p_template;
    s := replace(s, '{schema}', COALESCE(p_schema,''));
    s := replace(s, '{table}',  COALESCE(p_table,''));
    s := replace(s, '{parent}', COALESCE(p_parent,''));
    s := replace(s, '{child}',  COALESCE(p_child,''));
    s := replace(s, '{fk}',     COALESCE(p_fk,''));
    s := replace(s, '{op}',     COALESCE(p_op,''));

    IF length(s) <= 63 THEN
      RETURN s;
    ELSE
      -- hash compatto e non deprecato
      RETURN left(s, 63-1-6) || '_' || substr(to_hex(hashtextextended(s, 0)), 1, 6);
    END IF;
  END;
  $function$
```

---
{% include-markdown "signature-core.md" %}
