-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Gli indirizzi: singolare e plurale per il ruolo e per il soggetto
-- (2026-10-19). R-BE-6 e R-BE-12 del BE, decisione D-16a di Tid,
-- brief-db-processi-accensione-per-ambiente §6.10 (la richiesta) e §6.16 (la
-- risposta). ChangeSet 20261019-36 … -39.
--
-- Elenco test (plan 14):
--  -- il BB della copia degli obbligatori (fn_indirizzi_con_obbligatori) --
--  1)   una copia del primo per ogni tipo che manca, in ordine di tipo, una per tipo
--  2)   elenco vuoto: nessuna copia
--  -- la singolare del ruolo (fn_crea_indirizzo_ruolo) --
--  3)   un indirizzo del ruolo: l'id, il tipo, nessuna istanza
--  4)   lo stesso tipo di nuovo: lo rifiuta il vincolo
--  5)   un indirizzo di un'istanza: l'istanza sulla riga
--  6)   una chiave estranea: E_CAMPO_NON_AMMESSO
--  7)   un ruolo che non c'e': E_SOGGETTO_RUOLO_NON_TROVATO
--  -- la plurale del ruolo (fn_crea_indirizzi_ruolo) --
--  8)   un tipo che il ruolo ha solo per un'istanza: l'indirizzo del ruolo nasce
--       (prima del 20261019-38 si saltava)
--  9)   l'istanza nella plurale: E_CAMPO_NON_AMMESSO (passa solo dalla singolare)
--  -- la plurale del soggetto (fn_crea_indirizzi_soggetto) --
--  10)  un tipo che il soggetto ha gia': si salta
--  11)  senza l'obbligatorio: nasce l'indirizzo e la copia per l'obbligatorio
--  12)  ... e la copia porta l'indirizzo del primo
--  13)  con la copia spenta: nasce solo l'indirizzo chiesto
--  14)  un soggetto che non c'e': E_SOGGETTO_NOT_FOUND
--
-- Scopo:
--  - provare le quattro madri e il BB COSTRUENDO soggetto, ruolo, istanza e
--    indirizzi (regola zero: il test non legge gli indirizzi di oggi).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- La fixture crea il soggetto (padre) e i suoi indirizzi nello stesso
-- builder, che apre e richiude da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT script.fn_stato_id_da_iso2('IT') AS it_id,
       dbops.fn_pgtap_crea_soggetto_pg('pgTAP indirizzi singolare e plurale', 3,
                                        script.fn_stato_id_da_iso2('IT')) AS soggetto_id;

-- Il ruolo con un'istanza: un cliente col suo billing account e la sua
-- istanza, dal builder (un'istanza nasce e vive col suo billing account).
-- Per il cliente sono ammessi POSTA, SPED, RES (obbligatorio FATT).
ALTER TABLE _f ADD COLUMN sr_id bigint, ADD COLUMN istanza_id bigint;
UPDATE _f SET (sr_id, istanza_id) = (
    SELECT c.soggetto_ruolo_id, c.istanza_utility_id
      FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP indirizzi singolare e plurale') c);

-- Un indirizzo libero valido per l'Italia, nella forma che il guard pretende;
-- il tipo si aggiunge caso per caso.
CREATE TEMP TABLE _el ON COMMIT DROP AS
SELECT jsonb_strip_nulls(
           jsonb_build_object('indirizzo_libero', 'Via pgTAP indirizzi 1', 'stato_id', _f.it_id)
           || to_jsonb(fm)) AS base
  FROM _f, dbops.fn_pgtap_indirizzo_libero_forma(_f.it_id) fm;

-- ============================================================
-- 1-2) Il BB della copia degli obbligatori
-- ============================================================
SELECT is(
    anagrafiche.fn_indirizzi_con_obbligatori(
        '[{"tipo_indirizzo_id": 1, "x": "a"}]'::jsonb, ARRAY[5, 3, 5, 1, NULL]),
    '[{"tipo_indirizzo_id": 1, "x": "a"}, {"tipo_indirizzo_id": 3, "x": "a"}, {"tipo_indirizzo_id": 5, "x": "a"}]'::jsonb,
    '1) una copia del primo per ogni tipo che manca, in ordine di tipo, una per tipo');

SELECT is(
    anagrafiche.fn_indirizzi_con_obbligatori('[]'::jsonb, ARRAY[1, 2]),
    '[]'::jsonb,
    '2) elenco vuoto: nessuna copia');

-- ============================================================
-- 3-7) La singolare del ruolo
-- ============================================================
CREATE TEMP TABLE _r3 ON COMMIT DROP AS
SELECT anagrafiche.fn_crea_indirizzo_ruolo(
           _f.sr_id, _el.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'POSTA')) AS id
  FROM _f, _el;

