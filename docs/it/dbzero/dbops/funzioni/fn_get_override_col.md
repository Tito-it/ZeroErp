{% include-markdown "it/dbzero/dbops/manual/fn_get_override_col.md" %}
# ⚙️ Funzione `fn_get_override_col`

```sql
CREATE FUNCTION fn_get_override_col(p_schema text, p_table text, p_role text, p_default text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_get_override_col(p_schema text, p_table text, p_role text, p_default text)
 RETURNS text
 LANGUAGE sql
AS $function$
     SELECT COALESCE((
       SELECT col_name
         FROM dbops.automation_overrides_cols
       WHERE schema_name=p_schema
         AND table_name=p_table
         AND col_role=p_role
       LIMIT 1
     ), p_default);
   $function$

COMMENT ON FUNCTION dbops.fn_get_override_col(p_schema text, p_table text, p_role text, p_default text)
IS 'Il nome della colonna che una tabella usa per un ruolo logico delle automazioni: l''override di dbops.automation_overrides_cols per (p_schema, p_table, p_role), una riga sola per chiave primaria, altrimenti p_default. I ruoli sono quelli del CHECK della tabella: ATTIVO_COL, STORICIZZA_COL, STORICO_FK, CODICE_COL, CODICE_INTERNO_COL. Non verifica che la colonna esista: per quello dbops.fn_col_exists. La usano i generatori e i trigger delle automazioni (ATTIVO, storico, provisioning dello storico), il risolutore dello scope dello storico e il presidio dbops.vw_marcatori_automazione_senza_esecutore.';
```

</div>

---
{% include-markdown "signature-core.md" %}
