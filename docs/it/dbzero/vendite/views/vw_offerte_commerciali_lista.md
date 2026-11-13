{% include-markdown "it/dbzero/vendite/manual/vw_offerte_commerciali_lista.md" %}
# 🔍 View `vw_offerte_commerciali_lista`

> 📝 **Descrizione**
>
> Vista flat canonica e self-contained delle offerte commerciali, per la lista configurabile (vendite.offerte). Nomi canonici (ragione_sociale_completa, id_fiscale_univoco_cf_piva, ba_codice); listino_codice, listino_versione_codice e valuta_codice gia' risolti. Pura denormalizzazione: nessuno scope e nessun filtro, security_invoker=on (la RLS dell'offerta si applica attraverso la vista). Gli stati si leggono per significato dal vocabolario config.stati_doc_offerte: is_superata (is_superato, rimpiazzata da una revisione successiva), is_abortito (annullata), is_attiva = NOT is_superata AND NOT is_abortito; «solo l'ultima revisione» si chiede a is_superata IS FALSE. is_scaduta: la validita' (validita_al) e' passata rispetto alla data operativa dell'azienda (script.fn_data_operativa) e il cliente non ha ancora risposto, cioe' lo stato non ha un esito; un'offerta accettata, rifiutata, superata o annullata non e' scaduta. has_next_revisione: esiste una revisione figlia, in qualunque stato. La pratica viene da pratiche.fn_pratica_del_documento; le colonne del grafo del lineage le legge il backend da vendite.fn_documento_lineage_sintesi.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_offerte_commerciali_lista
WITH (security_invoker=on) AS
SELECT o.id,
    o.uid,
    o.codice,
    o.revisione_numero,
    o.revisione_padre_id,
    ((NOT sdo.is_superato) AND (NOT sdo.is_abortito)) AS is_attiva,
    (EXISTS ( SELECT 1
           FROM vendite.offerte_commerciali figlio
          WHERE (figlio.revisione_padre_id = o.id))) AS has_next_revisione,
    o.stato_doc_offerta_id,
    sdo.codice_interno AS stato_codice_interno,
    sdo.descrizione AS stato_descrizione,
    o.billing_account_id,
    ba.codice AS ba_codice,
    s.id AS soggetto_id,
    s.ragione_sociale_completa,
    s.id_fiscale_univoco_cf_piva,
    o.emittente_fiscale_id,
    ef.codice AS emittente_fiscale_codice,
    o.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    o.istanza_utility_id,
    iu.codice AS istanza_utility_codice,
    o.listino_id,
    l.codice AS listino_codice,
    o.listino_versione_id,
    lv.codice_versione AS listino_versione_codice,
    o.tipo_variazione_globale,
    o.valore_variazione_globale,
    o.valuta_id,
    v_val.codice AS valuta_codice,
    o.validita_dal,
    o.validita_al,
    ((sdo.esito IS NULL) AND (o.validita_al IS NOT NULL) AND (o.validita_al < ( SELECT script.fn_data_operativa() AS fn_data_operativa))) AS is_scaduta,
    o.data_emissione,
    o.data_accettazione,
    o.data_rifiuto,
    o.data_annullamento,
    o.data_insert,
    o.user_insert,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    sdo.fase,
    pr.pratica_id,
    pr.pratica_numero,
    pr.n_pratiche,
    sdo.is_superato AS is_superata,
    sdo.is_abortito,
    o.revisione_radice_id
   FROM ((((((((((((vendite.offerte_commerciali o
     JOIN config.stati_doc_offerte sdo ON ((sdo.id = o.stato_doc_offerta_id)))
     LEFT JOIN anagrafiche.istanze_utilities iu ON ((iu.id = o.istanza_utility_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = iu.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = o.billing_account_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = o.emittente_fiscale_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = ef.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN config.utilities u ON ((u.id = o.utility_id)))
     LEFT JOIN vendite.listini l ON ((l.id = o.listino_id)))
     LEFT JOIN vendite.listini_versioni lv ON ((lv.id = o.listino_versione_id)))
     LEFT JOIN config.valute v_val ON ((v_val.id = o.valuta_id)))
     LEFT JOIN LATERAL pratiche.fn_pratica_del_documento(( SELECT so_pr.id
           FROM config.sorgenti so_pr
          WHERE (((so_pr.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (so_pr.attivo IS TRUE))), o.id, o.uid) pr(n_pratiche, pratica_id, pratica_numero) ON (true));
```

</div>


---
{% include-markdown "signature-core.md" %}
