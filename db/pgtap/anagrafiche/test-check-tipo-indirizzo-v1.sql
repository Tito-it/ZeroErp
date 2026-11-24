-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il tipo di un indirizzo, sul soggetto e sul ruolo: la check, le singolari
-- che la chiamano, il predicato del ruolo estratto, gli obbligatori delle
-- plurali sulla finestra di validita'.
--   Brief: brief-db-copia-indirizzo-soggetto §4.1, §4.2, §4.6, giro 1
--   (D-1, D-3, D-4 di Tid, 2026-11-15). ChangeSet 20261114-84 … -95; codici
--   e frasi in config/codici_errore.csv e config/messaggi_errore.csv.
--   Rev 2026-11-17 (brief-db-fornitore-privato-indirizzi, 20261116-18, -20): la
--   meta' sul contesto del ruolo prende la natura in coda (qui NULL: la natura
--   non conta), la plurale del ruolo legge il building block degli obbligatori
--   (presidio 4). La natura sul ruolo la prova test-fornitore-privato-indirizzi-v1.
--
-- Elenco test (plan 34):
--   presidi «la regola sta in un posto solo»
--    1) la singolare del soggetto chiama la check e non contiene il predicato
--    2) la singolare del ruolo chiama la check e non contiene il predicato
--    3) il guard del ruolo legge il predicato, non la matrice
--    4) le due plurali leggono gli obbligatori dalle sedi (rev. 2026-11-24)
--   il predicato del ruolo (matrice costruita)
--    5) riga attiva e valida: ammesso
--    6) riga attiva ma scaduta: non ammesso
--    7) tipo assente dalla matrice: non ammesso
--    8) tipo di ruolo NULL: ammesso
--   la check del soggetto sul contesto (matrice della natura costruita)
--    9) tipo ammesso e non presente: nessun motivo
--   10) tipo gia' presente: TIPO_GIA_PRESENTE
--   11) tipo con la riga scaduta: TIPO_NON_AMMESSO_DALLA_NATURA
--   12) presente e scaduto: i due motivi, nell'ordine
--   13) ... coi codici a catalogo, nello stesso ordine
--   14) natura NULL: nessun motivo
--   la singolare del soggetto
--   15) un tipo nuovo: passa
--   16) lo stesso tipo di nuovo: E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE (non piu' il 23505)
--   17) ... e il campo da accendere e' tipo_indirizzo_codice_interno
--   18) un tipo con la riga scaduta: E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO
--   19) la check su un soggetto che non c'e': E_SOGGETTO_NOT_FOUND
--   la plurale del soggetto (D-4)
--   20) un obbligatorio scaduto: la plurale passa
--   21) ... e non ne fa nascere la copia
--   il ruolo
--   22) la check sul contesto: presente e scaduto, i due motivi nell'ordine
--   23) la singolare del ruolo: un tipo nuovo, passa
--   24) lo stesso tipo di nuovo: E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE
--   25) lo stesso tipo su un'istanza: nessun motivo (un'altra chiave)
--   26) un tipo con la riga scaduta: E_TIPO_INDIRIZZO_NON_PERMESSO
--   27) la check su un ruolo che non c'e': E_SOGGETTO_RUOLO_NON_TROVATO
--   28) la plurale del ruolo con un obbligatorio scaduto: passa
--   29) ... e non ne fa nascere la copia
--   le frasi del tipo non ammesso (Q-1)
--   30) i valori del motivo sul soggetto: la natura e il tipo, per descrizione
--   31) la frase del guard del soggetto, da una strada che salta la madre
--   32) i valori del motivo sul ruolo: il tipo di ruolo e il tipo, per descrizione
--   33) la frase del guard del ruolo, da una strada che salta la madre
--   il fallback permissivo
--   34) tipo di ruolo senza nessuna riga di matrice: ammesso
--
-- Scopo:
--  - ogni motivo e ogni ramo si COSTRUISCONO: le righe di matrice che contano
--    (attiva, scaduta, obbligatoria scaduta, assente) le scrive il test, e il
--    soggetto, il ruolo e la sua istanza nascono dai builder (regola zero:
--    niente si appoggia alle righe di oggi). Il seed serve solo come catalogo
--    dei tipi (codici interni FORNITURA, CON, POSTA).
--  - i rifiuti si asseriscono sul CODICE (dbops.fn_pgtap_codice_errore), non
--    sulla frase: e' il contratto col backend.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- La fixture crea il soggetto (padre) e i suoi indirizzi nello stesso
-- builder, che apre e richiude da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(34);

