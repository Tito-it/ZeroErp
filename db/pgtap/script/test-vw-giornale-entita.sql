-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.vw_giornale_entita — la cucitura dei quattro registri
--       (changeSet 20260822-70, brief-db-event-log-scope-e-riga-parlante §3.6)
-- ------------------------------------------------------------
-- Indice test (plan 15):
--  1) ⛔ la vista e' security_invoker — senza, tutto il perimetro cade
--  2) la fixture arriva nella vista da OGNI registro vivo di config.registri_giornale
--  3) `riga_key` e' unica: i quattro spazi di id non si sovrappongono
--  4) il ramo event_log porta il filo del giro e il numero di chi ha agito
--  5) ⭐ il task run porta il correlation_id passato all'apertura (changeSet 67)
--  6) la mappa della gravita': C -> ERROR, W -> WARN, I -> INFO
--  7) un tentativo fallito e' ERROR, e il codice errore entra nel «cosa»
--  8) ⭐ IL CANARINO: nessuna riga con `gravita` vuota, in tutta la vista
--  9) ⭐ ogni `entity_type` prodotto esiste in config.tipi_entita
-- 10) il `quando` di un tentativo chiuso e' lo started_at, non l'ended_at
--     (R-6, 20260919-04: la riga e' la corsa, e la corsa nasce li'; ended_at
--     lo puo' scrivere la corsa successiva, e una riga di diario non cambia
--     posto dopo essere nata — fino al 19-09 questo test pinnava il contrario)
-- 11) ⛔ nessun registro fuori dal catalogo config.registri_giornale
-- 12) una segnalazione RITIRATA resta nel diario: non si filtra
-- 13) ⭐ ...e si vede che e' ritirata: il flag c'e', accanto a quella viva
-- 14) event_log ha `disabilitato` NULL: il concetto non esiste
-- 15) i task_runs hanno NULL: il ritiro esiste, ma su un altro asse
--
-- Scopo:
--  - la vista non aggiunge un dato: rende leggibile insieme cio' che sta in
--    quattro posti. Il presidio serve su due cose che si rompono in silenzio —
--    la MAPPA della gravita' (tre vocabolari chiusi che entrano in uno) e
--    l'ASSE delle entita' (che deve restare il catalogo, non un elenco locale).
--  - ⭐ La 8, la 9 e la 11 sono canarini: non collaudano la vista di oggi, si
--    accendono il giorno che un CHECK si allarga o che un tipo nuovo entra in
--    un registro senza passare dal catalogo. E' la lezione del lotto L5 —
--    due elenchi che possono dissentire vanno fatti gridare — applicata prima
--    che il danno accada.
--  - ⭐ Dal 19-09 (20260919-08) anche l'asse dei REGISTRI e' un catalogo,
--    config.registri_giornale: la 2 e la 11 lo leggono da li', e l'elenco
--    dei quattro nomi scritto qui dentro e' stato ritirato — era la stessa
--    quarta copia che il catalogo nasce per togliere. Il legame fra vista e
--    catalogo nei due versi (sulla DEFINIZIONE, non sulle righe) sta in
--    test-giornale-registri-catalogo-v1.sql; qui si guarda che le RIGHE non
--    escano dal vocabolario (11) e che la fixture li tocchi tutti (2).
--
-- ⚠️ **Cosa questo file NON verifica, dichiarato**: la separazione fra
--    emittenti. Per farlo servirebbe un lotto o una fattura di un ALTRO
--    emittente, e l'operatore non li puo' creare (la `WITH CHECK` delle policy
--    lo impedisce, ed e' giusto cosi'). Il meccanismo e' presidiato dove vive:
--    `db/pgtap/rls/test-rls-event-log-ef-whitelist-write.sql` per il ramo che
--    si protegge da se', e i test RLS delle due testate per gli altri tre.
--    Qui si presidia la PRECONDIZIONE di tutto: che la vista sia
--    `security_invoker` (test 1). Senza quella, i tre join non filtrano niente.
--
-- ⚠️ Le asserzioni 8, 9 e 11 leggono TUTTA la vista visibile all'operatore,
--    non solo la fixture: sono data-dependent di proposito — un canarino che
--    guardasse solo le proprie righe non canterebbe mai.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Scattano al COMMIT, e qui il COMMIT non arriva mai (si chiude in ROLLBACK):
--   sarebbero saltati in silenzio, e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner — ed e' la condizione stessa di cio'
-- che verifica: con `security_invoker` la vista mostra il perimetro di CHI
-- LEGGE, quindi leggerla da owner non collauderebbe niente.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(15);

