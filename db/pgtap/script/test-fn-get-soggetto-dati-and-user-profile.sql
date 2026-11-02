-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_soggetto_dati_by_ruolo
--       script.fn_get_user_profile
--
-- Elenco test:
--  1) fn_get_soggetto_dati_by_ruolo: PF con ruolo restituisce record
--  2) fn_get_soggetto_dati_by_ruolo: soggetto_id corretto
--  3) fn_get_soggetto_dati_by_ruolo: tipo_ruolo risolto (codice_interno)
--  4) fn_get_soggetto_dati_by_ruolo: ragione_sociale_completa non nulla
--  5) fn_get_soggetto_dati_by_ruolo: soggetto_attivo = true
--  6) fn_get_soggetto_dati_by_ruolo: tipo_soggetto_id risolto
--  7) fn_get_soggetto_dati_by_ruolo: ID inesistente → nessun record
--  8) fn_get_soggetto_dati_by_ruolo: NULL → errore
--  9) fn_get_soggetto_dati_by_ruolo: 0 → errore
-- 10) fn_get_soggetto_dati_by_ruolo: emittente con dati societari → has_dati_societari = true
-- 11) fn_get_soggetto_dati_by_ruolo: emittente → dati_societari_id non nullo
-- 12) fn_get_soggetto_dati_by_ruolo: PF senza dati societari → has_dati_societari = false
-- 13) fn_get_user_profile: profilo completo restituisce JSONB non nullo
-- 14) fn_get_user_profile: blocco utente contiene username
-- 15) fn_get_user_profile: blocco utente contiene auth_user_id
-- 16) fn_get_user_profile: ruolo_sistema presente
-- 17) fn_get_user_profile: blocco risorse_umane contiene risorsa_umana_id
-- 18) fn_get_user_profile: blocco risorse_umane contiene soggetto_ruolo_id
-- 19) fn_get_user_profile: blocco risorse_umane contiene qualifica_id
-- 20) fn_get_user_profile: blocco soggetto contiene soggetto_id
-- 21) fn_get_user_profile: blocco soggetto contiene ragione_sociale_completa
-- 22) fn_get_user_profile: blocco soggetto contiene tipo_ruolo_codice_interno
-- 23) fn_get_user_profile: blocco emittente presente (o null se nessun emittente)
-- 24) fn_get_user_profile: chiave permessi_oggetto presente nel JSONB
-- 25) fn_get_user_profile: auth_user_id inesistente → errore
-- 26) fn_get_user_profile: NULL → errore
-- 27) fn_get_user_profile: il blocco risorse_umane NON porta piu'
--     `risorse_umane_auth_user_id` (nome vecchio del ponte, portava l'id
--     dell'identita': tolta il 12-09-2026, 20_code/20260912-24)
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

SELECT plan(26);

-- ============================================================
-- 0. Setup: raccolta riferimenti da dati esistenti
-- ============================================================

-- ⛔ 2026-09-23: il contesto era «il primo operatore con identita' attiva e
--   risorsa umana attiva», PESCATO. Su un database ricostruito dai changelog
--   non ce n'e' nessuno — l'operatore della riga di contesto e' un utente
--   TECNICO, senza risorsa umana — e la fixture moriva su
--   «p_soggetto_ruolo_id obbligatorio». Ora l'operatore UMANO si costruisce,
--   dal percorso di produzione (fn_crea_operatore_v2, via il builder).
-- ⚠️ In DUE istruzioni, e non per stile: un JOIN nella stessa istruzione del
--   builder legge risorse_umane con la snapshot di PRIMA che il builder la
--   scrivesse, e la temp table nasce vuota.
CREATE TEMP TABLE tmp_operatore_umano AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('profilo utente');

CREATE TEMP TABLE tmp_profile_ctx AS
SELECT
    ou.auth_user_id       AS user_id,
    ou.identita_id,
    ou.risorsa_umana_id,
    ou.soggetto_ruolo_id,
    ou.soggetto_id,
    ru.qualifica_id,
    ru.unita_organizzativa_id
