# 🔍 View `vw_preventivi_riepilogo_iva_dettaglio`

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_riepilogo_iva_dettaglio AS
SELECT ri.id,
    ri.preventivo_id,
    ri.iva_id,
    iva.codice AS iva_codice,
    iva.descrizione AS iva_descrizione,
    iva.aliquota_iva AS iva_aliquota,
    ri.natura_id,
    n.codice AS natura_codice,
    ri.esigibilita,
    ri.split_payment,
    ri.imponibile,
    ri.imposta,
    ri.arrotondamento,
    (ri.imponibile + ri.imposta) AS totale_riga,
    ri.data_insert,
    ri.data_update
   FROM ((vendite.preventivi_riepiloghi_iva ri
     LEFT JOIN config.iva iva ON ((iva.id = ri.iva_id)))
     LEFT JOIN config.iva_natura n ON ((n.id = ri.natura_id)))
  ORDER BY ri.preventivo_id, iva.aliquota_iva, ri.id;
```


---
{% include-markdown "signature-core.md" %}
