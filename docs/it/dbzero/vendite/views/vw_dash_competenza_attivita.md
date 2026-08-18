{% include-markdown "it/dbzero/vendite/manual/vw_dash_competenza_attivita.md" %}
# 🔍 View `vw_dash_competenza_attivita`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_competenza_attivita
WITH (security_invoker=on) AS
SELECT ca.competenza_mese,
    co.id AS commessa_id,
    (co.codice)::text AS commessa_codice,
    ca.id AS commessa_attivita_id,
    co.emittente_soggetto_ruolo_id,
    s.ragione_sociale_completa AS cliente_display,
    ca.articolo_id,
    ca.data_attivita,
    ca.quantita,
    ca.stato_approvazione,
    ca.stato_emissione,
    (
        CASE
            WHEN (((ca.stato_emissione)::text <> 'EMESSA'::text) AND ((ca.stato_approvazione)::text <> 'APPROVATA'::text)) THEN 'DA_APPROVARE'::text
            WHEN ((ca.stato_emissione)::text <> 'EMESSA'::text) THEN 'DA_EMETTERE'::text
            WHEN (af.fattura_riga_id IS NULL) THEN 'EMESSA_NON_FATTURATA'::text
            ELSE 'FATTURATA'::text
        END)::character varying AS stadio,
    (COALESCE(ca.prezzo_snapshot, (0)::numeric) * ca.quantita) AS valore,
    af.data_insert AS data_emissione,
        CASE
            WHEN (af.id IS NULL) THEN NULL::boolean
            ELSE ((date_trunc('month'::text, af.data_insert))::date > ca.competenza_mese)
        END AS emessa_in_ritardo,
    af.sospesa,
    af.posticipa_al,
    f.id AS fattura_id,
    af.fattura_riga_id,
    f.anno AS fattura_anno,
    f.serie AS fattura_serie,
    f.numero AS fattura_numero,
    sdf.codice_interno AS stato_fattura_codice_interno,
    sdf.codice AS stato_fattura_codice,
    (
        CASE
            WHEN (fr.id IS NULL) THEN NULL::numeric
            WHEN (COALESCE(fr.qta, (0)::numeric) = (0)::numeric) THEN (0)::numeric
            ELSE ((fr.imponibile_riga * af.quantita) / fr.qta)
        END)::numeric(18,6) AS valore_fatturato,
    COALESCE(f.critical, false) AS fattura_critical,
    lf.lotto_id,
    ca.sorgente_tipo_id,
    ca.sorgente_uid,
    ca.tipo_movimento,
    vendite.fn_build_gruppo_fatturabile_key(ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id) AS gruppo_key,
    sc.emittibile AS commessa_emittibile,
    sc.codice_interno AS commessa_stato_codice_interno,
    COALESCE(sc.descrizione, sc.codice) AS commessa_stato_descrizione,
    co.billing_account_id
   FROM (((((((((((vendite.commesse co
     JOIN vendite.stati_commessa sc ON ((sc.id = co.stato_commessa_id)))
     JOIN vendite.commesse_attivita ca ON ((ca.commessa_id = co.id)))
     LEFT JOIN vendite.attivita_fatturabili af ON ((af.commessa_attivita_id = ca.id)))
     LEFT JOIN vendite.fatture_righe fr ON ((fr.id = af.fattura_riga_id)))
     LEFT JOIN vendite.fatture f ON ((f.id = fr.fattura_id)))
     LEFT JOIN config.stati_doc_fiscale sdf ON ((sdf.id = f.stato_doc_fiscale_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = co.billing_account_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = ba.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     LEFT JOIN LATERAL ( SELECT flf.lotto_id
           FROM vendite.fatturazione_lotti_fatture flf
          WHERE (flf.fattura_id = f.id)
          ORDER BY flf.lotto_id DESC
         LIMIT 1) lf ON (true))
     CROSS JOIN LATERAL ( SELECT script.fn_get_emittenti_scope_sr_ids((NULLIF(current_setting('app.current_user_id'::text, true), ''::text))::integer) AS sr_ids) escope)
  WHERE (((escope.sr_ids IS NULL) OR (co.emittente_soggetto_ruolo_id = ANY (escope.sr_ids))) AND ((sc.codice_interno)::text <> 'ANNULLATA'::text) AND ((ca.stato_emissione)::text <> 'ANNULLATA'::text) AND (((ca.stato_approvazione)::text <> 'RIFIUTATA'::text) OR ((ca.stato_emissione)::text = 'EMESSA'::text)));
```


---
{% include-markdown "signature-core.md" %}
