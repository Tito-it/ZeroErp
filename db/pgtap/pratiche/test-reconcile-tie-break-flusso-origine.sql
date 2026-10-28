-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su pratiche.template_flussi_avanzamento_proiezione, che a runtime
--   scrive solo pratiche.fn_copia_definizione — e quella gira dentro
--   fn_fork_definizione / fn_nuova_versione_definizione, entrambe SECURITY DEFINER.
--   Il ruolo applicativo ha solo SELECT ed e' corretto cosi': il soggetto del test
--   sta fuori dal percorso applicativo (brief §29.2).
-- pgTAP test per Zero ERP
-- Test: GUIDA (D4) — fn_reconcile_sorgente, tie-break flusso_id vs ancora
--       d'ORIGINE (brief-db-reconcile-tie-break-flusso-origine.md §5-6).
--
--   Difetto: il tie-break `f.id = flusso_id` escludeva il milestone in ATTESA
--   quando il link puntava al flusso d'ORIGINE (che non attende il documento).
--   Fix: il tie-break si applica SOLO se il flusso linkato attende esso stesso
--   il tipo (v_link_usabile). Questo file esercita i casi che il fix cambia.
--
--   Fixture: tipo_prestazione con 3 step —
--     GEN     = attende NULL (origine, es. PREVENTIVAZIONE), no binding;
--     WAIT1   = attende PREVENTIVO, binding NULL (qualsiasi verdetto);
--     WAIT2   = attende PREVENTIVO, binding NULL.
--   Preventivi portati nello stato bersaglio PRIMA di agganciarli a una
--   pratica (il trigger reconcile e' AFTER UPDATE: scatta a ogni passaggio,
--   ma senza aggancio non ha niente da riconciliare) + chiamata ESPLICITA a
--   fn_reconcile_sorgente. Tutto in transazione con ROLLBACK.
--
-- Indice test (0..N):
--   0)  fn_reconcile_sorgente presente
--   C1) Origine != attesa (bug PRA-0000802): link->GEN, 1 milestone WAIT ->
--       1a return 1 · 1b WAIT COMPLETATO/POSITIVO · 1c GEN invariato ·
--       1d nessun E_RECONCILE_AMBIGUO (criterio 3: no falso ambiguo)
--   C4) Due milestone in attesa + link d'origine (non usabile) ->
--       4a return 0 · 4b riga E_RECONCILE_AMBIGUO · 4c entrambi DA_ESEGUIRE
--   C5) Link USABILE che disambigua fra piu' candidati in attesa ->
--       5a return 1 · 5b il milestone indicato COMPLETATO · 5c l'altro DA_ESEGUIRE
--   C2) Origine = attesa (regressione): link->WAIT stesso -> 2a return 1 ·
--       2b COMPLETATO
--   C6) Nessun verdetto (preventivo EMESSO) + link d'origine ->
--       6a return 0 · 6b WAIT invariato · 6c nessun errore
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i preventivi nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima nascevano
--   gia' ACCETTATO/EMESSO).
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): i preventivi
--   degli scenari si portano allo stato con una riga (merce, 1 x 10) da
--   dbops.fn_pgtap_crea_preventivo_con_righe (p_preventivo_id): l'emissione
--   senza righe e' rifiutata. Nessuna attesa conta righe o importi.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(16);

-- Stati flusso (idempotente).
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true),
       ('IN_CORSO',    'IN_CORSO',    'In corso',    true),
       ('COMPLETATO',  'COMPLETATO',  'Completato',  true)
ON CONFLICT (codice_interno) DO NOTHING;

-- ============================================================
-- 0) La funzione esiste
-- ============================================================
SELECT has_function('pratiche', 'fn_reconcile_sorgente', ARRAY['bigint','text'],
  '0. pratiche.fn_reconcile_sorgente(bigint, text) presente');

-- ============================================================
-- Riferimenti minimi (pattern test-guida-avanza-esito-proiettato)
-- ============================================================
-- ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-2): il preventivo ha
--   sempre il suo billing account, quello della sua coppia (istanza, utility),
--   e il guard dell'emittente pretende che il BA sia dell'emittente del
--   documento. Fino a quel giorno la coppia si PESCAVA dal primo BA del
--   database e il preventivo nasceva senza BA. Ora il cliente si COSTRUISCE,
--   col BA legato esplicitamente all'emittente usato dal file.
--   ⛔ Si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_tb_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'pgtap tb preventivo col BA', NULL,
    (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1));

