-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed dbops.audit_sources (Fase 5 P1 2026-04-29).
--
-- Verifica:
--   - 8 righe seedate (6 esistenti + user_override_oggetti +
--     identita_digitali nuovi).
--   - Coerenza area_funzionale con il vocabolario controllato:
--     PERMESSI | AUTH | ANAGRAFICHE | EMITTENTI | FATTURAZIONE.
--   - Le storico_table / storico_pk_col puntano a oggetti esistenti
--     (catch tipo nel CSV).
--   - La vista pubblica vw_audit_sources espone solo 3 colonne.
--
-- Indice test (1..6):
--    1. dbops.audit_sources contiene almeno 8 righe attive
--    2. Codici attesi presenti (set match)
--    3. Tutte le righe attive usano un valore di area_funzionale
--       del vocabolario controllato
--    4. Tutte le storico_table referenziate esistono (regclass cast)
--    5. Tutte le storico_pk_col referenziate esistono come colonne
--       della rispettiva storico
--    6. Vista vw_audit_sources espone esattamente 3 colonne
--       (code, label_key, area_funzionale)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(6);

-- =========================================================
-- 1) Almeno 8 righe attive
-- =========================================================
SELECT cmp_ok(
    (SELECT count(*)::int FROM dbops.audit_sources WHERE attivo = true),
    '>=',
    8,
    '1) dbops.audit_sources ha almeno 8 righe attive (seed Fase 5)'
);

-- =========================================================
-- 2) Set di codici attesi presenti (intersezione match)
-- =========================================================
SELECT bag_eq(
    $$
    SELECT code FROM dbops.audit_sources WHERE attivo = true
     AND code IN ('user_override_aree','user_override_azioni','user_override_oggetti',
                  'user_emittenti_fiscali','risorse_umane_auth_user',
                  'profili_reparto_aree','profili_reparto_azioni','identita_digitali')
    $$,
    $$ VALUES ('user_override_aree'),('user_override_azioni'),('user_override_oggetti'),
              ('user_emittenti_fiscali'),('risorse_umane_auth_user'),
              ('profili_reparto_aree'),('profili_reparto_azioni'),('identita_digitali') $$,
    '2) Tutti i 8 codici target presenti e attivi'
);

-- =========================================================
-- 3) Vocabolario controllato area_funzionale
-- =========================================================
SELECT is(
    (SELECT count(*)::int
       FROM dbops.audit_sources
      WHERE attivo = true
        AND area_funzionale NOT IN
            ('PERMESSI','AUTH','ANAGRAFICHE','EMITTENTI','FATTURAZIONE')),
    0,
    '3) Tutte le righe usano un area_funzionale del vocabolario controllato'
);

-- =========================================================
-- 4) Le storico_table esistono come oggetti DB (regclass cast
--    fallirebbe se la tabella non esiste -> raise gestito da DO)
-- =========================================================
DO $check$
DECLARE
    v_row record;
BEGIN
    FOR v_row IN SELECT code, storico_table FROM dbops.audit_sources WHERE attivo = true
    LOOP
        PERFORM v_row.storico_table::regclass;
    END LOOP;
END
$check$;

SELECT pass('4) Tutte le storico_table referenziate esistono (regclass cast OK)');

-- =========================================================
-- 5) Tutte le storico_pk_col esistono come colonne nelle storico
-- =========================================================
SELECT is(
    (SELECT count(*)::int
       FROM dbops.audit_sources s
      WHERE s.attivo = true
        AND NOT EXISTS (
            SELECT 1
              FROM information_schema.columns c
             WHERE c.table_schema = split_part(s.storico_table, '.', 1)
               AND c.table_name   = split_part(s.storico_table, '.', 2)
               AND c.column_name  = s.storico_pk_col
        )),
    0,
    '5) Tutte le storico_pk_col referenziate esistono come colonne'
);

-- =========================================================
-- 6) Vista pubblica espone solo 3 colonne
-- =========================================================
SELECT bag_eq(
    $$
    SELECT column_name
      FROM information_schema.columns
     WHERE table_schema = 'script'
       AND table_name   = 'vw_audit_sources'
    $$,
    $$ VALUES ('code'), ('label_key'), ('area_funzionale') $$,
    '6) script.vw_audit_sources espone esattamente (code, label_key, area_funzionale)'
);

SELECT * FROM finish();
ROLLBACK;
