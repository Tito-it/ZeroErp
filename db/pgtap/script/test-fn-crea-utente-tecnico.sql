-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su dbops.processi (catalogo che a
--   runtime non scrive nessuno) e la funzione sotto test crea utenti Django,
--   soggetti e identita' — un percorso che l'applicazione non offre e non deve
--   offrire: la fabbrica e' REVOCATA a PUBLIC apposta. Verificato cercando gli
--   scrittori, non dedotto.
--
-- Test: script.fn_crea_utente_tecnico
-- Brief: brief-db-processi-automatici-identita-e-perimetro §4 (fase 3b)
--
-- Elenco test (plan 12):
--  1) la funzione esiste
--  2) ⛔ PUBLIC non ha EXECUTE sulla fabbrica
--  3) su un processo eleggibile crea l'utente e ritorna l'auth_user_id
--  4) l'utente Django nasce con password INUTILIZZABILE (prefisso '!')
--  5) l'identita' e' OPERATORE e porta il flag tecnica
--  6) ⛔ senza profilo l'identita' non ha alcun binding (minimo privilegio)
--  7) l'utente nasce con ESATTAMENTE un emittente (modello 1-a-1)
-- 12) il soggetto di processo ha il contatto di riferimento (guard differito)
--  8) ⛔ un profilo non-AD_HOC (SUPER_ADMIN) viene rifiutato
--  9) ⛔ un processo di CODA viene rifiutato
-- 10) ⛔ un secondo utente su stesso processo E emittente viene rifiutato
-- 11) ⭐ i due mondi restano disgiunti: togliere il flag tecnica viene rifiutato
--
-- Scopo:
--  - provare che i CINQUE inserimenti coordinati riescono davvero: e' il test
--    che verifica le colonne di django.auth_user, che non stanno nella doc
--    auto-gen e che altrimenti sarebbero un'assunzione;
--  - provare i tre divieti COSTRUENDO i casi vietati, non sperando che non
--    capitino — soprattutto il divieto SUPER_ADMIN, che e' la scorciatoia
--    ovvia e riaprirebbe la porta che il cantiere chiude;
--  - fissare l'ASSENZA della whitelist (test 7): e' una decisione (D-9), e
--    senza un test sembrerebbe una dimenticanza da completare.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ `SET CONSTRAINTS ALL IMMEDIATE` NON sta qui, ed e' il caso che il template
--   descrive: «va DOVE L'UNITA' DI LAVORO E' COMPLETA». La fabbrica crea il
--   soggetto in un'istruzione e il suo contatto in quella dopo; il guard sui
--   contatti e' DIFFERITO (verifica al commit), quindi con IMMEDIATE in testa
--   scatterebbe a meta' strada — bocciando un soggetto che sta per ricevere il
--   contatto due righe piu' sotto.
--   ⇒ Sta dopo il blocco di creazione, prima di ogni asserzione. Il guardrail
--     del preambolo controlla la presenza, non la posizione.
-- ⛔ E la finestra si DICHIARA (rev 2026-10-18): su un database vuoto la riga di
--   contesto qui sopra costruisce il mondo ed esce con i vincoli IMMEDIATE. Senza
--   questa riga la fabbrica moriva su E_SOGGETTO_NO_CONTATTI: verde su dbdev
--   (dove il mondo c'e' gia' e il contesto non costruisce niente), rosso sullo
--   scratch ricostruito da zero.
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(12);

-- ============================================================
-- 1..2. Esistenza e postura dei privilegi
-- ============================================================
SELECT has_function('script', 'fn_crea_utente_tecnico',
                    'script.fn_crea_utente_tecnico esiste');

-- ⛔ Una fabbrica di utenti aperta a PUBLIC e' un buco. Il REVOKE sta nello
--   stesso changeSet della CREATE, e questo test lo tiene fermo.
SELECT ok(
    NOT has_function_privilege('public',
        (SELECT p.oid
           FROM pg_catalog.pg_proc p
           JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
          WHERE n.nspname = 'script' AND p.proname = 'fn_crea_utente_tecnico'),
        'EXECUTE'),
    'fn_crea_utente_tecnico: PUBLIC senza EXECUTE'
);

-- ============================================================
-- Fixture: due processi (uno headless eleggibile, uno di coda) e un
-- profilo non-SUPER_ADMIN su cui appoggiarsi.
-- ============================================================
DO $fixture$
DECLARE
    v_profilo config.profili_accesso.codice%TYPE;
BEGIN
    -- 20261016-20: chi ha una sveglia dichiara l'accensione; un CODA no.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
    VALUES (9401, 'PGTAP-FABBRICA-OK',
            'processo di dominio headless per il collaudo della fabbrica',
            'DOMINIO', 'COMMAND', true, true, true, 'PROGRAMMA', true),
           (9402, 'PGTAP-FABBRICA-CODA',
            'processo di dominio accodato da un operatore',
            'DOMINIO', 'CODA', NULL, NULL, NULL, 'PROGRAMMA', NULL);

    -- L'emittente su cui creare l'utente: quello dell'operatore di contesto
    -- (rev 2026-10-18). L'emittente non si pesca, si deriva: prima era «il
    -- primo attivo della tabella».
    PERFORM set_config('pgtap.emittente',
        COALESCE((SELECT ef.codice
                    FROM anagrafiche.emittenti_fiscali ef
                   WHERE ef.id = script.fn_pgtap_emittente_operatore()), ''), true);

    -- Un profilo NON-AD_HOC su cui provare il rifiuto.
    SELECT pa.codice INTO v_profilo
      FROM config.profili_accesso pa
     WHERE pa.attivo
       AND pa.tipo <> 'AD_HOC'::config.tipo_profilo_accesso
     ORDER BY pa.id
     LIMIT 1;

    PERFORM set_config('pgtap.profilo_non_adhoc', COALESCE(v_profilo, ''), true);
END
$fixture$;

-- ============================================================
-- 3..7. Il percorso felice, e le cinque scritture
-- ============================================================
DO $crea$
DECLARE
    v_auth_user_id integer;
BEGIN
    -- ⭐ Nessun profilo: e' il caso NORMALE. Un processo headless non passa da
    --   percorsi capability-gated, quindi zero capability e' minimo privilegio.
    v_auth_user_id := script.fn_crea_utente_tecnico(
        'PGTAP-FABBRICA-OK', current_setting('pgtap.emittente'));
    PERFORM set_config('pgtap.auth_user_id', v_auth_user_id::text, true);
END
$crea$;

-- Unita' di lavoro completa (utente + soggetto + contatto + ruolo + identita'):
-- da qui in poi i vincoli differiti devono scattare, o il file sarebbe verde
-- per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT isnt(
    NULLIF(current_setting('pgtap.auth_user_id', true), ''),
    NULL,
    'la fabbrica ritorna l''auth_user_id dell''utente creato'
);

