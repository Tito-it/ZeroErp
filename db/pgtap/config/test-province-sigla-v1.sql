-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La sigla di una provincia: senza spazi di riempimento, e per l'Italia di
--   due lettere.
--   Brief: brief-db-character-n-spazi-di-riempimento (D-2 di Tid, 2026-10-10).
--   ChangeSet: 20261010-26 (varchar + chk_province_sigla_forma), -27 (viste
--   geo senza TRIM), -36 (config.fn_sigla_provincia_ammessa e i due guard).
--
-- Elenco test (plan 12):
--  1) provincia italiana con due lettere: entra
--  2) provincia italiana con tre caratteri: E_PROVINCIA_SIGLA_NON_VALIDA
--  3) provincia italiana in minuscolo: rifiutata
--  4) provincia estera con lettere e cifre: entra
--  5) provincia estera con un trattino: rifiutata (forma generale, dal guard
--       e non dal CHECK: la frase nomina la provincia)
--  6) UPDATE della sigla di una provincia italiana a tre lettere: rifiutato
--  7) UPDATE di un'altra colonna: il guard non giudica (OF sigla, regione_id)
--  8) una provincia estera spostata in una regione italiana: rifiutata
--  9) una regione che passa all'Italia con una provincia di sigla lunga:
--       rifiutata (guard AFTER su config.regioni)
-- 10) una regione che passa all'Italia con province a due lettere: passa
-- 11) la sigla si rilegge senza spazi: 'ZQ' e' lunga 2 (era character(10))
-- 12) le viste di lista la espongono com'e': vw_comuni_lista e
--       vw_province_lista, senza TRIM
--
-- ⭐ La fixture costruisce le sue regioni e le sue province: lo stato
--   italiano e uno estero si prendono dal catalogo per codice ISO (seed di
--   config.stati, presente anche sul database ricostruito da zero).
-- ⚠️ Il pattern delle frasi non attraversa i segnaposti: il messaggio e'
--   «La sigla «%s» della provincia %s non è valida.».
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _fx ON COMMIT DROP AS
SELECT (SELECT s.id FROM config.stati s WHERE s.codice_iso2 = 'IT' ORDER BY s.id LIMIT 1)  AS stato_it,
       (SELECT s.id FROM config.stati s WHERE s.codice_iso2 = 'FR' ORDER BY s.id LIMIT 1)  AS stato_ee,
       NULL::integer AS reg_it, NULL::integer AS reg_ee, NULL::integer AS reg_ee2,
       NULL::integer AS prov_it, NULL::integer AS prov_ee;

DO $fx$
DECLARE
    v_it   integer;
    v_ee   integer;
    v_ee2  integer;
BEGIN
    INSERT INTO config.regioni (descrizione, stato_id)
    SELECT 'PGTAP regione italiana sigla', stato_it FROM _fx
    RETURNING id INTO v_it;
    INSERT INTO config.regioni (descrizione, stato_id)
    SELECT 'PGTAP regione estera sigla', stato_ee FROM _fx
    RETURNING id INTO v_ee;
    INSERT INTO config.regioni (descrizione, stato_id)
    SELECT 'PGTAP regione estera a due lettere', stato_ee FROM _fx
    RETURNING id INTO v_ee2;
    UPDATE _fx SET reg_it = v_it, reg_ee = v_ee, reg_ee2 = v_ee2;
END
$fx$;

-- ============================================================
-- 1-5. INSERT
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO config.province (descrizione, sigla, regione_id)
      SELECT 'PGTAP Provincia Italiana', 'ZQ', reg_it FROM _fx$$,
    '1) provincia italiana con due lettere maiuscole: entra'
);
UPDATE _fx SET prov_it = (SELECT p.id FROM config.province p WHERE p.descrizione = 'PGTAP Provincia Italiana');

SELECT throws_like(
    $$INSERT INTO config.province (descrizione, sigla, regione_id)
      SELECT 'PGTAP Tre Lettere', 'ZQX', reg_it FROM _fx$$,
    '%della provincia%non è valida%',
    '2) provincia italiana con tre lettere: E_PROVINCIA_SIGLA_NON_VALIDA'
);