-- ============================================================
-- Fixture
-- ============================================================
-- Una riga di matrice nello stato voluto: si toglie quella che c'e' per la
-- coppia e se ne scrive una nuova. Le due matrici hanno l'id senza default.
CREATE FUNCTION pg_temp.matrice_natura(
    p_natura config.tipi_soggetto_dettaglio_tipi_indirizzo.tipo_soggetto_dettaglio_id%TYPE,
    p_tipo   config.tipi_indirizzi.codice_interno%TYPE,
    p_obbl   config.tipi_soggetto_dettaglio_tipi_indirizzo.obbligatorio%TYPE,
    p_dal    config.tipi_soggetto_dettaglio_tipi_indirizzo.valido_dal%TYPE,
    p_al     config.tipi_soggetto_dettaglio_tipi_indirizzo.valido_al%TYPE)
RETURNS void LANGUAGE plpgsql AS $f$
DECLARE v_tipo config.tipi_indirizzi.id%TYPE :=
            (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = p_tipo);
BEGIN
    DELETE FROM config.tipi_soggetto_dettaglio_tipi_indirizzo
     WHERE tipo_soggetto_dettaglio_id = p_natura AND tipo_indirizzo_id = v_tipo;
    INSERT INTO config.tipi_soggetto_dettaglio_tipi_indirizzo
           (id, tipo_soggetto_dettaglio_id, tipo_indirizzo_id, obbligatorio, attivo, valido_dal, valido_al)
    VALUES ((SELECT COALESCE(max(id), 0) + 1 FROM config.tipi_soggetto_dettaglio_tipi_indirizzo),
            p_natura, v_tipo, p_obbl, true, p_dal, p_al);
END $f$;

CREATE FUNCTION pg_temp.matrice_ruolo(
    p_tipo_ruolo config.tipi_ruolo_tipi_indirizzo.tipo_ruolo_id%TYPE,
    p_tipo       config.tipi_indirizzi.codice_interno%TYPE,
    p_obbl       config.tipi_ruolo_tipi_indirizzo.obbligatorio%TYPE,
    p_dal        config.tipi_ruolo_tipi_indirizzo.valido_dal%TYPE,
    p_al         config.tipi_ruolo_tipi_indirizzo.valido_al%TYPE)
RETURNS void LANGUAGE plpgsql AS $f$
DECLARE v_tipo config.tipi_indirizzi.id%TYPE :=
            (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = p_tipo);
BEGIN
    DELETE FROM config.tipi_ruolo_tipi_indirizzo
     WHERE tipo_ruolo_id = p_tipo_ruolo AND tipo_indirizzo_id = v_tipo;
    INSERT INTO config.tipi_ruolo_tipi_indirizzo
           (id, tipo_ruolo_id, tipo_indirizzo_id, obbligatorio, attivo, valido_dal, valido_al)
    VALUES ((SELECT COALESCE(max(id), 0) + 1 FROM config.tipi_ruolo_tipi_indirizzo),
            p_tipo_ruolo, v_tipo, p_obbl, true, p_dal, p_al);
END $f$;

CREATE FUNCTION pg_temp.tipo(p_codice config.tipi_indirizzi.codice_interno%TYPE)
RETURNS config.tipi_indirizzi.id%TYPE LANGUAGE sql AS
$f$ SELECT id FROM config.tipi_indirizzi WHERE codice_interno = p_codice $f$;

CREATE FUNCTION pg_temp.reasons(p_motivi jsonb) RETURNS text[] LANGUAGE sql AS
$f$ SELECT COALESCE(array_agg(m ->> 'reason' ORDER BY o), '{}')
      FROM jsonb_array_elements(p_motivi) WITH ORDINALITY AS e(m, o) $f$;

CREATE FUNCTION pg_temp.codici(p_motivi jsonb) RETURNS text[] LANGUAGE sql AS
$f$ SELECT COALESCE(array_agg(m ->> 'codice' ORDER BY o), '{}')
      FROM jsonb_array_elements(p_motivi) WITH ORDINALITY AS e(m, o) $f$;

