{% include-markdown "it/dbzero/script/manual/vw_stato_sorgente.md" %}
# 🔍 View `vw_stato_sorgente`

> 📝 **Descrizione**
>
> Lo stato di un documento nel vocabolario comune (fase, esito, terminale): la union dei resolver di dominio, al piu' una riga per documento. Sei rami, uno per tipo: vendite.vw_stato_sorgente_preventivo, _offerta, _ordine, _contratto, _ddt e _reso; ogni ramo trova il suo tipo per codice in config.sorgenti. Un tipo senza ramo non ha righe: l'assenza della riga e' il «non risolto», e risolto e' sempre true. La chiave del documento sta in tre colonne: sorgente_chiave_uuid, valorizzata nei rami a key_selector uid; sorgente_chiave_id, nei rami a key_selector id; sorgente_uid, la stessa chiave in testo nella forma canonica (uid::text o id::text). Si cerca sulle chiavi native, un ramo per chiave e non con un OR (l'OR non scende nei rami della union): uuid_eq e int8eq sono leakproof, quindi sotto RLS la chiave arriva all'Index Cond di ogni ramo, e il ramo dell'altra specie, con la colonna NULL costante, il planner lo scarta. Il confronto su sorgente_uid invece non arriva mai all'indice (uuid_out e int8out non sono leakproof) e legge per intero tutte le tabelle dei documenti. Cosi' la leggono pratiche.fn_stato_sorgente, script.vw_pratica_doc_sorgente e script.vw_flusso_doc_sorgente. Un ramo nuovo ha le stesse colonne e valorizza la colonna nativa della sua specie, o nessun lettore lo trova (pgTAP vendite/test-vw-stato-sorgente-ddt-reso-v1). security_invoker.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_stato_sorgente
WITH (security_invoker=on) AS
SELECT r.sorgente_tipo_id,
    r.sorgente_uid,
    true AS risolto,
    (r.stato_codice_interno)::text AS stato_codice_interno,
    (r.stato_codice)::text AS stato_codice,
    (r.stato_descrizione)::text AS stato_descrizione,
    (r.fase)::text AS fase,
    (r.esito)::text AS esito,
    r.terminale,
    r.sorgente_chiave_uuid,
    r.sorgente_chiave_id
   FROM vendite.vw_stato_sorgente_preventivo r
UNION ALL
 SELECT r.sorgente_tipo_id,
    r.sorgente_uid,
    true AS risolto,
    (r.stato_codice_interno)::text AS stato_codice_interno,
    (r.stato_codice)::text AS stato_codice,
    (r.stato_descrizione)::text AS stato_descrizione,
    (r.fase)::text AS fase,
    (r.esito)::text AS esito,
    r.terminale,
    r.sorgente_chiave_uuid,
    r.sorgente_chiave_id
   FROM vendite.vw_stato_sorgente_offerta r
UNION ALL
 SELECT r.sorgente_tipo_id,
    r.sorgente_uid,
    true AS risolto,
    (r.stato_codice_interno)::text AS stato_codice_interno,
    (r.stato_codice)::text AS stato_codice,
    (r.stato_descrizione)::text AS stato_descrizione,
    (r.fase)::text AS fase,
    (r.esito)::text AS esito,
    r.terminale,
    r.sorgente_chiave_uuid,
    r.sorgente_chiave_id
   FROM vendite.vw_stato_sorgente_ordine r
UNION ALL
 SELECT r.sorgente_tipo_id,
    r.sorgente_uid,
    true AS risolto,
    (r.stato_codice_interno)::text AS stato_codice_interno,
    (r.stato_codice)::text AS stato_codice,
    (r.stato_descrizione)::text AS stato_descrizione,
    (r.fase)::text AS fase,
    (r.esito)::text AS esito,
    r.terminale,
    r.sorgente_chiave_uuid,
    r.sorgente_chiave_id
   FROM vendite.vw_stato_sorgente_contratto r
UNION ALL
 SELECT r.sorgente_tipo_id,
    r.sorgente_uid,
    true AS risolto,
    (r.stato_codice_interno)::text AS stato_codice_interno,
    (r.stato_codice)::text AS stato_codice,
    (r.stato_descrizione)::text AS stato_descrizione,
    (r.fase)::text AS fase,
    (r.esito)::text AS esito,
    r.terminale,
    r.sorgente_chiave_uuid,
    r.sorgente_chiave_id
   FROM vendite.vw_stato_sorgente_ddt r
UNION ALL
 SELECT r.sorgente_tipo_id,
    r.sorgente_uid,
    true AS risolto,
    (r.stato_codice_interno)::text AS stato_codice_interno,
    (r.stato_codice)::text AS stato_codice,
    (r.stato_descrizione)::text AS stato_descrizione,
    (r.fase)::text AS fase,
    (r.esito)::text AS esito,
    r.terminale,
    r.sorgente_chiave_uuid,
    r.sorgente_chiave_id
   FROM vendite.vw_stato_sorgente_reso r;
```

</div>


---
{% include-markdown "signature-core.md" %}
