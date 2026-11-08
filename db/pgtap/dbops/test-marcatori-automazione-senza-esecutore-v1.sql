-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — il file legge il catalogo di PostgreSQL, l'ambito
--   delle automazioni e il registro del debito: nessun dato di dominio, nessuna
--   RLS. Una veste applicativa non cambierebbe nessuna risposta.
-- pgtap-runner: owner
-- pgtap-runner-motivo: i casi si COSTRUISCONO (uno schema e cinque tabelle di
--   prova, trigger montati e disabilitati: DDL) e si scrivono righe in
--   dbops.automation_scope, dbops.automation_cleanup_exclusions e
--   dbops.marcatori_automazione_debito, che a runtime popola solo il mirror CSV
--   e su cui il ruolo applicativo non scrive. Tutto in transazione annullata.
-- pgTAP test per Zero ERP
--
-- Test: una colonna che promette un'automazione ha chi la esegue
--   Vista: dbops.vw_marcatori_automazione_senza_esecutore (20261108-27; la
--   colonna di storicizzazione dall'override, 20261108-92)
--   Registro: dbops.marcatori_automazione_debito (20261108-26, seed 20261108-31)
--   Brief: brief-db-revisione-dbops, giro 7 (D35, D36, D37; perimetro di Tid del
--   2026-11-07: tx_id, storicizza, cleanup_at); giro 7-bis (§23, 2026-11-08):
--   i cataloghi di dbops scritti dal solo seed perdono i marcatori, la vista
--   legge l'override STORICIZZA_COL.
--
-- Elenco test (plan 16):
--   1) ⭐ IL PRESIDIO: sul database nessuna riga NON_DICHIARATO ne' DEBITO_ESTINTO
--   2) le chiusure del giro 7: dbops.audit_sources non ha piu' le quattro colonne
--   3) le chiusure del giro 7: shop.ricevute e dbops.ai_query_log sono nell'ambito
--   4) ⭐ i tre marcatori fuori ambito escono NON_DICHIARATO (caso COSTRUITO),
--      e il trigger montato a mano basta per tx_id
--   5) ⛔ un trigger DISABILITATO non e' un esecutore
--   6) ⭐ il vocabolario del CHECK del registro e' quello che la vista riconosce
--   7) una tabella che entra nell'ambito esce dal presidio (lo stesso filtro dei runner)
--   8) ⛔ cleanup_at nell'ambito ma escluso dalla pulizia resta scoperto, col perche'
--   9) ⭐ una riga di registro sul caso lo fa DEBITO_DICHIARATO, con la ragione
--  10) ⛔ una riga di registro senza piu' il suo caso esce DEBITO_ESTINTO
--  11) ⛔ il registro rifiuta una ragione corta
--  12) ⛔ e un marcatore fuori vocabolario
--  13) lo schema storico e' fuori: una shadow ricopia le colonne della madre
--  14) le chiusure del giro 7-bis: i sedici cataloghi di dbops scritti dal solo
--      seed non hanno piu' tx_id, data_update, user_update
--  15) ⭐ storicizza rinominata con l'override STORICIZZA_COL e' ancora il marcatore
--  16) ⛔ una colonna «storicizza» su una tabella con l'override verso un'altra
--      colonna non lo e' (si legge come la provision dello storico)
--
-- ⭐ I test 4 e 7 vanno letti insieme: il primo prova che il presidio vede, il
--   secondo che non vede troppo. Provare solo il 4 lascerebbe passare una vista
--   che segnala tutto; solo il 7, una vista che non segnala niente.
-- ⚠️ Il test 1 guarda il database com'e': su un dbdev fra l'apply e la
--   convergenza (ci-apply) e' verde lo stesso, perche' la vista guarda l'ambito e
--   non i trigger montati dai runner. E' una scelta del criterio, non un buco.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- 1) Il presidio sul database com'e' (prima di costruire i casi)
-- ============================================================
SELECT is_empty(
    $q$SELECT marcatore, schema_tabella, nome_tabella, stato
         FROM dbops.vw_marcatori_automazione_senza_esecutore
        WHERE stato <> 'DEBITO_DICHIARATO'$q$,
    '1) Nessun marcatore senza esecutore NON dichiarato, nessuna riga di registro estinta');

