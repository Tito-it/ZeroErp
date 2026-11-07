-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): gli ordini senza bolla da dbops.fn_pgtap_crea_ordine_con_righe (l'ordine a due righe del caso 1 con p_righe, la bozza DRAFT, B CONFERMATO), la commessa da dbops.fn_pgtap_crea_commessa (sorgente ROOT), le attivita' da dbops.fn_pgtap_crea_commessa_attivita con la sorgente ORDINE_VENDITA (E-3); helper sm_mk_ordine e sm_mk_af ritirati. Resta a mano il legame della riga MULTIPLA (il caso del 9).
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso dal builder dbops.fn_pgtap_crea_reso, la ri-spedizione parziale da dbops.fn_pgtap_crea_ddt_riconsegna (alla sua data); helper sm_mk_reso e sm_rispedisci ritirati, l'azione conferma_reso la concede il builder.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, D-1): gli ordini costruiti dal builder nascono al 2026-08-05 (p_data_ordine), come gli ordini scritti a mano prima del giro 1: nessuna bolla piu' vecchia del suo ordine.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): le bolle da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (date con p_data; le tre spedizioni del caso 1 con p_ordine_id + p_righe, l'ordine ha due righe); restano scritti a mano l'ordine del caso 1 (riga 2 mai spedita), gli ordini senza bolla (bozza, B), il legame della riga MULTIPLA (in bozza, il caso del 9), la bolla di ri-consegna (indirizzo e causale; gli stati per dbops.fn_pgtap_porta_a_stato) e il reso (giro 2).
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_situazione_merce_ordine — la situazione merce per riga
--       d'ordine PER DOCUMENTO (D14 giro 2 — D3;
--       brief-db-partita-merce-per-documento §2.2, §7; changeSet 20260921-26, -27).
--
-- Indice test (plan 13):
--   1) la funzione esiste, e' BEGIN ATOMIC, NON e' SECURITY DEFINER e dipende
--      da fn_partite_merce nel catalogo (la catena RLS passa di li')
--   2) ⭐ pin di D1: la vista e' la PROIEZIONE della funzione — nomina
--      fn_situazione_merce_ordine e nessuna tabella, nessuna partita
--   3) ⭐ pin dei tipi: 21 colonne, `ordinato` numeric(18,6) (un SELECT * dalla
--      funzione lo perderebbe), security_invoker=on
--   4) ⭐ ordine su tre DDT (10+10+10), fatturato dall'ORDINE per 15: chiesto
--      per ORDINE, una riga con consegnato 30, fatturato_da_ordine 15,
--      differenza 15, DA_FATTURARE, 3 partite, da_spedire 0
--   5) ⭐ LA SEMANTICA DEL SEME PER DDT: chiesto dal DDT DI MEZZO, la stessa
--      riga con la situazione INTERA (consegnato 30, 3 partite) — non la sola
--      partita di quel DDT (10, 1). E' «le righe d'ordine che quella spedizione
--      ha toccato», come il pannello legge dal 2026-08-19
--   6) ...e nei due semi le righe sono IDENTICHE alla vista filtrata come la
--      filtra il backend (EXCEPT ALL nei due versi)
--   7) la riga MAI SPEDITA dello stesso ordine: NON_SPEDITA con da_spedire 4
--      per seme ORDINE; per seme DDT non esce (nessuna spedizione l'ha toccata)
--   8) un ordine in BOZZA: NON_IMPEGNATA e da_spedire NULL, non zero
--   9) ⭐ riga MULTIPLA (un DDT dell'ordine A3 evade anche un ordine B, legato
--      in bozza dal 2026-10-11, D-6): per seme DDT
--      escono ENTRAMBE le righe d'ordine; quella di A e' NON_MISURABILE e quella
--      di B ha 0 partite (la partita conta sotto la riga MINIMA) — come la vista
--  10) ri-consegna: reso per ri-consegna 5 e ri-spedizione 3 — consegnato 13,
--      reso 5, tenuti 8, da_spedire 2 (5 resi − 3 ri-spediti), identica alla vista
--  11) niente da seminare: id inesistente e array VUOTO danno zero righe — vuoto
--      NON e' «tutte» (NULL, NULL lo e')
--  12) scope: chi non vede l'ordine non vede la situazione — zero righe
--  13) ⭐ `fatturato_anticipato`: spedito 4 di 10, fatturato 10 sull'ORDINE —
--      allocato sulla merce 4 (la capienza e' il consegnato), anticipato 6,
--      differenza 0 e PAREGGIATA (non «da accreditare»), da_spedire 6.
--      Ereditato il 22-09 da test-vw-contatore-merce-v1 (ritirato con la
--      vista, D6): era il solo presidio del VALORE di questa colonna
--
-- Scopo:
--  - la funzione e' equivalente alla vista per costruzione; questo file
--    COSTRUISCE i casi in cui il seme per DDT risponderebbe un numero sbagliato
--    se leggesse la sola partita di quel DDT (5), o se non riportasse tutte le
--    righe toccate (9). Un EXCEPT ALL sulle righe di oggi non lo farebbe.
--  - il 2 e il 3 sono pin di FORMA: D1 (un corpo) e il contratto dei tipi.
--  - ⭐ il mondo (cliente, articolo) e' COSTRUITO dai builder di dbops, non
--    cercato: il file deve girare identico su dbdev e su un database da zero.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

-- ============================================================
-- 1-3) Struttura: funzione, pin di D1, pin dei tipi
-- ============================================================
SELECT ok(
  (SELECT p.prosqlbody IS NOT NULL AND NOT p.prosecdef
      AND EXISTS (SELECT 1 FROM pg_depend d
                   WHERE d.classid = 'pg_proc'::regclass AND d.objid = p.oid
                     AND d.refclassid = 'pg_proc'::regclass
                     AND d.refobjid = 'vendite.fn_partite_merce'::regproc)
     FROM pg_proc p
    WHERE p.proname = 'fn_situazione_merce_ordine' AND p.pronamespace = 'vendite'::regnamespace),
  '1) fn_situazione_merce_ordine esiste, e'' BEGIN ATOMIC, non DEFINER, e dipende da fn_partite_merce in pg_depend');

