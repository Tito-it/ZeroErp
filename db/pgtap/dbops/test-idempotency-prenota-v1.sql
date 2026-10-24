-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-contesto: escluso — il soggetto sono dbops.idempotency_keys e
--   dbops.request_log, senza RLS e senza perimetro di emittente: una veste
--   applicativa non cambierebbe nessuna risposta. Il file gira come
--   applicazione (nessun marcatore runner), che e' chi scrive le due tabelle.
-- pgTAP test per Zero ERP
--
-- Idempotency-Key: la scadenza delle righe (D5), la ripresa delle key
-- abbandonate (D6), la key legata a chi l'ha prenotata (D7), il testo
-- all'operatore (D4).
--   Brief: brief-be-verifica-documentazione-api, «Aperto per il team DB»
--   changeSet 20261023-02 (trigger alla nascita), -03 (colonne e CHECK),
--   -04 (dbops.fn_idempotency_prenota), -06 (p_ripresa_ammessa, §I.7.3);
--   20261024-01 (endpoint NOT NULL) e -02 (via il ramo delle key senza legame);
--   80_data: automation_scope.csv,
--   automation_rules_tbl.csv (regola 24), parameters_sistema.csv (id 62),
--   codici_errore.csv e messaggi_errore.csv (1386-1388).
--
-- ⚠️ La ripresa si prova retrodatando prenotata_at, che nessun trigger
--   riscrive: e' il motivo per cui la soglia non si misura da data_update.
--
-- Elenco test (plan 31):
--   forma
--    1) dbops.fn_idempotency_prenota esiste, SECURITY INVOKER
--    1-bis) una sola firma, a cinque argomenti (la firma a quattro e' ritirata)
--    2) le colonne auth_user_id, endpoint, prenotata_at esistono
--    3) ⛔ una key completed senza risposta e' respinta dal CHECK
--    3-bis) ⛔ ...e una failed con una risposta pure (il CHECK vale nei due versi)
--   D5 — scadenza
--    4) le due tabelle sono nello scope delle automazioni
--    5) la regola di idempotency_keys: un giorno, base data_insert
--    6) il trigger _m50_cleanup_at_ins e' montato su entrambe
--    7) una key nasce con cleanup_at = data_insert + 1 giorno
--    8) una riga di request_log nasce con cleanup_at = data_insert + 90 giorni
--   D6/D7 — la prenotazione
--    9) key nuova → ESEGUI, la riga e' in_progress e legata a utente ed endpoint
--    9-bis) ...la riga e' in_progress, legata a utente ed endpoint
--   10) stessa key, stesso utente, stesso endpoint, appena prenotata → IN_CORSO
--   11) ⛔ stessa key, ALTRO utente → E_IDEMPOTENCY_KEY_RIUSATA
--   12) ⛔ stessa key, ALTRO endpoint → E_IDEMPOTENCY_KEY_RIUSATA
--   13) ⛔ stessa key da una richiesta ANONIMA → E_IDEMPOTENCY_KEY_RIUSATA
--   14) in_progress da 60 s (sotto la soglia di 120) → IN_CORSO
--   15) in_progress da 200 s (sopra la soglia) → ESEGUI: ripresa
--   16) ...e la ripresa rinnova prenotata_at
--   17) completed → REPLAY con la risposta salvata
--   18) failed → ESEGUI: ripresa, e la riga torna in_progress
--   19) ⛔ una key senza endpoint e' respinta (NOT NULL, 20261024-01)
--   20) ⛔ una key con endpoint vuoto e' respinta dal CHECK
--   21) ⛔ key vuota → E_SCRIPT_CHIAMATA_NON_VALIDA
--   §I.7.3 — la ripresa dichiarata (i test 9-21 la dichiarano ammessa)
--   23) key nuova, ripresa non ammessa → ESEGUI
--   24) ⛔ in_progress da 200 s, ripresa non ammessa → IN_CORSO
--   24-bis) ...e la riga non si tocca
--   25) failed, ripresa non ammessa → ESEGUI: lo stato e' noto
--   26) ⛔ ripresa non dichiarata (NULL) → E_SCRIPT_CHIAMATA_NON_VALIDA
--   26-bis) ...e nessuna riga prenotata
--   catalogo
--   22) D4 e D7: classi giuste, IN_PROGRESS con causa, soluzione e riga en
--
-- Non coperto qui, dichiarato: il ramo E_CONFIG_MANCANTE della soglia (il
--   parametro assente) — l'applicazione non scrive config.parameters, e il file
--   gira come applicazione.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(31);