SELECT is(
    (SELECT ti.codice_interno || '/' || coalesce(i.istanza_utility_id::text, 'ruolo')
       FROM anagrafiche.indirizzi i
       JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id, _r3, _f
      WHERE i.id = _r3.id AND i.soggetto_ruolo_id = _f.sr_id),
    'POSTA/ruolo',
    '3) un indirizzo del ruolo: l''id, il tipo, nessuna istanza');

SELECT throws_ok(
    (SELECT format('SELECT anagrafiche.fn_crea_indirizzo_ruolo(%s, %L::jsonb)',
                   _f.sr_id, _el.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'POSTA'))
       FROM _f, _el),
    '23505', NULL,
    '4) lo stesso tipo di nuovo: lo rifiuta uq_indirizzi_ruolo_tipo_no_istanza');

CREATE TEMP TABLE _r5 ON COMMIT DROP AS
SELECT anagrafiche.fn_crea_indirizzo_ruolo(
           _f.sr_id, _el.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'SPED',
                                                    'istanza_utility_id', _f.istanza_id)) AS id
  FROM _f, _el;

SELECT is(
    (SELECT i.istanza_utility_id FROM anagrafiche.indirizzi i, _r5 WHERE i.id = _r5.id),
    (SELECT istanza_id FROM _f),
    '5) un indirizzo di un''istanza: l''istanza sulla riga');

SELECT throws_like(
    (SELECT format('SELECT anagrafiche.fn_crea_indirizzo_ruolo(%s, %L::jsonb)',
                   _f.sr_id, _el.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'POSTA',
                                                            'postal_box', 'X'))
       FROM _f, _el),
    '%postal_box%',
    '6) una chiave estranea: E_CAMPO_NON_AMMESSO');

SELECT throws_like(
    (SELECT format('SELECT anagrafiche.fn_crea_indirizzo_ruolo(-1, %L::jsonb)',
                   _el.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'POSTA'))
       FROM _el),
    '%-1%non esiste%',
    '7) un ruolo che non c''e'': E_SOGGETTO_RUOLO_NON_TROVATO');

-- ============================================================
-- 8-9) La plurale del ruolo
-- ============================================================
-- SPED il ruolo ce l'ha solo per l'istanza (test 5).
CREATE TEMP TABLE _r8 ON COMMIT DROP AS
SELECT anagrafiche.fn_crea_indirizzi_ruolo(
           _f.sr_id, jsonb_build_array(_el.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'SPED'))) AS n
  FROM _f, _el;

SELECT is(
    (SELECT n::text FROM _r8) || '/'
        || (SELECT count(*) FROM anagrafiche.indirizzi i
              JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id, _f
             WHERE i.soggetto_ruolo_id = _f.sr_id AND ti.codice_interno = 'SPED'
               AND i.istanza_utility_id IS NULL)::text,
    '1/1',
    '8) un tipo che il ruolo ha solo per un''istanza: l''indirizzo del ruolo nasce');

SELECT throws_like(
    (SELECT format('SELECT anagrafiche.fn_crea_indirizzi_ruolo(%s, %L::jsonb)',
                   _f.sr_id, jsonb_build_array(_el.base || jsonb_build_object(
                                 'tipo_indirizzo_codice_interno', 'RES', 'istanza_utility_id', _f.istanza_id)))
       FROM _f, _el),
    '%istanza_utility_id%',
    '9) l''istanza nella plurale: E_CAMPO_NON_AMMESSO, passa solo dalla singolare');

