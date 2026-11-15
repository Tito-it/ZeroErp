-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: gli oneri della bolla all'emissione.
--   script.fn_check_ddt_emittibile (motivi E_DDT_ONERE_NON_FATTURABILE e
--   E_DDT_EMISSIONE_SOLO_ONERI), vendite.trgfn_ddt_guard_causale_emissione
--   (li solleva), script.fn_available_actions_ddt (spegne l'emissione col
--   motivo), vendite.fn_ddt_push_diagnosi (il trigger di testata per l'onere
--   senza legame).
-- ChangeSet: 20261103-39, -41, -42
-- Brief: brief-db-addebito-trasporto-ordine §8.3 (K-2, K-7, K-8, K-9).
-- ------------------------------------------------------------
-- Indice test (plan 13):
--  A — onere a mano su una bolla di un ordine che fattura alla conferma
--   1) la check ha il motivo E_DDT_ONERE_NON_FATTURABILE, col numero di riga
--   2) la capability spegne l'emissione con reason ONERE_NON_FATTURABILE e
--      la sua reason_key
--   3) l'emissione si rifiuta: E_DDT_ONERE_NON_FATTURABILE
--   4) ⭐ la diagnosi del push legge il trigger dalla testata: l'onere a mano
--      e' DDT_FATTURA_DA_ORDINE (prima: trigger NULL, risultava pushabile)
--  B — l'onere copiato dall'ordine alla conferma e' esente
--   5) nessun motivo sull'onere, e la bolla si emette
--  C — causale non fatturabile (K-8)
--   6) onere a mano su una bolla in conto visione: E_DDT_ONERE_NON_FATTURABILE
--   7) onere COPIATO da un ordine alla consegna su una bolla in conto visione:
--      stesso motivo (la copia non esenta qui: la bolla non va in commessa)
--  D — K-2, una bolla di soli oneri
--   8) il primo motivo e' E_DDT_EMISSIONE_SOLO_ONERI, e la capability lo dice
--   9) l'emissione si rifiuta: E_DDT_EMISSIONE_SOLO_ONERI
--  E — gli oneri ammessi (K-9)
--  10) onere a mano su una bolla VENDITA senza ordine: nessun motivo, si emette
--  11) onere a mano su una bolla di un ordine che fattura alla CONSEGNA:
--      nessun motivo (la bolla lo spinge in commessa)
--  12) la bolla di sola merce: nessun motivo nuovo (non regressione)
--  13) forma: i due codici sono fra quelli che il guard di emissione solleva
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO: cliente dal mondo, causale e articolo-onere
--   costruiti; bolle dai builder (dbops.fn_pgtap_crea_ddt_da_ordine,
--   dbops.fn_pgtap_crea_ddt_senza_ordine) in bozza, l'onere a mano scritto
--   dal test, lo stato da dbops.fn_pgtap_porta_a_stato (il verbo vero).
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP onere emissione');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;
-- L'azione di processo dell'emissione all'utente del contesto: senza, la
-- capability NASCONDE «Emetti» (permesso => nascondi, M-3) e il test 2 non
-- vedrebbe il motivo. La concede anche fn_pgtap_porta_a_stato, ma solo quando
-- porta lo stato: qui la capability si legge prima.
DO $az$ BEGIN PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'emetti_ddt'); END $az$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

CREATE TEMP TABLE _caus AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_DOE_1', 'PGT_DOE_1', 'Fixture pgTAP: onere emissione')
    RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE _a AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-DOE-ONERE', false,
         p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                                  WHERE nv.codice_interno = 'SERVIZIO_UNA_TANTUM'),
         p_causale_onere_id  => (SELECT id FROM _caus)) AS onere,
       dbops.fn_pgtap_crea_articolo('PGT-DOE-MERCE', false) AS merce;

-- L'onere scritto a mano sulla bolla in bozza (riga 9), prezzo e aliquota.
CREATE OR REPLACE FUNCTION pg_temp.onere_a_mano(p_ddt bigint) RETURNS bigint
LANGUAGE sql AS $$
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, prezzo_unitario, iva_id)
  VALUES (p_ddt, 9, (SELECT onere FROM _a), 'Fixture pgTAP: onere a mano', 1, 15,
          (SELECT i.id FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1))
  RETURNING id
$$;

CREATE OR REPLACE FUNCTION pg_temp.motivi(p_ddt bigint) RETURNS jsonb
LANGUAGE sql AS $$
  SELECT script.fn_check_ddt_emittibile(d) FROM vendite.ddt d WHERE d.id = p_ddt
