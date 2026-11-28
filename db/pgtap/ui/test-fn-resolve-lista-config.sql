-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive a mano profili e legami per ruolo, che nessun
--   verbo scrive:
--   dal giro 10-bis le tabelle che danno l'accesso (scope, legami e contenuto dei
--   profili) sono in sola lettura per l'app, e le scrivono solo i verbi del SUPER_ADMIN
--   (brief-db-porte-aperte-dalla-sola-guc §14, giro 10-bis, 2026-11-26).
--   I soggetti del test sono funzioni di lettura delle tabelle di config, che
--   non hanno RLS: il ruolo di connessione non cambia cio' che misurano.
-- pgTAP test per Zero ERP
--
-- Test: ui.fn_resolve_lista_config
-- Funzione: ui.fn_resolve_lista_config(codice, auth_user_id, emittente_fiscale_id)
--
-- Semantica attesa:
--   - Lista inesistente -> errore E_UI_LISTA_NON_TROVATA
--   - Nessuna preferenza, nessun preset -> catalogo grezzo (ordine_default)
--   - Preset di sistema -> applicato correttamente
--   - Preset di profilo -> prevale su preset sistema
--   - Preferenza utente -> prevale su tutto
--   - Colonna sensibile senza grant -> BLOCCATA (non nel risultato)
--   - Colonna sensibile con grant -> presente con livello corretto
--   - Colonna 'identificatore' in preferenza con visibile:false -> normalizzata a true
--   - Nuova colonna non in preferenza salvata -> aggiunta con visibile:false, colonne_nuove++
--
-- Pattern: un operatore umano costruito, la cui veste OPERATORE porta il profilo AD_HOC.
-- ⚠️ Dal 2026-11-28 l'utente e' un OPERATORE costruito (dbops.fn_pgtap_crea_operatore_umano),
--   non piu' una veste CLIENTE_PORTALE: dal 20261127-49 un profilo personale (AD_HOC) si
--   lega solo a una veste OPERATORE (D-G4-2 di brief-db-accessi-area-clienti). Il caso 11
--   lega il profilo PORTALE di prova al tipo OPERATORE; il caso 12 indossa una veste che
--   la credenziale non ha (FORNITORE_PORTALE).
-- BEGIN; + ROLLBACK implicito a fine file.
--
-- Indice test (plan 13; le etichette delle asserzioni, che saltano il 10):
--   1.  Setup dati di test (lista + colonne + utente + identita)
--   2.  Lista inesistente -> eccezione P0001
--   3.  Catalogo grezzo: 2 colonne (sensibile BLOCCATA senza grant)
--   3b. Catalogo grezzo: la sensibile senza grant resta fuori
--   4.  Preset di sistema -> pagina_dimensione=10
--   5.  Preset di profilo -> pagina_dimensione=50 (prevale su sistema)
--   6.  Preferenza utente -> pagina_dimensione=100 (prevale su tutto)
--   7.  Colonna sensibile con grant LETTURA -> esportabile=false
--   8.  Colonna identificatore con visibile:false -> normalizzata a true
--   9.  Nuova colonna nel catalogo non in preferenza -> colonne_nuove=1
--   11. Cascata dei preset di ruolo: AD_HOC (priorita' 1) batte PORTALE (priorita' 3)
--   12. Una veste che la credenziale non ha -> nessun profilo -> preset di sistema
--   13. Ogni colonna dell'output espone la chiave priorita
--
-- ⚠️ Le misure (10, 25, 50, 100) sono scritte a mano: servono quattro misure
--   diverse, e il catalogo per contratto ne garantisce due. Se una esce dal
--   catalogo il guard ferma la fixture (E_UI_MISURA_PAGINA_NON_AMMESSA): un rosso,
--   non un verde a vuoto.
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

