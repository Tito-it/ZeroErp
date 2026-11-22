-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il CATALOGO DELLE LISTE, giro 4.
--   Brief: brief-db-revisione-ui, giro 4 (U22-U30, U37; Q13-Q18, Q32, Q35,
--   Q47, Q48); i casi 25-26 dal giro 5 (U31).
--   ChangeSet: 00_schema/ui/20261120-43, -44; 20_code/ui/20261120-45 … -49;
--   20_code/dbops/20261120-50; 90_end/20261120-51, -52; i registri in
--   80_data/sql/dbops (automazione_attivo_eccezioni, automation_lock_columns).
--
-- ⭐ Gira come APPLICAZIONE (il runner di default): i guard del giro distinguono
--   l'applicazione dal migrate (le dichiarazioni, le colonne orfane), e da owner
--   passerebbero tutti per la ragione sbagliata.
-- ⭐ Il mondo si COSTRUISCE: le liste di prova leggono tabelle TEMPORANEE, che
--   l'applicazione puo' creare e cambiare. Cosi' si costruiscono una vista che
--   cambia, una lista spenta su una relazione che non ha il campo, una tabella
--   partizionata, e la colonna tolta con un DDL che solo il presidio vede.
--   Nessun numero del seed decide un'asserzione.
-- ⚠️ I casi 7 e 8 chiedono una lista che dichiara legge_lineage: le porta il CSV
--   del seed (le sei liste documentali). Senza, skip() dichiarato: l'applicazione
--   non puo' dichiararla (e' il caso 9), e un verde senza lista lo direbbe per
--   sottrazione.
-- ⚠️ I casi 12-13 (i lucchetti) chiedono i trigger montati dal runner
--   (20261120-52) e il 14 il ritiro dei trigger ATTIVO (20261120-51): nella prova
--   sull'estratto, prima dell'apply, non ci sono.
--
-- Elenco test (plan 34):
--   La struttura
--    1) lista_colonna.origine_campo e' l'enum ui.origine_campo_lista, NOT NULL
--    2) il CHECK che ricopiava U24 + U25 non c'e' piu', i tre nuovi si'
--   U24, U25: campo sorgente ed export
--    3) un'azione con un campo sorgente e' rifiutata dal CHECK
--    4) una colonna composta esportabile e' rifiutata dal CHECK
--    5) ... non esportabile passa
--   U26: la lineage
--    6) ⭐ una colonna LINEAGE su una lista che non la dichiara: E_UI_LINEAGE_NON_DICHIARATA
--    7) ... su una lista che la dichiara passa
--    8) ... ma non filtrabile: il CHECK la rifiuta
--   U23: le dichiarazioni e i codici
--    9) l'app che dichiara legge_lineage su una lista nuova: E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE
--   10) ⭐ l'app che porta perimetro_emittente a false: lo stesso codice
--   11) ... e una lista nuova con perimetro_emittente = true (il default) passa
--   12) il codice di una lista non si riscrive: E_UI_LISTA_CODICE_IMMUTABILE
--   13) il codice di una colonna non si riscrive: E_UI_COLONNA_CODICE_IMMUTABILE
--   U22: la lista spenta sospende colonne e preset
--   14) ⭐ una lista con colonna e preset accesi si spegne
--   15) ... e per codice non risponde piu'
--   16) ... riaccesa, colonna e preset sono ancora accesi
--   U27: le colonne e la relazione
--   17) ⭐ l'app che cambia vista lasciando orfana una colonna: E_UI_LISTA_COLONNE_ORFANE
--   18) ... la frase nomina la colonna
--   19) su una lista spenta una colonna col campo assente e' accolta
--   20) ⭐ ... e la riaccensione e' rifiutata: E_UI_LISTA_COLONNE_ORFANE
--   21) una lista su una tabella partizionata e' accolta, con la sua colonna
--   22) ⭐ il presidio vede la colonna tolta con un DDL (CAMPO_ASSENTE)
--   23) ... e una lista accesa sana non ci compare
--   U28: i testi vuoti
--   24) una vista_sql vuota e' rifiutata dal CHECK
--   U31 (giro 5): il catalogo delle dashboard non si scrive come applicazione
--   25) l'INSERT di un widget: permesso negato
--   26) l'INSERT di una dashboard: permesso negato
--   U29: la veste NULL non allarga
--   27) ⭐ con la veste NULL, la colonna sensibile concessa TUTTO dal profilo di
--       un'altra veste resta BLOCCATO (il livello piu' restrittivo)
--   28) ... e sotto quella veste e' TUTTO
--   Aggiunti dal /verifica-db del 2026-11-22
--   29) il presidio vede la relazione tolta con un DDL (RELAZIONE_ASSENTE)
--   30) ... e una colonna LINEAGE su un nome che la sintesi non ha
--       (LINEAGE_SCONOSCIUTA; skip come i casi 7-8)
--   31-34) U28: il codice, la descrizione, lo schema_dati e le note vuoti di
--       una lista, un CHECK per caso, riconosciuto per nome
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(34);

