{% include-markdown "it/dbzero/dbops/manual/fn_find_file_usage.md" %}
# ⚙️ Funzione `fn_find_file_usage`

```sql
CREATE FUNCTION fn_find_file_usage(p_target_table regclass)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_find_file_usage(p_target_table regclass)
 RETURNS TABLE(table_with_fk regclass, fk_name name, posizione bigint, fk_column name, referenced_table regclass, referenced_column name)
 LANGUAGE sql
 STABLE
AS $function$
  -- Scopo: le FK che puntano a una tabella, una riga per colonna
  --   della chiave. Le legge dbops.fn_foreign_keys_info.
  -- Uso: SELECT * FROM dbops.fn_find_file_usage('vendite.fatture');
  SELECT i.source_table, i.constraint_name, i.posizione, i.source_column,
         i.target_table, i.target_column
    FROM dbops.fn_foreign_keys_info(p_target_table) i
   WHERE i.relazione = 'incoming';
$function$

COMMENT ON FUNCTION dbops.fn_find_file_usage(p_target_table regclass)
IS 'Le FK che puntano a una tabella (chi la usa): una riga per colonna della chiave, con la tabella che porta la FK, il nome del vincolo, la posizione della colonna nella chiave, la colonna della figlia e quella del padre a cui punta (referenced_column: puo'' essere una UNIQUE che non e'' la chiave primaria). Sono le righe incoming di dbops.fn_foreign_keys_info: le coppie di colonne e il trattamento delle partizioni sono i suoi. Strumento DBA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
