-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
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
-- FIXTURE COSTRUITA, NON PESCATA. Le due commesse di prova nascono qui dentro
-- copiando i riferimenti di una commessa esistente (billing account, utility,
-- emittente): cosi' i sei casi valgono anche su un database appena creato, e
-- non passano in silenzio per assenza di dati. Il preflight fallisce forte se
-- manca il minimo indispensabile.
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
-- app.current_user_id: senza, fn_get_emittenti_scope_sr_ids risponde '{}' e la
-- vista non mostra NULLA. Si impersona un super admin (scope = tutto), che e'
-- il contesto in cui la dashboard viene guardata davvero.
DO $$
DECLARE v_sa integer;
BEGIN
  SELECT au.id INTO v_sa
    FROM django.auth_user au
   WHERE au.is_active AND script.fn_is_super_admin(au.id)
   ORDER BY au.id LIMIT 1;
  PERFORM set_config('app.current_user_id', coalesce(v_sa::text, ''), true);
END $$;

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _fx_src AS
SELECT c.id            AS commessa_id,
       c.billing_account_id,
       c.utility_id,
       c.emittente_soggetto_ruolo_id,
       ca.id           AS riga_id
  FROM vendite.commesse c
  JOIN vendite.commesse_attivita ca ON ca.commessa_id = c.id
 WHERE ca.tipo_doc_fiscale_id IS NOT NULL
 ORDER BY c.id, ca.id
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _fx_src) = 1,
    '1. Preflight: esiste almeno una commessa con una riga tipizzata da cui copiare i riferimenti'
);

-- Commessa A: BOZZA, con una riga pronta (APPROVATA + NON_EMESSA + tipo_doc).
INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                              emittente_soggetto_ruolo_id, stato_commessa_id)
SELECT 'PGTAP-PRONTA-A', s.billing_account_id, s.utility_id,
       s.emittente_soggetto_ruolo_id,
       (SELECT id FROM vendite.stati_commessa WHERE codice_interno = 'BOZZA')
  FROM _fx_src s;

-- Commessa B: BOZZA, senza alcuna riga.
INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                              emittente_soggetto_ruolo_id, stato_commessa_id)
SELECT 'PGTAP-PRONTA-B', s.billing_account_id, s.utility_id,
       s.emittente_soggetto_ruolo_id,
       (SELECT id FROM vendite.stati_commessa WHERE codice_interno = 'BOZZA')
  FROM _fx_src s;

CREATE TEMP TABLE _fx AS
SELECT (SELECT id FROM vendite.commesse WHERE codice = 'PGTAP-PRONTA-A') AS com_a,
       (SELECT id FROM vendite.commesse WHERE codice = 'PGTAP-PRONTA-B') AS com_b;

-- La riga di A: copia integrale di una riga reale, riagganciata alla commessa A
-- e forzata nello stato che il motore raccoglie.
INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    prezzo_snapshot, tipo_doc_fiscale_id, stato_approvazione, stato_emissione,
    sorgente_tipo_id, sorgente_uid)
-- La copia e' una riga NORMALE e ha una sorgente (vincolo 20261012-27): quella
-- della commessa di test, non la sorgente della riga reale (che puntando a un
-- documento vero ne riproietterebbe lo stato).
SELECT (SELECT com_a FROM _fx), ca.segment_key, ca.articolo_id, ca.istanza_utility_id,
       ca.data_attivita, ca.uom_id, ca.quantita, ca.competenza_mese,
       ca.competenza_dal, ca.competenza_al, ca.prezzo_snapshot,
       ca.tipo_doc_fiscale_id, 'APPROVATA', 'NON_EMESSA',
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
       (SELECT com_a FROM _fx)::text
  FROM vendite.commesse_attivita ca
 WHERE ca.id = (SELECT riga_id FROM _fx_src);

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
UPDATE vendite.commesse
   SET stato_commessa_id = (SELECT id FROM vendite.stati_commessa WHERE codice_interno = 'PRONTA_FATTURAZIONE')
 WHERE id = (SELECT com_a FROM _fx);

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
SELECT throws_ok(
    format($$UPDATE vendite.commesse
                SET stato_commessa_id = (SELECT id FROM vendite.stati_commessa WHERE codice_interno = 'PRONTA_FATTURAZIONE')
              WHERE id = %s$$, (SELECT com_b FROM _fx)),
    'P0001',
    NULL,
    '7. Commessa senza righe pronte: il guard rifiuta il passaggio a PRONTA_FATTURAZIONE'
);

SELECT * FROM finish();
ROLLBACK;
