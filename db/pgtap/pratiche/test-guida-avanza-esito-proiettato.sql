-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su pratiche.template_flussi_avanzamento_proiezione, che a runtime
--   scrive solo pratiche.fn_copia_definizione — e quella gira dentro
--   fn_fork_definizione / fn_nuova_versione_definizione, entrambe SECURITY DEFINER.
--   Il ruolo applicativo ha solo SELECT ed e' corretto cosi': il soggetto del test
--   sta fuori dal percorso applicativo (brief §29.2).
-- pgTAP test per Zero ERP
-- Test: GUIDA (D4) — avanzamento milestone su esito proiettato
--       (brief-db-guida-avanza-esito-proiettato.md)
--       G1 colonna attende_sorgente_tipo_id + G2 binding avanzamento +
--       G3a fn_reconcile_sorgente + G3b trigger generico + G5 osservabilita' +
--       guard config-time (non-DOMINIO / mutua esclusione) + copia edizione.
-- ------------------------------------------------------------
-- Indice test (1..18; 21 asserzioni: 10/12/17 ne hanno due, a/b):
--  1) Struttura: template_flussi.attende_sorgente_tipo_id presente (G1)
--  2) Struttura: tabella template_flussi_avanzamento_proiezione presente (G2)
--  3) Struttura: tabella reconcile_errori presente (G5)
--  4) Struttura: trigger reconcile su vendite.preventivi presente (G3b pilota)
--  5) CHECK: binding con esito non-verdetto respinto (chk_tfap_esito_verdetto)
--  6) Guard: binding su step DOMINIO respinto (D-B3, 517)
--  7) Guard: binding su step con handler COMPLETATO attivo respinto (D-B10, 518)
--  8) Guard simmetrico: handler COMPLETATO su step con binding respinto (518)
--  9) Standalone -> avanza (E2E via trigger): preventivo ad ACCETTATO ->
--     milestone COMPLETATO con esito POSITIVO (due-salti, D-B2)
-- 10) Nessun verdetto -> no-op: preventivo EMESSO -> milestone resta DA_ESEGUIRE
-- 11) Additivita': step senza attende/binding -> nessun avanzamento
-- 12) Idempotenza: reconcile ripetuto sul terminale -> 0, milestone resta COMPLETATO (D-B11)
-- 13) Tie-break (D-B5): 2 candidati con flusso_id NULL -> nessun avanzamento
-- 14) Osservabilita' (D-B7): il tie-break ambiguo lascia una riga in reconcile_errori
-- 15) Copia edizione: fn_copia_definizione propaga attende_sorgente_tipo_id (G1)
-- 16) Copia edizione: fn_copia_definizione propaga il binding G2
-- 17) Inversione piena: binding NULL + preventivo RIFIUTATO -> milestone
--     COMPLETATO con esito NEGATIVO (follow-up owner §5)
-- 18) Ramo morto: con APPROVAZIONE NEGATIVO il prerequisito POSITIVO del passo a
--     valle NON e' soddisfatto (la pratica puo' chiudersi, niente smistamento)
-- 19) Senza aggancio a una pratica -> 0 avanzamenti anche con un verdetto
--     (uscita anticipata prima di fn_stato_sorgente, 20261005-22)
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i preventivi nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima nascevano
--   gia' EMESSO/ACCETTATO/RIFIUTATO), PRIMA dell'aggancio alla pratica: il
--   trigger z90 di riconciliazione scatta a ogni passaggio di stato, e senza
--   aggancio non ha niente da riconciliare.
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): i preventivi
--   si emettono con una riga (merce, 1 x 10) da
--   dbops.fn_pgtap_crea_preventivo_con_righe (p_preventivo_id): l'emissione
--   senza righe e' rifiutata. L'accettazione dei test 9 e 11 passa dal verbo
--   vendite.fn_cambia_stato_preventivo invece dell'UPDATE dello stato, che la
--   porta rifiuta: il trigger z90 sotto prova scatta uguale. Nessuna attesa
--   conta righe o importi.
-- rev 2026-11-08 (brief-db-sorgente-documento-e-riga lotto P, giro P.1): il preventivo del fixture tiene l'uid come uuid, il reconcile prende (tipo, sorgente_id, sorgente_uid).
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