CREATE TEMP TABLE tmp_tb_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_tb_cli) AS billing_account_id,
  (SELECT istanza_utility_id FROM tmp_tb_cli) AS istanza_utility_id,
  (SELECT utility_id FROM tmp_tb_cli) AS utility_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA') AS st_aperta,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS fl_da_eseguire,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1) AS src_preventivo,
  (SELECT sd.id FROM config.stati_doc_preventivi sd WHERE sd.codice_interno = 'EMESSO' LIMIT 1) AS stato_emesso_id,
  (SELECT sd.id FROM config.stati_doc_preventivi sd WHERE sd.codice_interno = 'ACCETTATO' LIMIT 1) AS stato_accettato_id;

-- ============================================================
-- Tipo prestazione + 3 step (GEN / WAIT1 / WAIT2)
-- ============================================================
CREATE TEMP TABLE tmp_tb_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_TIEBREAK', 'TEST_TIEBREAK', 'Tipo test tie-break origine', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
) SELECT id AS tp_id FROM ins;

-- GEN: step d'origine (attende NULL) — es. PREVENTIVAZIONE.
CREATE TEMP TABLE tmp_tb_gen AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi
    (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo,
     ripetibilita, modalita_esito)
  VALUES ((SELECT tp_id FROM tmp_tb_tp), 'TB_GEN', 'Step origine (non attende)',
          10, false, true, 'SEMPRE', 'MANUALE')
  RETURNING id
) SELECT id AS tf_id FROM ins;

