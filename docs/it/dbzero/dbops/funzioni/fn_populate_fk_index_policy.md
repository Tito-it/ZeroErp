{% include-markdown "it/dbzero/dbops/manual/fn_populate_fk_index_policy.md" %}
# ⚙️ Funzione `fn_populate_fk_index_policy`

```sql
CREATE FUNCTION fn_populate_fk_index_policy()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_populate_fk_index_policy()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_nuove bigint;
  v_tolte bigint;
BEGIN
  WITH scoperte AS MATERIALIZED (
         SELECT v.schema_name, v.table_name, v.constraint_name,
                v.create_index_suggestion, v.decisione
           FROM dbops.vw_fk_senza_indice v
       ),
       tolte AS (
         DELETE FROM dbops.fk_index_policy p
          WHERE p.decisione = 'DA_DECIDERE'
            AND NOT EXISTS (SELECT 1
                              FROM scoperte s
                             WHERE s.schema_name = p.schema_name
                               AND s.table_name = p.table_name
                               AND s.constraint_name = p.constraint_name)
         RETURNING 1
       ),
       nuove AS (
         INSERT INTO dbops.fk_index_policy (schema_name, table_name, constraint_name, dll_command)
         SELECT s.schema_name, s.table_name, s.constraint_name, s.create_index_suggestion
           FROM scoperte s
          WHERE s.decisione IS NULL
         ON CONFLICT (schema_name, table_name, constraint_name) DO NOTHING
         RETURNING 1
       )
  SELECT (SELECT count(*) FROM nuove), (SELECT count(*) FROM tolte)
    INTO v_nuove, v_tolte;

  RAISE NOTICE 'fn_populate_fk_index_policy: da_decidere_nuove=%, da_decidere_tolte=%', v_nuove, v_tolte;
END;
$function$

COMMENT ON FUNCTION dbops.fn_populate_fk_index_policy()
IS 'La scoperta della politica degli indici: registra in dbops.fk_index_policy, come DA_DECIDERE, le FK scoperte (dbops.vw_fk_senza_indice) che non hanno una riga, e toglie le righe DA_DECIDERE la cui FK non e'' piu'' scoperta (tolta, rinominata o coperta da un indice). Non scrive ne'' tocca mai una decisione: CON_INDICE e SENZA_INDICE le scrive solo il seed, e una riga decisa resta anche se la sua FK non c''e'' (le FK verso django.auth_user nascono dopo Liquibase). Non crea indici: lo fa dbops.apply_fk_index_policy, che le DA_DECIDERE le lascia stare. La chiamano il 90_end a ogni migrate e il job settimanale (maintenance.proc_apply_fk_index_policy_job). NOTICE con le righe nuove e tolte.';
```

</div>

---
{% include-markdown "signature-core.md" %}