-- ============================================================
-- 0) Fixture — un lotto, una fattura, e una riga per registro
-- ============================================================
CREATE TEMP TABLE tmp_refs_ge AS
WITH ba AS (
  SELECT b.id, b.utility_id
    FROM anagrafiche.billing_account b
   ORDER BY b.data_insert DESC NULLS LAST, b.id DESC
   LIMIT 1
)
SELECT script.fn_pgtap_registro_fattura() AS registro_id,
       ba.id         AS billing_account_id,
       ba.utility_id AS utility_id,
       (SELECT m.tipo_doc_fiscale_id
          FROM vendite.tipi_doc_fiscale_registri m
          JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
         WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1) AS valuta_id,
       script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
       (SELECT id FROM config.stati_doc_fiscale
         WHERE codice_interno = 'DRAFT' AND attivo IS TRUE ORDER BY id LIMIT 1) AS stato_draft_id,
       (SELECT fp.id FROM vendite.fatturazione_pipeline fp
         WHERE fp.attivo IS TRUE ORDER BY fp.id LIMIT 1) AS pipeline_id
  FROM ba;

CREATE TEMP TABLE tmp_lotto_ge AS
SELECT vendite.fn_create_fatturazione_lotto(
  p_competenza_mese             => date_trunc('month', script.fn_data_operativa())::date,
  p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_refs_ge),
  p_utility_id                  => (SELECT utility_id FROM tmp_refs_ge),
  p_billing_account_id          => NULL,
  p_lock_batch_id               => NULL,
  p_meta                        => jsonb_build_object('test_scope', 'pgtap_giornale'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ge)
) AS lotto_id;

-- ⚠️ Padre e figlio in DUE istruzioni: le CTE che scrivono condividono la
--   stessa snapshot, e una policy che risolve il perimetro dal padre non lo
--   troverebbe.
CREATE TEMP TABLE tmp_fattura_ge AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, stato_doc_fiscale_id,
      totale_doc, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id,
         r.billing_account_id, r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id,
         r.stato_draft_id, 10.00, 10.00,
         jsonb_build_object('test_scope', 'pgtap_giornale')
    FROM tmp_refs_ge r
  RETURNING id
)
SELECT id FROM ins;

-- Le tre gravita' del registro di lotto, piu' una riga SPENTA (test 12).
INSERT INTO vendite.fatturazione_lotti_log (lotto_id, data_ora, messaggio, status, disabilitato, fase, meta)
VALUES
  ((SELECT lotto_id FROM tmp_lotto_ge), now() - interval '50 min', 'pgtap giornale I', 'I', FALSE, 'Fase I', '{}'::jsonb),
  ((SELECT lotto_id FROM tmp_lotto_ge), now() - interval '40 min', 'pgtap giornale W', 'W', FALSE, 'Fase W', '{}'::jsonb),
  ((SELECT lotto_id FROM tmp_lotto_ge), now() - interval '30 min', 'pgtap giornale C', 'C', FALSE, 'Fase C', '{}'::jsonb),
  ((SELECT lotto_id FROM tmp_lotto_ge), now() - interval '20 min', 'pgtap giornale SPENTA', 'C', TRUE, 'Fase S', '{}'::jsonb);

INSERT INTO vendite.fatture_log (fattura_id, data_ora, messaggio, status, disabilitato, meta)
VALUES ((SELECT id FROM tmp_fattura_ge), now() - interval '15 min', 'pgtap giornale fattura', 'C', FALSE, '{}'::jsonb);

