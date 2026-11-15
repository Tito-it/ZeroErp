-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la PROVENIENZA delle righe di vendita, scritta dai verbi che le
--   generano e validata dal guard unico. Il modello: il tipo del documento +
--   una sola chiave (sorgente_id o sorgente_uid, secondo il key_selector) +
--   sorgente_riga = la riga d'origine. Ogni verbo si chiama davvero, sulla
--   strada dell'applicazione, e si legge la riga che ne esce.
-- ChangeSet: 20261106-46 … -58 (giro R.1), -60 e i due CSV (giro R.2)
--   rev 2026-11-08 (giro finale bis, G-4, 20261110-32): la riga di fattura non ha
--   provenienza; il test 1 guarda la sola riga d'ordine, il 2 resta (l'indice non c'e').
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto R
-- ------------------------------------------------------------
-- Indice test (plan 24):
--   LA FORMA
--    1) il DEFAULT 0 di sorgente_riga non c'e' piu' (ordini_righe; fatture_righe non ha
--       piu' la colonna dal giro finale bis, G-4)
--    2) gli indici unici «import» (tipo, uid) non ci sono piu'
--    3) le quattro tabelle hanno il CHECK di forma
--    4) le quattro tabelle montano il guard unico, coi loro argomenti
--   I VERBI
--    5) revisione: ogni riga della rev N+1 cita la rev N e la riga copiata
--    6) ... anche su un articolo ritirato dopo la rev N (la riga e' derivata)
--    7) push preventivo -> ordine: PREVENTIVO + la riga, accanto a preventivo_riga_id
--    8) ordine dall'offerta: la riga dall'eccezione cita l'eccezione
--    9) ... la riga del solo listino cita l'offerta intera (sorgente_riga NULL)
--   10) contratto dall'offerta: ogni riga cita l'eccezione copiata
--   11) bolla dall'ordine: ORDINE_VENDITA + la riga d'ordine
--   12) riconsegna: RESO_VENDITA + la riga del reso (D-4), non l'ordine
--   IL GUARD UNICO E LA FORMA
--   13) una riga a mano che cita la riga di un documento: passa
--   14) la riga di un ALTRO documento: E_SORG_RIGA_NON_DEL_DOCUMENTO
--   15) due chiavi: E_SORG_CHIAVE_NON_CONFORME
--   16) la chiave sbagliata per il tipo (id per un tipo a uid): E_SORG_CHIAVE_NON_CONFORME
--   17) un documento che non c'e': E_SORG_NOT_FOUND
--   18) sorgente_riga senza tipo: il CHECK di forma (23514)
--   19) livello minimo RIGA sulle righe di preventivo: E_SORG_LIVELLO_MANCANTE
--   IN USCITA
--   20) la riga d'origine citata non si cancella: E_SORG_ORIGINE_REFERENZIATA
--   21) ... e il documento d'origine nemmeno
--   22) tolta la citazione, la riga d'origine si cancella
--   I TIPI *_RIGA DI VENDITA (giro R.2)
--   23) non sono piu' sorgenti: nessuna riga in config.sorgenti
--   24) ... ma restano entita' (bersagli, note), con is_sorgente false
--
-- ⚠️ Il mondo si COSTRUISCE: cliente, listino, articoli, preventivi, offerte,
--   ordine, bolla, reso dai builder dbops.fn_pgtap_*. Gira come
--   l'applicazione (operatore in sessione, RLS attiva).
-- ⚠️ Il caso 6 e' quello che il lotto R chiude (brief-db-articoli-obsoleto-dal,
--   O-8): prima, la riga derivata da un articolo ritirato era trattata come
--   scelta nuova e respinta.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(24);