-- ============================================================
-- Fixture: le relazioni temporanee e le liste che le leggono
-- ============================================================
CREATE TEMP TABLE _rel_ab (a integer, b integer) ON COMMIT DROP;
CREATE TEMP TABLE _rel_a (a integer) ON COMMIT DROP;
CREATE TEMP TABLE _rel_part (a integer, k integer) PARTITION BY LIST (k);
CREATE TEMP TABLE _rel_ddl (a integer, b integer) ON COMMIT DROP;

CREATE TEMP TABLE _s AS
SELECT nspname::text AS schema_tmp FROM pg_catalog.pg_namespace WHERE oid = pg_my_temp_schema();

CREATE TEMP TABLE _l AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  SELECT '_pgtap.catalogo_' || v.n || '_' || substr(md5(clock_timestamp()::text), 1, 6),
         'Lista test pgTAP catalogo ' || v.n, s.schema_tmp, v.rel, v.attiva, '_pgtap'
    FROM _s s
   CROSS JOIN (VALUES (1, '_rel_ab', TRUE),     -- la lista che cambia vista
                      (2, NULL,      TRUE),     -- senza vista: azioni, composte, lineage
                      (3, '_rel_a',  FALSE),    -- spenta, la relazione non ha b
                      (4, '_rel_ddl', TRUE),    -- la colonna tolta col DDL
                      (5, '_rel_ab', TRUE),     -- si spegne con le parti accese
                      (6, NULL,      FALSE))    -- spenta e senza vista: parla solo il CHECK
               AS v(n, rel, attiva)
  RETURNING id, codice
)
SELECT id AS lista_id, codice AS lista_codice,
       row_number() OVER (ORDER BY id) AS n FROM ins;

INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato, ordine_default, user_insert)
SELECT l.lista_id, 'col_b', 'Colonna b', 'b', 'string', 10, '_pgtap'
  FROM _l l WHERE l.n IN (1, 4, 5);

-- Il preset della lista 5.
INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, attivo, user_insert)
SELECT lista_id, 'P_CATALOGO', 'Preset test catalogo', 'sistema', TRUE, '_pgtap' FROM _l WHERE n = 5;

-- ============================================================
-- 1-2) La struttura
-- ============================================================
SELECT is(
    (SELECT format_type(a.atttypid, a.atttypmod) || ':' || a.attnotnull::text
       FROM pg_catalog.pg_attribute a
      WHERE a.attrelid = 'ui.lista_colonna'::regclass AND a.attname = 'origine_campo'),
    'ui.origine_campo_lista:true',
    '1) lista_colonna.origine_campo e'' l''enum ui.origine_campo_lista, NOT NULL');

SELECT is(
    (SELECT array_agg(conname::text ORDER BY conname)
       FROM pg_catalog.pg_constraint
      WHERE conrelid = 'ui.lista_colonna'::regclass
        AND conname IN ('chk_ui_lista_colonna_azione_non_esportabile',
                        'chk_ui_lista_colonna_azione_senza_campo',
                        'chk_ui_lista_colonna_senza_campo_non_esportabile',
                        'chk_ui_lista_colonna_lineage_solo_mostrata')),
    ARRAY['chk_ui_lista_colonna_azione_senza_campo',
          'chk_ui_lista_colonna_lineage_solo_mostrata',
          'chk_ui_lista_colonna_senza_campo_non_esportabile'],
    '2) il CHECK delle azioni non esportabili e'' ritirato, i tre nuovi ci sono');

-- ============================================================
-- 3-5) U24, U25: sulla lista senza vista, il guard del campo non parla
-- ============================================================
SELECT throws_ok(
    format($$ INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_colonna,
                                           tipo_dato, esportabile, ordine_default, user_insert)
              VALUES (%s, 'azione_con_campo', 'Azione', 'qualcosa', 'azione', 'string', false, 10, '_pgtap') $$,
           (SELECT lista_id FROM _l WHERE n = 2)),
    '23514', NULL,
    '3) un''azione con un campo sorgente e'' rifiutata (chk_ui_lista_colonna_azione_senza_campo)');

