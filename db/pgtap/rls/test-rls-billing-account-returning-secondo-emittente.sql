-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: come `zeroerp_app`, l'operatore di un emittente NON di default crea
--   un billing account con `INSERT … RETURNING id` — il caso di prodotto D13.
-- Brief: brief-db-ba-riserva-emittente-operatore-d13.md
-- ChangeSet: 20_code/script/20260913-01 (la riserva in sessione del resolver)
--
-- Elenco test (plan 10):
--   0) PRECONDIZIONE: B NON e' l'emittente di default — il caso esiste
--   1) ⭐ INSERT … RETURNING id come operatore di B: vive
--   2) l'id restituito e' la riga scritta, e la riga si vede
--   3) il legame lo ha scritto il trigger z90, verso B
--   4) la riserva IN SESSIONE su un BA senza legame risponde B, non il default
--   5) ⛔ il perimetro non si allarga: l'operatore di A non vede il BA di B
--   6) gemello: SENZA sessione la riserva e' ancora il default
--   7) ...e senza sessione il BA legato risponde comunque B (il livello 1 vince)
--   8) postura: RLS accesa e NON forzata su anagrafiche.billing_account
--   9) postura: la policy di lettura e' FOR ALL — il RETURNING passa dalla USING
--
-- Scopo:
--  ⛔ Il difetto (trovato il 2026-09-12, riprodotto su dbdev con un operatore
--     vero dell'emittente 44): `INSERT INTO anagrafiche.billing_account …
--     RETURNING id` moriva con «la nuova riga viola la regola di sicurezza per
--     riga» (42501) ogni volta che l'emittente di chi agisce non era quello di
--     default. La policy di lettura risolve il BA dal legame in
--     emittenti_fiscali_billing_account; il legame lo scrive il trigger AFTER
--     `z90_link_ef`, cioe' DOPO che il RETURNING ha chiesto di vedere la riga;
--     nel frattempo il resolver ricadeva sul DEFAULT — un'altra azienda.
--     Sull'emittente di default passava, ed e' il motivo per cui nessuno l'ha
--     visto: il backend fa lo stesso RETURNING (clienti_repository,
--     create_billing_account) ⇒ con due emittenti in esercizio gli operatori
--     del secondo non aprivano clienti.
--  ⭐ La decisione (Tid, 2026-09-12): un BA non ancora collegato appartiene a
--     chi lo sta creando — la riserva del resolver passa dal default
--     all'emittente dell'operatore in sessione; il default resta solo senza
--     sessione. Questo file e' il caso di prodotto: ROSSO al test 1 prima del
--     20260913-01, VERDE dopo. Il 6 e il 7 sono i gemelli che dicono che il
--     default non e' sparito e che il livello 1 non e' stato toccato.
--  ⚠️ DUE aziende costruite, e il contesto e' quello di B: sullo scratch della
--     CI il PRIMO emittente creato diventa il default (bootstrap), quindi A lo
--     e' e B no; su dbdev il default e' un terzo (32) e B non lo e' comunque.
--     Il test 0 lo asserisce invece di darlo per scontato: senza quella
--     condizione il test 1 passerebbe anche col resolver vecchio.
--  ⚠️ Runner APPLICATIVO, e non e' un dettaglio: il soggetto del test e'
--     esattamente il percorso dell'applicazione sotto RLS. Da owner (senza
--     FORCE) il RETURNING passerebbe sempre e il file non misurerebbe niente:
--     i test 8 e 9 rendono quel presupposto un'asserzione.
--  ⚠️ Il BA si scrive A MANO, con RETURNING, e non con
--     dbops.fn_pgtap_crea_cliente_ba: dalla rev 20260912-38 l'helper il
--     RETURNING NON lo fa apposta (rilegge dal codice), quindi passerebbe anche
--     col difetto vivo. La catena sotto il BA (soggetto, ruolo CL, istanza) e'
--     invece quella dell'helper, riga per riga.
-- ------------------------------------------------------------

BEGIN;

-- ⛔ LE DUE AZIENDE SI COSTRUISCONO, in DUE istruzioni: l'ordine di creazione
--   e' portante (sullo scratch la prima diventa il default), e in una UNION
--   ALL l'ordine dei rami e' del planner, non del test.
CREATE TEMP TABLE _mondi AS
SELECT 'A'::text AS lato, m.*
  FROM dbops.fn_pgtap_crea_emittente_operatore() m;

INSERT INTO _mondi
SELECT 'B'::text, m.*
  FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- Contesto applicativo: l'operatore di B (ruolo OPERATORE + RLS attiva).
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'B'));
END $ctx$;

-- ⚠️ L'helper esce gia' con i vincoli IMMEDIATE; la riga sta qui perche' e'
--   il preambolo obbligatorio, e perche' la fixture del cliente li riapre e li
--   richiude da sola.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Fixture: la catena SOTTO il billing account (soggetto -> ruolo CL ->
-- istanza), la stessa di dbops.fn_pgtap_crea_cliente_ba. Il BA NO: quello
-- e' il soggetto del test 1 e si scrive li', con RETURNING.
-- ============================================================
CREATE TEMP TABLE _t_fix (
    istanza_utility_id   bigint,
    soggetto_ruolo_id    bigint,
    utility_id           integer,
    codice               character varying,
    categoria_cliente_id smallint,
    valuta_id            integer
);

DO $fix$
DECLARE
    v_soggetto_id anagrafiche.soggetti.id%TYPE;
    v_sr_id       anagrafiche.soggetti_ruoli.id%TYPE;
    v_ist_id      anagrafiche.istanze_utilities.id%TYPE;
    v_utility_id  config.utilities.id%TYPE;
    v_codice      anagrafiche.billing_account.codice%TYPE;
BEGIN
    SELECT u.id INTO v_utility_id FROM config.utilities u ORDER BY u.id LIMIT 1;
    IF v_utility_id IS NULL THEN
        RAISE EXCEPTION 'fixture: nessuna utility a catalogo';
    END IF;

    -- Codice libero: `codice` e' UNIQUE su billing_account e su
    -- istanze_utilities, senza filtro su nessuno stato.
    v_codice := 'PGTAPD13' || substring(md5(clock_timestamp()::text) from 1 for 8);

    v_soggetto_id := dbops.fn_pgtap_crea_soggetto_pg('Cliente D13 ' || v_codice);
    v_sr_id       := dbops.fn_pgtap_crea_soggetto_ruolo(v_soggetto_id, 'CL'::character varying);

    -- ⛔ LA FINESTRA DIFFERITA: `trg_istanze_utilities_z90_require_utility_dichiarata_ins`
    --   vuole il billing account e con i vincoli IMMEDIATE scatterebbe
    --   sull'INSERT dell'istanza. ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba,
    --   R-1): fino a quel giorno la fixture si completava con una riga
    --   precontrattuale, e l'istanza viveva senza BA. Ora quella riga pretende
    --   il BA della sua coppia, e il BA e' il SOGGETTO del test 1: la finestra
    --   resta APERTA fino al test 1 e si richiude subito dopo (vedi sotto),
    --   quando l'istanza ha il suo BA. E' la forma vera dell'operazione: istanza
    --   e BA nella stessa transazione.
    SET CONSTRAINTS ALL DEFERRED;

    -- `fittizia = true`: chk_istanza_fittizia_indirizzo vuole O il flag O un
    -- indirizzo di dettaglio, e a una fixture l'indirizzo non serve.
    INSERT INTO anagrafiche.istanze_utilities (codice, soggetto_id, fittizia)
    VALUES (v_codice, v_soggetto_id, true)
    RETURNING id INTO v_ist_id;

    INSERT INTO _t_fix
    VALUES (v_ist_id, v_sr_id, v_utility_id, v_codice,
            (SELECT cc.id FROM anagrafiche.categorie_clienti cc
              WHERE cc.codice_interno = 'STANDARD'),
            (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1));
END $fix$;

-- Un billing_account_id che NON esiste: esercita la riserva (livelli 2 e 3)
-- senza leggere anagrafiche.billing_account, che ha la RLS — un conteggio li'
-- sopra misurerebbe la policy, non il resolver.
CREATE TEMP TABLE _t_ba_ignoto ON COMMIT DROP AS
SELECT COALESCE(MAX(efba.billing_account_id), 0) + 1000000 AS ba_id
  FROM anagrafiche.emittenti_fiscali_billing_account efba;

-- Dove atterra l'id restituito dal RETURNING: e' la cosa che il backend
-- legge con fetchone(), e il test 2 la confronta con la riga.
CREATE TEMP TABLE _t_nuovo (billing_account_id bigint);

-- ============================================================
-- Asserzioni
-- ============================================================

-- 0) Senza questa condizione il test 1 passerebbe anche col resolver vecchio:
--    e' cio' che rende il caso un caso.
SELECT ok(
    NOT EXISTS (
        SELECT 1
          FROM anagrafiche.emittenti_fiscali_billing_account d
         WHERE d.is_default
           AND d.emittente_soggetto_ruolo_id
                   = (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'B')),
    '0. PRECONDIZIONE: B non e'' l''emittente di default — il caso esiste'
);

-- 1) ⭐ Il caso di prodotto: la stessa istruzione di
--    clienti_repository.create_billing_account, come operatore di B.
--    Prima del 20260913-01: 42501, «la nuova riga viola la regola di sicurezza».
SELECT lives_ok(
    $sql$
    DO $ins$
    DECLARE
        v_id anagrafiche.billing_account.id%TYPE;
    BEGIN
        INSERT INTO anagrafiche.billing_account
            (istanza_utility_id, soggetto_ruolo_id, utility_id,
             codice, categoria_cliente_id, valuta_id)
        SELECT f.istanza_utility_id, f.soggetto_ruolo_id, f.utility_id,
               f.codice, f.categoria_cliente_id, f.valuta_id
          FROM _t_fix f
        RETURNING id INTO v_id;

        INSERT INTO _t_nuovo (billing_account_id) VALUES (v_id);
    END $ins$
    $sql$,
    '1. * INSERT ... RETURNING id come operatore di B: vive (rosso prima del 20260913-01)'
);

-- La finestra differita si richiude QUI: l'istanza della fixture ha ora il suo
-- billing account (test 1), e il constraint trigger lo verifica. Se il test 1
-- e' morto, l'istanza e' senza BA e il file si ferma su E_ISTANZA_SENZA_BA:
-- il rosso del test 1 e' gia' stampato sopra.
SET CONSTRAINTS ALL IMMEDIATE;

-- 2) L'id restituito e' la riga appena scritta, e la riga si VEDE: sotto la
--    RLS «scritta» e «visibile» non sono la stessa cosa, ed e' tutto il punto.
SELECT is(
    (SELECT count(*)::int
       FROM anagrafiche.billing_account b
       JOIN _t_nuovo n ON n.billing_account_id = b.id
       JOIN _t_fix   f ON f.codice = b.codice),
    1,
    '2. l''id restituito e'' la riga scritta, e la riga si vede come operatore di B'
);

-- 3) Il legame lo ha scritto il trigger z90, verso l'azienda di chi agiva —
--    la riserva ha detto in anticipo cio' che il trigger ha poi scritto.
SELECT is(
    (SELECT efba.emittente_soggetto_ruolo_id
       FROM anagrafiche.emittenti_fiscali_billing_account efba
       JOIN _t_nuovo n ON n.billing_account_id = efba.billing_account_id
      WHERE NOT efba.is_default),
    (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'B'),
    '3. il legame scritto dal trigger z90 e'' verso B'
);

-- 4) La riserva, isolata: un BA senza legame, in sessione, e' di chi agisce.
--    E' il livello 2 del resolver, quello che prima non esisteva.
SELECT is(
    script.fn_get_ba_emittente_sr_id((SELECT ba_id FROM _t_ba_ignoto)),
    (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'B'),
    '4. BA senza legame, in sessione -> l''emittente dell''operatore (B), non il default'
);

-- 5) ⛔ Il perimetro non si e' allargato: come operatore di A, il BA di B non
--    c'e'. Il legame (livello 1) vince sulla sessione (livello 2).
SELECT set_config('app.current_user_id',
                  (SELECT auth_user_id::text FROM _mondi WHERE lato = 'A'),
                  true);

SELECT is(
    (SELECT count(*)::int
       FROM anagrafiche.billing_account b
       JOIN _t_nuovo n ON n.billing_account_id = b.id),
    0,
    '5. come operatore di A il BA di B NON si vede: il perimetro non si allarga'
);

-- 6) Il gemello: senza sessione (batch, manutenzione) la riserva e' ancora il
--    default dell'installazione — il livello 3 non e' sparito.
SELECT set_config('app.current_user_id', '', true);

SELECT is(
    script.fn_get_ba_emittente_sr_id((SELECT ba_id FROM _t_ba_ignoto)),
    (SELECT d.emittente_soggetto_ruolo_id
       FROM anagrafiche.emittenti_fiscali_billing_account d
      WHERE d.is_default),
    '6. BA senza legame, SENZA sessione -> l''emittente di default (livello 3)'
);

-- 7) ...e un BA legato risponde il suo emittente anche senza sessione: il
--    livello 1 non dipende da chi guarda.
SELECT is(
    script.fn_get_ba_emittente_sr_id((SELECT billing_account_id FROM _t_nuovo)),
    (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'B'),
    '7. BA legato, senza sessione -> B: il livello 1 vince su tutto'
);

-- ============================================================
-- La postura: il presupposto per cui il test 1 misura qualcosa
-- ============================================================
-- 8) Con la RLS spenta, o forzata sull'owner, il test 1 direbbe un'altra cosa.
SELECT is(
    (SELECT count(*)::int
       FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'anagrafiche'
        AND c.relname = 'billing_account'
        AND c.relrowsecurity
        AND NOT c.relforcerowsecurity),
    1,
    '8. RLS accesa e NON forzata su anagrafiche.billing_account'
);

-- 9) Il RETURNING passa dalla USING della policy di LETTURA: e' FOR ALL.
--    Una FOR SELECT sarebbe deny-all in scrittura, e una policy diversa da
--    questa sposterebbe il punto in cui il difetto si manifesta.
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_policy p
         WHERE p.polrelid = 'anagrafiche.billing_account'::regclass
           AND p.polname  = 'rls_billing_account_ef_whitelist'
           AND p.polcmd   = '*'),
    '9. la policy di lettura rls_billing_account_ef_whitelist e'' FOR ALL'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
