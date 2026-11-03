{% include-markdown "it/dbzero/vendite/manual/vw_ordini_righe_dettaglio.md" %}
# 🔍 View `vw_ordini_righe_dettaglio`

> 📝 **Descrizione**
>
> Righe dell'ordine con articolo, UoM, IVA, evaso e residuo: la SORGENTE delle righe per la lista configurabile vendite.ordine_righe e per il repository (brief-db-liste-righe-documento, D-8.6, 2026-09-28; prima esistevano solo come due query Python con proiezioni diverse). Tutte le righe, anche le non attive: il filtro lo mette chi legge. Nessun ORDER BY. importo_riga = round(…, 2) per mostrare, imponibile_riga_full pieno per chi aggrega, entrambi da script.fn_imponibile_riga. qta_evasa_operativa / qta_residua_operativa: somma dei fulfillment (UoM base) divisa per factor_to_base, residuo mai negativo, 6 decimali, NULL se il fattore e' zero. security_invoker: ordini_righe e i fulfillment sono in RLS. rev 2026-11-03 (20261103-25, brief-db-addebito-trasporto-ordine §7.3, §8.1): + e_onere e causale_onere_id in coda; sulla riga-onere qta_evasa_operativa e qta_residua_operativa sono NULL (l'onere non si evade).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_ordini_righe_dettaglio
WITH (security_invoker=true) AS
SELECT r.id,
    r.ordine_id,
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
        CASE
            WHEN (NOT k.e_onere) THEN round((COALESCE(ful.qta_evasa_base, (0)::numeric) / NULLIF(r.factor_to_base, (0)::numeric)), 6)
            ELSE NULL::numeric
        END AS qta_evasa_operativa,
        CASE
            WHEN (NOT k.e_onere) THEN round((GREATEST((r.quantita - COALESCE(ful.qta_evasa_base, (0)::numeric)), (0)::numeric) / NULLIF(r.factor_to_base, (0)::numeric)), 6)
            ELSE NULL::numeric
        END AS qta_residua_operativa,
    r.meta,
    r.data_insert,
    r.data_update,
    r.data_consegna_richiesta_cliente,
    r.data_consegna_confermata,
    (EXISTS ( SELECT 1
           FROM vendite.ordini_righe_componenti rc
          WHERE ((rc.riga_ordine_id = r.id) AND (rc.attivo IS TRUE)))) AS is_composito_caso_a,
    ((script.fn_check_ordine_riga_data_consegna_confermata(r.id) -> 0) ->> 'reason'::text) AS data_consegna_confermata_blocco,
    k.e_onere,
    a.causale_onere_id
   FROM (((((vendite.ordini_righe r
     LEFT JOIN catalogo.articoli a ON ((a.id = r.articolo_id)))
     LEFT JOIN catalogo.unita_misura um ON ((um.id = r.uom_operativa_id)))
     LEFT JOIN config.iva iva ON ((iva.id = r.iva_id)))
     LEFT JOIN LATERAL ( SELECT sum(f.qta_evasa) AS qta_evasa_base
           FROM vendite.ordini_righe_fulfillment f
          WHERE (f.ordine_riga_id = r.id)) ful ON (true))
     CROSS JOIN LATERAL ( SELECT (NOT script.fn_natura_e_merce(r.natura_vendita_id)) AS e_onere) k);
```

</div>


---
{% include-markdown "signature-core.md" %}
