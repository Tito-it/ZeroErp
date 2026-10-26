{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_ddt.md" %}
# 🔍 View `vw_dash_fatturazione_ddt`

> 📝 **Descrizione**
>
> Resolver DDT per la dashboard fatturazione (brief-db-fatturazione-ddt-resi §4a, step 6), sesta area di vw_dash_fatturazione_documenti: stesse 19 colonne dei gemelli. POPOLAZIONE = solo DDT con ruolo di fatturazione — fuori quelli di ordini con trigger CONFERMATO (fattura l'ordine: XOR; evita falso positivo PUSH_NON_ESEGUITO perpetuo e doppio conteggio del valore) e fuori le causali non fatturabili (solo trasporto, DL-28). Stesso discriminatore del lister, letto per la stessa strada (fulfillment). motivo_fermo TRIGGER-AWARE: DOC_BOZZA in DRAFT, IN_TRANSITO prima dello stato-trigger (viaggio in corso, non ritardo), PUSH_NON_ESEGUITO / PUSH_PARZIALE dal trigger in poi; soglia = rank del trigger, SPEDITO per lo standalone. Valore per riga con COALESCE(ddt_righe.prezzo_unitario, ordini_righe via fulfillment) — vw_ddt_righe_iva_base NON riusabile (filtra prezzo NOT NULL). data_riferimento = ddt.data (DL-17). fase/is_abortito dal catalogo. security_invoker=on + RLS. rev 2026-07-18. Rev 2026-10-20 (20261020-68, brief-db-grammatica-unica-documenti 2d e 2e): l'area DDT diventa DDT_VENDITA, il codice della sorgente; la chiave della riga la compone script.fn_segment_key.

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
    (date_trunc('month'::text, (d.data)::timestamp with time zone))::date AS competenza_mese,
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
            WHEN ((sdd.codice_interno)::text = 'DRAFT'::text) THEN 'DOC_BOZZA'::text
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
  GROUP BY d.id, d.uid, d.numero, d.data, d.emittente_fiscale_id, sdd.codice_interno, sdd.codice, sdd.fase, sdd.is_abortito, sdd.ordine, trg.ordine, sped.ordine, s.ragione_sociale_completa;
```

</div>


---
{% include-markdown "signature-core.md" %}
