{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_ordini.md" %}
# 🔍 View `vw_dash_fatturazione_ordini`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_ordini AS
WITH righe AS (
         SELECT orr.ordine_id,
            orr.id AS riga_id,
            ((orr.quantita * orr.prezzo_unitario) * ((1)::numeric - (COALESCE(orr.sconto_percentuale, (0)::numeric) / 100.0))) AS valore_riga,
            (EXISTS ( SELECT 1
                   FROM vendite.commesse_attivita ca
                  WHERE (((ca.segment_key)::text = ((('ORD:'::text || (o2.uid)::text) || ':R:'::text) || (orr.id)::text)) AND ((ca.stato_emissione)::text = 'EMESSA'::text)))) AS transitata
           FROM (vendite.ordini_righe orr
             JOIN vendite.ordini o2 ON ((o2.id = orr.ordine_id)))
          WHERE (orr.attivo IS TRUE)
        )
 SELECT 'ORDINI'::character varying AS area,
    (date_trunc('month'::text, (o.data)::timestamp with time zone))::date AS competenza_mese,
    o.id AS documento_id,
    (o.uid)::text AS documento_uid,
    (o.numero)::text AS codice,
    o.emittente_fiscale_id,
    NULL::bigint AS emittente_soggetto_ruolo_id,
    COALESCE(sum(r.valore_riga), (0)::numeric) AS valore_totale,
    COALESCE(sum(r.valore_riga) FILTER (WHERE r.transitata), (0)::numeric) AS valore_transitato,
    (count(r.riga_id))::integer AS unita_totali,
    (count(r.riga_id) FILTER (WHERE r.transitata))::integer AS unita_transitate,
    ((count(r.riga_id) > 0) AND (count(r.riga_id) = count(r.riga_id) FILTER (WHERE r.transitata))) AS is_transitato,
    ((sdo.esito)::text = 'NEGATIVO'::text) AS is_abortito,
    (
        CASE
            WHEN ((sdo.esito)::text = 'NEGATIVO'::text) THEN NULL::text
            WHEN ((count(r.riga_id) > 0) AND (count(r.riga_id) = count(r.riga_id) FILTER (WHERE r.transitata))) THEN NULL::text
            WHEN ((sdo.codice_interno)::text = 'DRAFT'::text) THEN 'DOC_BOZZA'::text
            WHEN (count(r.riga_id) FILTER (WHERE r.transitata) = 0) THEN 'PUSH_NON_ESEGUITO'::text
            ELSE 'PUSH_PARZIALE'::text
        END)::character varying AS motivo_fermo,
    sdo.codice_interno AS stato_codice_interno,
    sdo.codice AS stato_codice,
    sdo.fase
   FROM ((vendite.ordini o
     JOIN config.stati_doc_ordini sdo ON ((sdo.id = o.stato_doc_ordine_id)))
     LEFT JOIN righe r ON ((r.ordine_id = o.id)))
  GROUP BY o.id, o.uid, o.numero, o.data, o.emittente_fiscale_id, sdo.codice_interno, sdo.codice, sdo.fase, sdo.esito;
```


---
{% include-markdown "signature-core.md" %}
