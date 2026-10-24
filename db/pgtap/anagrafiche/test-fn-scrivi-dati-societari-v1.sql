-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-differiti: escluso — gli enti costruiti con fn_crea_soggetto_pg restano
--   SENZA indirizzi: il soggetto del test sono il verbo dei dati societari e i
--   guard BEFORE ROW della forma, non la saga di completezza, che ha i suoi
--   test. Il guard differito della forma al cambio di natura si fa scattare per
--   NOME (SET CONSTRAINTS anagrafiche.trg_soggetti_def_guard_forma_giuridica_natura_upd
--   IMMEDIATE), gli altri restano differiti fino al ROLLBACK.
-- pgTAP test per Zero ERP
--
-- I dati societari: il verbo di scrittura, la porta, la forma giuridica.
--   Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parti B e C)
--   changeSet 20261010-95 (REA e capitale nullable, coppia REA), -96 (forma
--   ammessa), -97 (guard della forma), -98 (guard al COMMIT sul cambio di
--   natura), -99 (verbo), 20261011-01 (fn_crea_soggetto_pg dal verbo), -02
--   (fixture dal verbo), -03 (forma NOT NULL), -04 (porta).
--
-- Elenco test (plan 23):
--   struttura e porta
--    1) il verbo e' SECURITY DEFINER, con pg_temp in coda al search_path
--    2) EXECUTE: a zeroerp_app si', a PUBLIC no
--    3) a zeroerp_app SELECT si', INSERT/UPDATE/DELETE no (has_table_privilege)
--    4) REA e capitale nullable, forma NOT NULL, CHECK sulla coppia REA
--   il verbo
--    5) crea i dati societari di un ente (forma associazione, senza capitale): B-6
--    6) li aggiorna: una riga sola, i valori nuovi (stato intero)
--    7) socio unico NULL -> il default dei parametri, non NULL
--    8) soggetto inesistente -> E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO
--    8-bis) soggetto NULL -> E_PARAMETRO_INVALIDO, non «non trovato» (20261012-02:
--       un chiamante rotto non e' un 404)
--   la forma (guard 20261010-97)
--    9) un ente con la forma SRL -> E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO
--   10) ... col campo 'forma_giuridica_id'
--   11) capitale su un'associazione (NONE) -> E_CAPITALE_SOCIALE_NON_AMMESSO
--   12) SRL senza capitale (REQUIRED) -> E_CAPITALE_SOCIALE_OBBLIGATORIO
--   13) SRL senza REA (REQUIRED) -> E_REA_OBBLIGATORIO
--   14) provincia REA senza numero -> CHECK chk_dati_societari_rea_coppia (23514)
--   15) forma NULL -> NOT NULL (23502)
--   cambio di natura (guard al COMMIT 20261010-98)
--   16) SC -> ENC senza cambiare la forma SRL -> E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA al COMMIT
--   17) SC -> ENC e poi forma associazione, nella stessa transazione -> passa
--   18) l'ordine inverso (prima la forma, natura ancora SC) -> rifiuto immediato della forma
--   fn_crea_soggetto_pg (B-4, B-6, B-7)
--   19) una SRL con REA e capitale e senza canale FE -> nasce (il canale non e' piu' obbligatorio)
--   20) ... e i suoi dati societari portano la forma
--   21) un ente con forma associazione e senza capitale -> nasce (prima falliva sempre)
--   la porta, come app (per ultimo)
--   22) UPDATE diretto di anagrafiche.dati_societari -> 42501
--       ⚠️ rosso da owner per costruzione (l'owner scrive sempre), verde come app
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL DEFERRED;

SELECT plan(23);

CREATE OR REPLACE FUNCTION pg_temp.colonna_del_rifiuto(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_col text;
BEGIN
    EXECUTE p_sql;
    RETURN '(nessun rifiuto)';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_col = COLUMN_NAME;
    RETURN v_col;
END $f$;

CREATE TEMP TABLE _ref AS
SELECT (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'ENC') AS enc,
       (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'SC')  AS sc,
       (SELECT id FROM config.forme_giuridiche WHERE codice = 'SRL')   AS srl,
       (SELECT id FROM config.forme_giuridiche WHERE codice = 'ASSOC') AS assoc,
       (SELECT p.id FROM config.province p ORDER BY p.id LIMIT 1)      AS prov;

-- Il verbo, coi parametri nominati: chi chiama scrive lo stato intero.
CREATE OR REPLACE FUNCTION pg_temp.ds_sql(p_soggetto uuid, p_forma bigint, p_rea text,
                                          p_capitale numeric, p_socio text DEFAULT 'SM')
RETURNS text LANGUAGE sql AS $f$
    SELECT format(
        'SELECT anagrafiche.fn_scrivi_dati_societari(
             p_soggetto_id := %L, p_forma_giuridica_id := %s,
             p_id_prov_iscri_rea := %s, p_iscrizione_rea := %L,
             p_capitale_sociale := %s, p_socio_unico := %L, p_liquidazione := ''LN'',
             p_destinatario_fe := NULL, p_pec_fatturazione := NULL, p_codice_sdi := NULL,
             p_data_costituzione := NULL)',
        p_soggetto, COALESCE(p_forma::text, 'NULL'),
        CASE WHEN p_rea IS NULL THEN 'NULL' ELSE (SELECT prov FROM _ref)::text END, p_rea,
        COALESCE(p_capitale::text, 'NULL'), p_socio);
$f$;

-- ============================================================
-- Struttura e porta
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_catalog.pg_proc p
              JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'anagrafiche' AND p.proname = 'fn_scrivi_dati_societari'
               AND p.prosecdef
               AND array_to_string(p.proconfig, ',') LIKE '%search_path=pg_catalog, public, pg_temp%'),
    '1. il verbo e'' SECURITY DEFINER, con pg_temp in coda al search_path');

