# 🔍 View `vw_fatture_lista`

> 📝 **Descrizione**
>
> ⭐ rev 2026-10-11 (20261011-97, brief-db-lineage-seminata-per-chiave giro B): la vista non aggancia piu' vw_documento_lineage. Le 8 colonne del grafo (frontiera_*, n_discendenti_attivi, is_transitato) le legge il backend da vendite.fn_documento_lineage_sintesi per le chiavi della pagina; la pratica resta, da pratiche.fn_pratica_del_documento. Vista flat canonica e self-contained delle fatture di vendita per la lista UI — la settima sorella di vw_contratti/ddt/offerte_commerciali/ordini/preventivi/resi_lista, e l'ultimo documento del ciclo attivo che ne era privo. Nomi canonici gia' noti al frontend: stato_codice_interno/stato_descrizione, ragione_sociale_completa, id_fiscale_univoco_cf_piva, ba_codice, utility_codice/utility_descrizione, emittente_ragione_sociale, soggetto_id. Cliente risolto via billing_account -&gt; soggetto_ruolo -&gt; soggetto (la fattura non porta un soggetto_ruolo cliente). emittente_fiscale_id DERIVATO da anagrafiche.emittenti_fiscali.soggetto_ruolo_id, che ha un vincolo di unicita' (uq_emittenti_fiscali_ruolo): il join non moltiplica le righe. Importi coi nomi della tabella (imponibile_tot, imposta_tot, totale_doc, totale_a_pagare) perche' fra le sorelle quel nome NON e' canonico. ⛔ security_invoker=on: vendite.fatture ha la RLS (rls_fatture_ef_whitelist per l'operatore, rls_fatture_ba_ownership per il portale) ed e' quella a dover mordere — la vista non filtra e non fa scope, denormalizza soltanto. ⛔ UN SOLO join interno, config.nature_doc_fiscale, e solo perche' natura_doc_id e' NOT NULL con FK; tutto il resto e' LEFT. In particolare anagrafiche.billing_account, che ha una RLS propria risolta da fn_scope_ef_whitelist_via_efba mentre la fattura usa fn_scope_ef_whitelist_via_sr: le due derivazioni del perimetro possono divergere, e un inner join farebbe sparire dalla lista una fattura che la sua policy lascia passare — una lista che mostra meno del dovuto senza nessun segnale. Le colonne nullable (stato/tipo/utility/valuta) sono LEFT per la stessa ragione di forma: una fattura senza stato deve comparire senza stato, non sparire. Bozze incluse: numero/serie/anno sono NULL finche' il documento non e' numerato. Genealogia da vendite.vw_documento_lineage (18 righe su 18 fatture, misurate): n_discendenti_attivi e is_transitato sono zero per costruzione perche' la fattura e' terminale. NON contiene il lotto di appartenenza: questa lista esiste per raggiungere la fattura SENZA passare dal lotto. Seed lista: ui.lista_definizione 'vendite.fatture' (attivo = f finche' il backend non espone l'endpoint). Registro: piano-migrazione-primevue-5.md §9, 2026-08-24. ⭐ rev 2026-08-29 — porta avanti anche frontiera_natura_doc_codice da vendite.vw_documento_lineage, accanto alle altre quattro frontiera_*. Senza, il chip «Transito» decodifica il solo tipo e chiama «Fattura» una nota di credito: vendite.fatture e' UNA tabella, e la chiave del nodo di frontiera (frontiera_uid) da questa vista non esce, quindi il consumatore non ha modo onesto di ricavarsela. ⚠️ La colonna e' in ULTIMA posizione perche' CREATE OR REPLACE VIEW puo' solo appendere: non e' un disordine da sistemare. ⛔ NULL non significa «non lo so» ma «la frontiera non e' un documento fiscale»: la natura esiste solo per le fatture. ⚠️ SU QUESTA VISTA LA COLONNA E' COSTANTE, ed e' bene saperlo prima di leggerla: una fattura e' sempre frontiera di SE STESSA (nel grafo forward non ha archi uscenti — l'arco N e' un ramo di ritorno; lo asserisce il pgTAP 30 di test-documento-lineage-v1.sql), quindi frontiera_natura_doc_codice qui vale SEMPRE la natura della riga stessa. C'e' lo stesso, e per una ragione di forma e non di dato: le sette liste sorelle devono esporre lo STESSO blocco frontiera_*, altrimenti chi scrive l'ottava copia da quella sbagliata. ⛔ E chi un giorno montasse la colonna «Transito» qui sappia che renderebbe il documento su se stesso: non un'etichetta sbagliata, un chip che non dice niente. ⛔ rev 2026-08-29 — BONIFICA NAMING §6c + il CODICE DEL TIPO. (1) `frontiera_natura_doc_codice` si chiama ora `frontiera_natura_doc_codice_interno`: il valore viene da `config.nature_doc_fiscale.codice_interno`, che e' la colonna IMMUTABILE, e linee-guida-sql §6c vieta `codice_interno AS *_codice` perche' il nome mentirebbe sulla sorgente — un consumatore che confronta contro un `*_codice` si aspetta la colonna MUTABILE. Il guardrail CI scripts/sql/check_naming_stato_codice.sql fallisce sul pattern. (2) arriva `frontiera_tipo_codice_interno`, il CODICE del tipo accanto al suo id: prima ogni consumatore se lo traduceva con lo stesso join a config.sorgenti — dieci copie scritte a mano nel backend, tutte fuori dalla portata del guardrail, che scansiona solo le viste. ⚠️ Il nome NON e' `frontiera_tipo_codice`: quel valore e' `config.sorgenti.codice_interno` e il FE lo usa per la chiave i18n e per instradare, cioe' come LOGICA. Chiamarlo `*_codice` avrebbe spostato dieci mislabel nascosti dentro l'unico posto dove il guardrail li vede. ⭐ rev 2026-09-17 (brief-db-distinta-ricerca-rate §4-bis.2, P-1): + numero_documento, registro_codice, registro_descrizione in coda. numero_documento e' vendite.fn_numero_documento_fattura(numero, serie), la SEDE UNICA del numero parlante («numero - serie», NULL sulla non numerata, mai la stringa vuota): la lista deve portarlo perche' il FE non compone — un contatore nudo e' ambiguo per costruzione (una fattura 1 e una nota di credito 1 nello stesso anno). Il registro e' LEFT: una bozza puo' non averlo e deve comparire senza, non sparire. Consumatori: il lookup fattura degli incassi (tre superfici) e la lista vendite.fatture, che leggono SELECT v.*. Lo stesso blocco registro_* va in coda anche a vw_ddt_lista, vw_ordini_lista e vw_resi_lista (Q-E): contratti, preventivi e offerte un registro non ce l'hanno, e non lo avranno. Rev 2026-10-20 (20261020-77, brief-db-grammatica-unica-documenti L2c-1): ricreata identica dopo l'allargamento di registri_fatturazione.codice a varchar(80) (20261020-74).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_fatture_lista
WITH (security_invoker=on) AS
SELECT f.id,
    f.uid,
    f.numero,
    f.serie,
    f.anno,
    f.data,
    f.registro_id,
    f.stato_doc_fiscale_id,
    sdf.codice_interno AS stato_codice_interno,
    sdf.descrizione AS stato_descrizione,
    sdf.fase,
    f.tipo_doc_fiscale_id,
    tdf.codice_interno AS tipo_doc_fiscale_codice_interno,
    tdf.descrizione AS tipo_doc_fiscale_descrizione,
    f.natura_doc_id,
    ndf.codice_interno AS natura_doc_codice_interno,
    ndf.descrizione AS natura_doc_descrizione,
    f.billing_account_id,
    ba.codice AS ba_codice,
    s_cli.id AS soggetto_id,
    s_cli.ragione_sociale_completa,
    s_cli.id_fiscale_univoco_cf_piva,
    f.emittente_soggetto_ruolo_id,
    ef.id AS emittente_fiscale_id,
    ef.codice AS emittente_fiscale_codice,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    f.utility_id,
    u.codice AS utility_codice,
    u.descrizione AS utility_descrizione,
    f.valuta_id,
    v_val.codice AS valuta_codice,
    f.imponibile_tot,
    f.imposta_tot,
    f.totale_doc,
    f.totale_a_pagare,
    f.sorgente_tipo_id,
    src.codice_interno AS sorgente_codice_interno,
    f.sorgente_uid,
    f.data_insert,
    f.user_insert,
    f.data_update,
    f.user_update,
    pr.pratica_id,
    pr.pratica_numero,
    pr.n_pratiche,
    vendite.fn_numero_documento_fattura(f.numero, f.serie) AS numero_documento,
    reg.codice AS registro_codice,
    reg.descrizione AS registro_descrizione
   FROM ((((((((((((((vendite.fatture f
     JOIN config.nature_doc_fiscale ndf ON ((ndf.id = f.natura_doc_id)))
     LEFT JOIN config.stati_doc_fiscale sdf ON ((sdf.id = f.stato_doc_fiscale_id)))
     LEFT JOIN config.tipi_doc_fiscale tdf ON ((tdf.id = f.tipo_doc_fiscale_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = f.billing_account_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_cli ON ((sr_cli.id = ba.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_cli ON ((s_cli.id = sr_cli.soggetto_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = f.emittente_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN config.utilities u ON ((u.id = f.utility_id)))
     LEFT JOIN config.valute v_val ON ((v_val.id = f.valuta_id)))
     LEFT JOIN config.sorgenti src ON ((src.id = f.sorgente_tipo_id)))
     LEFT JOIN LATERAL pratiche.fn_pratica_del_documento(( SELECT so_pr.id
           FROM config.sorgenti so_pr
          WHERE (((so_pr.codice_interno)::text = 'FATTURA'::text) AND (so_pr.attivo IS TRUE))), (f.id)::text) pr(n_pratiche, pratica_id, pratica_numero) ON (true))
     LEFT JOIN vendite.registri_fatturazione reg ON ((reg.id = f.registro_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