FROM tmp_operatore_umano ou
JOIN anagrafiche.risorse_umane ru ON ru.id = ou.risorsa_umana_id;

-- Contesto emittente: l'azienda di CHI AGISCE, derivata e non pescata
-- («il primo emittente attivo» coincide con lei solo finche' l'installazione
-- ne ha una). Ha dati societari per costruzione: e' una persona giuridica.
CREATE TEMP TABLE tmp_emittente_ctx AS
SELECT
    ef.id                AS emittente_id,
    ef.soggetto_ruolo_id AS ef_sr_id,
    sr.soggetto_id       AS ef_soggetto_id
FROM anagrafiche.emittenti_fiscali ef
JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
WHERE ef.id = script.fn_pgtap_emittente_operatore();

-- ============================================================
-- A. fn_get_soggetto_dati_by_ruolo — caso PF (risorsa umana)
-- ============================================================

-- 1) Restituisce almeno un record per un soggetto_ruolo_id valido
SELECT isnt(
    (SELECT soggetto_id FROM script.fn_get_soggetto_dati_by_ruolo(
        (SELECT soggetto_ruolo_id FROM tmp_profile_ctx)
    )),
    NULL::uuid,
    'fn_get_soggetto_dati_by_ruolo: PF con ruolo restituisce record'
);

-- 2) soggetto_id corrisponde
SELECT is(
    (SELECT soggetto_id FROM script.fn_get_soggetto_dati_by_ruolo(
        (SELECT soggetto_ruolo_id FROM tmp_profile_ctx)
    )),
    (SELECT soggetto_id FROM tmp_profile_ctx),
    'fn_get_soggetto_dati_by_ruolo: soggetto_id corretto'
);

-- 3) tipo_ruolo risolto (codice_interno non nullo)
SELECT isnt(
    (SELECT tipo_ruolo_codice_interno FROM script.fn_get_soggetto_dati_by_ruolo(
        (SELECT soggetto_ruolo_id FROM tmp_profile_ctx)
    )),
    NULL::varchar,
    'fn_get_soggetto_dati_by_ruolo: tipo_ruolo_codice_interno risolto'
);

-- 4) ragione_sociale_completa non nulla
SELECT isnt(
    (SELECT ragione_sociale_completa FROM script.fn_get_soggetto_dati_by_ruolo(
        (SELECT soggetto_ruolo_id FROM tmp_profile_ctx)
    )),
    NULL::text,
    'fn_get_soggetto_dati_by_ruolo: ragione_sociale_completa non nulla'
);

-- 5) soggetto_attivo = true
SELECT is(
    (SELECT soggetto_attivo FROM script.fn_get_soggetto_dati_by_ruolo(
        (SELECT soggetto_ruolo_id FROM tmp_profile_ctx)
    )),
    true,
    'fn_get_soggetto_dati_by_ruolo: soggetto_attivo = true'
);

-- 6) tipo_soggetto_id risolto (non nullo)
SELECT isnt(
    (SELECT tipo_soggetto_id FROM script.fn_get_soggetto_dati_by_ruolo(
        (SELECT soggetto_ruolo_id FROM tmp_profile_ctx)
    )),
    NULL::varchar,
    'fn_get_soggetto_dati_by_ruolo: tipo_soggetto_id risolto'
);

-- ============================================================
-- B. fn_get_soggetto_dati_by_ruolo — casi errore
-- ============================================================

-- 7) ID inesistente → nessun record (0 righe)
SELECT is(
    (SELECT COUNT(*) FROM script.fn_get_soggetto_dati_by_ruolo(99999999)),
    0::bigint,
    'fn_get_soggetto_dati_by_ruolo: ID inesistente → nessun record'
);

