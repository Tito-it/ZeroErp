{% include-markdown "it/dbzero/script/manual/fn_log.md" %}
# ⚙️ Funzione `fn_log`

> ⚠️ **2 firme** con lo stesso nome: ognuna ha il suo blocco qui sotto, in ordine di argomenti.

## Firma `(p_area text, p_function_name text, p_error_code text, p_context jsonb)`

```sql
CREATE FUNCTION fn_log(p_area text, p_function_name text, p_error_code text, p_context jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_log(p_area text, p_function_name text, p_error_code text, p_context jsonb)
 RETURNS void
 LANGUAGE sql
AS $function$
   -- 1) Forma base: 4 argomenti
  SELECT script.fn_log_error_only($1,$2,$3,$4,NULL::uuid,VARIADIC ARRAY[]::text[] )
$function$

COMMENT ON FUNCTION script.fn_log(p_area text, p_function_name text, p_error_code text, p_context jsonb)
IS 'Façade esplicito: area, funzione, codice, contesto. Delega a fn_log_error_only (tx_id = NULL).';
```

</div>

## Firma `(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid)`

```sql
CREATE FUNCTION fn_log(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_log(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid)
 RETURNS void
 LANGUAGE sql
AS $function$
-- Con tx_id: 5 argomenti , 6 nulla
  SELECT script.fn_log_error_only($1,$2,$3,$4,$5,VARIADIC ARRAY[]::text[])
$function$

COMMENT ON FUNCTION script.fn_log(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid)
IS 'Façade con tx_id esplicito. Delega a fn_log_error_only.';
```

</div>

---
{% include-markdown "signature-core.md" %}