-- ============================================================
-- 2-3) Le chiusure del giro 7
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM pg_attribute a
      WHERE a.attrelid = 'dbops.audit_sources'::regclass
        AND a.attnum > 0 AND NOT a.attisdropped
        AND a.attname IN ('tx_id', 'storicizza', 'data_update', 'user_update')),
    0,
    '2) dbops.audit_sources non ha piu'' tx_id, storicizza, data_update, user_update (D37)');

SELECT ok(
    'shop'  = ANY (dbops.fn_resolve_scope(NULL::text[]))
    AND dbops.fn_table_in_scope('shop', 'ricevute')
    AND 'dbops' = ANY (dbops.fn_resolve_scope(NULL::text[]))
    AND dbops.fn_table_in_scope('dbops', 'ai_query_log'),
    '3) shop.ricevute e dbops.ai_query_log sono nell''ambito delle automazioni (D35, D36)');

-- ============================================================
-- I casi costruiti: uno schema SUO, fuori dall'ambito (non ha righe in
-- dbops.automation_scope, quindi fn_resolve_scope non lo restituisce).
-- ============================================================
CREATE SCHEMA pgtap_marcatori;

CREATE TABLE pgtap_marcatori.t_tx       (id int PRIMARY KEY, tx_id uuid);
CREATE TABLE pgtap_marcatori.t_tx_mano  (id int PRIMARY KEY, tx_id uuid);
CREATE TABLE pgtap_marcatori.t_tx_spento(id int PRIMARY KEY, tx_id uuid);
CREATE TABLE pgtap_marcatori.t_sto      (id int PRIMARY KEY, storicizza boolean NOT NULL DEFAULT true);
CREATE TABLE pgtap_marcatori.t_cl       (id int PRIMARY KEY, cleanup_at timestamptz);
CREATE TABLE pgtap_marcatori.t_nessuno  (id int PRIMARY KEY, data_update timestamptz);

CREATE TRIGGER trg_t_tx_mano_gen_tx_id_ins_upd
    BEFORE INSERT OR UPDATE ON pgtap_marcatori.t_tx_mano
    FOR EACH ROW EXECUTE FUNCTION dbops.trgfn_tx_id_managed();
CREATE TRIGGER trg_t_tx_spento_gen_tx_id_ins_upd
    BEFORE INSERT OR UPDATE ON pgtap_marcatori.t_tx_spento
    FOR EACH ROW EXECUTE FUNCTION dbops.trgfn_tx_id_managed();
ALTER TABLE pgtap_marcatori.t_tx_spento DISABLE TRIGGER trg_t_tx_spento_gen_tx_id_ins_upd;

CREATE TEMP VIEW tmp_casi AS
SELECT marcatore, nome_tabella, stato, manca, ragione
  FROM dbops.vw_marcatori_automazione_senza_esecutore
 WHERE schema_tabella = 'pgtap_marcatori';

-- ⚠️ set_eq e non results_eq: nome_tabella viene da name, e un ORDER BY sul
--   cast a text non sa quale collation usare.
SELECT set_eq(
    $q$SELECT marcatore, nome_tabella, stato FROM tmp_casi
        WHERE nome_tabella <> 't_tx_spento'$q$,
    $q$VALUES ('TX_ID'::text,      't_tx'::text,  'NON_DICHIARATO'::text),
              ('STORICIZZA'::text, 't_sto'::text, 'NON_DICHIARATO'::text),
              ('CLEANUP_AT'::text, 't_cl'::text,  'NON_DICHIARATO'::text)$q$,
    '4) I tre marcatori fuori ambito escono NON_DICHIARATO; il trigger a mano basta per tx_id; data_update non e'' nel criterio');