-- ============================================================
-- Fixture: chi solleva cosa. Il codice di dominio arriva nel canale
--   CONSTRAINT (script.fn_log_and_raise_error); un errore senza codice
--   torna col suo SQLSTATE. NULL = non ha sollevato.
-- ============================================================
CREATE FUNCTION pg_temp.codice_di(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_cst text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME;
    RETURN COALESCE(NULLIF(v_cst, ''), SQLSTATE);
END
$f$;

-- ============================================================
-- forma
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'dbops' AND p.proname = 'fn_idempotency_prenota'
               AND NOT p.prosecdef),
    '1) dbops.fn_idempotency_prenota esiste ed e'' SECURITY INVOKER');

SELECT results_eq(
    $q$SELECT pg_get_function_identity_arguments(p.oid)
         FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'dbops' AND p.proname = 'fn_idempotency_prenota'$q$,
    $q$VALUES ('p_idempotency_key text, p_auth_user_id integer, p_endpoint text, p_request_id uuid, p_ripresa_ammessa boolean'::text)$q$,
    '1-bis) Una sola firma, con p_ripresa_ammessa in coda: la firma a quattro e'' ritirata (nessun overload ambiguo)');

SELECT is(
    (SELECT count(*)::int FROM information_schema.columns
      WHERE table_schema = 'dbops' AND table_name = 'idempotency_keys'
        AND column_name IN ('auth_user_id', 'endpoint', 'prenotata_at')),
    3,
    '2) idempotency_keys ha auth_user_id, endpoint e prenotata_at');

SELECT is(
    pg_temp.codice_di($q$
        INSERT INTO dbops.idempotency_keys (idempotency_key, status, tx_id, endpoint)
        VALUES ('pgtap-idem-chk', 'completed', gen_random_uuid(), 'POST /pgtap/')$q$),
    'chk_idempotency_keys_risposta_solo_completed',
    '3) Una key completed senza risposta e'' respinta dal suo CHECK: non si potrebbe ne'' rimandare ne'' riprendere');

SELECT is(
    pg_temp.codice_di($q$
        INSERT INTO dbops.idempotency_keys (idempotency_key, status, response_payload, endpoint)
        VALUES ('pgtap-idem-chk2', 'failed', '{"data": 1}'::jsonb, 'POST /pgtap/')$q$),
    'chk_idempotency_keys_risposta_solo_completed',
    '3-bis) ...e una failed CON una risposta pure: la risposta c''e'' se e solo se la key e'' completed');

-- ============================================================
-- D5 — la scadenza
-- ============================================================
SELECT ok(
    dbops.fn_table_in_scope('dbops', 'idempotency_keys')
    AND dbops.fn_table_in_scope('dbops', 'request_log'),
    '4) idempotency_keys e request_log sono nello scope delle automazioni (il purge le vede)');

SELECT results_eq(
    $q$SELECT (p ->> 'ttl_days')::int, p ->> 'base_ts_column'
         FROM dbops.fn_cleanup_at_params('dbops', 'idempotency_keys') p$q$,
    $q$VALUES (1, 'data_insert'::text)$q$,
    '5) La regola di idempotency_keys: un giorno da data_insert');

SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
       JOIN pg_class c     ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal
        AND n.nspname = 'dbops'
        AND (c.relname, t.tgname) IN (
             ('idempotency_keys', 'trg_idempotency_keys_m50_cleanup_at_ins'),
             ('request_log',      'trg_request_log_m50_cleanup_at_ins'))),
    2,
    '6) Il trigger di scadenza alla nascita e'' montato su entrambe le tabelle');

