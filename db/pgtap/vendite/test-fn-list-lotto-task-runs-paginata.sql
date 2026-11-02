-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_lotto_task_runs — paginazione, whitelist, `attivo`
--       (changeSet 20260821-38, cantiere brief-db-liste-drawer-lotto L1/P-1)
-- ------------------------------------------------------------
-- Indice test (plan 13)
-- 1)  Riferimenti minimi presenti
-- 2)  Lotto di prova creato
-- 3)  Fixture: 4 task run, 2 conclusi e 2 ancora in esecuzione
-- 4)  Chiamata di default: tutte le righe, e `total_count` le conta
-- 5)  L'ordine di default e' DISCENDENTE (quello storico della lista)
-- 6)  ⭐ `total_count` NON cambia con il `p_limit`: conta il filtrato, non la pagina
-- 7)  La pagina 2 non ripete righe della pagina 1 (pareggio rotto su id)
-- 8)  Tutti gli 8 nomi della whitelist sono accettati
-- 9)  ⭐ Un nome FUORI whitelist SOLLEVA, non ripiega in silenzio
-- 10) ...e lo fa nominando il parametro, non un errore qualunque
-- 11) p_lotto_id non positivo solleva
-- 12) ⚠️ NULLS LAST sul DESC: i task mai finiti non salgono in testa
-- 13) ⭐ `attivo`: una run spenta sparisce col default e torna con p_solo_attivi=false
--
-- Scopo:
--  - La funzione nasce per RIUNIRE due sorgenti che dicevano cose diverse
--    (questa, che ordinava ASC e ignorava `attivo`, e la query diretta del
--    backend, che ordina DESC e lo filtra). Le asserzioni 5 e 13 sono quelle
--    che misurano la riunione: senza, il refactor puo' regredire in silenzio
--    rovesciando una lista che l'operatore conosce o resuscitando i tentativi
--    di un giro annullato.
--  - Le 9 e 10 presidiano il fail-loud sull'ordinamento: una freccia fuori
--    whitelist che ripiega sul default produce una lista ordinata in un modo
--    che nessuno ha chiesto e che nessuno sa spiegare.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il test gira come gira l'applicazione (ruolo OPERATORE
-- + RLS attiva). La tabella dei task run non ha RLS, ma il LOTTO si', e la
-- fixture lo deve poter creare e rileggere.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- Vincoli differiti riportati a IMMEDIATE: qui il COMMIT non arriva mai, e
-- senza questa riga non verrebbero esercitati.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(19);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_refs_ptr AS
SELECT
  (
    SELECT m.tipo_doc_fiscale_id
    FROM vendite.tipi_doc_fiscale_registri m
    JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE
    ORDER BY m.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1
  ) AS utility_id,
  -- ⚠️ L'emittente NON si pesca: si deriva da chi agisce, o le policy
  --    ef_whitelist negano fail-closed.
  script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
  (
    SELECT fp.id FROM vendite.fatturazione_pipeline fp
     WHERE fp.attivo IS TRUE ORDER BY fp.id LIMIT 1
  ) AS pipeline_id,
  (
    SELECT s.id FROM config.stati_doc_fiscale s
     WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE
     ORDER BY s.id LIMIT 1
  ) AS stato_doc_fiscale_id;

SELECT ok(
  (
    SELECT tipo_doc_fiscale_id IS NOT NULL
       AND emittente_soggetto_ruolo_id IS NOT NULL
       AND pipeline_id IS NOT NULL
       AND stato_doc_fiscale_id IS NOT NULL
    FROM tmp_refs_ptr
  ),
  '1) riferimenti minimi presenti'
);

-- ============================================================
-- 1) Lotto di prova
-- ============================================================
CREATE TEMP TABLE tmp_lotto_ptr AS
SELECT vendite.fn_create_fatturazione_lotto(
  p_competenza_mese             => date_trunc('month', script.fn_data_operativa())::date,
  p_tipo_doc_fiscale_id         => (SELECT tipo_doc_fiscale_id FROM tmp_refs_ptr),
  p_utility_id                  => (SELECT utility_id FROM tmp_refs_ptr),
  p_billing_account_id          => NULL,
  p_lock_batch_id               => NULL,
  p_meta                        => jsonb_build_object('test_scope', 'pgtap_list_task_runs'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_ptr)
) AS lotto_id;

SELECT ok(
  (SELECT lotto_id IS NOT NULL AND lotto_id > 0 FROM tmp_lotto_ptr),
  '2) lotto di prova creato'
);

