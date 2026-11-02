-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.event_log + vendite.fn_log_event
--
-- ⚠️ ADEGUATO IL 2026-08-22 (L1 del Passo 0 osservabilita').
--   Tre cose sono cambiate sotto questo test, e ognuna lo avrebbe reso rosso:
--
--   ⚠️ E dal lotto L4 (stesso giorno) la firma e' scesa ancora, a SEI: via
--   anche `p_domain`, perche' il dominio e' una proprieta' del CODICE evento
--   (config.eventi_dominio) e non un dato che il chiamante possa scegliere.
--   La colonna `domain` non esiste piu'.
--
--   1. `fn_log_event` e' passata da NOVE parametri a SETTE: `p_actor` e
--      `p_source` non esistono piu' — riempivano due colonne costanti
--      (`service:django` e `django` su 386 righe su 386), mentre «chi» era gia'
--      `user_insert`. Le colonne sono state rimosse con `20260822-40`.
--   2. `entity_id` non e' piu' un numero qualunque: il trigger
--      `trg_event_log_a10_deriva_scope_ins` DERIVA il perimetro dall'entita'
--      citata, e se quell'entita' non esiste **rifiuta la riga**. I vecchi
--      `123` e `456` scritti a mano non sono piu' scrivibili, ed e' il
--      comportamento voluto: un evento che non si lega a niente non entra.
--   3. `entity_type` ha un vocabolario (`chk_event_log_entity_type`).
--
--   Le fixture usano quindi entita' REALI dell'emittente dell'operatore.
--
-- ⚠️ Il perimetro, l'identita' e la scadenza NON si verificano qui: hanno un
--   file loro, `test-event-log-deriva-scope.sql`. E i rami della retention
--   stanno in `test-event-log-append-only.sql`. Qui resta il contratto della
--   FUNZIONE: esiste, scrive, applica i default, e non aggira il CHECK.
--
-- Indice test (1..8):
-- 1) tabella event_log presente
-- 2) funzione fn_log_event presente (firma a SEI parametri)
-- 3) insert base via fn_log_event -> id valorizzato
-- 4) evento base persistito correttamente
-- 5) severity default = INFO quando NULL
-- 6) payload default = {} quando NULL
-- 7) severity invalida bloccata dal CHECK
-- 8) append-only: UPDATE bloccato
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

SELECT plan(8);

SELECT ok(
    to_regclass('vendite.event_log') IS NOT NULL,
    'tabella event_log presente'
  );

-- ⚠️ Non basta «la funzione esiste»: dal 2026-08-22 esiste con SEI parametri, e
--   le due firme precedenti (nove, poi sette) sono state DROPpate apposta —
--   due firme con DEFAULT rendono ambigua ogni chiamata. Qui si asserisce
--   l'identita' esatta, che e' l'unico modo di accorgersene.
SELECT is(
    (SELECT pg_get_function_identity_arguments(p.oid)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname = 'fn_log_event'),
    'p_entity_type text, p_entity_id bigint, p_event_code text, '
    || 'p_severity text, p_correlation_id uuid, p_payload jsonb',
    'funzione fn_log_event presente, e con la firma a SEI parametri'
  );

-- ============================================================
-- Fixture: entita' REALI dell'emittente dell'operatore.
-- ⚠️ Una scelta sola, proiettata da temp table: due sotto-select indipendenti
--   potrebbero pescare righe diverse.
-- ============================================================
CREATE TEMP TABLE tmp_event_log_rif AS
SELECT
    (SELECT l.id FROM vendite.fatturazione_lotti l
      WHERE l.emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()
      ORDER BY l.id LIMIT 1)  AS lotto_id,
    (SELECT c.id FROM vendite.commesse c
      WHERE c.emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()
      ORDER BY c.id LIMIT 1)  AS commessa_id;

CREATE TEMP TABLE tmp_event_log_base AS
SELECT vendite.fn_log_event(
    p_entity_type    => 'LOTTO',
    p_entity_id      => r.lotto_id,
    p_event_code     => 'STEP_STARTED',
    p_severity       => 'INFO',
    p_correlation_id => NULL::uuid,
    p_payload        => jsonb_build_object('step', 'DRAFT')
  ) AS event_id