-- Il soggetto (una persona giuridica) e il ruolo con un'istanza, dai builder.
-- ⚠️ Le colonne delle tabelle temporanee hanno il tipo esplicito: %TYPE nel DDL
--   di tabella non si scrive (linee-guida-sql §5g). Ognuna e' il tipo della
--   colonna di cui e' il riflesso.
CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT script.fn_stato_id_da_iso2('IT') AS it_id,
       dbops.fn_pgtap_crea_soggetto_pg('pgTAP check tipo indirizzo', 3,
                                       script.fn_stato_id_da_iso2('IT')) AS soggetto_id;

ALTER TABLE _f ADD COLUMN natura bigint, ADD COLUMN sr_id bigint,
               ADD COLUMN istanza_id bigint,
               -- il tipo di soggetti_ruoli.tipo_ruolo_id, a cui la check e' ancorata
               ADD COLUMN tipo_ruolo integer;
UPDATE _f SET natura = (SELECT s.tipo_soggetto_dettaglio_id
                          FROM anagrafiche.soggetti s WHERE s.id = _f.soggetto_id);
UPDATE _f SET (sr_id, istanza_id) = (
    SELECT c.soggetto_ruolo_id, c.istanza_utility_id
      FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP check tipo indirizzo') c);
UPDATE _f SET tipo_ruolo = (SELECT sr.tipo_ruolo_id
                              FROM anagrafiche.soggetti_ruoli sr WHERE sr.id = _f.sr_id);

-- Un indirizzo libero valido per l'Italia; il tipo si aggiunge caso per caso.
CREATE TEMP TABLE _el ON COMMIT DROP AS
SELECT jsonb_strip_nulls(
           jsonb_build_object('indirizzo_libero', 'Via pgTAP check tipo 1', 'stato_id', _f.it_id)
           || to_jsonb(fm)) AS base
  FROM _f, dbops.fn_pgtap_indirizzo_libero_forma(_f.it_id) fm;

-- Le righe che contano, sulle due matrici: FORNITURA attiva e valida, CON
-- attiva ma scaduta, POSTA attiva e valida (il tipo chiesto alle plurali).
SELECT pg_temp.matrice_natura(natura, 'FORNITURA', false, NULL, NULL),
       pg_temp.matrice_natura(natura, 'CON',       false, DATE '2000-01-01', DATE '2000-12-31'),
       pg_temp.matrice_natura(natura, 'POSTA',     false, NULL, NULL),
       pg_temp.matrice_ruolo(tipo_ruolo, 'FORNITURA', false, NULL, NULL),
       pg_temp.matrice_ruolo(tipo_ruolo, 'CON',       false, DATE '2000-01-01', DATE '2000-12-31'),
       pg_temp.matrice_ruolo(tipo_ruolo, 'POSTA',     false, NULL, NULL)
  FROM _f;

-- ============================================================
-- 1-4) Presidi: la regola sta in un posto solo
-- ============================================================
SELECT ok(
    pg_get_functiondef('anagrafiche.fn_crea_indirizzo_soggetto(uuid, jsonb)'::regprocedure)
        LIKE '%anagrafiche.fn_check_tipo_indirizzo_soggetto(%'
    AND pg_get_functiondef('anagrafiche.fn_crea_indirizzo_soggetto(uuid, jsonb)'::regprocedure)
        NOT LIKE '%fn_tipo_indirizzo_ammesso_per_natura%'
    AND pg_get_functiondef('anagrafiche.fn_crea_indirizzo_soggetto(uuid, jsonb)'::regprocedure)
        NOT LIKE '%tipi_soggetto_dettaglio_tipi_indirizzo%',
    '1) la singolare del soggetto chiama la check e non contiene il predicato');

SELECT ok(
    pg_get_functiondef('anagrafiche.fn_crea_indirizzo_ruolo(bigint, jsonb)'::regprocedure)
        LIKE '%anagrafiche.fn_check_tipo_indirizzo_ruolo(%'
    AND pg_get_functiondef('anagrafiche.fn_crea_indirizzo_ruolo(bigint, jsonb)'::regprocedure)
        NOT LIKE '%fn_tipo_indirizzo_ammesso_per_ruolo%'
    AND pg_get_functiondef('anagrafiche.fn_crea_indirizzo_ruolo(bigint, jsonb)'::regprocedure)
        NOT LIKE '%tipi_ruolo_tipi_indirizzo%',
    '2) la singolare del ruolo chiama la check e non contiene il predicato');

SELECT ok(
    pg_get_functiondef('anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo()'::regprocedure)
        LIKE '%anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo(%'
    AND pg_get_functiondef('anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo()'::regprocedure)
        NOT LIKE '%config.tipi_ruolo_tipi_indirizzo%',
    '3) il guard del ruolo legge il predicato, non la matrice');

