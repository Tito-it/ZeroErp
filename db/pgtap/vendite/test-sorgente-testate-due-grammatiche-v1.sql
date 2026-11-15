-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: i lettori della sorgente di testata leggono le DUE grammatiche.
--   Oggi una bolla porta l'uid dell'ordine in sorgente_uid; dal lotto T porta
--   l'id in sorgente_id (S-5). I lettori del giro 0.3 cercano il documento con
--   la regola d'incontro del modello (doc.id = sorgente_id OR doc.uid =
--   sorgente_uid) e non si ritoccano quando la conversione arriva. Qui la
--   bolla si COSTRUISCE nella grammatica del lotto T (solo sorgente_id), e
--   ogni lettore deve trovare l'ordine come lo trovava con l'uid.
-- ChangeSet: 20261106-22 … -45
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto 0 giro 0.3
-- ------------------------------------------------------------
-- Indice test (plan 15):
--   1) fixture: la bolla porta l'ordine nel solo sorgente_id
--   2) vendite.fn_ddt_trigger_ordine_testata lo trova per id
--   3) ... e per uid, come prima (la grammatica di oggi)
--   4) vendite.fn_ddt_vincoli_cliente: vincolo SORGENTE con l'etichetta e il BA dell'ordine
--   5) il guard del cliente rifiuta il cambio di BA (E_DOC_CLIENTE_DIVERSO_DA_SORGENTE)
--   6) script.fn_check_ordine_annullabile: motivo E_ORD_ANNULLA_CON_DDT
--   7) lineage, seme l'ordine: l'arco H verso la bolla
--   8) lineage, seme la bolla: l'arco H dall'ordine
--   9) lineage, tutti gli archi: l'arco H c'e'
--  10) una bolla nuova col solo sorgente_id eredita il cliente dall'ordine (trgfn_ddt_normalize)
--  11) script.fn_get_sorgente_emittente_sr_id(tipo, id, NULL): l'emittente dell'ordine
--  12) ... (tipo, NULL, uid): lo stesso
--  13) la firma testuale si e' ritirata (giro C.2: i chiamanti passano le colonne del modello)
--  14) firma nuova: nessuna chiave E_SORG_KEY_MISSING, documento che non c'e' E_SORG_EMITTENTE_NON_RISOLTO
--  15) le firme vecchie dei due BB di bolla sono ritirate, le nuove ci sono
--
-- ⚠️ I resi non si provano qui nella grammatica del lotto T: resi.sorgente_uid e'
--   NOT NULL fino al lotto T, che lo toglie quando converte. I loro lettori sono
--   provati dall'equivalenza prima/dopo sulla popolazione (brief §7.2, «La prova
--   del giro 0.3») e il lotto T li ripassa con la conversione.
-- ⚠️ I casi si COSTRUISCONO: ordine dal builder, bolla dalla madre via
--   dbops.fn_pgtap_crea_ddt_da_ordine. Nessun dato esistente.
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP sorgente due grammatiche');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

CREATE TEMP TABLE _a AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-SDG-MERCE', false) AS merce;

-- L'ordine confermato (fattura alla conferma) e la sua bolla in bozza.
CREATE TEMP TABLE _o AS
SELECT o.ordine_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('pgTAP SDG', 'CONFERMATO',
         (SELECT billing_account_id FROM _m),
         p_fatturazione_trigger => 'CONFERMATO',
         p_righe => jsonb_build_array(jsonb_build_object(
             'articolo_id', (SELECT merce FROM _a), 'quantita', 2, 'prezzo', 5))) o;

CREATE TEMP TABLE _b AS
SELECT b.ddt_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP SDG', 'DRAFT', p_ordine_id => (SELECT ordine_id FROM _o)) b;