SELECT throws_ok(
    format($$ INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato,
                                           ordine_default, user_insert)
              VALUES (%s, 'composta_esportabile', 'Composta', NULL, 'string', 10, '_pgtap') $$,
           (SELECT lista_id FROM _l WHERE n = 2)),
    '23514', NULL,
    '4) una colonna composta esportabile e'' rifiutata (chk_ui_lista_colonna_senza_campo_non_esportabile)');

SELECT lives_ok(
    format($$ INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato,
                                           esportabile, ordine_default, user_insert)
              VALUES (%s, 'composta', 'Composta', NULL, 'string', false, 10, '_pgtap') $$,
           (SELECT lista_id FROM _l WHERE n = 2)),
    '5) ... non esportabile passa');

-- ============================================================
-- 6-8) U26: la lineage
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$ INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, origine_campo,
                                         tipo_dato, filtrabile, ordinabile, ordine_default, user_insert)
           VALUES (%s, 'lineage_qui_no', 'Transito', 'frontiera_codice', 'LINEAGE', 'string',
                   false, false, 10, '_pgtap') $$,
        (SELECT lista_id FROM _l WHERE n = 2))),
    'E_UI_LINEAGE_NON_DICHIARATA',
    '6) una colonna LINEAGE su una lista che non la dichiara: E_UI_LINEAGE_NON_DICHIARATA');

CREATE TEMP TABLE _ll AS
SELECT ld.id AS lista_id FROM ui.lista_definizione ld
 WHERE ld.legge_lineage AND ld.attivo ORDER BY ld.id LIMIT 1;

SELECT CASE WHEN EXISTS (SELECT 1 FROM _ll)
    THEN lives_ok(
        format($$ INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, origine_campo,
                                               tipo_dato, filtrabile, ordinabile, ordine_default, user_insert)
                  VALUES (%s, '_pgtap_lineage_ok', 'Transito', 'frontiera_codice', 'LINEAGE', 'string',
                          false, false, 10, '_pgtap') $$,
               (SELECT lista_id FROM _ll)),
        '7) ... su una lista che la dichiara passa')
    ELSE skip('7) nessuna lista dichiara legge_lineage (il CSV del seed non e'' caricato): il caso non si costruisce dall''applicazione', 1)
END;

SELECT CASE WHEN EXISTS (SELECT 1 FROM _ll)
    THEN throws_ok(
        format($$ INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, origine_campo,
                                               tipo_dato, filtrabile, ordinabile, ordine_default, user_insert)
                  VALUES (%s, '_pgtap_lineage_filtro', 'Transito', 'frontiera_codice', 'LINEAGE', 'string',
                          true, false, 10, '_pgtap') $$,
               (SELECT lista_id FROM _ll)),
        '23514', NULL,
        '8) ... ma filtrabile e'' rifiutata (chk_ui_lista_colonna_lineage_solo_mostrata)')
    ELSE skip('8) nessuna lista dichiara legge_lineage (il CSV del seed non e'' caricato)', 1)
END;

-- ============================================================
-- 9-13) U23: le dichiarazioni e i codici
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$ INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, attivo, user_insert, legge_lineage)
           VALUES ('_pgtap.catalogo_lineage', 'Lista che si dichiara da sola', 'vendite', TRUE, '_pgtap', TRUE) $$),
    'E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE',
    '9) l''app che dichiara legge_lineage: E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$ UPDATE ui.lista_definizione SET perimetro_emittente = false WHERE id = %s $$,
        (SELECT lista_id FROM _l WHERE n = 2))),
    'E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE',
    '10) l''app che porta perimetro_emittente a false: E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE');