-- ⚠️ Due contesti, in ordine, e l'ordine e' il punto.
--   La fixture lavora prima nel contesto dell'operatore di default. Poi, prima
--   delle asserzioni, si indossa la veste che il test collauda davvero —
--   OPERATORE, quella dell'identita' che la fixture ha appena creato, con il
--   suo id nella GUC.
--   E' la «correzione vera» che il commento qui sopra nominava lasciandola al
--   cantiere `ui`: «veste vuota» non e' una condizione che l'applicazione
--   produca mai, quindi collaudarci sopra non misura l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);
-- =========================================================
-- 1. Setup: lista + colonne + auth_user + identita
-- =========================================================
-- Crea la lista di test
CREATE TEMP TABLE _t_lista AS WITH ins AS (
    INSERT INTO ui.lista_definizione (
            codice,
            descrizione,
            schema_dati,
            vista_sql,
            attivo,
            user_insert
        )
    VALUES (
            '_pgtap.test_resolve_' || substr(md5(clock_timestamp()::text), 1, 6),
            'Lista test per pgTAP fn_resolve_lista_config',
            'pgtap',
            NULL,
            TRUE,
            '_pgtap'
        )
    RETURNING id,
        codice
)
SELECT id AS lista_id,
    codice AS lista_codice
FROM ins;
-- Colonna 1: identificatore (ragione_sociale), tipo 'identificatore', non sensibile
CREATE TEMP TABLE _t_col1 AS WITH ins AS (
    INSERT INTO ui.lista_colonna (
            lista_id,
            codice,
            etichetta,
            campo_sorgente,
            tipo_colonna,
            tipo_dato,
            ordine_default,
            attivo,
            user_insert
        )
    SELECT lista_id,
        'ragione_sociale',
        'Ragione Sociale',
        'ragione_sociale',
        'identificatore',
        'string',
        10,
        TRUE,
        '_pgtap'
    FROM _t_lista
    RETURNING id
)
SELECT id AS col_id
FROM ins;
-- Colonna 2: informazione, non sensibile
CREATE TEMP TABLE _t_col2 AS WITH ins AS (
    INSERT INTO ui.lista_colonna (
            lista_id,
            codice,
            etichetta,
            campo_sorgente,
            tipo_colonna,
            tipo_dato,
            ordine_default,
            attivo,
            user_insert
        )
    SELECT lista_id,
        'citta',
        'Citta',
        'citta',
        'informazione',
        'string',
        20,
        TRUE,
        '_pgtap'
    FROM _t_lista
    RETURNING id
)
SELECT id AS col_id
FROM ins;
-- Colonna 3: sensibile (esposizione_finanziaria)
CREATE TEMP TABLE _t_col3 AS WITH ins AS (
    INSERT INTO ui.lista_colonna (
            lista_id,
            codice,
            etichetta,
            campo_sorgente,
            tipo_colonna,
            tipo_dato,
            ordine_default,
            sensibile,
            attivo,
            user_insert
        )
    SELECT lista_id,
        'esposizione_fin',
        'Esposizione Fin.',
        'esposizione_fin',
        'informazione',
        'numeric',
        30,
        TRUE,
        TRUE,
        '_pgtap'
    FROM _t_lista
    RETURNING id
)
SELECT id AS col_id
FROM ins;
-- L'utente di test: un operatore umano costruito, con la sua veste OPERATORE.
CREATE TEMP TABLE _t_op AS
SELECT o.auth_user_id, o.identita_id
  FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP lista config') o;

CREATE TEMP TABLE _t_au AS
SELECT auth_user_id FROM _t_op;

CREATE TEMP TABLE _t_id AS
SELECT identita_id FROM _t_op;

-- Da qui in poi si agisce come l'identita' appena creata: e' la veste che il
-- test collauda davvero, e senza la quale i profili PORTALE/AD_HOC verrebbero
-- filtrati (asserzioni 5, 7 e 11).
SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);
SELECT set_config('app.current_identita_id', (SELECT identita_id::text FROM _t_id), true);
-- Profilo AD_HOC per i test di permessi
CREATE TEMP TABLE _t_profilo AS WITH ins AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    VALUES (
            'AD_HOC',
            '_PGTAP_RESOLVE_' || upper(substr(md5(clock_timestamp()::text), 1, 8)),
            'Profilo AD_HOC test fn_resolve_lista_config',
            TRUE
        )
    RETURNING id
)
SELECT id AS profilo_id
FROM ins;
-- Binding del profilo AD_HOC all'identita di test
DO $lega$
BEGIN
    PERFORM config.fn_applica_lega_profilo_identita((
        SELECT profilo_id
        FROM _t_profilo
    ), (
        SELECT identita_id
        FROM _t_id
    ));
