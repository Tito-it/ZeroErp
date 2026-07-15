{% include-markdown "it/dbzero/vendite/manual/vw_documento_lineage_nodi.md" %}
# 🔍 View `vw_documento_lineage_nodi`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_documento_lineage_nodi
WITH (security_invoker=on) AS
SELECT s.id AS tipo_id,
    (p.uid)::text AS uid,
    p.numero AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (1)::smallint AS pipeline_rank
   FROM ((vendite.preventivi p
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'PREVENTIVO'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_preventivi st ON ((st.id = p.stato_doc_preventivo_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (oc.uid)::text AS uid,
    oc.codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (1)::smallint AS pipeline_rank
   FROM ((vendite.offerte_commerciali oc
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_offerte st ON ((st.id = oc.stato_doc_offerta_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (o.id)::text AS uid,
    o.numero AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (2)::smallint AS pipeline_rank
   FROM ((vendite.ordini o
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_ordini st ON ((st.id = o.stato_doc_ordine_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (c.id)::text AS uid,
    c.numero AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (2)::smallint AS pipeline_rank
   FROM ((vendite.contratti c
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'CONTRATTO'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_contratti st ON ((st.id = c.stato_doc_contratto_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (d.id)::text AS uid,
    d.numero AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (3)::smallint AS pipeline_rank
   FROM ((vendite.ddt d
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'DDT_VENDITA'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_ddt st ON ((st.id = d.stato_doc_ddt_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (f.id)::text AS uid,
    (f.numero)::text AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (5)::smallint AS pipeline_rank
   FROM ((vendite.fatture f
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'FATTURA'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_fiscale st ON ((st.id = f.stato_doc_fiscale_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (cm.id)::text AS uid,
    cm.codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (4)::smallint AS pipeline_rank
   FROM ((vendite.commesse cm
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'COMMESSA'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN vendite.stati_commessa st ON ((st.id = cm.stato_commessa_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (r.id)::text AS uid,
    r.numero AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (0)::smallint AS pipeline_rank
   FROM ((vendite.resi r
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'RESO_VENDITA'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_reso st ON ((st.id = r.stato_doc_reso_id)));
```


---
{% include-markdown "signature-core.md" %}
