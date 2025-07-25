# 🔍 View `vw_stati_estesi`

```sql
CREATE OR REPLACE VIEW script.vw_stati_estesi AS
SELECT id,
    descrizione,
    sigla_stato,
    codice_iso2,
    codice_iso3,
    codice_telefonico,
    continente,
    (extra_country ->> 'codice_istat'::text) AS codice_istat,
    (extra_country ->> 'codice_catastale'::text) AS codice_catastale,
    (extra_country ->> 'stato_utilizzo'::text) AS stato_utilizzo
   FROM stati s;
```

---
{% include-markdown "signature-core.md" %}