SELECT plan(22);

-- Provisioning stati flusso (idempotente).
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true),
       ('IN_CORSO',    'IN_CORSO',    'In corso',    true),
       ('COMPLETATO',  'COMPLETATO',  'Completato',  true)
ON CONFLICT (codice_interno) DO NOTHING;

-- ============================================================
-- Riferimenti minimi (pattern test-proiezione-stato-sorgente)
-- ============================================================
-- ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-2): il preventivo ha
--   sempre il suo billing account, quello della sua coppia (istanza, utility),
--   e il guard dell'emittente pretende che il BA sia dell'emittente del
--   documento. Fino a quel giorno la coppia si PESCAVA dal primo BA del
--   database e il preventivo nasceva senza BA. Ora il cliente si COSTRUISCE,
--   col BA legato esplicitamente all'emittente usato dal file.
--   ⛔ Si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_g_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'pgtap g preventivo col BA', NULL,
    (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1));

CREATE TEMP TABLE tmp_g_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_g_cli) AS billing_account_id,
  (SELECT istanza_utility_id FROM tmp_g_cli) AS istanza_utility_id,
  (SELECT utility_id FROM tmp_g_cli) AS utility_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1) AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA') AS st_aperta,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS fl_da_eseguire,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1) AS src_preventivo,
  (SELECT sd.id FROM config.stati_doc_preventivi sd WHERE sd.codice_interno = 'EMESSO' LIMIT 1) AS stato_emesso_id,
  (SELECT sd.id FROM config.stati_doc_preventivi sd WHERE sd.codice_interno = 'ACCETTATO' LIMIT 1) AS stato_accettato_id,
  (SELECT id FROM pratiche.template_flussi_handler_eventi WHERE evento = 'COMPLETATO' LIMIT 1) AS any_handler_evento_id;

-- Un handler ATTIVO di fixture per costruire un binding handler_eventi attivo
-- (trgfn_child_requires_active_parent rifiuta un binding attivo verso un
-- handler spento). Fabbricato qui e non pescato dai binding del seed: quale
-- handler del seed sia acceso e' un dato che cambia (vendita.accetta_preventivo
-- e' stato ritirato).
CREATE TEMP TABLE tmp_g_hid AS
WITH ins AS (
  INSERT INTO pratiche.handler_flussi (handler_key, codice, descrizione, attivo)
  VALUES ('pgtap.guida_fixture', 'PGTAP_GUIDA_FIXTURE',
          'Handler di fixture del pgTAP GUIDA (mai dispatchato)', true)
  RETURNING id
)
SELECT id AS handler_id FROM ins;

-- ============================================================
-- Tipo prestazione + step di fixture
-- ============================================================
CREATE TEMP TABLE tmp_g_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_GUIDA', 'TEST_GUIDA', 'Tipo test GUIDA D4', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
) SELECT id AS tp_id FROM ins;

-- MILESTONE: step non-DOMINIO che attende il PREVENTIVO.
CREATE TEMP TABLE tmp_g_ms AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi
    (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo,
     ripetibilita, modalita_esito, attende_sorgente_tipo_id)
  VALUES ((SELECT tp_id FROM tmp_g_tp), 'MS_PREV', 'Milestone attende preventivo',
          10, false, true, 'SEMPRE', 'MANUALE', (SELECT src_preventivo FROM tmp_g_refs))
  RETURNING id, definizione_id
) SELECT id AS tf_id, definizione_id FROM ins;

-- MILESTONE2: secondo step che attende il PREVENTIVO (per il tie-break).
CREATE TEMP TABLE tmp_g_ms2 AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi
    (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo,
     ripetibilita, modalita_esito, attende_sorgente_tipo_id)
  VALUES ((SELECT tp_id FROM tmp_g_tp), 'MS_PREV_2', 'Milestone 2 attende preventivo',
          20, false, true, 'SEMPRE', 'MANUALE', (SELECT src_preventivo FROM tmp_g_refs))
  RETURNING id
) SELECT id AS tf_id FROM ins;

