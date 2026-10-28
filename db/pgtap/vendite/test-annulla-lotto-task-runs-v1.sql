-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: chi annulla un lotto ABBASSA LA BANDIERA — vendite.fn_annulla_lotto_da_draft
-- Piano: brief-residuo-fatturabili-e-bandiere-esito-parziale, sezioni 5 e 9.4 (D4)
-- ------------------------------------------------------------
-- Cosa presidia questo file
--   Dopo l'annullo di un lotto la segnalazione sul calendario di competenza
--   restava accesa, ed era FEDELE AL DATO: la CTE `task_err` di
--   vw_dash_competenza_errori prende i task_run in ERRORE ancora attivi e non
--   guarda lo stato del lotto. Il run restava ERRORE, quindi l'evento restava.
--   Ma la lista si chiama «errori vivi»: un lotto annullato non e' piu' lavoro
--   in corso, il suo errore e' storia.
--
-- 🔴 IL TEST CHE VALE DI PIU' E' IL 6, e non il 5.
--   Il 5 dice che la bandiera si e' abbassata. Il 6 dice COME, ed e' l'unica
--   parte che una riscrittura futura puo' sbagliare restando verde altrove:
--   la leva e' l'ESITO (`task_stato = 'ANNULLATO'`), NON `attivo = false`.
--   ⛔ `attivo = false` sembra la strada ovvia e non basta: la SELECT di
--   fn_resolve_lotto_task_execution_mode non filtra su `attivo`, quindi il
--   rilancio continuerebbe a saltare i task. Lo dice per iscritto la sorella
--   fn_riporta_lotto_a_draft nel proprio corpo, che questa funzione imita.
--   ⚠️ E `attivo` risponde gia' a una domanda sua — «questo e' il tentativo
--   valido». Caricarlo anche di «il lotto non e' piu' in lavorazione» sono due
--   domande su un flag solo: finche' concordano non si vede niente, e il
--   giorno che dissentono non c'e' scritto da nessuna parte quale vince.
--   ⇒ Per questo il 6 asserisce ANCHE che i run restano `attivo = t`.
--
-- ⭐⭐ IL SOGGETTO SI FABBRICA, NON SI CERCA — e lo si e' pagato.
--   La prima stesura sceglieva un lotto reale annullabile con corse aperte, e
--   se non lo trovava saltava. Provata il 2026-09-04: su questo database non
--   ce n'era NESSUNO — i due lotti del collaudo erano uno gia' annullato e uno
--   gia' riportato in bozza — e il file passava saltando SEI asserzioni su
--   sette. Verde, e muto: esattamente la forma del verde per sottrazione, che
--   su un database ricostruito da zero (cioe' in CI) sarebbe la norma e non
--   l'eccezione.
--   ⇒ Ora lotto, corsa ed errore si costruiscono con le PRIMITIVE VERE —
--   fn_get_or_create_lotto, fn_start_lotto_task_run, fn_fail_lotto_task_run —
--   dentro BEGIN/ROLLBACK. Nascono con lo stato e i riferimenti del giro
--   reale, e il file misura le stesse cose ovunque giri.
--   ⛔ Non con INSERT a mano: proverebbero la mia idea delle tabelle, non la
--   riga che la pipeline produce davvero.
-- ------------------------------------------------------------
-- Indice test
-- 1) La funzione esiste e restituisce i CINQUE contatori
-- 2) Fixture: un lotto annullabile con almeno una corsa da chiudere
-- 3) Il caso e' costruito: una corsa del lotto e' in ERRORE e attiva
-- 4) L'annullo gira e DICE quante corse ha chiuso
-- 5) Nessuna corsa del lotto resta in ERRORE: task_err non ha piu' materia
-- 6) 🔴 Le corse sono chiuse PER ESITO, e restano `attivo = t`
-- 7) La vista degli errori vivi non mostra piu' il lotto
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- ============================================================
-- 1) Strutturale (gira sempre)
-- ============================================================
-- Cinque e non quattro: `annullati_task_run` ha un nome suo perche' senza un
-- numero proprio «ho chiuso le corse» non si distingue da «non c'era niente da
-- chiudere». E' lo stesso contatore che la sorella restituisce gia'.
-- ⚠️ Si guardano i NOMI, non il conteggio: una sesta colonna domani non deve
-- far diventare rosso questo test, una colonna rinominata si'.
SELECT ok(
  (SELECT count(*) FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'fn_annulla_lotto_da_draft'
      AND pg_get_function_result(p.oid) ILIKE '%annullati_task_run%'
      AND pg_get_function_result(p.oid) ILIKE '%deleted_fatture%'
      AND pg_get_function_result(p.oid) ILIKE '%updated_attivita%') = 1,
  '1) La funzione esiste e restituisce i cinque contatori');

