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
IS '
  Ritorna il **nome della colonna** da usare per un certo *ruolo logico* (es. `AUDIT_TS`,
  `AUDIT_USER`, `ATTIVO_COL`, `STORICO_FK`) verificando prima un **override** nella tabella
  `dbops.automation_overrides_cols`. Se non presente, restituisce il **valore di default**
  passato in input.

   **Ritorno**: `text` — Nome colonna effettivo (override se presente, altrimenti `p_default`).

   **Parametri**
    - `p_schema text`: schema della tabella.
    - `p_table  text`: nome della tabella.
    - `p_role   text`: ruolo logico della colonna (chiave su `automation_overrides_cols.col_role`).
    - `p_default text`: nome colonna di default da usare in assenza di override.

   **Note implementative**
    - Query diretta su `dbops.automation_overrides_cols` con `LIMIT 1`.
    - Usa `COALESCE(..., p_default)` per garantire sempre un valore di ritorno.

   **Casi d’uso tipici**
    - Generazione/validazione automatica di trigger e funzioni che dipendono da colonne “convenzione”.
    - Personalizzazione per tabella di audit columns o fk di storico.

   **Limitazioni**
    - Non valida l’esistenza reale della colonna; in combinazione usare `dbops._col_exists`.
  ';
```

</div>

---
{% include-markdown "signature-core.md" %}
