{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_ordine.md" %}
# 🔍 View `vw_stato_sorgente_ordine`

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_ordine AS
SELECT s.id AS sorgente_tipo_id,
    (o.id)::text AS sorgente_uid,
    sdor.codice_interno AS stato_codice_interno,
    sdor.codice AS stato_codice,
    sdor.descrizione AS stato_descrizione,
    sdor.fase,
    sdor.esito,
    sdor.terminale
   FROM ((vendite.ordini o
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_ordini sdor ON ((sdor.id = o.stato_doc_ordine_id)));
```


---
{% include-markdown "signature-core.md" %}
