{% include-markdown "it/dbzero/catalogo/manual/fn_uom_operativa_alla_data.md" %}
# ⚙️ Funzione `fn_uom_operativa_alla_data`

```sql
CREATE FUNCTION fn_uom_operativa_alla_data(p_articolo_id uuid, p_uom_id bigint, p_data date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_uom_operativa_alla_data(p_articolo_id uuid, p_uom_id bigint, p_data date)
 RETURNS TABLE(factor_to_base numeric, qty_step numeric, max_decimals integer, forbid_fraction boolean)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 SELECT o.factor_to_base,
     o.qty_step,
     o.max_decimals,
     o.forbid_fraction
    FROM (catalogo.fn_uom_fonti_conversione(fn_uom_operativa_alla_data.p_articolo_id, fn_uom_operativa_alla_data.p_uom_id) f(priorita, fonte_id, fattore, validita)
      JOIN catalogo.articoli_uom_operativa o ON ((o.id = f.fonte_id)))
   WHERE ((f.priorita = 1) AND (f.validita @> fn_uom_operativa_alla_data.p_data));
END

COMMENT ON FUNCTION catalogo.fn_uom_operativa_alla_data(p_articolo_id uuid, p_uom_id bigint, p_data date)
IS 'La mappatura dell''unita'' p_uom_id per l''articolo p_articolo_id alla data p_data: il fattore verso l''unita'' base e le regole della quantita'' (qty_step, max_decimals, forbid_fraction) della riga di catalogo.articoli_uom_operativa che e'' la fonte di priorita'' 1 di catalogo.fn_uom_fonti_conversione e la cui validita contiene p_data. Al piu'' una riga (uq_articoli_uom_operativa_no_overlap); nessuna se l''unita'' non e'' mappata a quella data, o se p_data e'' NULL. La riga base vale a ogni data. Quale mappatura vale lo dice fn_uom_fonti_conversione, sede unica del predicato; qui si leggono le regole della quantita'', che chiama script.trgfn_qta_from_operativa. SECURITY INVOKER: la tabella non ha RLS.';
```

</div>

---
{% include-markdown "signature-core.md" %}
