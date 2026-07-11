-- ============================================================
-- test-indirizzi-documenti-simmetria-v1.sql
-- Copertura: brief-db-indirizzi-documenti-simmetria-e-cascata §6
-- ------------------------------------------------------------
-- Indice test (1..14):
--  1) seed DDT: solo CON ammesso
--  2) seed ORDINI: CON + FATT
--  3) seed PREVENTIVI: FATT, CON, FORNITURA, RES
--  4) SPED ritirato: non presente in nessun ambito
--  5) obbligatori: CON@DDT e FATT@FATTURE marcati obbligatorio
--  6) CHECK ambito: accetta i nuovi ambiti (OFFERTE/CONTRATTI/ACQUISTI_DDT)
--  7) CHECK ambito: rifiuta un ambito non previsto
--  8) fn_indirizzi_obbligatori_mancanti: DDT senza CON -> {CON}
--  9) fn_indirizzi_obbligatori_mancanti: DDT con CON -> {}
-- 10) fn_snapshot_indirizzo: id inesistente -> errore
-- 11) fn_snapshot_indirizzo: shape (display + intestazione) su indirizzo reale
-- 12) fn_snapshot_indirizzo: espone origine_soggetto_ruolo_id
-- 13) simmetria: le 6 tabelle *_indirizzi documento esistono
-- 14) tipo colonna: tipo_indirizzo_id e' integer ovunque (allineato a config)
-- ============================================================
BEGIN;
SELECT plan(14);

-- Riferimenti tipo (id per codice_interno).
CREATE TEMP TABLE tmp_ti AS
SELECT
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON')       AS con_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT')      AS fatt_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FORNITURA') AS forn_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'RES')       AS res_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'SPED')      AS sped_id;

-- 1) DDT: solo CON.
SELECT is(
  (SELECT array_agg(tipo_indirizzo_id ORDER BY tipo_indirizzo_id)
     FROM config.tipi_indirizzi_allowed
    WHERE ambito = 'DDT' AND attivo),
  ARRAY[(SELECT con_id FROM tmp_ti)]::integer[],
  '1) whitelist DDT: solo CON'
);

-- 2) ORDINI: CON + FATT.
SELECT is(
  (SELECT array_agg(tipo_indirizzo_id ORDER BY tipo_indirizzo_id)
     FROM config.tipi_indirizzi_allowed
    WHERE ambito = 'ORDINI' AND attivo),
  (SELECT array_agg(x ORDER BY x) FROM unnest(ARRAY[
      (SELECT con_id FROM tmp_ti), (SELECT fatt_id FROM tmp_ti)]) x)::integer[],
  '2) whitelist ORDINI: CON + FATT'
);

-- 3) PREVENTIVI: FATT, CON, FORNITURA, RES (4 tipi).
SELECT is(
  (SELECT count(*)::int FROM config.tipi_indirizzi_allowed
    WHERE ambito = 'PREVENTIVI' AND attivo),
  4, '3) whitelist PREVENTIVI: 4 tipi (FATT,CON,FORNITURA,RES)'
);

-- 4) SPED ritirato da ogni ambito documento.
SELECT is(
  (SELECT count(*)::int FROM config.tipi_indirizzi_allowed
    WHERE tipo_indirizzo_id = (SELECT sped_id FROM tmp_ti)),
  0, '4) SPED ritirato: assente da tutti gli ambiti'
);

-- 5) Obbligatori: CON@DDT e FATT@FATTURE.
SELECT is(
  (SELECT count(*)::int FROM config.tipi_indirizzi_allowed
    WHERE obbligatorio IS TRUE
      AND ((ambito = 'DDT'     AND tipo_indirizzo_id = (SELECT con_id  FROM tmp_ti))
        OR (ambito = 'FATTURE' AND tipo_indirizzo_id = (SELECT fatt_id FROM tmp_ti)))),
  2, '5) obbligatori: CON@DDT e FATT@FATTURE'
);

