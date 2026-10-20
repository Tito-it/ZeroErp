{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_commesse.md" %}
# 🔍 View `vw_dash_fatturazione_commesse`

> 📝 **Descrizione**
>
> Dashboard fatturazione: resolver area COMMESSE. Valore imponibile snapshot totale vs EMESSO. Denominatore = sole attivita' COMPUTABILI: esclude i void (stato_emissione ANNULLATA; stato_approvazione RIFIUTATA se non gia' EMESSA) simmetrico a orr.attivo degli ordini -&gt; is_transitato/totale/motivo_fermo non falsati dalle void. is_abortito=stato commessa ANNULLATA. SCOPE EMITTENTE nel resolver via fn_get_emittenti_scope_sr_ids(GUC): NULL=tutto, '{}'=niente (fail-closed), array=whitelist. cliente_display=ragione sociale intestatario BA. Consumata da vw_dash_fatturazione_documenti. Rev 2026-10-20 (20261020-85, brief-db-grammatica-unica-documenti 2d, G-6): l'area COMMESSE diventa COMMESSA, il codice della sorgente (il plurale e' ritirato).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_commesse
WITH (security_invoker=on) AS
SELECT 'COMMESSA'::character varying AS area,
    ca.competenza_mese,
    co.id AS documento_id,
    (co.id)::text AS documento_uid,
    (co.codice)::text AS codice,
    NULL::bigint AS emittente_fiscale_id,
    co.emittente_soggetto_ruolo_id,
    sum((COALESCE(ca.prezzo_snapshot, (0)::numeric) * ca.quantita)) AS valore_totale,
    COALESCE(sum((COALESCE(ca.prezzo_snapshot, (0)::numeric) * ca.quantita)) FILTER (WHERE ((ca.stato_emissione)::text = 'EMESSA'::text)), (0)::numeric) AS valore_transitato,
    (count(*))::integer AS unita_totali,
    (count(*) FILTER (WHERE ((ca.stato_emissione)::text = 'EMESSA'::text)))::integer AS unita_transitate,
    (count(*) = count(*) FILTER (WHERE ((ca.stato_emissione)::text = 'EMESSA'::text))) AS is_transitato,
    ((sc.codice_interno)::text = 'ANNULLATA'::text) AS is_abortito,
    (
        CASE
            WHEN ((sc.codice_interno)::text = 'ANNULLATA'::text) THEN NULL::text
            WHEN (count(*) = count(*) FILTER (WHERE ((ca.stato_emissione)::text = 'EMESSA'::text))) THEN NULL::text
            WHEN (count(*) FILTER (WHERE (((ca.stato_emissione)::text <> 'EMESSA'::text) AND ((ca.stato_approvazione)::text <> 'APPROVATA'::text))) > 0) THEN 'ATTIVITA_NON_APPROVATA'::text
            ELSE 'ATTIVITA_NON_EMESSA'::text
        END)::character varying AS motivo_fermo,
    sc.codice_interno AS stato_codice_interno,
    sc.codice AS stato_codice,
    NULL::character varying AS fase,
    s.ragione_sociale_completa AS cliente_display,
    ca.competenza_mese AS data_riferimento
   FROM ((((((vendite.commesse co
     JOIN vendite.stati_commessa sc ON ((sc.id = co.stato_commessa_id)))
     JOIN vendite.commesse_attivita ca ON ((ca.commessa_id = co.id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = co.billing_account_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = ba.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     CROSS JOIN LATERAL ( SELECT script.fn_get_emittenti_scope_sr_ids((NULLIF(current_setting('app.current_user_id'::text, true), ''::text))::integer) AS sr_ids) escope)
  WHERE (((escope.sr_ids IS NULL) OR (co.emittente_soggetto_ruolo_id = ANY (escope.sr_ids))) AND ((ca.stato_emissione)::text <> 'ANNULLATA'::text) AND (((ca.stato_approvazione)::text <> 'RIFIUTATA'::text) OR ((ca.stato_emissione)::text = 'EMESSA'::text)))
  GROUP BY co.id, co.codice, co.emittente_soggetto_ruolo_id, ca.competenza_mese, sc.codice_interno, sc.codice, s.ragione_sociale_completa;
```

</div>


---
{% include-markdown "signature-core.md" %}
