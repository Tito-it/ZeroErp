{% include-markdown "it/dbzero/script/manual/vw_stato_sorgente.md" %}
# 🔍 View `vw_stato_sorgente`

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
