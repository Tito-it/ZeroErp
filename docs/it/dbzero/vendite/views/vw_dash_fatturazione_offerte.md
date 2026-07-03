{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_offerte.md" %}
# 🔍 View `vw_dash_fatturazione_offerte`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_offerte AS
SELECT 'OFFERTE'::character varying AS area,
    (date_trunc('month'::text, (COALESCE(o.validita_dal, (o.data_emissione)::date, (o.data_insert)::date))::timestamp with time zone))::date AS competenza_mese,
    o.id AS documento_id,
    (o.uid)::text AS documento_uid,
    o.codice,
    o.emittente_fiscale_id,
    NULL::bigint AS emittente_soggetto_ruolo_id,
    NULL::numeric AS valore_totale,
    NULL::numeric AS valore_transitato,
    1 AS unita_totali,
        CASE
            WHEN (((ct.id IS NOT NULL) AND (NOT ct.is_abortito_snapshot)) OR ((fo.ordine_id IS NOT NULL) AND ((fo.esito)::text IS DISTINCT FROM 'NEGATIVO'::text))) THEN 1
            ELSE 0
        END AS unita_transitate,
    (((ct.id IS NOT NULL) AND (NOT ct.is_abortito_snapshot)) OR ((fo.ordine_id IS NOT NULL) AND ((fo.esito)::text IS DISTINCT FROM 'NEGATIVO'::text))) AS is_transitato,
    ((sdo.esito)::text = 'NEGATIVO'::text) AS is_abortito,
    (
        CASE
            WHEN ((sdo.esito)::text = 'NEGATIVO'::text) THEN NULL::text
            WHEN (((ct.id IS NOT NULL) AND (NOT ct.is_abortito_snapshot)) OR ((fo.ordine_id IS NOT NULL) AND ((fo.esito)::text IS DISTINCT FROM 'NEGATIVO'::text))) THEN NULL::text
            WHEN ((ct.id IS NOT NULL) OR (fo.ordine_id IS NOT NULL)) THEN 'FIGLIO_ABORTITO'::text
            WHEN ((sdo.codice_interno)::text = 'BOZZA'::text) THEN 'DOC_BOZZA'::text
            WHEN ((sdo.codice_interno)::text = 'EMESSA'::text) THEN 'IN_ATTESA_ACCETTAZIONE'::text
            ELSE 'SENZA_FIGLIO'::text
        END)::character varying AS motivo_fermo,
    sdo.codice_interno AS stato_codice_interno,
    sdo.codice AS stato_codice,
    sdo.fase
   FROM (((vendite.offerte_commerciali o
     JOIN config.stati_doc_offerte sdo ON ((sdo.id = o.stato_doc_offerta_id)))
     LEFT JOIN vendite.contratti ct ON ((ct.offerta_id = o.id)))
     LEFT JOIN LATERAL ( SELECT od.id AS ordine_id,
            sdor.esito
           FROM (vendite.ordini od
             JOIN config.stati_doc_ordini sdor ON ((sdor.id = od.stato_doc_ordine_id)))
          WHERE (((od.documento_origine_tipo)::text = 'OFFERTA'::text) AND (od.documento_origine_id = o.id))
         LIMIT 1) fo ON (true));
```


---
{% include-markdown "signature-core.md" %}