-- WAIT1 / WAIT2: step che attendono il PREVENTIVO (milestone in attesa).
CREATE TEMP TABLE tmp_tb_w1 AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi
    (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo,
     ripetibilita, modalita_esito, attende_sorgente_tipo_id)
  VALUES ((SELECT tp_id FROM tmp_tb_tp), 'TB_WAIT1', 'Milestone attende preventivo #1',
          20, false, true, 'SEMPRE', 'MANUALE', (SELECT src_preventivo FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS tf_id FROM ins;

CREATE TEMP TABLE tmp_tb_w2 AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi
    (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo,
     ripetibilita, modalita_esito, attende_sorgente_tipo_id)
  VALUES ((SELECT tp_id FROM tmp_tb_tp), 'TB_WAIT2', 'Milestone attende preventivo #2',
          30, false, true, 'SEMPRE', 'MANUALE', (SELECT src_preventivo FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS tf_id FROM ins;

-- Binding G2 NULL (qualsiasi verdetto) su entrambi i WAIT.
INSERT INTO pratiche.template_flussi_avanzamento_proiezione (template_flusso_id, esito_richiesto)
VALUES ((SELECT tf_id FROM tmp_tb_w1), NULL),
       ((SELECT tf_id FROM tmp_tb_w2), NULL);

-- Helper: crea una pratica del tipo di test e ritorna l'id.
-- (inline via INSERT ripetuti per chiarezza dei singoli scenari)

-- ============================================================
-- Preventivi (uno per scenario), portati nello stato bersaglio.
-- ⚠️ rev 2026-10-24 (brief-modello-documento-vendita N-1): nascono in bozza
--   (lo stato non si scrive: lo mette il trigger della nascita) e vanno allo
--   stato bersaglio con dbops.fn_pgtap_porta_a_stato, per la matrice e sotto
--   i guard veri, PRIMA di ogni aggancio a una pratica.
-- ⚠️ rev 2026-10-25 (§8, giro 6): ognuno con una riga (merce, 1 x 10) scritta
--   in bozza da dbops.fn_pgtap_crea_preventivo_con_righe, che poi porta lo
--   stato: senza righe l'emissione e' rifiutata (E_PREV_NESSUNA_RIGA_ATTIVA).
-- ============================================================
CREATE TEMP TABLE tmp_tb_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi
    (numero, rev, billing_account_id, istanza_utility_id, utility_id, validita_dal, validita_al, valuta_id,
     data, fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT
    'PGTAP-TB-' || x.tag || '-' || substr(md5(clock_timestamp()::text || x.tag), 1, 8),
    0, r.billing_account_id, r.istanza_utility_id, r.utility_id, DATE '2026-07-01', DATE '2026-07-31', r.valuta_id,
    DATE '2026-07-01', false, false,
    jsonb_build_object('test_scope','pgtap_tiebreak','tag',x.tag), r.emittente_id
  FROM tmp_tb_refs r
  CROSS JOIN (
    SELECT 'C1' AS tag
    UNION ALL SELECT 'C4'
    UNION ALL SELECT 'C5'
    UNION ALL SELECT 'C2'
    UNION ALL SELECT 'C6'
  ) x
  RETURNING id, (uid)::text AS uid, meta ->> 'tag' AS tag
)
SELECT id, uid, tag FROM ins;

-- C1/C4/C5/C2 ad ACCETTATO (passando da EMESSO), C6 a EMESSO.
DO $porta$
DECLARE
  r record;
BEGIN
  FOR r IN SELECT p.id, p.tag FROM tmp_tb_prev p ORDER BY p.id LOOP
    PERFORM dbops.fn_pgtap_crea_preventivo_con_righe('tie-break ' || r.tag,
              CASE r.tag WHEN 'C6' THEN 'EMESSO' ELSE 'ACCETTATO' END,
              p_preventivo_id => r.id);
  END LOOP;
END
$porta$;

-- ============================================================
-- Scenario C1 — origine != attesa (bug): link->GEN, 1 milestone WAIT.
-- ============================================================
CREATE TEMP TABLE tmp_tb_c1_prat AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_tb_refs), (SELECT tp_id FROM tmp_tb_tp),
          (SELECT soggetto_id FROM tmp_tb_refs), (SELECT st_aperta FROM tmp_tb_refs),
          (SELECT priorita_id FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

CREATE TEMP TABLE tmp_tb_c1_gen AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_tb_c1_prat), (SELECT tf_id FROM tmp_tb_gen),
          (SELECT fl_da_eseguire FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

CREATE TEMP TABLE tmp_tb_c1_wait AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_tb_c1_prat), (SELECT tf_id FROM tmp_tb_w1),
          (SELECT fl_da_eseguire FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

-- Link ROOT ancorato al flusso d'ORIGINE (GEN).
INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
VALUES ((SELECT pratica_id FROM tmp_tb_c1_prat), (SELECT src_preventivo FROM tmp_tb_refs),
        (SELECT uid FROM tmp_tb_prev WHERE tag = 'C1'), 'ROOT', (SELECT flusso_id FROM tmp_tb_c1_gen));

SELECT is(
  pratiche.fn_reconcile_sorgente(
    (SELECT src_preventivo FROM tmp_tb_refs),
    (SELECT uid FROM tmp_tb_prev WHERE tag = 'C1')),
  1,
  '1a. Origine != attesa: reconcile avanza 1 milestone (il WAIT in attesa)');

SELECT results_eq(
  $$SELECT s.codice_interno, f.esito
      FROM pratiche.flussi f
      JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
     WHERE f.id = (SELECT flusso_id FROM tmp_tb_c1_wait)$$,
  $$VALUES ('COMPLETATO'::varchar, 'POSITIVO'::varchar)$$,
  '1b. Il milestone in attesa (WAIT) passa a COMPLETATO/POSITIVO');

SELECT is(
  (SELECT s.codice_interno FROM pratiche.flussi f
     JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
    WHERE f.id = (SELECT flusso_id FROM tmp_tb_c1_gen)),
  'DA_ESEGUIRE'::varchar,
  '1c. Il flusso d''origine (GEN) resta invariato (non e'' candidato)');

SELECT is(
  (SELECT count(*)::integer FROM pratiche.reconcile_errori re
    WHERE re.sorgente_uid = (SELECT uid FROM tmp_tb_prev WHERE tag = 'C1')),
  0,
  '1d. Nessun E_RECONCILE_AMBIGUO con un solo milestone in attesa (criterio 3)');

-- ============================================================
-- Scenario C4 — due milestone in attesa + link d'origine -> ambiguo.
-- ============================================================
CREATE TEMP TABLE tmp_tb_c4_prat AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_tb_refs), (SELECT tp_id FROM tmp_tb_tp),
          (SELECT soggetto_id FROM tmp_tb_refs), (SELECT st_aperta FROM tmp_tb_refs),
          (SELECT priorita_id FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

CREATE TEMP TABLE tmp_tb_c4_gen AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_tb_c4_prat), (SELECT tf_id FROM tmp_tb_gen),
          (SELECT fl_da_eseguire FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

CREATE TEMP TABLE tmp_tb_c4_wa AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_tb_c4_prat), (SELECT tf_id FROM tmp_tb_w1),
          (SELECT fl_da_eseguire FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

CREATE TEMP TABLE tmp_tb_c4_wb AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_tb_c4_prat), (SELECT tf_id FROM tmp_tb_w2),
          (SELECT fl_da_eseguire FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
VALUES ((SELECT pratica_id FROM tmp_tb_c4_prat), (SELECT src_preventivo FROM tmp_tb_refs),
        (SELECT uid FROM tmp_tb_prev WHERE tag = 'C4'), 'ROOT', (SELECT flusso_id FROM tmp_tb_c4_gen));

SELECT is(
  pratiche.fn_reconcile_sorgente(
    (SELECT src_preventivo FROM tmp_tb_refs),
    (SELECT uid FROM tmp_tb_prev WHERE tag = 'C4')),
  0,
  '4a. Due milestone in attesa + link d''origine (non usabile) -> 0 avanzamenti');

SELECT ok(
  EXISTS (SELECT 1 FROM pratiche.reconcile_errori re
           WHERE re.sorgente_uid = (SELECT uid FROM tmp_tb_prev WHERE tag = 'C4')
             AND re.errcode = 'E_RECONCILE_AMBIGUO'),
  '4b. La guardia d''ambiguita'' scatta: riga E_RECONCILE_AMBIGUO');

SELECT is(
  (SELECT count(*)::integer FROM pratiche.flussi f
     JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
    WHERE f.id IN ((SELECT flusso_id FROM tmp_tb_c4_wa), (SELECT flusso_id FROM tmp_tb_c4_wb))
      AND s.codice_interno = 'DA_ESEGUIRE'),
  2,
  '4c. Nessun avanzamento "a indovinare": entrambi i WAIT restano DA_ESEGUIRE');

-- ============================================================
-- Scenario C5 — link USABILE disambigua fra piu' candidati in attesa.
-- ============================================================
CREATE TEMP TABLE tmp_tb_c5_prat AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_tb_refs), (SELECT tp_id FROM tmp_tb_tp),
          (SELECT soggetto_id FROM tmp_tb_refs), (SELECT st_aperta FROM tmp_tb_refs),
          (SELECT priorita_id FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

CREATE TEMP TABLE tmp_tb_c5_wa AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_tb_c5_prat), (SELECT tf_id FROM tmp_tb_w1),
          (SELECT fl_da_eseguire FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

CREATE TEMP TABLE tmp_tb_c5_wb AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_tb_c5_prat), (SELECT tf_id FROM tmp_tb_w2),
          (SELECT fl_da_eseguire FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

-- Link che punta a WAIT-A (esso stesso attende il tipo -> USABILE come tie-break).
INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
VALUES ((SELECT pratica_id FROM tmp_tb_c5_prat), (SELECT src_preventivo FROM tmp_tb_refs),
        (SELECT uid FROM tmp_tb_prev WHERE tag = 'C5'), 'COLLEGATO', (SELECT flusso_id FROM tmp_tb_c5_wa));

SELECT is(
  pratiche.fn_reconcile_sorgente(
    (SELECT src_preventivo FROM tmp_tb_refs),
    (SELECT uid FROM tmp_tb_prev WHERE tag = 'C5')),
  1,
  '5a. Link usabile fra piu'' candidati: avanza solo 1 (quello indicato, D-B5)');

SELECT is(
  (SELECT s.codice_interno FROM pratiche.flussi f
     JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
    WHERE f.id = (SELECT flusso_id FROM tmp_tb_c5_wa)),
  'COMPLETATO'::varchar,
  '5b. Il milestone indicato dal link e'' COMPLETATO');

SELECT is(
  (SELECT s.codice_interno FROM pratiche.flussi f
     JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
    WHERE f.id = (SELECT flusso_id FROM tmp_tb_c5_wb)),
  'DA_ESEGUIRE'::varchar,
  '5c. L''altro candidato in attesa NON viene toccato');

-- ============================================================
-- Scenario C2 — origine = attesa (regressione: link->WAIT stesso).
-- ============================================================
CREATE TEMP TABLE tmp_tb_c2_prat AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_tb_refs), (SELECT tp_id FROM tmp_tb_tp),
          (SELECT soggetto_id FROM tmp_tb_refs), (SELECT st_aperta FROM tmp_tb_refs),
          (SELECT priorita_id FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

CREATE TEMP TABLE tmp_tb_c2_wait AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_tb_c2_prat), (SELECT tf_id FROM tmp_tb_w1),
          (SELECT fl_da_eseguire FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
VALUES ((SELECT pratica_id FROM tmp_tb_c2_prat), (SELECT src_preventivo FROM tmp_tb_refs),
        (SELECT uid FROM tmp_tb_prev WHERE tag = 'C2'), 'ROOT', (SELECT flusso_id FROM tmp_tb_c2_wait));

SELECT is(
  pratiche.fn_reconcile_sorgente(
    (SELECT src_preventivo FROM tmp_tb_refs),
    (SELECT uid FROM tmp_tb_prev WHERE tag = 'C2')),
  1,
  '2a. Origine = attesa (regressione): il milestone che genera e attende avanza');

SELECT is(
  (SELECT s.codice_interno FROM pratiche.flussi f
     JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
    WHERE f.id = (SELECT flusso_id FROM tmp_tb_c2_wait)),
  'COMPLETATO'::varchar,
  '2b. Milestone COMPLETATO (nessuna regressione sul caso semplice)');

-- ============================================================
-- Scenario C6 — nessun verdetto (preventivo EMESSO) + link d'origine.
-- ============================================================
CREATE TEMP TABLE tmp_tb_c6_prat AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_tb_refs), (SELECT tp_id FROM tmp_tb_tp),
          (SELECT soggetto_id FROM tmp_tb_refs), (SELECT st_aperta FROM tmp_tb_refs),
          (SELECT priorita_id FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

CREATE TEMP TABLE tmp_tb_c6_gen AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_tb_c6_prat), (SELECT tf_id FROM tmp_tb_gen),
          (SELECT fl_da_eseguire FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

CREATE TEMP TABLE tmp_tb_c6_wait AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_tb_c6_prat), (SELECT tf_id FROM tmp_tb_w1),
          (SELECT fl_da_eseguire FROM tmp_tb_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
VALUES ((SELECT pratica_id FROM tmp_tb_c6_prat), (SELECT src_preventivo FROM tmp_tb_refs),
        (SELECT uid FROM tmp_tb_prev WHERE tag = 'C6'), 'ROOT', (SELECT flusso_id FROM tmp_tb_c6_gen));

SELECT is(
  pratiche.fn_reconcile_sorgente(
    (SELECT src_preventivo FROM tmp_tb_refs),
    (SELECT uid FROM tmp_tb_prev WHERE tag = 'C6')),
  0,
  '6a. Nessun verdetto (preventivo EMESSO) -> 0 avanzamenti (invariato)');

SELECT is(
  (SELECT s.codice_interno FROM pratiche.flussi f
     JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
    WHERE f.id = (SELECT flusso_id FROM tmp_tb_c6_wait)),
  'DA_ESEGUIRE'::varchar,
  '6b. Il milestone in attesa resta DA_ESEGUIRE');

SELECT is(
  (SELECT count(*)::integer FROM pratiche.reconcile_errori re
    WHERE re.sorgente_uid = (SELECT uid FROM tmp_tb_prev WHERE tag = 'C6')),
  0,
  '6c. Nessun errore di riconciliazione senza verdetto');

SELECT * FROM finish();
ROLLBACK;
