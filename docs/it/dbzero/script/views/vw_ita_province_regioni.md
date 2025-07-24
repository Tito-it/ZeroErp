# 🔍 View `vw_ita_province_regioni`

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
   FROM (((province p
     LEFT JOIN province acc ON ((acc.id = ((p.extra_country ->> 'provincia_accisa_id'::text))::integer)))
     JOIN regioni r ON ((p.regione_id = r.id)))
     JOIN stati s ON ((r.stato_id = s.id)));
```
