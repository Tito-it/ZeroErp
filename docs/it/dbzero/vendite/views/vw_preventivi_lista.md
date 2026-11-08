{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_lista.md" %}
# 🔍 View `vw_preventivi_lista`

> 📝 **Descrizione**
>
> ⭐ rev 2026-10-11 (20261011-97, brief-db-lineage-seminata-per-chiave giro B): la vista non aggancia piu' vw_documento_lineage. Le 8 colonne del grafo (frontiera_*, n_discendenti_attivi, is_transitato) le legge il backend da vendite.fn_documento_lineage_sintesi per le chiavi della pagina; la pratica resta, da pratiche.fn_pratica_del_documento. Vista flat canonica preventivi per la lista UI configurabile (vendite.preventivi). Nomi canonici (ragione_sociale_completa, id_fiscale_univoco_cf_piva, ba_codice, is_attiva). Dal 2026-08-28 espone anche le DUE componenti di is_attiva come colonne proprie: is_superata (rimpiazzata da una rev superiore viva — il complemento e' «e' l'ultima revisione») e is_abortito (annullato), piu' has_next_revisione. Il toggle «Mostra storico revisioni» si scrive is_superata IS FALSE: is_attiva nasconde anche gli annullati e rende vuoto per costruzione il filtro di stato «Annullato». Pura denormalizzazione: nessuno scope/filtro/paginazione (restano nel repository consumer). security_invoker=on (RLS-ready). Soggetto via istanze_utilities (1 join, valorizzato anche per prospect). ⭐ rev 2026-08-29 — porta avanti anche frontiera_natura_doc_codice da vendite.vw_documento_lineage, accanto alle altre quattro frontiera_*. Senza, il chip «Transito» decodifica il solo tipo e chiama «Fattura» una nota di credito: vendite.fatture e' UNA tabella, e la chiave del nodo di frontiera (frontiera_uid) da questa vista non esce, quindi il consumatore non ha modo onesto di ricavarsela. ⚠️ La colonna e' in ULTIMA posizione perche' CREATE OR REPLACE VIEW puo' solo appendere: non e' un disordine da sistemare. ⛔ NULL non significa «non lo so» ma «la frontiera non e' un documento fiscale»: la natura esiste solo per le fatture. ⛔ rev 2026-08-29 — BONIFICA NAMING §6c + il CODICE DEL TIPO. (1) `frontiera_natura_doc_codice` si chiama ora `frontiera_natura_doc_codice_interno`: il valore viene da `config.nature_doc_fiscale.codice_interno`, che e' la colonna IMMUTABILE, e linee-guida-sql §6c vieta `codice_interno AS *_codice` perche' il nome mentirebbe sulla sorgente — un consumatore che confronta contro un `*_codice` si aspetta la colonna MUTABILE. Il guardrail CI scripts/sql/check_naming_stato_codice.sql fallisce sul pattern. (2) arriva `frontiera_tipo_codice_interno`, il CODICE del tipo accanto al suo id: prima ogni consumatore se lo traduceva con lo stesso join a config.sorgenti — dieci copie scritte a mano nel backend, tutte fuori dalla portata del guardrail, che scansiona solo le viste. ⚠️ Il nome NON e' `frontiera_tipo_codice`: quel valore e' `config.sorgenti.codice_interno` e il FE lo usa per la chiave i18n e per instradare, cioe' come LOGICA. Chiamarlo `*_codice` avrebbe spostato dieci mislabel nascosti dentro l'unico posto dove il guardrail li vede.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

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
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    sdp.fase,
    pr.pratica_id,
    pr.pratica_numero,
    pr.n_pratiche,
    p.is_superata,
    p.is_abortito,
    p.has_next_revisione
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
     LEFT JOIN LATERAL pratiche.fn_pratica_del_documento(( SELECT so_pr.id
           FROM config.sorgenti so_pr
          WHERE (((so_pr.codice_interno)::text = 'PREVENTIVO'::text) AND (so_pr.attivo IS TRUE))), p.id, p.uid) pr(n_pratiche, pratica_id, pratica_numero) ON (true));
```

</div>


---
{% include-markdown "signature-core.md" %}