SELECT lives_ok(
    $$ INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, attivo, user_insert, perimetro_emittente)
       VALUES ('_pgtap.catalogo_perimetro', 'Lista col perimetro di default', 'vendite', TRUE, '_pgtap', TRUE) $$,
    '11) ... una lista nuova col perimetro di default passa');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$ UPDATE ui.lista_definizione SET codice = codice || '_x' WHERE id = %s $$,
        (SELECT lista_id FROM _l WHERE n = 2))),
    'E_UI_LISTA_CODICE_IMMUTABILE',
    '12) il codice di una lista non si riscrive: E_UI_LISTA_CODICE_IMMUTABILE');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$ UPDATE ui.lista_colonna SET codice = 'col_b_x' WHERE lista_id = %s AND codice = 'col_b' $$,
        (SELECT lista_id FROM _l WHERE n = 1))),
    'E_UI_COLONNA_CODICE_IMMUTABILE',
    '13) il codice di una colonna non si riscrive: E_UI_COLONNA_CODICE_IMMUTABILE');

-- ============================================================
-- 14-16) U22: la lista spenta sospende colonne e preset
-- ============================================================
SELECT lives_ok(
    format($$ UPDATE ui.lista_definizione SET attivo = false WHERE id = %s $$,
           (SELECT lista_id FROM _l WHERE n = 5)),
    '14) una lista con colonna e preset accesi si spegne');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$ SELECT ui.fn_lista_da_codice(%L) $$, (SELECT lista_codice FROM _l WHERE n = 5))),
    'E_UI_LISTA_NON_TROVATA',
    '15) ... e per codice non risponde piu''');

UPDATE ui.lista_definizione SET attivo = true WHERE id = (SELECT lista_id FROM _l WHERE n = 5);

SELECT is(
    (SELECT (SELECT bool_and(lc.attivo) FROM ui.lista_colonna lc WHERE lc.lista_id = l.lista_id)::text
            || ':' ||
            (SELECT bool_and(lp.attivo) FROM ui.lista_preset lp WHERE lp.lista_id = l.lista_id)::text
       FROM _l l WHERE l.n = 5),
    'true:true',
    '16) ... riaccesa, colonna e preset sono ancora accesi');

-- ============================================================
-- 17-23) U27: le colonne e la relazione
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$ UPDATE ui.lista_definizione SET vista_sql = '_rel_a' WHERE id = %s $$,
        (SELECT lista_id FROM _l WHERE n = 1))),
    'E_UI_LISTA_COLONNE_ORFANE',
    '17) l''app che cambia vista lasciando orfana una colonna: E_UI_LISTA_COLONNE_ORFANE');

SELECT throws_like(
    format($$ UPDATE ui.lista_definizione SET vista_sql = '_rel_a' WHERE id = %s $$,
           (SELECT lista_id FROM _l WHERE n = 1)),
    '%col_b%',
    '18) ... la frase nomina la colonna');

SELECT lives_ok(
    format($$ INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato,
                                           ordine_default, user_insert)
              VALUES (%s, 'col_b', 'Colonna b', 'b', 'string', 10, '_pgtap') $$,
           (SELECT lista_id FROM _l WHERE n = 3)),
    '19) su una lista spenta una colonna col campo assente e'' accolta');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        $$ UPDATE ui.lista_definizione SET attivo = true WHERE id = %s $$,
        (SELECT lista_id FROM _l WHERE n = 3))),
    'E_UI_LISTA_COLONNE_ORFANE',
    '20) ... e la riaccensione e'' rifiutata: E_UI_LISTA_COLONNE_ORFANE');

SELECT lives_ok(
    format($$ WITH l AS (
                INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
                VALUES ('_pgtap.catalogo_partizionata', 'Lista su una partizionata', %L, '_rel_part', TRUE, '_pgtap')
                RETURNING id)
              INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato,
                                            ordine_default, user_insert)
              SELECT l.id, 'col_k', 'Colonna k', 'k', 'string', 10, '_pgtap' FROM l $$,
           (SELECT schema_tmp FROM _s)),
    '21) una lista su una tabella partizionata e'' accolta, con la sua colonna');

-- La colonna della lista 4 la toglie un DDL: nessun trigger di ui la vede.
ALTER TABLE _rel_ddl DROP COLUMN b;

SELECT is(
    (SELECT array_agg(v.causa || ':' || COALESCE(v.colonna_codice, '-') ORDER BY v.causa)
       FROM dbops.vw_liste_colonne_campo_orfano v
      WHERE v.lista_id = (SELECT lista_id FROM _l WHERE n = 4)),
    ARRAY['CAMPO_ASSENTE:col_b'],
    '22) il presidio vede la colonna tolta con un DDL');

SELECT is_empty(
    format($$ SELECT 1 FROM dbops.vw_liste_colonne_campo_orfano WHERE lista_id = %s $$,
           (SELECT lista_id FROM _l WHERE n = 1)),
    '23) ... e una lista accesa sana non ci compare');

