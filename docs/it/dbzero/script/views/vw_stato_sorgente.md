{% include-markdown "it/dbzero/script/manual/vw_stato_sorgente.md" %}
# 🔍 View `vw_stato_sorgente`

```sql
CREATE OR REPLACE VIEW script.vw_stato_sorgente AS
SELECT sorgente_tipo_id,
    sorgente_uid,
    true AS risolto,
    (stato_codice_interno)::text AS stato_codice_interno,
    (stato_codice)::text AS stato_codice,
    (stato_descrizione)::text AS stato_descrizione,
    (fase)::text AS fase,
    (esito)::text AS esito,
    terminale
   FROM vendite.vw_stato_sorgente_preventivo r;
```


---
{% include-markdown "signature-core.md" %}