-- ============================================================
-- LA FORMA
-- ============================================================
SELECT is(
  (SELECT string_agg(c.table_name || '=' || coalesce(c.column_default, 'NULL'), ', ' ORDER BY c.table_name)
     FROM information_schema.columns c
    WHERE c.table_schema = 'vendite' AND c.column_name = 'sorgente_riga'
      AND c.table_name = 'ordini_righe'),
  'ordini_righe=NULL',
  '1) sorgente_riga senza DEFAULT 0: lo 0 era una riga che non esiste');

SELECT ok(
  to_regclass('vendite.uq_ordini_righe_v_sorgente_fk') IS NULL
  AND to_regclass('vendite.uq_fatture_righe_v_sorgente_fk') IS NULL,
  '2) niente unicita'' «import» per (tipo, uid): due righe dello stesso documento sono la regola');

SELECT is(
  (SELECT count(*)::int FROM pg_constraint k
    WHERE k.contype = 'c'
      AND k.conname IN ('chk_preventivi_righe_sorgente_forma', 'chk_ordini_righe_sorgente_forma',
                        'chk_ddt_righe_sorgente_forma', 'chk_contratti_righe_sorgente_forma')),
  4,
  '3) le quattro righe di vendita hanno il CHECK di forma della provenienza');

-- rev 2026-11-08 (giro Z.2): schema e nome dalle colonne del lettore, non da
-- regclass::text, che omette lo schema quando sta nel search_path di chi lancia
-- (la trappola del test 1 del giro T.4).
SELECT results_eq(
  $$SELECT format('%I.%I', schema_tabella, nome_tabella) COLLATE "default", livello_minimo, azione_cancellazione
      FROM script.fn_sorgente_guard_montaggi()
     WHERE tabella IN ('vendite.preventivi_righe'::regclass, 'vendite.ordini_righe'::regclass,
                       'vendite.ddt_righe'::regclass, 'vendite.contratti_righe'::regclass)
     ORDER BY 1$$,
  $$VALUES ('vendite.contratti_righe', 'RIGA', 'BLOCCA'),
           ('vendite.ddt_righe', 'RIGA', 'BLOCCA'),
           ('vendite.ordini_righe', 'DOCUMENTO', 'BLOCCA'),
           ('vendite.preventivi_righe', 'RIGA', 'BLOCCA')$$,
  '4) il guard unico e'' montato sulle quattro righe: livello minimo e azione in cancellazione');

-- ============================================================
-- Fixture: il mondo
-- ============================================================
CREATE TEMP TABLE _cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'sorgente righe',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE _lis AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _cli), 'sorgente righe');

CREATE TEMP TABLE _ref AS
SELECT c.billing_account_id, c.istanza_utility_id, c.utility_id, c.soggetto_ruolo_id,
       script.fn_pgtap_emittente_operatore()                                        AS emittente_fiscale_id,
       dbops.fn_pgtap_crea_articolo('PGT-SRV-PREV', false)                          AS art_prev,
       dbops.fn_pgtap_crea_articolo('PGT-SRV-REV', false)                           AS art_rev,
       dbops.fn_pgtap_crea_articolo('PGT-SRV-OFF', false)                           AS art_off,
       (SELECT l.listino_id FROM _lis l)                                            AS listino_id,
       (SELECT l.listino_versione_id FROM _lis l)                                   AS listino_versione_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                     AS valuta_id,
       (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
       (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT') AS prev_draft_id,
       (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA')    AS off_bozza_id,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')          AS t_prev,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'OFFERTA_COMMERCIALE') AS t_off,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA')      AS t_ord,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'RESO_VENDITA')        AS t_reso
  FROM _cli c;

SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
    (SELECT listino_versione_id FROM _ref), ARRAY[(SELECT art_off FROM _ref)]);

CREATE TEMP TABLE _fix (chiave text PRIMARY KEY, id bigint);
CREATE FUNCTION pg_temp.fix(p text) RETURNS bigint LANGUAGE sql AS $$ SELECT id FROM _fix WHERE chiave = p $$;

