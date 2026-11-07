-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): la commessa da dbops.fn_pgtap_crea_commessa (sorgente ROOT); pg_temp.ric_fattura compone ora dbops.fn_pgtap_crea_commessa_attivita (sorgente DDT_VENDITA, E-3) e dbops.fn_pgtap_fattura_attivita, per le due partite fatturate.
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): i resi dal builder dbops.fn_pgtap_crea_reso, le ri-spedizioni da dbops.fn_pgtap_crea_ddt_riconsegna (ritirati pg_temp.ric_mk_reso e pg_temp.ric_rispedisci, con indirizzo e causale a mano); nulla della strada del reso resta scritto a mano.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; la bolla di ri-consegna (fn_genera_ddt_riconsegna) tiene indirizzo e causale scritti a mano, gli stati per dbops.fn_pgtap_porta_a_stato; i resi restano a mano (giro 2).
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: D-NC-4 — «una ri-consegna e' merce nuova SOLO per la parte accreditata»
--       (brief-design-note-credito-resi §12.5-bis; changeset 20260818-38)
-- ------------------------------------------------------------
-- Indice test (1..8):
--   1) fixture: partita da 10 fatturata, reso 3 per ri-consegna -> in coda
--   2) ⚠️ SENZA nota di credito la regola e' INERTE: la ri-consegna resta un
--      conto vuoto (differenza NULL, stato RICONSEGNA) — e' il caso D che a
--      agosto ha fermato tutto, e deve restare verde
--   3) SENZA nota di credito la spedizione d'ORIGINE riassorbe i pezzi
--      ri-consegnati: consegnato 10 + 3 = 13
--   4) ⭐ CON la nota di credito i pezzi accreditati CAMBIANO CASA: la
--      spedizione nuova prende quota 3
--   5) ⭐ e diventa una partita vera: DA_FATTURARE per 3
--   6) ⭐ la spedizione d'origine non porta piu' quei pezzi: torna a 10, e non
--      li puo' fatturare una seconda volta (il buco di luglio resta chiuso)
--   7) ⭐ INVARIANTE: la somma dei `consegnato` non cambia mai — i pezzi si
--      spostano, non si moltiplicano
--   8) ⭐ il segmento della spedizione nuova e' LIBERA, quindi il giro di
--      fatturazione normale la vede: nessun verbo nuovo, nessuna seconda
--      pipeline
--
-- Scopo:
--  - il caso non esiste nei dati (zero righe RETTIFICA al 2026-08-17) e si
--    costruisce PASSANDO DALLA MADRE: la nota di credito la crea
--    fn_accredita_riga_reso, non un INSERT a mano. Un ramo si verifica dal
--    percorso che lo attraversa, non dal codice che lo dichiara.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
-- ⛔ rev 2026-10-13: niente app.current_user_id = '1' (in CI l'utente 1 non
--   esiste): l'operatore e' quello del contesto aperto qui sopra.

-- ============================================================
-- Riferimenti (ogni scelta col suo ORDER BY; l'emittente si DERIVA)
-- ============================================================
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): cliente fatturabile legato all'azienda di chi agisce
--   e articolo merce non gestito a magazzino; dal DB si legge solo il seed.
CREATE TEMP TABLE tmp_mondo_ric AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP riconsegna dopo NC');

CREATE TEMP TABLE tmp_refs_ric AS
SELECT
  m.billing_account_id                    AS billing_account_id,
  dbops.fn_pgtap_crea_articolo('PGT-RIC-NC-V1', false)                                              AS articolo_id  -- rev 2026-10-13: costruito
FROM tmp_mondo_ric m;

-- ============================================================
-- Helper: l'attivita' sul segmento di una riga di bolla (E-3: sorgente
-- DDT_VENDITA) e la fattura vera agganciata, dai builder. Torna la riga di
-- fattura.
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.ric_fattura(p_ddt_uid uuid, p_ddt_riga_id bigint, p_qta numeric, p_prezzo numeric)
RETURNS bigint AS $$
DECLARE v_att bigint; v_riga bigint;
BEGIN
  SELECT a.attivita_id INTO v_att
    FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_com_ric), p_prezzo,
             p_articolo_id      => (SELECT articolo_id FROM tmp_refs_ric),
             p_sorgente_codice  => 'DDT_VENDITA',
             p_sorgente_chiave  => p_ddt_uid::text,
             p_sorgente_riga_id => p_ddt_riga_id,
             p_quantita         => p_qta) a;
  SELECT f.fattura_riga_id INTO v_riga
    FROM dbops.fn_pgtap_fattura_attivita('riconsegna dopo nc', ARRAY[v_att]) f;
  RETURN v_riga;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE: consegnati 10 a 20 euro, fatturati 10, resi 3 per ri-consegna
--          -> tenuti 7, fatturati 10 -> accredito dovuto 3 (FACOLTATIVA)
-- ============================================================
CREATE TEMP TABLE tmp_com_ric AS
SELECT c.commessa_id
  FROM dbops.fn_pgtap_crea_commessa('riconsegna dopo nc', NULL,
           (SELECT billing_account_id FROM tmp_refs_ric), p_con_sorgente_root => true) c;

-- La partita: bolla consegnata dal builder, 10 a 20 euro, trigger CONSEGNATO.
CREATE TEMP TABLE tmp_ric_p AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('riconsegna A',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ric),
         p_quantita => 10, p_prezzo => 20,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ric),
         p_fatturazione_trigger => 'CONSEGNATO');

