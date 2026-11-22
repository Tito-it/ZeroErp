-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: i casi del modello delle LISTE che nessun altro test costruiva.
--   Il preset d'azienda nella cascata e il preset di base spento; il cambio di
--   base e di snapshot nella stessa scrittura; la lista per codice NULL; la
--   cancellazione di una colonna (i permessi a cascata, il preset che la
--   trattiene); la priorita' negativa; il guard della vista sulle liste spente e
--   sul cambio del solo schema; il livello di colonna dal profilo REPARTO.
--   Brief: brief-db-revisione-ui, giro 6c (§3.6-quater, Q53 (a)).
--
-- ⭐ Gira come APPLICAZIONE (il runner di default): liste, colonne, preset,
--   preferenze, permessi, profili e unita' organizzative li scrive l'app.
-- ⭐ Il mondo si COSTRUISCE: un operatore umano, la sua azienda, una lista con i
--   suoi preset (di sistema e d'azienda), un profilo AD_HOC senza binding, un
--   reparto col suo profilo e il profilo PORTALE della veste OPERATORE. Le misure
--   sono i due default del catalogo. Nessuna riga del seed decide un'asserzione.
-- ⚠️ La veste OPERATORE ammette UN binding (uq_profili_accesso_bindings_ruolo): se
--   il catalogo ne porta gia' uno, il caso 14 usa quello, altrimenti lo costruisce.
--
-- Elenco test (plan 14):
--   La cascata dei preset
--    1) ui.fn_lista_da_codice(NULL): E_UI_LISTA_NON_TROVATA
--    2) ⭐ il preset dell'azienda accesa vince su quello di sistema, nel resolver
--    3) ... ed e' il preset di base per ui.fn_preset_di_base
--    4) ⭐ cambiare base e snapshot nella stessa UPDATE: lo snapshot e' quello della
--       base nuova, non il valore passato
--    5) ⭐ il preset di base spento non e' piu' base: torna quello di sistema
--    6) ... e la preferenza salvata su quella base lo dice (preset_base_cambiato)
--   La colonna
--    7) cancellare una colonna cancella i suoi permessi
--    8) ⭐ una colonna citata da un preset non si cancella (FK senza azione, 23503)
--    9) una priorita' negativa e' rifiutata (chk_ui_lista_colonna_priorita_non_negativa)
--   La vista della lista
--   10) una lista spenta si registra anche con una vista che non c'e'
--   11) ... e riaccenderla e' rifiutato: E_UI_VISTA_SQL_NON_TROVATA
--   12) ⭐ cambiare il solo schema verso uno senza la relazione: E_UI_VISTA_SQL_NON_TROVATA
--   Il livello di colonna
--   13) ⭐ il profilo REPARTO dell'unita' dell'operatore blocca la colonna
--   14) ⭐ REPARTO (TUTTO) contro PORTALE sulla veste (BLOCCATO): vince il reparto
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _m AS
SELECT ui.fn_misura_pagina_default('PAGINA') AS d_pag, ui.fn_misura_pagina_default('COMPATTA') AS d_com;

CREATE TEMP TABLE _u AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-liste-casi', false);

-- L'azienda di chi agisce: accesa, come la vuole il preset d'azienda.
CREATE TEMP TABLE _az AS
SELECT emittente_fiscale_id FROM dbops.fn_pgtap_azienda_di_chi_agisce('liste casi del modello');

CREATE TEMP TABLE _l AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  VALUES ('_pgtap.liste_casi_' || substr(md5(clock_timestamp()::text), 1, 6),
          'Lista test pgTAP casi del modello', 'pgtap', NULL, TRUE, 'pgtap')
  RETURNING id, codice
)
SELECT id AS lista_id, codice AS lista_codice FROM ins;

CREATE TEMP TABLE _c AS
WITH ins AS (
  INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato, ordine_default, user_insert)
  SELECT l.lista_id, v.codice, v.codice, 'campo_' || v.codice, 'string', v.ordine, 'pgtap'
    FROM _l l CROSS JOIN (VALUES ('c_1', 10), ('c_perm', 20), ('c_rep1', 30), ('c_rep2', 40)) v(codice, ordine)
  RETURNING id, codice
)
SELECT id AS colonna_id, codice FROM ins;

