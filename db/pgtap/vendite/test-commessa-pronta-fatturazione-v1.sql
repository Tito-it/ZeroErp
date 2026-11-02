-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la commessa si puo' dichiarare PRONTA_FATTURAZIONE a mano, e il
--       bottone dice la stessa cosa del guard.
--       script.fn_check_commessa_pronta_fatturazione
--       + script.fn_available_actions_commessa
--       + vendite.trgfn_commesse_guard_transizione
--       + vendite.vw_dash_competenza_attivita
--
-- Origine: brief-db-emittibilita-visibile-e-sbloccabile.md §3.4 (casi 1..5).
--
-- Indice test (1..7):
--   1. Preflight fixture: esiste una commessa da cui copiare i riferimenti
--   2. Commessa BOZZA CON righe pronte -> azione rendi_pronta ABILITATA
--   3. Commessa BOZZA SENZA righe pronte -> azione presente ma DISABILITATA,
--      col motivo scritto (non solo il fatto)
--   4. Guard e capability danno lo STESSO verdetto sullo stesso documento
--      ** e' l'invariante del §3.4 caso 4 del brief **
--   5. Vista: una commessa bloccata compare comunque, marcata
--      commessa_emittibile = false (segnalare, non nascondere)
--   6. La transizione, quando il check e' pulito, passa davvero
--   7. La transizione, quando il check non e' pulito, viene RIFIUTATA
--
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): la porta sulla
--   commessa rifiuta l'UPDATE diretto dello stato. I test 6 e 7 passano dal verbo
--   vendite.fn_cambia_stato_commessa, con l'azione cambia_stato_commessa
--   all'utente del contesto (il file prova la regola delle righe pronte, non il
--   permesso).
-- ⚠️ Attesa precisata: test 7 da throws_ok sul solo P0001 a throws_like sulla
--   frase di E_COMMESSA_NESSUNA_RIGA_APPROVATA: col solo P0001 sarebbe verde
--   anche per la porta o per il permesso, cioe' per la ragione sbagliata.
-- FIXTURE COSTRUITA, NON PESCATA. Le due commesse di prova nascono qui dentro
-- dai builder dbops (rev 2026-10-27, lotto 4 di D7: prima copiavano i
-- riferimenti di una commessa esistente, che da zero non c'era): cosi' i sei
-- casi valgono anche su un database appena creato, e non passano in silenzio
-- per assenza di dati. Il preflight fallisce forte se la riga di A non e'
-- tipizzata.
--
-- IMPORTANTE: nessun SAVEPOINT/ROLLBACK TO SAVEPOINT (rompe state pgTAP).
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

SELECT plan(7);

-- vw_dash_competenza_attivita filtra per scope emittente leggendo la GUC
-- app.current_user_id. rev 2026-10-27 (lotto 4 di D7): non si impersona piu'
-- «il primo super admin» di django.auth_user. Era una pesca anche quella:
-- sullo scratch non ce n'e' nessuno (la GUC restava vuota e il builder apriva
-- un mondo suo), su dev e' l'utente 1, che non ha un'azienda, e il builder si
-- ferma. Le commesse sono dell'azienda dell'operatore del test, e il suo scope
-- le vede: e' il contesto giusto.

-- ============================================================
-- Fixture
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): le due commesse si COSTRUISCONO
--   (dbops.fn_pgtap_crea_commessa, madre vendite.fn_get_or_create_commessa,
--   in BOZZA; la riga pronta di A da dbops.fn_pgtap_crea_commessa_attivita,
--   APPROVATA + NON_EMESSA). Prima copiavano BA, emittente e riga da una
--   commessa esistente pescata con LIMIT 1: su un database ricostruito da
--   zero non ce n'era nessuna. B riusa il cliente di A.
CREATE TEMP TABLE _fx_cm_a AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('pronta fatturazione A', NULL, NULL, true);

CREATE TEMP TABLE _fx_cm_b AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
    'pronta fatturazione B', NULL, (SELECT billing_account_id FROM _fx_cm_a), false);

CREATE TEMP TABLE _fx_src AS
SELECT a.commessa_id,
       a.billing_account_id,
       a.utility_id,
       a.emittente_soggetto_ruolo_id,
       ca.id           AS riga_id
  FROM _fx_cm_a a
  JOIN vendite.commesse_attivita ca ON ca.id = a.attivita_id
 WHERE ca.tipo_doc_fiscale_id IS NOT NULL;

SELECT ok(
    (SELECT count(*) FROM _fx_src) = 1,
    '1. Preflight: esiste almeno una commessa con una riga tipizzata da cui copiare i riferimenti'
);

CREATE TEMP TABLE _fx AS
SELECT (SELECT commessa_id FROM _fx_cm_a) AS com_a,
       (SELECT commessa_id FROM _fx_cm_b) AS com_b;

