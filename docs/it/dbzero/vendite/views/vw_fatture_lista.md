# 🔍 View `vw_fatture_lista`

> 📝 **Descrizione**
>
> Vista flat canonica e self-contained delle fatture di vendita per la lista UI — la settima sorella di vw_contratti/ddt/offerte_commerciali/ordini/preventivi/resi_lista, e l'ultimo documento del ciclo attivo che ne era privo. Nomi canonici gia' noti al frontend: stato_codice_interno/stato_descrizione, ragione_sociale_completa, id_fiscale_univoco_cf_piva, ba_codice, utility_codice/utility_descrizione, emittente_ragione_sociale, soggetto_id. Cliente risolto via billing_account -&gt; soggetto_ruolo -&gt; soggetto (la fattura non porta un soggetto_ruolo cliente). emittente_fiscale_id DERIVATO da anagrafiche.emittenti_fiscali.soggetto_ruolo_id, che ha un vincolo di unicita' (uq_emittenti_fiscali_ruolo): il join non moltiplica le righe. Importi coi nomi della tabella (imponibile_tot, imposta_tot, totale_doc, totale_a_pagare) perche' fra le sorelle quel nome NON e' canonico. ⛔ security_invoker=on: vendite.fatture ha la RLS (rls_fatture_ef_whitelist per l'operatore, rls_fatture_ba_ownership per il portale) ed e' quella a dover mordere — la vista non filtra e non fa scope, denormalizza soltanto. ⛔ UN SOLO join interno, config.nature_doc_fiscale, e solo perche' natura_doc_id e' NOT NULL con FK; tutto il resto e' LEFT. In particolare anagrafiche.billing_account, che ha una RLS propria risolta da fn_scope_ef_whitelist_via_efba mentre la fattura usa fn_scope_ef_whitelist_via_sr: le due derivazioni del perimetro possono divergere, e un inner join farebbe sparire dalla lista una fattura che la sua policy lascia passare — una lista che mostra meno del dovuto senza nessun segnale. Le colonne nullable (stato/tipo/utility/valuta) sono LEFT per la stessa ragione di forma: una fattura senza stato deve comparire senza stato, non sparire. Bozze incluse: numero/serie/anno sono NULL finche' il documento non e' numerato. Genealogia da vendite.vw_documento_lineage (18 righe su 18 fatture, misurate): n_discendenti_attivi e is_transitato sono zero per costruzione perche' la fattura e' terminale. NON contiene il lotto di appartenenza: questa lista esiste per raggiungere la fattura SENZA passare dal lotto. Seed lista: ui.lista_definizione 'vendite.fatture' (attivo = f finche' il backend non espone l'endpoint). Registro: docs/it/dev/work-in-progress/piano-migrazione-primevue-5.md §9, 2026-08-24.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

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
    tdf.codice_interno AS tipo_doc_fiscale_codice,
    tdf.descrizione AS tipo_doc_fiscale_descrizione,
    f.natura_doc_id,
    ndf.codice_interno AS natura_doc_codice,
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
    lin.pratica_id,
    lin.pratica_numero,
    lin.n_pratiche,
    lin.frontiera_tipo_id,
    lin.frontiera_codice,
    lin.frontiera_stato_codice_interno,
    lin.frontiera_fase,
    lin.n_discendenti_attivi,
    lin.is_transitato
   FROM (((((((((((((vendite.fatture f
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
     LEFT JOIN vendite.vw_documento_lineage lin ON (((lin.tipo_id = ( SELECT s.id
           FROM config.sorgenti s
          WHERE (((s.codice_interno)::text = 'FATTURA'::text) AND (s.attivo IS TRUE)))) AND (lin.uid = (f.id)::text))));
```


---
{% include-markdown "signature-core.md" %}