-- Il preset di sistema (senza misura) e quello dell'azienda (la misura COMPATTA).
CREATE TEMP TABLE _p AS
WITH ins AS (
  INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, emittente_fiscale_id, pagina_dimensione,
                               attivo, user_insert)
  SELECT l.lista_id, v.codice, 'Preset test casi del modello', v.ambito::ui.ambito_preset,
         CASE WHEN v.ambito = 'emittente_fiscale' THEN (SELECT emittente_fiscale_id FROM _az) END,
         CASE WHEN v.ambito = 'emittente_fiscale' THEN (SELECT d_com FROM _m) END, TRUE, 'pgtap'
    FROM _l l CROSS JOIN (VALUES ('P_SIS', 'sistema'), ('P_AZ', 'emittente_fiscale')) v(codice, ambito)
  RETURNING id, codice
)
SELECT id AS preset_id, codice FROM ins;

INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile, fissata)
SELECT p.preset_id, c.colonna_id, 1, TRUE, FALSE FROM _p p CROSS JOIN _c c WHERE c.codice = 'c_1';

CREATE FUNCTION pg_temp.p(p_codice text) RETURNS integer LANGUAGE sql STABLE
AS $$ SELECT preset_id FROM _p WHERE codice = p_codice $$;
CREATE FUNCTION pg_temp.c(p_codice text) RETURNS integer LANGUAGE sql STABLE
AS $$ SELECT colonna_id FROM _c WHERE codice = p_codice $$;
CREATE FUNCTION pg_temp.cfg() RETURNS jsonb LANGUAGE sql STABLE
AS $$ SELECT ui.fn_resolve_lista_config((SELECT lista_codice FROM _l), (SELECT auth_user_id FROM _u),
                                        (SELECT emittente_fiscale_id FROM _az)) $$;
CREATE FUNCTION pg_temp.base() RETURNS integer LANGUAGE sql STABLE
AS $$ SELECT b.preset_id
        FROM ui.fn_preset_di_base('lista', (SELECT lista_id FROM _l), (SELECT auth_user_id FROM _u),
                                  ui.fn_veste_corrente(), (SELECT emittente_fiscale_id FROM _az)) b $$;

-- ============================================================
-- 1-6) La cascata dei preset
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore($$ SELECT ui.fn_lista_da_codice(NULL) $$),
    'E_UI_LISTA_NON_TROVATA',
    '1) ui.fn_lista_da_codice(NULL): E_UI_LISTA_NON_TROVATA');

SELECT is(format('%s|%s', pg_temp.cfg() ->> 'pagina_dimensione', pg_temp.cfg() -> 'origine' ->> 'pagina_dimensione'),
    (SELECT format('%s|emittente_fiscale', d_com) FROM _m),
    '2) ⭐ il preset dell''azienda accesa vince su quello di sistema, nel resolver');

SELECT is(pg_temp.base(), pg_temp.p('P_AZ'),
    '3) ... ed e'' il preset di base per ui.fn_preset_di_base');

-- La preferenza nasce sulla base d'azienda; poi la base cambia, e chi scrive
--   passa anche uno snapshot suo, che non deve contare.
INSERT INTO ui.lista_preferenza_utente (auth_user_id, lista_id, preset_base_id, configurazione)
SELECT (SELECT auth_user_id FROM _u), l.lista_id, pg_temp.p('P_AZ'),
       jsonb_build_object('pagina_dimensione', (SELECT d_pag FROM _m))
  FROM _l l;

UPDATE ui.lista_preferenza_utente
   SET preset_base_id = pg_temp.p('P_SIS'),
       preset_base_contenuto_aggiornato_il = '{"colonne": "1999-01-01T00:00:00+00:00"}'::jsonb
 WHERE auth_user_id = (SELECT auth_user_id FROM _u) AND lista_id = (SELECT lista_id FROM _l);

SELECT is(
    (SELECT pu.preset_base_contenuto_aggiornato_il FROM ui.lista_preferenza_utente pu
      WHERE pu.auth_user_id = (SELECT auth_user_id FROM _u) AND pu.lista_id = (SELECT lista_id FROM _l)),
    (SELECT lp.contenuto_aggiornato_il FROM ui.lista_preset lp WHERE lp.id = pg_temp.p('P_SIS')),
    '4) ⭐ base e snapshot nella stessa UPDATE: lo snapshot e'' quello della base nuova');

-- Si torna sulla base d'azienda, poi la si spegne.
UPDATE ui.lista_preferenza_utente SET preset_base_id = pg_temp.p('P_AZ')
 WHERE auth_user_id = (SELECT auth_user_id FROM _u) AND lista_id = (SELECT lista_id FROM _l);
UPDATE ui.lista_preset SET attivo = FALSE WHERE id = pg_temp.p('P_AZ');

