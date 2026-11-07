{% include-markdown "it/dbzero/vendite/manual/vw_ddt_lista.md" %}
# 🔍 View `vw_ddt_lista`

> 📝 **Descrizione**
>
> Vista flat della lista delle bolle di vendita, per l'interfaccia: testata, destinatario (dal soggetto_ruolo), mittente e vettore (opzionali), billing account, emittente fiscale, utility, valuta, causale, aspetto dei beni, addebito del trasporto, i campi del trasporto per il PDF, la fase dello stato, la pratica (pratiche.fn_pratica_del_documento) e il registro (codice e descrizione). La provenienza: sorgente_tipo_id e sorgente_codice_interno, la chiave del documento in sorgente_id o sorgente_uid (una sola, secondo il key_selector del tipo); ordine_origine_id e ordine_origine_numero quando la bolla viene da un ordine (la regola d'incontro sulle due colonne), NULL per la bolla di riconsegna, che viene da un reso. Le colonne del grafo dei legami le legge il backend da vendite.fn_documento_lineage_sintesi. security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_ddt_lista
WITH (security_invoker=on) AS
SELECT d.id,
    d.uid,
    d.numero,
    d.serie,
    d.anno,
    d.data,
    d.stato_doc_ddt_id,
    sd.codice_interno AS stato_codice_interno,
    sd.descrizione AS stato_descrizione,
    d.destinatario_soggetto_ruolo_id,
    s_dest.id AS destinatario_soggetto_id,
    s_dest.ragione_sociale_completa AS destinatario_denominazione,
    s_dest.id_fiscale_univoco_cf_piva,
    d.mittente_soggetto_ruolo_id,
    s_mitt.ragione_sociale_completa AS mittente_denominazione,
    d.vettore_soggetto_ruolo_id,
    s_vett.ragione_sociale_completa AS vettore_denominazione,
    d.billing_account_id,
    ba.codice AS ba_codice,
    d.emittente_fiscale_id,
    ef.codice AS emittente_fiscale_codice,
    d.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    d.valuta_id,
    v_val.codice AS valuta_codice,
    d.causale_trasporto_id,
    ct.codice AS causale_trasporto_codice,
    ct.descrizione AS causale_trasporto_descrizione,
    d.aspetto_bene_id,
    ab.codice AS aspetto_bene_codice,
    ab.descrizione AS aspetto_bene_descrizione,
    d.modalita_addebito_trasporto_id,
    mat.codice AS modalita_addebito_trasporto_codice,
    d.num_colli,
    d.peso_lordo,
    d.peso_netto,
    d.volume,
    d.targa,
    d.autista,
    d.data_ora_partenza,
    d.data_ora_consegna_prev,
    d.tracking_code,
    d.sorgente_tipo_id,
    src.codice_interno AS sorgente_codice_interno,
    d.sorgente_uid,
    o_src.id AS ordine_origine_id,
    o_src.numero AS ordine_origine_numero,
    d.data_insert,
    d.user_insert,
    d.data_update,
    d.user_update,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    sd.fase,
    pr.pratica_id,
    pr.pratica_numero,
    pr.n_pratiche,
    reg.codice AS registro_codice,
    reg.descrizione AS registro_descrizione,
    d.sorgente_id
   FROM ((((((((((((((((((((vendite.ddt d
     JOIN config.stati_doc_ddt sd ON ((sd.id = d.stato_doc_ddt_id)))
     JOIN anagrafiche.soggetti_ruoli sr_dest ON ((sr_dest.id = d.destinatario_soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s_dest ON ((s_dest.id = sr_dest.soggetto_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_mitt ON ((sr_mitt.id = d.mittente_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_mitt ON ((s_mitt.id = sr_mitt.soggetto_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_vett ON ((sr_vett.id = d.vettore_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_vett ON ((s_vett.id = sr_vett.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = d.billing_account_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = d.emittente_fiscale_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = ef.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN config.utilities u ON ((u.id = d.utility_id)))
     LEFT JOIN config.valute v_val ON ((v_val.id = d.valuta_id)))
     LEFT JOIN config.causali_trasporto ct ON ((ct.id = d.causale_trasporto_id)))
     LEFT JOIN config.aspetti_beni ab ON ((ab.id = d.aspetto_bene_id)))
     LEFT JOIN config.modalita_addebito_trasporto mat ON ((mat.id = d.modalita_addebito_trasporto_id)))
     LEFT JOIN config.sorgenti src ON ((src.id = d.sorgente_tipo_id)))
     LEFT JOIN vendite.ordini o_src ON ((((o_src.id = d.sorgente_id) OR (o_src.uid = d.sorgente_uid)) AND ((src.codice_interno)::text = 'ORDINE_VENDITA'::text))))
     LEFT JOIN LATERAL pratiche.fn_pratica_del_documento(( SELECT so_pr.id
           FROM config.sorgenti so_pr
          WHERE (((so_pr.codice_interno)::text = 'DDT_VENDITA'::text) AND (so_pr.attivo IS TRUE))), (d.id)::text) pr(n_pratiche, pratica_id, pratica_numero) ON (true))
     LEFT JOIN vendite.registri_fatturazione reg ON ((reg.id = d.registro_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