-- NOOP: step senza attende (additivita').
CREATE TEMP TABLE tmp_g_noop AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi
    (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, ripetibilita, modalita_esito)
  VALUES ((SELECT tp_id FROM tmp_g_tp), 'MS_NOOP', 'Milestone senza proiezione',
          30, false, true, 'SEMPRE', 'MANUALE')
  RETURNING id
) SELECT id AS tf_id FROM ins;

-- DOMINIO: step a esito di ramo (per il guard 6).
CREATE TEMP TABLE tmp_g_dom AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi
    (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, ripetibilita, modalita_esito, esito_default)
  VALUES ((SELECT tp_id FROM tmp_g_tp), 'MS_DOMINIO', 'Milestone dominio',
          40, false, true, 'SEMPRE', 'DOMINIO', NULL)
  RETURNING id
) SELECT id AS tf_id FROM ins;

-- HANDLER: step con un handler_eventi COMPLETATO attivo (per il guard 7).
CREATE TEMP TABLE tmp_g_hstep AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi
    (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, ripetibilita, modalita_esito)
  VALUES ((SELECT tp_id FROM tmp_g_tp), 'MS_HANDLER', 'Milestone con handler',
          50, false, true, 'SEMPRE', 'MANUALE')
  RETURNING id
) SELECT id AS tf_id FROM ins;

INSERT INTO pratiche.template_flussi_handler_eventi
  (template_flusso_id, evento, esito_richiesto, handler_id, attivo)
VALUES ((SELECT tf_id FROM tmp_g_hstep), 'COMPLETATO', 'POSITIVO', (SELECT handler_id FROM tmp_g_hid), true);

-- Binding G2 attivo sui due milestone che proiettano.
INSERT INTO pratiche.template_flussi_avanzamento_proiezione (template_flusso_id, esito_richiesto)
VALUES ((SELECT tf_id FROM tmp_g_ms),  'POSITIVO'),
       ((SELECT tf_id FROM tmp_g_ms2), 'POSITIVO');

-- ============================================================
-- 1..4) Struttura
-- ============================================================
SELECT has_column('pratiche', 'template_flussi', 'attende_sorgente_tipo_id',
  '1. template_flussi.attende_sorgente_tipo_id presente (G1)');

SELECT has_table('pratiche', 'template_flussi_avanzamento_proiezione',
  '2. tabella template_flussi_avanzamento_proiezione presente (G2)');

SELECT has_table('pratiche', 'reconcile_errori',
  '3. tabella reconcile_errori presente (G5)');

SELECT has_trigger('vendite', 'preventivi', 'trg_preventivi_z90_reconcile_proiezione_upd',
  '4. trigger reconcile su vendite.preventivi presente (G3b pilota)');

-- ============================================================
-- 5..8) Guard config-time del binding
-- ============================================================
SELECT throws_ok(
  $$INSERT INTO pratiche.template_flussi_avanzamento_proiezione (template_flusso_id, esito_richiesto)
    VALUES ((SELECT tf_id FROM tmp_g_noop), 'MERCE_PRESENTE')$$,
  NULL, NULL,
  '5. binding con esito non-verdetto respinto (CHECK chk_tfap_esito_verdetto)');

SELECT throws_like(
  $$INSERT INTO pratiche.template_flussi_avanzamento_proiezione (template_flusso_id, esito_richiesto)
    VALUES ((SELECT tf_id FROM tmp_g_dom), 'POSITIVO')$$,
  '%DOMINIO%',
  '6. binding su step DOMINIO respinto (D-B3, 517)');

SELECT throws_like(
  $$INSERT INTO pratiche.template_flussi_avanzamento_proiezione (template_flusso_id, esito_richiesto)
    VALUES ((SELECT tf_id FROM tmp_g_hstep), 'POSITIVO')$$,
  '%onflitto%',
  '7. binding su step con handler COMPLETATO attivo respinto (D-B10, 518)');