-- 8) NULL → errore 22023 (invalid_parameter_value)
SELECT throws_ok(
    'SELECT * FROM script.fn_get_soggetto_dati_by_ruolo(NULL::bigint)',
    '22023',
    'p_soggetto_ruolo_id obbligatorio e > 0 (ricevuto: NULL)',
    'fn_get_soggetto_dati_by_ruolo: NULL → errore'
);

-- 9) 0 → errore 22023 (invalid_parameter_value)
SELECT throws_ok(
    'SELECT * FROM script.fn_get_soggetto_dati_by_ruolo(0)',
    '22023',
    'p_soggetto_ruolo_id obbligatorio e > 0 (ricevuto: 0)',
    'fn_get_soggetto_dati_by_ruolo: 0 → errore'
);

-- ============================================================
-- C. fn_get_soggetto_dati_by_ruolo — emittente con dati societari
-- ============================================================

-- 10) Emittente con dati societari → has_dati_societari = true
SELECT is(
    (SELECT has_dati_societari FROM script.fn_get_soggetto_dati_by_ruolo(
        (SELECT ef_sr_id FROM tmp_emittente_ctx)
    )),
    true,
    'fn_get_soggetto_dati_by_ruolo: emittente → has_dati_societari = true'
);

-- 11) Emittente → dati_societari_id non nullo
SELECT isnt(
    (SELECT dati_societari_id FROM script.fn_get_soggetto_dati_by_ruolo(
        (SELECT ef_sr_id FROM tmp_emittente_ctx)
    )),
    NULL::bigint,
    'fn_get_soggetto_dati_by_ruolo: emittente → dati_societari_id non nullo'
);

-- 12) Soggetto senza dati societari → has_dati_societari = false
-- ⭐ La persona fisica dell'operatore costruito: dati societari non ne ha per
--   costruzione. Prima si PESCAVA «un soggetto_ruolo il cui soggetto non ha
--   dati societari», cioe' si misurava la popolazione invece del caso.
SELECT is(
    (SELECT has_dati_societari FROM script.fn_get_soggetto_dati_by_ruolo(
        (SELECT soggetto_ruolo_id FROM tmp_profile_ctx)
    )),
    false,
    'fn_get_soggetto_dati_by_ruolo: soggetto senza dati societari → has_dati_societari = false'
);

-- ============================================================
-- D. fn_get_user_profile — profilo completo
-- ============================================================

-- 13) Profilo completo restituisce JSONB non nullo
SELECT isnt(
    script.fn_get_user_profile(
        (SELECT user_id FROM tmp_profile_ctx)
    ),
    NULL::jsonb,
    'fn_get_user_profile: profilo completo restituisce JSONB non nullo'
);

-- 14) Blocco utente contiene username
SELECT isnt(
    script.fn_get_user_profile(
        (SELECT user_id FROM tmp_profile_ctx)
    ) -> 'utente' ->> 'username',
    NULL,
    'fn_get_user_profile: blocco utente contiene username'
);

-- 15) Blocco utente contiene auth_user_id
SELECT isnt(
    script.fn_get_user_profile(
        (SELECT user_id FROM tmp_profile_ctx)
    ) -> 'utente' ->> 'auth_user_id',
    NULL,
    'fn_get_user_profile: blocco utente contiene auth_user_id'
);

-- 16) ⛔ RIMOSSO il 2026-08-18 — «fn_get_user_profile: ruolo_sistema presente»
--   La chiave `ruolo_sistema` e' stata TOLTA dall'output della funzione il
--   2026-04-29 (Fase 7 step 3), e il suo COMMENT lo dichiara: «rimossa la
--   chiave ruolo_sistema dall'output - BE post-Fase 7 LANDED non la legge
--   piu'». Questa asserzione pretendeva il contrario di una decisione presa.
--   ⚠️ Tolta e non riparata, come le quattro gemelle in
--   db/pgtap/config/test-permessi-strutture-base.sql: un test che chiede
--   indietro una cosa rimossa non e' un presidio.

