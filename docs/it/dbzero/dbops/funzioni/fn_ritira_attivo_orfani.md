{% include-markdown "it/dbzero/dbops/manual/fn_ritira_attivo_orfani.md" %}
# ⚙️ Funzione `fn_ritira_attivo_orfani`

```sql
CREATE FUNCTION fn_ritira_attivo_orfani()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_ritira_attivo_orfani()
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: togliere i trigger ATTIVO che nominano una tabella o una
--   colonna che non esiste piu'.
-- Uso: SELECT dbops.fn_ritira_attivo_orfani();  -- quanti ne ha tolti
DECLARE
    v_tabella   pg_catalog.pg_trigger.tgrelid%TYPE;
    v_trigger   pg_catalog.pg_trigger.tgname%TYPE;
    -- motivo e dettaglio vengono dal lettore, calcolati: text
    v_motivo    text;
    v_dettaglio text;
    -- conteggio: nessuna colonna da ancorare
    v_n         integer := 0;
BEGIN
    FOR v_tabella, v_trigger, v_motivo, v_dettaglio IN
        SELECT o.tabella, o.trigger_nome, o.motivo, o.dettaglio
          FROM dbops.fn_trigger_attivo_orfani() AS o
         WHERE o.motivo IN ('TABELLA_ASSENTE', 'COLONNA_ASSENTE')
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %s', v_trigger, v_tabella::regclass);
        RAISE NOTICE 'fn_ritira_attivo_orfani: ritirato % su % (% : %)',
            v_trigger, v_tabella::regclass, v_motivo, v_dettaglio;
        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION dbops.fn_ritira_attivo_orfani()
IS 'Toglie i trigger ATTIVO che nominano una tabella o una colonna che non esiste piu'' (motivi TABELLA_ASSENTE e COLONNA_ASSENTE di dbops.fn_trigger_attivo_orfani, il lettore unico). Non tocca ARGOMENTI_INVALIDI: e'' un errore di scrittura, lo segnala il presidio. Torna quanti ne ha tolti. Chiamata in testa da dbops.fn_run_automations_attivo, fuori dal dry run, accanto a dbops.fn_ritira_attivo_eccezioni: chi genera ritira, e un DROP TABLE della figlia non lascia il block sul padre a sollevare E_ATTIVO_BLOCK_FKCOL_NOT_FOUND.';
```

</div>

---
{% include-markdown "signature-core.md" %}
