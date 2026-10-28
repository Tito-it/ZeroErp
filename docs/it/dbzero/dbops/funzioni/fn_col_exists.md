{% include-markdown "it/dbzero/dbops/manual/fn_col_exists.md" %}
# ⚙️ Funzione `fn_col_exists`

```sql
CREATE FUNCTION fn_col_exists(p_schema text, p_table text, p_col text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_col_exists(p_schema text, p_table text, p_col text)
 RETURNS boolean
 LANGUAGE sql
AS $function$
    SELECT EXISTS(
      SELECT 1
        FROM information_schema.columns
      WHERE table_schema=p_schema
        AND table_name=p_table
        AND column_name=p_col
    );
  $function$

COMMENT ON FUNCTION dbops.fn_col_exists(p_schema text, p_table text, p_col text)
IS '
    Verifica se una **colonna** esiste in una tabella specificata, interrogando
    `information_schema.columns`.

    • **Ritorno**: `boolean` — TRUE se la colonna esiste (`schema`, `table`, `column`),
      altrimenti FALSE.

    • **Parametri**
      - `p_schema text`: schema della tabella.
      - `p_table  text`: nome della tabella.
      - `p_col    text`: nome della colonna.

    • **Note implementative**
      - Usa `EXISTS(...)` su `information_schema.columns` con match esatto su `table_schema`,
        `table_name`, `column_name`.
      - Leggera e **idempotente**, adatta a controlli pre-creazione di trigger/constraint.

    • **Casi d’uso tipici**
      - Pipeline di automazione per generare solo ciò che è coerente con lo schema corrente.
      - Validazioni in funzioni di provisioning/maintenance.

    • **Limitazioni**
      - Sensibile a maiuscole/minuscole se i nomi sono stati creati con doppie virgolette e case mixing.
    ';
```

</div>

---
{% include-markdown "signature-core.md" %}
