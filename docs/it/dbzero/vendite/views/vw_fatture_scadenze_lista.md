{% include-markdown "it/dbzero/vendite/manual/vw_fatture_scadenze_lista.md" %}
# 🔍 View `vw_fatture_scadenze_lista`

> 📝 **Descrizione**
>
> Vista d'IDENTITA' delle rate: una riga per rata di vendite.fatture_scadenze col suo documento (numero parlante dalla sede unica fn_numero_documento_fattura, registro, date, natura, tipo, stato, totali, valuta), il cliente e l'emittente denormalizzati. NESSUN SALDO: il residuo e' di pagamenti e vive nel nucleo pagamenti.fn_get_saldi_rate (P-3) — chi legge fa JOIN LATERAL sulla pagina o passa da pagamenti.vw_saldi_rate. ⛔ Niente «scaduta»/«insoluta»: sono derivate dal residuo. ⭐ La chiave si chiama scadenza_id, il vocabolario di pagamenti; `numero` (il contatore) resta accanto a `numero_documento` perche' il picker filtra per numero ESATTO. ⛔ security_invoker=on: la vista non filtra e non fa scope, a mordere e' la RLS di fatture_scadenze (OPERATORE via ef_whitelist e CLIENTE_PORTALE via ba_ownership, entrambe via testata): la stessa vista serve il picker degli incassi, lo scadenzario e il portale. Va RI-SPECIFICATA a ogni CREATE OR REPLACE. ⛔ DUE inner dimostrabili — vendite.fatture (FK NOT NULL, e la policy della rata e' lo stesso EXISTS sulla testata) e config.nature_doc_fiscale (FK NOT NULL) — tutto il resto e' LEFT: una rata su una bozza senza stato, registro o numero compare senza, non sparisce. ⚠️ I JOIN sono SCRITTI e non ereditati da vw_fatture_lista: impilarsi su quella vista trascina la CTE ricorsiva del lineage in ogni lettura delle rate (il planner non rimuove un LEFT JOIN su una vista). Nasce il 2026-09-17 per D19-c (brief-db-distinta-ricerca-rate §4-bis.3, P-2): il picker delle rate della distinta e' il primo consumatore dello scadenzario. Rev 2026-10-20 (20261020-78, brief-db-grammatica-unica-documenti L2c-1): ricreata identica dopo l'allargamento di registri_fatturazione.codice a varchar(80) (20261020-74).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_fatture_scadenze_lista
WITH (security_invoker=on) AS
SELECT sc.id AS scadenza_id,
    sc.fattura_id,
    sc.numero_rata,
    sc.data_scadenza,
    sc.importo,
    f.numero,
    vendite.fn_numero_documento_fattura(f.numero, f.serie) AS numero_documento,
    f.serie,
    f.anno,
    f.data,
    reg.codice AS registro_codice,
    reg.descrizione AS registro_descrizione,
    ndf.codice_interno AS natura_doc_codice_interno,
    ndf.descrizione AS natura_doc_descrizione,
    tdf.codice_interno AS tipo_doc_fiscale_codice_interno,
    tdf.descrizione AS tipo_doc_fiscale_descrizione,
    sdf.codice_interno AS stato_codice_interno,
    sdf.descrizione AS stato_descrizione,
    f.totale_doc,
    f.totale_a_pagare,
    v_val.codice AS valuta_codice,
    f.billing_account_id,
    ba.codice AS ba_codice,
    s_cli.id AS soggetto_id,
    s_cli.ragione_sociale_completa,
    s_cli.id_fiscale_univoco_cf_piva,
    f.emittente_soggetto_ruolo_id,
    ef.id AS emittente_fiscale_id,
    ef.codice AS emittente_fiscale_codice,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale
   FROM ((((((((((((vendite.fatture_scadenze sc
     JOIN vendite.fatture f ON ((f.id = sc.fattura_id)))
     JOIN config.nature_doc_fiscale ndf ON ((ndf.id = f.natura_doc_id)))
     LEFT JOIN config.stati_doc_fiscale sdf ON ((sdf.id = f.stato_doc_fiscale_id)))
     LEFT JOIN config.tipi_doc_fiscale tdf ON ((tdf.id = f.tipo_doc_fiscale_id)))
     LEFT JOIN vendite.registri_fatturazione reg ON ((reg.id = f.registro_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = f.billing_account_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_cli ON ((sr_cli.id = ba.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_cli ON ((s_cli.id = sr_cli.soggetto_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = f.emittente_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)))
     LEFT JOIN config.valute v_val ON ((v_val.id = f.valuta_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