$$;

CREATE OR REPLACE FUNCTION pg_temp.emetti(p_ddt bigint) RETURNS text
LANGUAGE sql AS $$
  SELECT dbops.fn_pgtap_codice_errore(format(
    'SELECT dbops.fn_pgtap_porta_a_stato(''vendite.ddt''::regclass, %s, ''EMESSO'')', p_ddt))
$$;

-- L'azione verso EMESSO della capability.
CREATE OR REPLACE FUNCTION pg_temp.azione_emetti(p_ddt bigint) RETURNS jsonb
LANGUAGE sql AS $$
  SELECT a FROM jsonb_array_elements(script.fn_available_actions_ddt(p_ddt) -> 'available_actions') a
   WHERE a ->> 'target_state' = 'EMESSO'
$$;

-- Un ordine con merce e onere.
CREATE OR REPLACE FUNCTION pg_temp.ordine(p_etichetta text, p_trigger text) RETURNS bigint
LANGUAGE sql AS $$
  SELECT o.ordine_id
    FROM dbops.fn_pgtap_crea_ordine_con_righe(p_etichetta, 'CONFERMATO',
           (SELECT billing_account_id FROM _m),
           p_fatturazione_trigger => p_trigger,
           p_righe => jsonb_build_array(
               jsonb_build_object('articolo_id', (SELECT merce FROM _a), 'quantita', 3, 'prezzo', 5),
               jsonb_build_object('articolo_id', (SELECT onere FROM _a), 'quantita', 1, 'prezzo', 15))) o
$$;

-- ============================================================
-- A — onere a mano su una bolla di un ordine alla conferma
-- ============================================================
CREATE TEMP TABLE _ba AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP DOE A', 'DRAFT',
         (SELECT billing_account_id FROM _m), p_fatturazione_trigger => 'CONFERMATO');
CREATE TEMP TABLE _ba_r AS SELECT pg_temp.onere_a_mano((SELECT ddt_id FROM _ba)) AS id;

SELECT ok(
  pg_temp.motivi((SELECT ddt_id FROM _ba))
    @> jsonb_build_array(jsonb_build_object(
         'codice', 'E_DDT_ONERE_NON_FATTURABILE',
         'dettaglio', jsonb_build_object('riga_id', (SELECT id FROM _ba_r), 'riga_nr', 9))),
  '1) onere a mano su bolla di ordine alla conferma: motivo E_DDT_ONERE_NON_FATTURABILE {riga_id, riga_nr}');

SELECT is(
  (SELECT (a ->> 'enabled') || '|' || (a ->> 'reason') || '|' || (a ->> 'reason_key')
     FROM pg_temp.azione_emetti((SELECT ddt_id FROM _ba)) a),
  'false|ONERE_NON_FATTURABILE|vendite.ddt.azione_reason.onere_non_fatturabile',
  '2) la capability spegne l''emissione col motivo (K-7)');

SELECT is(
  pg_temp.emetti((SELECT ddt_id FROM _ba)),
  'E_DDT_ONERE_NON_FATTURABILE',
  '3) l''emissione si rifiuta: E_DDT_ONERE_NON_FATTURABILE');

SELECT is(
  (SELECT g.motivo FROM vendite.fn_ddt_push_diagnosi((SELECT ddt_id FROM _ba)) g
    WHERE g.riga_id = (SELECT id FROM _ba_r)),
  'DDT_FATTURA_DA_ORDINE',
  '4) la diagnosi legge il trigger dalla testata: l''onere senza legame non si pusha dalla bolla');

-- ============================================================
-- B — l'onere copiato dall'ordine alla conferma e' esente
-- ============================================================
CREATE TEMP TABLE _bb AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP DOE B', 'DRAFT',
         p_ordine_id => pg_temp.ordine('pgTAP DOE B', 'CONFERMATO'));

SELECT is(
  (SELECT count(*) FROM jsonb_array_elements(pg_temp.motivi((SELECT ddt_id FROM _bb))) m
    WHERE m ->> 'codice' = 'E_DDT_ONERE_NON_FATTURABILE')::text
    || '|' || COALESCE(pg_temp.emetti((SELECT ddt_id FROM _bb)), 'emessa'),
  '0|emessa',
  '5) l''onere copiato dall''ordine alla conferma non e'' un motivo: la bolla si emette (lo fattura l''ordine)');

