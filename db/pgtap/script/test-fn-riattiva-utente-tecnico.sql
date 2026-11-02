-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture spegne e riaccende un utente tecnico —
--   django.auth_user, anagrafiche.identita_digitali, dbops.processi_identita —
--   e il ruolo applicativo non scrive su nessuna delle tre. Verificato cercando
--   gli scrittori, non dedotto.
--
-- Test: la sostituzione di un utente tecnico e' percorribile (DB-6, DB-8)
-- Brief: brief-db-processi-automatici-residui-be.md, DB-6 e DB-8
--
-- Elenco test (plan 6):
--  1) i codici nuovi sono a catalogo, con la classe giusta
--  2) ⭐ processo inesistente: dice «non trovato», non «non eleggibile» (DB-8)
--  3) ⛔ IL CASO DEL BE: legame spento + rifare l'utente -> si ferma PARLANDO
--  4) ✅ il verbo nuovo riattiva, e torna lo STESSO utente
--  5) ⭐ e riaccende tutti e TRE i livelli, non uno solo
--  6) ⛔ riattivare cio' che non esiste si ferma: il verbo non FABBRICA
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ IL DIFETTO, trovato dal backend e riprodotto:
--
--     legame disattivato -> fn_crea_utente_tecnico(...) -> 23505 NUDO
--
--   Il guard sul duplicato guarda `processi_identita.attivo`. Lo username NO, e
--   il suo UNIQUE non ha condizioni. ⇒ Disattivare il legame — **la via che il
--   nostro brief documentava** per sostituire l'utente di un processo — libera
--   il guard e lascia in piedi il muro.
--   ⭐ Il difetto non e' il 23505: e' che la strada documentata NON ERA
--     PERCORRIBILE, ed e' il tipo di frase che qualcuno segue fra sei mesi, di
--     fretta, su un processo che non fattura.
--
-- ⭐ I test 3 e 4 vanno letti INSIEME: il rifiuto indica un verbo, e il verbo
--   deve esistere. Un messaggio che manda da nessuna parte e' peggio di un
--   errore tecnico, perche' fa perdere tempo a chi ci crede.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- 1. I codici, e la loro classe
-- ============================================================
-- ⚠️ La classe non e' decorazione: e' cio' da cui il backend ricava lo stato
--   HTTP. `CONFLITTO_STATO` dice «i parametri sono giusti, e' lo stato del
--   mondo a non ammettere l'operazione» — e la risposta e' usare l'altro verbo,
--   non correggere l'input.
SELECT is(
    (SELECT string_agg(codice || '=' || classe, ' | ' ORDER BY codice)
       FROM config.codici_errore
      WHERE codice IN ('E_PROCESSO_NON_TROVATO',
                       'E_UTENTE_TECNICO_DA_RIATTIVARE',
                       'E_UTENTE_TECNICO_NON_TROVATO')),
    'E_PROCESSO_NON_TROVATO=NON_TROVATO | '
    'E_UTENTE_TECNICO_DA_RIATTIVARE=CONFLITTO_STATO | '
    'E_UTENTE_TECNICO_NON_TROVATO=NON_TROVATO',
    '1. i tre codici sono a catalogo con la classe giusta'
);

-- ============================================================
-- 2. DB-8: «non c'e'» e «non e' eleggibile» sono due cose diverse
-- ============================================================
-- Prima erano lo STESSO errore, e mandano a cercare in due posti diversi: il
-- primo nel seed del catalogo, il secondo nella riga che c'e' gia'.
SELECT throws_ok(
    format($$SELECT script.fn_crea_utente_tecnico('PGTAP-PROCESSO-CHE-NON-ESISTE', %L)$$,
           (SELECT codice FROM anagrafiche.emittenti_fiscali
             WHERE attivo ORDER BY id LIMIT 1)),
    'P0001',
    'Il processo PGTAP-PROCESSO-CHE-NON-ESISTE non esiste nel registro dei processi automatici.',
    '2. un processo inesistente dice «non trovato», non «non eleggibile»'
);

-- ============================================================
-- Fixture: si spegne un utente tecnico vero
-- ============================================================
-- ⭐ Si sceglie una coppia REALE e la si spegne come la spegnerebbe una persona
--   che vuole sostituire l'utente: e' il gesto che il brief documenta.
DO $fixture$
DECLARE
    v_processo   dbops.processi.codice%TYPE;
    v_emittente  anagrafiche.emittenti_fiscali.codice%TYPE;
    v_user       integer;   -- ⚠️ niente %TYPE su django.*
BEGIN
    -- Ordine stabile: una fixture che pesca a caso non verifica, scommette.
    SELECT p.codice, ef.codice, pi.auth_user_id
      INTO v_processo, v_emittente, v_user
      FROM dbops.processi_identita pi
      JOIN dbops.processi p ON p.id = pi.processo_id
      JOIN config.user_emittenti_fiscali uef ON uef.auth_user_id = pi.auth_user_id
      JOIN anagrafiche.emittenti_fiscali ef ON ef.id = uef.emittente_fiscale_id
     WHERE pi.attivo
     ORDER BY pi.id
     LIMIT 1;

    IF v_user IS NULL THEN
        PERFORM set_config('pgtap.ut_processo', '', true);
        RETURN;
    END IF;

    UPDATE dbops.processi_identita        SET attivo = false WHERE auth_user_id = v_user;
    UPDATE anagrafiche.identita_digitali  SET attivo = false WHERE auth_user_id = v_user;
    UPDATE django.auth_user               SET is_active = false WHERE id = v_user;

    PERFORM set_config('pgtap.ut_processo',  v_processo,  true);
    PERFORM set_config('pgtap.ut_emittente', v_emittente, true);
    PERFORM set_config('pgtap.ut_user',      v_user::text, true);