END
$lega$;
SELECT ok(
        (
            SELECT count(*)
            FROM _t_lista
        ) = 1
        AND (
            SELECT count(*)
            FROM _t_au
        ) = 1
        AND (
            SELECT count(*)
            FROM _t_id
        ) = 1,
        '1. Setup: lista + colonne + utente + identita creati'
    );
-- =========================================================
-- 2. Lista inesistente -> eccezione
-- =========================================================
-- fn_log_and_raise_error solleva P0001 (RAISE EXCEPTION generica).
-- Il codice applicativo E_UI_LISTA_NON_TROVATA è nel messaggio,
-- non nel SQLSTATE: usare 'P0001' come atteso, NULL per il messaggio.
SELECT throws_ok(
        $$SELECT ui.fn_resolve_lista_config('_pgtap.lista_inesistente_xyz', 0, NULL) $$,
        'P0001',
        NULL,
        '2. Lista inesistente -> eccezione (P0001: lista non trovata o non attiva)'
    );
-- =========================================================
-- 3. Nessun preset, nessuna preferenza -> catalogo grezzo
-- =========================================================
-- La funzione deve restituire tutte le colonne attive ordinate per ordine_default
-- L'utente ha gia' il profilo AD_HOC bindato (setup test 1).
-- esposizione_fin e' sensibile=TRUE: allow-list, nessun grant -> BLOCCATA.
-- Risultato atteso: 2 colonne (ragione_sociale + citta).
SELECT ok(
        (
            SELECT jsonb_array_length(
                    ui.fn_resolve_lista_config(
                        (
                            SELECT lista_codice
                            FROM _t_lista
                        ),
                        (
                            SELECT auth_user_id
                            FROM _t_au
                        ),
                        NULL
                    )->'colonne'
                )
        ) = 2,
        '3. Catalogo grezzo: 2 colonne (identificatore + informazione; sensibile BLOCCATA senza grant)'
    );
-- Verifica che il risultato abbia esattamente 2 colonne (3° e' sensibile, default BLOCCATO)
SELECT is(
        (
            SELECT jsonb_array_length(
                    ui.fn_resolve_lista_config(
                        (
                            SELECT lista_codice
                            FROM _t_lista
                        ),
                        (
                            SELECT auth_user_id
                            FROM _t_au
                        ),
                        NULL
                    )->'colonne'
                )
        ),
        2,
        '3b. Colonna sensibile senza grant -> BLOCCATA di default (allow-list): 2 colonne nel risultato'
    );
-- =========================================================
-- 4. Preset di sistema -> applicato correttamente
-- =========================================================
-- Crea preset di sistema con solo la colonna 'ragione_sociale' visibile
CREATE TEMP TABLE _t_preset_sys AS WITH ins AS (
    INSERT INTO ui.lista_preset (
            lista_id,
            codice,
            descrizione,
            ambito,
            pagina_dimensione,
            attivo,
            user_insert
        )
    SELECT lista_id,
        'default_sistema',
        'Preset di sistema test',
        'sistema',
        10,
        TRUE,
        '_pgtap'
    FROM _t_lista
    RETURNING id
)
SELECT id AS preset_id
FROM ins;
INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile)
SELECT p.preset_id,
    c.col_id,
    1,
    TRUE
FROM _t_preset_sys p,
    _t_col1 c;
INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile)
SELECT p.preset_id,
    c.col_id,
    2,
    FALSE -- citta: nel pool ma non visibile di default
FROM _t_preset_sys p,
    _t_col2 c;
SELECT is(
        (
            SELECT (
                    ui.fn_resolve_lista_config(
                        (
                            SELECT lista_codice
                            FROM _t_lista
                        ),
                        (
                            SELECT auth_user_id
                            FROM _t_au
                        ),
                        NULL
                    )->>'pagina_dimensione'
                )::INTEGER
        ),
        10,
        '4. Preset sistema applicato: pagina_dimensione = 10 dal preset'
    );