-- ⭐ Il prefisso '!' e' la convenzione Django per «non puo' autenticarsi». Un
--   processo non fa login, e nessuno deve poterlo fare al posto suo.
SELECT ok(
    (SELECT au.password LIKE '!%'
       FROM django.auth_user au
      WHERE au.id = current_setting('pgtap.auth_user_id')::integer),
    'l''utente Django nasce con password inutilizzabile (prefisso !)'
);

-- ⛔ OPERATORE non e' una preferenza: con qualunque altro ruolo applicativo le
--   policy rls_*_ef_whitelist non risolvono e il processo vede zero righe, in
--   silenzio. E il flag e' l'unico posto in cui «e' un processo» sta scritto.
SELECT ok(
    EXISTS (SELECT 1
              FROM anagrafiche.identita_digitali idg
             WHERE idg.auth_user_id = current_setting('pgtap.auth_user_id')::integer
               AND idg.attivo
               AND idg.tecnica
               AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo),
    'l''identita'' e'' OPERATORE attiva e porta il flag tecnica'
);

-- ⭐ ALTRA ASSENZA VOLUTA. Senza profilo l'identita' ha ZERO capability, ed e'
--   corretto: i profili alimentano liste, dashboard e resolver delle API, e un
--   processo headless non passa da nessuno di quei percorsi. Dare a
--   send_pending_emails i permessi di fatturare sarebbe potere non richiesto.
SELECT is_empty(
    format($$SELECT 1
               FROM config.profili_accesso_bindings b
               JOIN anagrafiche.identita_digitali idg ON idg.id = b.identita_digitale_id
              WHERE idg.auth_user_id = %s$$,
           current_setting('pgtap.auth_user_id')),
    'senza profilo l''identita'' tecnica non ha alcun binding: minimo privilegio'
);

