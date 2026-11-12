-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le viste delle note sono una per sede, e gemelle.
--       Ogni tabella-madre delle note (<schema>.note, partizionata) ha la sua
--       <schema>.vw_note; le viste hanno le stesse colonne nello stesso ordine,
--       sono security_invoker, si leggono dall'applicazione e non filtrano.
--       E' il presidio del meccanismo: una sede nuova delle note senza la sua
--       vista, o una vista che diverge dalle sorelle, fa rosso qui.
-- ChangeSet: 20_code/catalogo/20261112-31, vendite/-32, acquisti/-33, magazzino/-34.
--   Il vecchio lettore comune (script.fn_get_note e i suoi tre involucri), che
--   ricomponeva la stessa proiezione, e' ritirato in script/-35.
-- Brief: brief-db-revisione-catalogo §20.
--
-- Elenco test (plan 6):
--  1) ogni madre delle note ha la sua vw_note (e nessuna vw_note e' senza madre)
--  2) le sedi oggi sono quattro: catalogo, vendite, acquisti, magazzino
--  3) le viste hanno le stesse colonne, nello stesso ordine, di catalogo.vw_note
--  4) tutte security_invoker: chi legge vede cio' che le policy della sede gli
--     concedono (vendite e magazzino hanno la RLS sulla madre)
--  5) l'applicazione le legge
--  6) non filtrano: per chi legge, una riga per nota della madre
--
-- ⚠️ Il perimetro (4) si presidia sulla STRUTTURA: una vista security_invoker
--   sopra una madre con le policy applica le policy della madre. Il caso
--   costruito di una nota di un'altra azienda lo provano i pgTAP di perimetro
--   delle note sulla madre; qui si garantisce che la vista non li scavalchi.
-- ⚠️ Il 6 confronta le righe che ci sono: su un database senza note passa a
--   vuoto, ed e' dichiarato tale. Che la vista non abbia una WHERE lo dice la
--   sua definizione; il caso costruito per catalogo e' il test 12 di
--   catalogo/test-note-catalogo-forma-v1.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: IMMEDIATE li riporta a scattare a fine di ogni
--   istruzione (il COMMIT qui non arriva mai).
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come l'applicazione (ruolo OPERATORE +
-- RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- Le madri delle note: tabelle partizionate di nome «note», negli schemi
--   applicativi (storico ne tiene le copie, che non sono sedi).
CREATE TEMP TABLE tmp_madri AS
SELECT n.nspname::text AS schema_nome
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relname = 'note' AND c.relkind = 'p'
   AND n.nspname NOT IN ('storico', 'pg_catalog', 'information_schema');

CREATE TEMP TABLE tmp_viste AS
SELECT n.nspname::text AS schema_nome, c.oid AS vista_oid, c.reloptions
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relname = 'vw_note' AND c.relkind = 'v';

-- ============================================================
-- 1-2) Una vista per sede
-- ============================================================
SELECT is(
    (SELECT COALESCE(array_agg(x ORDER BY x), ARRAY[]::text[]) FROM (
        SELECT m.schema_nome || ': madre senza vw_note' AS x
          FROM tmp_madri m WHERE NOT EXISTS (SELECT 1 FROM tmp_viste v WHERE v.schema_nome = m.schema_nome)
        UNION ALL
        SELECT v.schema_nome || ': vw_note senza madre'
          FROM tmp_viste v WHERE NOT EXISTS (SELECT 1 FROM tmp_madri m WHERE m.schema_nome = v.schema_nome)) d),
    ARRAY[]::text[],
    '1) ogni madre delle note ha la sua vw_note, e ogni vw_note ha la sua madre');

SELECT is(
    (SELECT array_agg(schema_nome ORDER BY schema_nome) FROM tmp_madri),
    ARRAY['acquisti', 'catalogo', 'magazzino', 'vendite'],
    '2) le sedi delle note sono catalogo, vendite, acquisti, magazzino');

-- ============================================================
-- 3) Gemelle: stesse colonne, stesso ordine
-- ============================================================
CREATE TEMP TABLE tmp_colonne AS
SELECT v.schema_nome,
       string_agg(a.attname::text, ',' ORDER BY a.attnum) AS colonne
  FROM tmp_viste v
  JOIN pg_attribute a ON a.attrelid = v.vista_oid AND a.attnum > 0 AND NOT a.attisdropped
 GROUP BY v.schema_nome;

SELECT is(
    (SELECT COALESCE(array_agg(c.schema_nome ORDER BY c.schema_nome), ARRAY[]::text[])
       FROM tmp_colonne c
      WHERE c.colonne IS DISTINCT FROM (SELECT colonne FROM tmp_colonne WHERE schema_nome = 'catalogo')),
    ARRAY[]::text[],
    '3) le vw_note hanno le stesse colonne, nello stesso ordine, di catalogo.vw_note');

-- ============================================================
-- 4-5) Sicurezza e privilegi
-- ============================================================
SELECT is(
    (SELECT COALESCE(array_agg(schema_nome ORDER BY schema_nome), ARRAY[]::text[])
       FROM tmp_viste
      WHERE NOT COALESCE('security_invoker=true' = ANY (reloptions), false)),
    ARRAY[]::text[],
    '4) tutte le vw_note sono security_invoker');

SELECT is(
    (SELECT COALESCE(array_agg(schema_nome ORDER BY schema_nome), ARRAY[]::text[])
       FROM tmp_viste
      WHERE NOT has_table_privilege('zeroerp_app', vista_oid, 'SELECT')),
    ARRAY[]::text[],
    '5) l''applicazione legge tutte le vw_note');

-- ============================================================
-- 6) Non filtrano
-- ============================================================
CREATE FUNCTION pg_temp.scarti() RETURNS text[]
LANGUAGE plpgsql AS $$
DECLARE
    v_s      text;
    v_madre  bigint;
    v_vista  bigint;
    v_out    text[] := ARRAY[]::text[];
BEGIN
    FOR v_s IN SELECT schema_nome FROM tmp_madri ORDER BY schema_nome LOOP
        EXECUTE format('SELECT count(*) FROM %I.note', v_s) INTO v_madre;
        EXECUTE format('SELECT count(*) FROM %I.vw_note', v_s) INTO v_vista;
        IF v_madre IS DISTINCT FROM v_vista THEN
            v_out := array_append(v_out, format('%s: madre %s, vista %s', v_s, v_madre, v_vista));
        END IF;
    END LOOP;
    RETURN v_out;
END $$;

SELECT is(pg_temp.scarti(), ARRAY[]::text[],
    '6) per chi legge, ogni vw_note ha una riga per nota della sua madre');

SELECT * FROM finish();
ROLLBACK;
