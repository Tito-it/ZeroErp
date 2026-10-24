{% include-markdown "it/dbzero/anagrafiche/manual/fn_check_fornitore_attivo.md" %}
# ⚙️ Funzione `fn_check_fornitore_attivo`

```sql
CREATE FUNCTION fn_check_fornitore_attivo(p_fornitore_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_fornitore_attivo(p_fornitore_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Puro boolean: true se fornitore attivo e stato non blocca ordini
    RETURN EXISTS (
        SELECT 1
        FROM   anagrafiche.fornitori f
        JOIN   config.stati_fornitore sf
          ON   sf.id = f.stato_fornitore_id
        WHERE  f.id = p_fornitore_id
          AND  f.attivo = true
          AND  sf.blocca_ordini = false
    );
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_fornitore_attivo(p_fornitore_id bigint)
IS 'Check puro boolean: ritorna TRUE se il fornitore e attivo e il suo stato non blocca ordini, FALSE altrimenti. No raise.';
```

</div>

---
{% include-markdown "signature-core.md" %}
