{% include-markdown "it/dbzero/dbops/manual/fn_cleanup_esclusa.md" %}
# ⚙️ Funzione `fn_cleanup_esclusa`

```sql
CREATE FUNCTION fn_cleanup_esclusa(p_schema text, p_table text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_cleanup_esclusa(p_schema text, p_table text)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: la tabella e' esclusa dal cleanup? Una riga abilitata di
    --   dbops.automation_cleanup_exclusions la toglie a tutte le regole CLEANUP_AT e
    --   CLEANUP_PURGE: niente scadenza, niente purge.
    -- Lettori: dbops.fn_cleanup_at_regola (la scadenza, per il trigger alla nascita e
    --   per il runner), dbops.fn_run_automations_cleanup (il salto della tabella),
    --   dbops.vw_marcatori_automazione_senza_esecutore (cleanup_at senza purge).
    SELECT EXISTS (
        SELECT 1
          FROM dbops.automation_cleanup_exclusions e
         WHERE e.enabled
           AND e.schema_name = p_schema
           AND e.table_name  = p_table);
$function$

COMMENT ON FUNCTION dbops.fn_cleanup_esclusa(p_schema text, p_table text)
IS 'true se la tabella ha una riga abilitata in dbops.automation_cleanup_exclusions: per il cleanup non esiste, ne'' per la scadenza (CLEANUP_AT) ne'' per il purge (CLEANUP_PURGE). Confronto esatto su schema e tabella. La leggono dbops.fn_cleanup_at_regola, dbops.fn_run_automations_cleanup e dbops.vw_marcatori_automazione_senza_esecutore.';
```

</div>

---
{% include-markdown "signature-core.md" %}
