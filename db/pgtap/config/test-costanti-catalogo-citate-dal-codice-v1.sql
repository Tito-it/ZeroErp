-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le COSTANTI DI CATALOGO su cui il codice vivo si aggancia esistono, e
--       sono ancora citate da chi le usa.
--
-- Elenco test (plan 6):
--   1) gemello «esiste»: la lista non e' vuota e ogni tabella di catalogo che
--      nomina esiste davvero
--   2) ogni costante attesa esiste nel suo catalogo ed e' ATTIVA
--   3) config.sorgenti DDT_VENDITA ha key_selector = 'id'
--   4) anti-marciume: ogni coppia (oggetto vivo, costante) e' ancora vera
--   5) derivato, senza elenco: ogni sorgente passata come argomento ai trigger
--      di chiusura commessa (il freno sulle righe EMESSA) esiste a catalogo ed e' attiva
--   6) gemello «esiste» del test 5: quei trigger esistono
--
-- ── PERCHE' QUESTO FILE ESISTE ──────────────────────────────────────────
--
--   Il 2026-09-02 sono state rimosse SEDICI `preCondition` di Liquibase che
--   pretendevano una riga di seed dentro un changeSet di `00_schema`/`20_code`.
--   Erano mine: quelle fasi girano PRIMA di `80_data`, quindi su un database
--   ricostruito da zero — cioe' in CI — la riga non esiste ancora e il migrate
--   muore con «SQL Precondition failed. Expected '1' got '0'».
--   Regola e casistica: docs/it/linee-guida-sql.md §11.4, presidiata da
--   scripts/guardrail_precondition_seed.py.
--
--   ⭐ Ma il RISCHIO che quei cancelli descrivevano era vero, e ha solo
--   sbagliato POSTO: «se il `codice_interno` cambiasse, il `CASE` smetterebbe
--   di agganciarsi IN SILENZIO» — il bottone tornerebbe acceso, il trigger
--   diventerebbe un no-op, la vista perderebbe i suoi archi. Il posto giusto e'
--   qui: un pgTAP gira a `80_data` applicato, cioe' quando il catalogo c'e'.
--   Questo file e' la meta' che resta dopo la bonifica.
--
-- ── COSA NON STA QUI, E PERCHE' NON E' UNA DIMENTICANZA ─────────────────
--
--   * `config.tipi_entita` (codice `FATTURA`, changeSet 20260824-13 e
--     20260831-64): gia' presidiato da `dbops.vw_bersagli_non_dichiarati`, che
--     in CI fa fallire la build su un bersaglio non dichiarato. Rifarlo qui
--     sarebbe una seconda copia della stessa regola.
--   * `config.codici_errore` (E_BA_EMITTENTE_CON_STORIA, E_CONFIG_MANCANTE,
--     E_EMITTENTE_DEFAULT_SINGLETON, E_VENDITE_CHIAMATA_NON_VALIDA — changeSet
--     20260827-01/-03, 20260828-11/-13, 20260831-02): gia' presidiati dal
--     test 2 di `db/pgtap/script/test-catalogo-messaggi-errore-completo.sql`
--     («ogni codice sollevato da una funzione viva esiste a catalogo») e dai
--     controlli (B) e (D) di `scripts/sql/guardrail_codice_errore_strutturato.sql`.
--
-- ── ⚠️ IL LIMITE DI QUESTO PRESIDIO, DICHIARATO ─────────────────────────
--
--   I test 2/3/4 hanno per PERIMETRO l'elenco `_costanti` qui sotto: una
--   costante che nessuno ha aggiunto non e' guardata da nessuno. E' il difetto
--   noto dei presidi che cercano un nome nel TESTO di N oggetti — se domani
--   `fn_available_actions_reso` estrae il suo `CASE` in una funzione nuova,
--   il test 4 diventa rosso e chiede di aggiornare la riga: e' voluto, ed e'
--   il modo in cui l'elenco resta onesto invece di marcire in silenzio.
--   ⭐ Il test 5 non ha questo limite: deriva le sorgenti dagli ARGOMENTI dei
--   trigger (`pg_trigger.tgargs`), quindi copre anche i trigger montati domani.
--   Dove si puo' derivare si deriva; l'elenco resta dove la derivazione non
--   sarebbe completa.
--
-- Origine: bonifica preCondition/seed del 2026-09-02 · linee-guida-sql §11.4
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE. Senza, un fallimento a meta' lascia i dati di prova nel
--   database e rompe la corsa successiva, che vede un rosso non suo.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO. I test girano come `zeroerp_app` con la RLS
--   ATTIVA. I cataloghi letti qui (config.sorgenti, config.stati_doc_reso,
--   pagamenti.vendite_contabili_righe_stati) sono tabelle come le altre: senza
--   una veste dichiarata una policy fail-closed farebbe leggere ZERO righe, e
--   il test 2 conterebbe zero cattivi su zero candidati — verde per sottrazione.
--   E' esattamente contro quello che esiste il test 1.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI. Qui non si scrive niente, ma la riga resta: e' la
--   forma del preambolo presidiata da scripts/guardrail_pgtap_preambolo.py, e
--   dichiararla assente costerebbe una nota che il prossimo dovrebbe rileggere.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- L'elenco: cosa il codice vivo pretende dal catalogo
-- ============================================================
-- Ogni riga e' un contratto fra un SEED (80_data) e un OGGETTO di codice
-- (20_code/00_schema), ed e' la preCondition che il 2026-09-02 e' stata tolta
-- dal changeSet indicato in `changeset_origine`.
CREATE TEMP TABLE _costanti (
    cat_schema   text,
    cat_tabella  text,
    valore       text,
    obj_schema   text,
    obj_nome     text,
    obj_tipo     text,          -- 'FUNZIONE' | 'VISTA'
    changeset    text
) ON COMMIT DROP;