SELECT is(pg_temp.base(), pg_temp.p('P_SIS'),
    '5) ⭐ il preset di base spento non e'' piu'' base: torna quello di sistema');

SELECT is(pg_temp.cfg() ->> 'preset_base_cambiato', 'true',
    '6) ... e la preferenza salvata su quella base lo dice (preset_base_cambiato)');

-- ============================================================
-- 7-9) La colonna
-- ============================================================
CREATE TEMP TABLE _prof AS
WITH ins AS (
  INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
  VALUES ('AD_HOC', '_PGTAP_LCM_' || upper(substr(md5(clock_timestamp()::text), 1, 8)),
          'Profilo AD_HOC test casi del modello', TRUE)
  RETURNING id
)
SELECT id AS profilo_id FROM ins;

INSERT INTO ui.lista_colonna_permesso (colonna_id, profilo_accesso_id, livello_accesso, user_insert)
SELECT pg_temp.c('c_perm'), profilo_id, 'LETTURA', 'pgtap' FROM _prof;

-- ⚠️ 7-8 cancellano una colonna: come applicazione la colonna e' una riga
--   dell'installazione. Da proprietario nasce riga del seed, che il seed non lascia
--   cancellare (E_SEED_RIGA_NON_CANCELLABILE): i due casi si saltano, dichiarati.
-- Cancella la colonna, poi conta i permessi del profilo: due istruzioni, perche'
--   la cascata si veda (in una sola istruzione si leggerebbe lo snapshot di prima).
CREATE FUNCTION pg_temp.cancella_e_conta_permessi() RETURNS integer LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM ui.lista_colonna WHERE id = pg_temp.c('c_perm');
    RETURN (SELECT count(*)::int FROM ui.lista_colonna_permesso
             WHERE profilo_accesso_id = (SELECT profilo_id FROM _prof));
END $$;

CREATE TEMP TABLE _owner AS
SELECT script.fn_is_proprietario_tabella('ui.lista_colonna'::regclass) AS si;

SELECT CASE WHEN (SELECT si FROM _owner)
            THEN skip('7) da proprietario la colonna e'' una riga del seed, che non si cancella', 1)
            ELSE is(pg_temp.cancella_e_conta_permessi(), 0,
                    '7) cancellare una colonna cancella i suoi permessi') END;

SELECT CASE WHEN (SELECT si FROM _owner)
            THEN skip('8) da proprietario la colonna e'' una riga del seed, che non si cancella', 1)
            ELSE throws_ok(format($$ DELETE FROM ui.lista_colonna WHERE id = %s $$, pg_temp.c('c_1')),
                    '23503', NULL,
                    '8) ⭐ una colonna citata da un preset non si cancella: la FK della composizione e'' senza azione') END;

SELECT throws_ok(format($$ INSERT INTO ui.lista_colonna (lista_id, codice, etichetta, campo_sorgente, tipo_dato,
                                                         ordine_default, priorita, user_insert)
                           VALUES (%s, 'c_neg', 'c_neg', 'campo_neg', 'string', 90, -1, 'pgtap') $$,
                        (SELECT lista_id FROM _l)),
    '23514', NULL,
    '9) una priorita'' negativa e'' rifiutata (chk_ui_lista_colonna_priorita_non_negativa)');

-- ============================================================
-- 10-12) La vista della lista
-- ============================================================
SELECT lives_ok(
    $$ INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
       VALUES ('_pgtap.liste_casi_spenta', 'Lista test spenta', 'pgtap', '_pgtap_non_esiste', FALSE, 'pgtap') $$,
    '10) una lista spenta si registra anche con una vista che non c''e''');

SELECT is(dbops.fn_pgtap_codice_errore(
    $$ UPDATE ui.lista_definizione SET attivo = TRUE WHERE codice = '_pgtap.liste_casi_spenta' $$),
    'E_UI_VISTA_SQL_NON_TROVATA',
    '11) ... e riaccenderla e'' rifiutato: E_UI_VISTA_SQL_NON_TROVATA');

-- La relazione sta nello schema temporaneo; config non ce l'ha.
CREATE TEMP TABLE _rel_schema (campo integer);
INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
SELECT '_pgtap.liste_casi_schema', 'Lista test schema', n.nspname, '_rel_schema', TRUE, 'pgtap'
  FROM pg_catalog.pg_namespace n WHERE n.oid = pg_my_temp_schema();

