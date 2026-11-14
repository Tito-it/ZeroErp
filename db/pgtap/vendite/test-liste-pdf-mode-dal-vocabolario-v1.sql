-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le liste di preventivi, offerte e contratti portano pdf_mode dal
--   vocabolario.
--   ChangeSet: 20261114-25 (vendite.vw_preventivi_lista), -26
--   (vendite.vw_offerte_commerciali_lista), -34 (vendite.vw_contratti_lista).
--   Brief: brief-db-stati-documento-dal-vocabolario, giri 6a-bis, 2-ter e 6c
--   (D-PDF (a), Tid 2026-11-14).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - ogni riga delle due liste porta pdf_mode, la modalita' del PDF che il
--     vocabolario dichiara per il suo stato: il frontend accende il PDF dove
--     e' ARCHIVE, come la lista degli ordini, e non confronta piu' il codice
--     della bozza.
--
-- ⭐ LA MARCA SPOSTATA: pdf_mode della bozza si sposta in transazione su
--   ARCHIVE, e la lista deve seguirlo. Ogni marca ha il suo contrasto, letto
--   prima dello spostamento.
-- ⭐ I CASI SI COSTRUISCONO dai builder; nessuno skip.
--
-- Elenco test (plan 6):
--   1) contrasto: la lista dei preventivi, PREVIEW in bozza e ARCHIVE nell'emesso
--   2) contrasto: la lista delle offerte, PREVIEW in bozza e ARCHIVE nell'emessa
--   3) ⭐ pdf_mode della bozza del preventivo su ARCHIVE: la lista lo segue
--   4) ⭐ pdf_mode della bozza dell'offerta su ARCHIVE: la lista lo segue
--   5) contrasto: la lista dei contratti, PREVIEW in bozza e ARCHIVE nell'attivo
--   6) ⭐ pdf_mode della bozza del contratto su ARCHIVE: la lista lo segue
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE t_doc (caso text PRIMARY KEY,   -- l'etichetta del test
                         id   bigint);            -- l'id del documento, preventivo o offerta

INSERT INTO t_doc
SELECT 'prev_bozza', b.preventivo_id
  FROM dbops.fn_pgtap_crea_preventivo('liste pdf_mode, preventivo in bozza', 'DRAFT') b;

INSERT INTO t_doc
SELECT 'prev_emesso', r.preventivo_id
  FROM dbops.fn_pgtap_crea_preventivo_con_righe('liste pdf_mode, preventivo emesso', 'EMESSO') r;

INSERT INTO t_doc
SELECT c.caso, o.offerta_id
  FROM (VALUES ('off_bozza', 'BOZZA'), ('off_emessa', 'EMESSA')) c(caso, stato)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_offerta('liste pdf_mode, ' || c.caso, c.stato) o;

INSERT INTO t_doc
SELECT c.caso, k.contratto_id
  FROM (VALUES ('con_bozza', 'DRAFT'), ('con_attivo', 'ATTIVO')) c(caso, stato)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_contratto('liste pdf_mode, ' || c.caso, c.stato) k;

CREATE FUNCTION pg_temp.con(p_caso text)    -- text: l'etichetta del test
RETURNS vendite.vw_contratti_lista.pdf_mode%TYPE LANGUAGE sql STABLE AS $$
    SELECT v.pdf_mode FROM vendite.vw_contratti_lista v
     WHERE v.id = (SELECT id FROM t_doc WHERE caso = p_caso)
$$;

CREATE FUNCTION pg_temp.prev(p_caso text)   -- text: l'etichetta del test
RETURNS vendite.vw_preventivi_lista.pdf_mode%TYPE LANGUAGE sql STABLE AS $$
    SELECT v.pdf_mode FROM vendite.vw_preventivi_lista v
     WHERE v.id = (SELECT id FROM t_doc WHERE caso = p_caso)
$$;

CREATE FUNCTION pg_temp.off(p_caso text)    -- text: l'etichetta del test
RETURNS vendite.vw_offerte_commerciali_lista.pdf_mode%TYPE LANGUAGE sql STABLE AS $$
    SELECT v.pdf_mode FROM vendite.vw_offerte_commerciali_lista v
     WHERE v.id = (SELECT id FROM t_doc WHERE caso = p_caso)
$$;

-- ============================================================
-- 1-2) I contrasti, col vocabolario del seed
-- ============================================================
SELECT is(
    concat_ws(' ', pg_temp.prev('prev_bozza'), pg_temp.prev('prev_emesso')),
    'PREVIEW ARCHIVE',
    '1. contrasto: la lista dei preventivi da'' PREVIEW in bozza e ARCHIVE nell''emesso'
);

SELECT is(
    concat_ws(' ', pg_temp.off('off_bozza'), pg_temp.off('off_emessa')),
    'PREVIEW ARCHIVE',
    '2. contrasto: la lista delle offerte da'' PREVIEW in bozza e ARCHIVE nell''emessa'
);

SELECT is(
    concat_ws(' ', pg_temp.con('con_bozza'), pg_temp.con('con_attivo')),
    'PREVIEW ARCHIVE',
    '5. contrasto: la lista dei contratti da'' PREVIEW in bozza e ARCHIVE nell''attivo'
);

-- ============================================================
-- 3-4, 6) ⭐ La marca spostata: pdf_mode della bozza su ARCHIVE
-- ============================================================
UPDATE config.stati_doc_preventivi SET pdf_mode = 'ARCHIVE' WHERE codice_interno = 'DRAFT';
UPDATE config.stati_doc_offerte    SET pdf_mode = 'ARCHIVE' WHERE codice_interno = 'BOZZA';
UPDATE config.stati_doc_contratti  SET pdf_mode = 'ARCHIVE' WHERE codice_interno = 'DRAFT';

SELECT is(
    pg_temp.prev('prev_bozza')::text,
    'ARCHIVE',
    '3. con pdf_mode della bozza su ARCHIVE, la lista dei preventivi lo segue'
);

SELECT is(
    pg_temp.off('off_bozza')::text,
    'ARCHIVE',
    '4. con pdf_mode della bozza su ARCHIVE, la lista delle offerte lo segue'
);

SELECT is(
    pg_temp.con('con_bozza')::text,
    'ARCHIVE',
    '6. con pdf_mode della bozza su ARCHIVE, la lista dei contratti lo segue'
);

SELECT * FROM finish();

ROLLBACK;
