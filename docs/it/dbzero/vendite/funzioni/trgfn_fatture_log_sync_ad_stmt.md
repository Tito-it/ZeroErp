{% include-markdown "it/dbzero/vendite/manual/trgfn_fatture_log_sync_ad_stmt.md" %}
# ⚙️ Funzione `trgfn_fatture_log_sync_ad_stmt`

```sql
CREATE FUNCTION trgfn_fatture_log_sync_ad_stmt()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_log_sync_ad_stmt()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_ids bigint[];
BEGIN
  SELECT array_agg(DISTINCT o.fattura_id)::bigint[]
    INTO v_ids
    FROM old_table o
   WHERE o.fattura_id IS NOT NULL;

  PERFORM vendite.fn_sync_fatture_log_critical_lotto(v_ids);
  RETURN NULL;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_log_sync_ad_stmt()
IS 'AFTER DELETE statement su fatture_log: sincronizza critical/stato_esecuzione per fatture toccate.';
```

</div>

---
{% include-markdown "signature-core.md" %}