-- Un preventivo con una riga, nato DRAFT e portato allo stato chiesto.
CREATE FUNCTION pg_temp.mk_preventivo(p_chiave text, p_stato text, p_articolo uuid)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE r RECORD; v_prev bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM _ref;
  INSERT INTO vendite.preventivi (rev, billing_account_id, istanza_utility_id, utility_id,
      validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
      fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  VALUES (0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
          script.fn_data_operativa(), script.fn_data_operativa() + 30, r.valuta_id, r.prev_draft_id,
          script.fn_data_operativa(), false, false,
          jsonb_build_object('test_scope', 'pgtap_sorgente_righe'), r.emittente_fiscale_id)
  RETURNING id INTO v_prev;
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario,
      iva_id, attivo, meta)
  VALUES (v_prev, p_articolo, 4, 25, r.iva_id, true, jsonb_build_object('test_scope', 'pgtap_sorgente_righe'))
  RETURNING id INTO v_riga;
  IF p_stato <> 'DRAFT' THEN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_prev, p_stato);
  END IF;
  INSERT INTO _fix VALUES (p_chiave, v_prev), (p_chiave || '_riga', v_riga);
END $$;

-- Un'offerta ACCETTATA sul listino, con un OVERRIDE sull'articolo a listino.
CREATE FUNCTION pg_temp.mk_offerta(p_chiave text)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE r RECORD; v_off bigint; v_ecc bigint;
BEGIN
  SELECT * INTO r FROM _ref;
  INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,
      istanza_utility_id, utility_id, listino_id, listino_versione_id,
      validita_dal, validita_al, stato_doc_offerta_id)
  VALUES (r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
          r.listino_id, r.listino_versione_id, script.fn_data_operativa(),
          script.fn_data_operativa() + 364, r.off_bozza_id)
  RETURNING id INTO v_off;
  INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
      tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, attivo, qta_operativa)
  VALUES (v_off, r.art_off, 'OVERRIDE'::vendite.tipo_eccezione_contratto, NULL, NULL, 200, true,
          (SELECT 1.00 FROM vendite.fn_articolo_erogazioni(r.art_off) e
            WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1))
  RETURNING id INTO v_ecc;
  INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
  VALUES (v_off, r.istanza_utility_id, r.utility_id);
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', v_off, 'ACCETTATA');
  INSERT INTO _fix VALUES (p_chiave, v_off), (p_chiave || '_ecc', v_ecc);
END $$;

-- ============================================================
-- I VERBI
-- ============================================================
-- La revisione: dalla rev N EMESSA. L'articolo si ritira DOPO la rev N.
SELECT pg_temp.mk_preventivo('rev_n', 'EMESSO', (SELECT art_rev FROM _ref));
UPDATE catalogo.articoli SET obsoleto_dal = script.fn_data_operativa() - 1
 WHERE id = (SELECT art_rev FROM _ref);

CREATE TEMP TABLE _rev AS
SELECT COALESCE(dbops.fn_pgtap_codice_errore(format('SELECT vendite.fn_crea_revisione_preventivo(%s, %L)',
                            pg_temp.fix('rev_n'), 'pgtap')), 'PASSA') AS esito;
INSERT INTO _fix
SELECT 'rev_n1', p.id FROM vendite.preventivi p
 WHERE p.numero = (SELECT numero FROM vendite.preventivi WHERE id = pg_temp.fix('rev_n'))
   AND p.id <> pg_temp.fix('rev_n');

SELECT is(
  (SELECT string_agg(format('%s|%s|%s|%s', r.sorgente_tipo_id = k.t_prev, r.sorgente_id IS NULL,
                            r.sorgente_uid = p.uid, r.sorgente_riga = pg_temp.fix('rev_n_riga')), ',')
     FROM vendite.preventivi_righe r, _ref k, vendite.preventivi p
    WHERE r.preventivo_id = pg_temp.fix('rev_n1') AND p.id = pg_temp.fix('rev_n')),
  't|t|t|t',
  '5) revisione: la riga della rev N+1 cita PREVENTIVO, l''uid della rev N e la riga copiata');

