-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- L'indirizzo libero in due forme, decise dallo stato (2026-10-18).
-- Richiesta BE in brief-db-processi-accensione-per-ambiente §6.11 (R-BE-8,
-- -9, -10 del BE), decisioni D-1 … D-4 di Tid. ChangeSet 20261018-80 …
-- -99, 20261019-01 … -04.
--
-- Elenco test (plan 28: i 26 qui sotto, piu' 16a e 17a, che preparano 16 e 17):
--  1-2) il guard della forma gira DOPO il normalize, sulle due tabelle
--       (nome COLLATE "C"): un a10 vedrebbe lo stato prima del default
--  3)   i due CHECK free_requirements: forma estera = localita' sola
--  4)   il builder pgTAP scrive l'indirizzo italiano nella forma del
--       catalogo (comune e CAP, niente localita')
--  -- forma del catalogo (Italia, flag acceso), via UPDATE --
--  5)   senza comune: E_INDIRIZZO_LIBERO_INCOMPLETO
--  6)   ... e il campo arriva nel canale COLUMN (comune_id)
--  7)   senza CAP: E_INDIRIZZO_LIBERO_INCOMPLETO
--  8-10) localita', codice postale, regione: E_INDIRIZZO_CAMPO_ALTRA_FORMA
--  11)  la sotto-localita' (frazione) e' ammessa
--  12)  CAP di un altro comune: E_INDIRIZZO_CAP_ALTRO_COMUNE
--  -- forma estera (Francia, flag spento) --
--  13)  localita' sola, senza codice postale: passa
--  14)  localita' fatta di spazi: il normalize la porta a NULL, manca
--  15)  comune italiano su un indirizzo francese: E_INDIRIZZO_COMUNE_ALTRO_STATO
--  16)  stato non detto: il normalize scrive lo stato proposto (Italia)
--  -- la madre del soggetto in jsonb (D-4) --
--  17)  forma estera via fn_crea_indirizzo_soggetto: passa, postal_code NULL
--  18)  chiave postal_box (il nome ritirato): E_CAMPO_NON_AMMESSO
--  19)  Italia senza comune via madre: E_INDIRIZZO_LIBERO_INCOMPLETO
--  20)  la madre del ruolo scrive la forma estera (stessi BB)
--  -- lo stato da un codice ISO2 (D-1) --
--  21)  AM indica due stati (righe storiche): E_STATO_ISO2_AMBIGUO
--  22)  un codice che non c'e': NULL (il chiamante giudica)
--  23)  lo stato proposto e' l'Italia (STATO_PROPOSTO_ISO2 = IT)
--  -- il flag si accende dopo (D-2) --
--  24)  una riga francese in forma estera resta valida se non la si tocca
--  25)  ... e se si tocca l'indirizzo vale la forma del catalogo
--  -- per ultimo, cambia la configurazione --
--  26)  STATO_PROPOSTO_ISO2 vuoto: E_CONFIG_MANCANTE, nessun ripiego
--
-- Scopo:
--  - provare il guard anagrafiche.trgfn_indirizzi_guard_forma_libera, il
--    normalize, le due madri e i BB dello stato COSTRUENDO i casi (regola
--    zero: il test non legge la popolazione di oggi).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- La fixture crea il soggetto (padre) e i suoi indirizzi nello stesso
-- builder, che apre e richiude da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(28);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('pgTAP indirizzo due forme', 3, script.fn_stato_id_da_iso2('IT')) AS soggetto_id,
       script.fn_stato_id_da_iso2('IT') AS it_id,
       script.fn_stato_id_da_iso2('FR') AS fr_id;

-- La riga del soggetto (SEDELEG, obbligatoria per SC) e il suo comune.
ALTER TABLE _f ADD COLUMN riga_id bigint, ADD COLUMN comune_id integer, ADD COLUMN cap_id integer,
               ADD COLUMN cap_altro_id integer, ADD COLUMN cap_altro text;
UPDATE _f SET riga_id = s.id, comune_id = s.comune_id, cap_id = s.codice_postale_id
  FROM anagrafiche.indirizzi_soggetti s
 WHERE s.soggetto_id = _f.soggetto_id;

-- Un CAP di un ALTRO comune, scelto una volta (ordine per id).
UPDATE _f SET cap_altro_id = x.id, cap_altro = x.codice
  FROM (SELECT cp.id, cp.codice
          FROM config.codici_postali cp, _f
         WHERE cp.comune_id <> _f.comune_id
         ORDER BY cp.id
         LIMIT 1) x;