-- 6) CHECK ambito accetta i nuovi ambiti (insert + rollback al savepoint).
SAVEPOINT sp_chk_ok;
SELECT lives_ok($$
  INSERT INTO config.tipi_indirizzi_allowed (ambito, tipo_indirizzo_id)
  SELECT a, (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')
    FROM unnest(ARRAY['OFFERTE','CONTRATTI','ACQUISTI_DDT']) a
  ON CONFLICT DO NOTHING
$$, '6) CHECK ambito: accetta OFFERTE/CONTRATTI/ACQUISTI_DDT');
ROLLBACK TO SAVEPOINT sp_chk_ok;

-- 7) CHECK ambito rifiuta un ambito non previsto.
SELECT throws_ok($$
  INSERT INTO config.tipi_indirizzi_allowed (ambito, tipo_indirizzo_id)
  VALUES ('AMBITO_INESISTENTE', (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON'))
$$, '23514', NULL, '7) CHECK ambito: rifiuta ambito non previsto');

-- 8) Helper: DDT senza CON -> mancante CON.
SELECT is(
  script.fn_indirizzi_obbligatori_mancanti('DDT', ARRAY[]::integer[]),
  ARRAY['CON']::text[],
  '8) fn_indirizzi_obbligatori_mancanti DDT vuoto -> {CON}'
);

-- 9) Helper: DDT con CON -> nessun mancante.
SELECT is(
  script.fn_indirizzi_obbligatori_mancanti('DDT', ARRAY[(SELECT con_id FROM tmp_ti)]),
  ARRAY[]::text[],
  '9) fn_indirizzi_obbligatori_mancanti DDT con CON -> {}'
);

-- 10) fn_snapshot_indirizzo: id inesistente -> errore.
SELECT throws_ok(
  $$ SELECT snapshot FROM script.fn_snapshot_indirizzo(999999999) $$,
  'P0001', NULL, '10) fn_snapshot_indirizzo id inesistente -> errore'
);

-- 11-12) fn_snapshot_indirizzo su un indirizzo reale (se il DB ne ha uno
--        risolvibile via vw_indirizzi_resolved_ruolo). Skip condizionale.
CREATE TEMP TABLE tmp_ind AS
SELECT indirizzo_id
  FROM anagrafiche.vw_indirizzi_resolved_ruolo
 WHERE indirizzo_display IS NOT NULL
 LIMIT 1;

SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_ind)
  THEN skip('nessun indirizzo risolvibile nel DB: shape non testabile qui', 1)
  ELSE ok(
    (SELECT (snapshot ? 'display')
       FROM script.fn_snapshot_indirizzo((SELECT indirizzo_id FROM tmp_ind))),
    '11) fn_snapshot_indirizzo: snapshot contiene display'
  )
END;

SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM tmp_ind)
  THEN skip('nessun indirizzo risolvibile nel DB', 1)
  ELSE ok(
    (SELECT origine_soggetto_ruolo_id IS NOT NULL
       FROM script.fn_snapshot_indirizzo((SELECT indirizzo_id FROM tmp_ind))),
    '12) fn_snapshot_indirizzo: espone origine_soggetto_ruolo_id'
  )
END;

-- 13) Simmetria: le 6 tabelle *_indirizzi documento esistono.
SELECT is(
  (SELECT count(*)::int
     FROM information_schema.tables
    WHERE table_schema = 'vendite'
      AND table_name IN ('preventivi_indirizzi','ordini_indirizzi','fatture_indirizzi',
                         'ddt_indirizzi','offerte_commerciali_indirizzi','contratti_indirizzi')),
  6, '13) simmetria: 6 tabelle *_indirizzi vendite presenti'
);

-- 14) tipo_indirizzo_id integer ovunque (allineato a config.tipi_indirizzi.id).
SELECT is(
  (SELECT count(*)::int
     FROM information_schema.columns
    WHERE table_schema = 'vendite'
      AND table_name IN ('preventivi_indirizzi','ordini_indirizzi','fatture_indirizzi',
                         'ddt_indirizzi','offerte_commerciali_indirizzi','contratti_indirizzi')
      AND column_name = 'tipo_indirizzo_id'
      AND data_type <> 'integer'),
  0, '14) tipo_indirizzo_id e'' integer su tutte le tabelle documento'
);

SELECT * FROM finish();
ROLLBACK;
