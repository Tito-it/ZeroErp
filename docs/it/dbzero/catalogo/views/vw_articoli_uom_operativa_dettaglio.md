{% include-markdown "it/dbzero/catalogo/manual/vw_articoli_uom_operativa_dettaglio.md" %}
# 🔍 View `vw_articoli_uom_operativa_dettaglio`

> 📝 **Descrizione**
>
> Le unita' operative di un articolo per la lista e il drawer: le righe di catalogo.articoli_uom_operativa con codice e descrizione dell'unita' e dell'articolo, e la capability di riga, che dice che cosa il database lascia fare oggi. La da' catalogo.fn_uom_conversione_capability, lo stesso giudizio di catalogo.trgfn_uom_guard_storia: puo_eliminarsi e puo_cambiare_attivo (spegnere o riaccendere) solo su una mappatura senza giorni passati (motivo_non_eliminabile UOM_STORIA_IN_VIGORE); puo_chiudersi se la fine e' vuota o non ancora passata (motivo_non_chiudibile UOM_STORIA_CHIUSA), con data_min_chiusura (la piu' tarda fra inizio e ieri) e data_default_chiusura (la piu' tarda fra inizio e oggi). Sulla riga dell'unita' base niente di tutto questo: non si cancella (UOM_BASE_NON_ELIMINABILE, catalogo.trgfn_articoli_uom_operativa_guard_base), e attivo e fine non si offrono (UOM_BASE), perche' la base vale 1 a ogni data. Le colonne che non si cambiano mai (unita', articolo, fattore, inizio) il form le legge da dbops.vw_non_editable_fields. Nessuna security_invoker: le tabelle lette non hanno RLS.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW catalogo.vw_articoli_uom_operativa_dettaglio AS
SELECT auo.id,
    auo.articolo_id,
    auo.uom_id,
    auo.is_base,
    auo.factor_to_base,
    auo.is_sell_uom,
    auo.is_purchase_uom,
    auo.is_logistic_uom,
    auo.qty_step,
    auo.max_decimals,
    auo.forbid_fraction,
    auo.gtin,
    auo.valido_dal,
    auo.valido_al,
    auo.validita,
    auo.attivo,
    auo.meta,
    auo.user_insert,
    auo.user_update,
    auo.data_insert,
    auo.data_update,
    auo.tx_id,
    auo.storicizza,
    u.codice AS uom_codice,
    u.descrizione AS uom_descrizione,
    a.codice AS articolo_codice,
    a.descrizione AS articolo_descrizione,
    ((NOT auo.is_base) AND cap.puo_eliminarsi) AS puo_eliminarsi,
        CASE
            WHEN auo.is_base THEN 'UOM_BASE_NON_ELIMINABILE'::text
            ELSE cap.motivo_non_eliminabile
        END AS motivo_non_eliminabile,
    ((NOT auo.is_base) AND cap.puo_cambiare_attivo) AS puo_cambiare_attivo,
    ((NOT auo.is_base) AND cap.puo_chiudersi) AS puo_chiudersi,
        CASE
            WHEN (NOT auo.is_base) THEN cap.data_min_chiusura
            ELSE NULL::date
        END AS data_min_chiusura,
        CASE
            WHEN (NOT auo.is_base) THEN cap.data_default_chiusura
            ELSE NULL::date
        END AS data_default_chiusura,
        CASE
            WHEN auo.is_base THEN 'UOM_BASE'::text
            ELSE cap.motivo_non_chiudibile
        END AS motivo_non_chiudibile
   FROM (((catalogo.articoli_uom_operativa auo
     LEFT JOIN catalogo.unita_misura u ON ((u.id = auo.uom_id)))
     LEFT JOIN catalogo.articoli a ON ((a.id = auo.articolo_id)))
     CROSS JOIN LATERAL catalogo.fn_uom_conversione_capability(auo.valido_dal, auo.valido_al) cap(puo_eliminarsi, puo_cambiare_attivo, puo_chiudersi, data_min_chiusura, data_default_chiusura, motivo_non_eliminabile, motivo_non_chiudibile));
```

</div>


---
{% include-markdown "signature-core.md" %}
