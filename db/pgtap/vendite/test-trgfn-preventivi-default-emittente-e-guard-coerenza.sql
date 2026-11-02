-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trg_preventivi_a10_default_emittente_ins (BEFORE INSERT) — dal
--   2026-09-15 esegue il building block script.trgfn_default_emittente_fiscale
--   ('SOLLEVA') al posto della copia vendite.trgfn_preventivi_default_emittente,
--   ritirata (brief-db-emittente-di-default-un-bb-solo, 20260915-38); il NOME
--   del trigger e' invariato, ed e' cio' che il test 1 asserisce.
--   +   vendite.trgfn_preventivi_guard_utility_istanza_coerenza
-- Riferimento brief preventivi rev2 (sessione 2026-05-01).
--
-- Indice test (1..6):
--    1. Trigger preflight: entrambi i trigger esistono
--    2. GUC valida (operatore con EF) + payload senza emittente
--       -> trigger valorizza emittente_fiscale_id
--    3. Payload con emittente esplicito + GUC valida
--       -> trigger NON sovrascrive
--    4. Coppia (istanza, utility) coerente -> INSERT ok (lives_ok)
--    5. GUC vuota + payload senza emittente -> P0001 E_EMITTENTE_NON_RISOLTO
--       (throws_like sulla FRASE: il codice di dominio E_PREV_EMITTENTE_NON_RISOLTO
--       e' ritirato con obsoleto_dal dal 2026-09-15)
--       ⭐ unico punto in cui svuotare app.current_user_id resta legittimo:
--          la GUC vuota e' il caso in prova, non una scorciatoia (nota al 5)
--    6. Coppia (istanza, utility) incoerente -> raise P0001
--
-- IMPORTANTE: nessun SAVEPOINT/ROLLBACK TO SAVEPOINT.
-- pgTAP traccia lo stato test in una temp table interna; un rollback
-- a savepoint cancellerebbe le righe di stato dei test gia' eseguiti
-- e finish() farebbe "No tests run!". Tutto in una sola tx con
-- ROLLBACK finale (BEGIN/ROLLBACK del file) ripulisce le manipolazioni.
--
-- Le GUC sono settate con is_local=true per scope tx (rollback puliro).
-- Ogni INSERT usa numero random per evitare collisioni UNIQUE
-- (uq_preventivi_numero_rev) tra i test successo.
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

SELECT plan(6);

SET LOCAL zeroerp.allow_lock_columns_override = 'on';

-- ============================================================
-- Setup: contesto comune
-- ============================================================
CREATE TEMP TABLE _t_stato AS
SELECT id AS stato_id FROM config.stati_doc_preventivi
 WHERE attivo = true ORDER BY id LIMIT 1;

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba: BA legato all'azienda di chi agisce);
--   l'utente e' l'operatore del contesto e il suo emittente quello di
--   script.fn_pgtap_emittente_operatore(). Prima si pescavano col primo id
--   un BA, un utente django con emittente e «il primo» emittente attivo: da
--   zero non c'era niente. Dal catalogo di seed resta solo lo stato.
--   ⚠️ Il 3 passa l'emittente dell'operatore, lo stesso del default: senza
--   una seconda azienda nel perimetro il «non sovrascrive» non si distingue
--   (lo stesso valeva quando si pescava il primo emittente).
CREATE TEMP TABLE _t_ba AS
SELECT c.billing_account_id AS ba_id, c.istanza_utility_id, c.utility_id
  FROM dbops.fn_pgtap_crea_cliente_ba('default emittente preventivi') c;

CREATE TEMP TABLE _t_user_with_ef AS
SELECT NULLIF(current_setting('app.current_user_id', true), '')::integer AS user_id,
       script.fn_pgtap_emittente_operatore() AS ef_id;

CREATE TEMP TABLE _t_ef AS
SELECT script.fn_pgtap_emittente_operatore() AS ef_id;

-- ============================================================
-- 1) Preflight: entrambi i trigger esistono.
--    Senza, gli altri test passerebbero come falsi positivi.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c   ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'preventivi'
           AND t.tgname IN (
               'trg_preventivi_a10_default_emittente_ins',
               'trg_preventivi_a10_guard_utility_istanza_coerenza_ins_upd'
           )
        GROUP BY 1 HAVING count(*) = 2
    ),
    '1. Entrambi i trigger (default_emittente, guard_coerenza) esistono'
);

-- ============================================================
-- 2) GUC valida + no emittente nel payload -> auto-fill
-- ============================================================
SELECT set_config('app.current_user_id',
                   (SELECT user_id::text FROM _t_user_with_ef),
                   true);

CREATE TEMP TABLE _t_t2_result AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, data, stato_doc_preventivo_id, billing_account_id,
    istanza_utility_id, utility_id
  )
  SELECT
    'PGT_T2_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    script.fn_data_operativa(),
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba)
  WHERE (SELECT user_id FROM _t_user_with_ef) IS NOT NULL
  RETURNING emittente_fiscale_id
)
SELECT emittente_fiscale_id FROM ins;

