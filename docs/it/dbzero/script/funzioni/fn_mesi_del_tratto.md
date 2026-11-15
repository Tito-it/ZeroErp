{% include-markdown "it/dbzero/script/manual/fn_mesi_del_tratto.md" %}
# ⚙️ Funzione `fn_mesi_del_tratto`

```sql
CREATE FUNCTION fn_mesi_del_tratto(p_dal date, p_al date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_mesi_del_tratto(p_dal date, p_al date)
 RETURNS TABLE(mese date, fine_mese date)
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- k = 0 e' il mese di p_dal; l'ultimo k e' il mese di p_al.
    -- Con p_al in un mese prima, o un estremo NULL, la serie e'
    -- vuota.
    SELECT s.primo, script.fn_fine_mese_di(s.primo)
      FROM (SELECT k, script.fn_mesi_dopo(script.fn_mese_di(p_dal), k) AS primo
              FROM generate_series(
                       0,
                       (extract(year FROM p_al)::integer * 12
                        + extract(month FROM p_al)::integer)
                       - (extract(year FROM p_dal)::integer * 12
                          + extract(month FROM p_dal)::integer)) AS k) s
     ORDER BY s.k
$function$

COMMENT ON FUNCTION script.fn_mesi_del_tratto(p_dal date, p_al date)
IS 'I mesi di calendario che il tratto da p_dal a p_al tocca: una riga per mese, in ordine, col primo giorno (mese) e l''ultimo (fine_mese). p_al in un mese prima di quello di p_dal: nessuna riga; un estremo NULL: nessuna riga. Gli estremi del tratto non tagliano il mese: chi vuole i giorni coperti li taglia con greatest/least. Solo aritmetica di interi e date, quindi IMMUTABLE e indipendente dal fuso della sessione. Il planner la espande nel punto d''uso; per questo non e'' STRICT, e il NULL lo da'' la serie vuota. ⭐ Si usa al posto di generate_series(<date>, <date>, interval ''1 month''), che passa da timestamptz. Lavora su GIORNI: un istante passa prima da script.fn_giorno_operativo. Il mese di un giorno e'' script.fn_mese_di, n mesi dopo script.fn_mesi_dopo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
