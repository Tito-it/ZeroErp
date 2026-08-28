{% include-markdown "it/dbzero/vendite/manual/vw_offerte_commerciali_lista.md" %}
# 🔍 View `vw_offerte_commerciali_lista`

> 📝 **Descrizione**
>
> Vista flat canonica e self-contained offerte commerciali per la lista UI configurabile (vendite.offerte). Nomi canonici (ragione_sociale_completa, id_fiscale_univoco_cf_piva, ba_codice). Assorbe listino_codice/listino_versione_codice/valuta_codice e materializza is_scaduta (validita_al scaduta; gating per stato lato FE). Pura denormalizzazione: nessuno scope/filtro. security_invoker=on (RLS-ready). Dal 2026-08-28 le due domande sono colonne distinte: is_superata (= stati_doc_offerte.is_superato, rimpiazzata da una revisione successiva) e is_abortito (= stati_doc_offerte.is_abortito, annullata); is_attiva = NOT is_superata AND NOT is_abortito — stessi valori del precedente letterale NOT IN ('SUPERATA','ANNULLATA'), ora scritti sul catalogo. «Solo l'ultima revisione» si chiede a is_superata IS FALSE. has_next_revisione = EXISTS figlio (qualunque stato).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

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
    ((o.validita_al IS NOT NULL) AND (o.validita_al < CURRENT_DATE)) AS is_scaduta,
    o.data_emissione,
    o.data_accettazione,
    o.data_rifiuto,
    o.data_annullamento,
    o.data_insert,
    o.user_insert,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    sdo.fase,
    lin.pratica_id,
    lin.pratica_numero,
    lin.n_pratiche,
    lin.frontiera_tipo_id,
    lin.frontiera_codice,
    lin.frontiera_stato_codice_interno,
    lin.frontiera_fase,
    lin.n_discendenti_attivi,
    lin.is_transitato,
    sdo.is_superato AS is_superata,
    sdo.is_abortito
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
     LEFT JOIN vendite.vw_documento_lineage lin ON (((lin.tipo_id = ( SELECT sorgenti.id
           FROM config.sorgenti
          WHERE (((sorgenti.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (sorgenti.attivo IS TRUE)))) AND (lin.uid = (o.uid)::text))));
```


---
{% include-markdown "signature-core.md" %}
