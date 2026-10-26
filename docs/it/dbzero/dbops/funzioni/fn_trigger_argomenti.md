{% include-markdown "it/dbzero/dbops/manual/fn_trigger_argomenti.md" %}
# ⚙️ Funzione `fn_trigger_argomenti`

```sql
CREATE FUNCTION fn_trigger_argomenti(p_tgargs bytea)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_argomenti(p_tgargs bytea)
 RETURNS text[]
 LANGUAGE sql
 STABLE PARALLEL SAFE
AS $function$
  -- Scopo: gli argomenti di un trigger (pg_trigger.tgargs) come text[],
  --   nell'ordine del CREATE TRIGGER. Vuoto se il trigger non ne ha.
  -- Ogni argomento e' chiuso da un byte NUL: il pezzo n va dal NUL n-1
  -- (escluso) al NUL n (escluso).
  WITH nul AS (
      SELECT i AS fine,
             lag(i, 1, -1) OVER (ORDER BY i) AS inizio,
             row_number()  OVER (ORDER BY i) AS n
        FROM generate_series(0, COALESCE(length(p_tgargs), 0) - 1) AS g(i)
       WHERE get_byte(p_tgargs, i) = 0
  )
  SELECT COALESCE(
           array_agg(convert_from(substring(p_tgargs FROM inizio + 2 FOR fine - inizio - 1),
                                  current_setting('server_encoding'))
                     ORDER BY n),
           ARRAY[]::text[])
    FROM nul;
$function$

COMMENT ON FUNCTION dbops.fn_trigger_argomenti(p_tgargs bytea)
IS 'Gli argomenti di un trigger (pg_trigger.tgargs) come text[], nell''ordine del CREATE TRIGGER; vuoto se non ne ha. Taglia sui byte NUL e riconverte con la codifica del server: la forma encode(tgargs,''escape'') + rtrim(…,''\000'') tronca un argomento finale che termina con zero (rtrim toglie l''insieme {\,0}) e storpia i caratteri non ASCII. Building block per chi riconosce un trigger generico dai suoi argomenti. Brief: brief-db-lock-di-colonna-fuori-registro §7.';
```

</div>

---
{% include-markdown "signature-core.md" %}
