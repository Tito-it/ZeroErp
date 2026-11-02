-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture semina su ui.dashboard_definizione, che a runtime NON scrive nessuno:
--   ne' una funzione DB ne' il backend. E' seed di migrazione, e il SELECT-only del
--   ruolo applicativo e' corretto. Verificato cercando gli scrittori, non dedotto
--   (brief §29.2).
-- pgTAP test per Zero ERP
--
-- Test: ui.fn_resolve_dashboard_config
-- Funzione: ui.fn_resolve_dashboard_config(codice, auth_user_id, emittente_fiscale_id)
--
-- Semantica attesa (brief-db-dashboard-home §4):
--   - Dashboard inesistente -> errore E_UI_DASHBOARD_NON_TROVATA (P0001)
--   - Nessuna preferenza/preset -> catalogo grezzo (mai vuota), gated esclusi
--   - Widget gated (area) senza permesso -> non compare (§4.5)
--   - Preset sistema -> applicato; preset ruolo prevale su sistema
--   - Preferenza utente -> prevale su tutto (§4.2)
--   - Widget nuovo nel pool dopo il salvataggio -> visibile:false, widget_nuovi++ (§4.4)
--   - Widget disattivato -> sparisce anche da chi l'aveva in preferenza (§4.6)
--   - Due profili applicabili -> prevale la priorita' piu' bassa (§4.3)
--   - Campi opachi (deep_link/contatore_key/soglia) restituiti freschi da ui.widget
--
-- Pattern: CLIENTE_PORTALE (come test-fn-resolve-lista-config.sql) per evitare
-- la guard PF pura. Per questa veste (non-OPERATORE) le mappe permessi
-- producono BLOCCATO: i widget gated risultano sempre nascosti -> copre il
-- caso negativo §4.5. Il caso positivo di gating (widget visibile con permesso)
-- richiederebbe una identita OPERATORE con grant d'area ed e' fuori da questo
-- test (i widget non-gated coprono comunque la garanzia "mai vuota").
-- BEGIN; + ROLLBACK implicito a fine file.
--
-- Indice test (1..12):
--   1.  Setup (dashboard + widget + pool + utente + identita + profilo AD_HOC)
--   2.  Dashboard inesistente -> eccezione P0001
--   3.  Catalogo grezzo: 2 widget (non-gated); gated escluso ("mai vuota")
--   4.  §4.5: widget gated (area) assente dal risultato
--   5.  Preset sistema -> dimensione_max=6
--   6.  Preset ruolo AD_HOC -> dimensione_max=5 (prevale su sistema)
--   7.  §4.2: preferenza utente -> dimensione_max=9 (prevale su tutto)
--   8.  §4.4: nuovo widget nel pool dopo salvataggio -> widget_nuovi=1
--   9.  §4.6: widget disattivato -> assente anche con preferenza
--   10. §4.3: due profili -> AD_HOC (prio=1) prevale su prio>1 (dim=5 vs 77)
--   11. Arricchimento: widget espone contatore_key fresco da ui.widget
--   12. §3f: deep_link opaco restituito fedele
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
-- degli altri, e non e' una dimenticanza — ma la ragione qui e' scomoda e vale
-- la pena scriverla per esteso.
-- La fixture costruisce un'identita' CLIENTE_PORTALE (riga ~136) e su quella
-- verifica le precedenze fra preset. La funzione filtra i profili per la veste
-- corrente (`app.ruolo_applicativo` -> fn_get_profili_accesso_applicabili):
-- dichiarare OPERATORE in testa esclude — CORRETTAMENTE — il profilo di
-- un'identita' portale, e le asserzioni 6 e 10 cadono. La funzione fa il suo
-- mestiere; e' l'accoppiata «identita' portale + veste operatore» a non esistere.
-- ⚠️ Ma senza GUC la veste e' NULL = «tutte», e questa e' una condizione che
-- l'applicazione non produce MAI: il middleware la valorizza sempre. Quindi
-- oggi queste asserzioni sono verdi in un mondo che non esiste. La correzione
-- vera e' far dichiarare al test la veste coerente con la propria fixture
-- (CLIENTE_PORTALE), non imporgliene una operatore: e' una decisione del
-- cantiere `ui`, non di questo brief.
-- Brief: brief-db-pgtap-runner-rls-baseline §11.