SELECT is(
  (SELECT esito FROM _rev),
  'PASSA',
  '6) ... e passa anche su un articolo ritirato dopo la rev N: la riga e'' derivata, non una scelta');

-- Il push preventivo -> ordine.
SELECT pg_temp.mk_preventivo('acc', 'ACCETTATO', (SELECT art_prev FROM _ref));
INSERT INTO _fix SELECT 'ord_prev', vendite.fn_push_preventivo_a_ordine(pg_temp.fix('acc'));

SELECT is(
  (SELECT string_agg(format('%s|%s|%s|%s', r.sorgente_tipo_id = k.t_prev, r.sorgente_uid = p.uid,
                            r.sorgente_riga, r.preventivo_riga_id), ',')
     FROM vendite.ordini_righe r, _ref k, vendite.preventivi p
    WHERE r.ordine_id = pg_temp.fix('ord_prev') AND p.id = pg_temp.fix('acc')),
  format('t|t|%s|%s', pg_temp.fix('acc_riga'), pg_temp.fix('acc_riga')),
  '7) push preventivo -> ordine: PREVENTIVO + uid + la riga, accanto a preventivo_riga_id (il consumo)');

-- L'ordine dall'offerta: la riga dell'OVERRIDE e quella d'appoggio del listino.
SELECT pg_temp.mk_offerta('off_ord');
INSERT INTO _fix SELECT 'ord_off', vendite.fn_genera_ordine_da_offerta(pg_temp.fix('off_ord'));

SELECT is(
  (SELECT format('%s|%s|%s', r.sorgente_tipo_id = k.t_off, r.sorgente_uid = o.uid, r.sorgente_riga)
     FROM vendite.ordini_righe r, _ref k, vendite.offerte_commerciali o
    WHERE r.ordine_id = pg_temp.fix('ord_off') AND o.id = pg_temp.fix('off_ord')
      AND r.articolo_id = k.art_off),
  format('t|t|%s', pg_temp.fix('off_ord_ecc')),
  '8) ordine dall''offerta: la riga dall''eccezione cita OFFERTA_COMMERCIALE, l''offerta e l''eccezione');

SELECT is(
  (SELECT string_agg(format('%s|%s|%s', r.sorgente_tipo_id = k.t_off, r.sorgente_uid = o.uid,
                            coalesce(r.sorgente_riga::text, 'NULL')), ',')
     FROM vendite.ordini_righe r, _ref k, vendite.offerte_commerciali o
    WHERE r.ordine_id = pg_temp.fix('ord_off') AND o.id = pg_temp.fix('off_ord')
      AND r.articolo_id <> k.art_off),
  't|t|NULL',
  '9) ... la riga del solo listino cita l''offerta intera: sorgente_riga NULL (D-5)');

-- Il contratto dall'offerta.
SELECT pg_temp.mk_offerta('off_ctr');
INSERT INTO _fix SELECT 'ctr', vendite.fn_push_offerta_a_contratto(pg_temp.fix('off_ctr'), NULL::bigint);

SELECT is(
  (SELECT string_agg(format('%s|%s|%s', r.sorgente_tipo_id = k.t_off, r.sorgente_uid = o.uid, r.sorgente_riga), ',')
     FROM vendite.contratti_righe r, _ref k, vendite.offerte_commerciali o
    WHERE r.contratto_id = pg_temp.fix('ctr') AND o.id = pg_temp.fix('off_ctr')),
  format('t|t|%s', pg_temp.fix('off_ctr_ecc')),
  '10) contratto dall''offerta: la riga cita OFFERTA_COMMERCIALE, l''offerta e l''eccezione copiata');

