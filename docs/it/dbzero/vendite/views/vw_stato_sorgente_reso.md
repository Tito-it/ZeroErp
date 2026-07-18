# 🔍 View `vw_stato_sorgente_reso`

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_reso AS
SELECT s.id AS sorgente_tipo_id,
    (r.id)::text AS sorgente_uid,
    sdr.codice_interno AS stato_codice_interno,
    sdr.codice AS stato_codice,
    sdr.descrizione AS stato_descrizione,
    sdr.fase,
    (
        CASE
            WHEN sdr.is_abortito THEN 'NEGATIVO'::text
            WHEN ((sdr.fase)::text = 'CHIUSO'::text) THEN 'POSITIVO'::text
            ELSE NULL::text
        END)::character varying AS esito,
    ((sdr.fase)::text = 'CHIUSO'::text) AS terminale
   FROM ((vendite.resi r
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'RESO_VENDITA'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_reso sdr ON ((sdr.id = r.stato_doc_reso_id)));
```


---
{% include-markdown "signature-core.md" %}