-- 17) Blocco risorse_umane contiene risorsa_umana_id
SELECT isnt(
    script.fn_get_user_profile(
        (SELECT user_id FROM tmp_profile_ctx)
    ) -> 'risorse_umane' ->> 'risorsa_umana_id',
    NULL,
    'fn_get_user_profile: blocco risorse_umane contiene risorsa_umana_id'
);

-- 18) Blocco risorse_umane contiene soggetto_ruolo_id
SELECT isnt(
    script.fn_get_user_profile(
        (SELECT user_id FROM tmp_profile_ctx)
    ) -> 'risorse_umane' ->> 'soggetto_ruolo_id',
    NULL,
    'fn_get_user_profile: blocco risorse_umane contiene soggetto_ruolo_id'
);

-- 19) Blocco risorse_umane contiene qualifica_id
SELECT isnt(
    script.fn_get_user_profile(
        (SELECT user_id FROM tmp_profile_ctx)
    ) -> 'risorse_umane' ->> 'qualifica_id',
    NULL,
    'fn_get_user_profile: blocco risorse_umane contiene qualifica_id'
);

-- 20) Blocco soggetto contiene soggetto_id
SELECT isnt(
    script.fn_get_user_profile(
        (SELECT user_id FROM tmp_profile_ctx)
    ) -> 'soggetto' ->> 'soggetto_id',
    NULL,
    'fn_get_user_profile: blocco soggetto contiene soggetto_id'
);

-- 21) Blocco soggetto contiene ragione_sociale_completa
SELECT isnt(
    script.fn_get_user_profile(
        (SELECT user_id FROM tmp_profile_ctx)
    ) -> 'soggetto' ->> 'ragione_sociale_completa',
    NULL,
    'fn_get_user_profile: blocco soggetto contiene ragione_sociale_completa'
);

-- 22) Blocco soggetto contiene tipo_ruolo_codice_interno
SELECT isnt(
    script.fn_get_user_profile(
        (SELECT user_id FROM tmp_profile_ctx)
    ) -> 'soggetto' ->> 'tipo_ruolo_codice_interno',
    NULL,
    'fn_get_user_profile: blocco soggetto contiene tipo_ruolo_codice_interno'
);

-- 23) Blocco emittente: presente come chiave (puo' essere null se nessun emittente)
SELECT ok(
    script.fn_get_user_profile(
        (SELECT user_id FROM tmp_profile_ctx)
    ) ? 'emittente',
    'fn_get_user_profile: chiave emittente presente nel JSONB'
);

-- 24) Chiave permessi_oggetto presente nel JSONB
SELECT ok(
    script.fn_get_user_profile(
        (SELECT user_id FROM tmp_profile_ctx)
    ) ? 'permessi_oggetto',
    'fn_get_user_profile: chiave permessi_oggetto presente nel JSONB'
);

-- ============================================================
-- E. fn_get_user_profile — casi errore
-- ============================================================

-- 25) auth_user_id inesistente → errore P0001 via fn_log_and_raise_error
SELECT throws_ok(
    'SELECT script.fn_get_user_profile(99999999)',
    'P0001',
    'auth_user con id=99999999 non trovato..',
    'fn_get_user_profile: auth_user_id inesistente → errore'
);

-- 26) NULL → errore P0001 via fn_log_and_raise_error
SELECT throws_ok(
    'SELECT script.fn_get_user_profile(NULL::integer)',
    'P0001',
    'p_auth_user_id obbligatorio e > 0..',
    'fn_get_user_profile: NULL → errore'
);

-- ============================================================
-- 27) La chiave col nome vecchio non c'e' piu' (P-3 di analisi-software-per-dati-morti §6.6)
SELECT ok(
    NOT (
        script.fn_get_user_profile(
            (SELECT user_id FROM tmp_profile_ctx)
        ) -> 'risorse_umane' ? 'risorse_umane_auth_user_id'
    ),
    'fn_get_user_profile: il blocco risorse_umane non porta risorse_umane_auth_user_id (20_code/20260912-24)'
);

SELECT * FROM finish();
ROLLBACK;