-- Riporta la riga alla forma del catalogo prima di ogni caso.
CREATE TEMP TABLE _sql ON COMMIT DROP AS
SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET stato_id = %s, comune_id = %s, codice_postale_id = %s, locality = NULL, postal_code = NULL, administrative_area = NULL, sublocality = NULL WHERE id = %s',
              it_id, comune_id, cap_id, riga_id) AS reset_it
  FROM _f;

-- ============================================================
-- 1-3) Forma: ordine dei trigger e CHECK
-- ============================================================
SELECT ok(
    (SELECT 'trg_indirizzi_soggetti_z10_guard_forma_libera_ins_upd' COLLATE "C"
            > 'trg_indirizzi_soggetti_normalize_ins_upd' COLLATE "C")
    AND EXISTS (SELECT 1 FROM pg_trigger
                 WHERE tgrelid = 'anagrafiche.indirizzi_soggetti'::regclass
                   AND tgname = 'trg_indirizzi_soggetti_z10_guard_forma_libera_ins_upd')
    AND EXISTS (SELECT 1 FROM pg_trigger
                 WHERE tgrelid = 'anagrafiche.indirizzi_soggetti'::regclass
                   AND tgname = 'trg_indirizzi_soggetti_normalize_ins_upd'),
    '1) indirizzi_soggetti: il guard della forma gira dopo il normalize');

SELECT ok(
    (SELECT 'trg_indirizzi_z10_guard_forma_libera_ins_upd' COLLATE "C"
            > 'trg_indirizzi_normalize_ins_upd' COLLATE "C")
    AND EXISTS (SELECT 1 FROM pg_trigger
                 WHERE tgrelid = 'anagrafiche.indirizzi'::regclass
                   AND tgname = 'trg_indirizzi_z10_guard_forma_libera_ins_upd')
    AND EXISTS (SELECT 1 FROM pg_trigger
                 WHERE tgrelid = 'anagrafiche.indirizzi'::regclass
                   AND tgname = 'trg_indirizzi_normalize_ins_upd'),
    '2) indirizzi: il guard della forma gira dopo il normalize');

SELECT ok(
    (SELECT bool_and(pg_get_constraintdef(c.oid) LIKE '%locality IS NOT NULL%'
                     AND pg_get_constraintdef(c.oid) NOT LIKE '%administrative_area%'
                     AND pg_get_constraintdef(c.oid) NOT LIKE '%postal_code%'
                     AND pg_get_constraintdef(c.oid) NOT LIKE '%postal_box%')
       FROM pg_constraint c
      WHERE c.conname IN ('chk_indirizzi_free_requirements', 'chk_indirizzi_soggetti_free_requirements'))
    AND (SELECT count(*) FROM pg_constraint c
          WHERE c.conname IN ('chk_indirizzi_free_requirements', 'chk_indirizzi_soggetti_free_requirements')) = 2,
    '3) i due CHECK restano come rete, con la forma estera = localita'' sola');

-- ============================================================
-- 4) Il builder scrive la forma del catalogo
-- ============================================================
SELECT ok(
    (SELECT s.comune_id IS NOT NULL AND s.codice_postale_id IS NOT NULL
            AND s.locality IS NULL AND s.postal_code IS NULL
       FROM anagrafiche.indirizzi_soggetti s, _f WHERE s.id = _f.riga_id),
    '4) il builder pgTAP scrive l''indirizzo italiano con comune e CAP del catalogo');

-- ============================================================
-- 5-12) Forma del catalogo (Italia)
-- ============================================================
SELECT throws_like(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET comune_id = NULL WHERE id = %s', riga_id) FROM _f),
    '%manca il comune%',
    '5) Italia senza comune: E_INDIRIZZO_LIBERO_INCOMPLETO');

CREATE TEMP TABLE _col (colonna text) ON COMMIT DROP;
DO $t6$
DECLARE v_col text;
BEGIN
    BEGIN
        UPDATE anagrafiche.indirizzi_soggetti SET comune_id = NULL
         WHERE id = (SELECT riga_id FROM _f);
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_col = COLUMN_NAME;
    END;
    INSERT INTO _col VALUES (v_col);
END $t6$;
SELECT is((SELECT colonna FROM _col), 'comune_id',
    '6) il campo che manca arriva nel canale COLUMN');

