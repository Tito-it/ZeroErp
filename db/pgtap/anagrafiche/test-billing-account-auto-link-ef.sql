-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trigger BEFORE/AFTER INSERT su anagrafiche.billing_account
--       - trgfn_billing_account_guard_admin_globale (a10 - guard)
--       - trgfn_billing_account_link_ef (z90 - auto-link)
--
-- Elenco test:
--  1) GUC app.current_user_id assente -> INSERT passa, nessun mapping
--     (rev 2026-10-04: senza RETURNING, vedi il test)
--  2) Operatore con EF assegnato -> INSERT passa, mapping specifico creato
--  3) Mapping non duplicato (idempotenza)
--  4) Super admin senza emittente di lavoro + esistono emittenti -> INSERT bloccata
--
-- IMPORTANTE: questo file NON usa SAVEPOINT/ROLLBACK TO SAVEPOINT.
-- pgTAP traccia lo stato dei test in una temp table interna; un
-- ROLLBACK TO SAVEPOINT cancellerebbe le righe di stato dei test
-- eseguiti dentro il savepoint, facendo fallire finish() con
-- "No tests run!". Tutto gira in una sola transazione e il ROLLBACK
-- finale (BEGIN/ROLLBACK del file) ripulisce le manipolazioni.
--
-- Per evitare collisioni con UNIQUE(istanza_utility_id, utility_id) ogni
-- test ha la sua istanza utility NUOVA (quattro slot), costruita sulla
-- terna di un cliente costruito.
-- ------------------------------------------------------------

-- ============================================================================
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   Su un database ricostruito (la CI) il file era 3 verdi FINTI e 1 rosso:
--   1. la terna (ruolo, utility, soggetto) si PESCAVA dal primo billing
--      account esistente: da zero non ce n'e', i quattro slot restavano
--      vuoti, e i test 1-3 finivano nello «skip soft» — che scriveva il
--      valore ATTESO e passava senza aver inserito niente (verde per
--      sottrazione);
--   2. il test 4 inseriva da una tabella di slot vuota: zero righe, nessuna
--      eccezione, rosso.
--   E il test 4 aveva un secondo difetto, indipendente: «amministratore
--   globale» lo otteneva SVUOTANDO la whitelist dell'operatore di contesto
--   (con lo sportello allow_user_emittente_delete_override). Ma dopo P-2a
--   (2026-08-18) un operatore senza whitelist non e' un admin globale: e'
--   fail-closed. L'admin globale del modello e' il SUPER ADMIN, che nasce
--   senza azienda — nessuna riga in user_emittenti_fiscali, ed e' questo che
--   script.fn_check_user_can_create_ba legge.
--   Ora: la terna viene da dbops.fn_pgtap_crea_cliente_ba, i rami «skip
--   soft» sollevano (uno slot mancante e' un difetto della fixture, non un
--   caso), e il test 4 agisce come un super admin costruito con
--   dbops.fn_pgtap_crea_operatore_umano(..., p_super_admin := true).
--
-- rev 2026-09-26 (brief-db-messaggio-ba-senza-emittente).
--   Il test 4 riconosceva il rifiuto dal TESTO ('%amministratore globale%'):
--   riscritto il messaggio (id 358) sulla regola vera, il test sarebbe
--   diventato rosso senza che il guard cambiasse. Ora legge il CODICE dal
--   canale CONSTRAINT (contratto P0001 + CONSTRAINT = codice): la frase
--   per l'operatore e' del catalogo, non del test.
-- ============================================================================

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

SELECT plan(4);

SET LOCAL zeroerp.allow_lock_columns_override = 'on';

-- ============================================================
-- Setup contesto
-- ============================================================
-- L'emittente NON e' «il primo attivo»: e' quello dell'operatore che il
-- preambolo ha messo in sessione. Con due emittenti in whitelist diverse, «il
-- primo attivo» e' una scommessa che il perimetro non conferma.
CREATE TEMP TABLE tmp_link_ctx AS
SELECT
    ef.id                AS emittente_pk,
    ef.soggetto_ruolo_id AS emittente_sr_id
FROM anagrafiche.emittenti_fiscali ef
WHERE ef.id = script.fn_pgtap_emittente_operatore();