-- ============================================================
-- D6/D7 — la prenotazione. Una key per caso; utente 9001 e endpoint fissi.
-- ============================================================
SELECT is(
    (SELECT esito FROM dbops.fn_idempotency_prenota('pgtap-idem-k1', 9001, 'POST /pgtap/azione/', p_ripresa_ammessa => true)),
    'ESEGUI',
    '9) Key nuova: ESEGUI');

SELECT is(
    (SELECT cleanup_at = data_insert + interval '1 day'
       FROM dbops.idempotency_keys WHERE idempotency_key = 'pgtap-idem-k1'),
    true,
    '7) La key nasce con cleanup_at = data_insert + 1 giorno');

INSERT INTO dbops.request_log (method, path, status_code)
VALUES ('POST', '/pgtap/request-log/', 200);

SELECT is(
    (SELECT cleanup_at = data_insert + interval '90 days'
       FROM dbops.request_log WHERE path = '/pgtap/request-log/'
      ORDER BY id DESC LIMIT 1),
    true,
    '8) Una riga di request_log nasce con cleanup_at = data_insert + 90 giorni (regola 14)');

SELECT results_eq(
    $q$SELECT status, auth_user_id, endpoint, prenotata_at = now()
         FROM dbops.idempotency_keys WHERE idempotency_key = 'pgtap-idem-k1'$q$,
    $q$VALUES ('in_progress'::text, 9001, 'POST /pgtap/azione/'::text, true)$q$,
    '9-bis) ...la riga e'' in_progress, legata a utente ed endpoint, prenotata adesso');

SELECT is(
    (SELECT esito FROM dbops.fn_idempotency_prenota('pgtap-idem-k1', 9001, 'POST /pgtap/azione/', p_ripresa_ammessa => true)),
    'IN_CORSO',
    '10) Stessa key, stessa richiesta, appena prenotata: IN_CORSO');

SELECT is(
    pg_temp.codice_di($q$SELECT * FROM dbops.fn_idempotency_prenota('pgtap-idem-k1', 9002, 'POST /pgtap/azione/', p_ripresa_ammessa => true)$q$),
    'E_IDEMPOTENCY_KEY_RIUSATA',
    '11) Stessa key da un ALTRO utente: E_IDEMPOTENCY_KEY_RIUSATA, mai la risposta dell''altro');

SELECT is(
    pg_temp.codice_di($q$SELECT * FROM dbops.fn_idempotency_prenota('pgtap-idem-k1', 9001, 'POST /pgtap/altra/', p_ripresa_ammessa => true)$q$),
    'E_IDEMPOTENCY_KEY_RIUSATA',
    '12) Stessa key su un ALTRO endpoint: E_IDEMPOTENCY_KEY_RIUSATA');

SELECT is(
    pg_temp.codice_di($q$SELECT * FROM dbops.fn_idempotency_prenota('pgtap-idem-k1', NULL, 'POST /pgtap/azione/', p_ripresa_ammessa => true)$q$),
    'E_IDEMPOTENCY_KEY_RIUSATA',
    '13) Stessa key da una richiesta ANONIMA: NULL e'' un utente diverso, non un jolly');

UPDATE dbops.idempotency_keys
   SET prenotata_at = now() - interval '60 seconds'
 WHERE idempotency_key = 'pgtap-idem-k1';

SELECT is(
    (SELECT esito FROM dbops.fn_idempotency_prenota('pgtap-idem-k1', 9001, 'POST /pgtap/azione/', p_ripresa_ammessa => true)),
    'IN_CORSO',
    '14) In corso da 60 secondi, sotto la soglia di 120: IN_CORSO');

UPDATE dbops.idempotency_keys
   SET prenotata_at = now() - interval '200 seconds'
 WHERE idempotency_key = 'pgtap-idem-k1';

