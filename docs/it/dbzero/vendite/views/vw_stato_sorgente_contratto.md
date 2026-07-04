{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_contratto.md" %}
# 🔍 View `vw_stato_sorgente_contratto`

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_contratto AS
SELECT s.id AS sorgente_tipo_id,
    (c.id)::text AS sorgente_uid,
    sdc.codice_interno AS stato_codice_interno,
    sdc.codice AS stato_codice,
    sdc.descrizione AS stato_descrizione,
    sdc.fase,
    sdc.esito,
    sdc.terminale
   FROM ((vendite.contratti c
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'CONTRATTO'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_contratti sdc ON ((sdc.id = c.stato_doc_contratto_id)));
```


---
{% include-markdown "signature-core.md" %}
