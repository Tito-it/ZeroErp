{% include-markdown "it/dbzero/vendite/manual/trgfn_preventivi_righe_ricalcola_totali.md" %}
# ⚙️ Funzione `trgfn_preventivi_righe_ricalcola_totali`

```sql
CREATE FUNCTION trgfn_preventivi_righe_ricalcola_totali()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_righe_ricalcola_totali()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_pid  vendite.preventivi_righe.preventivo_id%TYPE;
  v_sql  text;
BEGIN
  -- Costruisce la query in base all'evento DML:
  -- INSERT -> solo new_rows (transition table disponibile)
  -- DELETE -> solo old_rows
  -- UPDATE -> UNION di entrambe (copre cambio preventivo_id)
  IF TG_OP = 'INSERT' THEN
    v_sql := 'SELECT DISTINCT preventivo_id FROM new_rows';
  ELSIF TG_OP = 'DELETE' THEN
    v_sql := 'SELECT DISTINCT preventivo_id FROM old_rows';
  ELSE
    -- UPDATE: ricalcola sia per il vecchio che per il nuovo preventivo_id
    v_sql := 'SELECT DISTINCT preventivo_id FROM new_rows '
          || 'UNION '
          || 'SELECT DISTINCT preventivo_id FROM old_rows';
  END IF;

  -- Ricalcola una sola volta per ogni preventivo coinvolto
  FOR v_pid IN EXECUTE v_sql
  LOOP
    PERFORM vendite.fn_ricalcola_totali_preventivo(v_pid);
  END LOOP;

  RETURN NULL;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_preventivi_righe_ricalcola_totali()
IS 'Trigger function STATEMENT-level: ricalcola totali testata per ogni preventivo coinvolto. Usa EXECUTE + transition tables PG 18.';
```

</div>

---
{% include-markdown "signature-core.md" %}
