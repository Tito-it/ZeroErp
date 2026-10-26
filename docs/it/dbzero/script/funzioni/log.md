{% include-markdown "it/dbzero/script/manual/log.md" %}
# ⚙️ Funzione `log`

```sql
CREATE FUNCTION log(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.log(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
 RETURNS void
 LANGUAGE sql
AS $function$
    --  Completa con VARIADIC: 6 argomenti
  SELECT script.fn_log_error_only($1,$2,$3,$4,$5, VARIADIC $6)
$function$

COMMENT ON FUNCTION script.log(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
IS 'Façade completo: supporta VARIADIC valori per format().';
```

</div>

---
{% include-markdown "signature-core.md" %}