SELECT ok(
  (SELECT d ~ 'fn_situazione_merce_ordine' AND d !~ 'vendite\.ordini_righe'
      AND d !~ 'vw_partite_merce' AND d !~ 'fn_partite_merce' AND d !~ 'vw_af_merce_per_riga'
     FROM pg_get_viewdef('vendite.vw_situazione_merce_ordine'::regclass, true) AS d),
  '2) la vista e'' la proiezione di fn_situazione_merce_ordine: nomina la funzione e nessuna tabella');

SELECT is(
  (SELECT count(*)::int || '|' || max(format_type(a.atttypid, a.atttypmod)) FILTER (WHERE a.attname = 'ordinato')
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.vw_situazione_merce_ordine'::regclass AND a.attnum > 0 AND NOT a.attisdropped)
  || '|' || COALESCE((SELECT o.option_value FROM pg_options_to_table(
                        (SELECT c.reloptions FROM pg_class c WHERE c.oid = 'vendite.vw_situazione_merce_ordine'::regclass)) o
                       WHERE o.option_name = 'security_invoker'), 'off'),
  '21|numeric(18,6)|on',
  '3) la vista ha 21 colonne, ordinato resta numeric(18,6), security_invoker=on');

-- ============================================================
-- Il mondo si COSTRUISCE, non si cerca (guida pgTAP; D7). Stessa fixture di
-- test-fn-partite-merce-chiusura-v1: cliente e articolo dai builder di dbops,
-- il catalogo per codice_interno.
-- ⚠️ Ordine obbligato: PRIMA il contesto, POI il cliente (il legame BA ->
--    emittente lo scrive il trigger z90 verso chi agisce).
-- ============================================================
CREATE TEMP TABLE tmp_cli_sm AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_situazione');

CREATE TEMP TABLE tmp_refs_sm AS
SELECT
  c.billing_account_id,
  dbops.fn_pgtap_crea_articolo('PGT-SM-ART', false) AS articolo_id
FROM tmp_cli_sm c;

-- Commessa + ROOT, dal builder: serve alle attivita' fatturabili (corsia ORD).
CREATE TEMP TABLE tmp_com_sm AS
SELECT commessa_id
  FROM dbops.fn_pgtap_crea_commessa('pgtap_situazione', NULL, (SELECT billing_account_id FROM tmp_refs_sm),
                                    p_con_sorgente_root => true);

-- ============================================================
-- Helper (padre e figlio in due istruzioni: le CTE che scrivono condividono
-- la snapshot e le policy negano fail-closed)
-- ============================================================

-- Il fatturato d'ordine: un'attivita' sulla riga d'ordine (sorgente
-- ORDINE_VENDITA, E-3: la chiave la compone il builder), emessa.
CREATE OR REPLACE FUNCTION pg_temp.sm_mk_af(p_ordine_uid uuid, p_ordine_riga_id bigint, p_qta numeric)
RETURNS void AS $$
BEGIN
  PERFORM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_com_sm), 20,
            (SELECT articolo_id FROM tmp_refs_sm),
            p_sorgente_codice => 'ORDINE_VENDITA', p_sorgente_chiave => p_ordine_uid::text,
            p_sorgente_riga_id => p_ordine_riga_id, p_quantita => p_qta,
            p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31');
  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_sm), true, false);