SELECT is(
    (SELECT has_function_privilege('zeroerp_app', p.oid, 'EXECUTE')::text || '/'
            || has_function_privilege('public', p.oid, 'EXECUTE')::text
       FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'anagrafiche' AND p.proname = 'fn_scrivi_dati_societari'),
    'true/false',
    '2. EXECUTE sul verbo: all''app si'', a PUBLIC no');

SELECT is(
    has_table_privilege('zeroerp_app', 'anagrafiche.dati_societari', 'SELECT')::text || '/'
    || has_table_privilege('zeroerp_app', 'anagrafiche.dati_societari', 'INSERT')::text || '/'
    || has_table_privilege('zeroerp_app', 'anagrafiche.dati_societari', 'UPDATE')::text || '/'
    || has_table_privilege('zeroerp_app', 'anagrafiche.dati_societari', 'DELETE')::text,
    'true/false/false/false',
    '3. la porta: l''app legge i dati societari, non li scrive (B-5)');

SELECT is(
    (SELECT string_agg(a.attname || '=' || a.attnotnull::text, ',' ORDER BY a.attname)
       FROM pg_catalog.pg_attribute a
      WHERE a.attrelid = 'anagrafiche.dati_societari'::regclass
        AND a.attname IN ('capitale_sociale', 'forma_giuridica_id', 'id_prov_iscri_rea', 'iscrizione_rea'))
    || '|' || (SELECT count(*)::text FROM pg_catalog.pg_constraint c
                WHERE c.conrelid = 'anagrafiche.dati_societari'::regclass
                  AND c.conname = 'chk_dati_societari_rea_coppia'),
    'capitale_sociale=false,forma_giuridica_id=true,id_prov_iscri_rea=false,iscrizione_rea=false|1',
    '4. REA e capitale li dice la forma (nullable), la forma c''e'' sempre (NOT NULL), la coppia REA ha il suo CHECK');

-- ============================================================
-- Il verbo. Le societa' dal builder per prime: esce IMMEDIATE.
-- ============================================================
CREATE TEMP TABLE _sc AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Verbo DS pgTAP srl', p_piva := dbops.fn_pgtap_piva_libera(11)) AS id;
CREATE TEMP TABLE _sc2 AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Verbo DS pgTAP srl due', p_piva := dbops.fn_pgtap_piva_libera(12)) AS id;
SET CONSTRAINTS ALL DEFERRED;

-- Un ente SENZA dati societari: policy OPTIONAL, fn_crea_soggetto_pg non li crea.
CREATE TEMP TABLE _enc AS
SELECT anagrafiche.fn_crea_soggetto_pg(
           p_ragione_sociale := 'Verbo DS pgTAP associazione',
           p_tipo_soggetto_dettaglio_id := (SELECT enc FROM _ref),
           p_email := 'pgtap.verbo.ds.enc@example.com',
           p_partita_iva := v.piva, p_codice_fiscale := v.piva) AS id
  FROM (SELECT dbops.fn_pgtap_piva_libera(13) AS piva) v;

SELECT lives_ok(
    pg_temp.ds_sql((SELECT id FROM _enc), (SELECT assoc FROM _ref), NULL, NULL),
    '5. il verbo crea i dati societari di un ente: associazione, senza REA ne'' capitale (B-6)');

