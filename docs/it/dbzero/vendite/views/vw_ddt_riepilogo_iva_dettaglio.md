{% include-markdown "it/dbzero/vendite/manual/vw_ddt_riepilogo_iva_dettaglio.md" %}
# 🔍 View `vw_ddt_riepilogo_iva_dettaglio`

> 📝 **Descrizione**
>
> Riepilogo IVA per DDT vendita derivato dalle righe DDT attive e valorizzate. Aggrega per ddt_id, iva_id e aliquota effettiva; arrotonda l'imponibile dopo la SUM e calcola l'imposta sull'imponibile aggregato arrotondato. Natura resta NULL. Esigibilita e split_payment (rev 2026-10-01, D-6 di brief-db-esigibilita-iva-per-cassa-emittente) escono per codice IVA da script.fn_esigibilita_iva_documento con emittente e cliente del documento: la stessa regola delle righe di fattura, calcolata al momento (il documento non e' fiscale e non ha snapshot). Clone di vw_ordini_riepilogo_iva_dettaglio.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_ddt_riepilogo_iva_dettaglio
WITH (security_invoker=on) AS
WITH imponibili AS (
         SELECT b.ddt_id,
            b.iva_id,
            b.aliquota_effettiva,
            sum(b.imponibile_riga_full) AS imponibile_full
           FROM vendite.vw_ddt_righe_iva_base b
          GROUP BY b.ddt_id, b.iva_id, b.aliquota_effettiva
        ), aggregati AS (
         SELECT i.ddt_id,
            i.iva_id,
            i.aliquota_effettiva,
            round(i.imponibile_full, 2) AS imponibile,
            (i.imponibile_full - round(i.imponibile_full, 2)) AS arrotondamento
           FROM imponibili i
        ), riepilogo AS (
         SELECT a.ddt_id,
            a.iva_id,
            a.aliquota_effettiva,
            a.imponibile,
            round(((a.imponibile * COALESCE(a.aliquota_effettiva, (0)::numeric)) / (100)::numeric), 2) AS imposta,
            a.arrotondamento
           FROM aggregati a
        )
 SELECT r.ddt_id,
    r.iva_id,
    iva.codice AS iva_codice,
    iva.descrizione AS iva_descrizione,
    r.aliquota_effettiva AS iva_aliquota,
    NULL::integer AS natura_id,
    NULL::text AS natura_codice,
    (e.esigibilita)::character(1) AS esigibilita,
    e.split_payment,
    r.imponibile,
    r.imposta,
    r.arrotondamento,
    (r.imponibile + r.imposta) AS totale_riga
   FROM (((riepilogo r
     JOIN vendite.ddt d ON ((d.id = r.ddt_id)))
     LEFT JOIN config.iva iva ON ((iva.id = r.iva_id)))
     LEFT JOIN LATERAL script.fn_esigibilita_iva_documento(d.emittente_fiscale_id, d.billing_account_id, r.iva_id) e(esigibilita, split_payment) ON (true));
```

</div>


---
{% include-markdown "signature-core.md" %}
