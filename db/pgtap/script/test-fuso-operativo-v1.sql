-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: IL FUSO DELL'AZIENDA HA UNA SEDE SOLA, E I CONFINI DEL GIORNO LO SEGUONO
--       script.fn_fuso_operativo · script.fn_inizio_giorno_operativo
--       script.fn_giorno_operativo · script.fn_data_operativa
--       brief-be-db-fe-un-solo-fuso-aziendale §5.1 D-1, D-2 (20261009-40..43)
-- ------------------------------------------------------------
-- Indice test (1..22)
--  1-3) le tre funzioni nuove esistono con la firma attesa
--  4) fn_fuso_operativo restituisce il parametro
--  5) sede unica: nessun'altra funzione legge SYSTEM_FUSO_ORARIO
--  6) inizio del giorno d'estate (+2)
--  7) inizio del giorno d'inverno (+1)
--  8) il giorno del cambio d'ora di marzo dura 23 ore
--  9) il giorno del cambio d'ora di ottobre dura 25 ore
-- 10) 23:30 UTC del giorno D-1 e' il giorno D (01:30 a Roma)
-- 11) un secondo prima della mezzanotte aziendale e' ancora il giorno D-1
-- 12) andata e ritorno: giorno(inizio(D)) = D
-- 13) il risultato non dipende dal fuso della SESSIONE
-- 14) fn_data_operativa = fn_giorno_operativo(now())
-- 15) un altro fuso aziendale (Asia/Tokyo) sposta il confine
-- 16-17) NULL -> NULL, senza nemmeno leggere il fuso
-- 18-20) parametro VUOTO -> le tre funzioni sollevano (nessun ripiego a UTC)
-- 21) fuso non riconosciuto dal sistema -> errore di dominio che nomina il valore
-- 22) parametro ASSENTE -> solleva
-- ------------------------------------------------------------
-- Scopo:
--  - il fuso si legge in UN posto (regola del 2): fn_data_operativa,
--    fn_inizio_giorno_operativo e fn_giorno_operativo lo chiedono a
--    fn_fuso_operativo, che porta da sola il fail-loud;
--  - i confini fra istante e giorno si calcolano nel fuso dell'AZIENDA, mai in
--    quello della sessione. Il caso si COSTRUISCE con istanti espliciti: non si
--    aspetta la mezzanotte, e il test non dipende dall'ora in cui gira.
--
-- ⚠️ La sessione si forza a un fuso LONTANO da quello dell'azienda
--   (Pacific/Kiritimati, +14) APPOSTA: se una funzione leggesse il fuso della
--   sessione invece del parametro, i test 6-15 lo vedrebbero a qualunque ora.
--   E' la forma di §5.4 del brief («la CI vede il fuso a ogni ora»).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET LOCAL TimeZone = 'Pacific/Kiritimati';

SELECT plan(22);

-- ⭐ Il fuso dell'azienda lo fissa il test: Europe/Rome e' quello del seed, ma
--   i valori attesi sotto sono scritti per Europe/Rome, e non devono dipendere
--   da una decisione di configurazione che puo' cambiare.
UPDATE config.parameters SET default_value = 'Europe/Rome' WHERE code = 'SYSTEM_FUSO_ORARIO';

-- ============================================================
-- 1-5) Le funzioni e la sede unica
-- ============================================================
SELECT has_function('script', 'fn_fuso_operativo', ARRAY[]::text[],
  '1) script.fn_fuso_operativo() esiste');
SELECT has_function('script', 'fn_inizio_giorno_operativo', ARRAY['date'],
  '2) script.fn_inizio_giorno_operativo(date) esiste');
SELECT has_function('script', 'fn_giorno_operativo', ARRAY['timestamp with time zone'],
  '3) script.fn_giorno_operativo(timestamptz) esiste');

SELECT is(script.fn_fuso_operativo(), 'Europe/Rome',
  '4) fn_fuso_operativo restituisce il fuso del parametro');

-- ⭐ La regola del 2 sul fuso: chi passa fra istante e calendario lo CHIEDE a
--   fn_fuso_operativo. Una seconda funzione che legge il parametro da se' e'
--   una seconda copia della lettura e del fail-loud, e prima o poi diverge.
SELECT is(
  ARRAY(SELECT n.nspname || '.' || p.proname
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE p.prosrc ILIKE '%SYSTEM_FUSO_ORARIO%'
           AND n.nspname NOT IN ('pg_catalog', 'information_schema')
         ORDER BY 1),
  ARRAY['script.fn_fuso_operativo'],
  '5) sede unica: solo fn_fuso_operativo legge SYSTEM_FUSO_ORARIO');

-- ============================================================
-- 6-12) I confini, costruiti
-- ============================================================
SELECT is(script.fn_inizio_giorno_operativo(date '2026-07-15'),
          timestamptz '2026-07-14 22:00:00+00',
  '6) d''estate il giorno D comincia alle 22:00 UTC del giorno prima (+2)');

SELECT is(script.fn_inizio_giorno_operativo(date '2026-01-15'),
          timestamptz '2026-01-14 23:00:00+00',
  '7) d''inverno il giorno D comincia alle 23:00 UTC del giorno prima (+1)');

-- Europe/Rome passa all'ora legale l'ultima domenica di marzo (2026-03-29) e
-- torna a quella solare l'ultima domenica di ottobre (2026-10-25).
SELECT is(script.fn_inizio_giorno_operativo(date '2026-03-30')
          - script.fn_inizio_giorno_operativo(date '2026-03-29'),
          interval '23 hours',
  '8) il giorno del cambio d''ora di marzo dura 23 ore');