-- La bolla dall'ordine (il builder passa dal verbo), il reso per riconsegna,
-- la riconsegna (anche lei dal verbo).
CREATE TEMP TABLE _ddt AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('sorgente righe',
         p_billing_account_id => (SELECT billing_account_id FROM _ref),
         p_quantita => 10, p_prezzo => 20, p_articolo_id => (SELECT art_prev FROM _ref));

SELECT is(
  (SELECT format('%s|%s|%s|%s', r.sorgente_tipo_id = k.t_ord, r.sorgente_id = d.ordine_id,
                 r.sorgente_uid IS NULL, r.sorgente_riga = d.ordine_riga_id)
     FROM vendite.ddt_righe r, _ref k, _ddt d WHERE r.id = d.ddt_riga_id),
  't|t|t|t',
  '11) bolla dall''ordine: ORDINE_VENDITA + id dell''ordine + la riga d''ordine');

CREATE TEMP TABLE _reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('sorgente righe', (SELECT ddt_id FROM _ddt), 3, 'RESO_PER_RICONSEGNA');
CREATE TEMP TABLE _ric AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM _reso),
         p_resi_riga_id => (SELECT resi_riga_id FROM _reso), p_quantita => 3);

SELECT is(
  (SELECT format('%s|%s|%s|%s', r.sorgente_tipo_id = k.t_reso, r.sorgente_id = s.reso_id,
                 r.sorgente_uid IS NULL, r.sorgente_riga = s.resi_riga_id)
     FROM vendite.ddt_righe r, _ref k, _reso s, _ric c WHERE r.id = c.ddt_riga_id),
  't|t|t|t',
  '12) riconsegna: RESO_VENDITA + id del reso + la riga del reso (la provenienza e'' il reso, D-4)');

-- ============================================================
-- IL GUARD UNICO E LA FORMA, su una riga d'ordine in bozza scritta a mano
-- ============================================================
-- Il documento citato: un preventivo in bozza, la sua riga si puo' cancellare.
SELECT pg_temp.mk_preventivo('bozza', 'DRAFT', (SELECT art_prev FROM _ref));

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, qta_operativa,
                                         prezzo_unitario, iva_id, sorgente_tipo_id, sorgente_uid, sorgente_riga)
       SELECT %s, 99, k.art_prev, 'pgTAP sorgente righe', 1, 10, k.iva_id, k.t_prev, p.uid, %s
         FROM _ref k, vendite.preventivi p WHERE p.id = %s$q$,
    pg_temp.fix('ord_prev'), pg_temp.fix('bozza_riga'), pg_temp.fix('bozza'))),
  NULL,
  '13) una riga scritta a mano che cita il documento e una sua riga: il guard la ammette');

INSERT INTO _fix SELECT 'mano', r.id FROM vendite.ordini_righe r
 WHERE r.ordine_id = pg_temp.fix('ord_prev') AND r.riga_nr = 99;

