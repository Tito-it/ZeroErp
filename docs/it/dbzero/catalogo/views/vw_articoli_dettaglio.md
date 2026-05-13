{% include-markdown "it/dbzero/catalogo/manual/vw_articoli_dettaglio.md" %}
# 🔍 View `vw_articoli_dettaglio`

```sql
CREATE OR REPLACE VIEW catalogo.vw_articoli_dettaglio AS
SELECT a.id,
    a.codice,
    a.descrizione,
    a.descrizione_breve,
    a.uom_id,
    a.tipo_voce_id,
    a.gruppo_voce_id,
    a.spesa_id,
    a.iva_id,
    a.conto_contabile_vendita_id,
    a.conto_contabile_acquisto_id,
    a.is_composito,
    a.is_solo_componente,
    a.requires_serial,
    a.listino_tipologia_id,
    a.meta,
    a.user_insert,
    a.user_update,
    a.data_insert,
    a.data_update,
    a.tx_id,
    a.storicizza,
    a.attivo,
    a.note_target_tipo,
    a.note_id,
    u.id AS uom_ref_id,
    u.codice AS uom_codice,
    u.descrizione AS uom_descrizione,
    t.id AS tipologia_ref_id,
    t.codice AS tipologia_codice,
    t.descrizione AS tipologia_descrizione,
    g.id AS gruppo_ref_id,
    g.codice AS gruppo_codice,
    g.descrizione AS gruppo_descrizione,
    s.id AS spesa_ref_id,
    s.codice AS spesa_codice,
    s.descrizione AS spesa_descrizione,
    i.id AS iva_ref_id,
    i.codice AS iva_codice,
    i.descrizione AS iva_descrizione,
    i.aliquota_iva AS iva_aliquota_iva,
    lt.codice AS tipologia_listino_codice,
    lt.descrizione AS tipologia_listino_descrizione,
    (a.is_composito AND (NOT a.is_solo_componente)) AS puo_gestire_bom,
        CASE
            WHEN (a.is_composito AND (NOT a.is_solo_componente)) THEN NULL::text
            WHEN a.is_solo_componente THEN 'ARTICOLO_SOLO_COMPONENTE'::text
            ELSE 'ARTICOLO_NON_COMPOSITO'::text
        END AS motivo_non_gestibile_bom,
    (a.is_composito AND (EXISTS ( SELECT 1
           FROM catalogo.articoli_componenti ac
          WHERE ((ac.prodotto_id = a.id) AND (ac.validita @> CURRENT_DATE) AND (ac.attivo = true))))) AS has_componenti_alla_data
   FROM ((((((catalogo.articoli a
     LEFT JOIN catalogo.unita_misura u ON ((u.id = a.uom_id)))
     LEFT JOIN vendite.articoli_tipologie t ON ((t.id = a.tipo_voce_id)))
     LEFT JOIN vendite.articoli_gruppi g ON ((g.id = a.gruppo_voce_id)))
     LEFT JOIN vendite.articoli_spesa s ON ((s.id = a.spesa_id)))
     LEFT JOIN config.iva i ON ((i.id = a.iva_id)))
     LEFT JOIN config.listini_tipologie lt ON ((lt.id = a.listino_tipologia_id)));
```


---
{% include-markdown "signature-core.md" %}