SELECT throws_like(
  $$INSERT INTO pratiche.template_flussi_handler_eventi
      (template_flusso_id, evento, esito_richiesto, handler_id, attivo)
    VALUES ((SELECT tf_id FROM tmp_g_ms), 'COMPLETATO', 'POSITIVO',
            (SELECT handler_id FROM tmp_g_hid), true)$$,
  '%onflitto%',
  '8. handler COMPLETATO su step con binding respinto (D-B10 lato simmetrico, 518)');

-- ============================================================
-- Fixture pratiche/flussi/preventivi
-- ============================================================
-- Preventivi: 3 EMESSO (adv, noop-milestone, additivita') + 1 ACCETTATO (tie-break).
-- ⚠️ rev 2026-10-24 (brief-modello-documento-vendita N-1): nascono in bozza
--   (lo stato non si scrive: lo mette il trigger della nascita) e si portano
--   avanti subito sotto, per la matrice.
-- ⚠️ rev 2026-10-25 (§8, giro 6): ognuno con una riga (merce, 1 x 10) scritta
--   in bozza da dbops.fn_pgtap_crea_preventivo_con_righe, che poi porta lo
--   stato: senza righe l'emissione e' rifiutata (E_PREV_NESSUNA_RIGA_ATTIVA).
-- rev 2026-10-31 (brief-db-scadenza-preventivi §8.3): validita_al da oggi + 30, come i
--   builder. Con una data fissa di luglio 2026 la validita' era gia' finita, e l'accettazione
--   ora la rifiuta (E_PREV_VALIDITA_SCADUTA): la data era un dettaglio, non il caso.
CREATE TEMP TABLE tmp_g_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi
    (numero, rev, billing_account_id, istanza_utility_id, utility_id, validita_dal, validita_al, valuta_id,
     data, fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT
    'PGTAP-GUIDA-' || x.suffisso || '-' || substr(md5(clock_timestamp()::text || x.suffisso), 1, 8),
    0, r.billing_account_id, r.istanza_utility_id, r.utility_id, DATE '2026-07-01', script.fn_data_operativa() + 30, r.valuta_id,
    DATE '2026-07-01', false, false,
    '{"test_scope":"pgtap_guida"}'::jsonb, r.emittente_id
  FROM tmp_g_refs r
  CROSS JOIN (
    SELECT 'ADV'   AS suffisso
    UNION ALL SELECT 'NOV'
    UNION ALL SELECT 'ADD'
    UNION ALL SELECT 'AMB'
  ) x
  RETURNING id, uid
)
SELECT i.id, i.uid
FROM ins i;

-- Etichettatura stabile per suffisso nel numero (ADV/NOV/ADD/AMB).
CREATE TEMP TABLE tmp_g_prev_lbl AS
SELECT p.id, p.uid,
       split_part(v.numero, '-', 3) AS tag
FROM tmp_g_prev p
JOIN vendite.preventivi v ON v.id = p.id;

-- Lo stato della fixture, per la matrice e sotto i guard veri: AMB ad
--   ACCETTATO (passa da EMESSO), gli altri tre a EMESSO. Prima dell'aggancio
--   alla pratica: il reconcile z90 che scatta qui non trova legami.
DO $porta$
DECLARE
  r record;
BEGIN
  FOR r IN SELECT l.id, l.tag FROM tmp_g_prev_lbl l ORDER BY l.id LOOP
    PERFORM dbops.fn_pgtap_crea_preventivo_con_righe('guida ' || r.tag,
              CASE r.tag WHEN 'AMB' THEN 'ACCETTATO' ELSE 'EMESSO' END,
              p_preventivo_id => r.id);
  END LOOP;
END
$porta$;

-- 3 pratiche (adv, nov, add) + 1 pratica tie-break (amb).
CREATE TEMP TABLE tmp_g_prat AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  SELECT (SELECT emittente_id FROM tmp_g_refs), (SELECT tp_id FROM tmp_g_tp),
         (SELECT soggetto_id FROM tmp_g_refs), (SELECT st_aperta FROM tmp_g_refs),
         (SELECT priorita_id FROM tmp_g_refs)
  FROM generate_series(1, 4) g
  RETURNING id
)
SELECT id, row_number() OVER (ORDER BY id) AS n FROM ins;

