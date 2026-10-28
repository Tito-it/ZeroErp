-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): l'ordine B2 da dbops.fn_pgtap_crea_ordine_con_righe, la commessa da dbops.fn_pgtap_crea_commessa (sorgente ROOT), le attivita' fatturate da dbops.fn_pgtap_crea_commessa_attivita con la sorgente DDT_VENDITA (E-3) e dbops.fn_pgtap_fattura_attivita; helper ca_mk_ordine, ca_mk_af e ca_fattura ritirati. Resta a mano il legame della riga MULTIPLA (il caso del 7).
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): i resi dal builder dbops.fn_pgtap_crea_reso (i due resi A e B sulla stessa riga, nell'ordine che decide la greedy; il tipo per codice); helper ca_mk_reso ritirato, l'azione conferma_reso la concede il builder.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, D-1): gli ordini costruiti dal builder nascono al 2026-08-05 (p_data_ordine), come gli ordini scritti a mano prima del giro 1: nessuna bolla piu' vecchia del suo ordine.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): le bolle da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (data con p_data); restano scritti a mano l'ordine B2 senza bolla e il legame della riga MULTIPLA (in bozza, il caso del 7) e i resi (giro 2).
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_resi_da_accreditare — la coda accrediti PER DOCUMENTO
--       (D14 giro 2 — D3; brief-db-partita-merce-per-documento §2.2, §7;
--        changeSet 20260921-28..-31).
--
-- Indice test (plan 12):
--   1) la funzione esiste, e' BEGIN ATOMIC, NON e' SECURITY DEFINER e dipende
--      da fn_partite_merce nel catalogo (la catena RLS passa di li')
--   2) ⭐ pin di D1: la vista e' la PROIEZIONE della funzione — nomina
--      fn_resi_da_accreditare e nessuna tabella, nessuna partita
--   3) ⭐ pin dei tipi: 27 colonne coi CINQUE typmod dei varchar (reso_numero 32,
--      ba_codice 30, descrizione 255, motivo 255, ddt_numero 20) — un SELECT *
--      dalla funzione li perderebbe — e security_invoker=on
--   4) ⭐ LE SORELLE: partita da 10 fatturata 6, DUE resi a credito sulla stessa
--      riga (A 4, poi B 3): capienza 3 → A prende 3 e B resta fuori. Chiesta
--      per DDT la coda ha UNA riga (A, 3, DOVUTA) — senza la sorella A, B si
--      prenderebbe i 3
--   5) ⭐ il guard del ponte attraverso la funzione: fn_resi_riga_tetti_accredito
--      dice 3 per A e 0 per B (il valore fail-closed)
--   6) seme per DDT e per ORDINE: identici alla vista filtrata come la filtra il
--      backend (ddt_id / EXISTS sul fulfillment), nei due versi
--   7) ⭐ riga MULTIPLA (la riga di DDT evade anche un ordine B2): la coda per
--      l'ordine B2 la CONTIENE (predicato del BB), mentre la partita per B2 non
--      esce da fn_partite_merce (ordine_id = riga minima): due semantiche
--      «per ordine», di proposito diverse
--   8) ⭐ il verbo attraverso la funzione: fn_accredita_riga_reso(A) scrive
--      qta_partita 3; emessa la rettifica, la partita pareggia e la coda del
--      DDT e' vuota (gia_accreditato 3)
--   9) FACOLTATIVA: reso PER RI-CONSEGNA con residuo aperto su una partita
--      fatturata per intero → in coda con l'etichetta FACOLTATIVA
--  10) niente in coda: reso su una partita NON fatturata (differenza positiva)
--      da' zero righe per quel DDT, come id inesistente e array VUOTO
--  11) (NULL, NULL) = la vista: stesso numero di righe (vuoto NON e' «tutte»)
--  12) scope: chi non vede il documento non vede la coda — zero righe
--
-- Scopo:
--  - la funzione e' equivalente alla vista per costruzione; questo file
--    COSTRUISCE il caso in cui, senza le sorelle nella finestra, la greedy
--    darebbe a una riga una quota gia' presa (4, 5), e quello in cui il seme
--    per ordine deve seguire il predicato del backend e non quello della
--    partita (7). Un EXCEPT ALL sulle righe di oggi non lo farebbe.
--  - i due VERBI (accredita, guard del ponte) si provano attraverso la
--    funzione: sono i lettori per riga che pagavano la coda di tutti.
--  - ⭐ il mondo (cliente, articolo) e' COSTRUITO dai builder di dbops, non
--    cercato: il file deve girare identico su dbdev e su un database da zero.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

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
    WHERE p.proname = 'fn_resi_da_accreditare' AND p.pronamespace = 'vendite'::regnamespace),
  '1) fn_resi_da_accreditare esiste, e'' BEGIN ATOMIC, non DEFINER, e dipende da fn_partite_merce in pg_depend');

