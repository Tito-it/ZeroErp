{% include-markdown "it/dbzero/catalogo/manual/vw_articoli_uom_operativa_dettaglio.md" %}
# 🔍 View `vw_articoli_uom_operativa_dettaglio`

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
    auo.rounding_mode,
    auo.max_decimals,
    auo.forbid_fraction,
    auo.require_lot,
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
    (NOT auo.is_base) AS puo_eliminarsi,
        CASE
            WHEN auo.is_base THEN 'UOM_BASE_NON_ELIMINABILE'::text
            ELSE NULL::text
        END AS motivo_non_eliminabile
   FROM ((catalogo.articoli_uom_operativa auo
     LEFT JOIN catalogo.unita_misura u ON ((u.id = auo.uom_id)))
     LEFT JOIN catalogo.articoli a ON ((a.id = auo.articolo_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
