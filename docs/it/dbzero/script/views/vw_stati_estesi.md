{% include-markdown "it/dbzero/script/manual/vw_stati_estesi.md" %}
# 🔍 View `vw_stati_estesi`

> 📝 **Descrizione**
>
> Estensione dei dati degli stati: include info ISTAT, catastale e contesto da jsonb.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

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
   FROM config.stati s;
```

</div>


---
{% include-markdown "signature-core.md" %}