SELECT is(script.fn_inizio_giorno_operativo(date '2026-10-26')
          - script.fn_inizio_giorno_operativo(date '2026-10-25'),
          interval '25 hours',
  '9) il giorno del cambio d''ora di ottobre dura 25 ore');

-- ⭐ Il caso del difetto: un fatto delle 01:30 di Roma. Nel fuso della sessione
--   del backend (UTC) e' ancora il giorno prima.
SELECT is(script.fn_giorno_operativo(timestamptz '2026-07-14 23:30:00+00'),
          date '2026-07-15',
  '10) le 23:30 UTC del 14 luglio sono il 15 luglio per l''azienda (01:30 a Roma)');

SELECT is(script.fn_giorno_operativo(timestamptz '2026-07-14 21:59:59+00'),
          date '2026-07-14',
  '11) un secondo prima della mezzanotte aziendale e'' ancora il giorno prima');

SELECT is(script.fn_giorno_operativo(script.fn_inizio_giorno_operativo(date '2026-10-25')),
          date '2026-10-25',
  '12) andata e ritorno: il giorno dell''inizio del giorno D e'' D (anche a cambio d''ora)');

-- ============================================================
-- 13-15) Il fuso che conta e' quello dell'azienda
-- ============================================================
-- Lo stesso calcolo con la sessione in due fusi opposti: il risultato non cambia.
CREATE TEMP TABLE tmp_fuso_sessioni (fuso_sessione text, inizio timestamptz, giorno date);
SET LOCAL TimeZone = 'UTC';
INSERT INTO tmp_fuso_sessioni
SELECT 'UTC', script.fn_inizio_giorno_operativo(date '2026-07-15'),
       script.fn_giorno_operativo(timestamptz '2026-07-14 23:30:00+00');
SET LOCAL TimeZone = 'America/Los_Angeles';
INSERT INTO tmp_fuso_sessioni
SELECT 'America/Los_Angeles', script.fn_inizio_giorno_operativo(date '2026-07-15'),
       script.fn_giorno_operativo(timestamptz '2026-07-14 23:30:00+00');
SET LOCAL TimeZone = 'Pacific/Kiritimati';

SELECT is(
  (SELECT count(DISTINCT (inizio, giorno))::int FROM tmp_fuso_sessioni),
  1,
  '13) cambiare il fuso della sessione non cambia nessun confine');

SELECT is(script.fn_data_operativa(), script.fn_giorno_operativo(now()),
  '14) fn_data_operativa e fn_giorno_operativo(now()) rispondono lo stesso giorno');

UPDATE config.parameters SET default_value = 'Asia/Tokyo' WHERE code = 'SYSTEM_FUSO_ORARIO';
SELECT is(script.fn_inizio_giorno_operativo(date '2026-07-15'),
          timestamptz '2026-07-14 15:00:00+00',
  '15) con l''azienda a Tokyo (+9) il giorno D comincia alle 15:00 UTC del giorno prima');
UPDATE config.parameters SET default_value = 'Europe/Rome' WHERE code = 'SYSTEM_FUSO_ORARIO';

-- ============================================================
-- 16-22) NULL e fail-loud
-- ============================================================
-- ⭐ NULL -> NULL anche con il parametro rotto: un filtro opzionale non
--   valorizzato non deve far fallire la lista.
UPDATE config.parameters SET default_value = '' WHERE code = 'SYSTEM_FUSO_ORARIO';
SELECT ok(script.fn_inizio_giorno_operativo(NULL) IS NULL,
  '16) fn_inizio_giorno_operativo(NULL) -> NULL, senza leggere il fuso');
SELECT ok(script.fn_giorno_operativo(NULL) IS NULL,
  '17) fn_giorno_operativo(NULL) -> NULL, senza leggere il fuso');

SELECT throws_ok($$ SELECT script.fn_fuso_operativo() $$, 'P0001', NULL,
  '18) parametro VUOTO -> fn_fuso_operativo solleva (nessun ripiego a UTC)');
SELECT throws_ok($$ SELECT script.fn_inizio_giorno_operativo(date '2026-07-15') $$, 'P0001', NULL,
  '19) parametro VUOTO -> fn_inizio_giorno_operativo solleva');
SELECT throws_ok($$ SELECT script.fn_giorno_operativo(now()) $$, 'P0001', NULL,
  '20) parametro VUOTO -> fn_giorno_operativo solleva');

-- La rete di sicurezza: un valore che il sistema non riconosce (passato
-- spegnendo la riga del registro, che alla scrittura lo rifiuterebbe) solleva
-- l'errore di DOMINIO, non un 22023 grezzo. Si riaccende subito.
UPDATE config.parameter_fk_surrogate SET enabled = false WHERE code_pattern = 'SYSTEM_FUSO_ORARIO';
UPDATE config.parameters SET default_value = 'Europe/Roma' WHERE code = 'SYSTEM_FUSO_ORARIO';
SELECT throws_like($$ SELECT script.fn_inizio_giorno_operativo(date '2026-07-15') $$,
  '%Europe/Roma%',
  '21) fuso non riconosciuto dal sistema -> errore di dominio che nomina il valore');
UPDATE config.parameters SET default_value = 'Europe/Rome' WHERE code = 'SYSTEM_FUSO_ORARIO';
UPDATE config.parameter_fk_surrogate SET enabled = true WHERE code_pattern = 'SYSTEM_FUSO_ORARIO';

DELETE FROM config.parameters WHERE code = 'SYSTEM_FUSO_ORARIO';
SELECT throws_ok($$ SELECT script.fn_giorno_operativo(now()) $$, 'P0001', NULL,
  '22) parametro ASSENTE -> solleva');

SELECT * FROM finish();
ROLLBACK;