END $$ LANGUAGE plpgsql;

-- Il confronto fn(seme) = vista filtrata COME LA FILTRA IL BACKEND, nei DUE
-- versi: per ordine `ordine_id = o`, per DDT l'EXISTS sul fulfillment.
CREATE OR REPLACE FUNCTION pg_temp.sm_diff_ordine(p_ord bigint) RETURNS bigint AS $$
  SELECT (SELECT count(*) FROM (SELECT * FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[p_ord])
                                 EXCEPT ALL
                                SELECT * FROM vendite.vw_situazione_merce_ordine v WHERE v.ordine_id = p_ord) a)
       + (SELECT count(*) FROM (SELECT * FROM vendite.vw_situazione_merce_ordine v WHERE v.ordine_id = p_ord
                                 EXCEPT ALL
                                SELECT * FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[p_ord])) b);
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.sm_diff_ddt(p_ddt bigint) RETURNS bigint AS $$
  WITH v AS (
    SELECT s.* FROM vendite.vw_situazione_merce_ordine s
     WHERE EXISTS (SELECT 1 FROM vendite.ordini_righe_fulfillment f
                     JOIN vendite.ddt_righe dr_f ON dr_f.id = f.ddt_riga_id
                    WHERE f.ordine_riga_id = s.ordine_riga_id AND dr_f.ddt_id = p_ddt))
  SELECT (SELECT count(*) FROM (SELECT * FROM vendite.fn_situazione_merce_ordine(ARRAY[p_ddt], NULL)
                                 EXCEPT ALL SELECT * FROM v) a)
       + (SELECT count(*) FROM (SELECT * FROM v
                                 EXCEPT ALL SELECT * FROM vendite.fn_situazione_merce_ordine(ARRAY[p_ddt], NULL)) b);
$$ LANGUAGE sql;

-- ============================================================
-- CASO 1 — un ordine da 30 spedito su TRE DDT (10, 10, 10), fatturato
--          dall'ORDINE per 15.
-- ============================================================
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la riga 2 «mai
--   spedita» del caso 2 nasce QUI, in bozza, con la riga 1 (20261008-90: dopo i
--   DDT l'ordine e' fuori bozza e non prende righe). Il 4 legge percio' la riga 1.
CREATE TEMP TABLE tmp_o1 AS
SELECT ordine_id, ordine_uid, ordine_riga_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('situazione 1', 'CONFERMATO',
         (SELECT billing_account_id FROM tmp_refs_sm), p_fatturazione_trigger => 'CONSEGNATO',
         p_data_ordine => DATE '2026-08-05',
         p_righe => jsonb_build_array(
           jsonb_build_object('articolo_id', (SELECT articolo_id FROM tmp_refs_sm), 'quantita', 30, 'prezzo', 20),
           jsonb_build_object('articolo_id', (SELECT articolo_id FROM tmp_refs_sm), 'quantita', 4, 'prezzo', 20,
                              'descrizione', 'Riga mai spedita')));
-- Due righe attive: la quantita' da evadere si dice con p_righe.
CREATE TEMP TABLE tmp_d1 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('situazione 1', p_ordine_id => (SELECT ordine_id FROM tmp_o1),
         p_righe => jsonb_build_array(jsonb_build_object(
                      'ordine_riga_id', (SELECT ordine_riga_id FROM tmp_o1), 'qta_da_evadere', 10)),
         p_data => DATE '2026-08-10');
