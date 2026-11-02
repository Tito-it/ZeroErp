-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.vw_dash_commesse_respinte — una riga per commessa respinta
-- Piano: brief-residuo-fatturabili-e-bandiere-esito-parziale, sezioni 4 e 9 (D3)
-- ------------------------------------------------------------
-- Cosa presidia questo file
--   La richiesta di Tid del 2026-09-04: «le commesse in errore devono vedersi
--   TUTTE, e ognuna mostrare il problema, per poter cercare di risolvere».
--
-- 🔴 IL TEST CHE VALE DI PIU' E' IL 4, ed e' l'unica ragione per cui questa
--   vista legge il log invece del `meta` del task run.
--   `pipeline_step_executor` scrive nel meta
--       "commesse_fallite": [e.item for e in esito.errori][:5]
--   cioe' TRONCA A CINQUE. Con sei commesse respinte una vista costruita sul
--   meta ne mostrerebbe cinque, e la sesta sparirebbe **senza che niente lo
--   dica** — che e' esattamente la forma del difetto che questo brief racconta.
--   ⇒ Il test costruisce SEI respinte e pretende di vederle tutte e sei. Se un
--   domani qualcuno «semplificasse» la vista puntandola al meta, questo test
--   diventa rosso — ed e' il solo posto in cui quella scelta e' presidiata.
--
-- ⚠️ IL 5 PRESIDIA L'AGGANCIO, e sembra pedanteria finche' non serve.
--   Il `commessa_id` si legge da `meta->'context'->>'commessa_id'`, non dal
--   numero dentro la frase «Errore emissione commessa 34137». Il messaggio e'
--   prosa: cambia quando qualcuno lo riscrive meglio, e un aggancio sul testo
--   si rompe in silenzio. Il test fabbrica una riga col numero SOLO nella
--   frase e pretende che la vista NON la elenchi.
--
-- ⭐ IL SOGGETTO SI FABBRICA, NON SI CERCA: lotto con la primitiva vera,
--   righe di log costruite qui. Su un database ricostruito da zero il file
--   misura le stesse cose, invece di saltare.
-- ------------------------------------------------------------
-- Indice test
-- 1) La vista esiste ed e' security_invoker
-- 2) Il pannello errori porta l'elenco, e la GRANA non e' cambiata
-- 3) Fixture: sei commesse respinte su un lotto
-- 4) 🔴 La vista le elenca TUTTE E SEI (il meta ne porterebbe cinque)
-- 5) ⚠️ L'aggancio e' per CHIAVE: il numero nella sola frase non basta
-- 6) Fail-closed: senza contesto la vista e' vuota
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ============================================================
-- 1-2) Strutturali
-- ============================================================
SELECT ok(
  (SELECT count(*) FROM pg_class c
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname = 'vw_dash_commesse_respinte'
      AND c.relkind = 'v'
      AND array_to_string(c.reloptions, ',') ILIKE '%security_invoker%') = 1,
  '1) La vista esiste ed e security_invoker');

-- ⭐ La grana del pannello errori NON deve cambiare: e' la promessa fatta al
--   badge del calendario. Le due colonne sono IN CODA, e una riga resta un
--   evento. Se un domani qualcuno la trasformasse in una riga per commessa,
--   il conteggio del mese cambierebbe significato senza che nessuno lo decida.
SELECT ok(
  (SELECT count(*) FROM information_schema.columns
    WHERE table_schema = 'vendite' AND table_name = 'vw_dash_competenza_errori'
      AND column_name IN ('commesse_fallite', 'n_commesse_fallite')) = 2,
  '2) Il pannello errori porta lelenco e il conteggio');

-- ============================================================
-- Fixture — sei respinte, costruite
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba) e l'emittente e' quello di chi agisce
--   (script.fn_pgtap_emittente_sr_operatore). Prima utility ed emittente si
--   pescavano dal primo BA e dalla prima fattura: da zero non c'erano.
CREATE TEMP TABLE tmp_cli_resp AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('dash commesse respinte');

CREATE TEMP TABLE tmp_lotto_resp AS
SELECT vendite.fn_get_or_create_lotto(
         p_competenza_mese             => (date_trunc('month', script.fn_data_operativa()) + interval '5 month')::date,
         p_tipo_doc_fiscale_id         => (SELECT id FROM config.tipi_doc_fiscale
                                            WHERE attivo IS TRUE ORDER BY id LIMIT 1),
         p_utility_id                  => (SELECT utility_id FROM tmp_cli_resp),
         p_emittente_soggetto_ruolo_id => script.fn_pgtap_emittente_sr_operatore(),
         p_tipo_lotto                  => 'MASSIVO') AS id;