SELECT plan(12);

-- =========================================================
-- 1. Setup
-- =========================================================
-- Dashboard di test
CREATE TEMP TABLE _t_dash AS WITH ins AS (
    INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
    VALUES (
        '_pgtap.dash_' || substr(md5(clock_timestamp()::text), 1, 6),
        'Dashboard test pgTAP fn_resolve_dashboard_config',
        TRUE,
        '_pgtap'
    )
    RETURNING id, codice
)
SELECT id AS dashboard_id, codice AS dashboard_codice FROM ins;

-- Un'area funzionale reale per il widget gated (l'utente CLIENTE_PORTALE
-- e' BLOCCATO su tutte -> gating negativo).
CREATE TEMP TABLE _t_area AS
SELECT id AS area_id FROM config.aree_funzionali WHERE attivo = TRUE ORDER BY id LIMIT 1;

-- W1: non-gated (card di benvenuto), nessun campo opaco
CREATE TEMP TABLE _t_w1 AS WITH ins AS (
    INSERT INTO ui.widget (codice, etichetta, tipo_widget, attivo, user_insert)
    VALUES ('w_benvenuto', 'Benvenuto', 'kpi', TRUE, '_pgtap')
    RETURNING id
)
SELECT id AS widget_id FROM ins;

-- W2: non-gated, con deep_link/contatore_key/soglia (arricchimento)
CREATE TEMP TABLE _t_w2 AS WITH ins AS (
    INSERT INTO ui.widget (
        codice, etichetta, etichetta_i18n_key, tipo_widget,
        deep_link, contatore_key, soglia, attivo, user_insert
    )
    VALUES (
        'w_resi', 'Resi da accreditare', 'dashboard.widget.resi_da_accreditare', 'kpi',
        '{"route":"vendite.resi","params":{"stato":"da_accreditare"}}'::jsonb,
        'resi_da_accreditare',
        '{"warn":5,"alert":10}'::jsonb,
        TRUE, '_pgtap'
    )
    RETURNING id
)
SELECT id AS widget_id FROM ins;

-- W3: gated su area reale (senza permesso per la veste di test)
CREATE TEMP TABLE _t_w3 AS WITH ins AS (
    INSERT INTO ui.widget (codice, etichetta, tipo_widget, area_id, attivo, user_insert)
    SELECT 'w_gated', 'Gated', 'kpi', a.area_id, TRUE, '_pgtap'
    FROM _t_area a
    RETURNING id
)
SELECT id AS widget_id FROM ins;

-- Composizione: i 3 widget nel pool della dashboard
INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT d.dashboard_id, w.widget_id, 10 FROM _t_dash d, _t_w1 w;
INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT d.dashboard_id, w.widget_id, 20 FROM _t_dash d, _t_w2 w;
INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT d.dashboard_id, w.widget_id, 30 FROM _t_dash d, _t_w3 w;

-- auth_user di test
CREATE TEMP TABLE _t_au AS WITH ins AS (
    INSERT INTO django.auth_user (
        username, password, is_active, is_staff, is_superuser,
        first_name, last_name, email, date_joined
    )
    VALUES (
        '_pgtap_dash_' || substr(md5(clock_timestamp()::text), 1, 6),
        '!', TRUE, FALSE, FALSE, '', '', '', now()
    )
    RETURNING id
)
SELECT id AS auth_user_id FROM ins;

-- ⛔ Il cliente si COSTRUISCE (2026-09-23). Fino a oggi questa fixture pescava
--   un `billing_account` esistente: su un database ricostruito non ce n'e'
--   nessuno, la temp table restava VUOTA, l'INSERT dell'identita' inseriva
--   zero righe e il binding finiva con `identita_digitale_id` NULL — da cui
--   l'errore «binding non coerente col tipo del profilo», che nominava il
--   profilo e non la causa. Il BB costruisce azienda, operatore e cliente
--   nell'ordine giusto e riusa l'azienda del contesto gia' aperto.
CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('dashboard config');

