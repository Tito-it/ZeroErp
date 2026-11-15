-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il trasporto che il cliente non ci deve. Un onere di causale
--   TRASPORTO su una bolla in porto ASSEGNATO o con addebito a TERZI non si
--   emette (script.fn_check_ddt_emittibile punto 3-quater, sollevato da
--   vendite.trgfn_ddt_guard_causale_emissione); in FRANCO, senza modalita' o
--   con un altro onere, nessun motivo.
-- ChangeSet: 20261103-47 (la check), -48 (il gate di emissione); seed della
--   causale TRASPORTO e di ONERE_TRASPORTO (giro 2, §10.1)
-- Brief: brief-db-addebito-trasporto-ordine §10.2, T-3 bis
-- ------------------------------------------------------------
-- Indice test (plan 8):
--   1) il codice e' a catalogo, con la sua classe
--   2) ASSEGNATO + onere di trasporto: il motivo, col numero di riga e la modalita'
--   3) …la capability spegne «Emetti» col motivo
--   4) …l'emissione si rifiuta: E_DDT_TRASPORTO_NON_DOVUTO
--   5) TERZI + onere di trasporto: lo stesso motivo
--   6) FRANCO + onere di trasporto: nessun motivo, si emette
--   7) senza modalita' + onere di trasporto: nessun motivo
--   8) ASSEGNATO + un altro onere (non di trasporto): nessun motivo
--
-- ⚠️ L'articolo di trasporto e' quello del SEED (ONERE_TRASPORTO, causale
--   TRASPORTO): la causale e' 1:1 con l'articolo, e la regola si lega al
--   codice della causale. L'altro onere e' una fixture con una causale propria.
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP trasporto non dovuto');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;
-- L'azione di processo dell'emissione all'utente del contesto: senza, la
-- capability NASCONDE «Emetti» (permesso => nascondi) e il test 3 non vedrebbe
-- il motivo.
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'emetti_ddt'); END $az$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

CREATE TEMP TABLE _caus AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_DTN_1', 'PGT_DTN_1', 'Fixture pgTAP: onere non di trasporto')
    RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE _a AS
SELECT (SELECT a.id FROM catalogo.articoli a WHERE a.codice = 'ONERE_TRASPORTO') AS trasporto,
       dbops.fn_pgtap_crea_articolo('PGT-DTN-ALTRO', false,
         p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                                  WHERE nv.codice_interno = 'SERVIZIO_UNA_TANTUM'),
         p_causale_onere_id  => (SELECT id FROM _caus)) AS altro;

-- Una bolla VENDITA senza ordine, in bozza, con la modalita' data e un onere.
CREATE OR REPLACE FUNCTION pg_temp.bolla(p_etichetta text, p_modalita text, p_onere uuid) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE v_ddt bigint;
BEGIN
  SELECT b.ddt_id INTO v_ddt
    FROM dbops.fn_pgtap_crea_ddt_senza_ordine(p_etichetta, 'DRAFT',
           (SELECT billing_account_id FROM _m)) b;
  UPDATE vendite.ddt
     SET modalita_addebito_trasporto_id = (SELECT ma.id FROM config.modalita_addebito_trasporto ma
                                            WHERE ma.codice_interno = p_modalita)
   WHERE id = v_ddt;
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, prezzo_unitario, iva_id)
  VALUES (v_ddt, 9, p_onere, 'Fixture pgTAP: onere', 1, 15,
          (SELECT i.id FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1));
  RETURN v_ddt;
END $$;

CREATE OR REPLACE FUNCTION pg_temp.motivi(p_ddt bigint) RETURNS jsonb
LANGUAGE sql AS $$
  SELECT script.fn_check_ddt_emittibile(d) FROM vendite.ddt d WHERE d.id = p_ddt
$$;

CREATE OR REPLACE FUNCTION pg_temp.emetti(p_ddt bigint) RETURNS text
LANGUAGE sql AS $$
  SELECT dbops.fn_pgtap_codice_errore(format(
    'SELECT dbops.fn_pgtap_porta_a_stato(''vendite.ddt''::regclass, %s, ''EMESSO'')', p_ddt))
$$;

SELECT is(
  (SELECT ce.classe::text FROM config.codici_errore ce WHERE ce.codice = 'E_DDT_TRASPORTO_NON_DOVUTO'),
  'CONFLITTO_STATO',
  '1) E_DDT_TRASPORTO_NON_DOVUTO e'' a catalogo, CONFLITTO_STATO');

CREATE TEMP TABLE _ass AS SELECT pg_temp.bolla('pgTAP DTN ass', 'ASSEGNATO', (SELECT trasporto FROM _a)) AS id;

SELECT is(
  (SELECT (m ->> 'codice') || '|' || (m -> 'dettaglio' ->> 'riga_nr') || '|' || (m -> 'dettaglio' ->> 'modalita')
     FROM jsonb_array_elements(pg_temp.motivi((SELECT id FROM _ass))) m
    WHERE m ->> 'codice' = 'E_DDT_TRASPORTO_NON_DOVUTO'),
  'E_DDT_TRASPORTO_NON_DOVUTO|9|ASSEGNATO',
  '2) porto assegnato + onere di trasporto: il motivo, col numero di riga e la modalita''');

SELECT is(
  (SELECT (a ->> 'enabled') || '|' || (a ->> 'reason') || '|' || (a ->> 'reason_key')
     FROM jsonb_array_elements(script.fn_available_actions_ddt((SELECT id FROM _ass)) -> 'available_actions') a
    WHERE a ->> 'target_state' = 'EMESSO'),
  'false|TRASPORTO_NON_DOVUTO|vendite.ddt.azione_reason.trasporto_non_dovuto',
  '3) la capability spegne «Emetti» col motivo');

SELECT is(pg_temp.emetti((SELECT id FROM _ass)), 'E_DDT_TRASPORTO_NON_DOVUTO',
  '4) l''emissione si rifiuta: E_DDT_TRASPORTO_NON_DOVUTO');

SELECT is(
  (SELECT m ->> 'codice' FROM jsonb_array_elements(pg_temp.motivi(
            pg_temp.bolla('pgTAP DTN terzi', 'TERZI', (SELECT trasporto FROM _a)))) m
    WHERE m ->> 'codice' = 'E_DDT_TRASPORTO_NON_DOVUTO'),
  'E_DDT_TRASPORTO_NON_DOVUTO',
  '5) addebito a terzi + onere di trasporto: lo stesso motivo');

CREATE TEMP TABLE _fr AS SELECT pg_temp.bolla('pgTAP DTN franco', 'FRANCO', (SELECT trasporto FROM _a)) AS id;

SELECT is(
  pg_temp.motivi((SELECT id FROM _fr))::text || '|' || COALESCE(pg_temp.emetti((SELECT id FROM _fr)), 'emessa'),
  '[]|emessa',
  '6) porto franco + onere di trasporto: nessun motivo, la bolla si emette');

SELECT is(
  pg_temp.motivi(pg_temp.bolla('pgTAP DTN nulla', NULL, (SELECT trasporto FROM _a)))::text,
  '[]',
  '7) senza modalita'' di addebito + onere di trasporto: nessun motivo');

SELECT is(
  pg_temp.motivi(pg_temp.bolla('pgTAP DTN altro', 'ASSEGNATO', (SELECT altro FROM _a)))::text,
  '[]',
  '8) porto assegnato + un onere che non e'' trasporto: nessun motivo');

SELECT * FROM finish();
ROLLBACK;