SELECT is(
  dbops.fn_pgtap_codice_errore(format('UPDATE vendite.ordini_righe SET sorgente_riga = %s WHERE id = %s',
                       pg_temp.fix('acc_riga'), pg_temp.fix('mano'))),
  'E_SORG_RIGA_NON_DEL_DOCUMENTO',
  '14) la riga di un ALTRO documento: E_SORG_RIGA_NON_DEL_DOCUMENTO');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('UPDATE vendite.ordini_righe SET sorgente_id = %s WHERE id = %s',
                       pg_temp.fix('bozza'), pg_temp.fix('mano'))),
  'E_SORG_CHIAVE_NON_CONFORME',
  '15) due chiavi insieme: E_SORG_CHIAVE_NON_CONFORME');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('UPDATE vendite.ordini_righe SET sorgente_uid = NULL, sorgente_id = %s WHERE id = %s',
                       pg_temp.fix('bozza'), pg_temp.fix('mano'))),
  'E_SORG_CHIAVE_NON_CONFORME',
  '16) l''id per un tipo a chiave uid: E_SORG_CHIAVE_NON_CONFORME (la chiave la dice il key_selector)');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('UPDATE vendite.ordini_righe SET sorgente_uid = %L, sorgente_riga = NULL WHERE id = %s',
                       '00000000-0000-7000-8000-000000000000', pg_temp.fix('mano'))),
  'E_SORG_NOT_FOUND',
  '17) un documento che non c''e'': E_SORG_NOT_FOUND');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('UPDATE vendite.ordini_righe SET sorgente_tipo_id = NULL, sorgente_uid = NULL WHERE id = %s',
                       pg_temp.fix('mano'))),
  'chk_ordini_righe_sorgente_forma',
  '18) sorgente_riga senza tipo: il guard tace (nessun tipo), il CHECK di forma rifiuta');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario,
                                             iva_id, sorgente_tipo_id, sorgente_uid)
       SELECT %s, k.art_prev, 1, 10, k.iva_id, k.t_prev, p.uid
         FROM _ref k, vendite.preventivi p WHERE p.id = %s$q$,
    pg_temp.fix('bozza'), pg_temp.fix('acc'))),
  'E_SORG_LIVELLO_MANCANTE',
  '19) righe di preventivo, livello minimo RIGA: il documento intero senza la riga e'' E_SORG_LIVELLO_MANCANTE');

-- ============================================================
-- IN USCITA
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.preventivi_righe WHERE id = %s', pg_temp.fix('bozza_riga'))),
  'E_SORG_ORIGINE_REFERENZIATA',
  '20) la riga d''origine citata da una riga d''ordine non si cancella (BLOCCA)');

-- rev 2026-11-08 (giro Z.2 di brief-db-sorgente-documento-e-riga): il
-- preventivo si cancella solo da bozza vuota, e il guard della testata parla
-- prima del lato «in uscita». Le righe si disattivano (in bozza si puo'), la
-- bozza e' vuota, e il rifiuto che il test prova resta quello del figlio.
UPDATE vendite.preventivi_righe SET attivo = false WHERE preventivo_id = pg_temp.fix('bozza');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.preventivi WHERE id = %s', pg_temp.fix('bozza'))),
  'E_SORG_ORIGINE_REFERENZIATA',
  '21) ... e il preventivo d''origine nemmeno');

DELETE FROM vendite.ordini_righe WHERE id = pg_temp.fix('mano');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.preventivi_righe WHERE id = %s', pg_temp.fix('bozza_riga'))),
  NULL,
  '22) tolta la riga che la cita, la riga d''origine si cancella');

-- ============================================================
-- I TIPI *_RIGA DI VENDITA (giro R.2): una riga si scrive col tipo del suo
-- documento e sorgente_riga (S-2), il tipo «la riga come documento» non c'e' piu'.
-- ============================================================
SELECT is_empty(
  $$SELECT s.codice_interno FROM config.sorgenti s
     WHERE s.codice_interno IN (SELECT c FROM (VALUES ('PREVENTIVO_RIGA'), ('CONTRATTO_RIGA'), ('ORDINE_VENDITA_RIGA'), ('DDT_VENDITA_RIGA'), ('FATTURA_RIGA'), ('RESO_VENDITA_RIGA')) v(c))$$,
  '23) i sei tipi *_RIGA di vendita non sono piu'' sorgenti');

SELECT is(
  (SELECT count(*)::int FROM config.tipi_entita e
    WHERE e.codice IN (SELECT c FROM (VALUES ('PREVENTIVO_RIGA'), ('CONTRATTO_RIGA'), ('ORDINE_VENDITA_RIGA'), ('DDT_VENDITA_RIGA'), ('FATTURA_RIGA'), ('RESO_VENDITA_RIGA')) v(c))
      AND e.is_sorgente IS FALSE AND e.sorgente_codice_interno IS NULL),
  6,
  '24) ... e restano entita'' (bersagli, note, giornale), con is_sorgente false');

SELECT * FROM finish();
ROLLBACK;