CREATE TEMP TABLE _t_sr AS
SELECT cliente_soggetto_ruolo_id AS sr_id FROM _t_mondo;

-- ⛔ E SUBITO DOPO SI RIMETTE LA SESSIONE COM'ERA, che in questo file e' SENZA
--   veste (vedi la nota lunga in testa). Costruire il cliente RICHIEDE un
--   contesto — sotto la RLS un billing account non si scrive da una sessione
--   senza veste — ma tenerlo aperto cambierebbe cio' che il file misura: con
--   `app.ruolo_applicativo = OPERATORE` la funzione escluderebbe, CORRETTA-
--   MENTE, il profilo di un'identita' portale, e le asserzioni 6 e 10
--   cadrebbero. Quale veste debba dichiarare questo file resta la decisione
--   del cantiere `ui` che la nota in testa descrive: qui si costruisce il
--   mondo senza toccare la domanda.
SELECT set_config('app.ruolo_applicativo', '', false);
SELECT set_config('app.current_user_id',   '', false);

-- Identita CLIENTE_PORTALE
CREATE TEMP TABLE _t_id AS WITH ins AS (
    SELECT anagrafiche.fn_crea_veste_portale(a.auth_user_id, s.sr_id, 'CLIENTE_PORTALE', TRUE) AS id FROM _t_sr s, _t_au a)
SELECT id AS identita_id FROM ins;

-- Profilo AD_HOC (prio=1) + binding all'identita
CREATE TEMP TABLE _t_profilo AS WITH ins AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    VALUES (
        'AD_HOC',
        '_PGTAP_DASH_' || upper(substr(md5(clock_timestamp()::text), 1, 8)),
        'Profilo AD_HOC test fn_resolve_dashboard_config',
        TRUE
    )
    RETURNING id
)
SELECT id AS profilo_id FROM ins;

DO $lega$
BEGIN
    PERFORM config.fn_lega_profilo_identita((SELECT profilo_id FROM _t_profilo), (SELECT identita_id FROM _t_id));
END
$lega$;

SELECT ok(
    (SELECT count(*) FROM _t_dash) = 1
    AND (SELECT count(*) FROM _t_au) = 1
    AND (SELECT count(*) FROM _t_area) = 1,
    '1. Setup: dashboard + widget + pool + utente + identita + area creati'
);

-- =========================================================
-- 2. Dashboard inesistente -> eccezione
-- =========================================================
SELECT throws_ok(
    $$SELECT ui.fn_resolve_dashboard_config('_pgtap.dash_inesistente_xyz', 0, NULL) $$,
    'P0001',
    NULL,
    '2. Dashboard inesistente -> eccezione (P0001: dashboard non trovata o non attiva)'
);

-- =========================================================
-- 3. Catalogo grezzo (no preset/preferenza) -> 2 widget (gated escluso)
-- =========================================================
SELECT is(
    (SELECT jsonb_array_length(
        ui.fn_resolve_dashboard_config(
            (SELECT dashboard_codice FROM _t_dash),
            (SELECT auth_user_id FROM _t_au),
            NULL
        )->'widget'
    )),
    2,
    '3. Catalogo grezzo: 2 widget non-gated (mai vuota); gated escluso'
);

-- =========================================================
-- 4. §4.5: widget gated (area) assente dal risultato
-- =========================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(
            ui.fn_resolve_dashboard_config(
                (SELECT dashboard_codice FROM _t_dash),
                (SELECT auth_user_id FROM _t_au),
                NULL
            )->'widget'
        ) elem
        WHERE elem->>'codice' = 'w_gated'
    ),
    '4. §4.5: widget gated su area senza permesso -> non compare'
);

-- =========================================================
-- 5. Preset sistema -> dimensione_max=6
-- =========================================================
CREATE TEMP TABLE _t_preset_sys AS WITH ins AS (
    INSERT INTO ui.dashboard_preset (
        dashboard_id, codice, descrizione, ambito, is_default, dimensione_max, attivo, user_insert
    )
    SELECT dashboard_id, 'default_sistema', 'Preset sistema test', 'sistema', TRUE, 6, TRUE, '_pgtap'
    FROM _t_dash
    RETURNING id
)
SELECT id AS preset_id FROM ins;

INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT p.preset_id, w.widget_id, 1, TRUE FROM _t_preset_sys p, _t_w1 w;

SELECT is(
    (SELECT (ui.fn_resolve_dashboard_config(
        (SELECT dashboard_codice FROM _t_dash),
        (SELECT auth_user_id FROM _t_au),
        NULL
    )->>'dimensione_max')::INTEGER),
    6,
    '5. Preset sistema applicato: dimensione_max = 6'
);

-- =========================================================
-- 6. Preset ruolo AD_HOC -> dimensione_max=5 (prevale su sistema)
-- =========================================================
CREATE TEMP TABLE _t_preset_prof AS WITH ins AS (
    INSERT INTO ui.dashboard_preset (
        dashboard_id, codice, descrizione, ambito, profilo_accesso_id,
        is_default, dimensione_max, attivo, user_insert
    )
    SELECT dashboard_id, 'preset_profilo', 'Preset AD_HOC test', 'ruolo',
        (SELECT profilo_id FROM _t_profilo), TRUE, 5, TRUE, '_pgtap'
    FROM _t_dash
    RETURNING id
)
SELECT id AS preset_id FROM ins;

INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT p.preset_id, w.widget_id, 1, TRUE FROM _t_preset_prof p, _t_w1 w;

SELECT is(
    (SELECT (ui.fn_resolve_dashboard_config(
        (SELECT dashboard_codice FROM _t_dash),
        (SELECT auth_user_id FROM _t_au),
        NULL
    )->>'dimensione_max')::INTEGER),
    5,
    '6. Preset ruolo AD_HOC (dim=5) prevale su preset sistema (dim=6)'
);

-- =========================================================
-- 7. §4.2: preferenza utente -> dimensione_max=9 (prevale su tutto)
--    La preferenza include i 3 widget esistenti al momento del salvataggio
--    (w_benvenuto, w_resi, w_gated) cosi' che nel test 8 solo w_nuovo sia nuovo.
-- =========================================================
INSERT INTO ui.dashboard_preferenza_utente (auth_user_id, dashboard_id, configurazione, data_insert)
SELECT
    (SELECT auth_user_id FROM _t_au),
    (SELECT dashboard_id FROM _t_dash),
    jsonb_build_object(
        'widget', jsonb_build_array(
            jsonb_build_object('codice','w_benvenuto','ordine',1,'visibile',true),
            jsonb_build_object('codice','w_resi','ordine',2,'visibile',true),
            jsonb_build_object('codice','w_gated','ordine',3,'visibile',true)
        ),
        'dimensione_max', 9
    ),
    now();

SELECT is(
    (SELECT (ui.fn_resolve_dashboard_config(
        (SELECT dashboard_codice FROM _t_dash),
        (SELECT auth_user_id FROM _t_au),
        NULL
    )->>'dimensione_max')::INTEGER),
    9,
    '7. §4.2: preferenza utente (dim=9) prevale su preset ruolo (5) e sistema (6)'
);

-- =========================================================
-- 8. §4.4: nuovo widget nel pool dopo il salvataggio -> widget_nuovi=1
-- =========================================================
CREATE TEMP TABLE _t_w4 AS WITH ins AS (
    INSERT INTO ui.widget (codice, etichetta, tipo_widget, attivo, user_insert)
    VALUES ('w_nuovo', 'Nuovo', 'kpi', TRUE, '_pgtap')
    RETURNING id
)
SELECT id AS widget_id FROM ins;

INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default)
SELECT d.dashboard_id, w.widget_id, 40 FROM _t_dash d, _t_w4 w;

SELECT is(
    (SELECT (ui.fn_resolve_dashboard_config(
        (SELECT dashboard_codice FROM _t_dash),
        (SELECT auth_user_id FROM _t_au),
        NULL
    )->>'widget_nuovi')::INTEGER),
    1,
    '8. §4.4: nuovo widget nel pool non in preferenza -> widget_nuovi = 1'
);