-- Flussi: adv(MS su pratica1), add(NOOP su pratica3), amb1(MS)/amb2(MS2) su pratica4.
CREATE TEMP TABLE tmp_g_fl_adv AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT id FROM tmp_g_prat WHERE n = 1), (SELECT tf_id FROM tmp_g_ms),
          (SELECT fl_da_eseguire FROM tmp_g_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

CREATE TEMP TABLE tmp_g_fl_nov AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT id FROM tmp_g_prat WHERE n = 2), (SELECT tf_id FROM tmp_g_ms),
          (SELECT fl_da_eseguire FROM tmp_g_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

CREATE TEMP TABLE tmp_g_fl_add AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT id FROM tmp_g_prat WHERE n = 3), (SELECT tf_id FROM tmp_g_noop),
          (SELECT fl_da_eseguire FROM tmp_g_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

CREATE TEMP TABLE tmp_g_fl_amb AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT id FROM tmp_g_prat WHERE n = 4), (SELECT tf_id FROM tmp_g_ms),
          (SELECT fl_da_eseguire FROM tmp_g_refs)),
         ((SELECT id FROM tmp_g_prat WHERE n = 4), (SELECT tf_id FROM tmp_g_ms2),
          (SELECT fl_da_eseguire FROM tmp_g_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

-- Aggancio documento->pratica.
INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
VALUES
  -- ADV: ROOT col flusso_id esplicito (tie-break non ambiguo).
  ((SELECT id FROM tmp_g_prat WHERE n = 1), (SELECT src_preventivo FROM tmp_g_refs),
   (SELECT uid FROM tmp_g_prev_lbl WHERE tag = 'ADV'), 'ROOT', (SELECT flusso_id FROM tmp_g_fl_adv)),
  -- NOV: ROOT col flusso_id esplicito.
  ((SELECT id FROM tmp_g_prat WHERE n = 2), (SELECT src_preventivo FROM tmp_g_refs),
   (SELECT uid FROM tmp_g_prev_lbl WHERE tag = 'NOV'), 'ROOT', (SELECT flusso_id FROM tmp_g_fl_nov)),
  -- ADD: ROOT col flusso_id esplicito (step NOOP).
  ((SELECT id FROM tmp_g_prat WHERE n = 3), (SELECT src_preventivo FROM tmp_g_refs),
   (SELECT uid FROM tmp_g_prev_lbl WHERE tag = 'ADD'), 'ROOT', (SELECT flusso_id FROM tmp_g_fl_add)),
  -- AMB: COLLEGATO con flusso_id NULL -> 2 candidati -> ambiguo.
  ((SELECT id FROM tmp_g_prat WHERE n = 4), (SELECT src_preventivo FROM tmp_g_refs),
   (SELECT uid FROM tmp_g_prev_lbl WHERE tag = 'AMB'), 'COLLEGATO', NULL);

-- ============================================================
-- 9) Standalone -> avanza (E2E via trigger G3b + due-salti)
-- ============================================================
-- rev 2026-10-25 (§8, giro 6): l'accettazione passa dal verbo; l'UPDATE
--   diretto dello stato lo rifiuta la porta (E_DOC_STATO_SOLO_DAL_VERBO).
DO $verbo$ BEGIN
  PERFORM vendite.fn_cambia_stato_preventivo(
            (SELECT id FROM tmp_g_prev_lbl WHERE tag = 'ADV'), 'ACCETTATO');
END $verbo$;

SELECT results_eq(
  $$SELECT s.codice_interno, f.esito
      FROM pratiche.flussi f
      JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
     WHERE f.id = (SELECT flusso_id FROM tmp_g_fl_adv)$$,
  $$VALUES ('COMPLETATO'::varchar, 'POSITIVO'::varchar)$$,
  '9. Standalone: preventivo ACCETTATO -> milestone COMPLETATO/POSITIVO (due-salti)');

-- ============================================================
-- 10) Nessun verdetto -> no-op (preventivo EMESSO)
-- ============================================================
SELECT is(
  pratiche.fn_reconcile_sorgente(
    (SELECT src_preventivo FROM tmp_g_refs),
    NULL,
    (SELECT uid FROM tmp_g_prev_lbl WHERE tag = 'NOV')),
  0,
  '10a. reconcile su preventivo EMESSO (esito NULL) -> 0 avanzamenti');