DO $agg$ BEGIN
    PERFORM anagrafiche.fn_scrivi_dati_societari(
        p_soggetto_id := (SELECT id FROM _enc), p_forma_giuridica_id := (SELECT assoc FROM _ref),
        p_id_prov_iscri_rea := NULL, p_iscrizione_rea := NULL, p_capitale_sociale := NULL,
        p_socio_unico := 'SM', p_liquidazione := 'LN',
        p_destinatario_fe := 'P', p_pec_fatturazione := '  ente.pgtap@pec.example.com  ',
        p_codice_sdi := NULL, p_data_costituzione := NULL);
END $agg$;

SELECT is(
    (SELECT count(*)::text || '|' || max(ds.destinatario_fe) || '|' || max(ds.pec_fatturazione)
       FROM anagrafiche.dati_societari ds WHERE ds.soggetto_id = (SELECT id FROM _enc)),
    '1|P|ente.pgtap@pec.example.com',
    '6. il verbo li aggiorna: una riga sola, il canale nuovo, la PEC ripulita');

DO $agg$ BEGIN
    EXECUTE pg_temp.ds_sql((SELECT id FROM _enc), (SELECT assoc FROM _ref), NULL, NULL, NULL);
END $agg$;

SELECT isnt(
    (SELECT ds.socio_unico::text FROM anagrafiche.dati_societari ds WHERE ds.soggetto_id = (SELECT id FROM _enc)),
    NULL,
    '7. socio unico NULL nello stato intero -> il default dei parametri (la colonna e'' NOT NULL)');

SELECT throws_like(
    pg_temp.ds_sql('00000000-0000-0000-0000-000000000000'::uuid, (SELECT srl FROM _ref), 'X', 1),
    '%non trovato%',
    '8. soggetto inesistente -> E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO');

SELECT throws_like(
    pg_temp.ds_sql(NULL::uuid, (SELECT srl FROM _ref), 'X', 1),
    'Parametro non valido%',
    '8-bis. soggetto NULL -> E_PARAMETRO_INVALIDO, non E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO');

-- ============================================================
-- La forma (guard 20261010-97)
-- ============================================================
SELECT throws_like(
    pg_temp.ds_sql((SELECT id FROM _enc), (SELECT srl FROM _ref), NULL, NULL),
    '%non e'' ammessa per il tipo soggetto%',
    '9. un ente con la forma SRL -> E_FORMA_GIURIDICA_NON_AMMESSA_PER_TIPO_SOGGETTO (C-1)');

SELECT is(
    pg_temp.colonna_del_rifiuto(pg_temp.ds_sql((SELECT id FROM _enc), (SELECT srl FROM _ref), NULL, NULL)),
    'forma_giuridica_id',
    '10. il rifiuto porta il campo ''forma_giuridica_id''');

SELECT throws_like(
    pg_temp.ds_sql((SELECT id FROM _enc), (SELECT assoc FROM _ref), NULL, 5000),
    '%il capitale sociale non si indica%',
    '11. capitale su un''associazione (policy NONE) -> E_CAPITALE_SOCIALE_NON_AMMESSO');

SELECT throws_like(
    pg_temp.ds_sql((SELECT id FROM _sc), (SELECT srl FROM _ref), 'REA-PGTAP-V12', NULL),
    '%il capitale sociale e'' obbligatorio%',
    '12. una SRL senza capitale (policy REQUIRED) -> E_CAPITALE_SOCIALE_OBBLIGATORIO');

SELECT throws_like(
    pg_temp.ds_sql((SELECT id FROM _sc), (SELECT srl FROM _ref), NULL, 10000),
    '%al REA e'' obbligatoria%',
    '13. una SRL senza REA (policy REQUIRED) -> E_REA_OBBLIGATORIO');

-- ⚠️ Su un'associazione (REA facoltativo) e non su una SRL: li' il guard della
--   forma (BEFORE ROW, REA obbligatorio) parlerebbe prima del CHECK di riga.
SELECT throws_ok(
    format($$SELECT anagrafiche.fn_scrivi_dati_societari(
               p_soggetto_id := %L, p_forma_giuridica_id := %s,
               p_id_prov_iscri_rea := %s, p_iscrizione_rea := NULL, p_capitale_sociale := NULL,
               p_socio_unico := 'SM', p_liquidazione := 'LN', p_destinatario_fe := NULL,
               p_pec_fatturazione := NULL, p_codice_sdi := NULL, p_data_costituzione := NULL)$$,
           (SELECT id FROM _enc), (SELECT assoc FROM _ref), (SELECT prov FROM _ref)),
    '23514', NULL,
    '14. la provincia REA senza il numero -> CHECK chk_dati_societari_rea_coppia');

