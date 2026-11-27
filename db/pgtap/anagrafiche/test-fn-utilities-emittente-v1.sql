-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: le utility di un'azienda (anagrafiche.fn_utilities_emittente) e la
--   tendina del billing account che le usa (anagrafiche.fn_lookup_utilities_per_ba).
--   Brief: brief-db-utility-gestite-dall-emittente §4-bis (C2), §6 (D-U-1, D-U-2), §8-bis (U4).
--   ChangeSet: 20261127-41 (il BB), 20261127-42 (la tendina).
-- ------------------------------------------------------------
-- Elenco test (plan 9):
--  Il BB
--   1) una riga per ogni utility ammessa oggi per l'emittente fiscale
--   2) l'azienda di prova le gestisce tutte, ciascuna con la sua riga
--   3) un'utility tolta resta in elenco, non gestita e senza riga
--   4) un'utility ammessa per EF e non per il cliente: c'e' senza ruolo...
--   5) ...e non c'e' col ruolo del cliente
--   6) i parametri sono quelli effettivi, e personalizzata li segue
--   7) un ruolo che non e' un emittente: E_PARAMETRO_INVALIDO
--  La tendina del billing account
--   8) propone le utility gestite ammesse per il cliente...
--   9) ...e non quella che l'azienda non gestisce
--
-- Scopo:
--  - i casi si COSTRUISCONO: un'azienda nuova (gestisce ogni utility ammessa per
--    EF, dbops.fn_pgtap_crea_emittente), a cui si toglie il telefono (TEL), e
--    un'utility nuova ammessa per EF e non per il cliente;
--  - il test 1 confronta col conteggio della matrice letto qui, non con un numero.
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

CREATE TEMP TABLE _u AS
SELECT (SELECT u.id FROM config.utilities u WHERE u.codice = 'ENE') AS ene,
       (SELECT u.id FROM config.utilities u WHERE u.codice = 'TEL') AS tel;

-- ============================================================
-- Il BB
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM anagrafiche.fn_utilities_emittente((SELECT soggetto_ruolo_id FROM _mondo))),
  (SELECT count(DISTINCT m.utility_id)::int
     FROM config.utilities_tipi_ruolo m
     JOIN config.tipi_ruoli t ON t.id = m.tipo_ruolo_id AND t.codice_interno = 'EF'
    WHERE m.attivo AND (m.valido_dal IS NULL OR m.valido_dal <= script.fn_data_operativa())
      AND (m.valido_al IS NULL OR m.valido_al >= script.fn_data_operativa())),
  '1) una riga per ogni utility ammessa oggi per l''emittente fiscale');

SELECT is(
  (SELECT count(*)::int FROM anagrafiche.fn_utilities_emittente((SELECT soggetto_ruolo_id FROM _mondo)) a
    WHERE NOT a.gestita OR a.riga_id IS NULL),
  0,
  '2) l''azienda di prova le gestisce tutte, ciascuna con la sua riga');

DELETE FROM anagrafiche.emittenti_fiscali_utilities r
 USING _mondo m, _u
 WHERE r.emittente_soggetto_ruolo_id = m.soggetto_ruolo_id AND r.utility_id = _u.tel;

SELECT is(
  (SELECT row(a.gestita, a.riga_id)::text
     FROM anagrafiche.fn_utilities_emittente((SELECT soggetto_ruolo_id FROM _mondo)) a
    WHERE a.utility_id = (SELECT tel FROM _u)),
  row(false, NULL::bigint)::text,
  '3) un''utility tolta resta in elenco, non gestita e senza riga');

-- Un'utility nuova, ammessa per EF e non per il cliente, gestita dall'azienda.
CREATE TEMP TABLE _nuova AS
WITH ins AS (
  INSERT INTO config.utilities (id, codice, codice_interno, descrizione)
  SELECT max(u.id) + 1, 'PGTAP_UE', 'PGTAP_UE', 'pgTAP utility solo EF' FROM config.utilities u
  RETURNING id)
SELECT id FROM ins;
INSERT INTO config.utilities_tipi_ruolo (utility_id, tipo_ruolo_id, attivo)
SELECT n.id, t.id, true FROM _nuova n, config.tipi_ruoli t WHERE t.codice_interno = 'EF';
INSERT INTO anagrafiche.emittenti_fiscali_utilities (emittente_soggetto_ruolo_id, utility_id)
SELECT m.soggetto_ruolo_id, n.id FROM _mondo m, _nuova n;

SELECT ok(
  EXISTS (SELECT 1 FROM anagrafiche.fn_utilities_emittente((SELECT soggetto_ruolo_id FROM _mondo)) a
           WHERE a.utility_id = (SELECT id FROM _nuova) AND a.gestita),
  '4) un''utility ammessa per EF e non per il cliente: c''e'' senza ruolo');

SELECT ok(
  NOT EXISTS (SELECT 1 FROM anagrafiche.fn_utilities_emittente((SELECT soggetto_ruolo_id FROM _mondo), 'CL') a
               WHERE a.utility_id = (SELECT id FROM _nuova)),
  '5) ...e non c''e'' col ruolo del cliente');

UPDATE anagrafiche.emittenti_fiscali_utilities r
   SET arrotondamento_importi_dec = 0
  FROM _mondo m, _u
 WHERE r.emittente_soggetto_ruolo_id = m.soggetto_ruolo_id AND r.utility_id = _u.ene;

SELECT is(
  (SELECT row(a.arrotondamento_importi_dec, a.personalizzata)::text
     FROM anagrafiche.fn_utilities_emittente((SELECT soggetto_ruolo_id FROM _mondo)) a
    WHERE a.utility_id = (SELECT ene FROM _u)),
  row(0::smallint, true)::text,
  '6) i parametri sono quelli effettivi, e personalizzata li segue');

CREATE TEMP TABLE _ba AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('utilities emittente', (SELECT ene FROM _u),
                                             (SELECT soggetto_ruolo_id FROM _mondo));

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $$SELECT * FROM anagrafiche.fn_utilities_emittente(%s)$$,
    (SELECT soggetto_ruolo_id FROM _ba))),
  'E_PARAMETRO_INVALIDO',
  '7) il ruolo del cliente non e'' un emittente: E_PARAMETRO_INVALIDO');

-- ============================================================
-- La tendina del billing account
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM anagrafiche.fn_lookup_utilities_per_ba((SELECT billing_account_id FROM _ba), 'CL') l
           WHERE l.utility_id = (SELECT ene FROM _u)),
  '8) la tendina propone le utility gestite ammesse per il cliente');

SELECT ok(
  NOT EXISTS (SELECT 1 FROM anagrafiche.fn_lookup_utilities_per_ba((SELECT billing_account_id FROM _ba), 'CL') l
               WHERE l.utility_id = (SELECT tel FROM _u)),
  '9) ...e non quella che l''azienda non gestisce');

SELECT * FROM finish();

ROLLBACK;
