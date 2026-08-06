-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: pratiche.template_flussi_handler_eventi — legame data-driven
--       template -> handler per evento (IN_CORSO/COMPLETATO) esito-aware.
--       + seed handler vendita.accetta_preventivo e binding APPROVAZIONE_CLIENTE.
--
-- Indice test (1..9):
--    1. tabella template_flussi_handler_eventi esiste
--    2. FK template_flusso_id -> template_flussi
--    3. FK handler_id -> handler_flussi
--    4. seed handler vendita.accetta_preventivo presente e attivo
--    5. binding 9003 (APPROVAZIONE_CLIENTE imm.) -> COMPLETATO/POSITIVO/accetta_preventivo
--    6. binding 9007 (APPROVAZIONE_CLIENTE diff.) -> COMPLETATO/POSITIVO/accetta_preventivo
--    7. evento fuori vocabolario -> viola CHECK (23514)
--    8. esito_richiesto fuori vocabolario -> viola FK (23503)
--    9. handler_id inesistente -> viola FK (23503)
--
-- BEGIN; + ROLLBACK finale: nessuna manipolazione persiste.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

-- ============================================================
-- 1) tabella esiste
-- ============================================================
SELECT has_table(
    'pratiche', 'template_flussi_handler_eventi',
    '1. tabella pratiche.template_flussi_handler_eventi esiste'
);

-- ============================================================
-- 2) FK verso template_flussi
-- ============================================================
SELECT fk_ok(
    'pratiche', 'template_flussi_handler_eventi', 'template_flusso_id',
    'pratiche', 'template_flussi', 'id',
    '2. FK template_flusso_id -> template_flussi.id'
);

-- ============================================================
-- 3) FK verso handler_flussi
-- ============================================================
SELECT fk_ok(
    'pratiche', 'template_flussi_handler_eventi', 'handler_id',
    'pratiche', 'handler_flussi', 'id',
    '3. FK handler_id -> handler_flussi.id'
);

-- ============================================================
-- 4) seed handler accetta_preventivo presente e attivo
-- ============================================================
SELECT is(
    (SELECT attivo
       FROM pratiche.handler_flussi
      WHERE handler_key = 'vendita.accetta_preventivo'),
    true,
    '4. handler vendita.accetta_preventivo presente e attivo'
);

-- ============================================================
-- 5) binding 9003 -> COMPLETATO / POSITIVO / accetta_preventivo
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pratiche.template_flussi_handler_eventi e
          JOIN pratiche.handler_flussi h ON h.id = e.handler_id
         WHERE e.template_flusso_id = 9003
           AND e.evento             = 'COMPLETATO'
           AND e.esito_richiesto    = 'POSITIVO'
           AND h.handler_key        = 'vendita.accetta_preventivo'
    ),
    '5. binding 9003 (APPROVAZIONE_CLIENTE imm.) -> COMPLETATO/POSITIVO/accetta_preventivo'
);

-- ============================================================
-- 6) binding 9007 -> COMPLETATO / POSITIVO / accetta_preventivo
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pratiche.template_flussi_handler_eventi e
          JOIN pratiche.handler_flussi h ON h.id = e.handler_id
         WHERE e.template_flusso_id = 9007
           AND e.evento             = 'COMPLETATO'
           AND e.esito_richiesto    = 'POSITIVO'
           AND h.handler_key        = 'vendita.accetta_preventivo'
    ),
    '6. binding 9007 (APPROVAZIONE_CLIENTE diff.) -> COMPLETATO/POSITIVO/accetta_preventivo'
);

-- ============================================================
-- 7) evento fuori vocabolario -> CHECK chk_tfhe_evento (23514)
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO pratiche.template_flussi_handler_eventi
           (template_flusso_id, evento, handler_id)
       VALUES (9001, 'PIPPO', 9001) $$,
    '23514',
    NULL,
    '7. evento non ammesso -> viola CHECK (23514)'
);

-- ============================================================
-- 8) esito fuori vocabolario -> FK fk_tfhe_esito_richiesto (23503)
--    Dal 20260701-03 esito_richiesto e' FK a config.esiti_flussi_pratiche
--    (codice_interno), non piu' CHECK: un valore non a vocabolario viola la FK.
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO pratiche.template_flussi_handler_eventi
           (template_flusso_id, evento, esito_richiesto, handler_id)
       VALUES (9001, 'COMPLETATO', 'BOH', 9001) $$,
    '23503',
    NULL,
    '8. esito_richiesto non ammesso -> viola FK (23503)'
);

-- ============================================================
-- 9) handler_id inesistente -> FK fk_tfhe_handler (23503)
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO pratiche.template_flussi_handler_eventi
           (template_flusso_id, evento, handler_id)
       VALUES (9001, 'IN_CORSO', 999999) $$,
    '23503',
    NULL,
    '9. handler_id inesistente -> viola FK (23503)'
);

SELECT * FROM finish();
ROLLBACK;
