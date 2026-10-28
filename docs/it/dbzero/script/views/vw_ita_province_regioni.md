{% include-markdown "it/dbzero/script/manual/vw_ita_province_regioni.md" %}
# 🔍 View `vw_ita_province_regioni`

> 📝 **Descrizione**
>
> Estensione Italia: province con accisa, regioni e codici ISTAT/catastali via jsonb.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_ita_province_regioni AS
SELECT p.id AS id_provincia,
    lpad((p.extra_country ->> 'codice_istat'::text), 3, '0'::text) AS ita_codice_istat_provincia,
    p.descrizione AS ita_nome_provincia,
    p.sigla AS ita_sigla_provincia,
    acc.id AS id_provincia_accisa,
    acc.descrizione AS ita_provincia_accisa,
    acc.sigla AS ita_sigla_accisa,
    r.id AS id_regione,
    lpad((r.extra_country ->> 'codice_istat'::text), 2, '0'::text) AS ita_codice_istat_regione,
    r.descrizione AS ita_nome_regione,
    ((r.extra_country ->> 'mezzogiorno'::text))::character(1) AS ita_mezzogiorno,
    s.id AS id_stato,
    s.sigla_stato AS ita_sigla_stato,
    s.descrizione AS ita_nome_stato,
    (s.extra_country ->> 'codice_istat'::text) AS ita_codice_istat_stato,
    (s.extra_country ->> 'codice_catastale'::text) AS ita_codice_catastale_stato
   FROM (((config.province p
     LEFT JOIN config.province acc ON ((acc.id = ((p.extra_country ->> 'provincia_accisa_id'::text))::integer)))
     JOIN config.regioni r ON ((p.regione_id = r.id)))
     JOIN config.stati s ON ((r.stato_id = s.id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
