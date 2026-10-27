-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_lotto_segnalazioni — la finestra dell'ULTIMO JOB
--       (changeSet 20260821-44, cantiere brief-db-liste-drawer-lotto, D-6)
-- ------------------------------------------------------------
-- Indice test (plan 8)
-- 1) Fixture: lotto, fattura e quattro segnalazioni su una linea del tempo
-- 2) ⚠️ Senza nessuna corsa, TUTTO e' corrente (ancora NULL)
-- 3) ...e non c'e' niente fuori dalla finestra
-- 4) Con UNA corsa, sono correnti solo le segnalazioni successive
-- 5) ⭐ Con DUE corse l'ancora e' la SECONDA, non la prima
-- 6) ⛔ ...e le due corse condividono il correlation_id: se l'ancora fosse
--    quello, non distinguerebbe niente
-- 7) `fuori_job_count` conta le righe VIVE che la finestra lascia fuori
-- 8) ⭐ Col filtro acceso spariscono dalla lista ma NON dal conteggio
--
-- Scopo:
--  - «Valgono le segnalazioni dell'ultimo job» (decisione di Tid) non aveva un
--    identificatore su cui appoggiarsi: `tentativo` conta per task, `tx_id` e'
--    una GUC di sessione che sopravvive alla corsa, e il `correlation_id` degli
--    eventi e' il `lock_batch_id` — che DUE CORSE CONDIVIDONO. L'unica cosa che
--    distingue una corsa dalla precedente e' l'`event_time` del suo
--    PIPELINE_STARTED. La 5 e la 6 sono le due facce di quella misura.
--  - La 8 e' la proprieta' che rende onesto il filtro: le segnalazioni per
--    fattura attraversano i job finche' sono vere (il runner azzera solo le C
--    di lotto), quindi una riga viva puo' restare fuori dalla finestra. Se
--    sparisse senza lasciare traccia sarebbe la classe di difetto in cui uno
--    zero sembra un dato: qui viene tolta dalla lista e CONTATA.
--
-- ⚠️ La linea del tempo si scrive a mano: `now()` e' costante dentro una
--    transazione, quindi quattro righe nate qui avrebbero lo stesso istante e
--    la finestra non misurerebbe niente.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- 0) Fixture
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, gia' legato all'azienda di chi agisce):
--   prima si pescava l'ultimo billing account del DB, e da zero non c'era.
--   Tipo documento (dal ponte tipo->registro), valuta e stato restano letture
--   di catalogo; registro ed emittente sono gia' quelli di chi agisce.
CREATE TEMP TABLE tmp_cli_jb AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('lista segnalazioni lotto job');

CREATE TEMP TABLE tmp_refs_jb AS
SELECT script.fn_pgtap_registro_fattura() AS registro_id,
       ba.billing_account_id AS billing_account_id,
       ba.utility_id         AS utility_id,
       (SELECT m.tipo_doc_fiscale_id
          FROM vendite.tipi_doc_fiscale_registri m
          JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
         WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
       script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
       (SELECT id FROM config.stati_doc_fiscale
         WHERE codice_interno = 'DRAFT' AND attivo IS TRUE ORDER BY id LIMIT 1) AS stato_draft_id
  FROM tmp_cli_jb ba;

CREATE TEMP TABLE tmp_lotto_jb AS
SELECT vendite.fn_create_fatturazione_lotto(
  p_competenza_mese             => date_trunc('month', script.fn_data_operativa())::date,
  p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_refs_jb),
  p_utility_id                  => (SELECT utility_id FROM tmp_refs_jb),
  p_billing_account_id          => NULL,
  p_lock_batch_id               => NULL,
  p_meta                        => jsonb_build_object('test_scope', 'pgtap_job'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_jb)
) AS lotto_id;

CREATE TEMP TABLE tmp_fattura_jb AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, stato_doc_fiscale_id,
      totale_doc, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id,
         r.billing_account_id, r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id,
         r.stato_draft_id, 10.00, 10.00,
         jsonb_build_object('test_scope', 'pgtap_job')
    FROM tmp_refs_jb r
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id)
SELECT (SELECT lotto_id FROM tmp_lotto_jb),
       (SELECT id FROM tmp_fattura_jb),
       (SELECT stato_draft_id FROM tmp_refs_jb);

-- La linea del tempo, dalla piu' vecchia alla piu' recente:
--   -60 min  A  (LOTTO)     ← prima di tutto
--   -40 min  B  (FATTURA)   ← dopo la prima corsa
--   -10 min  C  (FATTURA)   ← dopo la seconda
--    -5 min  D  (LOTTO)     ← idem
INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
VALUES
  ((SELECT id FROM tmp_fattura_jb), now() - interval '40 min', 'pgtap B', 'C', FALSE,
   jsonb_build_object('task', 'pgtap')),
  ((SELECT id FROM tmp_fattura_jb), now() - interval '10 min', 'pgtap C', 'C', FALSE,
   jsonb_build_object('task', 'pgtap'));

