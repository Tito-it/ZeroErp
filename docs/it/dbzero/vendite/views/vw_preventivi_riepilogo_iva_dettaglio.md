{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_riepilogo_iva_dettaglio.md" %}
# 🔍 View `vw_preventivi_riepilogo_iva_dettaglio`

> 📝 **Descrizione**
>
> Riepilogo IVA per preventivo arricchito con codice/descrizione/aliquota IVA e codice natura. Per UI riepilogo IVA del preventivo (simmetrico a quello fatture).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_riepilogo_iva_dettaglio
WITH (security_invoker=true) AS
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

</div>


---
{% include-markdown "signature-core.md" %}
