{% include-markdown "it/dbzero/script/manual/fn_mese_di.md" %}
# ⚙️ Funzione `fn_mese_di`

```sql
CREATE FUNCTION fn_mese_di(p_giorno date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_mese_di(p_giorno date)
 RETURNS date
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE STRICT
AS $function$
    -- Il primo giorno del mese di p_giorno: p_giorno meno i
    -- giorni gia' passati del suo mese. date - integer e'
    -- date: nessun istante, nessun fuso.
    SELECT p_giorno - (EXTRACT(day FROM p_giorno)::integer - 1)
$function$

COMMENT ON FUNCTION script.fn_mese_di(p_giorno date)
IS 'Il primo giorno del mese di p_giorno: il mese di competenza di un giorno. Solo aritmetica di date, quindi IMMUTABLE e indipendente dal fuso della sessione: si usa anche in un CHECK o in un indice. ⭐ Si usa al posto di date_trunc(''month'', <date>)::date, che passa da un timestamptz nel fuso della sessione. Lavora su un GIORNO: un istante (timestamptz) passa prima da script.fn_giorno_operativo, che da'' il giorno nel fuso dell''azienda. NULL -> NULL. L''ultimo giorno del mese e'' script.fn_fine_mese_di.';
```

</div>

---
{% include-markdown "signature-core.md" %}
