{% include-markdown "it/dbzero/vendite/manual/vw_ddt_righe_dettaglio.md" %}
# 🔍 View `vw_ddt_righe_dettaglio`

> 📝 **Descrizione**
>
> Righe del DDT con articolo, UoM e IVA: la SORGENTE delle righe per la lista configurabile vendite.ddt_righe e per il repository (brief-db-liste-righe-documento, D-8.6, 2026-09-28; prima esistevano solo come due query Python con proiezioni diverse). Tutte le righe, anche le non attive: il filtro lo mette chi legge. Nessun ORDER BY. importo_riga = round(…, 2) per mostrare, imponibile_riga_full pieno per chi aggrega, entrambi da script.fn_imponibile_riga: NULL sulla riga senza prezzo (DDT di solo trasporto), mai uno zero finto (V-2/DEC-6). security_invoker: ddt_righe e' in RLS.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_ddt_righe_dettaglio
WITH (security_invoker=true) AS
SELECT r.id,
    r.ddt_id,
    r.riga_nr,
    r.attivo,
    r.articolo_id,
    a.codice AS articolo_codice,
    a.descrizione AS articolo_descrizione,
    r.descrizione,
    r.quantita,
    r.qta_operativa,
    r.factor_to_base,
    r.uom_operativa_id,
    um.codice AS uom_codice,
    r.prezzo_unitario,
    r.sconto_percentuale,
    r.iva_id,
    iva.codice AS iva_codice,
    iva.descrizione AS iva_descrizione,
    iva.aliquota_iva AS iva_aliquota,
    round(script.fn_imponibile_riga(r.quantita, r.prezzo_unitario, r.sconto_percentuale), 2) AS importo_riga,
    script.fn_imponibile_riga(r.quantita, r.prezzo_unitario, r.sconto_percentuale) AS imponibile_riga_full,
    r.meta,
    r.data_insert,
    r.data_update,
    (EXISTS ( SELECT 1
           FROM vendite.ddt_righe_componenti rc
          WHERE ((rc.riga_ddt_id = r.id) AND (rc.attivo IS TRUE)))) AS is_composito_caso_a,
    vendite.fn_ddt_riga_evasa(r.id) AS evasa,
    ((script.fn_check_ddt_riga_correggi_qta_evasa(r.id) -> 0) ->> 'reason'::text) AS correggi_qta_evasa_blocco
   FROM (((vendite.ddt_righe r
     LEFT JOIN catalogo.articoli a ON ((a.id = r.articolo_id)))
     LEFT JOIN catalogo.unita_misura um ON ((um.id = r.uom_operativa_id)))
     LEFT JOIN config.iva iva ON ((iva.id = r.iva_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
