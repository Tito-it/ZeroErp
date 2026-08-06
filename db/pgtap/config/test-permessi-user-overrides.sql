-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: tabelle override utente e scope emittente
--       config.user_override_aree, config.user_override_oggetti,
--       config.user_override_azioni, config.user_emittenti_fiscali
--
-- Elenco test:
--  1) Riferimento django.auth_user presente
--  2) Riferimento aree_funzionali presente
--  3) Riferimento azioni_processo presente
--  4) user_override_aree: INSERT valido accettato
--  5) user_override_aree: default valido_dal = CURRENT_DATE
--  6) user_override_aree: UQ (user, area) duplicato bloccato
--  7) user_override_aree: CHECK valido_dal <= valido_al
--  8) user_override_oggetti: INSERT valido accettato
--  9) user_override_oggetti: UQ (user, app_label, model_name) bloccato
-- 10) user_override_oggetti: CHECK valido_dal <= valido_al
-- 11) user_override_azioni: INSERT valido accettato
-- 12) user_override_azioni: abilitata = true come inserito
-- 13) user_override_azioni: UQ (user, azione) duplicato bloccato
-- 14) user_override_azioni: CHECK valido_dal <= valido_al
-- 15) Riferimento anagrafiche.emittenti_fiscali presente
-- 16) user_emittenti_fiscali: INSERT valido accettato
-- 17) user_emittenti_fiscali: UQ (user, emittente) duplicato bloccato
-- 18) user_emittenti_fiscali: FK emittente_fiscale_id invalida bloccata
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(18);

-- ============================================================
-- 0. Raccolta riferimenti
-- ============================================================

CREATE TEMP TABLE tmp_refs_uo AS
SELECT
    (SELECT id FROM django.auth_user
     WHERE is_active = true ORDER BY id LIMIT 1)       AS user_id,
    (SELECT id FROM config.aree_funzionali
     WHERE codice = 'vendite')                          AS area_vendite_id,
    (SELECT id FROM config.aree_funzionali
     WHERE codice = 'acquisti')                         AS area_acquisti_id,
    (SELECT id FROM config.azioni_processo
     WHERE permission_codename = 'genera_fatture_lotti') AS azione_id,
    (SELECT id FROM config.azioni_processo
     WHERE permission_codename = 'approva_fattura')      AS azione_id_2,
    (SELECT id FROM anagrafiche.emittenti_fiscali
     WHERE attivo = true ORDER BY id LIMIT 1)            AS emittente_id;

SELECT ok(
    (SELECT user_id FROM tmp_refs_uo) IS NOT NULL,
    'Riferimento django.auth_user presente'
);

SELECT ok(
    (SELECT area_vendite_id FROM tmp_refs_uo) IS NOT NULL,
    'Riferimento aree_funzionali presente'
);

SELECT ok(
    (SELECT azione_id FROM tmp_refs_uo) IS NOT NULL,
    'Riferimento azioni_processo presente'
);

-- ============================================================
-- 1. config.user_override_aree
-- ============================================================

CREATE TEMP TABLE tmp_uoa_ins AS
WITH ins AS (
    INSERT INTO config.user_override_aree
        (auth_user_id, area_id, livello, meta)
    SELECT r.user_id, r.area_vendite_id,
           'TUTTO'::config.livello_accesso,
           jsonb_build_object('test_scope', 'pgtap_permessi_overrides')
    FROM tmp_refs_uo r
    RETURNING id, valido_dal
)
SELECT * FROM ins;

SELECT ok(
    (SELECT id FROM tmp_uoa_ins) IS NOT NULL,
    'user_override_aree: INSERT valido accettato'
);

SELECT is(
    (SELECT valido_dal FROM tmp_uoa_ins),
    CURRENT_DATE,
    'user_override_aree: default valido_dal = CURRENT_DATE'
);

-- UQ (auth_user_id, area_id)
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_override_aree
              (auth_user_id, area_id, livello)
          VALUES (%s, %s, 'LETTURA'::config.livello_accesso)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT area_vendite_id FROM tmp_refs_uo)
    ),
    '23505',
    NULL,
    'user_override_aree: UQ (user, area) duplicato bloccato'
);

-- CHECK valido_dal <= valido_al (usa area_acquisti_id per evitare UQ)
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_override_aree
              (auth_user_id, area_id, livello, valido_dal, valido_al)
          VALUES (%s, %s, 'LETTURA'::config.livello_accesso,
                  '2026-03-01'::date, '2026-02-01'::date)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT area_acquisti_id FROM tmp_refs_uo)
    ),
    '23514',
    NULL,
    'user_override_aree: CHECK valido_dal <= valido_al'
);

-- ============================================================
-- 2. config.user_override_oggetti
-- ============================================================