-- Il tentativo: si apre col filo del giro e si chiude con un errore, cosi'
-- porta insieme correlation_id, ended_at e error_code.
CREATE TEMP TABLE tmp_run_ge AS
SELECT t.task_run_id
  FROM vendite.fn_start_lotto_task_run(
         p_lotto_id             => (SELECT lotto_id FROM tmp_lotto_ge),
         p_pipeline_id          => (SELECT pipeline_id FROM tmp_refs_ge),
         p_stato_doc_fiscale_id => (SELECT stato_draft_id FROM tmp_refs_ge),
         p_task_code            => 'pgtap_giornale'::varchar,
         p_fase                 => 'Fase task'::varchar,
         p_meta                 => '{}'::jsonb,
         p_correlation_id       => '0198f0ff-0000-7000-8000-0000000000e1'::uuid
       ) t;

SELECT vendite.fn_fail_lotto_task_run(
         (SELECT task_run_id FROM tmp_run_ge),
         'E_PGTAP_GIORNALE'::varchar,
         'guasto finto per il test',
         '{}'::jsonb);

-- L'evento: la firma e' a SEI parametri dal changeSet 20260822-57.
CREATE TEMP TABLE tmp_evento_ge AS
SELECT vendite.fn_log_event(
         p_entity_type    => 'LOTTO',
         p_entity_id      => (SELECT lotto_id FROM tmp_lotto_ge),
         p_event_code     => 'PGTAP_GIORNALE',
         p_severity       => 'WARN',
         p_correlation_id => '0198f0ff-0000-7000-8000-0000000000e1'::uuid,
         p_payload        => jsonb_build_object('test_scope', 'pgtap_giornale')
       ) AS event_id;

-- ============================================================
-- 1) La precondizione di tutto
-- ============================================================
--   ⛔ Senza security_invoker la vista girerebbe come PROPRIETARIO: la policy
--   di event_log non morderebbe e i tre join vedrebbero ogni testata. Non e'
--   una proprieta' di stile: e' la sola ragione per cui questa vista si puo'
--   esporre.
SELECT ok(
  (
    SELECT c.reloptions @> ARRAY['security_invoker=true']
        OR c.reloptions @> ARRAY['security_invoker=on']
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'script' AND c.relname = 'vw_giornale_entita'
  ),
  '1. la vista e'' security_invoker: legge col perimetro di chi la interroga'
);

-- ============================================================
-- 2-3) Ogni registro vivo, e la chiave della riga
-- ============================================================
--   ⭐ Il termine di confronto e' il CATALOGO, non un elenco scritto qui: un
--   quinto ramo che entra nella vista (e nel catalogo, o l'altro presidio fa
--   rosso) senza una riga di fixture in questo file fa rosso QUI — e' il
--   modo in cui questo test chiede di essere esteso, invece di restare verde
--   guardando quattro rami su cinque.
SELECT set_eq(
  $$ SELECT DISTINCT g.registro
       FROM script.vw_giornale_entita g
      WHERE g.cosa LIKE 'pgtap%' OR g.cosa LIKE 'PGTAP%' $$,
  $$ SELECT rg.codice_interno
       FROM config.registri_giornale rg
      WHERE rg.obsoleto_dal IS NULL $$,
  '2. la fixture arriva nella vista da ogni registro vivo di config.registri_giornale'
);

SELECT is(
  (SELECT count(DISTINCT g.riga_key)::int FROM script.vw_giornale_entita g),
  (SELECT count(*)::int FROM script.vw_giornale_entita g),
  '3. riga_key e'' unica: i quattro spazi di id non si sovrappongono'
);