-- ============================================================
-- Fixture
-- ============================================================
-- ⭐⭐ IL SOGGETTO SI FABBRICA, NON SI CERCA.
--   La prima stesura sceglieva un lotto reale annullabile con corse aperte.
--   Misurato il 2026-09-04: su questo database non ce n'era NESSUNO — i due
--   lotti del collaudo erano uno gia' annullato e uno gia' riportato in bozza
--   — e il file passava saltando sei asserzioni su sette. Verde, e muto.
--   ⇒ Il lotto e la sua corsa si costruiscono con le PRIMITIVE VERE
--   (fn_get_or_create_lotto, fn_start_lotto_task_run, fn_fail_lotto_task_run),
--   cosi' nascono con lo stato e i riferimenti che avrebbero nel giro reale e
--   il test non dipende piu' da cosa c'e' in tabella. Su un database
--   ricostruito da zero misura le stesse cose.
--   ⚠️ La competenza e' spostata nel futuro per non incrociare i lotti veri
--   ne' la fixture del test «annulla lotto vuoto», che usa +2 mesi.
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba) e l'emittente e' quello di chi agisce
--   (script.fn_pgtap_emittente_sr_operatore). Prima utility ed emittente si
--   pescavano dal primo BA e dalla prima fattura: da zero non c'erano.
CREATE TEMP TABLE tmp_cli_ann AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('annulla lotto task runs');

CREATE TEMP TABLE tmp_lotto_ann AS
SELECT vendite.fn_get_or_create_lotto(
         p_competenza_mese             => (date_trunc('month', script.fn_data_operativa()) + interval '4 month')::date,
         p_tipo_doc_fiscale_id         => (SELECT id FROM config.tipi_doc_fiscale
                                            WHERE attivo IS TRUE ORDER BY id LIMIT 1),
         p_utility_id                  => (SELECT utility_id FROM tmp_cli_ann),
         p_emittente_soggetto_ruolo_id => script.fn_pgtap_emittente_sr_operatore(),
         p_tipo_lotto                  => 'MASSIVO') AS id;

-- La corsa: aperta con la primitiva della pipeline, non con un INSERT a mano.
-- Un INSERT proverebbe la mia idea della tabella, non la riga che il giro
-- reale produce.
CREATE TEMP TABLE tmp_runs_ann AS
SELECT r.task_run_id AS id
  FROM vendite.fn_start_lotto_task_run(
         p_lotto_id             => (SELECT id FROM tmp_lotto_ann),
         p_pipeline_id          => (SELECT p.id FROM vendite.fatturazione_pipeline p
                                     ORDER BY p.id LIMIT 1),
         p_stato_doc_fiscale_id => (SELECT fl.stato_doc_fiscale_id
                                      FROM vendite.fatturazione_lotti fl
                                     WHERE fl.id = (SELECT id FROM tmp_lotto_ann)),
         p_task_code            => 'pull_attivita_da_commessa') AS r;

SELECT ok(
  (SELECT count(*) FROM tmp_runs_ann) > 0
  AND script.fn_check_lotto_annullabile((SELECT id FROM tmp_lotto_ann)) = '[]'::jsonb,
  '2) Fixture: un lotto annullabile con almeno una corsa da chiudere');

-- ============================================================
-- 3) Il caso si COSTRUISCE
-- ============================================================
-- La corsa va in ERRORE con la primitiva della pipeline, non con un UPDATE a
-- mano: e' cosi' che il giro reale la chiude, ed e' il codice che il collaudo
-- ha visto (E_PULL_COMMESSA, esito parziale del pull).
SELECT vendite.fn_fail_lotto_task_run(
         (SELECT id FROM tmp_runs_ann),
         'E_PULL_COMMESSA',
         'Pull attivita'' completato con 1 commesse su 3 in errore');

SELECT ok(
  (SELECT count(*) FROM vendite.fatturazione_lotti_task_runs r
    WHERE r.lotto_id = (SELECT id FROM tmp_lotto_ann)
      AND r.task_stato = 'ERRORE'
      AND r.attivo IS TRUE) > 0,
  '3) Il caso e costruito: una corsa del lotto e in ERRORE e attiva');

-- Prima dell'annullo: il lotto si vede fra gli errori vivi? Dipende dallo
-- SCOPE EMITTENTE del contesto pgTAP, non dal difetto — si fotografa qui per
-- poterlo dire al test 7 invece di confondere un fail-closed con un successo.
CREATE TEMP TABLE tmp_evento_prima AS
SELECT count(*) AS n
  FROM vendite.vw_dash_competenza_errori v
 WHERE v.lotto_id = (SELECT id FROM tmp_lotto_ann)
   AND v.tipo_evento = 'TASK_ERRORE';

