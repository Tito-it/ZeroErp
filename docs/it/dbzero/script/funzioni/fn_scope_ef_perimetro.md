{% include-markdown "it/dbzero/script/manual/fn_scope_ef_perimetro.md" %}
# ⚙️ Funzione `fn_scope_ef_perimetro`

```sql
CREATE FUNCTION fn_scope_ef_perimetro(p_perimetro bigint[], p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_perimetro(p_perimetro bigint[], p_emittente_fiscale_id bigint)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Scopo: l'emittente della riga sta nel perimetro dell'operatore?
    --   La funzione di scope delle policy ef_whitelist (linee-guida-sql
    --   §10.3). Il perimetro NON lo calcola lei: glielo passa la policy in
    --   UNA sottoquery scalare non correlata su
    --   script.fn_get_emittenti_scope_pk_ids, che PostgreSQL valuta una
    --   volta per istruzione (InitPlan):
    --     script.fn_scope_ef_perimetro(
    --         (SELECT script.fn_get_emittenti_scope_pk_ids(<utente>)),
    --         <emittente della riga>)
    -- ⭐ Rev 2026-10-18 (D-3b-2c): era a tre argomenti (perimetro «tutti»
    --    a parte, due sottoquery) per farsi incorporare dal pianificatore.
    --    Ma due sottoquery calcolano il perimetro DUE volte per istruzione,
    --    e le letture di una riga sola (la maggior parte, nei verbi e nei
    --    trigger) pagavano il doppio. Qui il perimetro serve due volte,
    --    quindi la funzione non si incorpora: resta una chiamata per riga
    --    da ~1,5 µs, contro 0,02-0,08 ms della canonica per riga di prima.
    -- Emittente NULL -> false (COALESCE), salvo perimetro «tutti».
    SELECT p_perimetro IS NULL
        OR coalesce(p_emittente_fiscale_id = ANY (p_perimetro), false)
$function$

COMMENT ON FUNCTION script.fn_scope_ef_perimetro(p_perimetro bigint[], p_emittente_fiscale_id bigint)
IS 'Funzione di scope delle policy ef_whitelist (linee-guida-sql §10.3): l''emittente della riga sta nel perimetro dell''operatore? Il perimetro (script.fn_get_emittenti_scope_pk_ids: NULL = tutti, ''{}'' = nessuno) lo passa la policy in UNA sottoquery scalare non correlata, valutata una volta per istruzione (InitPlan); per riga resta questa chiamata pura (~1,5 µs). Emittente NULL -> false salvo perimetro tutti. Rev 2026-10-18 (20261018-24, D-3b-2c): sostituisce la firma a tre argomenti, che calcolava il perimetro due volte per istruzione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
