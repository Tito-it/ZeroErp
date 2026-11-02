-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il perimetro emittente sulla famiglia LISTINO (DB-4 / R-8)
-- Brief: brief-db-processi-automatici-residui-be.md, sezione DB-4
--
-- Elenco test (plan 8):
--  1) RLS abilitata e NON forzata su entrambe le tabelle
--  2) le policy sono FOR ALL — una FOR SELECT sarebbe deny-all in scrittura
--  3) il guard di scrittura c'e' su entrambe, coi DUE modi giusti
--  4) ⭐ l'operatore vede i propri listini e NON quello di un altro
--  5) ⭐ e non vede nemmeno le VERSIONI del listino altrui (percorso dal padre)
--  6) ✅ una scrittura nel proprio perimetro passa
--  7) ⛔ appendere una versione al listino di un altro si ferma, e SPIEGA
--  8) ⭐ il presidio non nomina piu' vendite.listini_versioni
--
-- Scopo:
--  - provare i due meccanismi SEPARATAMENTE, perche' rispondono a due domande
--    diverse: la policy NASCONDE (4, 5), il guard RIFIUTA E SPIEGA (7). Un test
--    che provasse solo il risultato «non entra» non distinguerebbe quale dei
--    due ha parlato — e il giorno che uno dei due sparisse resterebbe verde;
--  - fissare che il perimetro della figlia passa dal PADRE (5, 7), che e' la
--    parte nuova: `listini_versioni` non ha una colonna emittente e non deve
--    averla.
--
-- ⚠️ Runner: APPLICATIVO (nessun marcatore `pgtap-runner`), e non e' un
--   dettaglio. Dalla fase 6 il guard di scrittura esce subito per chi
--   bypasserebbe comunque la RLS — cioe' per l'OWNER. Girando da owner i test
--   6 e 7 sarebbero verdi *perche' non succede niente*.
--   ⇒ Il test 1 rende quel presupposto un'asserzione: se qualcuno mettesse
--     FORCE, o spostasse il file su owner, se ne accorge.
-- ------------------------------------------------------------

BEGIN;

-- ⛔ LE TRE AZIENDE SI COSTRUISCONO, non si cercano (2026-09-12): fino a quel
--   giorno il file pescava il proprio emittente, «un altro emittente attivo»
--   e un super admin fra i dati ESISTENTI, e senza di loro SALTAVA i test 4,
--   5, 6 e 7 — su un database ricostruito dai changelog moriva nella fixture
--   («Nessun emittente fiscale attivo»). Tre aziende con
--   `dbops.fn_pgtap_crea_emittente_operatore()`: MIA (il contesto), ALTRUI (il
--   listino fuori perimetro) e SA, il cui operatore diventa super admin con un
--   binding — e' lui che puo' costruire il listino altrui. Niente piu' `skip`.
--   ⚠️ Niente BA: la famiglia listino porta l'emittente in testata, quindi il
--   file resta sul runner APPLICATIVO.
CREATE TEMP TABLE _mondi AS
SELECT 'MIA'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRUI' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'SA'     AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $lega$ BEGIN PERFORM config.fn_lega_profilo_identita((SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'), (SELECT identita_id FROM _mondi WHERE lato = 'SA')); END $lega$;

-- ⚠️ L'helper esce con i vincoli IMMEDIATE; questo file li vuole DIFFERITI
--   fino a dopo la fixture (vedi sotto), quindi li riapre.
SET CONSTRAINTS ALL DEFERRED;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'MIA'));
END $ctx$;

-- ⚠️ `SET CONSTRAINTS ALL IMMEDIATE` sta DOPO la fixture: quella crea un
--   listino e la sua versione in due istruzioni, e i guard figli-padre della
--   famiglia sono differiti. In testa scatterebbero a meta' strada.

SELECT plan(8);

-- ============================================================
-- 1..3. La postura: com'e' fatta la difesa
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'vendite'
        AND c.relname IN ('listini', 'listini_versioni')
        AND c.relrowsecurity
        AND NOT c.relforcerowsecurity),
    2,
    '1. RLS abilitata e NON forzata su listini e listini_versioni'
);

