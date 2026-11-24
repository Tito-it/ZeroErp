-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: ui.lista_colonna.vuoto_ordinato_come_massimo — dove va il vuoto quando
--   una lista ordina per una colonna.
-- Riferimento: brief-db-lista-colonna-vuoto-in-ordine (§2, §7, §8.3; D-1 … D-3 e
--   D-5 di Tid, 2026-11-24); changeSet 00_schema/ui/20261123-65 (colonna e CHECK),
--   00_schema/pratiche/20261123-66 (i due COMMENT), il CSV di ui.lista_colonna coi
--   suoi due caricatori e la riga 4 di dbops.automazione_seed_primo_impianto
--   (80_data).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la colonna e' boolean NOT NULL, default false: una colonna che non dice
--     niente ordina il vuoto come il minimo;
--   - la dichiarazione chiede un campo sorgente, e non dipende da `ordinabile`
--     (D-3): una colonna non ordinabile la tiene;
--   - il seed dichiara le colonne il cui vuoto vuol dire «senza fine» (§3.1 del
--     brief, e la 304 per D-2) e le due giorni_alla_scadenza dei listini (D-5:
--     il vuoto, «non in scadenza», sta oltre ogni valore), cercate per lista e
--     codice, non per id;
--   - ⭐ la convenzione di valido_al (D-2): ogni colonna accesa su valido_al e'
--     dichiarata, perche' valido_al NULL vuol dire «aperto» in tutto il database
--     (linee guida SQL §7b). Il test legge la tabella, non il CSV: vede anche una
--     colonna creata dall'installazione;
--   - su una riga di seed la dichiarazione e' una colonna del software (D-1):
--     l'installazione non la cambia;
--   - i COMMENT della scadenza di pratica e flusso dicono il vuoto.
--
-- Gira come l'applicazione (runner di default): il caso 9 e' la scrittura
--   dell'installazione, che si riconosce da session_user.
-- ⚠️ Il caso 9: ROSSO DA OWNER, VERDE COME APP. Da proprietario la sessione e'
--   quella del migratore, cioe' il software, che la colonna la scrive (come i
--   casi di perimetro di test-seed-primo-impianto-ui-installazione-v1). Ed e'
--   verde solo dopo il ci_apply, che rimonta il trigger del seed con l'elenco
--   nuovo del registro. Il caso 8 legge il registro, ed e' verde gia' dopo il
--   migrate.
--
-- Elenco test (plan 11):
--    1) la colonna: boolean, NOT NULL, default false
--    2) il vincolo chk_ui_lista_colonna_vuoto_massimo_con_campo esiste
--    3) una colonna senza campo sorgente non dichiara: rifiutata dal vincolo
--    4) una colonna con il campo, NON ordinabile, dichiara: entra (D-3)
--    5) una colonna che non dice niente nasce false
--    6) il seed: le sedici colonne dichiarate, per lista e codice
--    7) ⭐ la convenzione di valido_al: nessuna colonna accesa su valido_al senza
--       la dichiarazione
--    8) il registro del primo impianto: la colonna e' del software
--    9) l'app cambia la dichiarazione di una colonna di seed:
--       E_SEED_COLONNA_DEL_SOFTWARE (D-1)
--   10) il COMMENT di pratiche.pratiche.data_scadenza dice il vuoto
--   11) … e quello di pratiche.flussi.data_scadenza
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- Una riga di prova dell'installazione, su una lista senza vista (il guard del
-- campo sorgente salta): campo sorgente, ordinabile e dichiarazione indicati.
-- Senza campo la colonna non si esporta (chk_ui_lista_colonna_senza_campo_non_esportabile).
-- p_dichiara NULL = la colonna non la nomina, e prende il default.
CREATE OR REPLACE FUNCTION pg_temp.riga(p_id integer, p_campo text, p_ordinabile boolean,
                                        p_dichiara boolean)
RETURNS text LANGUAGE sql AS $f$
  SELECT format(
    'INSERT INTO ui.lista_colonna (id, lista_id, codice, etichetta, campo_sorgente, tipo_colonna, '
    '  tipo_dato, esportabile, ordinabile, ordine_default, user_insert%1$s) '
    'SELECT %2$s, min(ld.id), %3$L, %4$L, %5$L, ''informazione'', ''date'', %6$L, %7$L, 9990, ''pgtap''%8$s '
    '  FROM ui.lista_definizione ld WHERE ld.vista_sql IS NULL',
    CASE WHEN p_dichiara IS NULL THEN '' ELSE ', vuoto_ordinato_come_massimo' END,
    p_id, 'zz_vuoto_' || p_id, 'Prova vuoto in ordine', p_campo,
    (p_campo IS NOT NULL)::text, p_ordinabile::text,
    CASE WHEN p_dichiara IS NULL THEN '' ELSE format(', %L', p_dichiara::text) END);
$f$;

-- ============================================================
-- 1-2 La colonna e il vincolo
-- ============================================================
SELECT is(
  (SELECT format_type(a.atttypid, a.atttypmod) || ' ' || a.attnotnull::text || ' '
          || pg_get_expr(d.adbin, d.adrelid)
     FROM pg_catalog.pg_attribute a
     LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
    WHERE a.attrelid = 'ui.lista_colonna'::regclass
      AND a.attname = 'vuoto_ordinato_come_massimo'
      AND NOT a.attisdropped),
  'boolean true false',
  '1) la colonna: boolean, NOT NULL, default false');

