{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_contratti.md" %}
# 🔍 View `vw_dash_fatturazione_contratti`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_contratti AS
SELECT 'CONTRATTI'::character varying AS area,
    (m.mese_ts)::date AS competenza_mese,
    c.id AS documento_id,
    (c.uid)::text AS documento_uid,
    (c.numero)::text AS codice,
    c.emittente_fiscale_id,
    NULL::bigint AS emittente_soggetto_ruolo_id,
    NULL::numeric AS valore_totale,
    NULL::numeric AS valore_transitato,
    1 AS unita_totali,
        CASE
            WHEN gen.canone_generato THEN 1
            ELSE 0
        END AS unita_transitate,
    gen.canone_generato AS is_transitato,
    false AS is_abortito,
    (
        CASE
            WHEN gen.canone_generato THEN NULL::text
            WHEN ((sdc.codice_interno)::text = 'DRAFT'::text) THEN 'DOC_BOZZA'::text
            ELSE 'CANONE_NON_GENERATO'::text
        END)::character varying AS motivo_fermo,
    sdc.codice_interno AS stato_codice_interno,
    sdc.codice AS stato_codice,
    sdc.fase,
    sog.ragione_sociale_completa AS cliente_display
   FROM (((((((vendite.contratti c
     JOIN config.stati_doc_contratti sdc ON (((sdc.id = c.stato_doc_contratto_id) AND ((sdc.esito)::text IS DISTINCT FROM 'NEGATIVO'::text))))
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'CONTRATTO'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = c.billing_account_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = ba.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti sog ON ((sog.id = sr.soggetto_id)))
     CROSS JOIN LATERAL generate_series(date_trunc('month'::text, (c.valido_dal)::timestamp with time zone), LEAST(COALESCE(date_trunc('month'::text, (c.valido_al)::timestamp with time zone), (date_trunc('month'::text, (CURRENT_DATE)::timestamp without time zone))::timestamp with time zone), (date_trunc('month'::text, (CURRENT_DATE)::timestamp without time zone))::timestamp with time zone), '1 mon'::interval) m(mese_ts))
     CROSS JOIN LATERAL ( SELECT (EXISTS ( SELECT 1
                   FROM vendite.commesse_attivita ca
                  WHERE ((ca.sorgente_tipo_id = s.id) AND (ca.sorgente_uid = (c.uid)::text) AND (ca.competenza_mese = (m.mese_ts)::date) AND ((ca.stato_emissione)::text = 'EMESSA'::text)))) AS canone_generato) gen);
```


---
{% include-markdown "signature-core.md" %}
