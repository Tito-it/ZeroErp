{% include-markdown "it/dbzero/ui/manual/fn_intero_da_jsonb.md" %}
# ⚙️ Funzione `fn_intero_da_jsonb`

```sql
CREATE FUNCTION fn_intero_da_jsonb(p_valore jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_intero_da_jsonb(p_valore jsonb)
 RETURNS integer
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- CASE e non AND: l'ordine di valutazione e' garantito, e il cast
    -- avviene solo su un testo di sole cifre.
    SELECT CASE
        WHEN jsonb_typeof(p_valore) = 'number'
         AND (p_valore #>> '{}') ~ '^[0-9]{1,9}$'
        THEN (p_valore #>> '{}')::integer
    END;
$function$

COMMENT ON FUNCTION ui.fn_intero_da_jsonb(p_valore jsonb)
IS 'Il numero intero non negativo scritto in un valore jsonb, o NULL: un jsonb di tipo number che, nella forma in cui jsonb lo conserva, ha sole cifre, al più nove. Conta la forma conservata, non la grafia: jsonb normalizza il numero e tiene i decimali scritti, quindi 1e2 vale 100, mentre 100.0 e 2.50e1 (conservati come 100.0 e 25.0) danno NULL. Una stringa (anche "25"), un number negativo o con decimali, il null jsonb e NULL danno NULL; la funzione non solleva mai. È la sede unica della domanda «questo valore è un intero?» per le configurazioni di ui: la leggono il guard di forma delle preferenze (ui.fn_check_forma_configurazione), ui.fn_guard_misura_pagina e i due resolver (ui.fn_resolve_lista_config, ui.fn_resolve_dashboard_config). Chi la usa decide il dominio (positivo, una misura del catalogo, il tetto della dashboard). IMMUTABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