-- =========================================================
-- 5. Preset di profilo -> prevale su preset sistema
-- =========================================================
CREATE TEMP TABLE _t_preset_prof AS WITH ins AS (
    INSERT INTO ui.lista_preset (
            lista_id,
            codice,
            descrizione,
            ambito,
            profilo_accesso_id,
            pagina_dimensione,
            attivo,
            user_insert
        )
    SELECT lista_id,
        'preset_profilo',
        'Preset profilo AD_HOC test',
        'ruolo',
        (
            SELECT profilo_id
            FROM _t_profilo
        ),
        50,
        TRUE,
        '_pgtap'
    FROM _t_lista
    RETURNING id
)
SELECT id AS preset_id
FROM ins;
INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile)
SELECT p.preset_id,
    c.col_id,
    1,
    TRUE
FROM _t_preset_prof p,
    _t_col1 c;
SELECT is(
        (
            SELECT (
                    ui.fn_resolve_lista_config(
                        (
                            SELECT lista_codice
                            FROM _t_lista
                        ),
                        (
                            SELECT auth_user_id
                            FROM _t_au
                        ),
                        NULL
                    )->>'pagina_dimensione'
                )::INTEGER
        ),
        50,
        '5. Preset profilo (pagina_dim=50) prevale su preset sistema (pagina_dim=10)'
    );
-- =========================================================
-- 6. Preferenza utente -> prevale su tutto
-- =========================================================
INSERT INTO ui.lista_preferenza_utente (
        auth_user_id,
        lista_id,
        preset_base_id,
        configurazione,
        data_insert
    )
SELECT (
        SELECT auth_user_id
        FROM _t_au
    ),
    (
        SELECT lista_id
        FROM _t_lista
    ),
    (
        SELECT preset_id
        FROM _t_preset_sys
    ),
    jsonb_build_object(
        'colonne',
        jsonb_build_array(
            jsonb_build_object(
                'codice',
                'ragione_sociale',
                'ordine',
                1,
                'larghezza',
                300,
                'visibile',
                true,
                'fissata',
                true
            )
        ),
        -- Dal giro 2 di brief-db-revisione-ui la preferenza non porta ordinamento e
        -- filtri: il guard di forma le rifiuta.
        'pagina_dimensione',
        100  -- una misura del catalogo ui.misure_pagina (dal 2026-09-30: 99 lo rifiuta il guard)
    ),
    now();
SELECT is(
        (
            SELECT (
                    ui.fn_resolve_lista_config(
                        (
                            SELECT lista_codice
                            FROM _t_lista
                        ),
                        (
                            SELECT auth_user_id
                            FROM _t_au
                        ),
                        NULL
                    )->>'pagina_dimensione'
                )::INTEGER
        ),
        100,
        '6. Preferenza utente (pagina_dim=100) prevale su preset profilo (50) e sistema (10)'
    );
-- =========================================================
-- 7. Colonna sensibile con grant LETTURA -> presente, esportabile=false
-- =========================================================
-- Concediamo LETTURA sulla colonna sensibile per il profilo AD_HOC
INSERT INTO ui.lista_colonna_permesso (
        colonna_id,
        profilo_accesso_id,
        livello_accesso,
        user_insert
    )
SELECT (
        SELECT col_id
        FROM _t_col3
    ),
    (
        SELECT profilo_id
        FROM _t_profilo
    ),
    'LETTURA',
    '_pgtap';
-- Cancella la preferenza utente per tornare alla cascata preset
DELETE FROM ui.lista_preferenza_utente
WHERE auth_user_id = (
        SELECT auth_user_id
        FROM _t_au
    );
SELECT ok(
        EXISTS (
            SELECT 1
            FROM jsonb_array_elements(
                    ui.fn_resolve_lista_config(
                        (
                            SELECT lista_codice
                            FROM _t_lista
                        ),
                        (
                            SELECT auth_user_id
                            FROM _t_au
                        ),
                        NULL
                    )->'colonne'
                ) elem
            WHERE elem->>'codice' = 'esposizione_fin'
                AND (elem->>'esportabile')::BOOLEAN = FALSE
        ),
        '7. Colonna sensibile con grant LETTURA: presente nel risultato con esportabile=false'
    );