-- ⛔ `FOR SELECT` sarebbe attivamente sbagliata: e' deny-all in scrittura, e
--   `INSERT ... RETURNING` passa comunque dalla USING. La famiglia usa FOR ALL.
SELECT is(
    (SELECT count(*)::int FROM pg_policy p
      WHERE p.polrelid IN ('vendite.listini'::regclass,
                           'vendite.listini_versioni'::regclass)
        AND p.polcmd = '*'),
    2,
    '2. le policy sono FOR ALL, non FOR SELECT (che sarebbe deny-all in scrittura)'
);

-- ⭐ I DUE MODI sono diversi apposta: il listino porta l'emittente, la versione
--   lo eredita dal padre. Asserire solo «c'e' un guard» lascerebbe passare un
--   guard montato col modo sbagliato, che risolverebbe sempre NULL — cioe' un
--   guard spento che sembra acceso.
SELECT is(
    -- ⚠️ `tgargs` e' un `bytea`: castato a text esce in esadecimale, e il
    --   confronto fallirebbe con un messaggio illeggibile. `encode(...,
    --   'escape')` restituisce i due argomenti separati da \000.
    (SELECT string_agg(c.relname || ':' || encode(t.tgargs, 'escape'),
                       ' | ' ORDER BY c.relname)
       FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
       JOIN pg_proc f ON f.oid = t.tgfoid
      WHERE n.nspname = 'vendite'
        AND c.relname IN ('listini', 'listini_versioni')
        AND NOT t.tgisinternal
        AND f.proname = 'trgfn_guard_emittente_scope'),
    'listini:soggetto_ruolo\000emittente_soggetto_ruolo_id\000 | listini_versioni:listino\000listino_id\000',
    '3. il guard c''e'' su entrambe, col modo giusto per ciascuna'
);

-- ============================================================
-- Fixture: un listino di UN ALTRO emittente, e la sua versione
-- ============================================================
-- ⭐ Si passa dal SUPER ADMIN, e non e' una scorciatoia: creare un documento
--   fuori dal proprio perimetro e' esattamente cio' che l'operatore non puo'
--   fare (lo prova il test 7), e il super admin e' l'unico attore che puo'.
--   La fixture si mette nei panni di chi potrebbe davvero costruire questo
--   mondo, poi torna operatore.
DO $fixture$
DECLARE
    v_super       integer;   -- ⚠️ niente %TYPE su django.*
    v_altro_sr    anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_listino_id  vendite.listini.id%TYPE;
BEGIN
    SELECT m.soggetto_ruolo_id INTO v_altro_sr FROM _mondi m WHERE m.lato = 'ALTRUI';
    SELECT m.auth_user_id      INTO v_super    FROM _mondi m WHERE m.lato = 'SA';

    PERFORM script.fn_pgtap_set_contesto_operatore(v_super);

    INSERT INTO vendite.listini
        (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP-LIST-ALTRUI-' || substring(md5(clock_timestamp()::text) from 1 for 6),
           'listino di un altro emittente, per il test di perimetro',
           (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1),
           (SELECT t.id FROM config.listini_tipologie t ORDER BY t.id LIMIT 1),
           v_altro_sr
    RETURNING id INTO v_listino_id;

    -- ⚠️ `validita` e' una colonna GENERATA: non si scrive.
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
    VALUES (v_listino_id, 'V-PGTAP', script.fn_data_operativa());

    PERFORM set_config('pgtap.listino_altrui', v_listino_id::text, true);
END
$fixture$;

-- ⛔ QUI, E ANCORA IN CONTESTO SUPER ADMIN. Non e' una sfumatura.
--   `trgfn_child_requires_active_parent` su `listini_versioni` legge il listino
--   padre, ed e' DIFFERITO: non scatta all'INSERT, scatta quando i vincoli
--   vengono verificati. E li' legge SOTTO LA RLS, col contesto attivo IN QUEL
--   MOMENTO — non con quello in cui la riga e' stata scritta.
--   ⇒ Tornando operatore prima di questa riga, il padre diventa invisibile e il
--     guard alza «Padre non attivo» su un listino perfettamente attivo: un rosso
--     che sembra un difetto della fixture e invece e' la RLS che funziona.
--   ⚠️ Vale per qualunque fixture che cambi attore: i vincoli differiti si
--     chiudono nei panni di chi ha scritto.
SET CONSTRAINTS ALL IMMEDIATE;

-- Si torna all'operatore normale: da qui in poi si collauda cio' che vede e
-- cio' che puo' fare LUI.
DO $torna$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'MIA'));
END $torna$;

