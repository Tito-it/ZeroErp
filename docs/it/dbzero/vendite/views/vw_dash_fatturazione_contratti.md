{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_contratti.md" %}
# 🔍 View `vw_dash_fatturazione_contratti`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_contratti AS
SELECT 'CONTRATTI'::character varying AS area,
    NULL::date AS competenza_mese,
    c.id AS documento_id,
    (c.uid)::text AS documento_uid,
    (c.numero)::text AS codice,
    c.emittente_fiscale_id,
    NULL::bigint AS emittente_soggetto_ruolo_id,
    NULL::numeric AS valore_totale,
    NULL::numeric AS valore_transitato,
    1 AS unita_totali,
    NULL::integer AS unita_transitate,
    NULL::boolean AS is_transitato,
    false AS is_abortito,
    NULL::character varying AS motivo_fermo,
    sdc.codice_interno AS stato_codice_interno,
    sdc.codice AS stato_codice,
    sdc.fase,
    sog.ragione_sociale_completa AS cliente_display,
    c.valido_dal AS data_riferimento
   FROM ((((vendite.contratti c
     JOIN config.stati_doc_contratti sdc ON (((sdc.id = c.stato_doc_contratto_id) AND ((sdc.esito)::text IS DISTINCT FROM 'NEGATIVO'::text))))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = c.billing_account_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = ba.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti sog ON ((sog.id = sr.soggetto_id)));
```


---
{% include-markdown "signature-core.md" %}