CREATE TEMP TABLE tmp_ric_fatt AS
SELECT pg_temp.ric_fattura((SELECT ddt_uid FROM tmp_ric_p), (SELECT ddt_riga_id FROM tmp_ric_p),
    10, 20) AS fattura_riga_id;

-- Reso PER RI-CONSEGNA: e' il tipo che riapre il residuo, e l'unico che
-- ammette una spedizione di ritorno.
CREATE TEMP TABLE tmp_ric_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('riconsegna A', (SELECT ddt_id FROM tmp_ric_p), 3,
         'RESO_PER_RICONSEGNA');

SELECT is(
  (SELECT q.accredito_dovuto FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_ric_reso)),
  3::numeric,
  '1) fixture: partita da 10 fatturata, reso 3 per ri-consegna -> accredito dovuto 3'
);

-- ============================================================
-- La RI-SPEDIZIONE (due volte, su due partite diverse): la bolla di
-- ri-consegna dal builder, 3 pezzi del reso al 1° agosto, CONSEGNATA.
-- ============================================================
-- ============================================================
-- CASO A — ri-spedizione SENZA nota di credito.
-- ⚠️ E' il caso D di test-fn-list-ddt-da-pushare-contatore-v1: la ri-consegna
--    non e' merce nuova e non deve proiettare nulla. Se diventa rosso, e' la
--    regola D-NC-4 a essere sbagliata, non il test.
-- ============================================================
CREATE TEMP TABLE tmp_ric_r2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM tmp_ric_reso),
         p_resi_riga_id => (SELECT resi_riga_id FROM tmp_ric_reso), p_quantita => 3,
         p_data => DATE '2026-08-01');

SELECT is(
  (SELECT COALESCE(p.differenza::text, 'NULL') || '|' || p.stato || '|' || p.riconsegna_quota_nuova::text
     FROM vendite.vw_partite_merce p WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_ric_r2)),
  'NULL|RICONSEGNA|0',
  '2) senza nota di credito la regola e'' INERTE: la ri-consegna resta un conto vuoto'
);

SELECT is(
  (SELECT p.consegnato FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_ric_p)),
  13::numeric(18,6),
  '3) senza nota di credito la spedizione d''ORIGINE riassorbe i pezzi: 10 + 3 = 13'
);

-- ============================================================
-- CASO B — la NOTA DI CREDITO arriva PRIMA della ri-spedizione, che e'
-- l'ordine reale dei fatti: l'accredito si decide sulla merce tornata, la
-- ri-spedizione viene dopo. (E non e' un dettaglio del test: dopo la
-- ri-spedizione la partita d'origine pareggia da sola e l'accredito non e'
-- piu' dovuto — il conto lo dice, e ha ragione.)
-- ⭐ La nota di credito la crea la MADRE, non un INSERT a mano.
-- ============================================================
CREATE TEMP TABLE tmp_ric_pb AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('riconsegna B',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ric),
         p_quantita => 10, p_prezzo => 20,
         p_articolo_id => (SELECT articolo_id FROM tmp_refs_ric),
         p_fatturazione_trigger => 'CONSEGNATO');

CREATE TEMP TABLE tmp_ric_fatt_b AS
SELECT pg_temp.ric_fattura((SELECT ddt_uid FROM tmp_ric_pb), (SELECT ddt_riga_id FROM tmp_ric_pb),
    10, 20) AS fattura_riga_id;

CREATE TEMP TABLE tmp_ric_reso_b AS
SELECT * FROM dbops.fn_pgtap_crea_reso('riconsegna B', (SELECT ddt_id FROM tmp_ric_pb), 3,
         'RESO_PER_RICONSEGNA');

SELECT vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_ric_reso_b));
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_ric), true, false);

CREATE TEMP TABLE tmp_ric_r2b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM tmp_ric_reso_b),
         p_resi_riga_id => (SELECT resi_riga_id FROM tmp_ric_reso_b), p_quantita => 3,
         p_data => DATE '2026-08-01');

SELECT is(
  (SELECT p.riconsegna_quota_nuova FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_ric_r2b)),
  3::numeric,
  '4) D-NC-4: i pezzi accreditati CAMBIANO CASA — la spedizione nuova prende quota 3'
);

SELECT is(
  (SELECT p.differenza::text || '|' || p.stato FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_ric_r2b)),
  '3.000000|DA_FATTURARE',
  '5) la spedizione nuova diventa una partita vera: 3 da fatturare'
);

SELECT is(
  (SELECT p.consegnato FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_ric_pb)),
  10::numeric(18,6),
  '6) la spedizione d''origine non porta piu'' quei pezzi: torna a 10, non li rifattura'
);

SELECT is(
  (SELECT sum(p.consegnato) FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id IN ((SELECT ddt_riga_id FROM tmp_ric_pb), (SELECT ddt_riga_id FROM tmp_ric_r2b))),
  13::numeric,
  '7) INVARIANTE: la somma dei consegnato non cambia — i pezzi si spostano, non si moltiplicano'
);

-- ⭐ E' il punto per cui la regola esiste: il segmento della spedizione
--    d'origine e' gia' EMESSA e la cintura del push lo blocca (giustamente);
--    quello della spedizione nuova e' vergine, quindi LIBERA, e il giro di
--    fatturazione NORMALE se ne accorge da solo — nessun verbo nuovo.
SELECT is(
  script.fn_get_stato_push_segment(
    script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_ric_r2b)::text, (SELECT ddt_riga_id FROM tmp_ric_r2b))),
  'LIBERA',
  '8) il segmento della spedizione nuova e'' LIBERA: la fatturazione normale la vede'
);

SELECT * FROM finish();
ROLLBACK;
