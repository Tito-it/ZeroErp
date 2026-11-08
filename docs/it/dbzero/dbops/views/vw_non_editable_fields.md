{% include-markdown "it/dbzero/dbops/manual/vw_non_editable_fields.md" %}
# 🔍 View `vw_non_editable_fields`

> 📝 **Descrizione**
>
> I campi che il form deve presentare non modificabili per lock incondizionato: una riga per colonna che un trigger di lock vivo e abilitato blocca (dbops.vw_lock_columns_vivi), con il codice d'errore che l'UPDATE solleverebbe. Dice cio' che il database rifiuta, codice_interno compreso, e non cio' che il registro dbops.automation_lock_columns dichiara: se i due divergono e' rosso il presidio dbops/test-lock-columns-convergenza. Una colonna bloccata da due trigger compare due volte. I lock condizionali, che dipendono dallo stato della riga, non ci sono: li aggiunge dbops.fn_non_editable_fields.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_non_editable_fields
WITH (security_invoker=true) AS
SELECT v.schema_name AS target_schema,
    v.table_name AS target_table,
    v.argomenti[g.i] AS column_name,
    v.argomenti[(g.i + 1)] AS error_code,
    v.trigger_name
   FROM (dbops.vw_lock_columns_vivi v
     CROSS JOIN LATERAL generate_series(1, (cardinality(v.argomenti) - 1), 2) g(i))
  WHERE v.abilitato;
```

</div>


---
{% include-markdown "signature-core.md" %}
