{% include-markdown "it/dbzero/script/manual/vw_stato_sorgente.md" %}
# 🔍 View `vw_stato_sorgente`

> 📝 **Descrizione**
>
> Traduttore di stato per la sorgente polimorfa: dato (sorgente_tipo_id, sorgente_uid) restituisce lo stato del documento nel vocabolario comune (fase/esito/terminale). SEI rami dal 2026-07-18 (step 6b, brief-db-fatturazione-ddt-resi §4a): preventivo, offerta, ordine, contratto, DDT, reso — tutti i tipi documento registrati hanno ora un ramo. La chiave sorgente_uid segue config.sorgenti.key_selector (uid per preventivo/offerta, id::text per gli altri): vedi config/manual/sorgenti.md §Convenzione chiave sorgente. risolto = true sempre: l'assenza di riga E' il "non risolto". ⭐ rev 2026-10-05 (20261005-23): due colonne in coda, la chiave nel suo tipo — sorgente_chiave_uuid (rami a key_selector uid) e sorgente_chiave_id (rami a key_selector id); in ogni riga una sola e' valorizzata e coincide con sorgente_uid. Le legge pratiche.fn_stato_sorgente: sotto RLS il confronto su sorgente_uid (uid::text, id::text) non arriva mai all'indice, perche' uuid_out e int8out non sono leakproof, e cercare UN documento scandiva per intero tutte e sei le tabelle; sulla chiave nativa ogni ramo fa un Index Cond e quello dell'altra specie, con la colonna a NULL costante, il planner lo scarta. Un ramo nuovo deve valorizzare la sua colonna, o fn_stato_sorgente non lo trova (pgTAP: test-vw-stato-sorgente-ddt-reso-v1 test 12).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

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
