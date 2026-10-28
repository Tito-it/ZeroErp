# ⚙️ Funzione `fn_migrate_add_indirizzo_normalizzato`

```sql
CREATE FUNCTION fn_migrate_add_indirizzo_normalizzato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_migrate_add_indirizzo_normalizzato()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- verifico se la colonna è già stata creata
  IF NOT EXISTS (
    SELECT 1
      FROM information_schema.columns
     WHERE table_schema = 'anagrafiche'
       AND table_name   = 'indirizzi_dettaglio'
       AND column_name  = 'indirizzo_normalizzato'
  ) THEN
    -- eseguo il DDL
    EXECUTE $ddl$
      ALTER TABLE anagrafiche.indirizzi_dettaglio
        ADD COLUMN indirizzo_normalizzato text
          GENERATED ALWAYS AS (
            TRIM(
              via_norm
              || COALESCE(', '     || civico_norm,      '')
              || COALESCE(', Pal.' || palazzina,        '')
              || COALESCE(', Scala '  || scala,         '')
              || COALESCE(', P'      || piano,          '')
              || COALESCE(', Int.'   || interno,        '')
            )
          ) STORED;
    $ddl$;
  END IF;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
