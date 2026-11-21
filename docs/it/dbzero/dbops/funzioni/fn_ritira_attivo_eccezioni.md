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
-- Scopo: togliere i trigger ATTIVO gia' generati per le FK che
--   l'automazione non lega (dbops.fn_attivo_fk_esclusa): le eccezioni
--   dichiarate e le FK senza _id fuori dal registro delle inclusioni.
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
                   -- la figlia: il block la nomina negli argomenti,
                   -- il require sta sulla figlia stessa
                   CASE WHEN p.proname = 'trgfn_prevent_deactivate_if_children'
                        THEN g.figlia_schema  ELSE cn.nspname END AS figlia_schema,
                   CASE WHEN p.proname = 'trgfn_prevent_deactivate_if_children'
                        THEN g.figlia_tabella ELSE c.relname  END AS figlia_tabella,
                   g.fk_col
              FROM pg_catalog.pg_trigger t
              JOIN pg_catalog.pg_class c      ON c.oid = t.tgrelid
              JOIN pg_catalog.pg_namespace cn ON cn.oid = c.relnamespace
              JOIN pg_catalog.pg_proc p       ON p.oid = t.tgfoid
              JOIN pg_catalog.pg_namespace n  ON n.oid = p.pronamespace
              CROSS JOIN LATERAL dbops.fn_trigger_attivo_argomenti(
                  p.proname, dbops.fn_trigger_argomenti(t.tgargs)) AS g
             WHERE NOT t.tgisinternal
               AND n.nspname = 'dbops'
               AND p.proname IN ('trgfn_child_requires_active_parent',
                                 'trgfn_prevent_deactivate_if_children')
               -- un montaggio fuori grammatica non e' un ritiro:
               -- lo riporta dbops.fn_trigger_attivo_orfani
               AND g.valido
        )
        SELECT trg.tgname, trg.tgrelid
          FROM trg
         WHERE dbops.fn_attivo_fk_esclusa(trg.figlia_schema, trg.figlia_tabella, trg.fk_col) IS NOT NULL
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s', v_trigger, v_tabella::regclass);
        RAISE NOTICE 'fn_ritira_attivo_eccezioni: ritirato % su %', v_trigger, v_tabella::regclass;
        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION dbops.fn_ritira_attivo_eccezioni()
IS 'Toglie i trigger ATTIVO gia'' generati per le FK che l''automazione non lega, chiedendolo a dbops.fn_attivo_fk_esclusa: le FK dichiarate in dbops.automazione_attivo_eccezioni e le FK la cui colonna non finisce in _id e che non sono in dbops.automazione_attivo_inclusioni. Toglie il require sul figlio (dbops.trgfn_child_requires_active_parent, sulla tabella figlia, con quella colonna FK) e il block sul padre (dbops.trgfn_prevent_deactivate_if_children, che nomina quella figlia e quella colonna FK); vale anche per un trigger ATTIVO montato a mano, che su una FK senza _id va dichiarato nel registro delle inclusioni. Li riconosce per FUNZIONE e ARGOMENTI, non per nome (i nomi generati oltre 63 caratteri sono troncati con un hash); gli argomenti li legge per nome dbops.fn_trigger_attivo_argomenti, la grammatica delle funzioni trigger. Un montaggio fuori grammatica non si tocca: lo riporta dbops.fn_trigger_attivo_orfani. Torna quanti ne ha tolti. Chiamata in testa da dbops.fn_run_automations_attivo (chi genera ritira).';
```

</div>

---
{% include-markdown "signature-core.md" %}