-- L'OPERATORE e' quello che il preambolo ha messo in sessione, non uno cercato
-- a mano.
--
-- ⚠️ Il file lo cercava con `risorse_umane_auth_user.ruolo_sistema <> 'DISABILITATO'`,
--   e quella colonna e' stata RITIRATA (non c'e' la colonna, non c'e' il tipo
--   enum che la tipizzava): era la ragione per cui questo file moriva alla prima
--   istruzione, con ZERO asserzioni eseguite.
--
-- ⭐ E non si sostituisce creando un utente Django nuovo: senza un'identita'
--   OPERATORE attiva lo scope emittenti di un utente e' `{}`, cioe' fail-closed
--   (`script.fn_get_emittenti_scope_sr_ids`), e non passerebbe nemmeno la
--   rilettura del BA appena inserito. L'operatore di contesto ha per costruzione
--   identita' attiva e whitelist: rifargli la saga del soggetto non aggiunge
--   niente al test.
CREATE TEMP TABLE tmp_link_user AS
SELECT NULLIF(current_setting('app.current_user_id', true), '')::integer AS user_id;

-- QUATTRO SLOT = quattro istanze utility NUOVE, una per test.
--
-- ⚠️ PRIMA ERANO QUATTRO BA ESISTENTI, PRESI IN PRESTITO E CANCELLATI. Servivano
--   solo per la loro terna (istanza, soggetto_ruolo, utility): il test inserisce
--   un BA nuovo, e la DELETE del «template» era li' per liberare
--   UNIQUE(istanza_utility_id, utility_id). Oggi quella DELETE non passa piu' —
--   le FK figlie la bloccano — e i tre DO la catturavano finendo in «skip soft»:
--   il file risultava con asserzioni che passavano senza aver inserito niente.
--   ⭐ E' la premessa decaduta della suite: si smette di cancellare e si smette
--   di collidere. Ogni slot ha la sua istanza, quindi la UNIQUE non e' mai in
--   gioco e le tre asserzioni tornano a misurare l'auto-link.
-- La terna (ruolo CL, utility, soggetto) viene da un cliente COSTRUITO: con
-- il contesto aperto, senza terzo parametro (il legame lo scrive il trigger
-- z90 verso l'emittente di chi agisce).
CREATE TEMP TABLE tmp_link_seed AS
SELECT soggetto_ruolo_id, utility_id, soggetto_id
  FROM dbops.fn_pgtap_crea_cliente_ba('auto-link EF');

CREATE TEMP TABLE tmp_link_templates (
    slot               int,
    istanza_utility_id bigint,
    soggetto_ruolo_id  bigint,
    utility_id         integer,
    valido_dal         date
);

DO $seed$
DECLARE v_seed record; v_iu bigint; v_i int; v_sfx text;
BEGIN
    SELECT * INTO v_seed FROM tmp_link_seed;
    IF v_seed IS NULL THEN
        RAISE EXCEPTION 'Setup: il cliente costruito non ha dato la terna (ruolo, utility, soggetto)';
    END IF;

    -- ⭐ FINESTRA DIFFERITA: `trg_istanze_utilities_z90_require_utility_dichiarata_ins`
    --   e' un CONSTRAINT TRIGGER DEFERRABLE INITIALLY DEFERRED che pretende il
    --   billing account. Il preambolo obbligatorio lo fa scattare sul primo
    --   insert: si apre la finestra qui.
    --   ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-1): fino a quel
    --   giorno ogni istanza si completava con una riga precontrattuale e la
    --   finestra si richiudeva subito. Ora quella riga pretende il BA della sua
    --   coppia, e il BA e' il SOGGETTO dei test 1-3: la finestra resta APERTA e
    --   si richiude in coda al file, quando ogni istanza ha il suo BA. E' la
    --   forma vera dell'operazione: istanza e BA nella stessa transazione.
    --   Lo slot 4 riusa l'istanza dello slot 3: il suo INSERT e' rifiutato dal
    --   guard BEFORE (test 4), quindi un'istanza sua resterebbe senza BA.
    SET CONSTRAINTS ALL DEFERRED;

    FOR v_i IN 1..3 LOOP
        v_sfx := substring(md5(clock_timestamp()::text || v_i::text) from 1 for 8);

        INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
        VALUES (v_seed.soggetto_id, true, 'PGTAP-AUTOLINK-IU-' || v_i || '-' || v_sfx)
        RETURNING id INTO v_iu;

        INSERT INTO tmp_link_templates
        VALUES (v_i, v_iu, v_seed.soggetto_ruolo_id, v_seed.utility_id, script.fn_data_operativa());
    END LOOP;

    INSERT INTO tmp_link_templates
    VALUES (4, v_iu, v_seed.soggetto_ruolo_id, v_seed.utility_id, script.fn_data_operativa());
END $seed$;

-- Tabella di appoggio per i risultati intermedi (creata fuori da qualunque
-- savepoint perche' ne abbiamo eliminati: il ROLLBACK finale la elimina
-- comunque insieme al resto).
CREATE TEMP TABLE tmp_link_results (
    test_name     text PRIMARY KEY,
    setup_ok      boolean NOT NULL DEFAULT false,
    new_ba_id     bigint,
    mapping_count int,
    mapped_sr_id  bigint
);

