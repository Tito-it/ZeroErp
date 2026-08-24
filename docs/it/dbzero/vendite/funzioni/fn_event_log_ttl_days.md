# ⚙️ Funzione `fn_event_log_ttl_days`

```sql
CREATE FUNCTION fn_event_log_ttl_days()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_event_log_ttl_days()
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_ttl_days integer;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rispondere quanti giorni vive una riga di event_log,
    --   leggendolo DALLA STESSA sorgente che usa l'automazione
    --   settimanale: dbops.automation_rules_tbl.
    --
    -- ⭐ Esiste per non avere due termini di retention che
    --   divergono: quello del trigger e quello del job. La
    --   regola piu' specifica vince (priority, poi id), con
    --   fallback alla *all — stesso criterio di
    --   dbops.fn_run_automations_cleanup.
    --
    -- ⚠️ NULL = nessuna regola corrisponde. Il chiamante lascia
    --   allora cleanup_at a NULL e la riga non scade mai:
    --   in dubbio non si cancella.
    -- =========================================================
    SELECT (r.params ->> 'ttl_days')::integer
      INTO v_ttl_days
      FROM dbops.automation_rules_tbl r
     WHERE r.enabled
       AND upper(btrim(r.rule_type)) = 'CLEANUP_AT'
       AND dbops.fn_schema_match(r.target_schema, 'vendite')
       AND (upper(r.target_table) = '*ALL' OR 'event_log' ILIKE r.target_table)
       AND (r.params ->> 'ttl_days') IS NOT NULL
     ORDER BY r.priority, r.id
     LIMIT 1;

    RETURN v_ttl_days;
END
$function$

COMMENT ON FUNCTION vendite.fn_event_log_ttl_days()
IS 'Giorni di vita di una riga di vendite.event_log, letti da dbops.automation_rules_tbl (regola CLEANUP_AT piu'' specifica, fallback *all). ⭐ Esiste perche'' il termine sta in UNA sede sola: il trigger che valorizza cleanup_at e il job settimanale devono leggere lo stesso numero. ⚠️ NULL = nessuna regola: la riga non scade mai (in dubbio non si cancella).';
```

---
{% include-markdown "signature-core.md" %}