SELECT is(
  (SELECT s.codice_interno FROM pratiche.flussi f
     JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
    WHERE f.id = (SELECT flusso_id FROM tmp_g_fl_nov)),
  'DA_ESEGUIRE'::varchar,
  '10b. milestone del preventivo EMESSO resta DA_ESEGUIRE');

-- ============================================================
-- 11) Additivita': step senza attende/binding -> nessun avanzamento
-- ============================================================
-- rev 2026-10-25 (§8, giro 6): l'accettazione passa dal verbo; l'UPDATE
--   diretto dello stato lo rifiuta la porta (E_DOC_STATO_SOLO_DAL_VERBO).
DO $verbo$ BEGIN
  PERFORM vendite.fn_cambia_stato_preventivo(
            (SELECT id FROM tmp_g_prev_lbl WHERE tag = 'ADD'), 'ACCETTATO');
END $verbo$;

SELECT is(
  (SELECT s.codice_interno FROM pratiche.flussi f
     JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
    WHERE f.id = (SELECT flusso_id FROM tmp_g_fl_add)),
  'DA_ESEGUIRE'::varchar,
  '11. step senza attende_sorgente -> milestone resta DA_ESEGUIRE (additivita'')');

-- ============================================================
-- 12) Idempotenza: reconcile ripetuto sul terminale -> 0, resta COMPLETATO
-- ============================================================
SELECT is(
  pratiche.fn_reconcile_sorgente(
    (SELECT src_preventivo FROM tmp_g_refs),
    NULL,
    (SELECT uid FROM tmp_g_prev_lbl WHERE tag = 'ADV')),
  0,
  '12a. reconcile ripetuto sul milestone gia'' COMPLETATO -> 0 (idempotenza, D-B11)');

SELECT is(
  (SELECT s.codice_interno FROM pratiche.flussi f
     JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
    WHERE f.id = (SELECT flusso_id FROM tmp_g_fl_adv)),
  'COMPLETATO'::varchar,
  '12b. il milestone resta COMPLETATO (nessun doppio avanzamento)');

-- ============================================================
-- 13-14) Tie-break ambiguo + osservabilita'
-- ============================================================
SELECT is(
  pratiche.fn_reconcile_sorgente(
    (SELECT src_preventivo FROM tmp_g_refs),
    NULL,
    (SELECT uid FROM tmp_g_prev_lbl WHERE tag = 'AMB')),
  0,
  '13. tie-break: 2 candidati con flusso_id NULL -> 0 avanzamenti (D-B5)');

SELECT ok(
  EXISTS (
    SELECT 1 FROM pratiche.reconcile_errori re
     WHERE re.sorgente_tipo_id = (SELECT src_preventivo FROM tmp_g_refs)
       AND re.sorgente_uid = (SELECT uid FROM tmp_g_prev_lbl WHERE tag = 'AMB')
       AND re.errcode = 'E_RECONCILE_AMBIGUO'
  ),
  '14. il tie-break ambiguo lascia una riga in reconcile_errori (osservabilita'', D-B7)');

-- ============================================================
-- 15-16) Copia edizione: fn_copia_definizione propaga G1 + G2
-- ============================================================
-- Copia verso l'emittente di test (scope (tipo, emittente) nuovo: nessun
-- conflitto con la BOZZA/preset dello scope (tipo, NULL)).
CREATE TEMP TABLE tmp_g_copia AS
SELECT pratiche.fn_copia_definizione(
         (SELECT definizione_id FROM tmp_g_ms)::integer,
         (SELECT emittente_id FROM tmp_g_refs)::bigint,
         false) AS new_def_id;

