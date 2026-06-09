# 🔍 View `vw_preventivi_righe_smistabili_ordine`

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_righe_smistabili_ordine AS
SELECT pr.preventivo_id,
    pr.id,
    pr.natura_vendita_id,
    pr.articolo_id,
    pr.descrizione,
    pr.prezzo_unitario,
    pr.sconto_percentuale,
    pr.iva_id,
    pr.qta_operativa,
    pr.uom_operativa_id,
    pr.factor_to_base,
    pr.ordine
   FROM (vendite.preventivi_righe pr
     JOIN config.nature_vendita nv ON ((nv.id = pr.natura_vendita_id)))
  WHERE ((COALESCE(pr.attivo, true) IS TRUE) AND ((nv.destinazione_tipo)::text = 'ORDINE'::text) AND (NOT (EXISTS ( SELECT 1
           FROM vendite.ordini_righe orr
          WHERE (orr.preventivo_riga_id = pr.id)))));
```


---
{% include-markdown "signature-core.md" %}
