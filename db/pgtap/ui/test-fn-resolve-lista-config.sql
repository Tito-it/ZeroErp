-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
-- Pattern: CLIENTE_PORTALE per evitare guard PF pura (stesso pattern
-- di test-fn-get-profili-accesso-applicabili.sql).
-- BEGIN; + ROLLBACK implicito a fine file.
--
-- Indice test (1..13):
--   1.  Setup dati di test (lista + colonne + utente + identita)
--   2.  Lista inesistente -> eccezione P0001
--   3.  Catalogo grezzo: 2 colonne (sensibile BLOCCATA senza grant)
--   4.  Catalogo grezzo 3b: conferma is(2)
--   5.  Preset di sistema -> pagina_dimensione=10
--   6.  Preset di profilo -> pagina_dimensione=50 (prevale su sistema)
--   7.  Preferenza utente -> pagina_dimensione=100 (prevale su tutto; 99 fino al 2026-09-30, fuori dal catalogo delle misure)
--   8.  Colonna sensibile con grant LETTURA -> esportabile=false
--   9.  Colonna identificatore con visibile:false -> normalizzata a true
--   10. Nuova colonna nel catalogo non in preferenza -> colonne_nuove=1
--   11. DB-3: cascata preset deterministica (AD_HOC prio=1 vs profilo prio>1 da DB reale)
--   12. DB-4: GUC-aware (veste OPERATORE -> nessun profilo -> fallback sistema)
--   13. DB-A: ogni colonna dell'output espone la chiave priorita
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

-- ⚠️ QUESTO FILE NON USA script.fn_pgtap_set_contesto_operatore(), a differenza
-- degli altri, e non e' una dimenticanza. Stessa ragione del gemello
-- test-fn-resolve-dashboard-config.sql, dove e' spiegata per esteso.
-- In breve: la fixture costruisce un'identita' CLIENTE_PORTALE (riga ~192, per
-- evitare il guard PF pura) e la funzione filtra i profili per la veste
-- corrente. Dichiarare OPERATORE in testa esclude — correttamente — quel
-- profilo, e cadono le asserzioni 5, 7 e 11.
-- Qui c'e' un indizio in piu': l'asserzione 12 manipola gia' `app.ruolo_applicativo`
-- da sola, per verificare proprio che la veste filtri. Il file conosce la GUC e
-- sceglie di tenerla vuota altrove — ma «veste vuota» e' una condizione che
-- l'applicazione non produce mai. Correzione vera: dichiarare CLIENTE_PORTALE,
-- decisione del cantiere `ui`.
-- Brief: brief-db-pgtap-runner-rls-baseline §11.

-- ⚠️ Due vesti, in ordine, e l'ordine e' il punto.
--   La fixture deve prima VEDERE (billing_account e' sotto RLS: senza una veste
--   dichiarata l'utente applicativo legge zero righe, _t_sr resta vuota e cade
--   tutto a valle). Poi, prima delle asserzioni, si indossa la veste che il test
--   collauda davvero — CLIENTE_PORTALE, quella dell'identita' che la fixture ha
--   appena creato.
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
-- auth_user di test (CLIENTE_PORTALE per evitare guard PF pura)
CREATE TEMP TABLE _t_au AS WITH ins AS (
    INSERT INTO django.auth_user (
            username,
            password,
            is_active,
            is_staff,
            is_superuser,
            first_name,
            last_name,
            email,
            date_joined
        )
    VALUES (
            '_pgtap_resolve_' || substr(md5(clock_timestamp()::text), 1, 6),
            '!',
            TRUE,
            FALSE,
            FALSE,
            '',
            '',
            '',
            now()
        )
    RETURNING id
)
SELECT id AS auth_user_id
FROM ins;
-- ⛔ Il cliente si COSTRUISCE (2026-09-23). Fino a oggi questa fixture pescava
--   un `billing_account` esistente: su un database ricostruito non ce n'e'
--   nessuno, la temp table restava VUOTA, l'INSERT dell'identita' inseriva
--   zero righe e il binding finiva con `identita_digitale_id` NULL — da cui
--   l'errore «binding non coerente col tipo del profilo», che nominava il
--   profilo e non la causa. Il BB costruisce azienda, operatore e cliente
--   nell'ordine giusto e riusa l'azienda del contesto gia' aperto.
CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('lista config');

