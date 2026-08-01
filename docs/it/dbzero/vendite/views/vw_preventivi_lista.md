{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_lista.md" %}
# 🔍 View `vw_preventivi_lista`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_lista
WITH (security_invoker=on) AS
SELECT p.id,
    p.uid,
    p.numero,
    p.rev,
    p.is_attiva,
    p.data,
    p.stato_doc_preventivo_id,
    sdp.codice_interno AS stato_codice_interno,
    sdp.descrizione AS stato_descrizione,
    p.billing_account_id,
    ba.codice AS ba_codice,
    s.id AS soggetto_id,
    s.ragione_sociale_completa,
    s.id_fiscale_univoco_cf_piva,
    p.emittente_fiscale_id,
    ef.codice AS emittente_fiscale_codice,
    p.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    p.istanza_utility_id,
    iu.codice AS istanza_utility_codice,
    p.totale_imponibile,
    p.totale_iva,
    p.totale_documento,
    p.valuta_id,
    v_val.codice AS valuta_codice,
    p.validita_dal,
    p.validita_al,
    p.competenza_mese,
    p.data_insert,
    s_ef.ragione_sociale_completa AS emittente_fiscale_descrizione,
    sdp.fase,
    lin.pratica_id,
    lin.pratica_numero,
    lin.n_pratiche,
    lin.frontiera_tipo_id,
    lin.frontiera_codice,
    lin.frontiera_stato_codice_interno,
    lin.frontiera_fase,
    lin.n_discendenti_attivi,
    lin.is_transitato
   FROM ((((((((((vendite.vw_preventivi p
     JOIN config.stati_doc_preventivi sdp ON ((sdp.id = p.stato_doc_preventivo_id)))
     LEFT JOIN anagrafiche.istanze_utilities iu ON ((iu.id = p.istanza_utility_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = iu.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = p.billing_account_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = p.emittente_fiscale_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = ef.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN config.utilities u ON ((u.id = p.utility_id)))
     LEFT JOIN config.valute v_val ON ((v_val.id = p.valuta_id)))
     LEFT JOIN vendite.vw_documento_lineage lin ON (((lin.tipo_id = ( SELECT sorgenti.id
           FROM config.sorgenti
          WHERE (((sorgenti.codice_interno)::text = 'PREVENTIVO'::text) AND (sorgenti.attivo IS TRUE)))) AND (lin.uid = (p.uid)::text))));
```


---
{% include-markdown "signature-core.md" %}
