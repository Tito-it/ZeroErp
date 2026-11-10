{% include-markdown "it/dbzero/dbops/manual/fn_jsonb_array_di_testi.md" %}
# ⚙️ Funzione `fn_jsonb_array_di_testi`

```sql
CREATE FUNCTION fn_jsonb_array_di_testi(p_valore jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_jsonb_array_di_testi(p_valore jsonb)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Scopo: il valore e' NULL oppure un array JSON di soli testi? La forma delle chiavi di
    --   dbops.automazione_overlap, letta dal suo CHECK (una subquery non puo' stare in un CHECK).
    -- jsonb e non %TYPE: serve due colonne, e potra' servire altri registri.
    SELECT p_valore IS NULL
        OR (jsonb_typeof(p_valore) = 'array'
            AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(p_valore) AS e(x)
                             WHERE jsonb_typeof(e.x) <> 'string'));
$function$

COMMENT ON FUNCTION dbops.fn_jsonb_array_di_testi(p_valore jsonb)
IS 'true se il valore e'' NULL o un array JSON i cui elementi sono tutti testi. La legge il CHECK chk_automazione_overlap_chiavi su key_columns e key_expressions di dbops.automazione_overlap.';
```

</div>

---
{% include-markdown "signature-core.md" %}