INSERT INTO _costanti VALUES
    -- Il CASE che disabilita col motivo la transizione ad ANNULLATO: se il
    -- codice cambiasse, il bottone «annulla reso» tornerebbe ACCESO in silenzio
    -- anche con un accredito registrato, e l'operatore prenderebbe un 409.
    ('config',    'stati_doc_reso',                'ANNULLATO',
     'script',    'fn_available_actions_reso',     'FUNZIONE', '20260820-12'),

    -- Lo stato su cui il trigger marca il fondo eseguito: senza la riga a
    -- catalogo il confronto e' sempre falso e il trigger un no-op MUTO.
    ('pagamenti', 'vendite_contabili_righe_stati', 'POSTATA',
     'pagamenti', 'trgfn_vendite_contabili_righe_marca_fondo_eseguito', 'FUNZIONE', '20260821-51'),

    -- Lo stato in cui la distinta di correzione rimette le righe.
    ('pagamenti', 'vendite_contabili_righe_stati', 'DA_ABBINARE',
     'pagamenti', 'fn_crea_distinta_correzione',  'FUNZIONE', '20260828-20'),

    -- La voce di catalogo su cui la lista fatture aggancia il lineage: senza,
    -- il JOIN non fallisce — resta muto, che e' peggio.
    ('config',    'sorgenti',                      'FATTURA',
     'vendite',   'vw_fatture_lista',              'VISTA',    '20260824-15'),

    -- L'arco del ramo inverso (reso) nel grafo del lineage. ⭐ Dal 2026-10-11
    -- (20261011-64/-66) la grammatica dei 13 archi sta nella funzione e la
    -- vista ne e' la proiezione: il contratto e' con la funzione.
    ('config',    'sorgenti',                      'RESO_VENDITA',
     'vendite',   'fn_documento_lineage_archi',    'FUNZIONE', '20261011-64'),

    -- La sorgente che la ri-consegna scrive sul DDT generato dal reso.
    ('config',    'sorgenti',                      'RESO_VENDITA',
     'vendite',   'fn_genera_ddt_riconsegna',      'FUNZIONE', '20260828-04'),

    -- L'arco sorgente-DDT. ⚠️ Qui la costante non basta: conta anche il
    -- key_selector, ed e' il test 3.
    ('config',    'sorgenti',                      'DDT_VENDITA',
     'vendite',   'fn_documento_lineage_archi',    'FUNZIONE', '20261011-64');

