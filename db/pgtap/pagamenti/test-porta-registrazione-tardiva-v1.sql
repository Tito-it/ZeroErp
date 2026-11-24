-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: la porta 9, la registrazione tardiva, si apre solo dal verbo, col suo
--   permesso e nel suo perimetro.
-- Riferimento: brief-db-porte-aperte-dalla-sola-guc §11 (giro 9; D-A a, D-S a di
--   Tid, 2026-11-23/25); changeSet 20_code/pagamenti/20261124-07 (la porta: GUC
--   sulla riga E proprietario), -08 (il verbo SECURITY DEFINER col guard di
--   registra_distinta e il perimetro all'ingresso), -09 (il guard di scope del
--   movimento dopo il mirror). Che cosa fa la madre lo prova
--   test-posta-riga-tardiva-v1 (D20-b).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il verbo e' SECURITY DEFINER col search_path fissato; il guard della
--     distinta finale resta INVOKER;
--   - sul movimento il guard di scope gira dopo il mirror che ricava la fattura
--     dalla riga (prima la leggeva vuota);
--   - senza registra_distinta il verbo rifiuta (E_PERMESSO_NEGATO) e non scrive;
--   - l'applicazione non apre la porta: con la GUC sull'id giusto un UPDATE
--     diretto SOSPESA -> ABBINATA sotto la distinta chiusa resta rifiutato;
--   - DUE EMITTENTI: la riga di una distinta dell'altra azienda «non c'e'»
--     (E_RIGA_CONTABILE_NON_TROVATA, la stessa risposta di una riga inesistente);
--     una riga propria registrata su una fattura dell'altra si ferma
--     (E_SCOPE_EMITTENTE); in tutti e due i casi niente scritto;
--   - col permesso il verbo registra, e la GUC dopo e' vuota.
--
-- ⛔ IL MONDO SI COSTRUISCE: due aziende coi loro operatori
--   (dbops.fn_pgtap_crea_emittente_operatore), senza azioni. Le cose di B si
--   costruiscono nel contesto dell'operatore di B, poi il contesto passa ad A,
--   che e' chi agisce. registra_distinta la da' dbops.fn_pgtap_concedi_azione,
--   fra un caso e l'altro.
-- ⚠️ Gira come l'applicazione (runner di default). Da proprietario chi scrive e'
--   il proprietario, e la porta col valore giusto gli si apre: 6 e' rosso per
--   costruzione.
-- ⚠️ Il movimento su una fattura fuori perimetro scritto da una DEFINER non si
--   costruisce da qui: l'app non crea funzioni del proprietario, e il verbo lo
--   ferma prima (8). Il guard del movimento lo presidia l'ordine (2).
--
-- Elenco test (plan 11):
--    1) il verbo: SECURITY DEFINER, search_path fissato; il guard: INVOKER
--    2) sul movimento il guard di scope gira dopo il mirror, e il nome storico non c'e' piu'
--    3) la distinta di A e' registrata: due righe SOSPESE sotto una CHIUSA
--    4) senza registra_distinta il verbo rifiuta: E_PERMESSO_NEGATO
--    5) … e non scrive: la riga e' ancora SOSPESA, nessun movimento
--    6) ⭐ l'app scrive la GUC con l'id della riga e la abbina diretta: rifiutata,
--       la porta chiede anche il proprietario
--    7) ⭐ la riga di una distinta di B: E_RIGA_CONTABILE_NON_TROVATA
--    8) ⭐ una riga di A registrata sulla fattura di B: E_SCOPE_EMITTENTE
--    9) … e in tutti e due i casi niente scritto
--   10) col permesso il verbo registra: esito POSTATA
--   11) dopo il verbo la GUC e' vuota
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- Due aziende, ciascuna col suo operatore.
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
UNION ALL
SELECT 'B' AS lato, m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- ⚠️ 2. CONTESTO APPLICATIVO: prima B, per costruirne le cose.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'B')); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_cat AS
SELECT (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                               AS valuta_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1)   AS centro_banca_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1)                    AS st_abbinata,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SOSPESA'  ORDER BY s.id LIMIT 1)                    AS st_sospesa,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA' ORDER BY s.id LIMIT 1)                    AS d_validata;

CREATE TEMP TABLE tmp_cli (lato text, billing_account_id bigint, utility_id integer);
CREATE TEMP TABLE tmp_fatture (lato text, id bigint);
CREATE TEMP TABLE tmp_distinte (lato text, contabile_id bigint);
CREATE TEMP TABLE tmp_righe (et text, id bigint);

-- Il cliente, la fattura e la distinta dell'azienda di chi e' in contesto.
-- p_righe: le righe della distinta, (etichetta, stato ABBINATA o SOSPESA).
CREATE OR REPLACE FUNCTION pg_temp.mondo(p_lato text, p_righe text[])
RETURNS void LANGUAGE plpgsql AS $f$
DECLARE
  v_sr  bigint := (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = p_lato);
  v_ef  bigint := (SELECT emittente_fiscale_id FROM _mondi WHERE lato = p_lato);
  v_ba  bigint;
  v_ut  integer;
  v_fa  bigint;
  v_co  bigint;
  v_et  text;
