{% include-markdown "it/dbzero/script/manual/vw_stato_sorgente.md" %}
# 🔍 View `vw_stato_sorgente`

> 📝 **Descrizione**
>
> Traduttore di stato per la sorgente polimorfa: dato (sorgente_tipo_id, sorgente_uid) restituisce lo stato del documento nel vocabolario comune (fase/esito/terminale). SEI rami dal 2026-07-18 (step 6b, brief-db-fatturazione-ddt-resi §4a): preventivo, offerta, ordine, contratto, DDT, reso — tutti i tipi documento registrati hanno ora un ramo. La chiave sorgente_uid segue config.sorgenti.key_selector (uid per preventivo/offerta, id::text per gli altri): vedi config/manual/sorgenti.md §Convenzione chiave sorgente. risolto = true sempre: l'assenza di riga E' il "non risolto".

```sql
CREATE OR REPLACE VIEW script.vw_stato_sorgente AS
SELECT r.sorgente_tipo_id,
    r.sorgente_uid,
    true AS risolto,
    (r.stato_codice_interno)::text AS stato_codice_interno,
    (r.stato_codice)::text AS stato_codice,
    (r.stato_descrizione)::text AS stato_descrizione,
    (r.fase)::text AS fase,
    (r.esito)::text AS esito,
    r.terminale
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
    r.terminale
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
    r.terminale
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
    r.terminale
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
    r.terminale
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
    r.terminale
   FROM vendite.vw_stato_sorgente_reso r;
```


---
{% include-markdown "signature-core.md" %}
