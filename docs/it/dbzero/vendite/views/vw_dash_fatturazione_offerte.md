{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_offerte.md" %}
# 🔍 View `vw_dash_fatturazione_offerte`

> 📝 **Descrizione**
>
> Dashboard fatturazione: resolver area OFFERTE, a conteggi (D-2). Transitata = figlio vivo (contratto via offerta_id NOT is_abortito_snapshot, o ordine documento_origine OFFERTA esito != NEGATIVO). FIGLIO_ABORTITO = figlio annullato (XOR permanente). cliente_display=ragione sociale intestatario istanza (path vw_offerte_commerciali_lista). Consumata da vw_dash_fatturazione_documenti. rev 2026-10-11 (20261011-76, brief-db-annullo-documento-con-legami D-6): un'offerta ha al piu' un figlio VIVO ma puo' avere piu' figli annullati; i figli si riassumono in una riga per lato (esiste, vivo), cosi' l'offerta non si duplica e un figlio morto non nasconde quello vivo. FIGLIO_ABORTITO resta il caso «figli solo annullati», che ora si sblocca rigenerando. ⭐ rev 2026-10-19 (20261019-93, brief-db-grammatica-unica-documenti lotto 2b, G-3 di Tid): ricreata dopo l'allargamento della colonna; il codice di origine o di destinazione e' quello di config.sorgenti (OFFERTA -&gt; OFFERTA_COMMERCIALE, ORDINE -&gt; ORDINE_VENDITA). Rev 2026-10-20 (20261020-69, brief-db-grammatica-unica-documenti 2d, G-6): l'area OFFERTE diventa OFFERTA_COMMERCIALE, il codice della sorgente (il plurale e' ritirato).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

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
            WHEN ((sdo.codice_interno)::text = 'BOZZA'::text) THEN 'DOC_BOZZA'::text
            WHEN ((sdo.codice_interno)::text = 'EMESSA'::text) THEN 'IN_ATTESA_ACCETTAZIONE'::text
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
           FROM vendite.contratti c
          WHERE (c.offerta_id = o.id)) ct)
     CROSS JOIN LATERAL ( SELECT (count(*) > 0) AS esiste,
            COALESCE(bool_or(((sdor.esito)::text IS DISTINCT FROM 'NEGATIVO'::text)), false) AS vivo
           FROM (vendite.ordini od
             JOIN config.stati_doc_ordini sdor ON ((sdor.id = od.stato_doc_ordine_id)))
          WHERE (((od.documento_origine_tipo)::text = 'OFFERTA_COMMERCIALE'::text) AND (od.documento_origine_id = o.id))) fo)
     LEFT JOIN anagrafiche.istanze_utilities iu ON ((iu.id = o.istanza_utility_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = iu.soggetto_id)));
```


---
{% include-markdown "signature-core.md" %}
