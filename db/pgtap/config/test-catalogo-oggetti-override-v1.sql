-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un override per oggetto esiste solo per un oggetto A CATALOGO e NON
--   RISERVATO — config.area_model_overrides.riservato (20260928-01) e la FK
--   composita fk_user_override_oggetti_catalogo (20260928-02); il seed del
--   catalogo in CSV (20260928-03) e l'uscita di billing_account (20260928-04).
--   Brief: brief-db-be-fe-catalogo-oggetti-permessi, §3.1 (D-3, D-4, D-5).
--
-- ⭐ La regola viveva solo nel backend (put_override_oggetti + la blacklist
--   _MODEL_OVERRIDE_RISERVATI): qui si prova che la tiene il DB, per ogni
--   percorso di scrittura, e che tiene anche quando e' il CATALOGO a cambiare
--   sotto un override.
--
-- Elenco test (plan 12):
--   La forma
--    1) user_override_oggetti.riservato e' generata (STORED)
--    2) la FK e' (app_label, model_name, riservato) -> area_model_overrides
--   Il vincolo (operatore e oggetto COSTRUITI)
--    3) override su un oggetto a catalogo, non riservato: passa
--    4) oggetto non a catalogo -> 23503
--    5) oggetto a catalogo ma riservato -> 23503
--    6) riservato scritto dal chiamante -> 428C9 (colonna generata)
--    7) l'oggetto DIVENTA riservato mentre ha un override -> 23503
--    8) l'oggetto esce dal catalogo mentre ha un override -> 23503
--   Il seed (contratto del catalogo, 80_data)
--    9) anagrafiche.billing_account non e' a catalogo (D-5)
--   10) offerta_commerciale e uom_tipi a catalogo, personalizzabili (caso B)
--   11) i dieci oggetti del kernel dei permessi a catalogo, riservati (D-4)
--   12) ordine, ddt, contratto, reso a catalogo, personalizzabili (caso B,
--       rev 2026-09-28: BE e FE li applicano su tutte le rotte, brief §3.5)
--
-- ⚠️ Gira come l'APPLICAZIONE: override e catalogo si scrivono come li scrive il
--   pannello dei permessi. Operatore COSTRUITO (fn_pgtap_crea_emittente_operatore).
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

-- Due oggetti di fixture: uno personalizzabile, uno riservato.
INSERT INTO config.area_model_overrides (app_label, model_name, area_id, riservato)
SELECT 'pgtap_app', m.model_name, af.id, m.riservato
  FROM config.aree_funzionali af,
       (VALUES ('pgtap_libero', false), ('pgtap_riservato', true)) m(model_name, riservato)
 WHERE af.schema_db = 'vendite';

-- ============================================================
-- 1-2 La forma
-- ============================================================
SELECT is(
    (SELECT format('%s|%s', a.attgenerated, pg_get_expr(d.adbin, d.adrelid))
       FROM pg_attribute a
       JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
      WHERE a.attrelid = 'config.user_override_oggetti'::regclass AND a.attname = 'riservato'),
    's|false',
    '1) user_override_oggetti.riservato: generata STORED, sempre false');

SELECT is(
    (SELECT format('%s -> %s.%s(%s)',
                   (SELECT string_agg(a.attname, ',' ORDER BY k.ord)
                      FROM unnest(c.conkey) WITH ORDINALITY k(attnum, ord)
                      JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum),
                   n.nspname, r.relname,
                   (SELECT string_agg(a.attname, ',' ORDER BY k.ord)
                      FROM unnest(c.confkey) WITH ORDINALITY k(attnum, ord)
                      JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = k.attnum))
       FROM pg_constraint c
       JOIN pg_class r ON r.oid = c.confrelid
       JOIN pg_namespace n ON n.oid = r.relnamespace
      WHERE c.conrelid = 'config.user_override_oggetti'::regclass
        AND c.conname = 'fk_user_override_oggetti_catalogo'),
    'app_label,model_name,riservato -> config.area_model_overrides(app_label,model_name,riservato)',
    '2) FK composita verso il catalogo, riservato compreso');

-- ============================================================
-- 3-8 Il vincolo
-- ============================================================
SELECT lives_ok(
    format($$INSERT INTO config.user_override_oggetti (auth_user_id, app_label, model_name, livello, motivo)
             VALUES (%s, 'pgtap_app', 'pgtap_libero', 'LETTURA', 'Fixture pgTAP')$$,
           (SELECT auth_user_id FROM _mondo)),
    '3) override su un oggetto a catalogo e non riservato: passa');