INSERT INTO vendite.fatturazione_lotti_log (lotto_id, data_ora, messaggio, status, disabilitato, fase, meta)
VALUES
  ((SELECT lotto_id FROM tmp_lotto_jb), now() - interval '60 min', 'pgtap A', 'C', FALSE,
   'Fase A', jsonb_build_object('task', 'pgtap')),
  ((SELECT lotto_id FROM tmp_lotto_jb), now() - interval '5 min', 'pgtap D', 'W', FALSE,
   'Fase D', jsonb_build_object('task', 'pgtap'));

SELECT is(
  (SELECT count(*)::int
     FROM vendite.fn_list_lotto_segnalazioni((SELECT lotto_id FROM tmp_lotto_jb)) s),
  4,
  '1) fixture: quattro segnalazioni vive su una linea del tempo'
);

-- ============================================================
-- 1) Nessuna corsa: l'ancora e' NULL
--    ⚠️ Senza una corsa precedente non c'e' niente da considerare stantio, e
--    il filtro non deve togliere nulla.
-- ============================================================
SELECT is(
  (SELECT count(*) FILTER (WHERE s.job_corrente)::int
     FROM vendite.fn_list_lotto_segnalazioni((SELECT lotto_id FROM tmp_lotto_jb)) s),
  4,
  '2) senza nessuna corsa, tutte le segnalazioni sono correnti'
);

SELECT is(
  (SELECT max(s.fuori_job_count)::int
     FROM vendite.fn_list_lotto_segnalazioni((SELECT lotto_id FROM tmp_lotto_jb)) s),
  0,
  '3) ...e non c''e'' niente fuori dalla finestra'
);

-- ============================================================
-- 2) La prima corsa
--    ⚠️ `event_time` esplicito, per la stessa ragione dei log: dentro una
--    transazione `now()` non avanza.
-- ============================================================
CREATE TEMP TABLE tmp_corr_jb AS SELECT uuidv7() AS correlation_id;

INSERT INTO vendite.event_log (event_time, entity_type, entity_id,
                               event_code, severity, correlation_id, payload)
SELECT now() - interval '50 min', 'LOTTO', (SELECT lotto_id FROM tmp_lotto_jb),
       'PIPELINE_STARTED', 'INFO', (SELECT correlation_id FROM tmp_corr_jb),
       '{}'::jsonb;

SELECT is(
  (SELECT string_agg(s.messaggio, ',' ORDER BY s.messaggio)
     FROM vendite.fn_list_lotto_segnalazioni((SELECT lotto_id FROM tmp_lotto_jb)) s
    WHERE s.job_corrente),
  'pgtap B,pgtap C,pgtap D',
  '4) con una corsa sola, e'' corrente tutto cio'' che viene dopo di essa'
);

-- ============================================================
-- 3) La seconda corsa
--    ⛔ STESSO correlation_id della prima: e' il lock_batch_id, che nasce col
--       lotto. Se l'ancora fosse quello, le due corse sarebbero la stessa cosa.
-- ============================================================
INSERT INTO vendite.event_log (event_time, entity_type, entity_id,
                               event_code, severity, correlation_id, payload)
SELECT now() - interval '20 min', 'LOTTO', (SELECT lotto_id FROM tmp_lotto_jb),
       'PIPELINE_STARTED', 'INFO', (SELECT correlation_id FROM tmp_corr_jb),
       '{}'::jsonb;

SELECT is(
  (SELECT string_agg(s.messaggio, ',' ORDER BY s.messaggio)
     FROM vendite.fn_list_lotto_segnalazioni((SELECT lotto_id FROM tmp_lotto_jb)) s
    WHERE s.job_corrente),
  'pgtap C,pgtap D',
  '5) con due corse l''ancora e'' la SECONDA: B esce dalla finestra'
);

SELECT is(
  (SELECT count(DISTINCT e.correlation_id)::int || '|' || count(*)::int
     FROM vendite.event_log e
    WHERE e.entity_type = 'LOTTO'
      AND e.entity_id = (SELECT lotto_id FROM tmp_lotto_jb)
      AND e.event_code = 'PIPELINE_STARTED'),
  '1|2',
  '6) le due corse condividono il correlation_id: da solo non distinguerebbe'
);

-- ============================================================
-- 4) Ciò che resta fuori si conta
-- ============================================================
SELECT is(
  (SELECT max(s.fuori_job_count)::int
     FROM vendite.fn_list_lotto_segnalazioni((SELECT lotto_id FROM tmp_lotto_jb)) s),
  2,
  '7) fuori_job_count conta le due righe vive fuori dalla finestra'
);

-- ⭐ Col filtro acceso escono dalla LISTA ma restano nel CONTEGGIO: una riga
--    viva che sparisce senza traccia sarebbe uno zero travestito da dato.
SELECT is(
  (SELECT count(*)::int || '|' || max(s.total_count)::int || '|' || max(s.fuori_job_count)::int
     FROM vendite.fn_list_lotto_segnalazioni(
            (SELECT lotto_id FROM tmp_lotto_jb), NULL, NULL, TRUE, TRUE) s),
  '2|2|2',
  '8) col filtro acceso spariscono dalla lista ma non dal conteggio'
);

SELECT * FROM finish();
ROLLBACK;