-- ============================================================
-- 24-26) U28: i testi vuoti
-- ============================================================
-- Su una lista spenta il guard della vista non giudica: a rifiutare e' il CHECK.
SELECT throws_ok(
    format($$ UPDATE ui.lista_definizione SET vista_sql = '  ' WHERE id = %s $$,
           (SELECT lista_id FROM _l WHERE n = 6)),
    '23514', NULL,
    '24) una vista_sql vuota e'' rifiutata (chk_lista_definizione_vista_sql_non_vuota)');

-- ============================================================
-- 25-26) U31 (giro 5): il catalogo delle dashboard lo scrive solo il migratore
-- ============================================================
-- ⚠️ Fino al giro 4 i due casi provavano i CHECK dei testi vuoti di widget e
--   dashboard. Dal giro 5 l'applicazione non scrive quelle tabelle (la porta di
--   90_end/20261120-60): i CHECK si provano da owner in
--   ui/test-ui-catalogo-dashboard-v1 (casi 20-21), e qui resta il rifiuto, che
--   si vede solo come applicazione (rosso da owner per costruzione).
SELECT throws_ok(
    $$ INSERT INTO ui.widget (codice, etichetta, tipo_widget, attivo, user_insert)
       VALUES ('_pgtap_widget_app', 'Widget app', 'kpi', TRUE, '_pgtap') $$,
    '42501', NULL,
    '25) come app, l''INSERT di un widget: permesso negato');

SELECT throws_ok(
    $$ INSERT INTO ui.dashboard_definizione (codice, descrizione, attivo, user_insert)
       VALUES ('_pgtap.dash_app', 'Dashboard app', TRUE, '_pgtap') $$,
    '42501', NULL,
    '26) come app, l''INSERT di una dashboard: permesso negato');

-- ============================================================
-- 27-28) U29: la veste NULL non allarga
-- ============================================================
-- Un operatore umano costruito qui ha la veste OPERATORE; gli si aggiunge una
--   veste CLIENTE_PORTALE, e un profilo AD_HOC legato a quell'identita' concede
--   TUTTO su una colonna sensibile. Sotto OPERATORE nessun grant: la sensibile e'
--   BLOCCATO. ⚠️ Non l'utente di contesto: puo' essere un account di processo,
--   e un processo non indossa una veste di persona.
CREATE TEMP TABLE _ctx AS
SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-catalogo-liste', false);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('catalogo liste');

CREATE TEMP TABLE _idp AS
SELECT anagrafiche.fn_crea_veste_portale(c.auth_user_id, m.cliente_soggetto_ruolo_id, 'CLIENTE_PORTALE', TRUE)
       AS identita_id
  FROM _ctx c CROSS JOIN _mondo m;

CREATE TEMP TABLE _pr AS
WITH ins AS (
  INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
  VALUES ('AD_HOC', '_PGTAP_CATALOGO_' || upper(substr(md5(clock_timestamp()::text), 1, 8)),
          'Profilo AD_HOC test catalogo liste', TRUE)
  RETURNING id
)
SELECT id AS profilo_id FROM ins;

DO $lega$
BEGIN
  PERFORM config.fn_lega_profilo_identita((SELECT profilo_id FROM _pr), (SELECT identita_id FROM _idp));
END
$lega$;

INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato, sensibile,
                              ordine_default, user_insert)
SELECT lista_id, 'col_a_sensibile', 'Colonna a', 'a', 'string', TRUE, 20, '_pgtap' FROM _l WHERE n = 1;

INSERT INTO ui.lista_colonna_permesso (colonna_id, profilo_accesso_id, livello_accesso, user_insert)
SELECT lc.id, p.profilo_id, 'TUTTO', '_pgtap'
  FROM ui.lista_colonna lc CROSS JOIN _pr p
 WHERE lc.lista_id = (SELECT lista_id FROM _l WHERE n = 1) AND lc.codice = 'col_a_sensibile';

SELECT is(
    (SELECT lv.livello_accesso::text
       FROM ui.fn_lista_colonne_livello((SELECT lista_id FROM _l WHERE n = 1),
                                        (SELECT auth_user_id FROM _ctx), NULL) lv
      WHERE lv.codice = 'col_a_sensibile'),
    'BLOCCATO',
    '27) con la veste NULL la sensibile concessa da un''altra veste resta BLOCCATO');