SELECT ok(
  (SELECT d ~ 'fn_resi_da_accreditare' AND d !~ 'vendite\.resi_righe'
      AND d !~ 'vw_partite_merce' AND d !~ 'fn_partite_merce' AND d !~ 'vw_resi_righe_effettive'
     FROM pg_get_viewdef('vendite.vw_resi_da_accreditare'::regclass, true) AS d),
  '2) la vista e'' la proiezione di fn_resi_da_accreditare: nomina la funzione e nessuna tabella');

SELECT is(
  (SELECT count(*)::int || '|' ||
          string_agg(a.attname || '=' || format_type(a.atttypid, a.atttypmod), ',' ORDER BY a.attnum)
            FILTER (WHERE a.attname IN ('reso_numero','ba_codice','descrizione','motivo','ddt_numero'))
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.vw_resi_da_accreditare'::regclass AND a.attnum > 0 AND NOT a.attisdropped)
  || '|' || COALESCE((SELECT o.option_value FROM pg_options_to_table(
                        (SELECT c.reloptions FROM pg_class c WHERE c.oid = 'vendite.vw_resi_da_accreditare'::regclass)) o
                       WHERE o.option_name = 'security_invoker'), 'off'),
  '27|reso_numero=character varying(32),ba_codice=character varying(30),descrizione=character varying(255),motivo=character varying(255),ddt_numero=character varying(20)|on',
  '3) la vista ha 27 colonne, i cinque varchar tengono il typmod, security_invoker=on');

-- ============================================================
-- Il mondo si COSTRUISCE, non si cerca (guida pgTAP; D7). Stessa fixture di
-- test-fn-partite-merce-chiusura-v1: cliente e articolo dai builder di dbops,
-- il catalogo per codice_interno.
-- ⚠️ Ordine obbligato: PRIMA il contesto, POI il cliente (il legame BA ->
--    emittente lo scrive il trigger z90 verso chi agisce).
-- ============================================================
CREATE TEMP TABLE tmp_cli_ca AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_coda_accrediti');

CREATE TEMP TABLE tmp_refs_ca AS
SELECT
  c.billing_account_id,
  dbops.fn_pgtap_crea_articolo('PGT-CA-ART', false) AS articolo_id
FROM tmp_cli_ca c;

-- Commessa + ROOT, dal builder: serve alle attivita' fatturabili (corsia DDT).
CREATE TEMP TABLE tmp_com_ca AS
SELECT commessa_id
  FROM dbops.fn_pgtap_crea_commessa('pgtap_coda_accrediti', NULL, (SELECT billing_account_id FROM tmp_refs_ca),
                                    p_con_sorgente_root => true);

-- ============================================================
-- Helper (padre e figlio in due istruzioni: le CTE che scrivono condividono
-- la snapshot e le policy negano fail-closed)
-- ============================================================

-- Una FATTURA sul segmento DDT (l'accredito copia il prezzo da fatture_righe):
-- l'attivita' sulla riga della bolla (sorgente DDT_VENDITA, E-3), emessa e
-- agganciata dal builder. Restituisce la riga di fattura.
CREATE OR REPLACE FUNCTION pg_temp.ca_fattura(p_ddt_uid uuid, p_ddt_riga_id bigint, p_qta numeric)
RETURNS bigint AS $$
DECLARE v_att bigint; v_riga bigint;
BEGIN
  SELECT a.attivita_id INTO v_att
    FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_com_ca), 20,
           (SELECT articolo_id FROM tmp_refs_ca),
           p_sorgente_codice => 'DDT_VENDITA', p_sorgente_uid => p_ddt_uid::text,
           p_sorgente_riga_id => p_ddt_riga_id, p_quantita => p_qta,
           p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31') a;
  SELECT f.fattura_riga_id INTO v_riga
    FROM dbops.fn_pgtap_fattura_attivita('pgtap_coda_accrediti', ARRAY[v_att]) f;
  RETURN v_riga;
END $$ LANGUAGE plpgsql;

-- Il confronto fn(seme) = vista filtrata COME LA FILTRA IL BACKEND (il BB
-- filtro_coda_per_documento), nei DUE versi.
CREATE OR REPLACE FUNCTION pg_temp.ca_diff_ddt(p_ddt bigint) RETURNS bigint AS $$
  SELECT (SELECT count(*) FROM (SELECT * FROM vendite.fn_resi_da_accreditare(ARRAY[p_ddt], NULL)
                                 EXCEPT ALL
                                SELECT * FROM vendite.vw_resi_da_accreditare v WHERE v.ddt_id = p_ddt) a)
       + (SELECT count(*) FROM (SELECT * FROM vendite.vw_resi_da_accreditare v WHERE v.ddt_id = p_ddt
                                 EXCEPT ALL
                                SELECT * FROM vendite.fn_resi_da_accreditare(ARRAY[p_ddt], NULL)) b);
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.ca_diff_ordine(p_ord bigint) RETURNS bigint AS $$
  WITH v AS (
    SELECT q.* FROM vendite.vw_resi_da_accreditare q
     WHERE EXISTS (SELECT 1 FROM vendite.ordini_righe_fulfillment f
                     JOIN vendite.ordini_righe orr ON orr.id = f.ordine_riga_id
                    WHERE f.ddt_riga_id = q.ddt_riga_id AND orr.ordine_id = p_ord))
  SELECT (SELECT count(*) FROM (SELECT * FROM vendite.fn_resi_da_accreditare(NULL, ARRAY[p_ord])
                                 EXCEPT ALL SELECT * FROM v) a)
       + (SELECT count(*) FROM (SELECT * FROM v
                                 EXCEPT ALL SELECT * FROM vendite.fn_resi_da_accreditare(NULL, ARRAY[p_ord])) b);
$$ LANGUAGE sql;

-- ============================================================
-- CASO 1 — LE SORELLE. Partita da 10 fatturata 6 (corsia DDT); due resi A
--          CREDITO sulla stessa riga: A 4, poi B 3. tenuti 3, fatturati 6:
--          capienza 3. La greedy per resi_riga_id da' 3 ad A e 0 a B.
-- ============================================================
-- ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-6): un legame
--   nasce solo con la bolla in bozza. La bolla si chiede DRAFT, la riga
--   MULTIPLA si lega all'ordine B2, poi la bolla va a CONSEGNATO: dopo la
--   consegna l'INSERT e' E_RIGA_DOC_NON_BOZZA.
CREATE TEMP TABLE tmp_p AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('coda accrediti 1', 'DRAFT', p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ca),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ca), p_prezzo => 20,
         p_fatturazione_trigger => 'CONSEGNATO',
         p_quantita => 10, p_data => DATE '2026-08-13',
         p_data_ordine => DATE '2026-08-05');
