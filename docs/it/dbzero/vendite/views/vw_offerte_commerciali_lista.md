{% include-markdown "it/dbzero/vendite/manual/vw_offerte_commerciali_lista.md" %}
# 🔍 View `vw_offerte_commerciali_lista`

> 📝 **Descrizione**
>
> ⭐ rev 2026-10-11 (20261011-97, brief-db-lineage-seminata-per-chiave giro B): la vista non aggancia piu' vw_documento_lineage. Le 8 colonne del grafo (frontiera_*, n_discendenti_attivi, is_transitato) le legge il backend da vendite.fn_documento_lineage_sintesi per le chiavi della pagina; la pratica resta, da pratiche.fn_pratica_del_documento. Vista flat canonica e self-contained offerte commerciali per la lista UI configurabile (vendite.offerte). Nomi canonici (ragione_sociale_completa, id_fiscale_univoco_cf_piva, ba_codice). Assorbe listino_codice/listino_versione_codice/valuta_codice e materializza is_scaduta (validita_al scaduta; gating per stato lato FE). Pura denormalizzazione: nessuno scope/filtro. security_invoker=on (RLS-ready). Dal 2026-08-28 le due domande sono colonne distinte: is_superata (= stati_doc_offerte.is_superato, rimpiazzata da una revisione successiva) e is_abortito (= stati_doc_offerte.is_abortito, annullata); is_attiva = NOT is_superata AND NOT is_abortito — stessi valori del precedente letterale NOT IN ('SUPERATA','ANNULLATA'), ora scritti sul catalogo. «Solo l'ultima revisione» si chiede a is_superata IS FALSE. has_next_revisione = EXISTS figlio (qualunque stato). ⭐ rev 2026-08-29 — porta avanti anche frontiera_natura_doc_codice da vendite.vw_documento_lineage, accanto alle altre quattro frontiera_*. Senza, il chip «Transito» decodifica il solo tipo e chiama «Fattura» una nota di credito: vendite.fatture e' UNA tabella, e la chiave del nodo di frontiera (frontiera_uid) da questa vista non esce, quindi il consumatore non ha modo onesto di ricavarsela. ⚠️ La colonna e' in ULTIMA posizione perche' CREATE OR REPLACE VIEW puo' solo appendere: non e' un disordine da sistemare. ⛔ NULL non significa «non lo so» ma «la frontiera non e' un documento fiscale»: la natura esiste solo per le fatture. ⛔ rev 2026-08-29 — BONIFICA NAMING §6c + il CODICE DEL TIPO. (1) `frontiera_natura_doc_codice` si chiama ora `frontiera_natura_doc_codice_interno`: il valore viene da `config.nature_doc_fiscale.codice_interno`, che e' la colonna IMMUTABILE, e linee-guida-sql §6c vieta `codice_interno AS *_codice` perche' il nome mentirebbe sulla sorgente — un consumatore che confronta contro un `*_codice` si aspetta la colonna MUTABILE. Il guardrail CI scripts/sql/check_naming_stato_codice.sql fallisce sul pattern. (2) arriva `frontiera_tipo_codice_interno`, il CODICE del tipo accanto al suo id: prima ogni consumatore se lo traduceva con lo stesso join a config.sorgenti — dieci copie scritte a mano nel backend, tutte fuori dalla portata del guardrail, che scansiona solo le viste. ⚠️ Il nome NON e' `frontiera_tipo_codice`: quel valore e' `config.sorgenti.codice_interno` e il FE lo usa per la chiave i18n e per instradare, cioe' come LOGICA. Chiamarlo `*_codice` avrebbe spostato dieci mislabel nascosti dentro l'unico posto dove il guardrail li vede.

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
    ((o.validita_al IS NOT NULL) AND (o.validita_al < ( SELECT script.fn_data_operativa() AS fn_data_operativa))) AS is_scaduta,
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
          WHERE (((so_pr.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (so_pr.attivo IS TRUE))), (o.uid)::text) pr(n_pratiche, pratica_id, pratica_numero) ON (true));
```

</div>


---
{% include-markdown "signature-core.md" %}
