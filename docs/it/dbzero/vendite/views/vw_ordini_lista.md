{% include-markdown "it/dbzero/vendite/manual/vw_ordini_lista.md" %}
# 🔍 View `vw_ordini_lista`

> 📝 **Descrizione**
>
> Vista canonica della lista e del dettaglio degli ordini di vendita: la testata con le decodifiche denormalizzate (stato, cliente, billing account, emittente, utility, pagamento, valuta, agente, registro) e la provenienza. Sola denormalizzazione, nessuno scope: security_invoker=on, la RLS di vendite.ordini morde. La provenienza viene da sorgente_* (in coda: sorgente_tipo_id, sorgente_id, sorgente_uid), cercata con la regola d'incontro del modello (doc.id = sorgente_id OR doc.uid = sorgente_uid); documento_origine_tipo e' il codice di config.sorgenti, documento_origine_id l'id del documento d'origine (anche per preventivo e offerta, che hanno chiave uid), documento_origine_codice il suo numero (preventivi.numero, offerte_commerciali.codice). NULL = ordine nato da solo. pdf_mode e' la modalita' del bottone PDF, dallo stato. pratica_* da pratiche.fn_pratica_del_documento. data_consegna_richiesta_cliente_min e' la prima data di consegna chiesta dal cliente sulle righe attive (NULL: nessuna la dichiara), calcolata dalle righe e non salvata in testata. registro_codice e registro_descrizione da vendite.registri_fatturazione, come nelle liste sorelle che hanno un registro (fatture, bolle, resi). Le colonne del grafo (frontiera_*, discendenti, transito) non stanno qui: le legge il backend da vendite.fn_documento_lineage_sintesi. Le colonne nuove vanno in coda: CREATE OR REPLACE VIEW puo' solo appendere.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_ordini_lista
WITH (security_invoker=on) AS
SELECT o.id,
    o.uid,
    o.numero,
    o.serie,
    o.anno,
    o.data,
    o.stato_doc_ordine_id,
    sd.codice_interno AS stato_codice_interno,
    sd.descrizione AS stato_descrizione,
    o.soggetto_ruolo_id,
    s.id AS soggetto_id,
    s.ragione_sociale_completa,
    s.id_fiscale_univoco_cf_piva,
    o.billing_account_id,
    ba.codice AS ba_codice,
    o.emittente_fiscale_id,
    ef.codice AS emittente_fiscale_codice,
    o.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    o.imponibile_tot,
    o.sconto_tot,
    o.iva_tot,
    o.totale_doc,
    o.modalita_pagamento_id,
    mp.codice AS modalita_pagamento_codice,
    o.termine_pagamento_id,
    tp.codice AS termine_pagamento_codice,
    o.valuta_id,
    v_val.codice AS valuta_codice,
    o.tasso_cambio,
    o.fatturazione_trigger,
    o.canale_origine,
    o.agente_soggetto_ruolo_id,
    s_ag.ragione_sociale_completa AS agente_denominazione,
    so_or.codice_interno AS documento_origine_tipo,
        CASE so_or.codice_interno
            WHEN 'PREVENTIVO'::text THEN pv.id
            WHEN 'OFFERTA_COMMERCIALE'::text THEN oc.id
            ELSE o.sorgente_id
        END AS documento_origine_id,
        CASE so_or.codice_interno
            WHEN 'PREVENTIVO'::text THEN pv.numero
            WHEN 'OFFERTA_COMMERCIALE'::text THEN (oc.codice)::character varying
            ELSE NULL::character varying
        END AS documento_origine_codice,
    o.data_insert,
    o.user_insert,
    o.data_update,
    o.user_update,
    sd.pdf_mode,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    sd.fase,
    pr.pratica_id,
    pr.pratica_numero,
    pr.n_pratiche,
    dcr.data_consegna_richiesta_cliente_min,
    reg.codice AS registro_codice,
    reg.descrizione AS registro_descrizione,
    o.sorgente_tipo_id,
    o.sorgente_id,
    o.sorgente_uid
   FROM (((((((((((((((((((vendite.ordini o
     JOIN config.stati_doc_ordini sd ON ((sd.id = o.stato_doc_ordine_id)))
     JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = o.soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = o.billing_account_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = o.emittente_fiscale_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = ef.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN config.utilities u ON ((u.id = o.utility_id)))
     LEFT JOIN config.modalita_pagamento mp ON ((mp.id = o.modalita_pagamento_id)))
     LEFT JOIN config.termini_pagamento tp ON ((tp.id = o.termine_pagamento_id)))
     LEFT JOIN config.valute v_val ON ((v_val.id = o.valuta_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ag ON ((sr_ag.id = o.agente_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ag ON ((s_ag.id = sr_ag.soggetto_id)))
     LEFT JOIN config.sorgenti so_or ON ((so_or.id = o.sorgente_tipo_id)))
     LEFT JOIN vendite.preventivi pv ON ((((so_or.codice_interno)::text = 'PREVENTIVO'::text) AND ((pv.id = o.sorgente_id) OR (pv.uid = o.sorgente_uid)))))
     LEFT JOIN vendite.offerte_commerciali oc ON ((((so_or.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND ((oc.id = o.sorgente_id) OR (oc.uid = o.sorgente_uid)))))
     LEFT JOIN LATERAL pratiche.fn_pratica_del_documento(( SELECT so_pr.id
           FROM config.sorgenti so_pr
          WHERE (((so_pr.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (so_pr.attivo IS TRUE))), o.id, o.uid) pr(n_pratiche, pratica_id, pratica_numero) ON (true))
     LEFT JOIN LATERAL ( SELECT min(orr.data_consegna_richiesta_cliente) AS data_consegna_richiesta_cliente_min
           FROM vendite.ordini_righe orr
          WHERE ((orr.ordine_id = o.id) AND (orr.attivo IS TRUE))) dcr ON (true))
     LEFT JOIN vendite.registri_fatturazione reg ON ((reg.id = o.registro_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
