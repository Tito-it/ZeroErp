{% include-markdown "it/dbzero/vendite/manual/vw_contratti_lista.md" %}
# 🔍 View `vw_contratti_lista`

> 📝 **Descrizione**
>
> ⭐ rev 2026-10-11 (20261011-97, brief-db-lineage-seminata-per-chiave giro B): la vista non aggancia piu' vw_documento_lineage. Le 8 colonne del grafo (frontiera_*, n_discendenti_attivi, is_transitato) le legge il backend da vendite.fn_documento_lineage_sintesi per le chiavi della pagina; la pratica resta, da pratiche.fn_pratica_del_documento. Vista flat contratti per la lista UI configurabile (vendite.contratti). Pura denormalizzazione: nessuno scope/filtro/paginazione (restano nel repository consumer). security_invoker=on per rispettare la RLS della tabella base. stato_codice_interno = codice_interno (logica/severity), stato_codice = codice (display). Sorgente dati per ui.lista_definizione codice='vendite.contratti'. ⭐ rev 2026-08-29 — porta avanti anche frontiera_natura_doc_codice da vendite.vw_documento_lineage, accanto alle altre quattro frontiera_*. Senza, il chip «Transito» decodifica il solo tipo e chiama «Fattura» una nota di credito: vendite.fatture e' UNA tabella, e la chiave del nodo di frontiera (frontiera_uid) da questa vista non esce, quindi il consumatore non ha modo onesto di ricavarsela. ⚠️ La colonna e' in ULTIMA posizione perche' CREATE OR REPLACE VIEW puo' solo appendere: non e' un disordine da sistemare. ⛔ NULL non significa «non lo so» ma «la frontiera non e' un documento fiscale»: la natura esiste solo per le fatture. ⛔ rev 2026-08-29 — BONIFICA NAMING §6c + il CODICE DEL TIPO. (1) `frontiera_natura_doc_codice` si chiama ora `frontiera_natura_doc_codice_interno`: il valore viene da `config.nature_doc_fiscale.codice_interno`, che e' la colonna IMMUTABILE, e linee-guida-sql §6c vieta `codice_interno AS *_codice` perche' il nome mentirebbe sulla sorgente — un consumatore che confronta contro un `*_codice` si aspetta la colonna MUTABILE. Il guardrail CI scripts/sql/check_naming_stato_codice.sql fallisce sul pattern. (2) arriva `frontiera_tipo_codice_interno`, il CODICE del tipo accanto al suo id: prima ogni consumatore se lo traduceva con lo stesso join a config.sorgenti — dieci copie scritte a mano nel backend, tutte fuori dalla portata del guardrail, che scansiona solo le viste. ⚠️ Il nome NON e' `frontiera_tipo_codice`: quel valore e' `config.sorgenti.codice_interno` e il FE lo usa per la chiave i18n e per instradare, cioe' come LOGICA. Chiamarlo `*_codice` avrebbe spostato dieci mislabel nascosti dentro l'unico posto dove il guardrail li vede.

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