SELECT is(
  (SELECT emittente_fiscale_id FROM _t_t2_result),
  (SELECT ef_id FROM _t_user_with_ef),
  '2. GUC valida + payload senza emittente -> auto-fill da fn_resolve_emittente_for_user'
);

-- ============================================================
-- 3) Payload con emittente esplicito + GUC valida -> NON sovrascritto
-- ============================================================
CREATE TEMP TABLE _t_t3_result AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, data, stato_doc_preventivo_id, billing_account_id,
    istanza_utility_id, utility_id, emittente_fiscale_id
  )
  SELECT
    'PGT_T3_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    script.fn_data_operativa(),
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba),
    (SELECT ef_id FROM _t_ef)
  WHERE (SELECT ef_id FROM _t_ef) IS NOT NULL
  RETURNING emittente_fiscale_id
)
SELECT emittente_fiscale_id FROM ins;

SELECT is(
  (SELECT emittente_fiscale_id FROM _t_t3_result),
  (SELECT ef_id FROM _t_ef),
  '3. Payload con emittente esplicito -> trigger NON sovrascrive'
);

-- ============================================================
-- 4) Coppia (istanza, utility) coerente via BA -> INSERT ok
--    (combina trigger default_emittente + guard_coerenza in path felice)
-- ============================================================
SELECT lives_ok(
  format($SQL$
    INSERT INTO vendite.preventivi (
      numero, data, stato_doc_preventivo_id, billing_account_id,
      istanza_utility_id, utility_id
    ) VALUES (
      %L, script.fn_data_operativa(), %s, %s, %s, %s
    )
  $SQL$,
    'PGT_T4_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba)
  ),
  '4. Coppia coerente via BA + GUC valida -> INSERT ok'
);

-- ============================================================
-- 5) GUC vuota + payload senza emittente -> P0001
-- ============================================================
-- ⭐ 2026-09-04 — QUI SVUOTARE LA GUC RESTA GIUSTO, ed e' l'eccezione.
--   Negli altri file la GUC vuota era una scorciatoia per spegnere
--   `script.trgfn_guard_emittente_scope`, e la fase 6 di
--   `brief-db-processi-automatici-identita-e-perimetro` chiude quel ramo.
--   Qui invece la GUC vuota E' IL CASO IN PROVA: il trigger di default deve
--   rifiutare un preventivo di cui non sa dire l'emittente.
--
-- ⚠️ E regge dopo la fase 6 per una ragione fragile, che va detta: i trigger
--   `BEFORE ROW` scattano in ordine ALFABETICO, e su vendite.preventivi
--     trg_preventivi_a10_default_emittente_ins       <-- primo
--     trg_preventivi_a10_guard_emittente_scope_ins_upd
--   quindi il default alza `E_EMITTENTE_NON_RISOLTO` prima che il guard
--   di scope veda la riga. (Verificato su `pg_trigger`, non supposto; dal
--   2026-09-15 lo asserisce anche il test 8 di
--   script/test-trgfn-default-emittente-fiscale-v1 su ogni tabella montata.)
--   ⛔ Se qualcuno rinomina uno dei due, l'ordine si inverte e questo test
--   diventa rosso sull'ALTRO ERRORE — e lo DICE: dal 2026-09-15 la frase e'
--   asseribile (`throws_like`), perche' il messaggio del codice unico non
--   porta piu' il numero del documento nel `%s` (la diagnostica sta nel
--   context, non a video). Entrambi restano `P0001`: la frase distingue.
SELECT set_config('app.current_user_id', '', true);

SELECT throws_like(
  format($SQL$
    INSERT INTO vendite.preventivi (
      numero, data, stato_doc_preventivo_id, billing_account_id,
      istanza_utility_id, utility_id
    ) VALUES (
      %L, script.fn_data_operativa(), %s, %s, %s, %s
    )
  $SQL$,
    'PGT_T5_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba)
  ),
  'Nessun emittente fiscale attivo%',
  '5. GUC vuota + payload senza emittente -> P0001 E_EMITTENTE_NON_RISOLTO (frase del codice unico)'
);

-- Ripristino GUC valida per test 6 (ha bisogno di emittente per arrivare al guard)
SELECT set_config('app.current_user_id',
                   (SELECT user_id::text FROM _t_user_with_ef),
                   true);

-- ============================================================
-- 6) Coppia (istanza, utility=9999) incoerente -> P0001
-- ============================================================
SELECT throws_ok(
  format($SQL$
    INSERT INTO vendite.preventivi (
      numero, data, stato_doc_preventivo_id, billing_account_id,
      istanza_utility_id, utility_id
    ) VALUES (
      %L, script.fn_data_operativa(), %s, %s, %s, 9999
    )
  $SQL$,
    'PGT_T6_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba)
  ),
  'P0001',
  NULL,
  '6. Coppia (istanza, utility=9999) incoerente -> P0001 (E_PREV_UTILITY_ISTANZA_INCOERENTE)'
);

SELECT * FROM finish();
ROLLBACK;