CREATE TEMP TABLE tmp_uoo_ins AS
WITH ins AS (
    INSERT INTO config.user_override_oggetti
        (auth_user_id, app_label, model_name, livello, meta)
    SELECT r.user_id, 'vendite', 'fattura',
           'LETTURA'::config.livello_accesso,
           jsonb_build_object('test_scope', 'pgtap_permessi_overrides')
    FROM tmp_refs_uo r
    RETURNING id
)
SELECT * FROM ins;

SELECT ok(
    (SELECT id FROM tmp_uoo_ins) IS NOT NULL,
    'user_override_oggetti: INSERT valido accettato'
);

-- UQ (auth_user_id, app_label, model_name)
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_override_oggetti
              (auth_user_id, app_label, model_name, livello)
          VALUES (%s, 'vendite', 'fattura', 'BLOCCATO'::config.livello_accesso)$$,
        (SELECT user_id FROM tmp_refs_uo)
    ),
    '23505',
    NULL,
    'user_override_oggetti: UQ (user, app_label, model_name) duplicato bloccato'
);

-- CHECK valido_dal <= valido_al (usa model_name diverso per evitare UQ)
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_override_oggetti
              (auth_user_id, app_label, model_name, livello, valido_dal, valido_al)
          VALUES (%s, 'vendite', 'lotto',
                  'LETTURA'::config.livello_accesso,
                  '2026-03-01'::date, '2026-02-01'::date)$$,
        (SELECT user_id FROM tmp_refs_uo)
    ),
    '23514',
    NULL,
    'user_override_oggetti: CHECK valido_dal <= valido_al'
);

-- ============================================================
-- 3. config.user_override_azioni
-- ============================================================

CREATE TEMP TABLE tmp_uoaz_ins AS
WITH ins AS (
    INSERT INTO config.user_override_azioni
        (auth_user_id, azione_id, abilitata, meta)
    SELECT r.user_id, r.azione_id, true,
           jsonb_build_object('test_scope', 'pgtap_permessi_overrides')
    FROM tmp_refs_uo r
    RETURNING id, abilitata
)
SELECT * FROM ins;

SELECT ok(
    (SELECT id FROM tmp_uoaz_ins) IS NOT NULL,
    'user_override_azioni: INSERT valido accettato'
);

SELECT is(
    (SELECT abilitata FROM tmp_uoaz_ins),
    true,
    'user_override_azioni: abilitata = true come inserito'
);

-- UQ (auth_user_id, azione_id)
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_override_azioni
              (auth_user_id, azione_id, abilitata)
          VALUES (%s, %s, false)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT azione_id FROM tmp_refs_uo)
    ),
    '23505',
    NULL,
    'user_override_azioni: UQ (user, azione) duplicato bloccato'
);

-- CHECK valido_dal <= valido_al (usa azione_id_2 per evitare UQ)
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_override_azioni
              (auth_user_id, azione_id, abilitata, valido_dal, valido_al)
          VALUES (%s, %s, true,
                  '2026-03-01'::date, '2026-02-01'::date)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT azione_id_2 FROM tmp_refs_uo)
    ),
    '23514',
    NULL,
    'user_override_azioni: CHECK valido_dal <= valido_al'
);

-- ============================================================
-- 4. config.user_emittenti_fiscali
-- ============================================================

SELECT ok(
    (SELECT emittente_id FROM tmp_refs_uo) IS NOT NULL,
    'Riferimento anagrafiche.emittenti_fiscali presente'
);

SELECT lives_ok(
    format(
        $$INSERT INTO config.user_emittenti_fiscali
              (auth_user_id, emittente_fiscale_id, meta)
          VALUES (%s, %s,
                  '{"test_scope": "pgtap_permessi_overrides"}'::jsonb)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT emittente_id FROM tmp_refs_uo)
    ),
    'user_emittenti_fiscali: INSERT valido accettato'
);

-- UQ (auth_user_id, emittente_fiscale_id)
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_emittenti_fiscali
              (auth_user_id, emittente_fiscale_id)
          VALUES (%s, %s)$$,
        (SELECT user_id FROM tmp_refs_uo),
        (SELECT emittente_id FROM tmp_refs_uo)
    ),
    '23505',
    NULL,
    'user_emittenti_fiscali: UQ (user, emittente) duplicato bloccato'
);

-- FK emittente_fiscale_id invalida
SELECT throws_ok(
    format(
        $$INSERT INTO config.user_emittenti_fiscali
              (auth_user_id, emittente_fiscale_id)
          VALUES (%s, 999999)$$,
        (SELECT user_id FROM tmp_refs_uo)
    ),
    '23503',
    NULL,
    'user_emittenti_fiscali: FK emittente_fiscale_id invalida bloccata'
);

SELECT * FROM finish();

ROLLBACK;
