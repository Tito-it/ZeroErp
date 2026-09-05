-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il guard di scrittura sulla coda di stampa (DB-6 / R-10)
-- Brief: brief-db-processi-automatici-residui-be.md, risposta DB (R-D)
--
-- Elenco test (plan 6):
--  1) ⭐ IL PRESUPPOSTO: questa sessione SUBISCE la row level security
--  2) il guard c'e', ed e' montato sul modo `fattura` su `sorgente_id`
--  3) ⚠️ la FK che rende lecito quel modo esiste ancora
--  4) ✅ accodare la stampa di una PROPRIA fattura passa
--  5) ⛔ accodare la stampa di una fattura ALTRUI si ferma, e SPIEGA
--  6) ⭐ il presidio livello 2 e' VUOTO
--
-- Scopo:
--  - provare il caso che la policy da sola non copre bene: sull'INSERT il
--    `WITH CHECK` si valuta DOPO i trigger `BEFORE ROW`, quindi senza guard
--    l'operatore riceverebbe «new row violates row-level security policy» —
--    vero e inservibile. Il test 5 chiede il messaggio, non solo il rifiuto;
--  - ⚠️ fissare col test 3 l'ASSUNTO su cui il modo `fattura` regge. La tabella
--    porta `sorgente_tipo_id` e `sorgente_uid`, cioe' la forma delle sorgenti
--    polimorfe: quello che la rende non-polimorfa e' una FK dura. Se cadesse,
--    il guard punterebbe alla tabella sbagliata e la policy pure — e nessuno
--    dei due lo direbbe da solo.
--
-- ⚠️ Runner: APPLICATIVO. Dalla fase 6 il guard esce subito per chi bypasserebbe
--   comunque la RLS, cioe' per l'owner: girando da owner i test 4 e 5 sarebbero
--   verdi *perche' non succede niente*. Il test 1 rende il presupposto
--   un'asserzione.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ============================================================
-- 1..3. Il presupposto e la postura
-- ============================================================
SELECT ok(
    row_security_active('vendite.fatture_stampa_coda'::regclass),
    '1. questa sessione SUBISCE la RLS: i test 4 e 5 hanno senso'
);

-- ⚠️ Non basta «c''e'' un guard»: un guard montato col modo sbagliato
--   risolverebbe sempre NULL, cioe' sarebbe spento pur sembrando acceso.
SELECT is(
    (SELECT encode(t.tgargs, 'escape')
       FROM pg_trigger t JOIN pg_proc f ON f.oid = t.tgfoid
      WHERE t.tgrelid = 'vendite.fatture_stampa_coda'::regclass
        AND NOT t.tgisinternal
        AND f.proname = 'trgfn_guard_emittente_scope'),
    'fattura\000sorgente_id\000',
    '2. il guard e'' montato sul modo fattura, su sorgente_id'
);

-- ⭐ QUESTO TEST FISSA UN ASSUNTO, ed e' il motivo per cui esiste.
--   `sorgente_tipo_id` + `sorgente_uid` sono la forma delle sorgenti polimorfe,
--   dove il portante puo' essere l'uid e puntare `sorgente_id` a UNA tabella
--   sarebbe sbagliato. Qui e' lecito solo perche' una FK dura lo fissa alle
--   fatture. ⛔ Se cadesse, guard e policy assumerebbero entrambi una cosa
--   falsa, e nessuno dei due se ne accorgerebbe.
SELECT isnt_empty(
    $$SELECT 1 FROM pg_constraint
       WHERE conname = 'fk_fatture_stampa_coda_fattura'
         AND conrelid = 'vendite.fatture_stampa_coda'::regclass$$,
    '3. la FK che fissa sorgente_id alle fatture esiste ancora'
);

-- ============================================================
-- Fixture: una fattura mia, e una di un altro emittente
-- ============================================================
-- ⭐ La fattura altrui si crea dal SUPER ADMIN, l'unico attore che puo'
--   scrivere fuori dal proprio perimetro — ed e' proprio cio' che il test 5
--   prova essere vietato all'operatore.
-- ⚠️ Se esiste un solo emittente attivo il caso non e' costruibile: si dichiara
--   e si salta, invece di fingere.
DO $fixture$
DECLARE
    v_mio_ef     anagrafiche.emittenti_fiscali.id%TYPE;
    v_altro_sr   anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_super      integer;   -- ⚠️ niente %TYPE su django.*
    v_mia        vendite.fatture.id%TYPE;
    v_altrui     vendite.fatture.id%TYPE;