-- ============================================================
-- 4-5) Il filo del giro, sui due rami che lo portano
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
      FROM script.vw_giornale_entita g
     WHERE g.registro       = 'EVENT_LOG'
       AND g.cosa           = 'PGTAP_GIORNALE'
       AND g.correlation_id = '0198f0ff-0000-7000-8000-0000000000e1'::uuid
       AND g.auth_user_id   IS NOT NULL
       AND g.gravita        = 'WARN'
  ),
  '4. il ramo event_log porta il filo del giro e il numero di chi ha agito'
);

-- ⭐ E' il ponte col changeSet 20260822-67: prima di quello la colonna esisteva
--   e nessuna funzione la scriveva, quindi questa riga sarebbe stata vuota.
SELECT is(
  (
    SELECT g.correlation_id
      FROM script.vw_giornale_entita g
     WHERE g.registro = 'TASK_RUN'
       AND g.riga_id  = (SELECT task_run_id FROM tmp_run_ge)
  ),
  '0198f0ff-0000-7000-8000-0000000000e1'::uuid,
  '5. il tentativo porta il correlation_id passato alla sua apertura'
);

-- ============================================================
-- 6-7) La mappa della gravita'
-- ============================================================
SELECT set_eq(
  $$ SELECT g.gravita || ':' || right(g.cosa, 1)
       FROM script.vw_giornale_entita g
      WHERE g.registro = 'LOTTO_LOG'
        AND g.cosa LIKE 'pgtap giornale _' $$,
  ARRAY['INFO:I', 'WARN:W', 'ERROR:C'],
  '6. C -> ERROR, W -> WARN, I -> INFO: i tre vocabolari entrano in uno'
);

SELECT ok(
  EXISTS (
    SELECT 1
      FROM script.vw_giornale_entita g
     WHERE g.registro = 'TASK_RUN'
       AND g.riga_id  = (SELECT task_run_id FROM tmp_run_ge)
       AND g.gravita  = 'ERROR'
       AND g.cosa LIKE '%pgtap_giornale%ERRORE%E_PGTAP_GIORNALE%'
  ),
  '7. un tentativo fallito e'' ERROR, e il codice errore entra nel «cosa»'
);

-- ============================================================
-- 8-9) I due canarini
-- ============================================================
--   ⚠️ Se la 8 diventa rossa NON si aggiunge un ELSE alla vista: si guarda
--   quale CHECK si e' allargato, e si decide che gravita' merita il valore
--   nuovo. L'ELSE e' il modo di non accorgersene mai.
SELECT is(
  (SELECT count(*)::int FROM script.vw_giornale_entita g WHERE g.gravita IS NULL),
  0,
  '8. nessuna riga con gravita vuota: la mappa copre tutti i vocabolari vivi'
);

--   ⚠️ E se diventa rossa la 9, un registro ha cominciato a citare un tipo di
--   entita' che il catalogo non conosce: l'asse della vista e'
--   `config.tipi_entita`, non un elenco scritto qui dentro.
SELECT is(
  (
    SELECT count(*)::int
      FROM script.vw_giornale_entita g
     WHERE NOT EXISTS (
             SELECT 1 FROM config.tipi_entita t WHERE t.codice = g.entity_type)
  ),
  0,
  '9. ogni entity_type prodotto esiste in config.tipi_entita'
);

-- ============================================================
-- 10-12) Tre scelte di disegno, rese verificabili
-- ============================================================
--   Il tentativo e' stato aperto e poi chiuso: il suo posto nella linea del
--   tempo e' il momento in cui E' NATO. Lo stato che mostra e' quello corrente
--   e non c'e' contraddizione: «il tentativo nato alle 10:00 e' finito cosi'».
--   ⭐ R-6 (20260919-04): fino al 19-09 qui si pinnava l'ended_at come «scelta
--   di disegno», ma ended_at lo scrive anche la corsa SUCCESSIVA (ANNULLATO)
--   e una riga di diario non deve cambiare posto dopo essere stata scritta.
SELECT is(
  (
    SELECT g.quando
      FROM script.vw_giornale_entita g
     WHERE g.registro = 'TASK_RUN'
       AND g.riga_id  = (SELECT task_run_id FROM tmp_run_ge)
  ),
  (
    SELECT r.started_at
      FROM vendite.fatturazione_lotti_task_runs r
     WHERE r.id = (SELECT task_run_id FROM tmp_run_ge)
  ),
  '10. il «quando» di un tentativo chiuso e'' lo started_at, non l''ended_at (R-6)'
);

