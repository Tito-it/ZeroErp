{% include-markdown "it/dbzero/catalogo/manual/fn_uom_primo_giorno_non_convertibile.md" %}
# ⚙️ Funzione `fn_uom_primo_giorno_non_convertibile`

```sql
CREATE FUNCTION fn_uom_primo_giorno_non_convertibile(p_articolo_id uuid, p_uom_id bigint, p_periodo daterange)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_uom_primo_giorno_non_convertibile(p_articolo_id uuid, p_uom_id bigint, p_periodo daterange)
 RETURNS date
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT
         CASE
             WHEN ((s.scoperti IS NULL) OR isempty(s.scoperti)) THEN NULL::date
             WHEN lower_inf(s.scoperti) THEN '-infinity'::date
             ELSE lower(s.scoperti)
         END AS lower
    FROM ( SELECT (datemultirange(fn_uom_primo_giorno_non_convertibile.p_periodo) - COALESCE(( SELECT range_agg(f.validita) AS range_agg
                    FROM catalogo.fn_uom_fonti_conversione(fn_uom_primo_giorno_non_convertibile.p_articolo_id, fn_uom_primo_giorno_non_convertibile.p_uom_id) f(priorita, fonte_id, fattore, validita)), '{}'::datemultirange)) AS scoperti) s;
END

COMMENT ON FUNCTION catalogo.fn_uom_primo_giorno_non_convertibile(p_articolo_id uuid, p_uom_id bigint, p_periodo daterange)
IS 'Il primo giorno del periodo p_periodo in cui l''unita'' p_uom_id NON si converte nell''unita'' base dell''articolo p_articolo_id; NULL se si converte in ogni giorno del periodo (o se il periodo e'' NULL o vuoto). Si converte un giorno coperto da almeno una fonte di catalogo.fn_uom_fonti_conversione (la base, una mappatura, una conversione generale): i giorni scoperti sono il periodo meno l''unione dei periodi delle fonti. Un buco senza inizio esce ''-infinity''. E'' la regola «l''unita'' vale per tutto il periodo» delle righe di listino: la leggono vendite.trgfn_listini_righe_guard_uom_periodo, vendite.fn_listino_versione_riga_uom_non_convertibile e vendite.fn_listini_attivi_uom_non_convertibili. SECURITY INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
