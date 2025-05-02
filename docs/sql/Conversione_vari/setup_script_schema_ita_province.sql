
-- 1. Creazione schema per organizzare script, funzioni, viste
CREATE SCHEMA IF NOT EXISTS script;

-- 2. Vista di esempio salvata nello schema "script"
CREATE OR REPLACE VIEW script.vw_ita_province_regioni AS
SELECT
    p.id AS id_provincia,
    lpad((p.extra_country ->> 'codice_istat')::text, 3, '0') AS ita_codice_istat_provincia,
    p.descrizione AS ita_nome_provincia,
    p.sigla AS ita_sigla_provincia,
    acc.id AS id_provincia_accisa,
    acc.descrizione AS ita_provincia_accisa,
    acc.sigla AS ita_sigla_accisa,
    r.id AS id_regione,
    lpad((r.codice_istat)::text, 2, '0') AS ita_codice_istat_regione,
    r.descrizione AS ita_nome_regione,
    r.mezzogiorno AS ita_mezzogiorno,
    s.id AS id_stato,
    s.sigla_stato AS ita_sigla_stato,
    s.descrizione AS ita_nome_stato,
    s.extra_country ->> 'codice_istat' AS ita_codice_istat_stato,
    s.extra_country ->> 'codice_catastale' AS ita_codice_catastale_stato
FROM config.province p
LEFT JOIN config.province acc 
    ON acc.id = (p.extra_country ->> 'provincia_accisa_id')::int
JOIN config.regioni r 
    ON p.regione_id = r.id
JOIN config.stati s 
    ON r.stato_id = s.id;

-- 3. Commento documentativo
COMMENT ON VIEW script.vw_ita_province_regioni IS
'Estensione logica per contesto Italia: join province, regione, stato e informazioni fiscali/ISTAT tramite JSONB.';
