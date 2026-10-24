-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-contesto: escluso — il soggetto e' una funzione che non legge tabelle
--   (script.fn_intero_positivo_da_testo) e una che legge un parametro di
--   sistema senza override (dbops.fn_idempotency_soglia_secondi): nessuna RLS,
--   nessun perimetro di emittente. Il file gira come applicazione (nessun
--   marcatore runner), che e' chi le chiama.
-- pgTAP test per Zero ERP
--
-- La regola «intero positivo» di un parametro di sistema, in una sede.
--   Brief: brief-be-verifica-documentazione-api §I.11.0, §I.11.1
--   changeSet 20261024-03 (script.fn_intero_positivo_da_testo), -04
--   (dbops.fn_idempotency_soglia_secondi), -05 (fn_idempotency_prenota la usa),
--   -06 (fn_login_parametri la usa).
--
-- ⭐ Le forme si provano con valori COSTRUITI: il building block non legge
--   tabelle, quindi l'applicazione, che non scrive config.parameters, prova
--   anche il ramo E_CONFIG_MANCANTE che prima era scoperto.
--
-- Elenco test (plan 9):
--   forma
--    1) il building block esiste, SECURITY INVOKER, STABLE
--    2) la soglia ha la sua funzione, SECURITY INVOKER, STABLE
--   la regola
--    3) le forme ammesse restituiscono l'intero (1, 120, 999999)
--    4) ⛔ le forme rifiutate danno E_CONFIG_MANCANTE (NULL, vuoto, 0, 007,
--       -5, 1.5, ' 120 ', 1234567, abc)
--    5) ⛔ senza il codice del parametro: E_SCRIPT_CHIAMATA_NON_VALIDA
--   la soglia
--    6) dbops.fn_idempotency_soglia_secondi() restituisce il default del seed
--   le copie ritirate
--    7) ⛔ la regex della regola sta in una funzione sola: il building block
--    8) fn_idempotency_prenota e fn_login_parametri chiamano il building block
--       (direttamente o attraverso la soglia)
--    9) fn_login_parametri restituisce i cinque parametri del seed
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

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
             WHERE n.nspname = 'script' AND p.proname = 'fn_intero_positivo_da_testo'
               AND NOT p.prosecdef AND p.provolatile = 's'),
    '1) script.fn_intero_positivo_da_testo esiste, SECURITY INVOKER e STABLE');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'dbops' AND p.proname = 'fn_idempotency_soglia_secondi'
               AND NOT p.prosecdef AND p.provolatile = 's'),
    '2) dbops.fn_idempotency_soglia_secondi esiste, SECURITY INVOKER e STABLE');

-- ============================================================
-- la regola
-- ============================================================
SELECT results_eq(
    $q$SELECT script.fn_intero_positivo_da_testo(v, 'PGTAP_PARAMETRO')
         FROM (VALUES (1, '1'), (2, '120'), (3, '999999')) t(n, v)
        ORDER BY n$q$,
    $q$VALUES (1), (120), (999999)$q$,
    '3) Le forme ammesse restituiscono l''intero');

SELECT results_eq(
    $q$SELECT forma, pg_temp.codice_di(format(
                 'SELECT script.fn_intero_positivo_da_testo(%L, %L)', v, 'PGTAP_PARAMETRO'))
         FROM (VALUES (1, 'NULL', NULL), (2, 'vuoto', ''), (3, 'zero', '0'),
                      (4, 'zeri iniziali', '007'), (5, 'segno', '-5'),
                      (6, 'decimale', '1.5'), (7, 'spazi', ' 120 '),
                      (8, 'sette cifre', '1234567'), (9, 'lettere', 'abc')) t(n, forma, v)
        ORDER BY n$q$,
    $q$VALUES ('NULL'::text, 'E_CONFIG_MANCANTE'::text), ('vuoto', 'E_CONFIG_MANCANTE'),
              ('zero', 'E_CONFIG_MANCANTE'), ('zeri iniziali', 'E_CONFIG_MANCANTE'),
              ('segno', 'E_CONFIG_MANCANTE'), ('decimale', 'E_CONFIG_MANCANTE'),
              ('spazi', 'E_CONFIG_MANCANTE'), ('sette cifre', 'E_CONFIG_MANCANTE'),
              ('lettere', 'E_CONFIG_MANCANTE')$q$,
    '4) Le forme rifiutate danno E_CONFIG_MANCANTE: niente ripiego, niente btrim');

SELECT is(
    pg_temp.codice_di($q$SELECT script.fn_intero_positivo_da_testo('120', '  ')$q$),
    'E_SCRIPT_CHIAMATA_NON_VALIDA',
    '5) Senza il codice del parametro la chiamata non e'' valida: l''errore non direbbe che cosa correggere');

-- ============================================================
-- la soglia
-- ============================================================
SELECT is(
    dbops.fn_idempotency_soglia_secondi(),
    (SELECT p.default_value::integer FROM config.parameters p
      WHERE p.code = 'SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI'),
    '6) La soglia e'' il default del parametro, letto e validato in una sede');

-- ============================================================
-- le copie ritirate
-- ============================================================
SELECT results_eq(
    $q$SELECT (n.nspname::text || '.' || p.proname::text) COLLATE "default"
         FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE p.prokind = 'f'
          AND n.nspname IN ('script', 'dbops', 'config', 'anagrafiche', 'vendite',
                            'catalogo', 'magazzino', 'pagamenti', 'pratiche',
                            'documenti', 'maintenance', 'ui', 'acquisti', 'contabilita')
          AND strpos(pg_get_functiondef(p.oid), '^[1-9][0-9]{0,5}$') > 0
        ORDER BY 1$q$,
    $q$VALUES ('script.fn_intero_positivo_da_testo'::text)$q$,
    '7) La regex della regola sta solo nel building block: nessuna copia nelle funzioni');

SELECT ok(
    strpos(pg_get_functiondef('dbops.fn_idempotency_prenota'::regproc),
           'dbops.fn_idempotency_soglia_secondi()') > 0
    AND strpos(pg_get_functiondef('dbops.fn_idempotency_soglia_secondi'::regproc),
               'script.fn_intero_positivo_da_testo(') > 0
    AND strpos(pg_get_functiondef('script.fn_login_parametri'::regproc),
               'script.fn_intero_positivo_da_testo(') > 0,
    '8) La prenotazione legge la soglia dalla sua funzione, e soglia e login validano col building block');

SELECT results_eq(
    $q$SELECT max_tentativi, blocco_minuti, tetto_credenziale,
              attesa_base_secondi, attesa_max_secondi
         FROM script.fn_login_parametri()$q$,
    $q$SELECT (SELECT default_value::integer FROM config.parameters WHERE code = 'login_max_tentativi_falliti'),
              (SELECT default_value::integer FROM config.parameters WHERE code = 'login_blocco_minuti'),
              (SELECT default_value::integer FROM config.parameters WHERE code = 'login_tetto_credenziale'),
              (SELECT default_value::integer FROM config.parameters WHERE code = 'login_attesa_base_secondi'),
              (SELECT default_value::integer FROM config.parameters WHERE code = 'login_attesa_max_secondi')$q$,
    '9) fn_login_parametri restituisce i cinque parametri del seed, come prima');

SELECT * FROM finish();
ROLLBACK;