-- ============================================================
-- 1) GUC app.current_user_id assente -> INSERT passa, 0 mapping
-- ============================================================
SELECT set_config('app.current_user_id', '', true);

-- ⚠️ Rev 2026-10-04 (Q-1, brief-db-esclusioni-implicite): l'id si prende
--   PRIMA, dalla sequenza, e l'INSERT non ha RETURNING. Con la veste OPERATORE
--   e l'utente vuoto la policy di lettura rls_billing_account_ef_whitelist
--   (fn_scope_ef_whitelist_via_efba) risponde ora FALSE — prima diceva TRUE,
--   «attore nullo = nessun filtro» — e il RETURNING, che passa dalla policy di
--   lettura, verrebbe rifiutato. Il soggetto del test resta il trigger
--   d'aggancio: la scrittura passa (WITH CHECK della policy _ins, solo veste),
--   e il mapping si conta su emittenti_fiscali_billing_account, senza RLS.
DO $$
DECLARE
    v_template tmp_link_templates%ROWTYPE;
    v_new_id bigint;
    v_mapping_count int;
BEGIN
    SELECT * INTO v_template FROM tmp_link_templates WHERE slot = 1;
    IF v_template IS NULL THEN
        RAISE EXCEPTION 'Test 1: slot 1 mancante (difetto della fixture)';
    END IF;

    -- Nessuna DELETE del «template»: lo slot e' un'istanza NUOVA, la UNIQUE
    -- (istanza_utility_id, utility_id) non e' in gioco. Vedi la nota del seed.

    v_new_id := nextval('anagrafiche.billing_account_id_seq');

    INSERT INTO anagrafiche.billing_account (
        id, codice, istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal,
        -- NOT NULL arrivata dopo la scrittura di questo file.
        categoria_cliente_id
    )
    VALUES (
        v_new_id,
        'PGTAP-AUTOLINK-1-' || floor(random()*1e9)::text,
        v_template.istanza_utility_id,
        v_template.soggetto_ruolo_id,
        v_template.utility_id,
        v_template.valido_dal,
        (SELECT id FROM anagrafiche.categorie_clienti WHERE codice_interno = 'STANDARD')
    );

    SELECT COUNT(*)::int INTO v_mapping_count
      FROM anagrafiche.emittenti_fiscali_billing_account
     WHERE billing_account_id = v_new_id;

    INSERT INTO tmp_link_results (test_name, setup_ok, new_ba_id, mapping_count)
    VALUES ('test1', true, v_new_id, v_mapping_count);
END $$;

SELECT is(
    (SELECT mapping_count FROM tmp_link_results WHERE test_name = 'test1'),
    0,
    'GUC assente -> nessun mapping auto-creato'
);

-- ============================================================
-- 2) Operatore con EF -> mapping specifico creato
-- ============================================================
-- Nessun INSERT in whitelist: l'operatore di contesto ha gia' la sua riga, ed e'
-- unica per utente (UNIQUE su auth_user_id). `tmp_link_ctx` e' proprio
-- l'emittente che quella riga gli assegna.
SELECT set_config('app.current_user_id',
                  (SELECT user_id::text FROM tmp_link_user),
                  true);

DO $$
DECLARE
    v_template tmp_link_templates%ROWTYPE;
    v_expected_sr_id bigint;
    v_new_id bigint;
    v_mapped_sr_id bigint;
BEGIN
    SELECT * INTO v_template FROM tmp_link_templates WHERE slot = 2;
    SELECT emittente_sr_id INTO v_expected_sr_id FROM tmp_link_ctx;

    IF v_template IS NULL THEN
        RAISE EXCEPTION 'Test 2: slot 2 mancante (difetto della fixture)';
    END IF;

    -- Nessuna DELETE del «template»: lo slot e' un'istanza NUOVA, la UNIQUE
    -- (istanza_utility_id, utility_id) non e' in gioco. Vedi la nota del seed.

    INSERT INTO anagrafiche.billing_account (
        codice, istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal,
        -- NOT NULL arrivata dopo la scrittura di questo file.
        categoria_cliente_id
    )
    VALUES (
        'PGTAP-AUTOLINK-2-' || floor(random()*1e9)::text,
        v_template.istanza_utility_id,
        v_template.soggetto_ruolo_id,
        v_template.utility_id,
        v_template.valido_dal,
        (SELECT id FROM anagrafiche.categorie_clienti WHERE codice_interno = 'STANDARD')
    )
    RETURNING id INTO v_new_id;

    SELECT efba.emittente_soggetto_ruolo_id
      INTO v_mapped_sr_id
      FROM anagrafiche.emittenti_fiscali_billing_account efba
     WHERE efba.billing_account_id = v_new_id
       AND efba.is_default = false;

    INSERT INTO tmp_link_results (test_name, setup_ok, new_ba_id, mapped_sr_id)
    VALUES ('test2', true, v_new_id, v_mapped_sr_id);
