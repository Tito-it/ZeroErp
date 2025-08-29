{% include-markdown "it/dbzero/dbops/manual/fn_run_automations.md" %}
# ⚙️ Funzione `fn_run_automations`

```sql
CREATE FUNCTION fn_run_automations(p_exec_mode text, p_schemas text[], p_dry_run boolean, p_parts text[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_run_automations(p_exec_mode text DEFAULT 'AUTO'::text, p_schemas text[] DEFAULT NULL::text[], p_dry_run boolean DEFAULT false, p_parts text[] DEFAULT ARRAY['TX_ID'::text, 'AUDIT_UPDATE'::text, 'STORICO'::text, 'ATTIVO'::text])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_schemas text[];
  needs_table_rules boolean;
BEGIN
  -- Orchestratore: calcola scope e chiama le parti richieste.
  -- p_parts: 'TX_ID','AUDIT_UPDATE','STORICO','ATTIVO' (e 'TABLE_RULES' per compatibilità) 

  -- Scope schemi
  IF p_schemas IS NOT NULL THEN
    v_schemas := p_schemas;
  ELSE
    IF EXISTS (
      SELECT 1
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='dbops' AND c.relname='automation_scope' AND c.relkind='r'
    ) AND EXISTS (SELECT 1 FROM dbops.automation_scope)
    THEN
      SELECT array_agg(DISTINCT schema_name) INTO v_schemas
        FROM dbops.automation_scope;
    ELSE
      SELECT array_agg(nspname) INTO v_schemas
        FROM pg_namespace
      WHERE n.nspname NOT LIKE 'pg_%'
        AND n.nspname <> 'information_schema'
        AND n.nspname <> 'storico';
    END IF;
  END IF;

  -- Compatibilità: se p_parts contiene 'TABLE_RULES', abilita i tre moduli tabellari
  needs_table_rules := ('TABLE_RULES' = ANY(p_parts));

  IF needs_table_rules OR 'TX_ID' = ANY(p_parts) THEN
    PERFORM dbops.fn_run_automations_tx_id(p_exec_mode, v_schemas, p_dry_run);
  END IF;

  IF needs_table_rules OR 'AUDIT_UPDATE' = ANY(p_parts) THEN
    PERFORM dbops.fn_run_automations_audit_update(p_exec_mode, v_schemas, p_dry_run);
  END IF;

  IF needs_table_rules OR 'STORICO' = ANY(p_parts) THEN
    PERFORM dbops.fn_run_automations_storico(p_exec_mode, v_schemas, p_dry_run);
  END IF;

  IF 'ATTIVO' = ANY(p_parts) THEN
    PERFORM dbops.fn_run_automations_attivo(p_exec_mode, v_schemas, p_dry_run);
  END IF;
END;
$function$
```

---
{% include-markdown "signature-core.md" %}