-- rev 2026-11-24 (D-T7a-4, brief-db-revisione-anagrafiche §21): le due plurali
--   leggono gli obbligatori dalle sedi, coi ripieghi: la soggetto i mancanti
--   (anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto, che legge
--   fn_tipo_indirizzo_obbligatorio_per_natura e il predicato), la ruolo il
--   requisito (anagrafiche.fn_indirizzi_obbligatori_ruolo, che compone il
--   predicato del ruolo con quello della natura). Prima: il predicato (la
--   soggetto) e fn_tipo_indirizzo_obbligatorio_per_ruolo (la ruolo, 20261116-20).
SELECT ok(
    pg_get_functiondef('anagrafiche.fn_crea_indirizzi_soggetto(uuid, jsonb, boolean)'::regprocedure)
        LIKE '%anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto(%'
    AND pg_get_functiondef('anagrafiche.fn_crea_indirizzi_ruolo(bigint, jsonb)'::regprocedure)
        LIKE '%anagrafiche.fn_indirizzi_obbligatori_ruolo(%',
    '4) le due plurali leggono gli obbligatori dalle sedi');

-- ============================================================
-- 5-8) Il predicato del ruolo
-- ============================================================
SELECT ok(anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo(
              (SELECT tipo_ruolo FROM _f), pg_temp.tipo('FORNITURA'), script.fn_data_operativa()),
          '5) riga attiva e valida: ammesso');

SELECT ok(NOT anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo(
              (SELECT tipo_ruolo FROM _f), pg_temp.tipo('CON'), script.fn_data_operativa()),
          '6) riga attiva ma scaduta: non ammesso');

DELETE FROM config.tipi_ruolo_tipi_indirizzo
 WHERE tipo_ruolo_id = (SELECT tipo_ruolo FROM _f) AND tipo_indirizzo_id = pg_temp.tipo('SEDEOP');
SELECT ok(NOT anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo(
              (SELECT tipo_ruolo FROM _f), pg_temp.tipo('SEDEOP'), script.fn_data_operativa()),
          '7) tipo assente da una matrice che c''e'': non ammesso');

SELECT ok(anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo(
              NULL, pg_temp.tipo('CON'), script.fn_data_operativa()),
          '8) tipo di ruolo NULL: ammesso');

-- ============================================================
-- 9-14) La check del soggetto sul contesto
-- ============================================================
SELECT is(
    pg_temp.reasons(anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(
        (SELECT natura FROM _f), '{}', pg_temp.tipo('FORNITURA'), script.fn_data_operativa(), NULL)),
    '{}'::text[],
    '9) tipo ammesso e non presente: nessun motivo');

SELECT is(
    pg_temp.reasons(anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(
        (SELECT natura FROM _f), ARRAY[pg_temp.tipo('FORNITURA')], pg_temp.tipo('FORNITURA'),
        script.fn_data_operativa(), NULL)),
    ARRAY['TIPO_GIA_PRESENTE'],
    '10) tipo gia'' presente: TIPO_GIA_PRESENTE');

SELECT is(
    pg_temp.reasons(anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(
        (SELECT natura FROM _f), '{}', pg_temp.tipo('CON'), script.fn_data_operativa(), NULL)),
    ARRAY['TIPO_NON_AMMESSO_DALLA_NATURA'],
    '11) tipo con la riga scaduta: TIPO_NON_AMMESSO_DALLA_NATURA');

SELECT is(
    pg_temp.reasons(anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(
        (SELECT natura FROM _f), ARRAY[pg_temp.tipo('CON')], pg_temp.tipo('CON'),
        script.fn_data_operativa(), NULL)),
    ARRAY['TIPO_GIA_PRESENTE', 'TIPO_NON_AMMESSO_DALLA_NATURA'],
    '12) presente e scaduto: i due motivi, nell''ordine');

SELECT is(
    pg_temp.codici(anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(
        (SELECT natura FROM _f), ARRAY[pg_temp.tipo('CON')], pg_temp.tipo('CON'),
        script.fn_data_operativa(), NULL)),
    ARRAY['E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE', 'E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO'],
    '13) ... coi codici a catalogo, nello stesso ordine');

SELECT is(
    pg_temp.reasons(anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(
        NULL, '{}', pg_temp.tipo('CON'), script.fn_data_operativa(), NULL)),
    '{}'::text[],
    '14) natura NULL: nessun motivo');