-- ============================================================
-- 4) L'annullo
-- ============================================================
-- ⚠️ La chiamata sta in un DO e il risultato in una temp table: l'asserzione
--   dopo LEGGE, non esegue. Una funzione che scrive dentro l'espressione di
--   una CASE renderebbe l'ordine delle scritture un dettaglio del planner.
CREATE TEMP TABLE tmp_esito_ann (
    updated_lotti      integer,
    updated_attivita   integer,
    deleted_fatture    integer,
    deleted_righe      integer,
    annullati_task_run integer
);

DO $annullo$
DECLARE
    v_lotto vendite.fatturazione_lotti.id%TYPE;
BEGIN
    SELECT id INTO v_lotto FROM tmp_lotto_ann;
    IF v_lotto IS NULL THEN RETURN; END IF;

    INSERT INTO tmp_esito_ann
    SELECT * FROM vendite.fn_annulla_lotto_da_draft(v_lotto);
END
$annullo$;

SELECT CASE
  WHEN TRUE THEN ok(
    (SELECT annullati_task_run FROM tmp_esito_ann) >= (SELECT count(*) FROM tmp_runs_ann),
    '4) L annullo gira e DICE quante corse ha chiuso')
END;

-- ============================================================
-- 5) La bandiera si abbassa
-- ============================================================
-- E' il predicato di `task_err` senza lo scope emittente: se nessuna corsa del
-- lotto resta in ERRORE e attiva, la vista non ha piu' materia da mostrare —
-- e questo si verifica anche dove lo scope del contesto pgTAP non arriva.
SELECT CASE
  WHEN TRUE THEN ok(
    (SELECT count(*) FROM vendite.fatturazione_lotti_task_runs r
      WHERE r.lotto_id = (SELECT id FROM tmp_lotto_ann)
        AND r.task_stato = 'ERRORE'
        AND r.attivo IS TRUE) = 0,
    '5) Nessuna corsa del lotto resta in ERRORE: task_err non ha piu materia')
END;

-- ============================================================
-- 6) 🔴 IL COME: per ESITO, e senza toccare `attivo`
-- ============================================================
-- Le due meta' di questa asserzione dicono cose diverse e servono entrambe:
--   - tutte ad ANNULLATO  -> la leva usata e' l'ESITO, quella che il rilancio
--     legge (fn_resolve_lotto_task_execution_mode: ANNULLATO -> RUN);
--   - tutte ancora attivo -> NON e' stato usato `attivo`, che risponde a
--     un'altra domanda e non basterebbe comunque.
-- ⛔ Senza la seconda meta', una riscrittura che spegnesse `attivo` invece di
--   scrivere l'esito passerebbe il test 5 e romperebbe il rilancio.
SELECT CASE
  WHEN TRUE THEN ok(
    (SELECT count(*) FROM vendite.fatturazione_lotti_task_runs r
      WHERE r.id IN (SELECT id FROM tmp_runs_ann)
        AND r.task_stato IS DISTINCT FROM 'ANNULLATO') = 0
    AND
    (SELECT count(*) FROM vendite.fatturazione_lotti_task_runs r
      WHERE r.id IN (SELECT id FROM tmp_runs_ann)
        AND r.attivo IS NOT TRUE) = 0,
    '6) Le corse sono chiuse PER ESITO (ANNULLATO) e restano attivo = t')
END;

-- ============================================================
-- 7) La vista
-- ============================================================
-- ⚠️ Salta se il contesto pgTAP non vedeva il lotto NEMMENO PRIMA: la vista
--   filtra sullo scope emittente di app.current_user_id, e uno zero da
--   scope e' fail-closed, non una bandiera abbassata. Confonderli farebbe
--   passare questo test anche a difetto intatto.
SELECT CASE
  WHEN (SELECT n FROM tmp_evento_prima) = 0
    THEN skip('il contesto pgTAP non vede questo lotto nella vista (scope emittente): lo zero sarebbe fail-closed', 1)
  ELSE ok(
    (SELECT count(*) FROM vendite.vw_dash_competenza_errori v
      WHERE v.lotto_id = (SELECT id FROM tmp_lotto_ann)
        AND v.tipo_evento = 'TASK_ERRORE') = 0,
    '7) La vista degli errori vivi non mostra piu il lotto')
END;

SELECT * FROM finish();
ROLLBACK;
