{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_ddt.md" %}
# 🔍 View `vw_dash_fatturazione_ddt`

> 📝 **Descrizione**
>
> Dashboard della fatturazione, area DDT_VENDITA: una riga per bolla, la sesta area di vendite.vw_dash_fatturazione_documenti, con le stesse colonne dei gemelli. Popolazione: solo le bolle con un ruolo di fatturazione; fuori quelle di ordini con fatturazione_trigger CONFERMATO (fattura l'ordine: niente falso PUSH_NON_ESEGUITO e niente doppio conteggio del valore) e fuori le causali non fatturabili (solo trasporto); lo stesso discriminatore della push-list, letto per la stessa strada (il legame di evasione). motivo_fermo: NULL se abortito; DOC_BOZZA nello stato iniziale del vocabolario (la colonna iniziale); IN_TRANSITO prima dello stato del trigger (viaggio in corso, non ritardo; per la bolla senza ordine la soglia e' SPEDITO, una destinazione del processo); dal trigger in poi PUSH_NON_ESEGUITO o PUSH_PARZIALE. Il valore per riga e' COALESCE(prezzo della riga di bolla, prezzo della riga d'ordine attraverso il legame); vendite.vw_ddt_righe_iva_base non serve, perche' filtra il prezzo valorizzato. La chiave della riga la compone script.fn_segment_key. data_riferimento: la data della bolla. fase e is_abortito dal vocabolario. security_invoker=on: la RLS resta di chi legge.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_ddt
WITH (security_invoker=on) AS
WITH righe AS (
         SELECT dr.ddt_id,
            dr.id AS riga_id,
            script.fn_imponibile_riga(dr.quantita, COALESCE(dr.prezzo_unitario, src.src_prezzo_unitario), dr.sconto_percentuale) AS valore_riga,
            (EXISTS ( SELECT 1
                   FROM vendite.commesse_attivita ca
                  WHERE (((ca.segment_key)::text = (script.fn_segment_key('DDT_VENDITA'::character varying, (d2.uid)::text, dr.id))::text) AND ((ca.stato_emissione)::text = 'EMESSA'::text)))) AS transitata
           FROM ((vendite.ddt_righe dr
             JOIN vendite.ddt d2 ON ((d2.id = dr.ddt_id)))
             LEFT JOIN LATERAL ( SELECT or_r.prezzo_unitario AS src_prezzo_unitario
                   FROM (vendite.ordini_righe_fulfillment ful
                     JOIN vendite.ordini_righe or_r ON ((or_r.id = ful.ordine_riga_id)))
                  WHERE (ful.ddt_riga_id = dr.id)
                  ORDER BY ful.id
                 LIMIT 1) src ON (true))
          WHERE (dr.attivo IS TRUE)
        )
 SELECT 'DDT_VENDITA'::character varying AS area,
    script.fn_mese_di(d.data) AS competenza_mese,
    d.id AS documento_id,
    (d.uid)::text AS documento_uid,
    (d.numero)::text AS codice,
    d.emittente_fiscale_id,
    NULL::bigint AS emittente_soggetto_ruolo_id,
    COALESCE(sum(r.valore_riga), (0)::numeric) AS valore_totale,
    COALESCE(sum(r.valore_riga) FILTER (WHERE r.transitata), (0)::numeric) AS valore_transitato,
    (count(r.riga_id))::integer AS unita_totali,
    (count(r.riga_id) FILTER (WHERE r.transitata))::integer AS unita_transitate,
    ((count(r.riga_id) > 0) AND (count(r.riga_id) = count(r.riga_id) FILTER (WHERE r.transitata))) AS is_transitato,
    sdd.is_abortito,
    (
        CASE
            WHEN sdd.is_abortito THEN NULL::text
            WHEN ((count(r.riga_id) > 0) AND (count(r.riga_id) = count(r.riga_id) FILTER (WHERE r.transitata))) THEN NULL::text
            WHEN sdd.iniziale THEN 'DOC_BOZZA'::text
            WHEN (sdd.ordine < COALESCE(trg.ordine, sped.ordine)) THEN 'IN_TRANSITO'::text
            WHEN (count(r.riga_id) FILTER (WHERE r.transitata) = 0) THEN 'PUSH_NON_ESEGUITO'::text
            ELSE 'PUSH_PARZIALE'::text
        END)::character varying AS motivo_fermo,
    sdd.codice_interno AS stato_codice_interno,
    sdd.codice AS stato_codice,
    sdd.fase,
    s.ragione_sociale_completa AS cliente_display,
    d.data AS data_riferimento
   FROM ((((((((vendite.ddt d
     JOIN config.stati_doc_ddt sdd ON ((sdd.id = d.stato_doc_ddt_id)))
     JOIN config.causali_trasporto caus ON (((caus.id = d.causale_trasporto_id) AND (caus.fatturabile IS TRUE))))
     LEFT JOIN LATERAL ( SELECT o_src.fatturazione_trigger
           FROM (((vendite.ordini_righe_fulfillment ful
             JOIN vendite.ordini_righe or_r ON ((or_r.id = ful.ordine_riga_id)))
             JOIN vendite.ordini o_src ON ((o_src.id = or_r.ordine_id)))
             JOIN vendite.ddt_righe dr2 ON ((dr2.id = ful.ddt_riga_id)))
          WHERE (dr2.ddt_id = d.id)
          ORDER BY ful.id
         LIMIT 1) ord ON (true))
     LEFT JOIN config.stati_doc_ddt trg ON (((trg.codice_interno)::text = (ord.fatturazione_trigger)::text)))
     LEFT JOIN config.stati_doc_ddt sped ON (((sped.codice_interno)::text = 'SPEDITO'::text)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = d.destinatario_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     LEFT JOIN righe r ON ((r.ddt_id = d.id)))
  WHERE ((COALESCE(ord.fatturazione_trigger, 'SPEDITO'::character varying))::text <> 'CONFERMATO'::text)
  GROUP BY d.id, d.uid, d.numero, d.data, d.emittente_fiscale_id, sdd.codice_interno, sdd.codice, sdd.fase, sdd.is_abortito, sdd.iniziale, sdd.ordine, trg.ordine, sped.ordine, s.ragione_sociale_completa;
```

</div>


---
{% include-markdown "signature-core.md" %}