-- =========================================================
-- 9. §4.6: widget disattivato -> assente anche con preferenza
-- =========================================================
UPDATE ui.widget SET attivo = FALSE WHERE id = (SELECT widget_id FROM _t_w1);

SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM jsonb_array_elements(
            ui.fn_resolve_dashboard_config(
                (SELECT dashboard_codice FROM _t_dash),
                (SELECT auth_user_id FROM _t_au),
                NULL
            )->'widget'
        ) elem
        WHERE elem->>'codice' = 'w_benvenuto'
    ),
    '9. §4.6: widget disattivato -> assente anche da chi lo aveva in preferenza'
);
-- ripristina W1 per i test successivi
UPDATE ui.widget SET attivo = TRUE WHERE id = (SELECT widget_id FROM _t_w1);

-- =========================================================
-- 10. §4.3: due profili -> AD_HOC (prio=1) prevale deterministicamente
--     Usa un profilo prio>1 gia' applicabile all'utente (binding reale, es.
--     PORTALE su CLIENTE_PORTALE): non ne creiamo uno nuovo. Se non esiste,
--     l'INSERT produce 0 righe e il test verifica comunque AD_HOC (dim=5).
-- =========================================================
DELETE FROM ui.dashboard_preferenza_utente
WHERE auth_user_id = (SELECT auth_user_id FROM _t_au);

CREATE TEMP TABLE _t_profilo_prio2 AS
SELECT profilo_accesso_id
FROM script.fn_get_profili_accesso_applicabili((SELECT auth_user_id FROM _t_au))
WHERE priorita > 1
LIMIT 1;

INSERT INTO ui.dashboard_preset (
    dashboard_id, codice, descrizione, ambito, profilo_accesso_id,
    is_default, dimensione_max, attivo, user_insert
)
SELECT d.dashboard_id, 'preset_prio2_pgtap', 'Preset prio>1 test priorita', 'ruolo',
    p.profilo_accesso_id, TRUE, 77, TRUE, '_pgtap'
FROM _t_dash d
JOIN _t_profilo_prio2 p ON TRUE;

INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine, visibile)
SELECT lp.id, w.widget_id, 1, TRUE
FROM ui.dashboard_preset lp, _t_w1 w
WHERE lp.codice = 'preset_prio2_pgtap'
  AND lp.dashboard_id = (SELECT dashboard_id FROM _t_dash);

SELECT is(
    (SELECT (ui.fn_resolve_dashboard_config(
        (SELECT dashboard_codice FROM _t_dash),
        (SELECT auth_user_id FROM _t_au),
        NULL
    )->>'dimensione_max')::INTEGER),
    5,
    '10. §4.3: AD_HOC (prio=1, dim=5) prevale su profilo prio>1 (dim=77)'
);

-- =========================================================
-- 11. Arricchimento: widget espone contatore_key fresco da ui.widget
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM jsonb_array_elements(
            ui.fn_resolve_dashboard_config(
                (SELECT dashboard_codice FROM _t_dash),
                (SELECT auth_user_id FROM _t_au),
                NULL
            )->'widget'
        ) elem
        WHERE elem->>'codice' = 'w_resi'
          AND elem->>'contatore_key' = 'resi_da_accreditare'
          AND elem->>'tipo_widget' = 'kpi'
    ),
    '11. Widget espone contatore_key + tipo_widget freschi da ui.widget'
);

-- =========================================================
-- 12. §3f: deep_link opaco restituito fedele
-- =========================================================
SELECT is(
    (SELECT elem->'deep_link'
     FROM jsonb_array_elements(
        ui.fn_resolve_dashboard_config(
            (SELECT dashboard_codice FROM _t_dash),
            (SELECT auth_user_id FROM _t_au),
            NULL
        )->'widget'
     ) elem
     WHERE elem->>'codice' = 'w_resi'),
    '{"route":"vendite.resi","params":{"stato":"da_accreditare"}}'::jsonb,
    '12. §3f: deep_link JSONB opaco restituito fedele (nessuna interpretazione DB)'
);

SELECT * FROM finish();
ROLLBACK;
