{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_offerta.md" %}
# 🔍 View `vw_stato_sorgente_offerta`

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_offerta AS
SELECT s.id AS sorgente_tipo_id,
    (oc.uid)::text AS sorgente_uid,
    sdo.codice_interno AS stato_codice_interno,
    sdo.codice AS stato_codice,
    sdo.descrizione AS stato_descrizione,
    sdo.fase,
    sdo.esito,
    sdo.terminale
   FROM ((vendite.offerte_commerciali oc
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_offerte sdo ON ((sdo.id = oc.stato_doc_offerta_id)));
```


---
{% include-markdown "signature-core.md" %}