-- ============================================================
-- C — causale non fatturabile (K-8)
-- ============================================================
CREATE TEMP TABLE _bc AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('pgTAP DOE C', 'DRAFT',
         (SELECT billing_account_id FROM _m), p_causale_codice => 'CONTO_VISIONE');
SELECT pg_temp.onere_a_mano((SELECT ddt_id FROM _bc));

SELECT is(
  pg_temp.emetti((SELECT ddt_id FROM _bc)),
  'E_DDT_ONERE_NON_FATTURABILE',
  '6) onere a mano su una bolla in conto visione: E_DDT_ONERE_NON_FATTURABILE');

CREATE TEMP TABLE _bc2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP DOE C2', 'DRAFT',
         p_ordine_id => pg_temp.ordine('pgTAP DOE C2', 'CONSEGNATO'),
         p_causale_codice => 'CONTO_VISIONE');

SELECT ok(
  pg_temp.motivi((SELECT ddt_id FROM _bc2))
    @> '[{"codice": "E_DDT_ONERE_NON_FATTURABILE"}]'::jsonb,
  '7) onere COPIATO su una bolla in conto visione: stesso motivo (K-8, la copia non esenta)');

-- ============================================================
-- D — K-2, una bolla di soli oneri
-- ============================================================
CREATE TEMP TABLE _bd AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('pgTAP DOE D', 'DRAFT',
         (SELECT billing_account_id FROM _m));
UPDATE vendite.ddt_righe SET attivo = false WHERE ddt_id = (SELECT ddt_id FROM _bd);
SELECT pg_temp.onere_a_mano((SELECT ddt_id FROM _bd));

SELECT is(
  (pg_temp.motivi((SELECT ddt_id FROM _bd)) -> 0 ->> 'codice')
    || '|' || (SELECT a ->> 'reason' FROM pg_temp.azione_emetti((SELECT ddt_id FROM _bd)) a),
  'E_DDT_EMISSIONE_SOLO_ONERI|DOCUMENTO_SOLO_ONERI',
  '8) bolla di soli oneri: primo motivo E_DDT_EMISSIONE_SOLO_ONERI, e la capability lo dice (K-2)');

SELECT is(
  pg_temp.emetti((SELECT ddt_id FROM _bd)),
  'E_DDT_EMISSIONE_SOLO_ONERI',
  '9) l''emissione di una bolla di soli oneri si rifiuta');

-- ============================================================
-- E — gli oneri ammessi (K-9) e la non regressione
-- ============================================================
CREATE TEMP TABLE _be AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('pgTAP DOE E', 'DRAFT',
         (SELECT billing_account_id FROM _m));
SELECT pg_temp.onere_a_mano((SELECT ddt_id FROM _be));

SELECT is(
  pg_temp.motivi((SELECT ddt_id FROM _be))::text || '|' || COALESCE(pg_temp.emetti((SELECT ddt_id FROM _be)), 'emessa'),
  '[]|emessa',
  '10) onere a mano su una bolla VENDITA senza ordine: nessun motivo, si emette (K-9)');

CREATE TEMP TABLE _bf AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP DOE F', 'DRAFT',
         (SELECT billing_account_id FROM _m), p_fatturazione_trigger => 'CONSEGNATO');
SELECT pg_temp.onere_a_mano((SELECT ddt_id FROM _bf));

SELECT is(
  pg_temp.motivi((SELECT ddt_id FROM _bf))::text,
  '[]',
  '11) onere a mano su una bolla di un ordine alla consegna: ammesso (la bolla lo spinge)');

CREATE TEMP TABLE _bg AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP DOE G', 'DRAFT',
         (SELECT billing_account_id FROM _m), p_fatturazione_trigger => 'CONFERMATO');

SELECT is(
  pg_temp.motivi((SELECT ddt_id FROM _bg))::text,
  '[]',
  '12) la bolla di sola merce dall''ordine alla conferma: nessun motivo (non regressione)');

SELECT ok(
  pg_get_functiondef('vendite.trgfn_ddt_guard_causale_emissione()'::regprocedure) ~ '''E_DDT_ONERE_NON_FATTURABILE'''
  AND pg_get_functiondef('vendite.trgfn_ddt_guard_causale_emissione()'::regprocedure) ~ '''E_DDT_EMISSIONE_SOLO_ONERI''',
  '13) forma: il guard di emissione ha un ramo per i due codici (il suo LOOP non ha un ELSE)');

SELECT * FROM finish();
ROLLBACK;