BEGIN
  SELECT c.billing_account_id, c.utility_id INTO v_ba, v_ut
    FROM dbops.fn_pgtap_crea_cliente_ba('porta tardiva ' || p_lato, NULL, v_sr) c;
  INSERT INTO tmp_cli VALUES (p_lato, v_ba, v_ut);

  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
  SELECT script.fn_pgtap_registro_fattura(v_sr), script.fn_data_operativa(), v_sr, v_ba,
         k.tipo_doc_fiscale_id, k.valuta_id, v_ut, 500.00,
         jsonb_build_object('test_scope', 'pgtap_porta_tardiva', 'lato', p_lato)
    FROM tmp_cat k
  RETURNING id INTO v_fa;
  INSERT INTO tmp_fatture VALUES (p_lato, v_fa);

  v_co := pagamenti.fn_get_or_create_vendite_contabile(
      p_centro_riscossione_id => (SELECT centro_banca_id FROM tmp_cat),
      p_data_contabile        => script.fn_data_operativa(),
      p_data_registrazione    => script.fn_data_operativa(),
      p_codice_stato_interno  => 'BOZZA',
      p_meta                  => jsonb_build_object('test_scope', 'pgtap_porta_tardiva', 'lato', p_lato),
      p_origine               => 'MANUALE',
      p_emittente_fiscale_id  => v_ef);
  INSERT INTO tmp_distinte VALUES (p_lato, v_co);

  FOREACH v_et IN ARRAY p_righe LOOP
    INSERT INTO pagamenti.vendite_contabili_righe
        (contabile_id, riferimento_ente, data_pagamento, importo,
         fattura_id, billing_account_id, stato_id, motivo_sospeso, meta)
    SELECT v_co, 'PGTAP_PORTA_TARD_' || v_et, script.fn_data_operativa(), 50.00,
           CASE WHEN v_et LIKE '%ABB' THEN v_fa END,
           CASE WHEN v_et LIKE '%ABB' THEN v_ba END,
           CASE WHEN v_et LIKE '%ABB' THEN k.st_abbinata ELSE k.st_sospesa END,
           CASE WHEN v_et LIKE '%ABB' THEN NULL ELSE 'da capire di chi e''' END,
           jsonb_build_object('test_scope', 'pgtap_porta_tardiva', 'et', v_et)
      FROM tmp_cat k;
    INSERT INTO tmp_righe
    SELECT v_et, cr.id FROM pagamenti.vendite_contabili_righe cr
     WHERE cr.contabile_id = v_co AND cr.meta ->> 'et' = v_et;
  END LOOP;
END
$f$;

-- B: una distinta in bozza con una riga SOSPESA. Basta: il perimetro parla prima
-- dello stato.
SELECT pg_temp.mondo('B', ARRAY['B_SOSP']);

-- A: chi agisce. Una distinta con una riga ABBINATA e tre SOSPESE, poi registrata.
-- A_S1 per il verbo, A_S2 per la fattura di B, A_S3 per la porta senza il verbo.
DO $ctxa$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'A')); END $ctxa$;

SELECT pg_temp.mondo('A', ARRAY['A_ABB', 'A_S1', 'A_S2', 'A_S3']);

UPDATE pagamenti.vendite_contabili c
   SET stato_id = (SELECT d_validata FROM tmp_cat)
 WHERE c.id = (SELECT contabile_id FROM tmp_distinte WHERE lato = 'A');

CREATE TEMP TABLE tmp_posting AS
SELECT * FROM pagamenti.fn_posta_contabile((SELECT contabile_id FROM tmp_distinte WHERE lato = 'A'));

