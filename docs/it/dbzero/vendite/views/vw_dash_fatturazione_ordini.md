{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_ordini.md" %}
# 🔍 View `vw_dash_fatturazione_ordini`

> 📝 **Descrizione**
>
> Resolver ordini per la dashboard fatturazione. rev 2026-07-18 (step 8, DL-23 EMENDATO): per trigger SPEDITO/CONSEGNATO valore_totale = RESIDUO DA SPEDIRE (per riga: GREATEST(0, quantita − Σ fulfillment.qta_evasa + fn_ordine_riga_qta_riconsegna) × prezzo scontato — reso-aware, formula single-source) perche' il valore spedito lo porta il DDT: chiude il doppio conteggio ordine-pieno + DDT. Con trigger CONFERMATO valore PIENO invariato (fattura l'ordine: col netto un ordine spedito-ma-non-pushato mostrerebbe 0 senza compensazione — buco cieco sulla configurazione di default). L'area Ordini e' l'unica a misura netta (accettato, §4c). rev 2026-07-18 (step 7, DL-20): trigger-aware, motivo IN_ATTESA_DDT (FISIOLOGICO) per trigger SPEDITO/CONSEGNATO. security_invoker=on + RLS. Rev 2026-10-20 (20261020-83, brief-db-grammatica-unica-documenti 2d e 2e): l'area ORDINI diventa ORDINE_VENDITA, il codice della sorgente; la chiave della riga la compone script.fn_segment_key.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_ordini
WITH (security_invoker=on) AS
WITH righe AS (
         SELECT orr.ordine_id,
            orr.id AS riga_id,
            script.fn_imponibile_riga(orr.quantita, orr.prezzo_unitario, orr.sconto_percentuale) AS valore_riga,
            script.fn_imponibile_riga(GREATEST((0)::numeric, ((orr.quantita - COALESCE(ful.evasa, (0)::numeric)) + vendite.fn_ordine_riga_qta_riconsegna(orr.id))), orr.prezzo_unitario, orr.sconto_percentuale) AS valore_riga_residua,
            (EXISTS ( SELECT 1
                   FROM vendite.commesse_attivita ca
                  WHERE (((ca.segment_key)::text = (script.fn_segment_key('ORDINE_VENDITA'::character varying, (o2.uid)::text, orr.id))::text) AND ((ca.stato_emissione)::text = 'EMESSA'::text)))) AS transitata
           FROM ((vendite.ordini_righe orr
             JOIN vendite.ordini o2 ON ((o2.id = orr.ordine_id)))
             LEFT JOIN ( SELECT f.ordine_riga_id,
                    sum(f.qta_evasa) AS evasa
                   FROM vendite.ordini_righe_fulfillment f
                  GROUP BY f.ordine_riga_id) ful ON ((ful.ordine_riga_id = orr.id)))
          WHERE (orr.attivo IS TRUE)
        )
 SELECT 'ORDINE_VENDITA'::character varying AS area,
    (date_trunc('month'::text, (o.data)::timestamp with time zone))::date AS competenza_mese,
    o.id AS documento_id,
    (o.uid)::text AS documento_uid,
    (o.numero)::text AS codice,
    o.emittente_fiscale_id,
    NULL::bigint AS emittente_soggetto_ruolo_id,
        CASE
            WHEN ((o.fatturazione_trigger)::text = ANY (ARRAY['SPEDITO'::text, 'CONSEGNATO'::text])) THEN COALESCE(sum(r.valore_riga_residua), (0)::numeric)
            ELSE COALESCE(sum(r.valore_riga), (0)::numeric)
        END AS valore_totale,
    COALESCE(sum(r.valore_riga) FILTER (WHERE r.transitata), (0)::numeric) AS valore_transitato,
    (count(r.riga_id))::integer AS unita_totali,
    (count(r.riga_id) FILTER (WHERE r.transitata))::integer AS unita_transitate,
    ((count(r.riga_id) > 0) AND (count(r.riga_id) = count(r.riga_id) FILTER (WHERE r.transitata))) AS is_transitato,
    COALESCE(((sdo.esito)::text = 'NEGATIVO'::text), false) AS is_abortito,
    (
        CASE
            WHEN COALESCE(((sdo.esito)::text = 'NEGATIVO'::text), false) THEN NULL::text
            WHEN ((count(r.riga_id) > 0) AND (count(r.riga_id) = count(r.riga_id) FILTER (WHERE r.transitata))) THEN NULL::text
            WHEN ((sdo.codice_interno)::text = 'DRAFT'::text) THEN 'DOC_BOZZA'::text
            WHEN ((o.fatturazione_trigger)::text = ANY (ARRAY['SPEDITO'::text, 'CONSEGNATO'::text])) THEN 'IN_ATTESA_DDT'::text
            WHEN (count(r.riga_id) FILTER (WHERE r.transitata) = 0) THEN 'PUSH_NON_ESEGUITO'::text
            ELSE 'PUSH_PARZIALE'::text
        END)::character varying AS motivo_fermo,
    sdo.codice_interno AS stato_codice_interno,
    sdo.codice AS stato_codice,
    sdo.fase,
    s.ragione_sociale_completa AS cliente_display,
    o.data AS data_riferimento
   FROM ((((vendite.ordini o
     JOIN config.stati_doc_ordini sdo ON ((sdo.id = o.stato_doc_ordine_id)))
     LEFT JOIN righe r ON ((r.ordine_id = o.id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = o.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
  GROUP BY o.id, o.uid, o.numero, o.data, o.emittente_fiscale_id, o.fatturazione_trigger, sdo.codice_interno, sdo.codice, sdo.fase, sdo.esito, s.ragione_sociale_completa;
```

</div>


---
{% include-markdown "signature-core.md" %}