SELECT is(dbops.fn_pgtap_codice_errore(
    $$ UPDATE ui.lista_definizione SET schema_dati = 'config' WHERE codice = '_pgtap.liste_casi_schema' $$),
    'E_UI_VISTA_SQL_NON_TROVATA',
    '12) ⭐ cambiare il solo schema verso uno senza la relazione: E_UI_VISTA_SQL_NON_TROVATA');

-- ============================================================
-- 13-14) Il livello di colonna dal profilo REPARTO
-- ============================================================
-- Il reparto: un'unita' organizzativa, la risorsa umana dell'operatore in quella
--   unita', e il profilo REPARTO legato all'unita'.
CREATE TEMP TABLE _uo AS
WITH ins AS (
  INSERT INTO config.unita_organizzative (codice, codice_interno, descrizione)
  SELECT '_PGTAP_LCM_UO_' || upper(substr(md5(clock_timestamp()::text), 1, 16)),
         '_PGTAP_LCM_UO_' || upper(substr(md5(clock_timestamp()::text), 1, 16)),
         'pgTAP casi del modello, reparto'
  RETURNING id
)
SELECT id AS uo_id FROM ins;

UPDATE anagrafiche.risorse_umane SET unita_organizzativa_id = (SELECT uo_id FROM _uo)
 WHERE id = (SELECT risorsa_umana_id FROM _u);

CREATE TEMP TABLE _rep AS
WITH ins AS (
  INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
  VALUES ('REPARTO', '_PGTAP_LCM_R_' || upper(substr(md5(clock_timestamp()::text), 1, 8)),
          'Profilo REPARTO test casi del modello', TRUE)
  RETURNING id
)
SELECT id AS profilo_id FROM ins;

INSERT INTO config.profili_accesso_bindings (profilo_accesso_id, unita_organizzativa_id, attivo)
SELECT profilo_id, (SELECT uo_id FROM _uo), TRUE FROM _rep;

-- Il PORTALE della veste OPERATORE: quello del catalogo se c'e', altrimenti uno
--   costruito (un binding per veste).
WITH p AS (
  INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
  SELECT 'PORTALE', '_PGTAP_LCM_P_' || upper(substr(md5(clock_timestamp()::text), 1, 8)),
         'Profilo PORTALE test casi del modello', TRUE
   WHERE NOT EXISTS (SELECT 1 FROM config.profili_accesso_bindings b
                      WHERE b.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo)
  RETURNING id
)
INSERT INTO config.profili_accesso_bindings (profilo_accesso_id, ruolo_applicativo, attivo)
SELECT p.id, 'OPERATORE'::config.ruolo_applicativo, TRUE FROM p;

-- Solo un binding acceso, su un profilo acceso: e' quello che la risoluzione dei
--   profili legge. Il caso 14 dice di averlo trovato.
CREATE TEMP TABLE _portale AS
SELECT b.profilo_accesso_id AS profilo_id
  FROM config.profili_accesso_bindings b
  JOIN config.profili_accesso pa ON pa.id = b.profilo_accesso_id
 WHERE b.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo AND b.attivo AND pa.attivo;

INSERT INTO ui.lista_colonna_permesso (colonna_id, profilo_accesso_id, livello_accesso, user_insert)
SELECT pg_temp.c('c_rep1'), profilo_id, 'BLOCCATO'::config.livello_accesso, 'pgtap' FROM _rep
UNION ALL
SELECT pg_temp.c('c_rep2'), profilo_id, 'TUTTO'::config.livello_accesso, 'pgtap' FROM _rep
UNION ALL
SELECT pg_temp.c('c_rep2'), profilo_id, 'BLOCCATO'::config.livello_accesso, 'pgtap' FROM _portale;

CREATE FUNCTION pg_temp.livello(p_codice text) RETURNS text LANGUAGE sql STABLE
AS $$ SELECT lv.livello_accesso::text
        FROM ui.fn_lista_colonne_livello((SELECT lista_id FROM _l), (SELECT auth_user_id FROM _u),
                                         'OPERATORE'::config.ruolo_applicativo) lv
       WHERE lv.codice = p_codice $$;

SELECT is(pg_temp.livello('c_rep1'), 'BLOCCATO',
    '13) ⭐ il profilo REPARTO dell''unita'' dell''operatore blocca la colonna');

SELECT is(format('%s|%s', (SELECT count(*) FROM _portale), pg_temp.livello('c_rep2')), '1|TUTTO',
    '14) ⭐ REPARTO (TUTTO) contro PORTALE sulla veste (BLOCCATO): vince il reparto, il piu'' specifico');

SELECT * FROM finish();
ROLLBACK;