-- ============================================================
-- 15-19) La singolare del soggetto
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)',
        (SELECT soggetto_id FROM _f),
        (SELECT base FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'FORNITURA'))),
    NULL,
    '15) un tipo nuovo: passa');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)',
        (SELECT soggetto_id FROM _f),
        (SELECT base FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'FORNITURA'))),
    'E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE',
    '16) lo stesso tipo di nuovo: E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE, non il 23505 del vincolo');

CREATE FUNCTION pg_temp.campo_di(p_sql text) RETURNS text LANGUAGE plpgsql AS $f$
DECLARE v_campo text;  -- valore della diagnostica
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_campo = COLUMN_NAME;
    RETURN v_campo;
END $f$;

SELECT is(
    pg_temp.campo_di(format(
        'SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)',
        (SELECT soggetto_id FROM _f),
        (SELECT base FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'FORNITURA'))),
    'tipo_indirizzo_codice_interno',
    '17) ... e il campo da accendere e'' tipo_indirizzo_codice_interno');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)',
        (SELECT soggetto_id FROM _f),
        (SELECT base FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'CON'))),
    'E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO',
    '18) un tipo con la riga scaduta: E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_check_tipo_indirizzo_soggetto(%L::uuid, %s)',
        '00000000-0000-0000-0000-000000000001', pg_temp.tipo('FORNITURA'))),
    'E_SOGGETTO_NOT_FOUND',
    '19) la check su un soggetto che non c''e'': E_SOGGETTO_NOT_FOUND');

-- ============================================================
-- 20-21) La plurale del soggetto: un obbligatorio scaduto non si copia (D-4)
-- ============================================================
SELECT pg_temp.matrice_natura(natura, 'CON', true, DATE '2000-01-01', DATE '2000-12-31') FROM _f;

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzi_soggetto(%L::uuid, %L::jsonb, true)',
        (SELECT soggetto_id FROM _f),
        jsonb_build_array((SELECT base FROM _el)
                          || jsonb_build_object('tipo_indirizzo_codice_interno', 'POSTA')))),
    NULL,
    '20) un obbligatorio scaduto: la plurale passa');

SELECT is(
    (SELECT string_agg(ti.codice_interno, ',' ORDER BY ti.codice_interno)
       FROM anagrafiche.indirizzi_soggetti i
       JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id
      WHERE i.soggetto_id = (SELECT soggetto_id FROM _f)
        AND ti.codice_interno IN ('CON', 'POSTA')),
    'POSTA',
    '21) ... e non ne fa nascere la copia: nasce solo l''indirizzo chiesto');

-- ============================================================
-- 22-29) Il ruolo
-- ============================================================
SELECT is(
    pg_temp.codici(anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto(
        (SELECT tipo_ruolo FROM _f), ARRAY[pg_temp.tipo('CON')], pg_temp.tipo('CON'),
        -- natura NULL: la natura non da' motivi (20261116-18)
        script.fn_data_operativa(), NULL, NULL)),
    ARRAY['E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE', 'E_TIPO_INDIRIZZO_NON_PERMESSO'],
    '22) la check del ruolo sul contesto: presente e scaduto, i due motivi nell''ordine');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzo_ruolo(%s, %L::jsonb)',
        (SELECT sr_id FROM _f),
        (SELECT base FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'FORNITURA'))),
    NULL,
    '23) la singolare del ruolo: un tipo nuovo, passa');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzo_ruolo(%s, %L::jsonb)',
        (SELECT sr_id FROM _f),
        (SELECT base FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'FORNITURA'))),
    'E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE',
    '24) lo stesso tipo di nuovo: E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE');

SELECT is(
    anagrafiche.fn_check_tipo_indirizzo_ruolo(
        (SELECT sr_id FROM _f), (SELECT istanza_id FROM _f), pg_temp.tipo('FORNITURA')),
    '[]'::jsonb,
    '25) lo stesso tipo su un''istanza: nessun motivo (un''altra chiave)');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzo_ruolo(%s, %L::jsonb)',
        (SELECT sr_id FROM _f),
        (SELECT base FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'CON'))),
    'E_TIPO_INDIRIZZO_NON_PERMESSO',
    '26) un tipo con la riga scaduta: E_TIPO_INDIRIZZO_NON_PERMESSO');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_check_tipo_indirizzo_ruolo(-1, NULL, %s)', pg_temp.tipo('FORNITURA'))),
    'E_SOGGETTO_RUOLO_NON_TROVATO',
    '27) la check su un ruolo che non c''e'': E_SOGGETTO_RUOLO_NON_TROVATO');

