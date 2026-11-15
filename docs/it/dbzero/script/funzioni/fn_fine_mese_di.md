{% include-markdown "it/dbzero/script/manual/fn_fine_mese_di.md" %}
# ⚙️ Funzione `fn_fine_mese_di`

```sql
CREATE FUNCTION fn_fine_mese_di(p_giorno date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_fine_mese_di(p_giorno date)
 RETURNS date
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE STRICT
AS $function$
    -- Il giorno prima del primo del mese successivo. Dal primo
    -- del mese, + 31 cade sempre nel mese seguente (nessun mese
    -- ha piu' di 31 giorni, nessuno meno di 28).
    SELECT script.fn_mese_di(script.fn_mese_di(p_giorno) + 31) - 1
$function$

COMMENT ON FUNCTION script.fn_fine_mese_di(p_giorno date)
IS 'L''ultimo giorno del mese di p_giorno (28, 29, 30 o 31). Solo aritmetica di date, quindi IMMUTABLE e indipendente dal fuso della sessione. ⭐ Si usa al posto di (date_trunc(''month'', x) + interval ''1 month - 1 day'')::date. Lavora su un GIORNO: un istante (timestamptz) passa prima da script.fn_giorno_operativo. NULL -> NULL. Il primo giorno del mese e'' script.fn_mese_di.';
```

</div>

---
{% include-markdown "signature-core.md" %}
