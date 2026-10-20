{% include-markdown "it/dbzero/dbops/manual/fn_cleanup_at_params.md" %}
# ⚙️ Funzione `fn_cleanup_at_params`

```sql
CREATE FUNCTION fn_cleanup_at_params(p_schema text, p_table text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_cleanup_at_params(p_schema text, p_table text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_params jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rispondere con quale regola CLEANUP_AT una tabella
    --   scade, leggendola DALLA STESSA sorgente che usa il job
    --   settimanale: dbops.automation_rules_tbl.
    --
    -- ⭐ Esiste per non avere due termini di retention che
    --   divergono: quello scritto alla nascita dal trigger e
    --   quello applicato dal job al pregresso. La regola piu'
    --   specifica vince (priority, poi id), con fallback alla
    --   *all — stesso criterio di dbops.fn_run_automations_cleanup.
    --
    -- ⚠️ NULL = nessuna regola con ttl_days corrisponde. Il
    --   chiamante lascia allora cleanup_at a NULL e la riga
    --   non scade mai: in dubbio non si cancella.
    --
    -- Regole:
    --   - torna l'intero jsonb `params`: ttl_days, base_ts_column,
    --     cleanup_column, apply_on_update
    --   - schema o tabella vuoti → NULL, cioe' «nessuna regola».
    --     ⚠️ Non un raise: la funzione e' STABLE (un lookup, chiamato
    --     per riga da un trigger) e fn_log_and_raise_error SCRIVE
    --     una riga di log — plpgsql_check lo segnala. Senza il ramo,
    --     `*all` coprirebbe anche una tabella senza nome e la
    --     risposta sarebbe il default: qui invece «non so di che
    --     tabella parli» vale «non scade mai», in dubbio si conserva.
    -- =========================================================
    IF NULLIF(btrim(p_schema), '') IS NULL
       OR NULLIF(btrim(p_table), '') IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT r.params
      INTO v_params
      FROM dbops.automation_rules_tbl r
     WHERE r.enabled
       AND upper(btrim(r.rule_type)) = 'CLEANUP_AT'
       AND dbops.fn_schema_match(r.target_schema, p_schema)
       AND (upper(r.target_table) = '*ALL' OR p_table ILIKE r.target_table)
       AND (r.params ->> 'ttl_days') IS NOT NULL
     ORDER BY r.priority, r.id
     LIMIT 1;

    RETURN v_params;
END
$function$

COMMENT ON FUNCTION dbops.fn_cleanup_at_params(p_schema text, p_table text)
IS 'I params (ttl_days, base_ts_column, ...) della regola CLEANUP_AT piu'' specifica di dbops.automation_rules_tbl che copre la tabella: priority, poi id, fallback alla *all — lo stesso criterio di dbops.fn_run_automations_cleanup. ⭐ Esiste perche'' il termine sta in UNA sede sola: il trigger che scrive cleanup_at alla nascita e il job che lo applica al pregresso devono leggere lo stesso numero. Generalizza vendite.fn_event_log_ttl_days (ritirata). ⚠️ NULL = nessuna regola: la riga non scade mai (in dubbio non si cancella). Analisi: analisi-osservabilita-log.md, Passo D.';
```

</div>

---
{% include-markdown "signature-core.md" %}