-- ============================================================
-- 2) Fixture: quattro task run
--    Due task code, due tentativi ciascuno. Di ogni coppia il primo viene
--    concluso (ended_at valorizzato) e il secondo resta in esecuzione
--    (ended_at NULL): serve alla 12, che misura i NULL in coda.
-- ============================================================
CREATE TEMP TABLE tmp_runs_ptr (ordine int, task_run_id bigint);

DO $fx$
DECLARE
  v_lotto    bigint := (SELECT lotto_id FROM tmp_lotto_ptr);
  v_pipeline bigint := (SELECT pipeline_id FROM tmp_refs_ptr);
  v_stato    bigint := (SELECT stato_doc_fiscale_id FROM tmp_refs_ptr);
  v_id       bigint;
  v_i        int := 0;
  v_code     text;
BEGIN
  FOREACH v_code IN ARRAY ARRAY['pgtap_lst_alfa', 'pgtap_lst_beta'] LOOP
    FOR v_i IN 1..2 LOOP
      SELECT t.task_run_id INTO v_id
        FROM vendite.fn_start_lotto_task_run(
               p_lotto_id             => v_lotto,
               p_pipeline_id          => v_pipeline,
               p_stato_doc_fiscale_id => v_stato,
               p_task_code            => v_code::varchar,
               p_fase                 => ('Fase ' || v_code)::varchar,
               p_meta                 => jsonb_build_object('test_scope', 'pgtap_list_task_runs')
             ) t;

      INSERT INTO tmp_runs_ptr(ordine, task_run_id)
      VALUES ((SELECT count(*) FROM tmp_runs_ptr) + 1, v_id);

      -- Il primo tentativo di ogni task si conclude, il secondo resta aperto.
      IF v_i = 1 THEN
        PERFORM vendite.fn_complete_lotto_task_run(v_id);
      END IF;
    END LOOP;
  END LOOP;
END
$fx$;

-- ⚠️ `now()` e' costante dentro una transazione: le quattro righe nascono con
--    lo STESSO started_at, e un test sull'ordine temporale non misurerebbe
--    niente. Qui la fixture distanzia gli istanti — e' l'unica cosa che
--    l'applicazione non puo' produrre in una transazione sola, ed e' anche
--    l'unica scrittura diretta di questo file.
UPDATE vendite.fatturazione_lotti_task_runs r
   SET started_at = now() - (make_interval(mins => p.ordine * 10))
  FROM tmp_runs_ptr p
 WHERE r.id = p.task_run_id;

SELECT is(
  (SELECT count(*)::int || '|' ||
          count(*) FILTER (WHERE r.ended_at IS NOT NULL)::int
     FROM vendite.fatturazione_lotti_task_runs r
    WHERE r.lotto_id = (SELECT lotto_id FROM tmp_lotto_ptr)),
  '4|2',
  '3) fixture: 4 task run, di cui 2 conclusi'
);

-- ============================================================
-- 3) Chiamata di default
-- ============================================================
SELECT is(
  (SELECT count(*)::int || '|' || max(t.total_count)::int
     FROM vendite.fn_list_lotto_task_runs((SELECT lotto_id FROM tmp_lotto_ptr)) t),
  '4|4',
  '4) default: 4 righe e total_count = 4'
);

-- ⭐ L'ordine di default e' DISCENDENTE. E' la meta' del refactor che puo'
--    regredire in silenzio: la vecchia funzione ordinava ASC, il backend DESC.
SELECT is(
  (SELECT array_agg(x.id ORDER BY x.o)
     FROM (SELECT row_number() OVER () AS o, s.id
             FROM vendite.fn_list_lotto_task_runs((SELECT lotto_id FROM tmp_lotto_ptr)) s) x),
  (SELECT array_agg(y.id ORDER BY y.started_at DESC, y.id DESC)
     FROM vendite.fatturazione_lotti_task_runs y
    WHERE y.lotto_id = (SELECT lotto_id FROM tmp_lotto_ptr) AND y.attivo IS TRUE),
  '5) l''ordine di default e'' started_at DESC, id DESC'
);

-- ============================================================
-- 4) Paginazione
-- ============================================================
SELECT is(
  (SELECT count(*)::int || '|' || max(t.total_count)::int
     FROM vendite.fn_list_lotto_task_runs(
            (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, TRUE, 2, 0) t),
  '2|4',
  '6) con limit 2: 2 righe, ma total_count resta 4'
);

-- Il pareggio si rompe su id nella stessa direzione: senza, la pagina 2
-- potrebbe ripetere una riga della 1 e perderne un'altra per sempre.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.fn_list_lotto_task_runs(
            (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, TRUE, 2, 0) a
     JOIN vendite.fn_list_lotto_task_runs(
            (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, TRUE, 2, 2) b
       ON b.id = a.id),
  0,
  '7) la pagina 2 non ripete righe della pagina 1'
);