SELECT throws_like(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET codice_postale_id = NULL WHERE id = %s', riga_id) FROM _f),
    '%manca il CAP%',
    '7) Italia senza CAP: E_INDIRIZZO_LIBERO_INCOMPLETO');

SELECT throws_like(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET locality = %L WHERE id = %s', 'Roma', riga_id) FROM _f),
    '%non si compila la localit%',
    '8) localita'' nella forma del catalogo: E_INDIRIZZO_CAMPO_ALTRA_FORMA');

SELECT throws_like(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET postal_code = %L WHERE id = %s', '00100', riga_id) FROM _f),
    '%non si compila il codice postale%',
    '9) codice postale libero nella forma del catalogo: E_INDIRIZZO_CAMPO_ALTRA_FORMA');

SELECT throws_like(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET administrative_area = %L WHERE id = %s', 'RM', riga_id) FROM _f),
    '%non si compila la regione o provincia%',
    '10) regione nella forma del catalogo: E_INDIRIZZO_CAMPO_ALTRA_FORMA');

SELECT lives_ok(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET sublocality = %L WHERE id = %s', 'Frazione pgTAP', riga_id) FROM _f),
    '11) la sotto-localita'' (frazione) e'' ammessa nella forma del catalogo');

SELECT throws_like(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET codice_postale_id = %s WHERE id = %s', cap_altro_id, riga_id) FROM _f),
    '%Il CAP % non % del comune %',
    '12) CAP di un altro comune: E_INDIRIZZO_CAP_ALTRO_COMUNE');

-- ============================================================
-- 13-16) Forma estera (Francia, catalogo spento)
-- ============================================================
SELECT lives_ok(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET stato_id = %s, comune_id = NULL, codice_postale_id = NULL, sublocality = NULL, locality = %L WHERE id = %s',
                   fr_id, 'Lione', riga_id) FROM _f),
    '13) Francia: la localita'' basta, il codice postale e'' facoltativo');

SELECT throws_like(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET locality = %L WHERE id = %s', '   ', riga_id) FROM _f),
    '%manca la localit%',
    '14) una localita'' di soli spazi e'' vuota (normalize): E_INDIRIZZO_LIBERO_INCOMPLETO');

SELECT throws_like(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET comune_id = %s, codice_postale_id = %s, locality = NULL WHERE id = %s',
                   comune_id, cap_id, riga_id) FROM _f),
    '%Il comune % non % in Francia%',
    '15) comune italiano su un indirizzo francese: E_INDIRIZZO_COMUNE_ALTRO_STATO');

SELECT lives_ok((SELECT reset_it FROM _sql), '16a) la riga torna alla forma del catalogo');
UPDATE anagrafiche.indirizzi_soggetti SET stato_id = NULL WHERE id = (SELECT riga_id FROM _f);
SELECT is(
    (SELECT s.stato_id FROM anagrafiche.indirizzi_soggetti s, _f WHERE s.id = _f.riga_id),
    (SELECT it_id FROM _f),
    '16) stato non detto: il normalize scrive lo stato proposto');

-- ============================================================
-- 17-20) Le madri in jsonb
-- ============================================================
SELECT lives_ok(
    (SELECT format('SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)',
                   soggetto_id,
                   jsonb_build_object('tipo_indirizzo_codice_interno', 'SPED',
                                      'indirizzo_libero', '12 rue pgTAP',
                                      'stato_id', fr_id,
                                      'locality', 'Parigi'))
       FROM _f),
    '17a) madre del soggetto: forma estera senza codice postale');
SELECT ok(
    (SELECT s.locality = 'Parigi' AND s.postal_code IS NULL AND s.comune_id IS NULL
       FROM anagrafiche.indirizzi_soggetti s
       JOIN config.tipi_indirizzi ti ON ti.id = s.tipo_indirizzo_id, _f
      WHERE s.soggetto_id = _f.soggetto_id AND ti.codice_interno = 'SPED'),
    '17) la madre del soggetto scrive la forma estera (D-4)');

SELECT throws_like(
    (SELECT format('SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)',
                   soggetto_id,
                   jsonb_build_object('tipo_indirizzo_codice_interno', 'POSTA',
                                      'indirizzo_libero', '12 rue pgTAP',
                                      'stato_id', fr_id,
                                      'locality', 'Parigi',
                                      'postal_box', '75001'))
       FROM _f),
    '%campo postal_box non si pu%',
    '18) la chiave ritirata postal_box: E_CAMPO_NON_AMMESSO');