-- Sei commesse vere, per avere un `commessa_codice` che non sia NULL.
-- rev 2026-10-27 (lotto 4 di D7): le sei commesse si COSTRUISCONO
--   (dbops.fn_pgtap_crea_commessa, sul cliente qui sopra): prima erano le
--   prime sei del DB, e da zero non ce n'era nessuna.
CREATE TEMP TABLE tmp_commesse_resp AS
SELECT c.commessa_id AS id, g.n
  FROM generate_series(1, 6) AS g(n)
  CROSS JOIN LATERAL dbops.fn_pgtap_crea_commessa(
                       'commessa respinta ' || g.n, NULL,
                       (SELECT billing_account_id FROM tmp_cli_resp)) c;

-- Le righe di log: e' la forma che `item_failed` scrive nel giro reale —
-- status 'C', il commessa_id nel `meta->'context'`, il codice in `meta`.
INSERT INTO vendite.fatturazione_lotti_log (lotto_id, messaggio, status, meta)
SELECT (SELECT id FROM tmp_lotto_resp),
       concat('Errore emissione commessa ', cr.id),
       'C',
       jsonb_build_object(
           'scope', 'LOTTO',
           'error_code', 'E_PULL_COMMESSA',
           'detail', concat('Errore emit commessa_id=', cr.id, ': fixture pgTAP'),
           'context', jsonb_build_object('task', 'pull_attivita_da_commessa',
                                         'commessa_id', cr.id))
  FROM tmp_commesse_resp cr;

SELECT ok(
  (SELECT count(*) FROM tmp_commesse_resp) = 6,
  '3) Fixture: sei commesse respinte su un lotto');

-- ============================================================
-- 4) 🔴 TUTTE E SEI
-- ============================================================
-- Il numero non e' decorativo: cinque sarebbe il conteggio di una vista
-- costruita sul `meta` troncato. Sei e' il conteggio di una vista costruita
-- sul log. Se domani il file torna a dire cinque, qualcuno ha cambiato
-- sorgente senza accorgersene.
SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_commesse_respinte v
    WHERE v.lotto_id = (SELECT id FROM tmp_lotto_resp)),
  6,
  '4) La vista elenca TUTTE E SEI le commesse respinte');

-- ============================================================
-- 5) ⚠️ L'aggancio e' per CHIAVE, non per testo
-- ============================================================
-- Una riga che porta il numero SOLO nella frase — `meta->'context'` senza
-- `commessa_id` — non ha una chiave: non deve comparire. Se comparisse
-- vorrebbe dire che qualcuno sta leggendo la prosa.
INSERT INTO vendite.fatturazione_lotti_log (lotto_id, messaggio, status, meta)
VALUES ((SELECT id FROM tmp_lotto_resp),
        'Errore emissione commessa 999999',
        'C',
        jsonb_build_object('scope', 'LOTTO', 'error_code', 'E_PULL_COMMESSA',
                           'context', jsonb_build_object('task', 'pull_attivita_da_commessa')));

SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_commesse_respinte v
    WHERE v.lotto_id = (SELECT id FROM tmp_lotto_resp)),
  6,
  '5) Il numero nella sola frase non entra: laggancio e per chiave');

-- ============================================================
-- 6) Fail-closed
-- ============================================================
-- ⚠️ Che svuotare la GUC sia fail-closed NON e' scontato e va provato, non
--   dato per buono: `fn_get_emittenti_scope_sr_ids(NULL)` risponde con un
--   array VUOTO (nessun emittente), mentre risponde NULL — cioe' «nessuna
--   restrizione» — per chi ha lo scope pieno. Se un giorno rispondesse NULL
--   anche senza utente, questa vista si aprirebbe a tutti in silenzio.
--   In fondo al file perche' da qui in poi il contesto e' spento.
SET LOCAL app.current_user_id = '';

SELECT is(
  (SELECT count(*)::integer FROM vendite.vw_dash_commesse_respinte),
  0,
  '6) Senza contesto la vista e vuota (fail-closed)');

SELECT * FROM finish();
ROLLBACK;
