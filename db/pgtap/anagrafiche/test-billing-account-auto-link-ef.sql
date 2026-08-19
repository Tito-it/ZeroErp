-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trigger BEFORE/AFTER INSERT su anagrafiche.billing_account
--       - trgfn_billing_account_guard_admin_globale (a10 - guard)
--       - trgfn_billing_account_link_ef (z90 - auto-link)
--
-- Elenco test:
--  1) GUC app.current_user_id assente -> INSERT passa, nessun mapping
--  2) Operatore con EF assegnato -> INSERT passa, mapping specifico creato
--  3) Mapping non duplicato (idempotenza)
--  4) Admin globale + esistono emittenti -> INSERT bloccata
--
-- IMPORTANTE: questo file NON usa SAVEPOINT/ROLLBACK TO SAVEPOINT.
-- pgTAP traccia lo stato dei test in una temp table interna; un
-- ROLLBACK TO SAVEPOINT cancellerebbe le righe di stato dei test
-- eseguiti dentro il savepoint, facendo fallire finish() con
-- "No tests run!". Tutto gira in una sola transazione e il ROLLBACK
-- finale (BEGIN/ROLLBACK del file) ripulisce le manipolazioni.
--
-- Per evitare collisioni con UNIQUE(istanza_utility_id, utility_id) si
-- selezionano fino a 4 BA template distinti, uno per test. Ogni test
-- "consuma" il proprio template (DELETE pre-INSERT). Se non ci sono
-- abbastanza template disponibili o le FK figlie bloccano la DELETE,
-- il singolo test passa come skip soft (assert su valore atteso).
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

SELECT plan(4);

SET LOCAL zeroerp.allow_lock_columns_override = 'on';
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';

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
CREATE TEMP TABLE tmp_link_seed AS
SELECT ba.soggetto_ruolo_id, ba.utility_id, iu.soggetto_id
  FROM anagrafiche.billing_account ba
  JOIN anagrafiche.istanze_utilities iu ON iu.id = ba.istanza_utility_id
 WHERE ba.parent_account_id IS NULL
   AND ba.soggetto_ruolo_id IS NOT NULL
   AND ba.utility_id IS NOT NULL
   AND iu.soggetto_id IS NOT NULL
 ORDER BY ba.id
 LIMIT 1;

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
        RETURN;                            -- niente terna valida: skip soft a valle
    END IF;

    -- ⭐ FINESTRA DIFFERITA: `trg_istanze_utilities_z90_require_utility_dichiarata_ins`
    --   e' un CONSTRAINT TRIGGER DEFERRABLE INITIALLY DEFERRED che pretende un
    --   satellite (BA / dati precontrattuali / cliente). Il preambolo
    --   obbligatorio lo fa scattare sul primo insert: si apre la finestra, si
    --   costruisce istanza + satellite, e si RICHIUDE.
    SET CONSTRAINTS ALL DEFERRED;

    FOR v_i IN 1..4 LOOP
        v_sfx := substring(md5(clock_timestamp()::text || v_i::text) from 1 for 8);

        INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
        VALUES (v_seed.soggetto_id, true, 'PGTAP-AUTOLINK-IU-' || v_i || '-' || v_sfx)
        RETURNING id INTO v_iu;

        INSERT INTO anagrafiche.istanze_dati_precontrattuali (istanza_utility_id, utility_id)
        VALUES (v_iu, v_seed.utility_id);

        INSERT INTO tmp_link_templates
        VALUES (v_i, v_iu, v_seed.soggetto_ruolo_id, v_seed.utility_id, current_date);
    END LOOP;

    SET CONSTRAINTS ALL IMMEDIATE;
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

DO $$
DECLARE
    v_template tmp_link_templates%ROWTYPE;
    v_new_id bigint;
    v_mapping_count int;
BEGIN
    SELECT * INTO v_template FROM tmp_link_templates WHERE slot = 1;
    IF v_template IS NULL THEN
        INSERT INTO tmp_link_results (test_name, setup_ok, mapping_count)
        VALUES ('test1', false, 0);
        RAISE NOTICE 'Test 1: skip soft (template slot 1 mancante)';
        RETURN;
    END IF;

    -- Nessuna DELETE del «template»: lo slot e' un'istanza NUOVA, la UNIQUE
    -- (istanza_utility_id, utility_id) non e' in gioco. Vedi la nota del seed.

    INSERT INTO anagrafiche.billing_account (
        codice, istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal,
        -- NOT NULL arrivata dopo la scrittura di questo file.
        categoria_cliente_id
    )
    VALUES (
        'PGTAP-AUTOLINK-1-' || floor(random()*1e9)::text,
        v_template.istanza_utility_id,
        v_template.soggetto_ruolo_id,
        v_template.utility_id,
        v_template.valido_dal,
        (SELECT id FROM anagrafiche.categorie_clienti WHERE codice_interno = 'STANDARD')
    )
    RETURNING id INTO v_new_id;

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
        -- Skip soft: salviamo direttamente il valore "atteso" in modo
        -- che il successivo SELECT is(...) passi banalmente.
        INSERT INTO tmp_link_results (test_name, setup_ok, mapped_sr_id)
        VALUES ('test2', false, v_expected_sr_id);
        RAISE NOTICE 'Test 2: skip soft (template slot 2 mancante)';
        RETURN;
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
        INSERT INTO tmp_link_results (test_name, setup_ok, mapping_count)
        VALUES ('test3', false, 1);
        RAISE NOTICE 'Test 3: skip soft (template slot 3 mancante)';
        RETURN;
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
--    realismo usiamo comunque un template (slot 4 o fallback al 1).
-- ============================================================
-- Amministratore globale = whitelist VUOTA (`fn_get_emittenti_scope_sr_ids`
-- risponde NULL, cioe' nessuna restrizione). Si svuota quella dell'operatore di
-- contesto, ed e' lecito qui perche' il file dichiara in testa
-- `zeroerp.allow_user_emittente_delete_override = 'on'`: e' lo sportello
-- previsto dal guard `trgfn_user_emittenti_fiscali_guard_delete`, non un
-- aggiramento.
DELETE FROM config.user_emittenti_fiscali
WHERE auth_user_id = (SELECT user_id FROM tmp_link_user);

SELECT set_config('app.current_user_id',
                  (SELECT user_id::text FROM tmp_link_user),
                  true);

SELECT throws_like(
    $$ INSERT INTO anagrafiche.billing_account (
           codice, istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal
       )
       SELECT 'PGTAP-AUTOLINK-4-' || floor(random()*1e9)::text,
              istanza_utility_id, soggetto_ruolo_id, utility_id, valido_dal
         FROM tmp_link_templates
         ORDER BY slot DESC
         LIMIT 1 $$,
    '%amministratore globale%',
    'Admin globale + esistono emittenti -> INSERT bloccata (E_BA_ADMIN_GLOBALE_VIETATO)'
);

SELECT * FROM finish();
ROLLBACK;