SELECT throws_like(
    $$INSERT INTO config.province (descrizione, sigla, regione_id)
      SELECT 'PGTAP Minuscola', 'zw', reg_it FROM _fx$$,
    '%della provincia%non è valida%',
    '3) provincia italiana in minuscolo: rifiutata'
);

SELECT lives_ok(
    $$INSERT INTO config.province (descrizione, sigla, regione_id)
      SELECT 'PGTAP Provincia Estera', 'AB12', reg_ee FROM _fx$$,
    '4) provincia estera con lettere e cifre: entra'
);
UPDATE _fx SET prov_ee = (SELECT p.id FROM config.province p WHERE p.descrizione = 'PGTAP Provincia Estera');

SELECT throws_like(
    $$INSERT INTO config.province (descrizione, sigla, regione_id)
      SELECT 'PGTAP Trattino', 'A-B', reg_ee FROM _fx$$,
    '%della provincia%non è valida%',
    '5) provincia estera con un trattino: rifiutata dal guard, prima del CHECK'
);

-- ============================================================
-- 6-8. UPDATE della provincia
-- ============================================================
SELECT throws_like(
    $$UPDATE config.province SET sigla = 'ZQX' WHERE id = (SELECT prov_it FROM _fx)$$,
    '%della provincia%non è valida%',
    '6) la sigla di una provincia italiana portata a tre lettere: rifiutata'
);

SELECT lives_ok(
    $$UPDATE config.province SET descrizione = 'PGTAP Provincia Italiana Bis'
       WHERE id = (SELECT prov_it FROM _fx)$$,
    '7) cambiare la descrizione non passa dal guard della sigla'
);

SELECT throws_like(
    $$UPDATE config.province SET regione_id = (SELECT reg_it FROM _fx)
       WHERE id = (SELECT prov_ee FROM _fx)$$,
    '%della provincia%non è valida%',
    '8) una provincia con sigla AB12 spostata in una regione italiana: rifiutata'
);

-- ============================================================
-- 9-10. La regione che cambia stato
-- ============================================================
SELECT throws_like(
    $$UPDATE config.regioni SET stato_id = (SELECT stato_it FROM _fx)
       WHERE id = (SELECT reg_ee FROM _fx)$$,
    '%della provincia%non è valida%',
    '9) una regione con una provincia AB12 non passa all''Italia'
);

INSERT INTO config.province (descrizione, sigla, regione_id)
SELECT 'PGTAP Provincia Estera Corta', 'ZW', reg_ee2 FROM _fx;

SELECT lives_ok(
    $$UPDATE config.regioni SET stato_id = (SELECT stato_it FROM _fx)
       WHERE id = (SELECT reg_ee2 FROM _fx)$$,
    '10) una regione con sole province a due lettere passa all''Italia'
);

-- ============================================================
-- 11-12. Nessuno spazio di riempimento
-- ============================================================
SELECT is(
    (SELECT p.sigla || '|' || octet_length(p.sigla) || '|' || p.descrizione || '|' || octet_length(p.descrizione)
       FROM config.province p WHERE p.id = (SELECT prov_it FROM _fx)),
    'ZQ|2|PGTAP Provincia Italiana Bis|28',
    '11) sigla e descrizione si rileggono come scritte, senza spazi di riempimento'
);

INSERT INTO config.comuni (descrizione, provincia_id)
SELECT 'PGTAP Comune Sigla', prov_it FROM _fx;

SELECT is(
    (SELECT c.provincia_sigla || '|' || c.provincia_descrizione || '|' || pl.sigla
       FROM config.vw_comuni_lista c
       JOIN config.vw_province_lista pl ON pl.id = c.provincia_id
      WHERE c.descrizione = 'PGTAP Comune Sigla'),
    'ZQ|PGTAP Provincia Italiana Bis|ZQ',
    '12) le viste di lista espongono sigla e descrizione come sono (niente TRIM, niente spazi)'
);

SELECT * FROM finish();
ROLLBACK;