SELECT is(
    (SELECT esito FROM dbops.fn_idempotency_prenota('pgtap-idem-k1', 9001, 'POST /pgtap/azione/', p_ripresa_ammessa => true)),
    'ESEGUI',
    '15) In corso da 200 secondi, sopra la soglia: abbandonata, ESEGUI (D6)');

SELECT results_eq(
    $q$SELECT status, prenotata_at = now()
         FROM dbops.idempotency_keys WHERE idempotency_key = 'pgtap-idem-k1'$q$,
    $q$VALUES ('in_progress'::text, true)$q$,
    '16) ...e la ripresa rinnova prenotata_at: chi riprende ha di nuovo tutta la soglia');

-- completed: come lo scrive IdempotencyStore.mark_completed
UPDATE dbops.idempotency_keys
   SET status = 'completed', tx_id = gen_random_uuid(),
       response_payload = '{"data": {"id": 42}}'::jsonb
 WHERE idempotency_key = 'pgtap-idem-k1';

SELECT results_eq(
    $q$SELECT esito, response_payload
         FROM dbops.fn_idempotency_prenota('pgtap-idem-k1', 9001, 'POST /pgtap/azione/', p_ripresa_ammessa => true)$q$,
    $q$VALUES ('REPLAY'::text, '{"data": {"id": 42}}'::jsonb)$q$,
    '17) Completed: REPLAY con la risposta salvata');

-- failed: come lo scrive IdempotencyStore.mark_failed
SELECT dbops.fn_idempotency_prenota('pgtap-idem-k2', 9001, 'POST /pgtap/azione/', p_ripresa_ammessa => true);
UPDATE dbops.idempotency_keys
   SET status = 'failed', tx_id = NULL, response_payload = NULL
 WHERE idempotency_key = 'pgtap-idem-k2';

-- ⚠️ L'esito si conserva e la riga si legge nell'istruzione DOPO: nella stessa
--   SELECT la riga si vedrebbe con la fotografia di prima della ripresa.
CREATE TEMP TABLE _t_esito AS
SELECT 'k2'::text AS caso, esito
  FROM dbops.fn_idempotency_prenota('pgtap-idem-k2', 9001, 'POST /pgtap/azione/', p_ripresa_ammessa => true);

SELECT results_eq(
    $q$SELECT e.esito, k.status
         FROM _t_esito e, dbops.idempotency_keys k
        WHERE e.caso = 'k2' AND k.idempotency_key = 'pgtap-idem-k2'$q$,
    $q$VALUES ('ESEGUI'::text, 'in_progress'::text)$q$,
    '18) Failed: ESEGUI, e la riga torna in_progress');

-- ogni key e' legata a una richiesta (20261024-01): una riga senza endpoint
-- non nasce, come la scriveva la prenotazione del backend prima di BE-1
SELECT is(
    pg_temp.codice_di($q$
        INSERT INTO dbops.idempotency_keys (idempotency_key, status)
        VALUES ('pgtap-idem-slegata', 'in_progress')$q$),
    '23502',
    '19) ⛔ Una key senza endpoint e'' respinta (NOT NULL): nessuna key senza la richiesta che l''ha prenotata');

SELECT is(
    pg_temp.codice_di($q$
        INSERT INTO dbops.idempotency_keys (idempotency_key, status, endpoint)
        VALUES ('pgtap-idem-vuota', 'in_progress', '   ')$q$),
    'chk_idempotency_keys_endpoint_non_vuoto',
    '20) ⛔ ...e una con endpoint vuoto pure: il legame dev''essere un valore');