SELECT is(
    (SELECT marcatore FROM tmp_casi WHERE nome_tabella = 't_tx_spento'),
    'TX_ID',
    '5) Un trigger disabilitato non e'' un esecutore: la tabella resta scoperta');

-- ⭐ Il vocabolario si legge dal CHECK del registro, non da un elenco nel test:
--   un marcatore nuovo senza il suo ramo nella vista fa rosso qui.
SELECT set_eq(
    $q$SELECT (regexp_matches(pg_get_constraintdef(k.oid), '''([A-Z_]+)''', 'g'))[1]
         FROM pg_constraint k
        WHERE k.conrelid = 'dbops.marcatori_automazione_debito'::regclass
          AND k.conname  = 'chk_marcatori_automazione_debito_marcatore'$q$,
    $q$SELECT DISTINCT marcatore FROM tmp_casi$q$,
    '6) Ogni marcatore del CHECK del registro ha il suo ramo nella vista, e viceversa');

-- ============================================================
-- 7-8) L'ambito: lo stesso filtro dei runner, e l'esclusione dalla pulizia
-- ============================================================
INSERT INTO dbops.automation_scope (schema_name, table_like)
VALUES ('pgtap_marcatori', 't_cl'), ('pgtap_marcatori', 't_sto');

SELECT set_eq(
    $q$SELECT nome_tabella FROM tmp_casi$q$,
    $q$VALUES ('t_tx'::text), ('t_tx_spento'::text)$q$,
    '7) Le tabelle che entrano nell''ambito escono dal presidio; quelle dello stesso schema non ammesse dal filtro restano');

INSERT INTO dbops.automation_cleanup_exclusions (schema_name, table_name, enabled, reason)
VALUES ('pgtap_marcatori', 't_cl', true, 'pgTAP: esclusa dalla pulizia per il test 8');

SELECT ok(
    (SELECT manca LIKE '%automation_cleanup_exclusions%'
       FROM tmp_casi WHERE nome_tabella = 't_cl' AND marcatore = 'CLEANUP_AT'),
    '8) cleanup_at nell''ambito ma escluso dalla pulizia resta scoperto, e la vista dice perche''');

-- ============================================================
-- 9-12) Il registro del debito
-- ============================================================
INSERT INTO dbops.marcatori_automazione_debito
       (id, marcatore, schema_tabella, nome_tabella, ragione, data_registrazione)
VALUES (990001, 'TX_ID', 'pgtap_marcatori', 't_tx',
        'pgTAP: caso costruito, debito dichiarato per provare lo stato atteso del presidio', DATE '2026-11-07'),
       (990002, 'TX_ID', 'pgtap_marcatori', 't_tx_mano',
        'pgTAP: caso costruito, la tabella ha il trigger a mano e il debito non esiste piu''', DATE '2026-11-07');

SELECT results_eq(
    $q$SELECT stato, ragione IS NOT NULL FROM tmp_casi WHERE nome_tabella = 't_tx'$q$,
    $q$VALUES ('DEBITO_DICHIARATO'::text, true)$q$,
    '9) Una riga di registro sul caso lo fa DEBITO_DICHIARATO, con la ragione accanto');

SELECT results_eq(
    $q$SELECT marcatore, stato FROM tmp_casi WHERE nome_tabella = 't_tx_mano'$q$,
    $q$VALUES ('TX_ID'::text, 'DEBITO_ESTINTO'::text)$q$,
    '10) Una riga di registro senza piu'' il suo caso esce DEBITO_ESTINTO: va tolta');

SELECT throws_ok(
    $q$INSERT INTO dbops.marcatori_automazione_debito
              (id, marcatore, schema_tabella, nome_tabella, ragione, data_registrazione)
       VALUES (990003, 'TX_ID', 'pgtap_marcatori', 't_sto', 'TODO', DATE '2026-11-07')$q$,
    '23514', NULL,
    '11) Il registro rifiuta una ragione di meno di quaranta caratteri');

