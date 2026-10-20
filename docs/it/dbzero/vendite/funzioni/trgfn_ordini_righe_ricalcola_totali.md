{% include-markdown "it/dbzero/vendite/manual/trgfn_ordini_righe_ricalcola_totali.md" %}
# ⚙️ Funzione `trgfn_ordini_righe_ricalcola_totali`

```sql
CREATE FUNCTION trgfn_ordini_righe_ricalcola_totali()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_righe_ricalcola_totali()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ordine_id vendite.ordini_righe.ordine_id%TYPE;
    v_sql       text;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_sql := 'SELECT DISTINCT ordine_id FROM new_rows WHERE ordine_id IS NOT NULL';
    ELSIF TG_OP = 'DELETE' THEN
        v_sql := 'SELECT DISTINCT ordine_id FROM old_rows WHERE ordine_id IS NOT NULL';
    ELSE
        v_sql := 'SELECT DISTINCT ordine_id FROM new_rows WHERE ordine_id IS NOT NULL '
              || 'UNION '
              || 'SELECT DISTINCT ordine_id FROM old_rows WHERE ordine_id IS NOT NULL';
    END IF;

    FOR v_ordine_id IN EXECUTE v_sql
    LOOP
        PERFORM vendite.fn_ricalcola_totali_ordine(v_ordine_id);
    END LOOP;

    RETURN NULL;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_ordini_righe_ricalcola_totali()
IS 'Trigger function STATEMENT-level: ricalcola i totali testata per ogni ordine coinvolto da INSERT/UPDATE/DELETE su vendite.ordini_righe. Usa transition tables PG 18.';
```

</div>

---
{% include-markdown "signature-core.md" %}
