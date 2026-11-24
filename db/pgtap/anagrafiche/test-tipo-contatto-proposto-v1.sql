-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il tipo di contatto PROPOSTO (D-T5-6 b, Tid 2026-11-24): quando chi crea
-- un soggetto non dice il tipo del contatto di default, il database scrive il
-- tipo proposto, letto da script.fn_tipo_contatto_proposto_id dal parametro
-- TIPO_CONTATTO_PROPOSTO, con la cascata degli override e senza ripiego.
-- Brief: brief-db-revisione-anagrafiche §20.8 (giro 3-bis, S43-10).
--
-- Elenco test (plan 12):
--  1)  il BB esiste
--  2)  script.fn_get_tipo_contatto_id e' ritirata (regola del 2)
--  3)  il seed: TIPO_CONTATTO_PROPOSTO = PRINCIPALE, e ammette override
--  -- il controesempio: un tipo con id 0, il «primo per id» --
--  4)  fn_crea_soggetto_pf senza tipo (dal builder PF): il contatto di
--      default ha il tipo proposto, non il primo per id
--  5)  fn_crea_soggetto_pg senza tipo (dal builder PG, che non lo sceglie
--      piu'): idem
--  -- il BB --
--  6)  senza override propone il tipo del parametro
--  7)  override per funzione su fn_crea_soggetto_pf: la porta lo segue
--  8)  override per funzione su fn_crea_soggetto_pg: la porta lo segue
--  -- per ultimi: la configurazione rotta non ripiega --
--  9)  un codice che non e' un tipo: lo rifiuta il registro alla scrittura
--      (E_PARAMETER_DEFAULT_VALUE_INVALID)
--  10) il tipo tolto dopo: E_DEFAULT_ERRATO
--  11) ... e la porta non crea il soggetto (nessun ripiego sul primo per id)
--  12) il parametro vuoto: E_CONFIG_MANCANTE
--
-- Scopo:
--  - provare la regola sul CONTROESEMPIO di partenza: un tipo con id minore di
--    tutti, che il ripiego di prima avrebbe scritto (regola zero: il test se
--    lo costruisce, non legge la tabella di oggi);
--  - provare che le due porte chiedono il BB col proprio nome (gli override
--    per funzione), e che il BB fallisce invece di ripiegare.
--  - Gira come app: l'app scrive config.parameters, parameter_overrides e
--    tipi_contatti (catalogo di dbdev, 2026-11-24).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- I due builder creano soggetto, contatto e indirizzi, e aprono e richiudono
-- da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- 1-3) Il BB, il ritiro, il seed
-- ============================================================
SELECT has_function('script', 'fn_tipo_contatto_proposto_id', ARRAY['text'],
    '1) script.fn_tipo_contatto_proposto_id(text) esiste');

SELECT hasnt_function('script', 'fn_get_tipo_contatto_id',
    '2) script.fn_get_tipo_contatto_id e'' ritirata: la ricerca del tipo ha una sede sola');

SELECT is(
    (SELECT p.default_value || '|' || p.ammette_override::text
       FROM config.parameters p WHERE p.code = 'TIPO_CONTATTO_PROPOSTO'),
    'PRINCIPALE|true',
    '3) il seed propone PRINCIPALE, e ammette override');

-- ============================================================
-- Fixture
-- ============================================================
-- Gli override di oggi non decidono il test: si tolgono.
DELETE FROM config.parameter_overrides o
 USING config.parameters p
 WHERE p.id = o.parameter_id
   AND p.code = 'TIPO_CONTATTO_PROPOSTO';

-- ⭐ Il controesempio: un tipo con id 0, il primo per id.
INSERT INTO config.tipi_contatti (id, descrizione, codice_interno, codice)
VALUES (0, 'pgTAP il primo per id', 'PGTAP0', 'PGTAP0');

CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT (SELECT t.id FROM config.tipi_contatti t
          JOIN config.parameters p ON p.default_value = t.codice_interno
         WHERE p.code = 'TIPO_CONTATTO_PROPOSTO') AS proposto_id,
       (SELECT t.id FROM config.tipi_contatti t WHERE t.codice_interno = 'REFERENTE') AS referente_id,
       (SELECT p.id FROM config.parameters p WHERE p.code = 'TIPO_CONTATTO_PROPOSTO') AS parametro_id;

