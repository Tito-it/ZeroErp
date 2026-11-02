-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto del test NON sta sul percorso applicativo —
--   `fn_accoda_chiusura_scadenze` la chiama un job pgAgent, che gira come
--   superuser, e nessun endpoint la espone (stessa ragione del fratello
--   test-fn-accoda-chiusura-scadenze.sql).
--
-- Test: dbops.fn_accoda_chiusura_scadenze — UNA VOLTA PER GIORNO AZIENDALE
-- Brief: brief-be-db-fe-un-solo-fuso-aziendale §5.1 D-9, decisione T-4
--        (20261009-46, 20261009-61)
--
-- Elenco test (plan 5):
--  1) la prima sveglia del giorno accoda un lavoro per azienda del roster
--  2) la chiave porta il GIORNO AZIENDALE (fn_data_operativa)
--  3) ⭐ con i lavori FATTI, la sveglia dell'ora dopo non accoda niente...
--  4) ...e li conta come saltati
--  5) ⭐ un lavoro andato in ERRORE non chiude il giorno: la sveglia dopo
--     riaccoda SOLO quell'azienda
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ PERCHE' SERVE UN CONTROLLO IN PIU' DELLA CHIAVE IDEMPOTENTE.
--   Da 20261009-61 il job pgAgent suona OGNI ORA, perche' il giorno lo decide
--   il fuso dell'azienda e non l'orario del server. La chiave idempotente di
--   fn_accoda_lavoro protegge solo i lavori VIVI (PENDING/IN_CORSO): un lavoro
--   gia' FATTO alle 00:05 non fermerebbe la sveglia delle 01:05, e la
--   chiusura si riaccoderebbe ventiquattro volte al giorno. Il test 3 e' quel
--   caso, costruito: i lavori si portano a FATTO a mano, senza aspettare il
--   drenatore.
-- ⚠️ Il test 1 del fratello prova gia' che due sveglie a lavori VIVI non
--   raddoppiano: qui si prova il caso che quella chiave non vede.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- Il roster si COSTRUISCE (due aziende: il test 5 ne fa fallire una e
-- pretende che l'altra resti chiusa), come nel fratello.
DO $roster$
BEGIN
    PERFORM dbops.fn_pgtap_crea_roster_processo('chiusura_scadenze_daily');
    PERFORM dbops.fn_pgtap_crea_roster_processo('chiusura_scadenze_daily');
END
$roster$;

-- ⭐ La condizione si COSTRUISCE: «nessun lavoro di chiusura per oggi».
--   Su un database vivo il job orario (20261009-61) ha gia' chiuso la
--   giornata delle aziende vere, e fn_accoda_chiusura_scadenze (20261009-46)
--   le salta: il test vedrebbe meno accodati del roster senza che niente sia
--   rotto (dbdev, 2026-10-09: 2 su 4). Si liberano le chiavi di oggi, come fa
--   gia' il test 6 del fratello; tutto si annulla col ROLLBACK.
UPDATE dbops.coda_lavori
   SET idempotency_key = idempotency_key || ':pgtap-prima'
 WHERE job_type = 'CHIUSURA_SCADENZE'
   AND idempotency_key LIKE 'CHIUSURA_SCADENZE:%:' || script.fn_data_operativa()::text;

CREATE TEMP TABLE tmp_cs_roster AS
SELECT count(*)::int AS n
  FROM dbops.vw_processi_roster
 WHERE processo_codice = 'chiusura_scadenze_daily';

-- ============================================================
-- 1-2) La prima sveglia del giorno
-- ============================================================
CREATE TEMP TABLE tmp_cs_giro1 AS SELECT dbops.fn_accoda_chiusura_scadenze() AS out;

SELECT is(
  (SELECT (out ->> '_accodati')::int FROM tmp_cs_giro1),
  (SELECT n FROM tmp_cs_roster),
  '1) la prima sveglia del giorno accoda un lavoro per azienda del roster');

SELECT is(
  (SELECT count(*)::int FROM dbops.coda_lavori
    WHERE job_type = 'CHIUSURA_SCADENZE'
      AND stato = 'PENDING'
      AND idempotency_key LIKE '%:' || script.fn_data_operativa()::text),
  (SELECT n FROM tmp_cs_roster),
  '2) la chiave dei lavori porta il giorno AZIENDALE (fn_data_operativa)');

-- ============================================================
-- 3-4) Lavori FATTI: la sveglia dopo esce
-- ============================================================
UPDATE dbops.coda_lavori
   SET stato = 'FATTO'
 WHERE job_type = 'CHIUSURA_SCADENZE'
   AND idempotency_key LIKE '%:' || script.fn_data_operativa()::text
   AND stato = 'PENDING';

CREATE TEMP TABLE tmp_cs_giro2 AS SELECT dbops.fn_accoda_chiusura_scadenze() AS out;

SELECT is(
  (SELECT (out ->> '_accodati')::int FROM tmp_cs_giro2),
  0,
  '3) con i lavori del giorno FATTI, la sveglia dell''ora dopo non accoda niente');

SELECT is(
  (SELECT (out ->> '_saltati')::int FROM tmp_cs_giro2),
  (SELECT n FROM tmp_cs_roster),
  '4) ...e conta le aziende come saltate');

-- ============================================================
-- 5) ERRORE non chiude il giorno
-- ============================================================
UPDATE dbops.coda_lavori
   SET stato = 'ERRORE'
 WHERE id = (SELECT min(id) FROM dbops.coda_lavori
              WHERE job_type = 'CHIUSURA_SCADENZE'
                AND idempotency_key LIKE '%:' || script.fn_data_operativa()::text
                AND stato = 'FATTO');

CREATE TEMP TABLE tmp_cs_giro3 AS SELECT dbops.fn_accoda_chiusura_scadenze() AS out;

SELECT is(
  (SELECT (out ->> '_accodati')::int || '/' || (out ->> '_saltati')::int FROM tmp_cs_giro3),
  '1/' || ((SELECT n FROM tmp_cs_roster) - 1)::text,
  '5) un lavoro in ERRORE non chiude il giorno: si riaccoda solo quell''azienda');

SELECT * FROM finish();
ROLLBACK;
