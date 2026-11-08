{% include-markdown "it/dbzero/vendite/manual/vw_contratti_lista.md" %}
# 🔍 View `vw_contratti_lista`

> 📝 **Descrizione**
>
> Vista flat dei contratti per la lista UI configurabile vendite.contratti (ui.lista_definizione): cliente (billing account e soggetto), emittente fiscale con la ragione sociale, utility, stato con la sua fase, listino e versione, variazione globale, categoria cliente dallo snapshot del contratto (non quella corrente del billing account), valuta, audit e la pratica del contratto. Pura denormalizzazione: nessun filtro, scope, ordinamento o paginazione propri, che restano al repository consumer. security_invoker: vale la RLS di chi legge; billing account, soggetto, utility e stato sono JOIN interni, quindi un contratto col billing account fuori perimetro non compare, mentre emittente, listino, versione, categoria e valuta sono LEFT JOIN e lasciano NULL. stato_codice_interno = codice_interno (logica), stato_codice = codice (display). pratica_id, pratica_numero e n_pratiche vengono da pratiche.fn_pratica_del_documento, col tipo CONTRATTO (da config.sorgenti per codice_interno, solo se attivo) e le due chiavi del contratto, id e uid. Le colonne del grafo (frontiera, discendenti, transito) non sono nella vista: il backend le chiede a vendite.fn_documento_lineage_sintesi per i contratti della pagina.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

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
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    sd.fase,
    pr.pratica_id,
    pr.pratica_numero,
    pr.n_pratiche
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
     LEFT JOIN LATERAL pratiche.fn_pratica_del_documento(( SELECT so_pr.id
           FROM config.sorgenti so_pr
          WHERE (((so_pr.codice_interno)::text = 'CONTRATTO'::text) AND (so_pr.attivo IS TRUE))), c.id, c.uid) pr(n_pratiche, pratica_id, pratica_numero) ON (true));
```

</div>


---
{% include-markdown "signature-core.md" %}
