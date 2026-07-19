{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_ddt.md" %}
# 🔍 View `vw_stato_sorgente_ddt`

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_ddt AS
SELECT s.id AS sorgente_tipo_id,
    (d.id)::text AS sorgente_uid,
    sdd.codice_interno AS stato_codice_interno,
    sdd.codice AS stato_codice,
    sdd.descrizione AS stato_descrizione,
    sdd.fase,
    (
        CASE
            WHEN sdd.is_abortito THEN 'NEGATIVO'::text
            WHEN ((sdd.fase)::text = 'CHIUSO'::text) THEN 'POSITIVO'::text
            ELSE NULL::text
        END)::character varying AS esito,
    ((sdd.fase)::text = 'CHIUSO'::text) AS terminale
   FROM ((vendite.ddt d
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'DDT_VENDITA'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_ddt sdd ON ((sdd.id = d.stato_doc_ddt_id)));
```


---
{% include-markdown "signature-core.md" %}
