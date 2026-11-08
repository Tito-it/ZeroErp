-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le due procedure di rinormalizzazione degli indirizzi
--   maintenance.proc_bump_toponomastica · maintenance.proc_bump_indirizzi_dettaglio
--   config.trgfn_toponomastica_protect_update
-- ChangeSet: 20261103-54, 20261103-55 · Brief: brief-db-revisione-maintenance D1, D8, D9
--
-- Elenco test (plan 8):
--  1) fixture: prima della correzione la via normalizzata dell'indirizzo di
--     dettaglio contiene la descrizione VECCHIA del toponimo (senza questo,
--     i test 6-7 passerebbero anche su una fixture che non distingue niente)
--  2) ✅ proc_bump_toponomastica gira
--  3) ⭐ D1: dopo la procedura il flag zeroerp.maintenance_toponomastica non e'
--     acceso, nella stessa transazione
--  4) ⛔ D1: e quindi il guard rifiuta ancora, nella stessa transazione, un
--     cambio a mano della descrizione del toponimo in uso
--  5) ⭐ lo stradario generale ha la descrizione nuova
--  6) ⭐ D9: l'indirizzo di dettaglio ha la descrizione nuova in via_norm
--  7) ⭐ D9: e in indirizzo_normalizzato
--  8) ⭐ D8: proc_bump_indirizzi_dettaglio non lascia acceso il flag degli
--     indirizzi (non lo accende piu')
--
-- ⚠️ La fixture si FABBRICA: toponimo, stradario generale, via e indirizzo
--   nascono qui. Su un database ricostruito da zero non ci sono indirizzi di
--   macchina, e un test che cercasse quelli esistenti passerebbe a vuoto.
--   Dal seed si prendono solo stato, comune e codice postale.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_fx AS
SELECT 'PGTAP BUMP VECCHIO ' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSUS') AS desc_vecchia,
       'PGTAP BUMP NUOVO '   || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSUS') AS desc_nuova,
       NULL::integer AS topo_id,
       NULL::integer AS sg_id,
       NULL::integer AS stradario_id,
       NULL::bigint  AS indirizzo_id;

WITH ins AS (
    INSERT INTO config.toponomastica (descrizione, stato_id, attivo)
    SELECT f.desc_vecchia, (SELECT id FROM config.stati ORDER BY id LIMIT 1), true
      FROM tmp_fx f
    RETURNING id
)
UPDATE tmp_fx SET topo_id = (SELECT id FROM ins);

WITH ins AS (
    INSERT INTO config.stradario_generale (toponomastica_id, descrizione, descrizione_breve)
    SELECT f.topo_id, 'PGTAP STRADA BUMP', 'PGTAPBUMP'
      FROM tmp_fx f
    RETURNING id
)
UPDATE tmp_fx SET sg_id = (SELECT id FROM ins);

-- Una via nuova sullo stradario generale nuovo: comune e codice postale dal
-- seed, presi da una via qualunque (servono solo come ancora).
WITH ancora AS (
    SELECT s.comune_id, s.codice_postale_id
      FROM config.stradario s
     ORDER BY s.id
     LIMIT 1
), ins AS (
    INSERT INTO config.stradario (comune_id, stradario_generale_id, codice_postale_id, storicizza)
    SELECT a.comune_id, f.sg_id, a.codice_postale_id, false
      FROM ancora a CROSS JOIN tmp_fx f
    RETURNING id
)
UPDATE tmp_fx SET stradario_id = (SELECT id FROM ins);

WITH ins AS (
    INSERT INTO anagrafiche.indirizzi_dettaglio (stradario_id, civico, altro)
    SELECT f.stradario_id, 1, 'Fixture pgTAP: bump toponomastica'
      FROM tmp_fx f
    RETURNING id
)
UPDATE tmp_fx SET indirizzo_id = (SELECT id FROM ins);

-- ============================================================
-- 1. La fixture distingue: oggi la via ha la descrizione vecchia
-- ============================================================
SELECT ok(
    (SELECT d.via_norm ILIKE '%' || f.desc_vecchia || '%'
       FROM anagrafiche.indirizzi_dettaglio d
       JOIN tmp_fx f ON f.indirizzo_id = d.id),
    'Fixture: prima della correzione via_norm contiene la descrizione vecchia'
);

-- ============================================================
-- 2. La correzione
-- ============================================================
SELECT lives_ok(
    $$
    DO $proc$
    DECLARE
      v_topo_id  integer;
      v_desc     text;
    BEGIN
      SELECT topo_id, desc_nuova INTO v_topo_id, v_desc FROM tmp_fx;
      CALL maintenance.proc_bump_toponomastica(v_topo_id, v_desc);
    END;
    $proc$;
    $$,
    'proc_bump_toponomastica corregge la descrizione di un toponimo in uso'
);

-- ============================================================
-- 3-4. D1: la porta si e' richiusa, nella stessa transazione
-- ============================================================
SELECT ok(
    current_setting('zeroerp.maintenance_toponomastica', true) IS DISTINCT FROM 'on',
    'D1: dopo la procedura il flag della toponomastica non e'' acceso'
);

SELECT throws_ok(
    $$
    UPDATE config.toponomastica
       SET descrizione = descrizione || ' A MANO'
     WHERE id = (SELECT topo_id FROM tmp_fx);
    $$,
    'P0001',
    NULL,
    'D1: dopo la procedura il guard rifiuta ancora la modifica a mano della descrizione'
);

-- ============================================================
-- 5-7. D9: la correzione arriva fino agli indirizzi di dettaglio
-- ============================================================
SELECT ok(
    (SELECT sg.indirizzo_normalizzato ILIKE '%' || f.desc_nuova || '%'
       FROM config.stradario_generale sg
       JOIN tmp_fx f ON f.sg_id = sg.id),
    'Lo stradario generale ha la descrizione nuova del toponimo'
);

SELECT ok(
    (SELECT d.via_norm ILIKE '%' || f.desc_nuova || '%'
       FROM anagrafiche.indirizzi_dettaglio d
       JOIN tmp_fx f ON f.indirizzo_id = d.id),
    'D9: la via normalizzata dell''indirizzo di dettaglio ha la descrizione nuova'
);

SELECT ok(
    (SELECT d.indirizzo_normalizzato ILIKE '%' || f.desc_nuova || '%'
       FROM anagrafiche.indirizzi_dettaglio d
       JOIN tmp_fx f ON f.indirizzo_id = d.id),
    'D9: l''indirizzo normalizzato di dettaglio ha la descrizione nuova'
);

-- ============================================================
-- 8. D8: la rinormalizzazione di una via non accende il flag
-- ============================================================
DO $proc$
DECLARE
  v_stradario_id integer;
BEGIN
  SELECT stradario_id INTO v_stradario_id FROM tmp_fx;
  CALL maintenance.proc_bump_indirizzi_dettaglio(v_stradario_id);
END;
$proc$;

SELECT ok(
    current_setting('zeroerp.maintenance_indirizzi_dettaglio', true) IS DISTINCT FROM 'on',
    'D8: dopo proc_bump_indirizzi_dettaglio il flag degli indirizzi non e'' acceso'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: questo file non lascia niente dietro di se'.
ROLLBACK;
