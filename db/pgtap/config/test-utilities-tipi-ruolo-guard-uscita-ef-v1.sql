-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: un'utility gestita da un'azienda non esce dalla matrice dell'emittente
--   fiscale, e la riga EF non ha data di fine; il seed della matrice.
--   Brief: brief-db-utility-gestite-dall-emittente §6 (D-U-7, D-U-10, D-U-11), §9 (V1, V2).
--   ChangeSet: 20261127-31 (guard fail-closed), 20261127-32 (questo guard),
--   20261127-33 (il seed).
-- ------------------------------------------------------------
-- Elenco test (plan 14):
--  Il montaggio
--   1) un solo trigger della funzione sulla matrice, BEFORE, INSERT UPDATE DELETE
--  La riga EF non ha data di fine
--   2) INSERT di una riga EF con valido_al: E_UTILITY_EF_SENZA_SCADENZA
--   3) la stessa riga senza data di fine nasce
--  Senza aziende che la gestiscono, la riga EF si governa liberamente
--   4) spenta
--   5) riaccesa
--  Un'azienda la gestisce (D-U-11: la riga presente)
--   6) l'azienda attiva l'utility: la riga in emittenti_fiscali_utilities nasce
--   7) spenta: E_UTILITY_EF_GESTITA, con la frase
--   8) data d'inizio futura: E_UTILITY_EF_GESTITA
--   9) data di fine: E_UTILITY_EF_SENZA_SCADENZA (la regola che parla per prima)
--  10) cancellata: E_UTILITY_EF_GESTITA
--  11) spostata su un altro tipo di ruolo: rifiutata (lucchetto o questo guard)
--  12) un ritocco che non la fa uscire (meta) passa
--  13) le righe degli altri tipi di ruolo non sono giudicate: quella del cliente si spegne
--  Il seed (D-U-10)
--  14) ogni utility del seed e' ammessa per EF e per CL, accesa e senza data di fine
--
-- Scopo:
--  - i casi si COSTRUISCONO: due utility nuove, senza righe nella matrice, e
--    un'azienda nuova (dbops.fn_pgtap_crea_emittente_operatore);
--  - il test 14 e' il presidio del seed: la sua assenza si vede solo su un
--    database costruito da zero, dove senza seed la matrice e' vuota;
--  - gira come l'applicazione: le righe della matrice scritte qui sono
--    dell'installazione, e il seed di primo impianto non le giudica.
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- Due utility nuove: config.utilities.id non ha default, il numero dopo il massimo.
CREATE TEMP TABLE _u AS
WITH base AS (SELECT max(u.id) AS m FROM config.utilities u),
ins AS (
  INSERT INTO config.utilities (id, codice, codice_interno, descrizione)
  SELECT b.m + n, 'PGTAP_EF' || n, 'PGTAP_EF' || n, 'pgTAP uscita EF ' || n
    FROM base b, generate_series(1, 2) n
  RETURNING id, codice
)
SELECT
  (SELECT id     FROM ins WHERE codice = 'PGTAP_EF1') AS u1,
  (SELECT codice FROM ins WHERE codice = 'PGTAP_EF1') AS u1_codice,
  (SELECT id     FROM ins WHERE codice = 'PGTAP_EF2') AS u2,
  (SELECT t.id FROM config.tipi_ruoli t WHERE t.codice_interno = 'EF') AS ef,
  (SELECT t.id FROM config.tipi_ruoli t WHERE t.codice_interno = 'CL') AS cl;

-- ============================================================
-- Il montaggio
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pg_trigger t
    WHERE t.tgrelid = 'config.utilities_tipi_ruolo'::regclass
      AND t.tgfoid = 'config.trgfn_utilities_tipi_ruolo_guard_uscita_ef()'::regprocedure
      AND NOT t.tgisinternal
      -- BEFORE (2), ROW (1), INSERT (4), DELETE (8), UPDATE (16)
      AND (t.tgtype & (1 | 2 | 4 | 8 | 16)) = (1 | 2 | 4 | 8 | 16)),
  1,
  '1) un solo trigger del guard sulla matrice, BEFORE per riga su INSERT, UPDATE, DELETE');

-- ============================================================
-- La riga EF non ha data di fine
-- ============================================================
SELECT throws_ok(
  format($$INSERT INTO config.utilities_tipi_ruolo (utility_id, tipo_ruolo_id, attivo, valido_al)
           VALUES (%s, %s, true, script.fn_data_operativa() + 30)$$,
         (SELECT u2 FROM _u), (SELECT ef FROM _u)),
  'P0001',
  format('Per l''emittente fiscale l''utility %s non ha una data di fine.', 'PGTAP_EF2'),
  '2) una riga EF con data di fine: E_UTILITY_EF_SENZA_SCADENZA');

SELECT lives_ok(
  format($$INSERT INTO config.utilities_tipi_ruolo (utility_id, tipo_ruolo_id, attivo)
           VALUES (%1$s, %2$s, true), (%1$s, %3$s, true)$$,
         (SELECT u1 FROM _u), (SELECT ef FROM _u), (SELECT cl FROM _u)),
  '3) senza data di fine la riga EF nasce (con quella del cliente)');

