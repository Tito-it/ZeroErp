{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_righe_smistabili_commessa.md" %}
# 🔍 View `vw_preventivi_righe_smistabili_commessa`

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_righe_smistabili_commessa AS
SELECT pr.preventivo_id,
    pr.id,
    p.uid AS preventivo_uid,
    pr.natura_vendita_id,
    pr.articolo_id,
    pr.descrizione,
    pr.prezzo_unitario,
    pr.sconto_percentuale,
    pr.iva_id,
    pr.quantita,
    pr.qta_operativa,
    pr.uom_operativa_id,
    pr.factor_to_base,
    pr.ordine
   FROM ((vendite.preventivi_righe pr
     JOIN vendite.preventivi p ON ((p.id = pr.preventivo_id)))
     LEFT JOIN config.nature_vendita nv ON ((nv.id = pr.natura_vendita_id)))
  WHERE ((pr.attivo IS TRUE) AND (pr.quantita > (0)::numeric) AND (pr.prezzo_unitario >= (0)::numeric) AND ((pr.natura_vendita_id IS NULL) OR ((nv.destinazione_tipo)::text = 'COMMESSA'::text)) AND (NOT (EXISTS ( SELECT 1
           FROM vendite.commesse_attivita ca
          WHERE (((ca.segment_key)::text = ((('PREV:'::text || (p.uid)::text) || ':R:'::text) || (pr.id)::text)) OR ((ca.segment_key)::text ~~ (((('PREV:'::text || (p.uid)::text) || ':R:'::text) || (pr.id)::text) || '#CMP:%'::text)))))));
```


---
{% include-markdown "signature-core.md" %}