CREATE TEMP TABLE tmp_d2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('situazione 1', p_ordine_id => (SELECT ordine_id FROM tmp_o1),
         p_righe => jsonb_build_array(jsonb_build_object(
                      'ordine_riga_id', (SELECT ordine_riga_id FROM tmp_o1), 'qta_da_evadere', 10)),
         p_data => DATE '2026-08-11');
CREATE TEMP TABLE tmp_d3 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('situazione 1', p_ordine_id => (SELECT ordine_id FROM tmp_o1),
         p_righe => jsonb_build_array(jsonb_build_object(
                      'ordine_riga_id', (SELECT ordine_riga_id FROM tmp_o1), 'qta_da_evadere', 10)),
         p_data => DATE '2026-08-12');
SELECT pg_temp.sm_mk_af((SELECT ordine_uid FROM tmp_o1), (SELECT ordine_riga_id FROM tmp_o1), 15);

SELECT results_eq(
  $q$SELECT s.consegnato, s.fatturato_da_ordine, s.differenza, s.stato::text, s.partite_merce, s.da_spedire
       FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)]) s
      WHERE s.riga_nr = 1$q$,
  $q$VALUES (30::numeric, 15::numeric, 15::numeric, 'DA_FATTURARE', 3, 0::numeric)$q$,
  '4) per ORDINE: consegnato 30, fatturato dall''ordine 15, differenza 15, DA_FATTURARE, 3 partite, niente da spedire');

-- ⭐ Il DDT di MEZZO. La situazione della riga d'ordine e' INTERA: 30 e 3
--    partite, non i 10 di quella spedizione.
SELECT results_eq(
  $q$SELECT s.ordine_riga_id, s.consegnato, s.fatturato_da_ordine, s.partite_merce
       FROM vendite.fn_situazione_merce_ordine(ARRAY[(SELECT ddt_id FROM tmp_d2)], NULL) s$q$,
  $q$SELECT ordine_riga_id, 30::numeric, 15::numeric, 3 FROM tmp_o1$q$,
  '5) per il DDT di mezzo: la riga d''ordine toccata, con la situazione INTERA (30 consegnati, 3 partite) e non la sola partita di quel DDT');

SELECT is(
  pg_temp.sm_diff_ordine((SELECT ordine_id FROM tmp_o1)) + pg_temp.sm_diff_ddt((SELECT ddt_id FROM tmp_d2)),
  0::bigint,
  '6) nei due semi le righe sono identiche alla vista filtrata come la filtra il backend, nei due versi');

-- ============================================================
-- CASO 2 — la riga MAI SPEDITA dello stesso ordine e l'ordine in BOZZA
-- ============================================================
-- (la riga 2 di tmp_o1 e' nata in bozza con l'ordine: vedi il caso 1)

SELECT results_eq(
  $q$SELECT (SELECT s.stato::text || '|' || (s.da_spedire = 4)::text || '|' || s.partite_merce::text
               FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)]) s
              WHERE s.riga_nr = 2),
            (SELECT count(*)::int FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)])),
            (SELECT count(*)::int FROM vendite.fn_situazione_merce_ordine(ARRAY[(SELECT ddt_id FROM tmp_d2)], NULL))$q$,
  $q$VALUES ('NON_SPEDITA|true|0', 2, 1)$q$,
  '7) la riga mai spedita: NON_SPEDITA con 4 da spedire per seme ordine (2 righe); per seme DDT non esce (1 riga)');

CREATE TEMP TABLE tmp_ob AS
SELECT ordine_id, ordine_uid, ordine_riga_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('situazione 2', 'DRAFT',
         (SELECT billing_account_id FROM tmp_refs_sm), p_quantita => 7, p_prezzo => 20,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_sm), p_fatturazione_trigger => 'CONSEGNATO',
         p_data_ordine => DATE '2026-08-05');

SELECT results_eq(
  $q$SELECT s.stato::text, s.da_spedire IS NULL, s.giorni_ritardo IS NULL
       FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_ob)]) s$q$,
  $q$VALUES ('NON_IMPEGNATA', true, true)$q$,
  '8) l''ordine in bozza: NON_IMPEGNATA, da_spedire NULL (non si applica), non zero');