CREATE TEMP TABLE _t_sr AS
SELECT cliente_soggetto_ruolo_id AS sr_id FROM _t_mondo;
-- Identita CLIENTE_PORTALE
CREATE TEMP TABLE _t_id AS WITH ins AS (
    SELECT anagrafiche.fn_crea_veste_portale(a.auth_user_id, s.sr_id, 'CLIENTE_PORTALE', TRUE) AS id FROM _t_sr s,
        _t_au a)
SELECT id AS identita_id
FROM ins;

-- Da qui in poi si agisce come l'identita' appena creata: e' la veste che il
-- test collauda davvero, e senza la quale i profili PORTALE/AD_HOC verrebbero
-- filtrati (asserzioni 5, 7 e 11).
SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
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
    PERFORM config.fn_lega_profilo_identita((
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
            is_default,
            pagina_dimensione,
            attivo,
            user_insert
        )
    SELECT lista_id,
        'default_sistema',
        'Preset di sistema test',
        'sistema',
        TRUE,
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
            is_default,
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
        TRUE,
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
        'ordinamento',
        '[]'::jsonb,
        'filtri',
        '{}'::jsonb,
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
        'ordinamento',
        '[]'::jsonb,
        'filtri',
        '{}'::jsonb,
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
-- 11. DB-3: cascata preset di ruolo deterministica
--     Usa il profilo prio>1 GIA' applicabile all'utente di test
--     (via binding globale esistente nel DB, es. PORTALE CLIENTE_PORTALE).
--     Non creiamo un nuovo binding: uq_profili_accesso_bindings_ruolo
--     ammette UN SOLO profilo per ruolo_applicativo.
-- =========================================================
-- Cancella preferenza utente per tornare alla cascata preset
DELETE FROM ui.lista_preferenza_utente
WHERE auth_user_id = (
        SELECT auth_user_id
        FROM _t_au
    );

-- Recupera il primo profilo prio>1 gia' applicabile all'utente
-- (es. PORTALE bound a CLIENTE_PORTALE nei dati reali del DB)
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

-- Crea preset per il profilo prio>1 con pagina=25 sulla lista di test
-- (77 fino al 2026-09-30: fuori dal catalogo ui.misure_pagina, oggi lo rifiuta il
-- guard; serve solo una misura DIVERSA da 50).
-- Se non esiste nessun profilo prio>1, il INSERT produce 0 righe
-- e il test verifica comunque che AD_HOC (prio=1) dia pagina=50.
INSERT INTO ui.lista_preset (
        lista_id,
        codice,
        descrizione,
        ambito,
        profilo_accesso_id,
        is_default,
        pagina_dimensione,
        attivo,
        user_insert
    )
SELECT l.lista_id,
    'preset_prio2_pgtap',
    'Preset prio>1 test priorita DB-3',
    'ruolo',
    p.profilo_accesso_id,
    TRUE,
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
        '11. DB-3: AD_HOC (prio=1, pagina=50) prevale su profilo prio>1 (pagina=25)'
    );
-- =========================================================
-- 12. DB-4: GUC app.ruolo_applicativo filtra la veste corrente
--     Con GUC='OPERATORE' l'utente non ha identita OPERATORE
--     -> nessun profilo per questa veste -> fallback preset sistema (pagina=10)
-- =========================================================
-- set_config con is_local=true e' equivalente a SET LOCAL (scope transazione)
SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);

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
        '12. DB-4: GUC=OPERATORE (nessuna identita per questa veste) -> fallback preset sistema (pagina=10)'
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