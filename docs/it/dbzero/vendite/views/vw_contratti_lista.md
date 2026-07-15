# 🔍 View `vw_contratti_lista`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_contratti_lista
WITH (security_invoker=on) AS
SELECT c.id,
    c.uid,
    c.numero,
    c.billing_account_id,
    ba.codice AS ba_codice,
    s.id AS soggetto_id,
    s.ragione_sociale_completa,
    s.id_fiscale_univoco_cf_piva,
    c.emittente_fiscale_id,
    ef.codice AS emittente_fiscale_codice,
    c.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    c.ambito,
    c.data,
    c.valido_dal,
    c.valido_al,
    c.stato_doc_contratto_id,
    sd.codice_interno AS stato_codice_interno,
    sd.codice AS stato_codice,
    sd.descrizione AS stato_descrizione,
    c.listino_id,
    l.codice AS listino_codice,
    l.descrizione AS listino_descrizione,
    c.listino_versione_id,
    lv.codice_versione AS listino_versione_codice,
    c.tipo_variazione_globale,
    c.valore_variazione_globale,
    c.categoria_cliente_id_snapshot,
    cc_snap.codice AS categoria_cliente_snapshot_codice,
    cc_snap.descrizione AS categoria_cliente_snapshot_descrizione,
    c.valuta_id,
    v_val.codice AS valuta_codice,
    v_val.descrizione AS valuta_descrizione,
    c.data_insert,
    c.user_insert,
    c.data_update,
    c.user_update,
    COALESCE(s_ef.ragione_sociale_completa, (ef.descrizione)::text) AS emittente_fiscale_descrizione,
    sd.fase,
    lin.pratica_id,
    lin.pratica_numero,
    lin.n_pratiche,
    lin.frontiera_tipo_id,
    lin.frontiera_codice,
    lin.frontiera_stato_codice_interno,
    lin.frontiera_fase,
    lin.n_discendenti_attivi,
    lin.is_transitato
   FROM (((((((((((((vendite.contratti c
     JOIN anagrafiche.billing_account ba ON ((ba.id = c.billing_account_id)))
     JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = ba.soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     JOIN config.utilities u ON ((u.id = c.utility_id)))
     JOIN config.stati_doc_contratti sd ON ((sd.id = c.stato_doc_contratto_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = c.emittente_fiscale_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = ef.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN vendite.listini l ON ((l.id = c.listino_id)))
     LEFT JOIN vendite.listini_versioni lv ON ((lv.id = c.listino_versione_id)))
     LEFT JOIN anagrafiche.categorie_clienti cc_snap ON ((cc_snap.id = c.categoria_cliente_id_snapshot)))
     LEFT JOIN config.valute v_val ON ((v_val.id = c.valuta_id)))
     LEFT JOIN vendite.vw_documento_lineage lin ON (((lin.tipo_id = ( SELECT sorgenti.id
           FROM config.sorgenti
          WHERE (((sorgenti.codice_interno)::text = 'CONTRATTO'::text) AND (sorgenti.attivo IS TRUE)))) AND (lin.uid = (c.id)::text))));
```


---
{% include-markdown "signature-core.md" %}