-- ============================================================
-- CASO 3 — la riga MULTIPLA: un DDT dell'ordine A3 evade ANCHE un ordine B
--          (id maggiore). La partita conta sotto la riga MINIMA (A3): per seme
--          DDT escono entrambe le righe toccate — A3 NON_MISURABILE, B senza
--          partite.
-- ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-6): un legame nasce
--   solo con la bolla in bozza. Fino a quel giorno il legame con B si scriveva
--   sul primo DDT del caso 1, gia' consegnato; ora nasce con la bolla in
--   bozza (DRAFT, poi CONSEGNATO per la matrice), e la coppia e' DEDICATA: sul DDT del
--   caso 1 avrebbe reso A non misurabile gia' al test 4.
-- ============================================================
CREATE TEMP TABLE tmp_dm AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('situazione 3', 'DRAFT', p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_sm),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_sm), p_prezzo => 20,
         p_fatturazione_trigger => 'CONSEGNATO',
         p_quantita => 10, p_data => DATE '2026-08-10',
         p_data_ordine => DATE '2026-08-05');
CREATE TEMP TABLE tmp_o3 AS SELECT ordine_id, ordine_uid, ordine_riga_id FROM tmp_dm;
CREATE TEMP TABLE tmp_om AS
SELECT ordine_id, ordine_uid, ordine_riga_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('situazione 3 B', 'CONFERMATO',
         (SELECT billing_account_id FROM tmp_refs_sm), p_quantita => 10, p_prezzo => 20,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_sm), p_fatturazione_trigger => 'CONSEGNATO',
         p_data_ordine => DATE '2026-08-05');
INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa, storicizza)
SELECT (SELECT ordine_riga_id FROM tmp_om), d.ddt_riga_id, d.quantita, false
  FROM tmp_dm d;
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_dm), 'CONSEGNATO');

SELECT results_eq(
  $q$SELECT s.ordine_riga_id = (SELECT ordine_riga_id FROM tmp_o3), s.stato::text, s.partite_merce, s.misurabile
       FROM vendite.fn_situazione_merce_ordine(ARRAY[(SELECT ddt_id FROM tmp_dm)], NULL) s
      ORDER BY s.ordine_riga_id$q$,
  $q$VALUES (true, 'NON_MISURABILE', 1, false), (false, 'NON_SPEDITA', 0, true)$q$,
  '9) riga MULTIPLA: per il DDT escono le DUE righe toccate — A3 NON_MISURABILE con la sua partita, B senza partite');

-- (l'uguaglianza con la vista per DDT1 e per l'ordine B e' asserita nel 10,
--  insieme a quella del caso della ri-consegna)

-- ============================================================
-- CASO 4 — la ri-consegna: reso per ri-consegna 5, ri-spedizione 3.
--   Partita d'origine: consegnato 10 + 3 ri-consegnati = 13, reso 5, tenuti 8;
--   la riga del DDT di ri-consegna e' esclusa (e_riconsegna). Evaso 13 (il
--   DDT di ri-consegna scrive un fulfillment); qta_riconsegna = 5 resi − 0
--   rinunciati = 5 → da_spedire = 10 − 13 + 5 = 2 (i pezzi non ancora
--   ri-spediti).
-- ============================================================
CREATE TEMP TABLE tmp_p AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('situazione 4', p_stato_codice_interno => 'CONSEGNATO', p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_sm),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_sm), p_prezzo => 20,
         p_fatturazione_trigger => 'CONSEGNATO',
         p_quantita => 10, p_data => DATE '2026-08-13',
         p_data_ordine => DATE '2026-08-05');
CREATE TEMP TABLE tmp_o2 AS SELECT ordine_id, ordine_uid, ordine_riga_id FROM tmp_p;
-- Il reso per ri-consegna confermato e la ri-spedizione consegnata: dai builder.
CREATE TEMP TABLE tmp_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('situazione 4', (SELECT ddt_id FROM tmp_p), 5, 'RESO_PER_RICONSEGNA',
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p));
CREATE TEMP TABLE tmp_r1 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM tmp_reso),
         p_resi_riga_id => (SELECT resi_riga_id FROM tmp_reso), p_quantita => 3, p_data => DATE '2026-09-01');