-- Cosa il catalogo offre DAVVERO, con il predicato di attivita' proprio di
-- ciascuna tabella. ⚠️ Non e' lo stesso predicato ovunque: `sorgenti` e
-- `stati_doc_reso` hanno solo `attivo`, gli stati contabili hanno ANCHE
-- `obsoleto_dal` — e una riga ritirata per data e' fuori servizio quanto una
-- spenta col flag.
CREATE TEMP TABLE _presenti (cat_schema text, cat_tabella text, valore text) ON COMMIT DROP;

INSERT INTO _presenti
SELECT 'config', 'sorgenti', s.codice_interno
  FROM config.sorgenti s
 WHERE s.attivo IS TRUE;

INSERT INTO _presenti
SELECT 'config', 'stati_doc_reso', r.codice_interno
  FROM config.stati_doc_reso r
 WHERE r.attivo IS TRUE;

INSERT INTO _presenti
SELECT 'pagamenti', 'vendite_contabili_righe_stati', v.codice_interno
  FROM pagamenti.vendite_contabili_righe_stati v
 WHERE v.attivo IS TRUE
   AND v.obsoleto_dal IS NULL;

-- ============================================================
-- 1. Gemello «esiste» — senza, i test 2 e 4 sono muti
-- ============================================================
-- ⚠️ Un test che CONTA I CATTIVI risponde zero anche quando i candidati sono
--   zero: se `_costanti` fosse vuota, o se una tabella di catalogo fosse stata
--   rinominata, il test 2 sarebbe verde senza aver verificato niente. Questa e'
--   la riga che lo impedisce.
SELECT ok(
    (SELECT count(*) FROM _costanti) = 7
    AND NOT EXISTS (
        SELECT 1 FROM _costanti c
         WHERE to_regclass(format('%I.%I', c.cat_schema, c.cat_tabella)) IS NULL
    )
    AND (SELECT count(*) FROM _presenti) > 0,
    '1. La lista delle costanti attese e'' popolata e ogni catalogo che nomina esiste'
);

-- ============================================================
-- 2. Ogni costante attesa esiste a catalogo ed e' ATTIVA
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM _costanti c
      WHERE NOT EXISTS (
            SELECT 1 FROM _presenti p
             WHERE p.cat_schema  = c.cat_schema
               AND p.cat_tabella = c.cat_tabella
               AND p.valore      = c.valore
      )),
    0,
    '2. Ogni costante citata dal codice esiste nel suo catalogo ed e'' attiva'
);

-- ============================================================
-- 3. DDT_VENDITA porta ancora la chiave che il ramo T assume
-- ============================================================
-- ⚠️ La chiave del ramo NON e' una scelta di chi ha scritto la vista: e' letta
--   da config.sorgenti. Se DDT_VENDITA passasse a key_selector = 'uid', il ramo
--   azzererebbe i suoi archi IN SILENZIO — nessun errore, solo un grafo che
--   dimagrisce. Era la preCondition del changeSet 20260828-24.
SELECT ok(
    EXISTS (
        SELECT 1 FROM config.sorgenti
         WHERE codice_interno = 'DDT_VENDITA'
           AND attivo IS TRUE
           AND key_selector = 'id'
    ),
    '3. config.sorgenti DDT_VENDITA e'' attiva e ha key_selector = ''id'''
);