CREATE TEMP TABLE _k AS
SELECT o.id AS ordine_id, o.uid AS ordine_uid, o.billing_account_id AS ordine_ba,
       ef.soggetto_ruolo_id AS emittente_sr_id,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA') AS t_ord,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'DDT_VENDITA')    AS t_ddt
  FROM vendite.ordini o
  JOIN anagrafiche.emittenti_fiscali ef ON ef.id = o.emittente_fiscale_id
 WHERE o.id = (SELECT ordine_id FROM _o);

-- La bolla nella grammatica del lotto T: l'ordine per id, niente uid.
UPDATE vendite.ddt
   SET sorgente_id = (SELECT ordine_id FROM _k), sorgente_uid = NULL
 WHERE id = (SELECT ddt_id FROM _b);

SELECT ok(
  (SELECT d.sorgente_uid IS NULL AND d.sorgente_id = k.ordine_id AND d.sorgente_tipo_id = k.t_ord
     FROM vendite.ddt d, _k k WHERE d.id = (SELECT ddt_id FROM _b)),
  '1) fixture: la bolla porta l''ordine nel solo sorgente_id');

SELECT is(
  (SELECT vendite.fn_ddt_trigger_ordine_testata(d.sorgente_tipo_id, d.sorgente_uid, d.sorgente_id)::text
     FROM vendite.ddt d WHERE d.id = (SELECT ddt_id FROM _b)),
  'CONFERMATO',
  '2) vendite.fn_ddt_trigger_ordine_testata trova l''ordine per id');

SELECT is(
  (SELECT vendite.fn_ddt_trigger_ordine_testata(k.t_ord, k.ordine_uid)::text FROM _k k),
  'CONFERMATO',
  '3) ... e per uid, come prima (due argomenti: il DEFAULT della chiave nuova)');

SELECT is(
  (SELECT array_agg(v.vincolo || ':' || (v.billing_account_id = k.ordine_ba)::text || ':' || (v.etichetta IS NOT NULL)::text)
     FROM vendite.ddt d, _k k,
          vendite.fn_ddt_vincoli_cliente(d.id, d.sorgente_tipo_id, d.sorgente_uid, d.sorgente_id) v
    WHERE d.id = (SELECT ddt_id FROM _b) AND v.vincolo = 'SORGENTE'),
  ARRAY['SORGENTE:true:true'],
  '4) vendite.fn_ddt_vincoli_cliente: vincolo SORGENTE con il BA e l''etichetta dell''ordine');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('UPDATE vendite.ddt SET billing_account_id = NULL WHERE id = %s', (SELECT ddt_id FROM _b))),
  'E_DOC_CLIENTE_DIVERSO_DA_SORGENTE',
  '5) il guard del cliente rifiuta il cambio di BA: l''ordine lo trova per id');

SELECT ok(
  script.fn_check_ordine_annullabile((SELECT ordine_id FROM _k)) @> '[{"codice": "E_ORD_ANNULLA_CON_DDT"}]'::jsonb,
  '6) script.fn_check_ordine_annullabile vede la bolla viva dell''ordine (motivo E_ORD_ANNULLA_CON_DDT)');

SELECT ok(
  EXISTS (SELECT 1 FROM _k k, vendite.fn_documento_lineage_archi(ARRAY[k.t_ord], ARRAY[k.ordine_id::text]) x
           WHERE x.arco = 'H' AND x.from_uid = k.ordine_id::text AND x.to_uid = (SELECT ddt_id FROM _b)::text),
  '7) lineage seminata dall''ordine: l''arco H verso la bolla');

SELECT ok(
  EXISTS (SELECT 1 FROM _k k, vendite.fn_documento_lineage_archi(ARRAY[k.t_ddt], ARRAY[(SELECT ddt_id FROM _b)::text]) x
           WHERE x.arco = 'H' AND x.from_uid = k.ordine_id::text AND x.to_uid = (SELECT ddt_id FROM _b)::text),
  '8) lineage seminata dalla bolla: l''arco H dall''ordine');