SELECT throws_like(
    (SELECT format('SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)',
                   soggetto_id,
                   jsonb_build_object('tipo_indirizzo_codice_interno', 'POSTA',
                                      'indirizzo_libero', 'Via pgTAP 9',
                                      'stato_id', it_id,
                                      'locality', 'Roma'))
       FROM _f),
    '%manca il comune%',
    '19) Italia senza comune via madre: E_INDIRIZZO_LIBERO_INCOMPLETO');

-- 20) La madre del ruolo: un tipo che la matrice del CL ammette e che il
--     ruolo non ha ancora (scelto una volta, ordine per id).
CREATE TEMP TABLE _r ON COMMIT DROP AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(soggetto_id, 'CL', it_id) AS ruolo_id FROM _f;
ALTER TABLE _r ADD COLUMN tipo_id integer;
UPDATE _r SET tipo_id = (
    SELECT m.tipo_indirizzo_id
      FROM config.tipi_ruolo_tipi_indirizzo m
      JOIN config.tipi_ruoli tr ON tr.id = m.tipo_ruolo_id
     WHERE tr.codice_interno = 'CL' AND m.attivo
       AND NOT EXISTS (SELECT 1 FROM anagrafiche.indirizzi i
                        WHERE i.soggetto_ruolo_id = _r.ruolo_id
                          AND i.tipo_indirizzo_id = m.tipo_indirizzo_id)
     ORDER BY m.tipo_indirizzo_id
     LIMIT 1);
SELECT CASE WHEN (SELECT tipo_id FROM _r) IS NULL
    THEN skip('20) la matrice del CL non ha un tipo libero: niente da provare sul ruolo', 1)
    ELSE is(
        (SELECT anagrafiche.fn_crea_indirizzi_ruolo(
                    _r.ruolo_id,
                    jsonb_build_array(jsonb_build_object(
                        'tipo_indirizzo_id', _r.tipo_id,
                        'indirizzo_libero',  '12 rue pgTAP',
                        'stato_id',          _f.fr_id,
                        'locality',          'Parigi',
                        'postal_code',       '75001')))
           FROM _r, _f),
        1,
        '20) la madre del ruolo scrive la forma estera, coi BB comuni')
    END;

-- ============================================================
-- 21-23) Lo stato da un codice ISO2
-- ============================================================
SELECT throws_like(
    $$SELECT script.fn_stato_id_da_iso2('AM', 'pgTAP')$$,
    '%AM indica 2 stati%',
    '21) un codice con due righe storiche: E_STATO_ISO2_AMBIGUO, mai una a caso');

SELECT is(script.fn_stato_id_da_iso2('XX', 'pgTAP'), NULL::integer,
    '22) un codice che non c''e'': NULL, il «non trovato» lo giudica il chiamante');

SELECT is(script.fn_stato_proposto_id('pgTAP'), (SELECT it_id FROM _f),
    '23) lo stato proposto e'' l''Italia');

-- ============================================================
-- 24-25) Il flag si accende dopo: le righe di prima restano finche'
--        non si toccano
-- ============================================================
UPDATE config.stati SET catalogo_comuni_completo = true WHERE id = (SELECT fr_id FROM _f);

SELECT lives_ok(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET storicizza = storicizza WHERE soggetto_id = %L::uuid AND locality = %L',
                   soggetto_id, 'Parigi') FROM _f),
    '24) Francia col catalogo acceso: la riga in forma estera, non toccata, passa');

SELECT throws_like(
    (SELECT format('UPDATE anagrafiche.indirizzi_soggetti SET locality = %L WHERE soggetto_id = %L::uuid AND locality = %L',
                   'Marsiglia', soggetto_id, 'Parigi') FROM _f),
    '%manca il comune%',
    '25) ... toccata, vale la forma del catalogo');

-- ============================================================
-- 26) Per ultimo: la configurazione vuota non ripiega
-- ============================================================
UPDATE config.parameters SET default_value = '' WHERE code = 'STATO_PROPOSTO_ISO2';
SELECT throws_like(
    $$SELECT script.fn_stato_proposto_id('pgTAP')$$,
    '%STATO_PROPOSTO_ISO2%',
    '26) STATO_PROPOSTO_ISO2 vuoto: E_CONFIG_MANCANTE, nessun ripiego');

SELECT * FROM finish();
ROLLBACK;