-- ============================================================
-- 10-14) La plurale del soggetto
-- ============================================================
SELECT is(
    (SELECT anagrafiche.fn_crea_indirizzi_soggetto(
                _f.soggetto_id,
                jsonb_build_array(_el.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'SEDELEG')))
       FROM _f, _el),
    0,
    '10) un tipo che il soggetto ha gia'': si salta');

-- Senza l'obbligatorio (SEDELEG) il soggetto sta in piedi solo dentro la
-- finestra dei differiti: si apre, si toglie SEDELEG, si scrive, si richiude
-- (i differiti verificano che l'obbligatorio ci sia).
SET CONSTRAINTS ALL DEFERRED;
DELETE FROM anagrafiche.indirizzi_soggetti s
 USING _f, config.tipi_indirizzi ti
 WHERE s.soggetto_id = _f.soggetto_id AND ti.id = s.tipo_indirizzo_id AND ti.codice_interno = 'SEDELEG';

CREATE TEMP TABLE _s11 ON COMMIT DROP AS
SELECT anagrafiche.fn_crea_indirizzi_soggetto(
           _f.soggetto_id,
           jsonb_build_array(_el.base || jsonb_build_object(
               'tipo_indirizzo_codice_interno', 'FATT', 'indirizzo_libero', 'Via pgTAP fatture 7'))) AS n
  FROM _f, _el;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT is(
    (SELECT n FROM _s11),
    2,
    '11) senza l''obbligatorio: nasce l''indirizzo e la copia per l''obbligatorio');

SELECT is(
    (SELECT s.indirizzo_libero
       FROM anagrafiche.indirizzi_soggetti s
       JOIN config.tipi_indirizzi ti ON ti.id = s.tipo_indirizzo_id, _f
      WHERE s.soggetto_id = _f.soggetto_id AND ti.codice_interno = 'SEDELEG'),
    'Via pgTAP fatture 7',
    '12) ... e la copia porta l''indirizzo del primo');

SET CONSTRAINTS ALL DEFERRED;
DELETE FROM anagrafiche.indirizzi_soggetti s
 USING _f, config.tipi_indirizzi ti
 WHERE s.soggetto_id = _f.soggetto_id AND ti.id = s.tipo_indirizzo_id
   AND ti.codice_interno IN ('SEDELEG', 'SPED');

CREATE TEMP TABLE _s13 ON COMMIT DROP AS
SELECT anagrafiche.fn_crea_indirizzi_soggetto(
           _f.soggetto_id,
           jsonb_build_array(_el.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'SPED')),
           false) AS n
  FROM _f, _el;

SELECT is(
    (SELECT n::text FROM _s13) || '/'
        || (SELECT count(*) FROM anagrafiche.indirizzi_soggetti s
              JOIN config.tipi_indirizzi ti ON ti.id = s.tipo_indirizzo_id, _f
             WHERE s.soggetto_id = _f.soggetto_id AND ti.codice_interno = 'SEDELEG')::text,
    '1/0',
    '13) con la copia spenta: nasce solo l''indirizzo chiesto');

-- L'obbligatorio torna, dalla singolare, prima di richiudere i differiti.
SELECT anagrafiche.fn_crea_indirizzo_soggetto(
           _f.soggetto_id, _el.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'SEDELEG'))
  FROM _f, _el;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT throws_like(
    (SELECT format('SELECT anagrafiche.fn_crea_indirizzi_soggetto(%L::uuid, %L::jsonb)',
                   gen_random_uuid(), jsonb_build_array(_el.base || jsonb_build_object('tipo_indirizzo_codice_interno', 'SPED')))
       FROM _el),
    '%non trovato%',
    '14) un soggetto che non c''e'': E_SOGGETTO_NOT_FOUND');

SELECT * FROM finish();
ROLLBACK;