-- rev 2026-10-27 (lotto 4 di D7): l'azione cambia_stato_commessa si concede
--   QUI, prima dei test 2-4, non piu' prima del 6: da 20261026-35 /
--   20261027-47 fn_available_actions_commessa NASCONDE «rendi pronta» a chi
--   non ha l'azione (permesso => nascondi). Il file prova la regola delle
--   righe pronte, non il permesso (rev 2026-10-26 in testa).
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');

-- ============================================================
-- 2) BOZZA con righe pronte -> rendi_pronta abilitata
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM jsonb_array_elements(
                   script.fn_available_actions_commessa((SELECT com_a FROM _fx)) -> 'available_actions') a
         WHERE a->>'key' = 'rendi_pronta'
           AND (a->>'enabled')::boolean IS TRUE
    ),
    '2. Commessa BOZZA con righe pronte: azione rendi_pronta presente e abilitata'
);

-- ============================================================
-- 3) BOZZA senza righe -> azione presente, disabilitata, col motivo
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM jsonb_array_elements(
                   script.fn_available_actions_commessa((SELECT com_b FROM _fx)) -> 'available_actions') a
         WHERE a->>'key' = 'rendi_pronta'
           AND (a->>'enabled')::boolean IS FALSE
           AND jsonb_array_length(a->'reasons') > 0
           AND a->'reasons'->0->>'codice' = 'E_COMMESSA_NESSUNA_RIGA_APPROVATA'
    ),
    '3. Commessa BOZZA senza righe pronte: azione presente, disabilitata e col motivo scritto'
);

-- ============================================================
-- 4) INVARIANTE: guard e capability leggono lo stesso verdetto
--    Entrambi passano da fn_check_commessa_pronta_fatturazione: qui si
--    verifica che il "puo'" del bottone coincida con il "[]" della fn.
-- ============================================================
SELECT ok(
    (SELECT (a->>'enabled')::boolean
       FROM jsonb_array_elements(
                script.fn_available_actions_commessa((SELECT com_a FROM _fx)) -> 'available_actions') a
      WHERE a->>'key' = 'rendi_pronta')
    = (jsonb_array_length(script.fn_check_commessa_pronta_fatturazione((SELECT com_a FROM _fx))) = 0)
    AND
    (SELECT (a->>'enabled')::boolean
       FROM jsonb_array_elements(
                script.fn_available_actions_commessa((SELECT com_b FROM _fx)) -> 'available_actions') a
      WHERE a->>'key' = 'rendi_pronta')
    = (jsonb_array_length(script.fn_check_commessa_pronta_fatturazione((SELECT com_b FROM _fx))) = 0),
    '4. INVARIANTE: bottone e verdetto della fn coincidono su entrambe le commesse'
);

-- ============================================================
-- 5) La vista segnala, non nasconde: la commessa e' ancora BOZZA e le sue
--    righe DEVONO comparire, marcate come non emittibili.
-- ============================================================
SELECT is(
    (SELECT jsonb_build_object(
              'righe',       count(*),
              'emittibile',  bool_and(v.commessa_emittibile),
              -- rev 04-08-2026: era `commessa_stato_codice`. Rinominata in
              -- `_codice_interno` da 20260804-67: esporre codice_interno con
              -- un alias *_codice viola linee-guida-sql §6c e faceva fallire
              -- il guardrail di naming in CI.
              'stato',       min(v.commessa_stato_codice_interno))
       FROM vendite.vw_dash_competenza_attivita v
      WHERE v.commessa_id = (SELECT com_a FROM _fx)),
    jsonb_build_object('righe', 1, 'emittibile', false, 'stato', 'BOZZA'),
    '5. La vista mostra la riga della commessa bloccata, marcata commessa_emittibile = false'
);

-- ============================================================
-- 6) La transizione lecita passa e rende la commessa emittibile
-- ============================================================
SELECT * FROM vendite.fn_cambia_stato_commessa((SELECT com_a FROM _fx), 'PRONTA_FATTURAZIONE');

SELECT ok(
    (SELECT sc.codice_interno = 'PRONTA_FATTURAZIONE' AND sc.emittibile IS TRUE
       FROM vendite.commesse c
       JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
      WHERE c.id = (SELECT com_a FROM _fx)),
    '6. Transizione manuale eseguita: commessa PRONTA_FATTURAZIONE ed emittibile'
);

-- ============================================================
-- 7) La transizione non lecita viene rifiutata dal guard
-- ============================================================
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_commessa(%s, 'PRONTA_FATTURAZIONE')$$,
           (SELECT com_b FROM _fx)),
    '%impossibile passare a PRONTA_FATTURAZIONE senza almeno una riga approvata%',
    '7. Commessa senza righe pronte: il guard rifiuta il passaggio a PRONTA_FATTURAZIONE'
);

SELECT * FROM finish();
ROLLBACK;
