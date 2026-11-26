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
-- Elenco test (plan 10):
--  1) i codici nuovi sono a catalogo, con la classe giusta
--  2) ⭐ processo inesistente: dice «non trovato», non «non eleggibile» (DB-8)
--  3) ⛔ IL CASO DEL BE: legame spento + rifare l'utente -> si ferma PARLANDO
--  4) ✅ il verbo nuovo riattiva, e torna lo STESSO utente
--  5) ⭐ e riaccende tutti e TRE i livelli, non uno solo
--  6) ⛔ riattivare cio' che non esiste si ferma: il verbo non FABBRICA
--  7) ⛔ senza SUPER_ADMIN non si riattiva (il permesso e' a DB dal 2026-11-25);
--     7-bis) e il rifiuto non tocca l'utente
--  8) un utente tecnico REVOCATO (fn_revoca_veste) porta il segno, con chi
--  9) ✅ la riattivazione toglie il segno col suo verbo e riaccende la veste
--
-- ⭐ Il contesto e' un SUPER_ADMIN costruito dal test (rev 2026-11-25,
--   brief-db-accessi-area-clienti giro 1): la riattivazione e' il gesto
--   dell'amministratore e lo chiede a DB. Prima il test girava su un operatore
--   qualunque, perche' il permesso lo chiedeva solo il backend.
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
-- ⭐ Il 4) riattiva con la sigla dell'emittente in MINUSCOLO (rev 2026-11-04,
--   20261104-37): l'emittente si cerca normalizzato e lo username si compone
--   col codice salvato, quindi l'utente da riattivare si ritrova.
--
-- ⭐ I test 3 e 4 vanno letti INSIEME: il rifiuto indica un verbo, e il verbo
--   deve esistere. Un messaggio che manda da nessuna parte e' peggio di un
--   errore tecnico, perche' fa perdere tempo a chi ci crede.
-- ------------------------------------------------------------

BEGIN;

-- L'utente tecnico dei casi 8-9 si costruisce PRIMA del contesto (stampo di
-- anagrafiche/test-area-accessi-v1.sql): crea la sua azienda.
CREATE TEMP TABLE _tec AS
SELECT r.auth_user_id, r.emittente_codice, r.identita_id
  FROM dbops.fn_pgtap_crea_roster_processo('send_pending_emails') r;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

-- Chi agisce: un SUPER_ADMIN e un operatore senza privilegi, dal percorso di
-- produzione.
CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-riattiva', true);
CREATE TEMP TABLE _op AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-OP-riattiva', false);
SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa));

SELECT plan(10);

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
                  lower(current_setting('pgtap.ut_emittente')));
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

-- ============================================================
-- 7. ⛔ Il permesso: solo SUPER_ADMIN
-- ============================================================
SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _op));
SELECT throws_ok(
    format($$SELECT script.fn_riattiva_utente_tecnico('send_pending_emails', %L)$$,
           (SELECT emittente_codice FROM _tec)),
    'P0001',
    'Non hai i permessi per questa operazione.',   -- E_PERMESSO_NEGATO
    '7. un operatore senza SUPER_ADMIN non riattiva un utente tecnico'
);
SELECT is(
    (SELECT idg.attivo FROM anagrafiche.identita_digitali idg WHERE idg.id = (SELECT identita_id FROM _tec)),
    true,
    '7-bis. (fixture) il rifiuto non ha toccato l''utente tecnico, ancora acceso'
);

-- ============================================================
-- 8-9. La revoca dell'utente tecnico, e la riattivazione che la toglie
-- ============================================================
-- Lo spegnimento dell'amministratore e' il verbo della revoca (D-R7): spegne la
-- veste e mette il segno. Il legame e l'utente si spengono come li spegnerebbe
-- la sostituzione documentata.
SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa));
SELECT anagrafiche.fn_revoca_veste((SELECT identita_id FROM _tec));
UPDATE dbops.processi_identita SET attivo = false WHERE auth_user_id = (SELECT auth_user_id FROM _tec);
UPDATE django.auth_user        SET is_active = false WHERE id = (SELECT auth_user_id FROM _tec);

SELECT is(
    (SELECT format('%s|%s', idg.attivo, idg.revocata_da_user_id = (SELECT auth_user_id FROM _sa))
       FROM anagrafiche.identita_digitali idg WHERE idg.id = (SELECT identita_id FROM _tec)),
    'f|t',
    '8. l''utente tecnico revocato e'' spento e porta il segno, col nome del super admin'
);

CREATE TEMP TABLE _riatt AS
SELECT script.fn_riattiva_utente_tecnico('send_pending_emails', (SELECT emittente_codice FROM _tec)) AS auth_user_id;
SELECT is(
    (SELECT format('%s|%s|%s', r.auth_user_id = t.auth_user_id, idg.attivo, idg.revocata_at IS NULL)
       FROM _riatt r, _tec t, anagrafiche.identita_digitali idg
      WHERE idg.id = t.identita_id),
    't|t|t',
    '9. la riattivazione toglie il segno e riaccende la veste dello stesso utente'
);

SELECT * FROM finish();

ROLLBACK;