--   ⚠️ Gemella della 9 sull'altro asse: l'elenco dei registri e'
--   config.registri_giornale, non quattro nomi scritti qui (ritirati il 19-09).
--   Il verso «ogni riga del catalogo ha il suo ramo» e' nell'altro presidio.
SELECT is(
  (
    SELECT count(*)::int
      FROM script.vw_giornale_entita g
     WHERE NOT EXISTS (
             SELECT 1 FROM config.registri_giornale rg
              WHERE rg.codice_interno = g.registro)
  ),
  0,
  '11. nessun registro fuori dal catalogo config.registri_giornale'
);

--   ⛔ Un diario dice cosa e' SUCCESSO, non cosa e' ancora aperto: la riga
--   spenta resta. «Cosa e' ancora aperto» ha gia' la sua sede in
--   vendite.fn_list_lotto_segnalazioni, che il filtro ce l'ha.
SELECT ok(
  EXISTS (
    SELECT 1
      FROM script.vw_giornale_entita g
     WHERE g.registro = 'LOTTO_LOG'
       AND g.cosa     = 'pgtap giornale SPENTA'
  ),
  '12. una segnalazione spenta resta nel diario: non si filtra'
);

-- ============================================================
-- 13-15) ⭐ Il flag del ritiro
-- ============================================================
--   La 12 dice che la riga resta; la 13 dice che si CAPISCE che e' ritirata.
--   Sono due proprieta' diverse, e la prima stesura della vista aveva solo la
--   prima: non filtrare e non dire non sono la stessa cosa. Senza il flag il
--   consumatore non puo' ne' marcare ne' nascondere — e non si filtra cio' che
--   non si vede.
--   ⚠️ L'asserzione confronta le DUE righe insieme, quella viva e quella
--   ritirata: un test che guardasse solo la ritirata passerebbe anche se la
--   vista rispondesse `true` a tutte.
SELECT set_eq(
  $$ SELECT g.cosa || '=' || g.disabilitato::text
       FROM script.vw_giornale_entita g
      WHERE g.registro = 'LOTTO_LOG'
        AND g.cosa IN ('pgtap giornale SPENTA', 'pgtap giornale C') $$,
  ARRAY['pgtap giornale SPENTA=true', 'pgtap giornale C=false'],
  '13. il flag del ritiro c''e'', e distingue la riga ritirata da quella viva'
);

--   ⛔ Qui NULL vuol dire «non si applica»: la tabella e' append-only, e un
--   evento e' un fatto accaduto — non un segnale che si accende e si spegne.
SELECT is(
  (
    SELECT count(*)::int
      FROM script.vw_giornale_entita g
     WHERE g.registro = 'EVENT_LOG'
       AND g.disabilitato IS NOT NULL
  ),
  0,
  '14. sul diario append-only il flag e'' sempre vuoto: non c''e'' niente da ritirare'
);

--   ⚠️ E qui NULL vuol dire un'altra cosa, ed e' scritto nella vista: il ritiro
--   esiste ma su un altro asse — `attivo` spegne il RECORD del tentativo (una
--   sola funzione lo fa), `disabilitato` ritira un SEGNALE (dieci funzioni).
--   Il giorno che qualcuno volesse vederlo qui, la mappatura si decide con dei
--   dati sotto: oggi 0 righe su 299 hanno `attivo = false`.
SELECT is(
  (
    SELECT count(*)::int
      FROM script.vw_giornale_entita g
     WHERE g.registro = 'TASK_RUN'
       AND g.disabilitato IS NOT NULL
  ),
  0,
  '15. sui tentativi il flag resta vuoto: il loro spegnimento e'' un altro asse'
);

SELECT * FROM finish();
ROLLBACK;