SELECT throws_ok(
    pg_temp.ds_sql((SELECT id FROM _sc), NULL, 'REA-PGTAP-V15', 10000),
    '23502', NULL,
    '15. dati societari senza forma -> NOT NULL (C-2)');

-- ============================================================
-- Cambio di natura: il guard al COMMIT (20261010-98)
-- ============================================================
SELECT throws_like(
    format($$UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = %s WHERE id = %L;
             SET CONSTRAINTS anagrafiche.trg_soggetti_def_guard_forma_giuridica_natura_upd IMMEDIATE$$,
           (SELECT enc FROM _ref), (SELECT id FROM _sc)),
    '%non ammette la forma giuridica%',
    '16. una SRL che diventa ente senza cambiare forma -> E_TIPO_SOGGETTO_FORMA_GIURIDICA_NON_AMMESSA al COMMIT');
SET CONSTRAINTS ALL DEFERRED;

SELECT lives_ok(
    format($$UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = %s WHERE id = %L;
             %s;
             SET CONSTRAINTS anagrafiche.trg_soggetti_def_guard_forma_giuridica_natura_upd IMMEDIATE$$,
           (SELECT enc FROM _ref), (SELECT id FROM _sc),
           pg_temp.ds_sql((SELECT id FROM _sc), (SELECT assoc FROM _ref), 'REA-PGTAP-V17', NULL)),
    '17. prima la natura, poi la forma (associazione), nella stessa transazione -> passa al COMMIT');
SET CONSTRAINTS ALL DEFERRED;

SELECT throws_like(
    pg_temp.ds_sql((SELECT id FROM _sc2), (SELECT assoc FROM _ref), 'REA-PGTAP-V18', NULL),
    '%non e'' ammessa per il tipo soggetto%',
    '18. l''ordine inverso: la forma dell''ente mentre la natura e'' ancora SC -> rifiuto immediato');

-- ============================================================
-- fn_crea_soggetto_pg (B-4, B-6, B-7)
-- ============================================================
CREATE TEMP TABLE _crea_srl (id uuid);
SELECT lives_ok(
    format($$INSERT INTO _crea_srl
             SELECT anagrafiche.fn_crea_soggetto_pg(
                 p_ragione_sociale := 'Crea DS pgTAP srl',
                 p_tipo_soggetto_dettaglio_id := %s,
                 p_email := 'pgtap.crea.ds.srl@example.com',
                 p_partita_iva := %L, p_codice_fiscale := %L,
                 p_forma_giuridica_id := %s, p_id_prov_iscri_rea := %s,
                 p_iscrizione_rea := 'REA-PGTAP-C19', p_capitale_sociale := 10000)$$,
           (SELECT sc FROM _ref), v.piva, v.piva, (SELECT srl FROM _ref), (SELECT prov FROM _ref)),
    '19. una SRL con REA e capitale e SENZA canale FE nasce: il canale non e'' piu'' obbligatorio (B-7)')
  FROM (SELECT dbops.fn_pgtap_piva_libera(14) AS piva) v;

SELECT is(
    (SELECT ds.forma_giuridica_id FROM anagrafiche.dati_societari ds
      WHERE ds.soggetto_id = (SELECT id FROM _crea_srl)),
    (SELECT srl FROM _ref),
    '20. ... e i suoi dati societari, scritti dal verbo, portano la forma');

SELECT lives_ok(
    format($$SELECT anagrafiche.fn_crea_soggetto_pg(
                 p_ragione_sociale := 'Crea DS pgTAP associazione',
                 p_tipo_soggetto_dettaglio_id := %s,
                 p_email := 'pgtap.crea.ds.assoc@example.com',
                 p_partita_iva := %L, p_codice_fiscale := %L,
                 p_forma_giuridica_id := %s)$$,
           (SELECT enc FROM _ref), v.piva, v.piva, (SELECT assoc FROM _ref)),
    '21. un ente con forma associazione e senza capitale nasce (B-6: prima la creazione falliva sempre)')
  FROM (SELECT dbops.fn_pgtap_piva_libera(15) AS piva) v;

-- ============================================================
-- La porta, come app. Per ultimo: un 42501 interrompe solo l'istruzione.
-- ============================================================
SELECT throws_ok(
    $$UPDATE anagrafiche.dati_societari SET id = id WHERE false$$,
    '42501', NULL,
    '22. UPDATE diretto dei dati societari -> 42501: scrive solo il verbo (rosso da owner, verde come app)');

SELECT * FROM finish();
ROLLBACK;
