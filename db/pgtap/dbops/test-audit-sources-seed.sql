-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: seed dbops.audit_sources (Fase 5 P1 2026-04-29 +
-- aggiornato 2026-05-04 dismissione modello profili_reparto_*).
--
-- Verifica:
--   - 9 righe seedate (5 user_override/emittenti/RUA + identita +
--     3 profili_accesso_*).
--   - Coerenza area_funzionale con il vocabolario controllato:
--     PERMESSI | AUTH | ANAGRAFICHE | EMITTENTI | FATTURAZIONE.
--   - Le storico_table / storico_pk_col puntano a oggetti esistenti
--     (catch tipo nel CSV).
--   - Nessun residuo del modello legacy profili_reparto_*.
--   - La vista pubblica vw_audit_sources espone solo 3 colonne.
--
-- Indice test (1..7):
--    1. dbops.audit_sources contiene almeno 9 righe attive
--    2. Codici attesi presenti (set match) — incluso il nuovo
--       modello profili_accesso_aree/_azioni/_bindings
--    3. Tutte le righe attive usano un valore di area_funzionale
--       del vocabolario controllato
--    4. Tutte le storico_table referenziate esistono (regclass cast)
--    5. Tutte le storico_pk_col referenziate esistono come colonne
--       della rispettiva storico
--    6. Nessun codice legacy profili_reparto_* presente
--    7. Vista vw_audit_sources espone esattamente 3 colonne
--       (code, label_key, area_funzionale)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- =========================================================
-- 1) Almeno 9 righe attive
-- =========================================================
SELECT cmp_ok(
    (SELECT count(*)::int FROM dbops.audit_sources WHERE attivo = true),
    '>=',
    9,
    '1) dbops.audit_sources ha almeno 9 righe attive (post dismissione profili_reparto_*)'
);

-- =========================================================
-- 2) Set di codici attesi presenti (intersezione match)
-- =========================================================
SELECT bag_eq(
    $$
    SELECT code FROM dbops.audit_sources WHERE attivo = true
     AND code IN ('user_override_aree','user_override_azioni','user_override_oggetti',
                  'user_emittenti_fiscali','risorse_umane_auth_user','identita_digitali',
                  'profili_accesso_aree','profili_accesso_azioni','profili_accesso_bindings')
    $$,
    $$ VALUES ('user_override_aree'),('user_override_azioni'),('user_override_oggetti'),
              ('user_emittenti_fiscali'),('risorse_umane_auth_user'),('identita_digitali'),
              ('profili_accesso_aree'),('profili_accesso_azioni'),('profili_accesso_bindings') $$,
    '2) Tutti i 9 codici target presenti e attivi (modello profili_accesso_*)'
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
-- 6) Nessun residuo del modello legacy profili_reparto_*
-- =========================================================
SELECT is(
    (SELECT count(*)::int
       FROM dbops.audit_sources
      WHERE code IN ('profili_reparto_aree','profili_reparto_azioni')),
    0,
    '6) Nessun codice legacy profili_reparto_* in dbops.audit_sources'
);

-- =========================================================
-- 7) Vista pubblica espone solo 3 colonne
-- =========================================================
SELECT bag_eq(
    $$
    SELECT column_name
      FROM information_schema.columns
     WHERE table_schema = 'script'
       AND table_name   = 'vw_audit_sources'
    $$,
    $$ VALUES ('code'), ('label_key'), ('area_funzionale') $$,
    '7) script.vw_audit_sources espone esattamente (code, label_key, area_funzionale)'
);

SELECT * FROM finish();
ROLLBACK;