FROM tmp_event_log_rif r
WHERE r.lotto_id IS NOT NULL;

SELECT CASE
    WHEN (SELECT lotto_id FROM tmp_event_log_rif) IS NULL
      THEN skip('nessun lotto dell''emittente dell''operatore: fixture non costruibile', 1)
    ELSE ok(
        (SELECT event_id IS NOT NULL FROM tmp_event_log_base),
        'insert base via fn_log_event -> id valorizzato'
    )
END;

SELECT CASE
    WHEN (SELECT lotto_id FROM tmp_event_log_rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE ok(
        EXISTS (
          SELECT 1
          FROM vendite.event_log e
          WHERE e.id = (SELECT event_id FROM tmp_event_log_base)
            AND e.entity_type = 'LOTTO'
            AND e.entity_id   = (SELECT lotto_id FROM tmp_event_log_rif)
            AND e.event_code  = 'STEP_STARTED'
            AND e.severity    = 'INFO'
            AND e.payload->>'step' = 'DRAFT'
        ),
        'evento base persistito correttamente'
    )
END;

CREATE TEMP TABLE tmp_event_log_defaults AS
SELECT vendite.fn_log_event(
    p_entity_type    => 'COMMESSA',
    p_entity_id      => r.commessa_id,
    -- ⚠️ Un codice che il giornale scrive DAVVERO: PUSH_COMPLETED e' uscito
    --   da event_log con la D-3 (un giro non ha padrone) ed e' tornato su
    --   commesse_push_log. Usarlo qui sarebbe collaudare con un codice che
    --   il catalogo non conosce piu'.
    p_event_code     => 'EMITTIBILITA_FALLITA',
    p_severity       => NULL,
    p_correlation_id => NULL::uuid,
    p_payload        => NULL
  ) AS event_id
FROM tmp_event_log_rif r
WHERE r.commessa_id IS NOT NULL;

SELECT CASE
    WHEN (SELECT commessa_id FROM tmp_event_log_rif) IS NULL
      THEN skip('nessuna commessa dell''emittente dell''operatore', 1)
    ELSE is(
        (SELECT e.severity FROM vendite.event_log e
          WHERE e.id = (SELECT event_id FROM tmp_event_log_defaults)),
        'INFO'::text,
        'severity default = INFO quando NULL'
    )
END;

SELECT CASE
    WHEN (SELECT commessa_id FROM tmp_event_log_rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE is(
        (SELECT e.payload FROM vendite.event_log e
          WHERE e.id = (SELECT event_id FROM tmp_event_log_defaults)),
        '{}'::jsonb,
        'payload default = {} quando NULL'
    )
END;

-- ⚠️ Per arrivare al CHECK serve un'entita' VERA: i BEFORE ROW girano prima dei
--   CHECK, e con un `entity_id` inesistente si verrebbe fermati dal trigger di
--   derivazione (P0001) senza mai toccare il vincolo che si voleva collaudare.
SELECT CASE
    WHEN (SELECT lotto_id FROM tmp_event_log_rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE throws_ok(
        format(
            'SELECT vendite.fn_log_event(%L, %s, %L, %L, NULL::uuid, %L::jsonb)',
            'LOTTO', (SELECT lotto_id FROM tmp_event_log_rif),
            'STEP_FAILED', 'KO', '{}'
        ),
        '23514',
        NULL,
        'severity invalida bloccata dal CHECK'
    )
END;

-- ⚠️ Il resto dell'append-only — DELETE su riga viva, DELETE su riga scaduta,
--   GUC di manutenzione — sta in test-event-log-append-only.sql. Qui resta
--   l'invariante piu' semplice, perche' e' quella che questo file dichiara.
SELECT CASE
    WHEN (SELECT lotto_id FROM tmp_event_log_rif) IS NULL
      THEN skip('fixture non costruibile', 1)
    ELSE throws_ok(
        format(
            'UPDATE vendite.event_log SET event_code = ''MUTATED'' WHERE id = %s',
            (SELECT event_id FROM tmp_event_log_base)
        ),
        'P0001',
        NULL,
        'append-only: UPDATE bloccato'
    )
END;

SELECT *
FROM finish();
ROLLBACK;