-- Il tipo del contatto che la porta scrive col soggetto: l'unico del soggetto
--   appena nato. ⚠️ Non is_default: quello lo decide un trigger della tabella,
--   per il contatto di un ruolo. Piu' di un contatto: NULL, e il test e' rosso.
-- ⛔ VOLATILE, non STABLE: la si chiama sul soggetto che la porta crea nella
--   stessa istruzione, e una STABLE legge la fotografia di prima.
CREATE FUNCTION pg_temp.tipo_default(p_soggetto_id anagrafiche.soggetti.id%TYPE)
RETURNS config.tipi_contatti.id%TYPE LANGUAGE sql VOLATILE AS $$
    SELECT CASE WHEN count(*) = 1 THEN min(c.tipo_contatto_id) END
      FROM anagrafiche.contatti c
     WHERE c.soggetto_id = p_soggetto_id
$$;

-- ============================================================
-- 4-5) Il controesempio: le porte senza tipo
-- ============================================================
SELECT is(
    pg_temp.tipo_default(dbops.fn_pgtap_crea_soggetto_pf('PgtapProposto', 'Pf')),
    (SELECT proposto_id FROM _f),
    '4) fn_crea_soggetto_pf senza tipo: il tipo proposto, non il primo per id');

SELECT is(
    pg_temp.tipo_default(dbops.fn_pgtap_crea_soggetto_pg('pgTAP tipo proposto PG')),
    (SELECT proposto_id FROM _f),
    '5) fn_crea_soggetto_pg senza tipo: il tipo proposto, non il primo per id');

-- ============================================================
-- 6-8) Il BB e la cascata degli override
-- ============================================================
SELECT is(script.fn_tipo_contatto_proposto_id('pgTAP'), (SELECT proposto_id FROM _f),
    '6) senza override: il tipo del parametro');

INSERT INTO config.parameter_overrides (parameter_id, overridden_value, function_name)
SELECT parametro_id, 'REFERENTE', 'anagrafiche.fn_crea_soggetto_pf' FROM _f;

SELECT is(
    pg_temp.tipo_default(dbops.fn_pgtap_crea_soggetto_pf('PgtapProposto', 'Override')),
    (SELECT referente_id FROM _f),
    '7) override per funzione su fn_crea_soggetto_pf: la porta lo segue');

INSERT INTO config.parameter_overrides (parameter_id, overridden_value, function_name)
SELECT parametro_id, 'REFERENTE', 'anagrafiche.fn_crea_soggetto_pg' FROM _f;

SELECT is(
    pg_temp.tipo_default(dbops.fn_pgtap_crea_soggetto_pg('pgTAP tipo proposto override')),
    (SELECT referente_id FROM _f),
    '8) override per funzione su fn_crea_soggetto_pg: la porta lo segue');

DELETE FROM config.parameter_overrides o
 USING _f WHERE o.parameter_id = _f.parametro_id;

-- ============================================================
-- 9-12) Per ultimi: la configurazione rotta non ripiega
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$UPDATE config.parameters SET default_value = 'PGTAPNONE' WHERE code = 'TIPO_CONTATTO_PROPOSTO'$$),
    'E_PARAMETER_DEFAULT_VALUE_INVALID',
    '9) un codice che non e'' un tipo di contatto: lo rifiuta il registro');

-- Il tipo esiste quando lo si scrive, e si toglie dopo.
INSERT INTO config.tipi_contatti (id, descrizione, codice_interno, codice)
VALUES (2147483646, 'pgTAP tipo che sparira''', 'PGTAPX', 'PGTAPX');
UPDATE config.parameters SET default_value = 'PGTAPX' WHERE code = 'TIPO_CONTATTO_PROPOSTO';
DELETE FROM config.tipi_contatti WHERE id = 2147483646;

SELECT is(dbops.fn_pgtap_codice_errore($$SELECT script.fn_tipo_contatto_proposto_id('pgTAP')$$),
    'E_DEFAULT_ERRATO',
    '10) il tipo proposto tolto dopo: E_DEFAULT_ERRATO');

SELECT is(dbops.fn_pgtap_codice_errore($$SELECT dbops.fn_pgtap_crea_soggetto_pf('PgtapProposto', 'Rotto')$$),
    'E_DEFAULT_ERRATO',
    '11) ... e la porta non crea il soggetto: nessun ripiego sul primo per id');

UPDATE config.parameters SET default_value = '' WHERE code = 'TIPO_CONTATTO_PROPOSTO';

SELECT is(dbops.fn_pgtap_codice_errore($$SELECT script.fn_tipo_contatto_proposto_id('pgTAP')$$),
    'E_CONFIG_MANCANTE',
    '12) il parametro vuoto: E_CONFIG_MANCANTE, nessun ripiego');

SELECT * FROM finish();
ROLLBACK;
