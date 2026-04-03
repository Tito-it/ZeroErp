{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_righe_dettaglio.md" %}
# 🔍 View `vw_preventivi_righe_dettaglio`

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_righe_dettaglio AS
SELECT pr.id,
    pr.preventivo_id,
    pr.ordine,
    pr.attivo,
    pr.articolo_id,
    a.codice AS articolo_codice,
    a.descrizione AS articolo_descrizione,
    pr.descrizione,
    pr.quantita,
    pr.qta_operativa,
    pr.factor_to_base,
    pr.uom_operativa_id,
    um.codice AS uom_codice,
    pr.prezzo_unitario,
    pr.sconto_percentuale,
    pr.iva_id,
    iva.codice AS iva_codice,
    iva.aliquota_iva AS iva_aliquota,
    round(((pr.quantita * pr.prezzo_unitario) * ((1)::numeric - (COALESCE(pr.sconto_percentuale, (0)::numeric) / (100)::numeric))), 2) AS importo_riga,
    round(((((pr.quantita * pr.prezzo_unitario) * ((1)::numeric - (COALESCE(pr.sconto_percentuale, (0)::numeric) / (100)::numeric))) * COALESCE(iva.aliquota_iva, (0)::numeric)) / (100)::numeric), 2) AS importo_iva_riga,
    pr.meta,
    pr.data_insert,
    pr.data_update
   FROM (((vendite.preventivi_righe pr
     LEFT JOIN catalogo.articoli a ON ((a.id = pr.articolo_id)))
     LEFT JOIN catalogo.unita_misura um ON ((um.id = pr.uom_operativa_id)))
     LEFT JOIN config.iva iva ON ((iva.id = pr.iva_id)))
  ORDER BY pr.preventivo_id, pr.ordine, pr.id;
```


---
{% include-markdown "signature-core.md" %}
