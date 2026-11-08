{% include-markdown "it/dbzero/dbops/manual/fn_regola_automazione_valida.md" %}
# ⚙️ Funzione `fn_regola_automazione_valida`

```sql
CREATE FUNCTION fn_regola_automazione_valida(p_rule_type text, p_exec_mode text, p_name_template text, p_params jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_regola_automazione_valida(p_rule_type text, p_exec_mode text, p_name_template text, p_params jsonb)
 RETURNS boolean
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
-- Scopo: una regola di dbops.automation_rules_tbl e' ben formata? La legge il
--   CHECK chk_automation_rules_tbl_regola_valida: una regola malformata non
--   entra, cosi' i runner non devono difendersi da lei.
-- Regole:
--   - params e' un oggetto JSON;
--   - le regole che montano un trigger dichiarano il nome (name_template non
--     vuoto): il nome sta nel registro, e solo li';
--   - ATTIVO: name_template e' un oggetto JSON con "block" e "require", e
--     ognuno ha il segnaposto dell'hash della FK ({fkhash6} o
--     {fkhash6_if_long}): due FK della stessa coppia devono poter avere due nomi;
--   - CLEANUP_AT e CLEANUP_PURGE valgono sempre (exec_mode AUTO): la scadenza la
--     scrive anche un trigger alla nascita, che non e' una corsa;
--   - CLEANUP_AT: ttl_days intero >= 1; apply_on_update booleano;
--     base_ts_column testo; nessun'altra chiave;
--   - CLEANUP_PURGE: batch_limit intero >= 1; nessun'altra chiave.
--   ⭐ Le chiavi del cleanup sono un elenco chiuso: una chiave che nessuno legge
--     (per esempio cleanup_column: la scadenza sta sempre in cleanup_at) e'
--     una manopola che non gira, e chi la scrive crede di aver cambiato qualcosa.
DECLARE
    v_t jsonb;
BEGIN
    IF p_params IS NULL OR jsonb_typeof(p_params) <> 'object' THEN
        RETURN false;
    END IF;

    IF p_rule_type IN ('TX_ID', 'AUDIT_UPDATE', 'STORICO', 'LOCK_COLUMNS',
                       'DATE_VALIDITA', 'CODICE_MAIUSCOLO')
       AND NULLIF(btrim(p_name_template), '') IS NULL THEN
        RETURN false;
    END IF;

    IF p_rule_type = 'ATTIVO' THEN
        IF p_name_template IS NULL OR NOT pg_input_is_valid(p_name_template, 'jsonb') THEN
            RETURN false;
        END IF;
        v_t := p_name_template::jsonb;
        IF jsonb_typeof(v_t) <> 'object'
           OR jsonb_typeof(v_t -> 'block') IS DISTINCT FROM 'string'
           OR jsonb_typeof(v_t -> 'require') IS DISTINCT FROM 'string'
           OR position('{fkhash6' IN v_t ->> 'block') = 0
           OR position('{fkhash6' IN v_t ->> 'require') = 0 THEN
            RETURN false;
        END IF;
    END IF;

    IF p_rule_type IN ('CLEANUP_AT', 'CLEANUP_PURGE') AND p_exec_mode <> 'AUTO' THEN
        RETURN false;
    END IF;

    IF p_rule_type = 'CLEANUP_AT' THEN
        IF jsonb_typeof(p_params -> 'ttl_days') IS DISTINCT FROM 'number'
           OR (p_params ->> 'ttl_days')::numeric <> trunc((p_params ->> 'ttl_days')::numeric)
           OR (p_params ->> 'ttl_days')::numeric < 1 THEN
            RETURN false;
        END IF;
        IF p_params ? 'apply_on_update'
           AND jsonb_typeof(p_params -> 'apply_on_update') <> 'boolean' THEN
            RETURN false;
        END IF;
    END IF;

    IF p_rule_type = 'CLEANUP_PURGE' AND p_params ? 'batch_limit'
       AND (   jsonb_typeof(p_params -> 'batch_limit') <> 'number'
            OR (p_params ->> 'batch_limit')::numeric <> trunc((p_params ->> 'batch_limit')::numeric)
            OR (p_params ->> 'batch_limit')::numeric < 1) THEN
        RETURN false;
    END IF;

    IF p_rule_type = 'CLEANUP_AT'
       AND (   (p_params ? 'base_ts_column' AND jsonb_typeof(p_params -> 'base_ts_column') <> 'string')
            OR EXISTS (SELECT 1 FROM jsonb_object_keys(p_params) k
                        WHERE k NOT IN ('ttl_days', 'apply_on_update', 'base_ts_column'))) THEN
        RETURN false;
    END IF;

    IF p_rule_type = 'CLEANUP_PURGE'
       AND EXISTS (SELECT 1 FROM jsonb_object_keys(p_params) k WHERE k <> 'batch_limit') THEN
        RETURN false;
    END IF;

    RETURN true;
END;
$function$

COMMENT ON FUNCTION dbops.fn_regola_automazione_valida(p_rule_type text, p_exec_mode text, p_name_template text, p_params jsonb)
IS 'true se una regola di dbops.automation_rules_tbl e'' ben formata; la legge il CHECK chk_automation_rules_tbl_regola_valida. params e'' un oggetto JSON; le regole che montano un trigger (TX_ID, AUDIT_UPDATE, STORICO, LOCK_COLUMNS, DATE_VALIDITA, CODICE_MAIUSCOLO) dichiarano name_template; ATTIVO dichiara un oggetto JSON con block e require, ciascuno col segnaposto dell''hash della FK ({fkhash6} o {fkhash6_if_long}); CLEANUP_AT e CLEANUP_PURGE hanno exec_mode AUTO, perche'' la scadenza la scrive anche il trigger alla nascita; CLEANUP_AT ha ttl_days intero >= 1, apply_on_update booleano, base_ts_column testo e nessun''altra chiave; CLEANUP_PURGE batch_limit intero >= 1 e nessun''altra chiave (la scadenza sta sempre in cleanup_at: una chiave che nessuno legge non entra). Una regola malformata non entra nel registro, cosi'' i runner non la convertono alla cieca.';
```

</div>

---
{% include-markdown "signature-core.md" %}