-- ⭐ Il perimetro e' COSTITUTIVO, e ce n'e' esattamente UNO:
--   config.user_emittenti_fiscali e' 1-a-1 sull'utente. Un utente tecnico nasce
--   PER un emittente, e uno senza non potrebbe fare niente — e' lo stato in cui
--   i primi quattro erano nati.
--   ⚠️ D-9 non e' violata: la fabbrica non SCEGLIE l'emittente, lo riceve.
SELECT is(
    (SELECT count(*)::int
       FROM config.user_emittenti_fiscali
      WHERE auth_user_id = current_setting('pgtap.auth_user_id')::integer),
    1,
    'l''utente tecnico nasce con ESATTAMENTE un emittente (modello 1-a-1)'
);

-- ============================================================
-- 8..10. I tre divieti, su casi COSTRUITI
-- ============================================================
-- ⛔⛔ SUPER_ADMIN e' la scorciatoia ovvia per «deve servire tutti gli
--   emittenti», e bypassa lo scope PRIMA della whitelist — riaprendo con un
--   nome rassicurante la porta che il cantiere esiste per chiudere. Non e'
--   AD_HOC, quindi cade nel guard generale.
SELECT throws_ok(
    format($$SELECT script.fn_crea_utente_tecnico('PGTAP-FABBRICA-OK', %L, 'SUPER_ADMIN')$$,
           current_setting('pgtap.emittente')),
    'P0001',
    NULL,
    'un profilo SUPER_ADMIN viene rifiutato'
);

SELECT throws_ok(
    format($$SELECT script.fn_crea_utente_tecnico('PGTAP-FABBRICA-CODA', %L)$$,
           current_setting('pgtap.emittente')),
    'P0001',
    NULL,
    'un processo di CODA viene rifiutato: ha gia'' l''identita'' dell''operatore'
);

SELECT throws_ok(
    format($$SELECT script.fn_crea_utente_tecnico('PGTAP-FABBRICA-OK', %L)$$,
           current_setting('pgtap.emittente')),
    'P0001',
    NULL,
    'un secondo utente sullo stesso processo E EMITTENTE viene rifiutato'
);

-- ============================================================
-- 12. Il contatto di riferimento del soggetto di processo
-- ============================================================
-- ⭐ Il guard differito trgfn_soggetti_guard_soggetto_contatti pretende almeno
--   un contatto, e ammette `is_default` coi canali vuoti. La fabbrica passa da
--   li' — nessun guard anagrafico e' stato modificato, e nessuna email e'
--   stata inventata. Questo test tiene ferma quella scelta: se un domani il
--   contatto sparisse dalla fabbrica, il migrate morirebbe al commit e nessuno
--   saprebbe perche'.
SELECT ok(
    EXISTS (SELECT 1
              FROM anagrafiche.contatti c
              JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = c.soggetto_id
              JOIN anagrafiche.identita_digitali idg ON idg.soggetto_ruolo_id = sr.id
             WHERE idg.auth_user_id = current_setting('pgtap.auth_user_id')::integer
               AND c.is_default),
    'il soggetto di processo ha il contatto di riferimento (is_default)'
);

-- ============================================================
-- 11. ⭐ I due mondi restano DISGIUNTI
-- ============================================================
-- ⛔ E' il test su cui va giudicata la modifica del guard di coerenza
--   (20260904-28). Il flag `tecnica` non APRE il ramo OPERATORE: sceglie
--   quale coppia di requisiti si applica, e restano chiuse entrambe —
--     tecnica = false -> RIS_UMANA + persona fisica pura
--     tecnica = true  -> PROC_AUTO
--   Se il flag fosse un bypass, togliendolo a un'identita' appesa a un
--   soggetto di PROCESSO la riga passerebbe lo stesso. Deve invece
--   fallire: quel soggetto non e' ne' una risorsa umana ne' una persona.
--   ⇒ Una persona non puo' essere PROC_AUTO, un processo non puo' essere
--     RIS_UMANA, e `tecnica` non e' una scorciatoia per nessuno dei due.
SELECT throws_ok(
    format($$UPDATE anagrafiche.identita_digitali
                SET tecnica = false
              WHERE auth_user_id = %s$$,
           current_setting('pgtap.auth_user_id')),
    'P0001',
    NULL,
    'togliere il flag tecnica a un''identita'' su soggetto di processo viene rifiutato'
);

SELECT * FROM finish();

ROLLBACK;