-- Un listino NEL PROPRIO perimetro, per il test 6: lo scrive l'operatore
-- stesso, che e' esattamente cio' che il test vuole vedere passare.
CREATE TEMP TABLE _mio_listino AS
WITH l AS (
    INSERT INTO vendite.listini
        (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP-LIST-MIO-' || substring(md5(clock_timestamp()::text) from 1 for 6),
           'listino del proprio emittente, per il test di scrittura',
           (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1),
           (SELECT t.id FROM config.listini_tipologie t ORDER BY t.id LIMIT 1),
           (SELECT m.soggetto_ruolo_id FROM _mondi m WHERE m.lato = 'MIA')
    RETURNING id
)
SELECT id AS listino_id FROM l;

-- ============================================================
-- 4..5. La policy NASCONDE
-- ============================================================
SELECT is_empty(
    format($$SELECT 1 FROM vendite.listini WHERE id = %s$$,
           current_setting('pgtap.listino_altrui')),
    '4. l''operatore non vede il listino di un altro emittente'
);

-- ⭐ Il percorso nuovo: la versione non ha una colonna emittente, quindi se il
--   padre e' fuori perimetro deve sparire anche lei. E' il fail-closed che
--   `fn_scope_ef_whitelist_via_listino` produce per costruzione, non per caso.
SELECT is_empty(
    format($$SELECT 1 FROM vendite.listini_versioni WHERE listino_id = %s$$,
           current_setting('pgtap.listino_altrui')),
    '5. e non vede le VERSIONI di quel listino: il perimetro passa dal padre'
);

-- ============================================================
-- 6. Cio' che deve continuare a passare
-- ============================================================
-- Prima del rifiuto va provato il consenso: una difesa che nega tutto
-- passerebbe i test 4, 5 e 7 senza essere corretta.
SELECT lives_ok(
    $$UPDATE vendite.listini
         SET descrizione = descrizione
       WHERE id = (SELECT listino_id FROM _mio_listino)$$,
    '6. una scrittura nel proprio perimetro passa'
);

-- ============================================================
-- 7. ⛔ Il guard RIFIUTA E SPIEGA
-- ============================================================
-- ⭐ Qui si vede la differenza fra i due meccanismi, ed e' il motivo per cui
--   servono entrambi: la policy da sola direbbe «new row violates row-level
--   security policy», che e' vero e inservibile. Il guard scatta BEFORE, quindi
--   parla per primo e nomina utente ed emittente.
-- ⚠️ Non si usa `throws_ok` con solo lo SQLSTATE: TUTTI gli errori applicativi
--   passano da `fn_log_and_raise_error` e sono `P0001`, quindi sarebbe verde
--   anche se a fermare la riga fosse un guard qualunque. Si chiede lo stato E
--   il messaggio, che il messaggio porta dentro gli id e non e' asseribile alla
--   lettera.
DO $prova$
DECLARE
    v_esito text := 'non-sollevato';
BEGIN
    BEGIN
        INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
        VALUES (current_setting('pgtap.listino_altrui')::bigint,
                'V-PGTAP-INTRUSO', script.fn_data_operativa());
    EXCEPTION WHEN OTHERS THEN
        v_esito := SQLSTATE || '|' ||
                   CASE WHEN SQLERRM ILIKE '%scope emittente fiscale%'
                        THEN 'scope' ELSE 'altro:' || left(SQLERRM, 60) END;
    END;

    PERFORM set_config('pgtap.esito7', v_esito, true);
END
$prova$;

SELECT is(
    current_setting('pgtap.esito7', true),
    'P0001|scope',
    '7. appendere una versione al listino di un altro si ferma, e SPIEGA'
);

-- ============================================================
-- 8. Il presidio
-- ============================================================
-- ⭐ E' la ragione per cui questo lavoro esiste: la vista nominava
--   `vendite.listini_versioni` come bersaglio di dominio senza difesa, e adesso
--   non deve piu'. ⚠️ L'altra riga che la vista porta —
--   `vendite.fatture_stampa_coda` — e' un residuo distinto (DB-6) e non si
--   asserisce qui: pretendere la vista VUOTA renderebbe questo test rosso per
--   un lavoro che non e' suo.
SELECT is_empty(
    $$SELECT 1 FROM dbops.vw_processi_dominio_senza_difesa
       WHERE schema_tabella = 'vendite'
         AND nome_tabella LIKE 'listini%'$$,
    '8. il presidio non nomina piu'' la famiglia listino'
);

SELECT * FROM finish();

ROLLBACK;
