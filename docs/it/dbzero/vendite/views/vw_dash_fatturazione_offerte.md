{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_offerte.md" %}
# 🔍 View `vw_dash_fatturazione_offerte`

> 📝 **Descrizione**
>
> Dashboard della fatturazione, area OFFERTA_COMMERCIALE: una riga per offerta, a conteggi. L'offerta e' transitata se ha un figlio vivo: un contratto non annullato (is_abortito_snapshot) o un ordine con esito diverso da NEGATIVO, cioe' un documento che la dichiara come provenienza (sorgente_tipo_id OFFERTA_COMMERCIALE, chiave dell'offerta in sorgente_uid o sorgente_id). Un'offerta ha al piu' un figlio vivo ma puo' averne piu' annullati: i figli si riassumono in una riga per lato (esiste, vivo), cosi' l'offerta non si duplica e un figlio annullato non nasconde quello vivo. motivo_fermo: NULL se transitata o con esito NEGATIVO; FIGLIO_ABORTITO se ha solo figli annullati (si sblocca rigenerando); DOC_BOZZA nello stato iniziale del vocabolario (config.stati_doc_offerte.iniziale); IN_ATTESA_ACCETTAZIONE nello stato di emissione (emissione); altrimenti SENZA_FIGLIO. Lo stato si legge per significato, non per codice. cliente_display e' la ragione sociale dell'intestatario dell'istanza. La consuma vendite.vw_dash_fatturazione_documenti. security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_offerte
WITH (security_invoker=on) AS
SELECT 'OFFERTA_COMMERCIALE'::character varying AS area,
    (date_trunc('month'::text, (COALESCE(o.validita_dal, script.fn_giorno_operativo(o.data_emissione), script.fn_giorno_operativo(o.data_insert)))::timestamp with time zone))::date AS competenza_mese,
    o.id AS documento_id,
    (o.uid)::text AS documento_uid,
    o.codice,
    o.emittente_fiscale_id,
    NULL::bigint AS emittente_soggetto_ruolo_id,
    NULL::numeric AS valore_totale,
    NULL::numeric AS valore_transitato,
    1 AS unita_totali,
        CASE
            WHEN (ct.vivo OR fo.vivo) THEN 1
            ELSE 0
        END AS unita_transitate,
    (ct.vivo OR fo.vivo) AS is_transitato,
    COALESCE(((sdo.esito)::text = 'NEGATIVO'::text), false) AS is_abortito,
    (
        CASE
            WHEN COALESCE(((sdo.esito)::text = 'NEGATIVO'::text), false) THEN NULL::text
            WHEN (ct.vivo OR fo.vivo) THEN NULL::text
            WHEN (ct.esiste OR fo.esiste) THEN 'FIGLIO_ABORTITO'::text
            WHEN sdo.iniziale THEN 'DOC_BOZZA'::text
            WHEN sdo.emissione THEN 'IN_ATTESA_ACCETTAZIONE'::text
            ELSE 'SENZA_FIGLIO'::text
        END)::character varying AS motivo_fermo,
    sdo.codice_interno AS stato_codice_interno,
    sdo.codice AS stato_codice,
    sdo.fase,
    s.ragione_sociale_completa AS cliente_display,
    COALESCE(script.fn_giorno_operativo(o.data_emissione), o.validita_dal, script.fn_giorno_operativo(o.data_insert)) AS data_riferimento
   FROM (((((vendite.offerte_commerciali o
     JOIN config.stati_doc_offerte sdo ON ((sdo.id = o.stato_doc_offerta_id)))
     CROSS JOIN LATERAL ( SELECT (count(*) > 0) AS esiste,
            COALESCE(bool_or((NOT c.is_abortito_snapshot)), false) AS vivo
           FROM (vendite.contratti c
             JOIN config.sorgenti so_c ON (((so_c.id = c.sorgente_tipo_id) AND ((so_c.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text))))
          WHERE ((c.sorgente_id = o.id) OR (c.sorgente_uid = o.uid))) ct)
     CROSS JOIN LATERAL ( SELECT (count(*) > 0) AS esiste,
            COALESCE(bool_or(((sdor.esito)::text IS DISTINCT FROM 'NEGATIVO'::text)), false) AS vivo
           FROM ((vendite.ordini od
             JOIN config.sorgenti so_o ON (((so_o.id = od.sorgente_tipo_id) AND ((so_o.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text))))
             JOIN config.stati_doc_ordini sdor ON ((sdor.id = od.stato_doc_ordine_id)))
          WHERE ((od.sorgente_id = o.id) OR (od.sorgente_uid = o.uid))) fo)
     LEFT JOIN anagrafiche.istanze_utilities iu ON ((iu.id = o.istanza_utility_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = iu.soggetto_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
