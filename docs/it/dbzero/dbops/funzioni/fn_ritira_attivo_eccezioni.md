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
    v_trigger pg_catalog.pg_trigger.tgname%TYPE;
    v_tabella pg_catalog.pg_trigger.tgrelid%TYPE;
    -- conteggio: nessuna colonna da ancorare
    v_n       integer := 0;
BEGIN
    FOR v_trigger, v_tabella IN
        WITH trg AS (
            SELECT t.tgname,
                   t.tgrelid,
                   p.proname,
                   g.figlia_schema,
                   g.figlia_tabella,
                   g.fk_col
              FROM pg_catalog.pg_trigger t
              JOIN pg_catalog.pg_proc p      ON p.oid = t.tgfoid
              JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
              CROSS JOIN LATERAL dbops.fn_trigger_attivo_argomenti(
                  p.proname, dbops.fn_trigger_argomenti(t.tgargs)) AS g
             WHERE NOT t.tgisinternal
               AND n.nspname = 'dbops'
               AND p.proname IN ('trgfn_child_requires_active_parent',
                                 'trgfn_prevent_deactivate_if_children')
        )
        SELECT trg.tgname, trg.tgrelid
          FROM trg
          JOIN dbops.automazione_attivo_eccezioni e
            ON (    trg.proname        = 'trgfn_child_requires_active_parent'
                AND trg.tgrelid        = to_regclass(format('%I.%I', e.schema_figlia, e.tabella_figlia))
                AND trg.fk_col         = e.colonna_fk)
            OR (    trg.proname        = 'trgfn_prevent_deactivate_if_children'
                AND trg.figlia_schema  = e.schema_figlia
                AND trg.figlia_tabella = e.tabella_figlia
                AND trg.fk_col         = e.colonna_fk)
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s', v_trigger, v_tabella::regclass);
        RAISE NOTICE 'fn_ritira_attivo_eccezioni: ritirato % su %', v_trigger, v_tabella::regclass;
        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION dbops.fn_ritira_attivo_eccezioni()
IS 'Toglie i trigger ATTIVO gia'' generati per le FK dichiarate eccezione in dbops.automazione_attivo_eccezioni: il require sul figlio (dbops.trgfn_child_requires_active_parent, sulla tabella figlia, con quella colonna FK) e il block sul padre (dbops.trgfn_prevent_deactivate_if_children, che nomina quella figlia e quella colonna FK). Li riconosce per FUNZIONE e ARGOMENTI, non per nome (i nomi generati oltre 63 caratteri sono troncati con un hash); gli argomenti li legge per nome dbops.fn_trigger_attivo_argomenti, la grammatica delle funzioni trigger. Un montaggio fuori grammatica non e'' riconosciuto: lo riporta dbops.fn_trigger_attivo_orfani. Torna quanti ne ha tolti. Chiamata in testa da dbops.fn_run_automations_attivo (chi genera ritira).';
```

</div>

---
{% include-markdown "signature-core.md" %}
