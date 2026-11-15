{% include-markdown "it/dbzero/script/manual/fn_mesi_dopo.md" %}
# ⚙️ Funzione `fn_mesi_dopo`

```sql
CREATE FUNCTION fn_mesi_dopo(p_giorno date, p_mesi integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_mesi_dopo(p_giorno date, p_mesi integer)
 RETURNS date
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- Il primo del mese d'arrivo (dal numero progressivo del
    -- mese, anno * 12 + mese - 1, piu' p_mesi) piu' il giorno di
    -- partenza, tagliato sulla fine di quel mese: il 31 su un
    -- mese di 30 giorni e' il 30.
    SELECT least(
               make_date((extract(year FROM p_giorno)::integer * 12
                          + extract(month FROM p_giorno)::integer - 1 + p_mesi) / 12,
                         (extract(year FROM p_giorno)::integer * 12
                          + extract(month FROM p_giorno)::integer - 1 + p_mesi) % 12 + 1,
                         1)
               + (extract(day FROM p_giorno)::integer - 1),
               script.fn_fine_mese_di(
                   make_date((extract(year FROM p_giorno)::integer * 12
                              + extract(month FROM p_giorno)::integer - 1 + p_mesi) / 12,
                             (extract(year FROM p_giorno)::integer * 12
                              + extract(month FROM p_giorno)::integer - 1 + p_mesi) % 12 + 1,
                             1)))
$function$

COMMENT ON FUNCTION script.fn_mesi_dopo(p_giorno date, p_mesi integer)
IS 'Il giorno p_giorno spostato di p_mesi mesi di calendario (negativo = indietro). Se il giorno non esiste nel mese d''arrivo e'' l''ultimo del mese: il 31 gennaio piu'' un mese e'' il 28 (o 29) febbraio, come date + interval in PostgreSQL. Solo aritmetica di interi e date, quindi IMMUTABLE e indipendente dal fuso della sessione. ⭐ Si usa al posto di (x + make_interval(months => n))::date e di x + interval ''n month''. Un''espressione sola, che il planner espande nel punto d''uso; per questo non e'' STRICT (least() non lo e''), ma un argomento NULL da'' NULL lo stesso. Lavora su un GIORNO: un istante (timestamptz) passa prima da script.fn_giorno_operativo. I mesi toccati da un tratto di giorni sono script.fn_mesi_del_tratto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
