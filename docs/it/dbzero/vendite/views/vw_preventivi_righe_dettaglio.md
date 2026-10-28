{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_righe_dettaglio.md" %}
# 🔍 View `vw_preventivi_righe_dettaglio`

> 📝 **Descrizione**
>
> Righe del preventivo con articolo, UoM, IVA (codice + descrizione + aliquota): la SORGENTE delle righe per la lista configurabile vendite.preventivo_righe e per il repository (brief-db-liste-righe-documento, D-8.6, 2026-09-28). Tutte le righe, anche le non attive: il filtro lo mette chi legge. Nessun ORDER BY: l'ordine lo chiede chi legge. importo_riga = round(…, 2) per mostrare, imponibile_riga_full a precisione piena per chi aggrega, entrambi da script.fn_imponibile_riga. NESSUN campo IVA per riga: l'IVA aggregata e' in vendite.preventivi_riepiloghi_iva. Dal 2026-09-28 anche data_consegna_richiesta_cliente, stato_approvazione_prezzo, pratica_approvazione_prezzo_id, is_composito_caso_a (prima solo nel repository). security_invoker: preventivi_righe e' in RLS.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_righe_dettaglio
WITH (security_invoker=true) AS
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
    iva.descrizione AS iva_descrizione,
    iva.aliquota_iva AS iva_aliquota,
    round(script.fn_imponibile_riga(pr.quantita, pr.prezzo_unitario, pr.sconto_percentuale), 2) AS importo_riga,
    script.fn_imponibile_riga(pr.quantita, pr.prezzo_unitario, pr.sconto_percentuale) AS imponibile_riga_full,
    pr.meta,
    pr.data_insert,
    pr.data_update,
    pr.data_consegna_richiesta_cliente,
    pr.stato_approvazione_prezzo,
    pr.pratica_approvazione_prezzo_id,
    (EXISTS ( SELECT 1
           FROM vendite.preventivi_righe_componenti prc
          WHERE ((prc.riga_preventivo_id = pr.id) AND (prc.attivo IS TRUE)))) AS is_composito_caso_a
   FROM (((vendite.preventivi_righe pr
     LEFT JOIN catalogo.articoli a ON ((a.id = pr.articolo_id)))
     LEFT JOIN catalogo.unita_misura um ON ((um.id = pr.uom_operativa_id)))
     LEFT JOIN config.iva iva ON ((iva.id = pr.iva_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