CREATE TEMP TABLE tmp_o1 AS SELECT ordine_id, ordine_uid, ordine_riga_id FROM tmp_p;
-- L'ordine B2, confermato e SENZA bolla: la bolla la riceve solo per legame.
CREATE TEMP TABLE tmp_ob AS
SELECT ordine_id, ordine_uid, ordine_riga_id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('coda accrediti B2', 'CONFERMATO',
         (SELECT billing_account_id FROM tmp_refs_ca), p_quantita => 10, p_prezzo => 20,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ca), p_fatturazione_trigger => 'CONSEGNATO',
         p_data_ordine => DATE '2026-08-05');
INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa, storicizza)
SELECT (SELECT ordine_riga_id FROM tmp_ob), p.ddt_riga_id, p.quantita, false
  FROM tmp_p p;
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_p), 'CONSEGNATO');
CREATE TEMP TABLE tmp_fr AS SELECT pg_temp.ca_fattura((SELECT ddt_uid FROM tmp_p), (SELECT ddt_riga_id FROM tmp_p), 6) AS fattura_riga_id;
-- I due resi a credito, confermati, dal builder: A prima di B (la greedy va per resi_riga_id).
CREATE TEMP TABLE tmp_ra AS
SELECT * FROM dbops.fn_pgtap_crea_reso('coda accrediti 1', (SELECT ddt_id FROM tmp_p), 4, 'RESO_A_CREDITO',
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p));
CREATE TEMP TABLE tmp_rb AS
SELECT * FROM dbops.fn_pgtap_crea_reso('coda accrediti 1', (SELECT ddt_id FROM tmp_p), 3, 'RESO_A_CREDITO',
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p));