SELECT pg_temp.matrice_ruolo(tipo_ruolo, 'CON', true, DATE '2000-01-01', DATE '2000-12-31') FROM _f;

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzi_ruolo(%s, %L::jsonb)',
        (SELECT sr_id FROM _f),
        jsonb_build_array((SELECT base FROM _el)
                          || jsonb_build_object('tipo_indirizzo_codice_interno', 'POSTA')))),
    NULL,
    '28) la plurale del ruolo con un obbligatorio scaduto: passa');

SELECT is(
    (SELECT count(*)::integer
       FROM anagrafiche.indirizzi i
      WHERE i.soggetto_ruolo_id = (SELECT sr_id FROM _f)
        AND i.tipo_indirizzo_id = pg_temp.tipo('CON')),
    0,
    '29) ... e non ne fa nascere la copia');

-- ============================================================
-- 30-33) Le frasi del tipo non ammesso: due valori, per descrizione
-- ============================================================
CREATE FUNCTION pg_temp.messaggio_di(p_sql text) RETURNS text LANGUAGE plpgsql AS $f$
DECLARE v_msg text;  -- valore della diagnostica
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
    RETURN v_msg;
END $f$;

CREATE TEMP TABLE _nomi ON COMMIT DROP AS
SELECT (SELECT COALESCE(tsd.descrizione, tsd.codice_interno)
          FROM config.tipi_soggetto_dettaglio tsd WHERE tsd.id = _f.natura) AS natura,
       (SELECT tr.descrizione FROM config.tipi_ruoli tr WHERE tr.id = _f.tipo_ruolo) AS ruolo,
       (SELECT ti.descrizione FROM config.tipi_indirizzi ti WHERE ti.codice_interno = 'CON') AS tipo
  FROM _f;

SELECT is(
    anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(
        (SELECT natura FROM _f), '{}', pg_temp.tipo('CON'), script.fn_data_operativa(), NULL)
        -> 0 -> 'valori',
    (SELECT jsonb_build_array(natura, tipo) FROM _nomi),
    '30) i valori del motivo sul soggetto: la natura e il tipo, per descrizione');

-- L'UPDATE diretto del tipo salta la madre: parla il guard della tabella.
SELECT is(
    pg_temp.messaggio_di(format(
        'UPDATE anagrafiche.indirizzi_soggetti SET tipo_indirizzo_id = %s
          WHERE soggetto_id = %L AND tipo_indirizzo_id = %s',
        pg_temp.tipo('CON'), (SELECT soggetto_id FROM _f), pg_temp.tipo('FORNITURA'))),
    (SELECT format('Il tipo soggetto %s non prevede l''indirizzo «%s».', natura, tipo) FROM _nomi),
    '31) la frase del guard del soggetto, da una strada che salta la madre');

SELECT is(
    anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto(
        (SELECT tipo_ruolo FROM _f), '{}', pg_temp.tipo('CON'), script.fn_data_operativa(), NULL, NULL)
        -> 0 -> 'valori',
    (SELECT jsonb_build_array(ruolo, tipo) FROM _nomi),
    '32) i valori del motivo sul ruolo: il tipo di ruolo e il tipo, per descrizione');

SELECT is(
    pg_temp.messaggio_di(format(
        'UPDATE anagrafiche.indirizzi SET tipo_indirizzo_id = %s
          WHERE soggetto_ruolo_id = %s AND istanza_utility_id IS NULL AND tipo_indirizzo_id = %s',
        pg_temp.tipo('CON'), (SELECT sr_id FROM _f), pg_temp.tipo('FORNITURA'))),
    (SELECT format('Il ruolo %s non prevede l''indirizzo «%s».', ruolo, tipo) FROM _nomi),
    '33) la frase del guard del ruolo, da una strada che salta la madre');

-- ============================================================
-- 34) Il fallback permissivo: un tipo di ruolo senza matrice
-- ============================================================
DELETE FROM config.tipi_ruolo_tipi_indirizzo WHERE tipo_ruolo_id = (SELECT tipo_ruolo FROM _f);

SELECT ok(anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo(
              (SELECT tipo_ruolo FROM _f), pg_temp.tipo('CON'), script.fn_data_operativa()),
          '34) tipo di ruolo senza nessuna riga di matrice: ammesso');

SELECT * FROM finish();
ROLLBACK;