-- =========================================================
-- 8. Colonna 'identificatore' in preferenza con visibile:false -> normalizzata a true
-- =========================================================
-- La preferenza include TUTTE le colonne esistenti al momento (3: ragione_sociale,
-- citta, esposizione_fin) cosi' che nel test 9, dopo l'aggiunta di partita_iva,
-- colonne_nuove sia esattamente 1 (solo la nuova, non le 3 gia' salvate).
INSERT INTO ui.lista_preferenza_utente (
        auth_user_id,
        lista_id,
        configurazione,
        data_insert
    )
SELECT (
        SELECT auth_user_id
        FROM _t_au
    ),
    (
        SELECT lista_id
        FROM _t_lista
    ),
    jsonb_build_object(
        'colonne',
        jsonb_build_array(
            jsonb_build_object(
                'codice',
                'ragione_sociale',
                'ordine',
                1,
                'larghezza',
                200,
                'visibile',
                false, -- visibile:false su identificatore -> normalizzata a true (oggetto del test)
                'fissata',
                false
            ),
            jsonb_build_object(
                'codice',
                'citta',
                'ordine',
                2,
                'larghezza',
                160,
                'visibile',
                true,
                'fissata',
                false
            ),
            jsonb_build_object(
                'codice',
                'esposizione_fin',
                'ordine',
                3,
                'larghezza',
                180,
                'visibile',
                true,
                'fissata',
                false
            )
        ),
        -- Dal giro 2 di brief-db-revisione-ui la preferenza non porta ordinamento e
        -- filtri: il guard di forma le rifiuta.
        'pagina_dimensione',
        25
    ),
    now();
SELECT ok(
        EXISTS (
            SELECT 1
            FROM jsonb_array_elements(
                    ui.fn_resolve_lista_config(
                        (
                            SELECT lista_codice
                            FROM _t_lista
                        ),
                        (
                            SELECT auth_user_id
                            FROM _t_au
                        ),
                        NULL
                    )->'colonne'
                ) elem
            WHERE elem->>'codice' = 'ragione_sociale'
                AND (elem->>'visibile')::BOOLEAN = TRUE -- normalizzata da false a true
        ),
        '8. Colonna identificatore con visibile:false in preferenza -> normalizzata a true'
    );
-- =========================================================
-- 9. Nuova colonna nel catalogo non in preferenza -> colonne_nuove=1
-- =========================================================
-- Aggiungiamo una quarta colonna al catalogo DOPO che la preferenza e' stata salvata
WITH ins AS (
    INSERT INTO ui.lista_colonna (
            lista_id,
            codice,
            etichetta,
            campo_sorgente,
            tipo_colonna,
            tipo_dato,
            ordine_default,
            attivo,
            user_insert
        )
    SELECT lista_id,
        'partita_iva',
        'P.IVA',
        'partita_iva',
        'informazione',
        'string',
        40,
        TRUE,
        '_pgtap'
    FROM _t_lista
    RETURNING id
)
SELECT id
FROM ins;
SELECT is(
        (
            SELECT (
                    ui.fn_resolve_lista_config(
                        (
                            SELECT lista_codice
                            FROM _t_lista
                        ),
                        (
                            SELECT auth_user_id
                            FROM _t_au
                        ),
                        NULL
                    )->>'colonne_nuove'
                )::INTEGER
        ),
        1,
        '9. Nuova colonna nel catalogo non in preferenza -> colonne_nuove = 1'
    );
-- =========================================================
-- 11. Cascata dei preset di ruolo: vince il profilo piu' prioritario
--     Il secondo profilo e' il PORTALE del tipo OPERATORE (priorita'
--     3). uq_profili_accesso_bindings_ruolo ammette UN binding per veste: se il
--     seed lo porta gia' si usa quello, altrimenti si costruisce qui. Il caso
--     dice anche di averlo trovato: senza, il preset di ruolo non nascerebbe e
--     il caso passerebbe senza provare niente.
-- =========================================================
WITH p AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    SELECT 'PORTALE', '_PGTAP_RESOLVE_P_' || upper(substr(md5(clock_timestamp()::text), 1, 8)),
           'Profilo PORTALE test fn_resolve_lista_config', TRUE
     WHERE NOT EXISTS (SELECT 1 FROM config.profili_accesso_bindings b
                        WHERE b.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo)
    RETURNING id
)
INSERT INTO config.profili_accesso_bindings (profilo_accesso_id, ruolo_applicativo, attivo)
SELECT p.id, 'OPERATORE'::config.ruolo_applicativo, TRUE FROM p;
-- Cancella preferenza utente per tornare alla cascata preset
DELETE FROM ui.lista_preferenza_utente
WHERE auth_user_id = (
        SELECT auth_user_id
        FROM _t_au
    );