SELECT is(
    (SELECT lv.livello_accesso::text
       FROM ui.fn_lista_colonne_livello((SELECT lista_id FROM _l WHERE n = 1),
                                        (SELECT auth_user_id FROM _ctx),
                                        'CLIENTE_PORTALE'::config.ruolo_applicativo) lv
      WHERE lv.codice = 'col_a_sensibile'),
    'TUTTO',
    '28) ... e sotto la veste del profilo e'' TUTTO');

-- ============================================================
-- 29-34) Aggiunti dal /verifica-db del 2026-11-22, numerati in coda
-- ============================================================
-- Q48 (a): il presidio e' l'unica verifica del nome di una colonna LINEAGE e
-- della relazione che sparisce. CAMPO_ASSENTE e' il caso 22; LINEAGE_NON_DICHIARATA
-- non si costruisce come applicazione (il guard la rifiuta, caso 6).
-- La relazione della lista 4 la toglie un DDL: il presidio vede la lista.
DROP TABLE _rel_ddl;

SELECT is(
    (SELECT array_agg(v.causa || ':' || COALESCE(v.colonna_codice, '-') ORDER BY v.causa)
       FROM dbops.vw_liste_colonne_campo_orfano v
      WHERE v.lista_id = (SELECT lista_id FROM _l WHERE n = 4)),
    ARRAY['RELAZIONE_ASSENTE:-'],
    '29) il presidio vede la relazione tolta con un DDL (RELAZIONE_ASSENTE), e non le sue colonne');

-- Il guard non legge piu' la sintesi della lineage (Q48): il nome inventato
-- entra, e lo vede solo il presidio. Senza lista che dichiara, nessuna riga.
INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, origine_campo,
                              tipo_dato, filtrabile, ordinabile, ordine_default, user_insert)
SELECT lista_id, '_pgtap_lineage_inventata', 'Transito', '_pgtap_campo_inventato', 'LINEAGE',
       'string', false, false, 10, '_pgtap' FROM _ll;

SELECT CASE WHEN EXISTS (SELECT 1 FROM _ll)
    THEN is(
        (SELECT array_agg(v.causa ORDER BY v.causa)
           FROM ui.lista_colonna lc
           JOIN dbops.vw_liste_colonne_campo_orfano v ON v.colonna_id = lc.id
          WHERE lc.lista_id = (SELECT lista_id FROM _ll) AND lc.codice = '_pgtap_lineage_inventata'),
        ARRAY['LINEAGE_SCONOSCIUTA'],
        '30) una colonna LINEAGE su un nome che la sintesi non ha: il presidio la vede (LINEAGE_SCONOSCIUTA)')
    ELSE skip('30) nessuna lista dichiara legge_lineage (il CSV del seed non e'' caricato)', 1)
END;

-- U28: un caso per CHECK dei testi di ui.lista_definizione (vista_sql e' il 24).
SELECT is(dbops.fn_pgtap_codice_errore(format(
        $$ INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
           VALUES (' ', 'Lista test pgTAP', %L, NULL, FALSE, '_pgtap') $$, (SELECT schema_tmp FROM _s))),
    'chk_lista_definizione_codice_non_vuoto',
    '31) un codice di lista vuoto e'' rifiutato dal CHECK');
SELECT is(dbops.fn_pgtap_codice_errore(format(
        $$ INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
           VALUES ('_pgtap.catalogo_descr_vuota', ' ', %L, NULL, FALSE, '_pgtap') $$, (SELECT schema_tmp FROM _s))),
    'chk_lista_definizione_descrizione_non_vuota',
    '32) una descrizione di lista vuota e'' rifiutata dal CHECK');
SELECT is(dbops.fn_pgtap_codice_errore(
        $$ INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
           VALUES ('_pgtap.catalogo_schema_vuoto', 'Lista test pgTAP', ' ', NULL, FALSE, '_pgtap') $$),
    'chk_lista_definizione_schema_dati_non_vuoto',
    '33) uno schema_dati vuoto e'' rifiutato dal CHECK');
SELECT is(dbops.fn_pgtap_codice_errore(format(
        $$ UPDATE ui.lista_definizione SET note = ' ' WHERE id = %s $$, (SELECT lista_id FROM _l WHERE n = 6))),
    'chk_lista_definizione_note_non_vuote',
    '34) una nota di lista vuota e'' rifiutata dal CHECK (NULL resta ammesso)');

SELECT * FROM finish();
ROLLBACK;
