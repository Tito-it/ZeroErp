{% include-markdown "it/dbzero/dbops/manual/fn_ritira_attivo_eccezioni.md" %}
# ⚙️ Funzione `fn_ritira_attivo_eccezioni`

```sql
CREATE FUNCTION fn_ritira_attivo_eccezioni()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_ritira_attivo_eccezioni()
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: togliere i trigger ATTIVO gia' generati per le FK dichiarate
--   eccezione in dbops.automazione_attivo_eccezioni.
-- Uso: SELECT dbops.fn_ritira_attivo_eccezioni();  -- quanti ne ha tolti
DECLARE
    r      record;
    v_n    integer := 0;
BEGIN
    FOR r IN
        WITH trg AS (
            SELECT t.tgname,
                   t.tgrelid,
                   p.proname,
                   -- rev 20260926-02: argomenti dal building block.
                   dbops.fn_trigger_argomenti(t.tgargs) AS a
              FROM pg_trigger t
              JOIN pg_proc p      ON p.oid = t.tgfoid
              JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE NOT t.tgisinternal
               AND n.nspname = 'dbops'
               AND p.proname IN ('trgfn_child_requires_active_parent',
                                 'trgfn_prevent_deactivate_if_children')
        )
        SELECT trg.tgname, trg.tgrelid::regclass AS rel
          FROM trg
          JOIN dbops.automazione_attivo_eccezioni e
            ON (    trg.proname = 'trgfn_child_requires_active_parent'
                AND trg.tgrelid = to_regclass(format('%I.%I', e.schema_figlia, e.tabella_figlia))
                AND trg.a[4]    = e.colonna_fk)
            OR (    trg.proname = 'trgfn_prevent_deactivate_if_children'
                AND trg.a[1]    = e.schema_figlia
                AND trg.a[2]    = e.tabella_figlia
                AND trg.a[3]    = e.colonna_fk)
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s', r.tgname, r.rel);
        RAISE NOTICE 'fn_ritira_attivo_eccezioni: ritirato % su %', r.tgname, r.rel;
        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION dbops.fn_ritira_attivo_eccezioni()
IS 'Toglie i trigger ATTIVO gia'' generati per le FK dichiarate eccezione in dbops.automazione_attivo_eccezioni: il require sul figlio (dbops.trgfn_child_requires_active_parent, colonna FK = argomento 4) e il block sul padre (dbops.trgfn_prevent_deactivate_if_children, argomenti 1-3 = schema, tabella e colonna FK della figlia). Li riconosce per FUNZIONE e ARGOMENTI, non per nome (i nomi generati oltre 63 caratteri sono hashati); gli argomenti li legge dbops.fn_trigger_argomenti (rev 20260926-02). Torna quanti ne ha tolti. Chiamata in testa da dbops.fn_run_automations_attivo (chi genera ritira) e una volta da 90_end/20260925-50. Brief: brief-db-blocco-login-per-credenziale §12.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
