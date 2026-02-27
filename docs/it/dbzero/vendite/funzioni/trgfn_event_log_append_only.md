# ⚙️ Funzione `trgfn_event_log_append_only`

```sql
CREATE FUNCTION trgfn_event_log_append_only()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_event_log_append_only()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  RAISE EXCEPTION 'vendite.event_log e'' append-only: operazione % non consentita', TG_OP;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
