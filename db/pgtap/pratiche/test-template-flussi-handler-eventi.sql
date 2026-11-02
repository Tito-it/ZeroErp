-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: pratiche.template_flussi_handler_eventi — legame data-driven
--       template -> handler per evento (IN_CORSO/COMPLETATO) esito-aware.
--       + handler vendita.accetta_preventivo RITIRATO dal backend (GUIDA D4):
--         i suoi collegamenti del seed restano, spenti.
--
-- Indice test (1..10):
--    1. tabella template_flussi_handler_eventi esiste
--    2. FK template_flusso_id -> template_flussi
--    3. FK handler_id -> handler_flussi
--    4. nessun collegamento ATTIVO verso vendita.accetta_preventivo nelle
--       edizioni preset (emittente NULL)
--    5. binding 9003 (APPROVAZIONE_CLIENTE imm.) -> accetta_preventivo, spento
--    6. binding 9007 (APPROVAZIONE_CLIENTE diff.) -> accetta_preventivo, spento
--    7. evento fuori vocabolario -> viola CHECK (23514)
--    8. esito_richiesto fuori vocabolario -> viola FK (23503)
--    9. handler_id inesistente -> viola FK (23503)
--   10. handler vendita.accetta_preventivo presente e SPENTO nel registro
--
-- BEGIN; + ROLLBACK finale: nessuna manipolazione persiste.
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

SELECT plan(10);

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
-- 4) nessun collegamento attivo verso l'handler ritirato (preset)
-- ============================================================
-- Il backend non registra piu' vendita.accetta_preventivo in HANDLER_MAP:
-- un collegamento attivo farebbe fallire il completamento dello step
-- (E_HANDLER_NON_REGISTRATO). Perimetro: le edizioni preset, le sole che
-- nascono dal seed; le edizioni di un emittente sono dati e, se pubblicate,
-- immutabili (si correggono con una nuova versione).
SELECT is(
    (SELECT count(*)::integer
       FROM pratiche.template_flussi_handler_eventi e
       JOIN pratiche.handler_flussi h        ON h.id  = e.handler_id
       JOIN pratiche.template_flussi tf      ON tf.id = e.template_flusso_id
       JOIN pratiche.workflow_definizioni wd ON wd.id = tf.definizione_id
      WHERE h.handler_key = 'vendita.accetta_preventivo'
        AND e.attivo
        AND wd.emittente_fiscale_id IS NULL),
    0,
    '4. nessun collegamento attivo verso vendita.accetta_preventivo nei preset'
);

-- ============================================================
-- 5) binding 9003 -> COMPLETATO / POSITIVO / accetta_preventivo, spento
-- ============================================================
SELECT is(
    (SELECT e.attivo
       FROM pratiche.template_flussi_handler_eventi e
       JOIN pratiche.handler_flussi h ON h.id = e.handler_id
      WHERE e.template_flusso_id = 9003
        AND e.evento             = 'COMPLETATO'
        AND e.esito_richiesto    = 'POSITIVO'
        AND h.handler_key        = 'vendita.accetta_preventivo'),
    false,
    '5. binding 9003 (APPROVAZIONE_CLIENTE imm.) -> accetta_preventivo, presente e spento'
);

-- ============================================================
-- 6) binding 9007 -> COMPLETATO / POSITIVO / accetta_preventivo, spento
-- ============================================================
SELECT is(
    (SELECT e.attivo
       FROM pratiche.template_flussi_handler_eventi e
       JOIN pratiche.handler_flussi h ON h.id = e.handler_id
      WHERE e.template_flusso_id = 9007
        AND e.evento             = 'COMPLETATO'
        AND e.esito_richiesto    = 'POSITIVO'
        AND h.handler_key        = 'vendita.accetta_preventivo'),
    false,
    '6. binding 9007 (APPROVAZIONE_CLIENTE diff.) -> accetta_preventivo, presente e spento'
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

-- ============================================================
-- 10) handler ritirato: presente nel registro, spento
-- ============================================================
-- Il registro DB e HANDLER_MAP devono dire la stessa cosa: il backend non
-- registra piu' vendita.accetta_preventivo, quindi a DB e' spento (e un
-- collegamento attivo verso di lui e' rifiutato da
-- trgfn_child_requires_active_parent).
SELECT is(
    (SELECT attivo
       FROM pratiche.handler_flussi
      WHERE handler_key = 'vendita.accetta_preventivo'),
    false,
    '10. handler vendita.accetta_preventivo presente e spento'
);

SELECT * FROM finish();
ROLLBACK;