SELECT results_eq(
  $q$SELECT s.consegnato, s.reso, s.tenuti, s.in_riconsegna, s.da_spedire, s.partite_merce,
            pg_temp.sm_diff_ordine((SELECT ordine_id FROM tmp_o2))
            + pg_temp.sm_diff_ddt((SELECT ddt_id FROM tmp_p))
            + pg_temp.sm_diff_ddt((SELECT ddt_id FROM tmp_dm))
            + pg_temp.sm_diff_ordine((SELECT ordine_id FROM tmp_om))
       FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o2)]) s$q$,
  $q$VALUES (13::numeric, 5::numeric, 8::numeric, 0::numeric, 2::numeric, 1, 0::bigint)$q$,
  '10) ri-consegna: consegnato 13, reso 5, tenuti 8, 2 da spedire; identica alla vista (anche i casi 3 e 9)');

-- ============================================================
-- 11) Niente da seminare
-- ============================================================
SELECT is(
  (SELECT count(*) FROM vendite.fn_situazione_merce_ordine(ARRAY[-1], NULL))::text
  || '|' || (SELECT count(*) FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[-1]))::text
  || '|' || (SELECT count(*) FROM vendite.fn_situazione_merce_ordine(ARRAY[]::bigint[], ARRAY[]::bigint[]))::text
  || '|' || ((SELECT count(*) FROM vendite.fn_situazione_merce_ordine(NULL, NULL))
             = (SELECT count(*) FROM vendite.vw_situazione_merce_ordine))::text,
  '0|0|0|true',
  '11) id inesistente e array VUOTO: zero righe — vuoto non e'' «tutte»; (NULL, NULL) lo e''');

-- ============================================================
-- CASO 5 — il fatturato che non ha ancora una merce. Ordine da 10, spedito 4,
--          fatturato 10 sull'ORDINE (trigger CONFERMATO, la configurazione del
--          cliente standard). L'allocazione sulla merce ha per capienza il
--          CONSEGNATO: 4 alla partita, 6 restano `fatturato_anticipato`. Il
--          saldo NON li vede — differenza 0, PAREGGIATA — perche' un -6 senza
--          reso non e' un accredito dovuto: e' merce da spedire (da_spedire 6).
--          ⚠️ Il contatore ritirato (vw_contatore_merce) qui diceva -6: era la
--          «parita'» del vecchio conto, e la ragione per cui il pannello
--          leggeva la situazione e non lui.
-- ============================================================
CREATE TEMP TABLE tmp_d5 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('situazione 5', p_stato_codice_interno => 'CONSEGNATO', p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_sm),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_sm), p_prezzo => 20,
         p_fatturazione_trigger => 'CONSEGNATO',
         p_quantita => 10, p_qta_da_evadere => 4, p_data => DATE '2026-08-16',
         p_data_ordine => DATE '2026-08-05');
CREATE TEMP TABLE tmp_o5 AS SELECT ordine_id, ordine_uid, ordine_riga_id FROM tmp_d5;
SELECT pg_temp.sm_mk_af((SELECT ordine_uid FROM tmp_o5), (SELECT ordine_riga_id FROM tmp_o5), 10);

SELECT results_eq(
  $q$SELECT s.consegnato, s.fatturato_da_ordine, s.fatturato_anticipato, s.differenza, s.stato::text, s.da_spedire
       FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o5)]) s$q$,
  $q$VALUES (4::numeric, 4::numeric, 6::numeric, 0::numeric, 'PAREGGIATA', 6::numeric)$q$,
  '13) spedito 4 di 10 e fatturato 10 sull''ordine: allocato 4, fatturato_anticipato 6, differenza 0 PAREGGIATA, 6 da spedire');

-- ============================================================
-- 12) Scope: chi non vede l'ordine non vede la situazione.
-- ⚠️ Con la veste OPERATORE e un utente senza whitelist la RLS non fa vedere
--    l'ordine, e la funzione — INVOKER — risponde ZERO righe, non conti a zero.
-- ============================================================
SELECT set_config('app.current_user_id', '999999999', true);

SELECT is(
  (SELECT count(*) FROM vendite.fn_situazione_merce_ordine(NULL, ARRAY[(SELECT ordine_id FROM tmp_o1)])),
  0::bigint,
  '12) scope che non vede l''ordine: la situazione sparisce, non esce con dei conti a zero (rosso da owner, che salta la RLS; verde come app)');

SELECT * FROM finish();
ROLLBACK;