SELECT is(
    pg_temp.codice_di($q$SELECT * FROM dbops.fn_idempotency_prenota('  ', 9001, 'POST /pgtap/azione/', p_ripresa_ammessa => true)$q$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '21) Key vuota: chiamata non valida, nessuna riga scritta');

-- ============================================================
-- §I.7.3 — la ripresa la dichiara il chiamante (20261023-06)
--   Una key per caso: k3 per la in_progress, k4 per la failed.
-- ============================================================
SELECT is(
    (SELECT esito FROM dbops.fn_idempotency_prenota('pgtap-idem-k3', 9001, 'POST /pgtap/a-passi/', p_ripresa_ammessa => false)),
    'ESEGUI',
    '23) Key nuova, ripresa NON ammessa: ESEGUI (la dichiarazione conta solo per le in_progress)');

UPDATE dbops.idempotency_keys
   SET prenotata_at = now() - interval '200 seconds'
 WHERE idempotency_key = 'pgtap-idem-k3';

SELECT is(
    (SELECT esito FROM dbops.fn_idempotency_prenota('pgtap-idem-k3', 9001, 'POST /pgtap/a-passi/', p_ripresa_ammessa => false)),
    'IN_CORSO',
    '24) ⛔ In corso da 200 secondi, sopra la soglia, ripresa NON ammessa: IN_CORSO (un lavoro a passi non si rifa'')');

SELECT results_eq(
    $q$SELECT status, prenotata_at = now() - interval '200 seconds'
         FROM dbops.idempotency_keys WHERE idempotency_key = 'pgtap-idem-k3'$q$,
    $q$VALUES ('in_progress'::text, true)$q$,
    '24-bis) ...e la riga non si tocca: prenotata_at resta quella della prenotazione');

SELECT dbops.fn_idempotency_prenota('pgtap-idem-k4', 9001, 'POST /pgtap/a-passi/', p_ripresa_ammessa => false);
UPDATE dbops.idempotency_keys
   SET status = 'failed', tx_id = NULL, response_payload = NULL
 WHERE idempotency_key = 'pgtap-idem-k4';

INSERT INTO _t_esito
SELECT 'k4', esito
  FROM dbops.fn_idempotency_prenota('pgtap-idem-k4', 9001, 'POST /pgtap/a-passi/', p_ripresa_ammessa => false);

SELECT results_eq(
    $q$SELECT e.esito, k.status
         FROM _t_esito e, dbops.idempotency_keys k
        WHERE e.caso = 'k4' AND k.idempotency_key = 'pgtap-idem-k4'$q$,
    $q$VALUES ('ESEGUI'::text, 'in_progress'::text)$q$,
    '25) Failed, ripresa NON ammessa: ESEGUI lo stesso, l''esito l''ha scritto il backend e lo stato e'' noto');

SELECT is(
    pg_temp.codice_di($q$SELECT * FROM dbops.fn_idempotency_prenota('pgtap-idem-k5', 9001, 'POST /pgtap/azione/')$q$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '26) ⛔ Ripresa non dichiarata (NULL): chiamata non valida, nessun default decide al posto del chiamante');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM dbops.idempotency_keys WHERE idempotency_key = 'pgtap-idem-k5'),
    '26-bis) ...e nessuna riga e'' stata prenotata');

-- ============================================================
-- catalogo — D4 e D7
-- ============================================================
SELECT ok(
    (SELECT classe FROM config.codici_errore WHERE codice = 'E_IDEMPOTENCY_KEY_RIUSATA') = 'DATO_ERRATO'
    AND (SELECT classe FROM config.codici_errore WHERE codice = 'E_IDEMPOTENCY_IN_PROGRESS') = 'CONFLITTO_STATO'
    AND EXISTS (SELECT 1 FROM config.messaggi_errore m
                 WHERE m.codice = 'E_IDEMPOTENCY_IN_PROGRESS' AND m.lingua = 'it'
                   AND NULLIF(btrim(m.causa), '') IS NOT NULL
                   AND NULLIF(btrim(m.soluzione), '') IS NOT NULL)
    AND EXISTS (SELECT 1 FROM config.messaggi_errore m
                 WHERE m.codice = 'E_IDEMPOTENCY_IN_PROGRESS' AND m.lingua = 'en'),
    '22) Catalogo: KEY_RIUSATA e'' DATO_ERRATO, IN_PROGRESS resta CONFLITTO_STATO e parla all''operatore (causa, soluzione, en)');

SELECT * FROM finish();
ROLLBACK;