END
$fixture$;

-- ============================================================
-- 3. ⛔ Il caso del BE
-- ============================================================
SELECT CASE
    WHEN NULLIF(current_setting('pgtap.ut_processo', true), '') IS NULL
        THEN skip('3. nessun utente tecnico su cui costruire il caso', 1)
    ELSE throws_ok(
        format($$SELECT script.fn_crea_utente_tecnico(%L, %L)$$,
               current_setting('pgtap.ut_processo'),
               current_setting('pgtap.ut_emittente')),
        'P0001',
        NULL,
        '3. col legame spento, rifare l''utente si ferma (non e'' piu'' un 23505 nudo)'
    )
END;

-- ============================================================
-- 4..5. ✅ Il verbo che il rifiuto indica
-- ============================================================
DO $riattiva$
DECLARE
    v_dopo integer;
BEGIN
    IF NULLIF(current_setting('pgtap.ut_processo', true), '') IS NULL THEN
        PERFORM set_config('pgtap.ut_dopo', '', true);
        RETURN;
    END IF;

    v_dopo := script.fn_riattiva_utente_tecnico(
                  current_setting('pgtap.ut_processo'),
                  current_setting('pgtap.ut_emittente'));
    PERFORM set_config('pgtap.ut_dopo', v_dopo::text, true);
END
$riattiva$;

SELECT CASE
    WHEN NULLIF(current_setting('pgtap.ut_dopo', true), '') IS NULL
        THEN skip('4. idem: nessun utente tecnico da riattivare', 1)
    ELSE is(
        current_setting('pgtap.ut_dopo'),
        current_setting('pgtap.ut_user'),
        '4. la riattivazione torna lo STESSO utente, non ne fabbrica un altro'
    )
END;

-- ⭐ E riaccende TUTTI E TRE i livelli. Spegnerne uno solo basta a fermare
--   l'utente, quindi riaccenderne uno solo lo lascerebbe esistente ma inerte —
--   in un modo che non si vede. Asserire solo sul legame sarebbe verde con
--   l'utente ancora spento.
SELECT CASE
    WHEN NULLIF(current_setting('pgtap.ut_dopo', true), '') IS NULL
        THEN skip('5. idem', 1)
    ELSE is(
        (SELECT (pi.attivo)::text || '/' || (idg.attivo)::text || '/' || (au.is_active)::text
           FROM dbops.processi_identita pi
           JOIN anagrafiche.identita_digitali idg ON idg.auth_user_id = pi.auth_user_id
           JOIN django.auth_user au ON au.id = pi.auth_user_id
          WHERE pi.auth_user_id = current_setting('pgtap.ut_user')::integer),
        'true/true/true',
        '5. riaccende legame, identita'' e utente: tutti e tre, o niente'
    )
END;

-- ============================================================
-- 6. ⛔ Non si riattiva cio' che non c'e'
-- ============================================================
-- ⛔ 2026-09-05 — QUESTO TEST CHIEDEVA LA COSA SBAGLIATA, e la correzione vale
--   piu' del test. Chiedeva che riattivare «su un'altra azienda» si fermasse.
--   Non si ferma, ed e' GIUSTO: lo username porta dentro l'emittente
--   (processo@emittente), quindi passare un'altra azienda non SPOSTA un utente
--   — ne indirizza un ALTRO, che esiste ed e' legittimo. Il test misurava un
--   pericolo che il modello non permette.
--   ⇒ Il caso vero e costruibile e' l'altro: chiedere la riattivazione di
--     qualcosa che non e' mai stato creato.
--
-- ⚠️ E il guard sul perimetro nella funzione resta, ma va detto cos'e': difesa
--   in profondita' contro un dato incoerente (username presente, riga di
--   perimetro assente o su un'altra azienda), NON un caso che l'applicazione
--   sappia produrre. Dichiararlo qui evita che qualcuno lo tolga credendolo
--   morto, o scriva un test che non puo' essere verde.
DO $senza_utente$
DECLARE
    v_id dbops.processi.id%TYPE := 9901;
BEGIN
    -- 20261016-20: un processo con una sveglia dichiara l'accensione.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
    VALUES (v_id, 'PGTAP-PROC-SENZA-UTENTE',
            'processo di prova che non ha mai avuto un utente tecnico',
            'DOMINIO', 'COMMAND', true, true, true, 'PROGRAMMA', true);
END
$senza_utente$;

SELECT throws_ok(
    format($$SELECT script.fn_riattiva_utente_tecnico('PGTAP-PROC-SENZA-UTENTE', %L)$$,
           (SELECT codice FROM anagrafiche.emittenti_fiscali
             WHERE attivo ORDER BY id LIMIT 1)),
    'P0001',
    NULL,
    '6. riattivare un utente mai creato si ferma: il verbo non fabbrica niente'
);

SELECT * FROM finish();

ROLLBACK;