-- Il verbo su una riga, verso una fattura, come istruzione da provare.
CREATE OR REPLACE FUNCTION pg_temp.tardiva(p_et text, p_lato_fattura text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format('SELECT * FROM pagamenti.fn_posta_riga_tardiva(%s, %s, %s)',
                (SELECT id FROM tmp_righe WHERE et = p_et),
                (SELECT id FROM tmp_fatture WHERE lato = p_lato_fattura),
                (SELECT billing_account_id FROM tmp_cli WHERE lato = p_lato_fattura));
$f$;

-- Lo stato di una riga, e quanti movimenti ha.
CREATE OR REPLACE FUNCTION pg_temp.riga(p_et text)
RETURNS text LANGUAGE sql AS $f$
  SELECT st.codice_interno || ' / '
         || (SELECT count(*) FROM pagamenti.vendite_movimenti m WHERE m.contabile_riga_id = cr.id)
    FROM pagamenti.vendite_contabili_righe cr
    JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
   WHERE cr.id = (SELECT id FROM tmp_righe WHERE et = p_et);
$f$;

-- ============================================================
-- 1-3 La forma, e la distinta registrata
-- ============================================================
SELECT is(
  (SELECT p.prosecdef AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search\_path=%')
     FROM pg_catalog.pg_proc p
    WHERE p.oid = 'pagamenti.fn_posta_riga_tardiva'::regproc)
  AND NOT (SELECT p.prosecdef FROM pg_catalog.pg_proc p
            WHERE p.oid = 'pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale'::regproc),
  true,
  '1) il verbo: SECURITY DEFINER, search_path fissato; il guard della distinta finale: INVOKER');

-- Per funzione, non per nome: il guard di scope e il mirror del movimento.
SELECT is(
  (SELECT bool_and(g.tgname COLLATE "C" > s.tgname COLLATE "C")
          AND count(*) = 1
          AND bool_and(g.tgname NOT LIKE '%\_a10\_%')
     FROM pg_catalog.pg_trigger g
     JOIN pg_catalog.pg_trigger s
       ON s.tgrelid = g.tgrelid
      AND s.tgfoid = 'pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga'::regproc
    WHERE g.tgrelid = 'pagamenti.vendite_movimenti'::regclass
      AND g.tgfoid = 'script.trgfn_guard_emittente_scope'::regproc
      AND NOT g.tgisinternal),
  true,
  '2) sul movimento il guard di scope gira dopo il mirror che ricava la fattura, e c''e'' un montaggio solo');

SELECT is(
  (SELECT s.codice_interno FROM pagamenti.vendite_contabili c
     JOIN pagamenti.vendite_contabili_stati s ON s.id = c.stato_id
    WHERE c.id = (SELECT contabile_id FROM tmp_distinte WHERE lato = 'A'))
  || ' / ' || pg_temp.riga('A_S1') || ' / ' || pg_temp.riga('A_S2'),
  'CHIUSA / SOSPESA / 0 / SOSPESA / 0',
  '3) la distinta di A e'' registrata: due righe SOSPESE sotto una CHIUSA');

-- ============================================================
-- 4-6 Senza il permesso, e senza il verbo
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.tardiva('A_S1', 'A')), 'E_PERMESSO_NEGATO',
          '4) senza registra_distinta il verbo rifiuta');

SELECT is(pg_temp.riga('A_S1'), 'SOSPESA / 0',
          '5) … e non scrive: la riga e'' ancora SOSPESA, nessun movimento');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            $q$WITH porta AS (
                 SELECT set_config('app.registrazione_tardiva_riga_id', %L, true))
               UPDATE pagamenti.vendite_contabili_righe
                  SET stato_id = %s, fattura_id = %s, billing_account_id = %s
                WHERE id = %s AND EXISTS (SELECT 1 FROM porta)$q$,
            (SELECT id FROM tmp_righe WHERE et = 'A_S3')::text,
            (SELECT st_abbinata FROM tmp_cat),
            (SELECT id FROM tmp_fatture WHERE lato = 'A'),
            (SELECT billing_account_id FROM tmp_cli WHERE lato = 'A'),
            (SELECT id FROM tmp_righe WHERE et = 'A_S3'))),
          'E_RIGA_CONTABILE_DISTINTA_FINALE',
          '6) l''app scrive la GUC con l''id della riga e la abbina diretta: rifiutata, la porta chiede anche il proprietario');

-- La GUC del caso 6 si svuota qui: da proprietario la scrittura riesce, e la GUC
-- resterebbe accesa sui casi che seguono.
DO $gucvuota$ BEGIN PERFORM set_config('app.registrazione_tardiva_riga_id', '', true); END $gucvuota$;

DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondi WHERE lato = 'A'), 'registra_distinta');
END $az$;

-- ============================================================
-- 7-9 Due emittenti
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.tardiva('B_SOSP', 'A')), 'E_RIGA_CONTABILE_NON_TROVATA',
          '7) la riga di una distinta di B: per A non c''e''');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.tardiva('A_S2', 'B')), 'E_SCOPE_EMITTENTE',
          '8) una riga di A registrata sulla fattura di B: si ferma sul perimetro');

-- ⚠️ La riga di B si legge nel contesto dell'operatore di B: come A, sotto la row
--   security, non si vede (ed e' proprio il caso 7).
CREATE TEMP TABLE _riga_a ON COMMIT DROP AS SELECT pg_temp.riga('A_S2') AS r;

DO $ctxb$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'B')); END $ctxb$;

SELECT is((SELECT r FROM _riga_a) || ' / ' || pg_temp.riga('B_SOSP'), 'SOSPESA / 0 / SOSPESA / 0',
          '9) … e in tutti e due i casi niente scritto');

DO $ctxa2$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'A')); END $ctxa2$;

-- ============================================================
-- 10-11 Col permesso, dal verbo
-- ============================================================
-- ⚠️ La scrittura in un'istruzione e la rilettura nelle successive.
CREATE TEMP TABLE _esito ON COMMIT DROP AS
SELECT coalesce(dbops.fn_pgtap_codice_errore(pg_temp.tardiva('A_S1', 'A')), 'ok') AS esito;

SELECT is((SELECT esito FROM _esito) || ' / ' || pg_temp.riga('A_S1'), 'ok / POSTATA / 1',
          '10) col permesso il verbo registra: la riga e'' POSTATA, col suo movimento');

SELECT is(coalesce(current_setting('app.registrazione_tardiva_riga_id', true), ''), '',
          '11) dopo il verbo la GUC e'' vuota');

SELECT * FROM finish();
ROLLBACK;