SELECT results_eq(
  $q$SELECT q.resi_riga_id = (SELECT resi_riga_id FROM tmp_ra), q.accredito_dovuto, q.etichetta::text, q.tenuti, q.fatturati
       FROM vendite.fn_resi_da_accreditare(ARRAY[(SELECT ddt_id FROM tmp_p)], NULL) q$q$,
  $q$VALUES (true, 3::numeric, 'DOVUTA', 3::numeric, 6::numeric)$q$,
  '4) le sorelle: per il DDT la coda ha UNA riga — A con 3 (DOVUTA); B resta fuori perche'' A ha preso la capienza');

-- ⭐ Il guard del ponte legge la coda attraverso la funzione: 3 per A, 0 per B.
--    Senza la sorella A nella finestra, B da sola leggerebbe 3.
SELECT results_eq(
  $q$SELECT (SELECT t.accredito_dovuto FROM vendite.fn_resi_riga_tetti_accredito((SELECT resi_riga_id FROM tmp_ra), (SELECT fattura_riga_id FROM tmp_fr)) t),
            (SELECT t.accredito_dovuto FROM vendite.fn_resi_riga_tetti_accredito((SELECT resi_riga_id FROM tmp_rb), (SELECT fattura_riga_id FROM tmp_fr)) t),
            (SELECT t.qta_riga_fattura   FROM vendite.fn_resi_riga_tetti_accredito((SELECT resi_riga_id FROM tmp_ra), (SELECT fattura_riga_id FROM tmp_fr)) t)$q$,
  $q$VALUES (3::numeric, 0::numeric, 6::numeric)$q$,
  '5) il tetto attraverso la funzione: 3 per A, 0 per B (fail-closed), 6 sulla riga di fattura');

SELECT is(
  pg_temp.ca_diff_ddt((SELECT ddt_id FROM tmp_p)) + pg_temp.ca_diff_ordine((SELECT ordine_id FROM tmp_o1)),
  0::bigint,
  '6) per DDT e per ordine la coda e'' identica alla vista filtrata come la filtra il backend, nei due versi');

-- ============================================================
-- CASO 2 — la riga MULTIPLA: la riga di DDT evade ANCHE un ordine B2 (id
--          maggiore). Nella coda di B2 c'e' (fulfillment); nella partita per
--          B2 no (ordine_id = riga minima). Due semantiche, di proposito.
-- ============================================================
-- (il legame con B2 nasce con la bolla in bozza, caso 1: D-6 del 2026-10-11)

SELECT results_eq(
  $q$SELECT (SELECT count(*)::int FROM vendite.fn_resi_da_accreditare(NULL, ARRAY[(SELECT ordine_id FROM tmp_ob)])),
            (SELECT count(*)::int FROM vendite.fn_partite_merce(NULL, ARRAY[(SELECT ordine_id FROM tmp_ob)])),
            pg_temp.ca_diff_ordine((SELECT ordine_id FROM tmp_ob))$q$,
  $q$VALUES (1, 0, 0::bigint)$q$,
  '7) riga MULTIPLA: la coda per l''ordine B2 la contiene (predicato del backend), la partita per B2 no (riga minima); identica alla vista');

-- ============================================================
-- CASO 3 — il verbo attraverso la funzione: accredita A, e A esce dalla coda.
-- ============================================================
CREATE TEMP TABLE tmp_acc AS SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_ra));
-- La RETTIFICA scritta in commessa entra nel conto quando diventa attivita'
-- fatturabile (come nel flusso: l'emissione segue il verbo).
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ca), true, false);

SELECT results_eq(
  $q$SELECT (SELECT sum(a.qta_partita) FROM tmp_acc a),
            (SELECT count(*)::int FROM vendite.fn_resi_da_accreditare(ARRAY[(SELECT ddt_id FROM tmp_p)], NULL)),
            (SELECT count(*)::int FROM vendite.vw_resi_da_accreditare v WHERE v.ddt_id = (SELECT ddt_id FROM tmp_p)),
            vendite.fn_resi_riga_accreditato_partita((SELECT resi_riga_id FROM tmp_ra))$q$,
  $q$VALUES (3::numeric, 0, 0, 3::numeric)$q$,
  '8) il verbo: accredita A per 3 (qta_partita); con la rettifica emessa la partita pareggia e la coda del DDT e'' vuota — per la funzione come per la vista');

