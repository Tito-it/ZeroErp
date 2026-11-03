-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_ddt_trigger_ordine_testata, il trigger di fatturazione
--   dell'ordine sorgente di TESTATA di una bolla, e il ritiro delle due copie
--   in linea (regola del 2).
-- ChangeSet: 20261103-43 (il BB), -44 (diagnosi del push), -45 (check di
--   emissione)
-- Brief: brief-db-addebito-trasporto-ordine §9.5, P-1
-- ------------------------------------------------------------
-- Indice test (plan 6):
--   1) il BB esiste, con la firma ancorata alle colonne della bolla
--   2) bolla da un ordine che fattura alla conferma: CONFERMATO
--   3) bolla da un ordine che fattura alla consegna: CONSEGNATO
--   4) bolla senza ordine: NULL
--   5) argomenti NULL: NULL
--   6) ⛔ le due copie sono ritirate: diagnosi e check chiamano il BB e non
--      leggono piu' l'ordine di testata in linea
--
-- ⚠️ I casi si COSTRUISCONO: ordini dal builder con le righe, bolle dalla
--   madre via dbops.fn_pgtap_crea_ddt_da_ordine, la bolla senza ordine dal
--   suo builder. Nessun dato esistente.
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP trigger ordine testata');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

CREATE TEMP TABLE _a AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-TOT-MERCE', false) AS merce;

-- Una bolla in bozza da un ordine confermato col trigger dato.
CREATE OR REPLACE FUNCTION pg_temp.bolla(p_etichetta text, p_trigger text) RETURNS bigint
LANGUAGE sql AS $$
  SELECT b.ddt_id
    FROM dbops.fn_pgtap_crea_ddt_da_ordine(p_etichetta, 'DRAFT',
           p_ordine_id => (SELECT o.ordine_id
                             FROM dbops.fn_pgtap_crea_ordine_con_righe(p_etichetta, 'CONFERMATO',
                                    (SELECT billing_account_id FROM _m),
                                    p_fatturazione_trigger => p_trigger,
                                    p_righe => jsonb_build_array(jsonb_build_object(
                                        'articolo_id', (SELECT merce FROM _a),
                                        'quantita', 2, 'prezzo', 5))) o)) b
$$;

CREATE OR REPLACE FUNCTION pg_temp.trg(p_ddt bigint) RETURNS text
LANGUAGE sql AS $$
  SELECT vendite.fn_ddt_trigger_ordine_testata(d.sorgente_tipo_id, d.sorgente_uid)::text
    FROM vendite.ddt d WHERE d.id = p_ddt
$$;

SELECT has_function('vendite', 'fn_ddt_trigger_ordine_testata', ARRAY['bigint', 'uuid'],
  '1) vendite.fn_ddt_trigger_ordine_testata(sorgente_tipo_id, sorgente_uid) esiste');

SELECT is(pg_temp.trg(pg_temp.bolla('pgTAP TOT conferma', 'CONFERMATO')), 'CONFERMATO',
  '2) bolla da un ordine che fattura alla conferma: CONFERMATO');

SELECT is(pg_temp.trg(pg_temp.bolla('pgTAP TOT consegna', 'CONSEGNATO')), 'CONSEGNATO',
  '3) bolla da un ordine che fattura alla consegna: CONSEGNATO');

SELECT is(
  pg_temp.trg((SELECT b.ddt_id FROM dbops.fn_pgtap_crea_ddt_senza_ordine('pgTAP TOT senza ordine', 'DRAFT',
                 p_billing_account_id => (SELECT billing_account_id FROM _m)) b)),
  NULL,
  '4) bolla senza ordine: NULL');

SELECT is(vendite.fn_ddt_trigger_ordine_testata(NULL, NULL)::text, NULL,
  '5) argomenti NULL: NULL');

-- ⛔ Il testo delle due funzioni: pg_get_functiondef copre anche la diagnosi
--   BEGIN ATOMIC (prosrc e' vuoto, linee-guida-sql §5c).
SELECT ok(
  (SELECT bool_and(def ~ 'fn_ddt_trigger_ordine_testata'
                   AND def !~ 'testata_fatturazione_trigger'
                   AND def !~* 'select\s+o\.fatturazione_trigger\s+into\s+v_trigger_testata')
     FROM (SELECT pg_get_functiondef(p.oid) AS def
             FROM pg_proc p
            WHERE p.oid IN ('vendite.fn_ddt_push_diagnosi'::regproc,
                            'script.fn_check_ddt_emittibile'::regproc)) x),
  '6) diagnosi e check di emissione leggono il trigger di testata dal BB, nessuna copia in linea');

SELECT * FROM finish();
ROLLBACK;
