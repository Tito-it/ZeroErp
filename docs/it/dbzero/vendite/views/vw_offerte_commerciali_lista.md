{% include-markdown "it/dbzero/vendite/manual/vw_offerte_commerciali_lista.md" %}
# 🔍 View `vw_offerte_commerciali_lista`

```sql
CREATE OR REPLACE VIEW vendite.vw_offerte_commerciali_lista AS
SELECT o.id,
    o.uid,
    o.codice,
    o.revisione_numero,
    o.revisione_padre_id,
    ((sdo.codice_interno)::text <> ALL ((ARRAY['SUPERATA'::character varying, 'ANNULLATA'::character varying])::text[])) AS is_attiva,
    (EXISTS ( SELECT 1
           FROM vendite.offerte_commerciali figlio
          WHERE (figlio.revisione_padre_id = o.id))) AS has_next_revisione,
    o.stato_doc_offerta_id,
    sdo.codice_interno AS stato_codice_interno,
    sdo.descrizione AS stato_descrizione,
    o.billing_account_id,
    ba.codice AS ba_codice,
    s.id AS soggetto_id,
    s.ragione_sociale_completa,
    s.id_fiscale_univoco_cf_piva,
    o.emittente_fiscale_id,
    ef.codice AS emittente_fiscale_codice,
    o.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    o.istanza_utility_id,
    iu.codice AS istanza_utility_codice,
    o.listino_id,
    l.codice AS listino_codice,
    o.listino_versione_id,
    lv.codice_versione AS listino_versione_codice,
    o.tipo_variazione_globale,
    o.valore_variazione_globale,
    o.valuta_id,
    v_val.codice AS valuta_codice,
    o.validita_dal,
    o.validita_al,
    ((o.validita_al IS NOT NULL) AND (o.validita_al < CURRENT_DATE)) AS is_scaduta,
    o.data_emissione,
    o.data_accettazione,
    o.data_rifiuto,
    o.data_annullamento,
    o.data_insert,
    o.user_insert
   FROM (((((((((vendite.offerte_commerciali o
     JOIN config.stati_doc_offerte sdo ON ((sdo.id = o.stato_doc_offerta_id)))
     LEFT JOIN anagrafiche.istanze_utilities iu ON ((iu.id = o.istanza_utility_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = iu.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = o.billing_account_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = o.emittente_fiscale_id)))
     LEFT JOIN config.utilities u ON ((u.id = o.utility_id)))
     LEFT JOIN vendite.listini l ON ((l.id = o.listino_id)))
     LEFT JOIN vendite.listini_versioni lv ON ((lv.id = o.listino_versione_id)))
     LEFT JOIN config.valute v_val ON ((v_val.id = o.valuta_id)));
```


---
{% include-markdown "signature-core.md" %}