END $$;

SELECT is(
    (SELECT mapped_sr_id FROM tmp_link_results WHERE test_name = 'test2'),
    (SELECT emittente_sr_id FROM tmp_link_ctx),
    'Operatore con EF -> mapping specifico verso l''emittente atteso'
);

-- ============================================================
-- 3) Idempotenza: 1 sola riga di mapping per BA
-- ============================================================
DO $$
DECLARE
    v_template tmp_link_templates%ROWTYPE;
    v_new_id bigint;
    v_count int;
BEGIN
    SELECT * INTO v_template FROM tmp_link_templates WHERE slot = 3;
    IF v_template IS NULL THEN
        RAISE EXCEPTION 'Test 3: slot 3 mancante (difetto della fixture)';
    END IF;

    -- Nessuna DELETE del «template»: lo slot e' un'istanza NUOVA, la UNIQUE
    -- (istanza_utility_id, utility_id) non e' in gioco. Vedi la nota del seed.

    INSERT INTO anagrafiche.billing_account (
        codice, istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal,
        -- NOT NULL arrivata dopo la scrittura di questo file.
        categoria_cliente_id
    )
    VALUES (
        'PGTAP-AUTOLINK-3-' || floor(random()*1e9)::text,
        v_template.istanza_utility_id,
        v_template.soggetto_ruolo_id,
        v_template.utility_id,
        v_template.valido_dal,
        (SELECT id FROM anagrafiche.categorie_clienti WHERE codice_interno = 'STANDARD')
    )
    RETURNING id INTO v_new_id;

    SELECT COUNT(*)::int INTO v_count
      FROM anagrafiche.emittenti_fiscali_billing_account
     WHERE billing_account_id = v_new_id;

    INSERT INTO tmp_link_results (test_name, setup_ok, new_ba_id, mapping_count)
    VALUES ('test3', true, v_new_id, v_count);
END $$;

SELECT is(
    (SELECT mapping_count FROM tmp_link_results WHERE test_name = 'test3'),
    1,
    'Mapping creato esattamente una volta (idempotenza)'
);

-- ============================================================
-- 4) Admin globale + esistono emittenti -> INSERT bloccata
--    NB: il guard BEFORE solleva PRIMA del check NOT NULL,
--    quindi l'INSERT minimal sarebbe sufficiente. Per maggiore
--    realismo usiamo comunque un template (slot 4).
-- ============================================================
-- Amministratore globale = il SUPER ADMIN, che nasce senza azienda: nessuna
-- riga in user_emittenti_fiscali. Emittenti attivi ce ne sono (quello del
-- mondo). E non sta «dentro» un emittente: app.current_emittente_id vuoto,
-- altrimenti il ramo 1 di fn_check_user_can_create_ba gli darebbe il diritto.
-- ⛔ Il builder scrive; si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_link_sa AS
SELECT auth_user_id
  FROM dbops.fn_pgtap_crea_operatore_umano('auto-link admin globale', p_super_admin := true);

SELECT set_config('app.current_user_id',
                  (SELECT auth_user_id::text FROM tmp_link_sa),
                  true);
SELECT set_config('app.current_emittente_id', '', true);

-- Il codice di dominio di un errore, letto dal canale CONSTRAINT
-- (contratto P0001 + CONSTRAINT = codice). NULL se non solleva.
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

SELECT is(
    pg_temp.codice_errore($$ INSERT INTO anagrafiche.billing_account (
           codice, istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal
       )
       SELECT 'PGTAP-AUTOLINK-4-' || floor(random()*1e9)::text,
              istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal
         FROM tmp_link_templates
        WHERE slot = 4 $$),
    'E_BA_ADMIN_GLOBALE_VIETATO',
    'Super admin senza emittente di lavoro + esistono emittenti -> INSERT bloccata (E_BA_ADMIN_GLOBALE_VIETATO)'
);

-- La finestra differita si richiude QUI: le istanze degli slot 1-3 hanno il
-- loro billing account (test 1-3) e il constraint trigger lo verifica. Se uno
-- dei test e' morto, la sua istanza e' senza BA e il file si ferma su
-- E_ISTANZA_SENZA_BA: il rosso del test e' gia' stampato sopra.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT * FROM finish();
ROLLBACK;
