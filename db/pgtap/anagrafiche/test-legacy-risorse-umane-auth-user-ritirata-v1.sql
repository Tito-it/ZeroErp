-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il ponte legacy utente↔risorsa umana e' stato RITIRATO (12-09-2026): questo
-- file asserisce che il ritiro tenga — anche dopo `ci_apply`, dove le
-- automazioni lavorano per pattern e una madre con la colonna `storicizza`
-- si vedrebbe ricreare la shadow.
--
--   Brief: brief-db-rls-storico-scope-congelato §10 (coda del 12-09, decisione
--   Tid). ChangeSet: 00_schema/storico/20260912-08 (shadow),
--   80_data/changelog/20260912-09 (registrazioni),
--   90_end/20260912-10 (madre + trigger function),
--   00_schema/anagrafiche/20260912-11 (il guard di automazione rimasto sulla
--   MADRE risorse_umane per la figlia droppata — vedi test 10).
--
-- ⭐ Perche' un test per un DROP. Un `onFail: MARK_RAN` o un IF EXISTS che non
--   trova niente lasciano il changeSet verde e l'oggetto vivo: e' gia' successo
--   (20260818-66, scoperto da tre `hasnt_function`). E qui il rischio e'
--   doppio: la shadow puo' RINASCERE a `ci_apply` se la madre sopravvive. Il
--   test gira in CI dopo `ci_apply`, cioe' esattamente dopo il giro che
--   potrebbe farla rinascere.
--
-- ⚠️ Perche' queste asserzioni NON stanno in test-risorse-umane-auth-user-view:
--   quel file e' in baseline ERRORE_FIXTURE su dev e CI — un file che fallisce
--   nella fixture non esegue NESSUNA asserzione, e un presidio messo li' sarebbe
--   muto.
--
-- Elenco test (plan 12):
-- 1) la madre anagrafiche._legacy_risorse_umane_auth_user non esiste
-- 2) la sua shadow storico._legacy_risorse_umane_auth_user non esiste
-- 3) la shadow VECCHIA storico.risorse_umane_auth_user non esiste (20260912-03)
-- 4) trgfn_risorse_umane_auth_user_guard_persona_fisica non esiste (era solo sua)
-- 5) trgfn_risorse_umane_auth_user_sync_active non esiste (era solo sua)
-- 6) anagrafiche.fn_sync_auth_user_is_active ESISTE ancora (la usano identita_digitali e risorse_umane)
-- 7) il nome vecchio anagrafiche.risorse_umane_auth_user NON esiste piu' (strato 2:
--    fino al 12-09 pomeriggio era una vista, e questo test lo pretendeva; rovesciato
--    con 90_end/20260912-26 — il sostituto e' identita_digitali, test 11)
-- 8) nessuna riga per la legacy in dbops.storico_scope_policy
-- 9) nessuna registrazione per i due nomi in config.storico_set_storicizza
-- 10) nessun trigger su anagrafiche.risorse_umane nomina la figlia droppata
--     (il guard ATTIVO generato per la sua FK: con la figlia assente solleva
--     E_ATTIVO_BLOCK_FKCOL_NOT_FOUND a OGNI disattivazione della madre)
-- 11) nessuna funzione viva LEGGE il nome vecchio o ne fotografa un %TYPE
--     (FROM/JOIN/%TYPE su risorse_umane_auth_user in pg_proc: zero) — e le
--     quattro riscritte sulla madre esistono, con l'helper e il guard nuovi
-- 12) nessun trigger su risorse_umane nomina il nome vecchio (00_schema/20260912-19)
--
-- Scopo:
--  - presidiare che il ritiro regga su ogni database, compreso uno ricostruito
--    da zero e passato da `ci_apply`;
--  - presidiare che il DROP non abbia portato via cio' che DOVEVA restare
--    (la funzione condivisa, la vista che ha preso il nome).
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE: il file legge solo il catalogo, ma il preambolo e' lo
--   stesso per tutti — un file senza BEGIN e' un file che il guardrail respinge,
--   e il giorno che qualcuno aggiunge una fixture la trova gia' al sicuro.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: il test gira come `zeroerp_app`. Qui legge
--   pg_catalog e due registri senza RLS, ma la veste si dichiara comunque: e'
--   il contratto del runner, non una scelta del singolo file.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: nessuna scrittura qui, ma la riga e' obbligatoria
--   (guardrail_pgtap_preambolo) e innocua.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- Asserzioni
-- ============================================================

-- 1) La madre legacy non esiste piu'.
SELECT hasnt_table(
    'anagrafiche', '_legacy_risorse_umane_auth_user',
    '1) anagrafiche._legacy_risorse_umane_auth_user non esiste (90_end/20260912-10)'
);

-- 2) La sua shadow non esiste — e NON e' rinata a ci_apply: le automazioni
--    scoprono le madri per la colonna `storicizza`, e la madre non c'e' piu'.
SELECT hasnt_table(
    'storico', '_legacy_risorse_umane_auth_user',
    '2) storico._legacy_risorse_umane_auth_user non esiste e non e'' rinata (00_schema/storico/20260912-08)'
);

-- 3) La shadow vecchia, di prima della rinomina (12 versioni), eliminata dal -03.
SELECT hasnt_table(
    'storico', 'risorse_umane_auth_user',
    '3) storico.risorse_umane_auth_user non esiste (00_schema/storico/20260912-03)'
);