SELECT is(
  (SELECT nt.attende_sorgente_tipo_id
     FROM pratiche.template_flussi nt
    WHERE nt.definizione_id = (SELECT new_def_id FROM tmp_g_copia)
      AND nt.codice = 'MS_PREV'),
  (SELECT src_preventivo FROM tmp_g_refs),
  '15. fn_copia_definizione propaga attende_sorgente_tipo_id alla nuova edizione (G1)');

SELECT ok(
  EXISTS (
    SELECT 1
      FROM pratiche.template_flussi_avanzamento_proiezione b
      JOIN pratiche.template_flussi nt ON nt.id = b.template_flusso_id
     WHERE nt.definizione_id = (SELECT new_def_id FROM tmp_g_copia)
       AND nt.codice = 'MS_PREV'
       AND b.esito_richiesto = 'POSITIVO'
  ),
  '16. fn_copia_definizione propaga il binding G2 alla nuova edizione');

-- ============================================================
-- 17-18) Inversione piena (binding NULL) + ramo morto sul rifiuto
-- ============================================================
-- Step con binding NULL (qualsiasi verdetto) + passo a valle gated su POSITIVO.
CREATE TEMP TABLE tmp_g_neg AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi
    (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo,
     ripetibilita, modalita_esito, attende_sorgente_tipo_id)
  VALUES ((SELECT tp_id FROM tmp_g_tp), 'MS_NEG', 'Milestone binding NULL',
          60, false, true, 'SEMPRE', 'MANUALE', (SELECT src_preventivo FROM tmp_g_refs))
  RETURNING id
) SELECT id AS tf_id FROM ins;

CREATE TEMP TABLE tmp_g_down AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi
    (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, ripetibilita, modalita_esito)
  VALUES ((SELECT tp_id FROM tmp_g_tp), 'MS_DOWN', 'Passo a valle gated su POSITIVO',
          70, true, true, 'SEMPRE', 'MANUALE')
  RETURNING id
) SELECT id AS tf_id FROM ins;

-- Prerequisito esito-aware: MS_DOWN richiede MS_NEG = POSITIVO.
INSERT INTO pratiche.template_flussi_prerequisiti (template_flusso_id, prerequisito_id, esito_richiesto)
VALUES ((SELECT tf_id FROM tmp_g_down), (SELECT tf_id FROM tmp_g_neg), 'POSITIVO');

-- Binding NULL = qualsiasi verdetto.
INSERT INTO pratiche.template_flussi_avanzamento_proiezione (template_flusso_id, esito_richiesto)
VALUES ((SELECT tf_id FROM tmp_g_neg), NULL);

