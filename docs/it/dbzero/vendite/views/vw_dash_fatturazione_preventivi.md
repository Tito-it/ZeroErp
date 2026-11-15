{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_preventivi.md" %}
# 🔍 View `vw_dash_fatturazione_preventivi`

> 📝 **Descrizione**
>
> Dashboard della fatturazione, area PREVENTIVO: una riga per preventivo, la sola revisione attiva (vendite.vw_preventivi.is_attiva). Valore imponibile totale e transitato dalle righe di vendite.vw_preventivi_smistamento_righe: una riga e' transitata quando non e' piu' RESIDUA. competenza_mese: COALESCE(competenza_mese, mese di validita_dal, mese della data). is_abortito: esito NEGATIVO dello stato (null-safe). motivo_fermo: NULL se abortito o transitato per intero; DOC_BOZZA nello stato iniziale del vocabolario, IN_ATTESA_ACCETTAZIONE nello stato di emissione, altrimenti RIGA_RESIDUA. cliente_display: la ragione sociale dell'intestatario dell'istanza. La consuma vendite.vw_dash_fatturazione_documenti. security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_preventivi
WITH (security_invoker=on) AS
WITH righe AS (
         SELECT sr.preventivo_id,
            sr.riga_id,
            script.fn_imponibile_riga(COALESCE(sr.quantita, (0)::numeric), sr.prezzo_unitario, pr.sconto_percentuale) AS valore_riga,
            (sr.stato_smistamento <> 'RESIDUA'::text) AS transitata
           FROM (vendite.vw_preventivi_smistamento_righe sr
             JOIN vendite.preventivi_righe pr ON ((pr.id = sr.riga_id)))
        )
 SELECT 'PREVENTIVO'::character varying AS area,
    COALESCE(p.competenza_mese, script.fn_mese_di(p.validita_dal), script.fn_mese_di(p.data)) AS competenza_mese,
    p.id AS documento_id,
    (p.uid)::text AS documento_uid,
    (p.numero)::text AS codice,
    p.emittente_fiscale_id,
    NULL::bigint AS emittente_soggetto_ruolo_id,
    COALESCE(sum(r.valore_riga), (0)::numeric) AS valore_totale,
    COALESCE(sum(r.valore_riga) FILTER (WHERE r.transitata), (0)::numeric) AS valore_transitato,
    (count(r.riga_id))::integer AS unita_totali,
    (count(r.riga_id) FILTER (WHERE r.transitata))::integer AS unita_transitate,
    ((count(r.riga_id) > 0) AND (count(r.riga_id) = count(r.riga_id) FILTER (WHERE r.transitata))) AS is_transitato,
    COALESCE(((sdp.esito)::text = 'NEGATIVO'::text), false) AS is_abortito,
    (
        CASE
            WHEN COALESCE(((sdp.esito)::text = 'NEGATIVO'::text), false) THEN NULL::text
            WHEN ((count(r.riga_id) > 0) AND (count(r.riga_id) = count(r.riga_id) FILTER (WHERE r.transitata))) THEN NULL::text
            WHEN sdp.iniziale THEN 'DOC_BOZZA'::text
            WHEN sdp.emissione THEN 'IN_ATTESA_ACCETTAZIONE'::text
            ELSE 'RIGA_RESIDUA'::text
        END)::character varying AS motivo_fermo,
    sdp.codice_interno AS stato_codice_interno,
    sdp.codice AS stato_codice,
    sdp.fase,
    s.ragione_sociale_completa AS cliente_display,
    p.data AS data_riferimento
   FROM ((((vendite.vw_preventivi p
     JOIN config.stati_doc_preventivi sdp ON ((sdp.id = p.stato_doc_preventivo_id)))
     LEFT JOIN righe r ON ((r.preventivo_id = p.id)))
     LEFT JOIN anagrafiche.istanze_utilities iu ON ((iu.id = p.istanza_utility_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = iu.soggetto_id)))
  WHERE p.is_attiva
  GROUP BY p.id, p.uid, p.numero, p.competenza_mese, p.validita_dal, p.data, p.emittente_fiscale_id, sdp.codice_interno, sdp.codice, sdp.fase, sdp.esito, sdp.iniziale, sdp.emissione, s.ragione_sociale_completa;
```

</div>


---
{% include-markdown "signature-core.md" %}