-- ============================================================
-- Senza aziende che la gestiscono
-- ============================================================
SELECT lives_ok(
  format($$UPDATE config.utilities_tipi_ruolo SET attivo = false
            WHERE utility_id = %s AND tipo_ruolo_id = %s$$,
         (SELECT u1 FROM _u), (SELECT ef FROM _u)),
  '4) nessuna azienda la gestisce: la riga EF si spegne');

SELECT lives_ok(
  format($$UPDATE config.utilities_tipi_ruolo SET attivo = true
            WHERE utility_id = %s AND tipo_ruolo_id = %s$$,
         (SELECT u1 FROM _u), (SELECT ef FROM _u)),
  '5) e si riaccende');

-- ============================================================
-- Un'azienda la gestisce
-- ============================================================
SELECT lives_ok(
  format($$INSERT INTO anagrafiche.emittenti_fiscali_utilities
             (emittente_soggetto_ruolo_id, utility_id, arrotondamento_importi_dec,
              metodo_arrotondamento_importi, attivo)
           VALUES (%s, %s, 2, 'HALF_UP', true)$$,
         (SELECT soggetto_ruolo_id FROM _mondo), (SELECT u1 FROM _u)),
  '6) l''azienda attiva l''utility, ammessa per EF');

SELECT throws_ok(
  format($$UPDATE config.utilities_tipi_ruolo SET attivo = false
            WHERE utility_id = %s AND tipo_ruolo_id = %s$$,
         (SELECT u1 FROM _u), (SELECT ef FROM _u)),
  'P0001',
  format('Aziende che gestiscono l''utility %s: %s. L''utility resta ammessa per l''emittente fiscale.',
         (SELECT u1_codice FROM _u), 1),
  '7) spenta con un''azienda che la gestisce: E_UTILITY_EF_GESTITA');

SELECT throws_ok(
  format($$UPDATE config.utilities_tipi_ruolo SET valido_dal = script.fn_data_operativa() + 1
            WHERE utility_id = %s AND tipo_ruolo_id = %s$$,
         (SELECT u1 FROM _u), (SELECT ef FROM _u)),
  'P0001',
  format('Aziende che gestiscono l''utility %s: %s. L''utility resta ammessa per l''emittente fiscale.',
         (SELECT u1_codice FROM _u), 1),
  '8) una data d''inizio futura: E_UTILITY_EF_GESTITA');

SELECT throws_ok(
  format($$UPDATE config.utilities_tipi_ruolo SET valido_al = script.fn_data_operativa() + 30
            WHERE utility_id = %s AND tipo_ruolo_id = %s$$,
         (SELECT u1 FROM _u), (SELECT ef FROM _u)),
  'P0001',
  format('Per l''emittente fiscale l''utility %s non ha una data di fine.', (SELECT u1_codice FROM _u)),
  '9) una data di fine: E_UTILITY_EF_SENZA_SCADENZA');

SELECT throws_ok(
  format($$DELETE FROM config.utilities_tipi_ruolo
            WHERE utility_id = %s AND tipo_ruolo_id = %s$$,
         (SELECT u1 FROM _u), (SELECT ef FROM _u)),
  'P0001',
  format('Aziende che gestiscono l''utility %s: %s. L''utility resta ammessa per l''emittente fiscale.',
         (SELECT u1_codice FROM _u), 1),
  '10) cancellata: E_UTILITY_EF_GESTITA');

-- Lo spostamento lo ferma per primo il lucchetto di colonna (a10), dove il
-- runner l'ha montato; altrimenti questo guard. Si asserisce il rifiuto.
SELECT throws_ok(
  format($$UPDATE config.utilities_tipi_ruolo SET tipo_ruolo_id = (
              SELECT t.id FROM config.tipi_ruoli t WHERE t.codice_interno = 'FO')
            WHERE utility_id = %s AND tipo_ruolo_id = %s$$,
         (SELECT u1 FROM _u), (SELECT ef FROM _u)),
  'P0001',
  NULL,
  '11) spostata su un altro tipo di ruolo: rifiutata');

SELECT lives_ok(
  format($$UPDATE config.utilities_tipi_ruolo SET meta = '{"nota": "pgtap"}'::jsonb
            WHERE utility_id = %s AND tipo_ruolo_id = %s$$,
         (SELECT u1 FROM _u), (SELECT ef FROM _u)),
  '12) un ritocco che non la fa uscire passa');

SELECT lives_ok(
  format($$UPDATE config.utilities_tipi_ruolo SET attivo = false
            WHERE utility_id = %s AND tipo_ruolo_id = %s$$,
         (SELECT u1 FROM _u), (SELECT cl FROM _u)),
  '13) la riga del cliente non e'' giudicata: si spegne');

-- ============================================================
-- Il seed
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM config.utilities u
     JOIN config.tipi_ruoli t ON t.codice_interno IN ('EF', 'CL')
     LEFT JOIN config.utilities_tipi_ruolo m
       ON m.utility_id = u.id AND m.tipo_ruolo_id = t.id
      AND m.attivo IS TRUE AND m.valido_al IS NULL
      AND (m.valido_dal IS NULL OR m.valido_dal <= script.fn_data_operativa())
    -- le utility del seed, per codice: config.utilities.csv
    WHERE u.codice IN ('ENE', 'GAS', 'ACQ', 'TEL', 'BASE')
      AND m.id IS NULL),
  0,
  '14) ogni utility del seed e'' ammessa per EF e per CL, accesa e senza data di fine');

SELECT * FROM finish();

ROLLBACK;