SELECT throws_ok(
    $q$INSERT INTO dbops.marcatori_automazione_debito
              (id, marcatore, schema_tabella, nome_tabella, ragione, data_registrazione)
       VALUES (990004, 'DATA_UPDATE', 'pgtap_marcatori', 't_nessuno',
               'pgTAP: un marcatore fuori dal vocabolario deciso per il presidio', DATE '2026-11-07')$q$,
    '23514', NULL,
    '12) Il registro rifiuta un marcatore fuori vocabolario (data_update e'' fuori per decisione)');

-- ============================================================
-- 13) Lo schema storico e' fuori
-- ============================================================
CREATE TABLE storico.pgtap_marcatori_shadow (id int PRIMARY KEY, tx_id uuid, storicizza boolean);

SELECT is_empty(
    $q$SELECT 1 FROM dbops.vw_marcatori_automazione_senza_esecutore
        WHERE schema_tabella = 'storico'$q$,
    '13) Lo schema storico e'' fuori dal criterio: le shadow ricopiano le colonne della madre');

-- ============================================================
-- 14) Le chiusure del giro 7-bis (20261108-90, -91)
-- ============================================================
SELECT is_empty(
    $q$SELECT c.relname::text, a.attname::text
         FROM pg_attribute a
         JOIN pg_class c ON c.oid = a.attrelid
        WHERE c.relnamespace = 'dbops'::regnamespace
          AND c.relname IN ('coda_lavori_tipi', 'marcatori_automazione_debito', 'processi',
                            'processi_bersagli', 'rls_perimetro_debito', 'stati_check_dichiarazioni',
                            'automazione_chiusura_scadenze', 'cause_fallimento',
                            'codici_errore_senza_policy', 'emittente_modi',
                            'messaggi_errore_codici_legacy', 'presidi', 'presidi_cause',
                            'presidi_testi', 'riferimenti_morti_esenzioni', 'storico_scope_policy')
          AND a.attname IN ('tx_id', 'data_update', 'user_update')
          AND a.attnum > 0 AND NOT a.attisdropped$q$,
    '14) I sedici cataloghi di dbops scritti dal solo seed non hanno piu'' tx_id, data_update, user_update');

-- ============================================================
-- 15-16) L'override della colonna di storicizzazione (20261108-92)
--   Due tabelle nuove dello schema di prova, fuori dall'ambito (il test 7 vi
--   ammette solo t_cl e t_sto per nome).
-- ============================================================
CREATE TABLE pgtap_marcatori.t_sto_ovr     (id int PRIMARY KEY, da_storicizzare boolean NOT NULL DEFAULT true);
CREATE TABLE pgtap_marcatori.t_sto_altrove (id int PRIMARY KEY, storicizza boolean NOT NULL DEFAULT true);
INSERT INTO dbops.automation_overrides_cols (schema_name, table_name, col_role, col_name)
VALUES ('pgtap_marcatori', 't_sto_ovr',     'STORICIZZA_COL', 'da_storicizzare'),
       ('pgtap_marcatori', 't_sto_altrove', 'STORICIZZA_COL', 'flag_storico_inesistente');

SELECT results_eq(
    $q$SELECT marcatore, stato FROM tmp_casi WHERE nome_tabella = 't_sto_ovr'$q$,
    $q$VALUES ('STORICIZZA'::text, 'NON_DICHIARATO'::text)$q$,
    '15) La colonna di storicizzazione rinominata con l''override STORICIZZA_COL e'' il marcatore');

SELECT is_empty(
    $q$SELECT 1 FROM tmp_casi WHERE nome_tabella = 't_sto_altrove'$q$,
    '16) Con l''override verso un''altra colonna, la colonna «storicizza» non e'' il marcatore (come la provision)');

SELECT * FROM finish();
ROLLBACK;