SELECT ok(
  EXISTS (SELECT 1 FROM _k k, vendite.fn_documento_lineage_archi(NULL, NULL) x
           WHERE x.arco = 'H' AND x.from_uid = k.ordine_id::text AND x.to_uid = (SELECT ddt_id FROM _b)::text),
  '9) lineage, tutti gli archi: l''arco H c''e''');

-- Una bolla nuova nella grammatica del lotto T: il cliente lo eredita dall'ordine.
CREATE TEMP TABLE _n AS
WITH ins AS (
  INSERT INTO vendite.ddt (sorgente_tipo_id, sorgente_id, destinatario_soggetto_ruolo_id)
  SELECT k.t_ord, k.ordine_id, (SELECT cliente_soggetto_ruolo_id FROM _m) FROM _k k
  RETURNING id, billing_account_id)
SELECT * FROM ins;

SELECT is(
  (SELECT n.billing_account_id FROM _n n),
  (SELECT ordine_ba FROM _k),
  '10) una bolla nuova col solo sorgente_id eredita il cliente dall''ordine (vendite.trgfn_ddt_normalize)');

SELECT is(
  (SELECT script.fn_get_sorgente_emittente_sr_id(k.t_ord, k.ordine_id, NULL::uuid) FROM _k k),
  (SELECT emittente_sr_id FROM _k),
  '11) script.fn_get_sorgente_emittente_sr_id(tipo, id, NULL): l''emittente dell''ordine');

SELECT is(
  (SELECT script.fn_get_sorgente_emittente_sr_id(k.t_ord, NULL::bigint, k.ordine_uid) FROM _k k),
  (SELECT emittente_sr_id FROM _k),
  '12) ... (tipo, NULL, uid): lo stesso, il BB legge la chiave che riceve');

-- rev 2026-11-07 (brief-db-sorgente-documento-e-riga giro C.2): la porta
--   testuale si e' ritirata; la forma canonica del testo la controlla il BB
--   della porta del link (script/test-guard-sorgente-polimorfa-testuale-v1).
SELECT ok(
  to_regprocedure('script.fn_get_sorgente_emittente_sr_id(bigint,text)') IS NULL,
  '13) la firma testuale del risolutore si e'' ritirata: resta quella sulle colonne del modello');

SELECT is(
  (SELECT COALESCE(dbops.fn_pgtap_codice_errore(format('SELECT script.fn_get_sorgente_emittente_sr_id(%s, NULL::bigint, NULL::uuid)', t_ord)), 'PASSA') FROM _k)
  || ' / ' ||
  (SELECT COALESCE(dbops.fn_pgtap_codice_errore(format('SELECT script.fn_get_sorgente_emittente_sr_id(%s, 999999999999::bigint, NULL::uuid)', t_ord)), 'PASSA') FROM _k),
  'E_SORG_KEY_MISSING / E_SORG_EMITTENTE_NON_RISOLTO',
  '14) ... i codici: nessuna chiave E_SORG_KEY_MISSING, documento che non c''e'' E_SORG_EMITTENTE_NON_RISOLTO');

SELECT is(
  ARRAY[to_regprocedure('vendite.fn_ddt_trigger_ordine_testata(bigint,uuid)') IS NOT NULL,
        to_regprocedure('vendite.fn_ddt_vincoli_cliente(bigint,bigint,uuid)') IS NOT NULL,
        to_regprocedure('vendite.fn_ddt_trigger_ordine_testata(bigint,uuid,bigint)') IS NOT NULL,
        to_regprocedure('vendite.fn_ddt_vincoli_cliente(bigint,bigint,uuid,bigint)') IS NOT NULL,
        to_regprocedure('script.fn_get_sorgente_emittente_sr_id(bigint,bigint,uuid)') IS NOT NULL]::text[],
  ARRAY['false', 'false', 'true', 'true', 'true'],
  '15) firme vecchie dei BB di bolla ritirate; le firme con sorgente_id ci sono');

SELECT * FROM finish();
ROLLBACK;
