-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: tabelle profili reparto (ereditarietà permessi)
--       config.profili_reparto_aree, config.profili_reparto_azioni
--
-- Elenco test:
--  1) Riferimento config.unita_organizzative presente
--  2) Riferimento config.aree_funzionali (vendite) presente
--  3) Riferimento config.azioni_processo presente
--  4) profili_reparto_aree: INSERT valido accettato
--  5) profili_reparto_aree: default livello = BLOCCATO
--  6) profili_reparto_aree: UQ (uo_id, area_id) duplicato bloccato
--  7) profili_reparto_aree: FK area_id invalida bloccata
--  8) profili_reparto_aree: FK unita_organizzativa_id invalida bloccata
--  9) profili_reparto_azioni: INSERT valido accettato
-- 10) profili_reparto_azioni: default abilitata = false
-- 11) profili_reparto_azioni: UQ (uo_id, azione_id) duplicato bloccato
-- 12) profili_reparto_azioni: FK azione_id invalida bloccata
-- ------------------------------------------------------------

BEGIN;

SELECT plan(12);

-- ============================================================
-- 0. Raccolta riferimenti
-- ============================================================

CREATE TEMP TABLE tmp_refs_pr AS
SELECT
    (SELECT id FROM config.unita_organizzative
     WHERE attivo = true ORDER BY id LIMIT 1)          AS uo_id,
    (SELECT id FROM config.aree_funzionali
     WHERE codice = 'vendite')                         AS area_vendite_id,
    (SELECT id FROM config.aree_funzionali
     WHERE codice = 'acquisti')                        AS area_acquisti_id,
    (SELECT id FROM config.azioni_processo
     WHERE permission_codename = 'genera_fatture_lotti') AS azione_id;

SELECT ok(
    (SELECT uo_id FROM tmp_refs_pr) IS NOT NULL,
    'Riferimento config.unita_organizzative presente'
);

SELECT ok(
    (SELECT area_vendite_id FROM tmp_refs_pr) IS NOT NULL,
    'Riferimento config.aree_funzionali (vendite) presente'
);

SELECT ok(
    (SELECT azione_id FROM tmp_refs_pr) IS NOT NULL,
    'Riferimento config.azioni_processo presente'
);

-- ============================================================
-- 1. config.profili_reparto_aree
-- ============================================================

CREATE TEMP TABLE tmp_pra_ins AS
WITH ins AS (
    INSERT INTO config.profili_reparto_aree
        (unita_organizzativa_id, area_id)
    SELECT r.uo_id, r.area_vendite_id
    FROM tmp_refs_pr r
    RETURNING id, livello
)
SELECT * FROM ins;

SELECT ok(
    (SELECT id FROM tmp_pra_ins) IS NOT NULL,
    'profili_reparto_aree: INSERT valido accettato'
);

SELECT is(
    (SELECT livello::text FROM tmp_pra_ins),
    'BLOCCATO',
    'profili_reparto_aree: default livello = BLOCCATO'
);

-- UQ (unita_organizzativa_id, area_id)
SELECT throws_ok(
    format(
        $$INSERT INTO config.profili_reparto_aree
              (unita_organizzativa_id, area_id)
          VALUES (%s, %s)$$,
        (SELECT uo_id FROM tmp_refs_pr),
        (SELECT area_vendite_id FROM tmp_refs_pr)
    ),
    '23505',
    NULL,
    'profili_reparto_aree: UQ (uo_id, area_id) duplicato bloccato'
);

-- FK area_id invalida
SELECT throws_ok(
    format(
        $$INSERT INTO config.profili_reparto_aree
              (unita_organizzativa_id, area_id)
          VALUES (%s, 999999)$$,
        (SELECT uo_id FROM tmp_refs_pr)
    ),
    '23503',
    NULL,
    'profili_reparto_aree: FK area_id invalida bloccata'
);

-- FK unita_organizzativa_id invalida
SELECT throws_ok(
    format(
        $$INSERT INTO config.profili_reparto_aree
              (unita_organizzativa_id, area_id)
          VALUES (999999, %s)$$,
        (SELECT area_acquisti_id FROM tmp_refs_pr)
    ),
    '23503',
    NULL,
    'profili_reparto_aree: FK unita_organizzativa_id invalida bloccata'
);

-- ============================================================
-- 2. config.profili_reparto_azioni
-- ============================================================

CREATE TEMP TABLE tmp_prz_ins AS
WITH ins AS (
    INSERT INTO config.profili_reparto_azioni
        (unita_organizzativa_id, azione_id)
    SELECT r.uo_id, r.azione_id
    FROM tmp_refs_pr r
    RETURNING id, abilitata
)
SELECT * FROM ins;

SELECT ok(
    (SELECT id FROM tmp_prz_ins) IS NOT NULL,
    'profili_reparto_azioni: INSERT valido accettato'
);

SELECT is(
    (SELECT abilitata FROM tmp_prz_ins),
    false,
    'profili_reparto_azioni: default abilitata = false'
);

-- UQ (unita_organizzativa_id, azione_id)
SELECT throws_ok(
    format(
        $$INSERT INTO config.profili_reparto_azioni
              (unita_organizzativa_id, azione_id)
          VALUES (%s, %s)$$,
        (SELECT uo_id FROM tmp_refs_pr),
        (SELECT azione_id FROM tmp_refs_pr)
    ),
    '23505',
    NULL,
    'profili_reparto_azioni: UQ (uo_id, azione_id) duplicato bloccato'
);

-- FK azione_id invalida
SELECT throws_ok(
    format(
        $$INSERT INTO config.profili_reparto_azioni
              (unita_organizzativa_id, azione_id)
          VALUES (%s, 999999)$$,
        (SELECT uo_id FROM tmp_refs_pr)
    ),
    '23503',
    NULL,
    'profili_reparto_azioni: FK azione_id invalida bloccata'
);

SELECT * FROM finish();

ROLLBACK;