-- Preventivo RIFIUTATO (proietta verdetto NEGATIVO).
-- ⚠️ rev 2026-10-24: nasce in bozza e va a RIFIUTATO per la matrice
--   (DRAFT -> EMESSO -> RIFIUTATO), prima dell'aggancio del test 17a.
--   rev 2026-10-25 (§8, giro 6): con una riga, dal builder (come sopra).
-- rev 2026-10-31 (brief-db-scadenza-preventivi §8.3): validita_al da oggi + 30, come i
--   builder. Con una data fissa di luglio 2026 la validita' era gia' finita, e l'accettazione
--   ora la rifiuta (E_PREV_VALIDITA_SCADUTA): la data era un dettaglio, non il caso.
CREATE TEMP TABLE tmp_g_prev_rif AS
WITH ins AS (
  INSERT INTO vendite.preventivi
    (numero, rev, billing_account_id, istanza_utility_id, utility_id, validita_dal, validita_al, valuta_id,
     data, fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  SELECT 'PGTAP-GUIDA-RIF-' || substr(md5(clock_timestamp()::text), 1, 8), 0,
         r.billing_account_id, r.istanza_utility_id, r.utility_id, DATE '2026-07-01', script.fn_data_operativa() + 30, r.valuta_id,
         DATE '2026-07-01', false, false, '{"test_scope":"pgtap_guida"}'::jsonb, r.emittente_id
  FROM tmp_g_refs r
  RETURNING id, uid
) SELECT id, uid FROM ins;

DO $porta$ BEGIN
  PERFORM dbops.fn_pgtap_crea_preventivo_con_righe('guida RIF', 'RIFIUTATO',
            p_preventivo_id => (SELECT id FROM tmp_g_prev_rif));
END $porta$;

-- Pratica NEG + flusso MS_NEG (DA_ESEGUIRE) + link ROOT col flusso_id.
CREATE TEMP TABLE tmp_g_prat_neg AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES ((SELECT emittente_id FROM tmp_g_refs), (SELECT tp_id FROM tmp_g_tp),
          (SELECT soggetto_id FROM tmp_g_refs), (SELECT st_aperta FROM tmp_g_refs),
          (SELECT priorita_id FROM tmp_g_refs))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

CREATE TEMP TABLE tmp_g_fl_neg AS
WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES ((SELECT pratica_id FROM tmp_g_prat_neg), (SELECT tf_id FROM tmp_g_neg),
          (SELECT fl_da_eseguire FROM tmp_g_refs))
  RETURNING id
) SELECT id AS flusso_id FROM ins;

-- ============================================================
-- 19) Senza aggancio -> 0, anche con un verdetto (rev 2026-10-05, 20261005-22)
--   Il preventivo RIFIUTATO proietta NEGATIVO e il milestone che lo
--   attenderebbe esiste gia', ma l'aggancio in pratiche_sorgenti non c'e'
--   ancora: niente da riconciliare. E' il ramo dell'uscita anticipata, che
--   salta il calcolo dell'esito. ⭐ L'altra meta' della prova e' il 17a, subito
--   dopo l'aggancio: stesso documento, stesso verdetto, avanza 1 — un'uscita
--   anticipata che scattasse anche CON l'aggancio lo farebbe tornare rosso.
-- ============================================================
SELECT is(
  pratiche.fn_reconcile_sorgente(
    (SELECT src_preventivo FROM tmp_g_refs),
    NULL,
    (SELECT uid FROM tmp_g_prev_rif)),
  0,
  '19. preventivo RIFIUTATO senza aggancio a una pratica -> 0 avanzamenti');

INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link, flusso_id)
VALUES ((SELECT pratica_id FROM tmp_g_prat_neg), (SELECT src_preventivo FROM tmp_g_refs),
        (SELECT uid FROM tmp_g_prev_rif), 'ROOT', (SELECT flusso_id FROM tmp_g_fl_neg));

SELECT is(
  pratiche.fn_reconcile_sorgente(
    (SELECT src_preventivo FROM tmp_g_refs),
    NULL,
    (SELECT uid FROM tmp_g_prev_rif)),
  1,
  '17a. binding NULL: reconcile su preventivo RIFIUTATO avanza 1 milestone');

SELECT results_eq(
  $$SELECT s.codice_interno, f.esito
      FROM pratiche.flussi f
      JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
     WHERE f.id = (SELECT flusso_id FROM tmp_g_fl_neg)$$,
  $$VALUES ('COMPLETATO'::varchar, 'NEGATIVO'::varchar)$$,
  '17b. binding NULL: milestone COMPLETATO con esito NEGATIVO (inversione piena)');

SELECT ok(
  EXISTS (
    SELECT 1
      FROM pratiche.fn_check_prerequisiti_flusso(
             (SELECT pratica_id FROM tmp_g_prat_neg),
             (SELECT tf_id FROM tmp_g_down)) p
     WHERE NOT p.soddisfatto
  ),
  '18. ramo morto: con APPROVAZIONE NEGATIVO il prerequisito POSITIVO del passo a valle NON e'' soddisfatto');

SELECT * FROM finish();
ROLLBACK;