-- ============================================================
-- 5) Whitelist di ordinamento
-- ============================================================
-- ⚠️ I nomi sono i `campo_sorgente` del seed della lista, non i suoi codici
--    logici: e' con quelli che il presidio gen_seed_lista.py confronta il flag
--    `ordinabile`. Se questa lista e quella del seed divergono, la lista nasce
--    con delle frecce bugiarde.
SELECT is(
  (SELECT count(*)::int
     FROM unnest(ARRAY['fase','task_code','tentativo','task_stato',
                       'started_at','ended_at','error_code','error_message']) AS nome
    WHERE (SELECT count(*)
             FROM vendite.fn_list_lotto_task_runs(
                    (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL,
                    TRUE, 500, 0, nome, 'asc')) = 4),
  8,
  '8) tutti gli 8 nomi della whitelist sono accettati'
);

-- ⭐ Fuori whitelist si SOLLEVA. `P0001` dice «errore di dominio»...
SELECT throws_ok(
  $$SELECT * FROM vendite.fn_list_lotto_task_runs(
      (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, TRUE, 10, 0, 'meta', 'asc')$$,
  'P0001',
  NULL,
  '9) un nome fuori whitelist solleva un errore di dominio'
);

-- ...e la frase dice QUALE: senza, l'asserzione qui sopra accetterebbe anche
-- il crash della funzione che voleva verificare.
SELECT throws_like(
  $$SELECT * FROM vendite.fn_list_lotto_task_runs(
      (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, TRUE, 10, 0, 'meta', 'asc')$$,
  '%p_order_by%',
  '10) ...e nomina il parametro rifiutato'
);

SELECT throws_ok(
  $$SELECT * FROM vendite.fn_list_lotto_task_runs(0)$$,
  'P0001',
  NULL,
  '11) p_lotto_id non positivo solleva'
);

-- ============================================================
-- 6) NULLS LAST
-- ============================================================
-- ⚠️ Su `DESC` PostgreSQL mette i NULL in TESTA: senza il NULLS LAST esplicito
--    i task mai finiti (ended_at NULL) salirebbero per primi, cioe' l'ordine
--    «dal piu' recente» comincerebbe da quelli che non sono ancora finiti.
SELECT is(
  (SELECT array_agg(x.finito ORDER BY x.o)
     FROM (SELECT row_number() OVER () AS o, (s.ended_at IS NOT NULL) AS finito
             FROM vendite.fn_list_lotto_task_runs(
                    (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL,
                    TRUE, 500, 0, 'ended_at', 'desc') s) x),
  ARRAY[true, true, false, false],
  '12) NULLS LAST sul DESC: i task mai finiti restano in coda'
);

-- ============================================================
-- 7) Il filtro `attivo`
-- ============================================================
-- ⚠️ Non e' decorativo: vendite.fn_riporta_lotto_a_draft spegne i task run
--    della vita precedente del lotto. Qui lo si simula con la scrittura che
--    quella funzione fa, perche' riportare davvero un lotto a DRAFT vorrebbe
--    dire collaudare un'altra funzione dentro questo file.
-- ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione: nella stessa, la
--    snapshot di statement leggerebbe PRIMA della scrittura.
UPDATE vendite.fatturazione_lotti_task_runs
   SET attivo = FALSE
 WHERE id = (SELECT task_run_id FROM tmp_runs_ptr ORDER BY ordine LIMIT 1);

SELECT is(
  (SELECT (SELECT count(*)::int FROM vendite.fn_list_lotto_task_runs(
             (SELECT lotto_id FROM tmp_lotto_ptr)))
       || '|' ||
          (SELECT count(*)::int FROM vendite.fn_list_lotto_task_runs(
             (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, FALSE))),
  '3|4',
  '13) una run spenta sparisce col default e torna con p_solo_attivi = false'
);

-- ============================================================
-- 14-19) ⭐ I FILTRI CHIESTI DAL BACKEND (2026-08-24)
--   Richiesta del backend, 2026-08-24. Analisi e limiti: testata del
--   changeSet 20260824-11.
--
--   ⚠️ La riga 1 e' stata spenta dal test 13, quindi il default ne vede 3.
--   Tutte le prove qui sotto girano con `p_solo_attivi = false`, cosi' la
--   base e' 4 e i conteggi si leggono senza doverli correggere a mente.
--
--   ⭐ L'invariante che rende leggibile la lista, ed e' il test 16:
--       total_count + esclusi_count = quante righe ci sono davvero.
--   Senza, una lista filtrata e una lista vuota si leggono uguali — ed e'
--   esattamente il motivo per cui il backend ha chiesto il conteggio.
-- ============================================================
CREATE TEMP TABLE tmp_filtri_ptr AS
SELECT
  (SELECT count(*)::int FROM vendite.fn_list_lotto_task_runs(
     (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, FALSE,
     500, 0, NULL, 'desc', FALSE, ARRAY['COMPLETATO'])) AS righe_completato,
  (SELECT max(esclusi_count)::int FROM vendite.fn_list_lotto_task_runs(
     (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, FALSE,
     500, 0, NULL, 'desc', FALSE, ARRAY['COMPLETATO'])) AS esclusi_completato,
  (SELECT max(total_count)::int FROM vendite.fn_list_lotto_task_runs(
     (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, FALSE,
     500, 0, NULL, 'desc', FALSE, ARRAY['COMPLETATO'])) AS total_completato,
  -- ⚠️ Due misure, non una: «tutte e due gli stati» da solo non
  --    discriminerebbe — 4 e' anche il risultato SENZA filtro. La seconda
  --    prova aggiunge uno stato ASSENTE dal fixture: se l'array fosse letto
  --    male (primo elemento soltanto, o OR mal formato) i due numeri
  --    cambierebbero insieme.
  (SELECT count(*)::int FROM vendite.fn_list_lotto_task_runs(
     (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, FALSE,
     500, 0, NULL, 'desc', FALSE, ARRAY['COMPLETATO','IN_ESECUZIONE'])) AS righe_due_stati,
  (SELECT count(*)::int FROM vendite.fn_list_lotto_task_runs(
     (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, FALSE,
     500, 0, NULL, 'desc', FALSE, ARRAY['COMPLETATO','ERRORE'])) AS righe_stato_assente,
  (SELECT count(*)::int FROM vendite.fn_list_lotto_task_runs(
     (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, FALSE,
     500, 0, NULL, 'desc', TRUE, NULL)) AS righe_solo_giro,
  (SELECT max(esclusi_count)::int FROM vendite.fn_list_lotto_task_runs(
     (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, FALSE,
     500, 0, NULL, 'desc', TRUE, NULL)) AS esclusi_solo_giro,
  (SELECT bool_and(giro_corrente) FROM vendite.fn_list_lotto_task_runs(
     (SELECT lotto_id FROM tmp_lotto_ptr), NULL, NULL, FALSE)) AS tutte_correnti;

SELECT is(
  (SELECT righe_completato FROM tmp_filtri_ptr), 2,
  '14) p_task_stato = {COMPLETATO}: restano le due run concluse'
);

SELECT is(
  (SELECT esclusi_completato FROM tmp_filtri_ptr), 2,
  '15) e esclusi_count dice quante ne ha tolte il filtro'
);

SELECT is(
  (SELECT total_completato + esclusi_completato FROM tmp_filtri_ptr), 4,
  '16) ⭐ invariante: total_count + esclusi_count = le righe che ci sono davvero'
);

SELECT is(
  (SELECT righe_due_stati || '|' || righe_stato_assente FROM tmp_filtri_ptr),
  '4|2',
  '17) l''array somma gli stati (4) e uno stato assente non aggiunge nulla (2)'
);

-- ⚠️ Il lotto di prova non e' mai passato dal runner, quindi in event_log non
--   c'e' nessun PIPELINE_STARTED: l'ancora e' NULL. Il contratto dice che
--   allora TUTTO conta come corrente — non c'e' nessuna corsa precedente da
--   cui distinguersi — e il filtro non deve nascondere niente.
SELECT is(
  (SELECT righe_solo_giro || '|' || esclusi_solo_giro FROM tmp_filtri_ptr),
  '4|0',
  '18) senza ancora (lotto mai passato dal runner) il filtro giro non toglie nulla'
);

SELECT ok(
  (SELECT tutte_correnti FROM tmp_filtri_ptr),
  '19) e la colonna giro_corrente lo dice riga per riga, non solo nel conteggio'
);

SELECT * FROM finish();
ROLLBACK;