-- ============================================================
-- 4. Anti-marciume: la coppia (oggetto, costante) e' ancora vera
-- ============================================================
-- ⭐ E' la meta' che impedisce all'elenco di invecchiare. Se una funzione viene
--   riscritta e smette di citare la costante, la riga di `_costanti` sta
--   guardando un contratto che non esiste piu': il test diventa rosso e chiede
--   di TOGLIERLA, invece di restare verde presidiando il nulla.
-- ⚠️ Il match e' sul letterale fra apici — `'ANNULLATO'` — non sulla parola
--   nuda: `prosrc LIKE '%ANNULLATO%'` risponderebbe vero anche a un commento.
SELECT is(
    (SELECT count(*)::int
       FROM _costanti c
      WHERE NOT EXISTS (
            SELECT 1
              FROM pg_proc p
              JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE c.obj_tipo   = 'FUNZIONE'
               AND n.nspname    = c.obj_schema
               AND p.proname    = c.obj_nome
               -- ⚠️ Una funzione BEGIN ATOMIC ha `prosrc` VUOTO: il corpo sta
               --    in prosqlbody, e lo deparsa pg_get_function_sqlbody (i
               --    letterali escono come 'X'::text, che il LIKE prende).
               AND coalesce(nullif(p.prosrc, ''), pg_get_function_sqlbody(p.oid))
                   LIKE '%' || quote_literal(c.valore) || '%'
      )
        AND NOT EXISTS (
            SELECT 1
              FROM pg_views v
             WHERE c.obj_tipo   = 'VISTA'
               AND v.schemaname = c.obj_schema
               AND v.viewname   = c.obj_nome
               AND v.definition LIKE '%' || quote_literal(c.valore) || '%'
      )),
    0,
    '4. Ogni oggetto dell''elenco esiste ancora e cita ancora la sua costante'
);

-- ============================================================
-- 5. Derivato: le sorgenti passate ai trigger di chiusura commessa
-- ============================================================
-- ⭐ Qui NON c'e' un elenco: la sorgente e' il PRIMO ARGOMENTO del trigger, e
--   si legge da `pg_trigger.tgargs`. Copre percio' anche i trigger che qualcuno
--   montera' domani su una testata nuova — che e' esattamente cio' che la
--   preCondition del changeSet 20260826-36 non sapeva fare, perche' elencava a
--   mano le quattro sorgenti del giorno.
-- ⚠️ `tgargs` e' un bytea con gli argomenti separati da NUL: `encode(...,
--   'escape')` li rende come la stringa letterale `\000`, che e' su cosa si
--   spezza.
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger tg
       JOIN pg_proc      pr ON pr.oid = tg.tgfoid
       JOIN pg_namespace pn ON pn.oid = pr.pronamespace
      WHERE NOT tg.tgisinternal
        AND pn.nspname = 'vendite'
        AND pr.proname = 'trgfn_doc_guard_chiusura_sorgente'
        AND NOT EXISTS (
            SELECT 1 FROM config.sorgenti s
             WHERE s.codice_interno = (string_to_array(encode(tg.tgargs, 'escape'), '\000'))[1]
               AND s.attivo IS TRUE
        )),
    0,
    '5. Ogni sorgente passata ai freni di chiusura commessa e'' a catalogo e attiva'
);

-- ============================================================
-- 6. Gemello «esiste» del test 5
-- ============================================================
-- ⚠️ Anche il test 5 conta i cattivi: se i trigger venissero rinominati o
--   smontati risponderebbe zero su zero. Il 2026-09-02 erano sette.
-- ⚠️ rev 2026-10-11 (brief-db-annullo-documento-con-legami D-5): il motore del
--   ritiro automatico (trgfn_doc_ritira_commessa_attivita, quattro trigger
--   _z90_) si e' ritirato — le righe NON_EMESSA le ritira il verbo di annullo
--   dopo la conferma. Restano i freni sulle righe EMESSA: tre (DDT, ordine,
--   contratto; il preventivo usa il proprio codice dentro la sua check).
SELECT cmp_ok(
    (SELECT count(*)::int
       FROM pg_trigger tg
       JOIN pg_proc      pr ON pr.oid = tg.tgfoid
       JOIN pg_namespace pn ON pn.oid = pr.pronamespace
      WHERE NOT tg.tgisinternal
        AND pn.nspname = 'vendite'
        AND pr.proname = 'trgfn_doc_guard_chiusura_sorgente'),
    '>=', 3,
    '6. I freni di chiusura sulle righe di commessa emesse esistono (il test 5 ha dei candidati)'
);

-- ============================================================
-- Chiusura
-- ============================================================
-- ⚠️ Niente cleanup: le temp table sono ON COMMIT DROP e chiude il ROLLBACK.
SELECT * FROM finish();
ROLLBACK;