-- Recupera il primo profilo prio>1 gia' applicabile all'utente
-- (il PORTALE del tipo OPERATORE qui sopra, o il REPARTO dell'operatore)
CREATE TEMP TABLE _t_profilo_prio2 AS
SELECT profilo_accesso_id
FROM script.fn_get_profili_accesso_applicabili(
    (
        SELECT auth_user_id
        FROM _t_au
    )
)
WHERE priorita > 1
LIMIT 1;

-- Il preset del profilo prio>1, con pagina=25: una misura del catalogo DIVERSA da 50.
INSERT INTO ui.lista_preset (
        lista_id,
        codice,
        descrizione,
        ambito,
        profilo_accesso_id,
        pagina_dimensione,
        attivo,
        user_insert
    )
SELECT l.lista_id,
    'preset_prio2_pgtap',
    'Preset prio>1 test priorita DB-3',
    'ruolo',
    p.profilo_accesso_id,
    25,
    TRUE,
    '_pgtap'
FROM _t_lista l
JOIN _t_profilo_prio2 p ON TRUE;

INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile)
SELECT lp.id,
    c.col_id,
    1,
    TRUE
FROM ui.lista_preset lp,
    _t_col1 c
WHERE lp.codice   = 'preset_prio2_pgtap'
    AND lp.lista_id = (
        SELECT lista_id
        FROM _t_lista
    );

SELECT is(
        (SELECT format('%s|%s',
                       (SELECT count(*) FROM ui.lista_preset lp
                         WHERE lp.codice = 'preset_prio2_pgtap'
                           AND lp.lista_id = (SELECT lista_id FROM _t_lista)),
                       ui.fn_resolve_lista_config((SELECT lista_codice FROM _t_lista),
                                                  (SELECT auth_user_id FROM _t_au),
                                                  NULL)->>'pagina_dimensione')),
        '1|50',
        '11. Il preset del profilo prio>1 c''e'', e AD_HOC (prio=1, pagina=50) prevale (pagina=25)'
    );
-- =========================================================
-- 12. DB-4: GUC app.ruolo_applicativo filtra la veste corrente
--     Con GUC='FORNITORE_PORTALE' l'utente non ha identita FORNITORE_PORTALE
--     -> nessun profilo per questa veste -> fallback preset sistema (pagina=10)
-- =========================================================
-- set_config con is_local=true e' equivalente a SET LOCAL (scope transazione)
SELECT set_config('app.ruolo_applicativo', 'FORNITORE_PORTALE', true);

SELECT is(
        (
            SELECT (
                    ui.fn_resolve_lista_config(
                        (
                            SELECT lista_codice
                            FROM _t_lista
                        ),
                        (
                            SELECT auth_user_id
                            FROM _t_au
                        ),
                        NULL
                    )->>'pagina_dimensione'
                )::INTEGER
        ),
        10,
        '12. DB-4: GUC=FORNITORE_PORTALE (nessuna identita per questa veste) -> fallback preset sistema (pagina=10)'
    );

-- Reset GUC: stringa vuota = NULLIF -> NULL = comportamento legacy
SELECT set_config('app.ruolo_applicativo', '', true);

-- =========================================================
-- 13. DB-A: ogni colonna nell'output espone la chiave 'priorita'
--     (parte del contratto API; letta fresca da ui.lista_colonna).
-- =========================================================
SELECT ok(
        NOT EXISTS (
            SELECT 1
            FROM jsonb_array_elements(
                    (
                        ui.fn_resolve_lista_config(
                            (SELECT lista_codice FROM _t_lista),
                            (SELECT auth_user_id FROM _t_au),
                            NULL
                        )
                    )->'colonne'
                ) AS elem
            WHERE NOT (elem ? 'priorita')
        ),
        '13. DB-A: ogni colonna dell''output espone la chiave priorita'
    );

SELECT *
FROM finish();
ROLLBACK;