-- ============================================================
-- CASO 4 — FACOLTATIVA: partita da 5 fatturata 5, reso PER RI-CONSEGNA 2 con
--          residuo aperto: tenuti 3, fatturati 5 → 2 in coda, FACOLTATIVA.
-- ============================================================
CREATE TEMP TABLE tmp_p3 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('coda accrediti 4', p_stato_codice_interno => 'CONSEGNATO', p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ca),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ca), p_prezzo => 20,
         p_fatturazione_trigger => 'CONSEGNATO',
         p_quantita => 5, p_data => DATE '2026-08-14',
         p_data_ordine => DATE '2026-08-05');
SELECT pg_temp.ca_fattura((SELECT ddt_uid FROM tmp_p3), (SELECT ddt_riga_id FROM tmp_p3), 5);
CREATE TEMP TABLE tmp_rc AS
SELECT * FROM dbops.fn_pgtap_crea_reso('coda accrediti 4', (SELECT ddt_id FROM tmp_p3), 2, 'RESO_PER_RICONSEGNA',
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p3));

SELECT results_eq(
  $q$SELECT q.accredito_dovuto, q.etichetta::text, q.blocco_codice IS NULL, pg_temp.ca_diff_ddt((SELECT ddt_id FROM tmp_p3))
       FROM vendite.fn_resi_da_accreditare(ARRAY[(SELECT ddt_id FROM tmp_p3)], NULL) q$q$,
  $q$VALUES (2::numeric, 'FACOLTATIVA', true, 0::bigint)$q$,
  '9) reso per ri-consegna con residuo aperto su partita fatturata: 2 in coda, FACOLTATIVA, identica alla vista');

-- ============================================================
-- CASO 5 — niente in coda: reso su una partita NON fatturata (differenza
--          positiva), id inesistente, array vuoto.
-- ============================================================
CREATE TEMP TABLE tmp_p4 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('coda accrediti 5', p_stato_codice_interno => 'CONSEGNATO', p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ca),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ca), p_prezzo => 20,
         p_fatturazione_trigger => 'CONSEGNATO',
         p_quantita => 5, p_data => DATE '2026-08-15',
         p_data_ordine => DATE '2026-08-05');
CREATE TEMP TABLE tmp_rd AS
SELECT * FROM dbops.fn_pgtap_crea_reso('coda accrediti 5', (SELECT ddt_id FROM tmp_p4), 2, 'RESO_A_CREDITO',
         p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_p4));

SELECT is(
  (SELECT count(*) FROM vendite.fn_resi_da_accreditare(ARRAY[(SELECT ddt_id FROM tmp_p4)], NULL))::text
  || '|' || (SELECT count(*) FROM vendite.fn_resi_da_accreditare(ARRAY[-1], NULL))::text
  || '|' || (SELECT count(*) FROM vendite.fn_resi_da_accreditare(NULL, ARRAY[-1]))::text
  || '|' || (SELECT count(*) FROM vendite.fn_resi_da_accreditare(ARRAY[]::bigint[], ARRAY[]::bigint[]))::text,
  '0|0|0|0',
  '10) reso su partita non fatturata, id inesistente, array VUOTO: zero righe — vuoto non e'' «tutte»');

SELECT is(
  (SELECT count(*) FROM vendite.fn_resi_da_accreditare(NULL, NULL)),
  (SELECT count(*) FROM vendite.vw_resi_da_accreditare),
  '11) (NULL, NULL) e'' la vista: lo stesso numero di righe');

-- ============================================================
-- 12) Scope: chi non vede il documento non vede la coda.
-- ⚠️ Con la veste OPERATORE e un utente senza whitelist la RLS non fa vedere
--    il DDT, e la funzione — INVOKER — risponde ZERO righe.
-- ============================================================
SELECT set_config('app.current_user_id', '999999999', true);

SELECT is(
  (SELECT count(*) FROM vendite.fn_resi_da_accreditare(ARRAY[(SELECT ddt_id FROM tmp_p3)], NULL)),
  0::bigint,
  '12) scope che non vede il DDT: la coda sparisce, non esce con dei conti a zero (rosso da owner, che salta la RLS; verde come app)');

SELECT * FROM finish();
ROLLBACK;