SELECT throws_ok(
    format($$INSERT INTO config.user_override_oggetti (auth_user_id, app_label, model_name, livello, motivo)
             VALUES (%s, 'pgtap_app', 'pgtap_fuori_catalogo', 'LETTURA', 'Fixture pgTAP')$$,
           (SELECT auth_user_id FROM _mondo)),
    '23503', NULL,
    '4) ⛔ oggetto non a catalogo: rifiutato');

SELECT throws_ok(
    format($$INSERT INTO config.user_override_oggetti (auth_user_id, app_label, model_name, livello, motivo)
             VALUES (%s, 'pgtap_app', 'pgtap_riservato', 'LETTURA', 'Fixture pgTAP')$$,
           (SELECT auth_user_id FROM _mondo)),
    '23503', NULL,
    '5) ⛔ oggetto a catalogo ma riservato: rifiutato');

SELECT throws_ok(
    format($$INSERT INTO config.user_override_oggetti (auth_user_id, app_label, model_name, livello, motivo, riservato)
             VALUES (%s, 'pgtap_app', 'pgtap_riservato', 'LETTURA', 'Fixture pgTAP', true)$$,
           (SELECT auth_user_id FROM _mondo)),
    '428C9', NULL,
    '6) ⛔ riservato scritto dal chiamante: la colonna e'' generata');

SELECT throws_ok(
    $$UPDATE config.area_model_overrides SET riservato = true
       WHERE app_label = 'pgtap_app' AND model_name = 'pgtap_libero'$$,
    '23503', NULL,
    '7) ⛔ l''oggetto diventa riservato mentre ha un override: fermo sulla FK');

SELECT throws_ok(
    $$DELETE FROM config.area_model_overrides
       WHERE app_label = 'pgtap_app' AND model_name = 'pgtap_libero'$$,
    '23503', NULL,
    '8) ⛔ l''oggetto esce dal catalogo mentre ha un override: fermo sulla FK');

-- ============================================================
-- 9-12 Il seed
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM config.area_model_overrides
      WHERE app_label = 'anagrafiche' AND model_name = 'billing_account'),
    0,
    '9) anagrafiche.billing_account non e'' a catalogo: il permesso e'' cliente (D-5)');

SELECT is(
    (SELECT string_agg(format('%s.%s=%s', app_label, model_name, riservato::text), ',' ORDER BY app_label, model_name)
       FROM config.area_model_overrides
      WHERE (app_label, model_name) IN (('vendite', 'offerta_commerciale'), ('catalogo', 'uom_tipi'))),
    'catalogo.uom_tipi=false,vendite.offerta_commerciale=false',
    '10) offerta_commerciale e uom_tipi a catalogo, personalizzabili (caso B)');

SELECT is(
    (SELECT string_agg(format('%s.%s', k.app_label, k.model_name), ',' ORDER BY k.app_label, k.model_name)
       FROM (VALUES ('anagrafiche', 'identita_digitali'), ('config', 'area_model_overrides'),
                    ('config', 'profili_accesso'), ('config', 'profili_accesso_aree'),
                    ('config', 'profili_accesso_azioni'), ('config', 'profili_accesso_bindings'),
                    ('config', 'user_emittenti_fiscali'), ('config', 'user_override_aree'),
                    ('config', 'user_override_azioni'), ('config', 'user_override_oggetti')) k(app_label, model_name)
      WHERE NOT EXISTS (SELECT 1 FROM config.area_model_overrides amo
                         WHERE amo.app_label = k.app_label AND amo.model_name = k.model_name
                           AND amo.riservato)),
    NULL,
    '11) i dieci oggetti del kernel dei permessi sono a catalogo e riservati (D-4)');

-- ⚠️ rev 2026-09-28. Fino a oggi il test pretendeva il contrario: i quattro
--   restavano fuori finche' il BE chiedeva l'AREA sulle loro rotte principali
--   (un BLOCCATO avrebbe nascosto i pulsanti lasciando aperta l'API, §1 terzo
--   caso). Dal 2026-09-28 BE e FE li applicano su tutte le rotte (brief §3.4),
--   quindi entrano a catalogo, personalizzabili. Il presidio che le quattro
--   porte coincidano e' quello Django della D-3 (test_catalogo_oggetti_rotte).
SELECT is(
    (SELECT string_agg(format('%s=%s', model_name, riservato::text), ',' ORDER BY model_name)
       FROM config.area_model_overrides
      WHERE app_label = 'vendite' AND model_name IN ('ordine', 'ddt', 'contratto', 'reso')),
    'contratto=false,ddt=false,ordine=false,reso=false',
    '12) ordine, ddt, contratto, reso a catalogo, personalizzabili (caso B)');

SELECT * FROM finish();
ROLLBACK;