-- 4-5) Le due trigger function che esistevano solo per la legacy: codice morto,
--      e il presidio dei riferimenti morti (classe ORFANA) le vedrebbe.
SELECT hasnt_function(
    'anagrafiche', 'trgfn_risorse_umane_auth_user_guard_persona_fisica', ARRAY[]::text[],
    '4) trgfn_risorse_umane_auth_user_guard_persona_fisica non esiste (era montata solo sulla legacy)'
);
SELECT hasnt_function(
    'anagrafiche', 'trgfn_risorse_umane_auth_user_sync_active', ARRAY[]::text[],
    '5) trgfn_risorse_umane_auth_user_sync_active non esiste (era montata solo sulla legacy)'
);

-- 6) Cio' che DOVEVA restare: la funzione condivisa che la trigger function
--    chiamava. La usano ancora identita_digitali e risorse_umane.
SELECT has_function(
    'anagrafiche', 'fn_sync_auth_user_is_active',
    '6) anagrafiche.fn_sync_auth_user_is_active esiste ancora (chiamata da identita_digitali e risorse_umane)'
);

-- 7) Il nome vecchio non esiste piu' (strato 2, 90_end/20260912-26). Fino al
--    12-09 pomeriggio questo test pretendeva la VISTA: rovesciato.
SELECT hasnt_view(
    'anagrafiche', 'risorse_umane_auth_user',
    '7) anagrafiche.risorse_umane_auth_user e'' una vista (il sostituto della tabella ritirata)'
);

-- 8) La mappa dello scope non ha piu' la riga della legacy: altrimenti
--    sarebbe RIGA_SENZA_MADRE in dbops.vw_storico_scope_da_dichiarare.
SELECT is(
    (SELECT count(*)::int
       FROM dbops.storico_scope_policy
      WHERE schema_tabella = 'anagrafiche'
        AND nome_tabella IN ('_legacy_risorse_umane_auth_user', 'risorse_umane_auth_user')),
    0,
    '8) nessuna riga per la legacy in dbops.storico_scope_policy (80_data/20260912-09)'
);

-- 9) Nessuna registrazione di storicizzazione per i due nomi: quella del nome
--    vecchio era stantia dal cutover (il job non la toglieva: `to_regclass`
--    risolve la VISTA omonima), quella della legacy cade con la tabella.
SELECT is(
    (SELECT count(*)::int
       FROM config.storico_set_storicizza
      WHERE table_name IN ('anagrafiche.risorse_umane_auth_user',
                           'anagrafiche._legacy_risorse_umane_auth_user')),
    0,
    '9) nessuna registrazione in config.storico_set_storicizza per i due nomi (80_data/20260912-09)'
);

-- 10) Un trigger sulla MADRE e' un lettore della FIGLIA, e un DROP TABLE non
--     lo porta via: `trg_risorse_umane_a10_legacy_risorse_umane_auth_user_blo_feea48`
--     (generato dall'automazione ATTIVO per la FK) e' sopravvissuto al -10 e,
--     cercando in pg_attribute la colonna FK di una tabella che non esiste,
--     sollevava E_ATTIVO_BLOCK_FKCOL_NOT_FOUND su ogni `attivo` true->false di
--     risorse_umane (provato il 12-09 in ROLLBACK). Ritirato dal 20260912-11.
--     ⚠️ Si cerca per ARGOMENTO del trigger, non per nome: il nome porta un hash.
--     ⚠️ Il gemello sul NOME VECCHIO (vista risorse_umane_auth_user) NON e' qui:
--     vive apposta, ed e' l'unico guard RU<->identita' attiva finche' lo strato 2
--     non decide dove va la regola (analisi-software-per-dati-morti §2.1).
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
      WHERE t.tgrelid = 'anagrafiche.risorse_umane'::regclass
        AND NOT t.tgisinternal
        AND pg_get_triggerdef(t.oid) ~ '_legacy_risorse_umane_auth_user'),
    0,
    '10) nessun trigger su anagrafiche.risorse_umane nomina la figlia droppata (00_schema/20260912-11)'
);

-- 11) Il ritiro del NOME regge nel codice: nessuna funzione lo legge ne' lo
--     fotografa in un %TYPE. Si cerca la LETTURA (FROM/JOIN/%TYPE), non la
--     parola: i commenti che raccontano la storia possono restare.
SELECT is(
    (SELECT COALESCE(string_agg(n.nspname || '.' || p.proname, ', ' ORDER BY 1), '')
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
        AND p.prosrc ~ '(FROM|JOIN)\s+anagrafiche\.risorse_umane_auth_user\M|risorse_umane_auth_user\.[a-z_]+%TYPE'),
    '',
    '11) nessuna funzione legge anagrafiche.risorse_umane_auth_user ne'' ne fotografa un %TYPE'
);

-- 12) Il gemello del test 10 per il nome vecchio: il guard di automazione che
--     leggeva la vista non e' piu' montato (00_schema/20260912-19). Con la
--     vista ritirata avrebbe sollevato E_ATTIVO_BLOCK_FKCOL_NOT_FOUND.
SELECT is(
    (SELECT count(*)::int FROM pg_trigger t
      WHERE t.tgrelid = 'anagrafiche.risorse_umane'::regclass
        AND NOT t.tgisinternal
        AND pg_get_triggerdef(t.oid) ~ '''risorse_umane_auth_user'''),
    0,
    '12) nessun trigger su anagrafiche.risorse_umane nomina il nome vecchio (00_schema/20260912-19)'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