SELECT is(
  (SELECT count(*)::int FROM pg_catalog.pg_constraint
    WHERE conrelid = 'ui.lista_colonna'::regclass
      AND contype = 'c'
      AND conname = 'chk_ui_lista_colonna_vuoto_massimo_con_campo'),
  1,
  '2) il vincolo chk_ui_lista_colonna_vuoto_massimo_con_campo esiste');

-- ============================================================
-- 3-5 Le righe costruite
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990101, NULL, false, true)),
          'chk_ui_lista_colonna_vuoto_massimo_con_campo',
          '3) una colonna senza campo sorgente non dichiara: rifiutata dal vincolo');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riga(990102, 'zz_fine', false, true)),
          NULL,
          '4) una colonna con il campo, non ordinabile, dichiara: entra (la dichiarazione non dipende da ordinabile)');

-- ⚠️ La scrittura in un'istruzione e la rilettura nella successiva: nella stessa
--   istruzione lo snapshot non vedrebbe la riga appena scritta.
CREATE TEMP TABLE tmp_esito_5 ON COMMIT DROP AS
  SELECT dbops.fn_pgtap_codice_errore(pg_temp.riga(990103, 'zz_data', true, NULL)) AS esito;

SELECT is(
  (SELECT e.esito IS NULL
          AND (SELECT NOT lc.vuoto_ordinato_come_massimo FROM ui.lista_colonna lc WHERE lc.id = 990103)
     FROM tmp_esito_5 e),
  true,
  '5) una colonna che non dice niente nasce false: il vuoto conta come il minimo');

-- ============================================================
-- 6-7 Il seed e la convenzione di valido_al
-- ============================================================
-- Le colonne dichiarate (brief §3.1, la 304 per D-2, giorni_alla_scadenza per
-- D-5): si contano quelle che mancano o non sono dichiarate.
SELECT is(
  (SELECT count(*)::int
     FROM (VALUES
             ('vendite.contratti',                     'valido_al'),
             ('vendite.preventivi',                    'validita_al'),
             ('vendite.offerte',                       'validita_al'),
             ('vendite.listini_versioni',              'valido_al'),
             ('vendite.listini_versioni',              'giorni_alla_scadenza'),
             ('vendite.listini',                       'giorni_alla_scadenza'),
             ('vendite.promo_articoli',                'valido_al'),
             ('catalogo.articolo_componenti',          'valido_al'),
             ('catalogo.conversioni_uom',              'valido_al'),
             ('anagrafiche.categorie_clienti_listini', 'valido_al'),
             ('anagrafiche.operatori',                 'valido_al'),
             ('config.tipi_ruolo_tipi_indirizzo',      'valido_al'),
             ('documenti.template_versioni',           'valido_al'),
             ('magazzino.lotti',                       'data_scadenza'),
             ('pratiche.flussi',                       'data_scadenza'),
             ('pratiche.pratiche',                     'data_scadenza')) AS v(lista, colonna)
     LEFT JOIN ui.lista_definizione ld ON ld.codice = v.lista
     LEFT JOIN ui.lista_colonna lc ON lc.lista_id = ld.id AND lc.codice = v.colonna
    WHERE lc.id IS NULL OR NOT lc.vuoto_ordinato_come_massimo),
  0,
  '6) il seed: le sedici colonne il cui vuoto sta oltre ogni valore sono dichiarate');

SELECT is(
  (SELECT count(*)::int FROM ui.lista_colonna lc
    WHERE lc.attivo
      AND lc.campo_sorgente = 'valido_al'
      AND NOT lc.vuoto_ordinato_come_massimo),
  0,
  '7) la convenzione di valido_al: ogni colonna accesa su valido_al dichiara il vuoto come il massimo');

-- ============================================================
-- 8-9 Una colonna del software (D-1)
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM dbops.automazione_seed_primo_impianto r
    WHERE r.schema_name = 'ui' AND r.table_name = 'lista_colonna'
      AND 'vuoto_ordinato_come_massimo' = ANY (r.colonne_software)),
  1,
  '8) il registro del primo impianto: la dichiarazione e'' una colonna del software di ui.lista_colonna');

SELECT is(
  dbops.fn_pgtap_codice_errore($$
    UPDATE ui.lista_colonna lc SET vuoto_ordinato_come_massimo = false
      FROM ui.lista_definizione ld
     WHERE ld.id = lc.lista_id AND ld.codice = 'vendite.contratti' AND lc.codice = 'valido_al'$$),
  'E_SEED_COLONNA_DEL_SOFTWARE',
  '9) l''app cambia la dichiarazione di una colonna di seed: E_SEED_COLONNA_DEL_SOFTWARE');

-- ============================================================
-- 10-11 I COMMENT della scadenza
-- ============================================================
SELECT ok(
  col_description('pratiche.pratiche'::regclass,
                  (SELECT attnum FROM pg_catalog.pg_attribute
                    WHERE attrelid = 'pratiche.pratiche'::regclass AND attname = 'data_scadenza'))
    LIKE '%NULL = nessuna scadenza%',
  '10) il COMMENT di pratiche.pratiche.data_scadenza dice il vuoto');

SELECT ok(
  col_description('pratiche.flussi'::regclass,
                  (SELECT attnum FROM pg_catalog.pg_attribute
                    WHERE attrelid = 'pratiche.flussi'::regclass AND attname = 'data_scadenza'))
    LIKE '%NULL = nessuna scadenza%',
  '11) … e quello di pratiche.flussi.data_scadenza');

SELECT * FROM finish();
ROLLBACK;
