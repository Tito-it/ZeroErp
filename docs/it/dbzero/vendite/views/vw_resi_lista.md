{% include-markdown "it/dbzero/vendite/manual/vw_resi_lista.md" %}
# 🔍 View `vw_resi_lista`

> 📝 **Descrizione**
>
> Vista flat della lista dei resi di vendita, per l'interfaccia: testata, destinatario (dal soggetto_ruolo), billing account, emittente fiscale, utility, valuta, la fase dello stato, la pratica (pratiche.fn_pratica_del_documento) e il registro (codice e descrizione). La provenienza: sorgente_tipo_id e sorgente_codice_interno, la chiave del documento in sorgente_id o sorgente_uid (una sola, secondo il key_selector del tipo); ddt_origine_id e ddt_origine_numero, la bolla da cui il reso nasce (tipo DDT_VENDITA, la regola d'incontro sulle due colonne). security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_resi_lista
WITH (security_invoker=on) AS
SELECT r.id,
    r.uid,
    r.numero,
    r.anno,
    r.data,
    r.stato_doc_reso_id,
    sr.codice_interno AS stato_codice_interno,
    sr.descrizione AS stato_descrizione,
    r.destinatario_soggetto_ruolo_id,
    s_dest.id AS destinatario_soggetto_id,
    s_dest.ragione_sociale_completa AS destinatario_denominazione,
    s_dest.id_fiscale_univoco_cf_piva,
    r.billing_account_id,
    ba.codice AS ba_codice,
    r.emittente_fiscale_id,
    ef.codice AS emittente_fiscale_codice,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    r.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    r.valuta_id,
    v_val.codice AS valuta_codice,
    r.sorgente_tipo_id,
    src.codice_interno AS sorgente_codice_interno,
    r.sorgente_uid,
    d_src.id AS ddt_origine_id,
    d_src.numero AS ddt_origine_numero,
    r.data_insert,
    r.user_insert,
    r.data_update,
    r.user_update,
    sr.fase,
    pr.pratica_id,
    pr.pratica_numero,
    pr.n_pratiche,
    reg.codice AS registro_codice,
    reg.descrizione AS registro_descrizione,
    r.sorgente_id
   FROM (((((((((((((vendite.resi r
     JOIN config.stati_doc_reso sr ON ((sr.id = r.stato_doc_reso_id)))
     JOIN anagrafiche.soggetti_ruoli sr_dest ON ((sr_dest.id = r.destinatario_soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s_dest ON ((s_dest.id = sr_dest.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = r.billing_account_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = r.emittente_fiscale_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = ef.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN config.utilities u ON ((u.id = r.utility_id)))
     LEFT JOIN config.valute v_val ON ((v_val.id = r.valuta_id)))
     LEFT JOIN config.sorgenti src ON ((src.id = r.sorgente_tipo_id)))
     LEFT JOIN vendite.ddt d_src ON ((((d_src.id = r.sorgente_id) OR (d_src.uid = r.sorgente_uid)) AND ((src.codice_interno)::text = 'DDT_VENDITA'::text))))
     LEFT JOIN LATERAL pratiche.fn_pratica_del_documento(( SELECT so_pr.id
           FROM config.sorgenti so_pr
          WHERE (((so_pr.codice_interno)::text = 'RESO_VENDITA'::text) AND (so_pr.attivo IS TRUE))), (r.id)::text) pr(n_pratiche, pratica_id, pratica_numero) ON (true))
     LEFT JOIN vendite.registri_fatturazione reg ON ((reg.id = r.registro_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