BEGIN
    v_mio_ef := script.fn_pgtap_emittente_operatore();

    -- Ordine stabile: una fixture che pesca a caso non verifica, scommette.
    SELECT f.id INTO v_mia
      FROM vendite.fatture f
      JOIN anagrafiche.emittenti_fiscali ef
        ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
     WHERE ef.id = v_mio_ef
     ORDER BY f.id
     LIMIT 1;

    -- ⛔ LA FATTURA ALTRUI SI COSTRUISCE, non si cerca.
    --   Misurato il 2026-09-05: su questo database il secondo emittente ha
    --   ZERO fatture. Cercandola, il test 5 si sarebbe SALTATO — dichiarando
    --   onestamente di non aver provato niente, ma lasciando non esercitata
    --   proprio l'asserzione per cui il file esiste.
    --   ⇒ La si crea, e la si crea dal SUPER ADMIN: e' l'unico attore che puo'
    --     scrivere fuori dal proprio perimetro, cioe' esattamente cio' che il
    --     test 5 prova essere vietato all'operatore.
    SELECT ef.soggetto_ruolo_id INTO v_altro_sr
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.attivo AND ef.id <> v_mio_ef
     ORDER BY ef.id
     LIMIT 1;

    SELECT u.id INTO v_super
      FROM django.auth_user u
     WHERE script.fn_is_super_admin(u.id)
     ORDER BY u.id
     LIMIT 1;

    IF v_altro_sr IS NOT NULL AND v_super IS NOT NULL THEN
        PERFORM script.fn_pgtap_set_contesto_operatore(v_super);

        -- ⭐ Il registro lo da' l'helper, che ne CREA uno coerente se
        --   quell'emittente non ne ha: senza, il guard registro-emittente
        --   rifiuterebbe la fattura per un motivo che non c'entra col test.
        INSERT INTO vendite.fatture
            (registro_id, emittente_soggetto_ruolo_id, billing_account_id, meta)
        SELECT script.fn_pgtap_registro_fattura(v_altro_sr),
               v_altro_sr,
               (SELECT ba.id FROM anagrafiche.billing_account ba
                 ORDER BY ba.id LIMIT 1),
               jsonb_build_object('test_scope', 'pgtap_guard_stampa_coda')
        RETURNING id INTO v_altrui;

        -- Si torna all'operatore normale: da qui si collauda cio' che puo'
        -- fare LUI.
        -- ⚠️ I vincoli sono gia' IMMEDIATE dal preambolo, quindi si sono
        --   chiusi qui sopra, nei panni di chi ha scritto. Fossero rimasti
        --   differiti si sarebbero verificati DOPO questo cambio di attore, e
        --   avrebbero letto sotto la RLS dell'operatore.
        PERFORM script.fn_pgtap_set_contesto_operatore();
    END IF;

    PERFORM set_config('pgtap.fattura_mia',
                       COALESCE(v_mia::text, ''), true);
    PERFORM set_config('pgtap.fattura_altrui',
                       COALESCE(v_altrui::text, ''), true);
END
$fixture$;

-- ============================================================
-- 4. ✅ Cio' che deve passare
-- ============================================================
-- Prima del rifiuto va provato il consenso: un guard che nega tutto passerebbe
-- il test 5 senza essere corretto.
SELECT CASE
    WHEN NULLIF(current_setting('pgtap.fattura_mia', true), '') IS NULL
        THEN skip('4. nessuna fattura nel proprio perimetro su cui costruire il caso', 1)
    ELSE lives_ok(
        format($$INSERT INTO vendite.fatture_stampa_coda
                     (sorgente_tipo_id, sorgente_id, sorgente_uid, stato)
                 SELECT (SELECT id FROM config.sorgenti
                          WHERE codice_interno = 'FATTURA'),
                        %s, 'pgtap-guard-mia', 'PENDING'$$,
               current_setting('pgtap.fattura_mia')),
        '4. accodare la stampa di una PROPRIA fattura passa'
    )
END;

-- ============================================================
-- 5. ⛔ Cio' che deve fermarsi, e come lo dice
-- ============================================================
-- ⭐ E' il caso per cui il guard esiste: sull'INSERT la policy arriverebbe
--   dopo, con un messaggio che non dice niente. Il guard scatta BEFORE e nomina
--   utente, emittente e tabella.
-- ⚠️ Non si usa `throws_ok` col solo SQLSTATE: tutti gli errori applicativi
--   passano da `fn_log_and_raise_error` e sono `P0001`, quindi sarebbe verde
--   anche se a fermare la riga fosse un guard qualunque — o la policy. Si
--   chiede lo stato E che il messaggio sia quello dello scope.
DO $prova$
DECLARE
    v_esito text := 'non-sollevato';
BEGIN
    IF NULLIF(current_setting('pgtap.fattura_altrui', true), '') IS NULL THEN
        PERFORM set_config('pgtap.esito5', 'skip', true);
        RETURN;
    END IF;

    BEGIN
        INSERT INTO vendite.fatture_stampa_coda
            (sorgente_tipo_id, sorgente_id, sorgente_uid, stato)
        SELECT (SELECT id FROM config.sorgenti WHERE codice_interno = 'FATTURA'),
               current_setting('pgtap.fattura_altrui')::bigint,
               'pgtap-guard-altrui', 'PENDING';
    EXCEPTION WHEN OTHERS THEN
        v_esito := SQLSTATE || '|' ||
                   CASE WHEN SQLERRM ILIKE '%scope emittente fiscale%'
                        THEN 'scope' ELSE 'altro:' || left(SQLERRM, 60) END;
    END;

    PERFORM set_config('pgtap.esito5', v_esito, true);
END
$prova$;

SELECT CASE
    WHEN current_setting('pgtap.esito5', true) = 'skip'
        THEN skip('5. nessuna fattura di un altro emittente su questo database', 1)
    ELSE is(
        current_setting('pgtap.esito5', true),
        'P0001|scope',
        '5. accodare la stampa di una fattura ALTRUI si ferma, e SPIEGA'
    )
END;

-- ============================================================
-- 6. ⭐ Il presidio arriva a ZERO
-- ============================================================
-- E' il primo presidio di questo cantiere che ci arriva davvero: qui la vista
-- deve essere VUOTA, non «senza la nostra riga».
SELECT is_empty(
    $$SELECT 1 FROM dbops.vw_processi_dominio_senza_difesa$$,
    '6. dbops.vw_processi_dominio_senza_difesa e'' vuota'
);

SELECT * FROM finish();

ROLLBACK;
