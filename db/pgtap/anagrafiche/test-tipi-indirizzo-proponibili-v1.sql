-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- I picker dei tipi di indirizzo: sulla natura, sul soggetto, sul tipo di
-- ruolo, sul ruolo. Propongono cio' che la madre singolare accetta, leggendo
-- la stessa check (linee-guida-sql §12.6).
--   Brief: brief-db-copia-indirizzo-soggetto §3.1, §4.3, §4.6, giro 2.
--   ChangeSet 20261114-96, -97; 20261115-60, -61 (§8, Q-2).
--   Rev 2026-11-17 (brief-db-fornitore-privato-indirizzi, 20261116-18): il picker
--   sul tipo di ruolo prende il soggetto in coda; qui sempre NULL (soggetto non
--   ancora scelto), e le risposte restano quelle di prima. La natura nei picker
--   la prova test-fornitore-privato-indirizzi-v1.
--
-- Elenco test (plan 25):
--   presidi
--    1) i picker del soggetto e della natura leggono la check della madre
--    2) i picker del ruolo e del tipo di ruolo leggono la check della madre
--   la natura (matrice costruita: FORNITURA valida, CON scaduta, POSTA obbligatoria)
--    3) una riga per tipo del catalogo
--    4) la riga scaduta (§3.1, primo caso): FORNITURA ammesso, CON spento col motivo
--    5) obbligatorio: POSTA si', CON no (la sua riga e' scaduta)
--    6) prima gli ammessi, poi gli altri
--   il soggetto
--    7) prima di scriverlo: FORNITURA ammesso
--    8) scritto FORNITURA: il picker lo spegne con TIPO_GIA_PRESENTE ...
--    9) ... e il codice e' quello che la singolare solleva
--   10) CON: il codice del picker e' quello che la singolare solleva
--   11) i valori del motivo: la natura e il tipo
--   12) un soggetto che non c'e': nessuna riga
--   la natura senza matrice (§3.1, secondo caso)
--   13) tutti i tipi ammessi
--   14) ... e la singolare accetta CON
--   il tipo di ruolo e il ruolo (matrice costruita come per la natura)
--   15) tipo di ruolo: FORNITURA ammesso, CON spento col motivo del ruolo
--   16) tipo di ruolo: obbligatorio, POSTA si', CON no
--   17) ruolo, scritto FORNITURA: spento col codice che la singolare solleva
--   18) ruolo, sull'istanza: FORNITURA ammesso (un'altra chiave)
--   19) un ruolo che non c'e': nessuna riga
--   20) tipo di ruolo senza matrice: tutti i tipi ammessi
--   21) ... e la singolare del ruolo accetta CON
--   la chiave che non c'e' (§8, Q-2): nessuna riga, come le gemelle sul salvato
--   22) una natura che non c'e': nessuna riga
--   23) natura NULL (nessuna natura scelta): tutti i tipi ammessi
--   24) un tipo di ruolo che non c'e': nessuna riga
--   25) tipo di ruolo NULL: tutti i tipi ammessi
--
-- Scopo:
--  - i due casi del §3.1 (la riga attiva fuori finestra, la natura o il tipo di
--    ruolo senza matrice) si COSTRUISCONO sulle matrici, e su ciascuno picker e
--    madre singolare devono dire la stessa cosa (regola zero: niente si appoggia
--    alle righe di oggi; il seed serve solo come catalogo dei tipi).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- La fixture crea il soggetto (padre) e i suoi indirizzi nello stesso
-- builder, che apre e richiude da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(25);

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

-- Il soggetto (una persona giuridica) e il ruolo con un'istanza, dai builder.
-- ⚠️ Le colonne delle tabelle temporanee hanno il tipo esplicito: %TYPE nel DDL
--   di tabella non si scrive (linee-guida-sql §5g). Ognuna e' il tipo della
--   colonna di cui e' il riflesso.
CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT script.fn_stato_id_da_iso2('IT') AS it_id,
       dbops.fn_pgtap_crea_soggetto_pg('pgTAP tipi indirizzo proponibili', 3,
                                       script.fn_stato_id_da_iso2('IT')) AS soggetto_id;

ALTER TABLE _f ADD COLUMN natura bigint, ADD COLUMN sr_id bigint,
               ADD COLUMN istanza_id bigint, ADD COLUMN tipo_ruolo integer;
UPDATE _f SET natura = (SELECT s.tipo_soggetto_dettaglio_id
                          FROM anagrafiche.soggetti s WHERE s.id = _f.soggetto_id);
UPDATE _f SET (sr_id, istanza_id) = (
    SELECT c.soggetto_ruolo_id, c.istanza_utility_id
      FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP tipi indirizzo proponibili') c);
UPDATE _f SET tipo_ruolo = (SELECT sr.tipo_ruolo_id
                              FROM anagrafiche.soggetti_ruoli sr WHERE sr.id = _f.sr_id);

-- Un indirizzo libero valido per l'Italia; il tipo si aggiunge caso per caso.
CREATE TEMP TABLE _el ON COMMIT DROP AS
SELECT jsonb_strip_nulls(
           jsonb_build_object('indirizzo_libero', 'Via pgTAP proponibili 1', 'stato_id', _f.it_id)
           || to_jsonb(fm)) AS base
  FROM _f, dbops.fn_pgtap_indirizzo_libero_forma(_f.it_id) fm;

-- Le righe che contano, sulle due matrici: FORNITURA attiva e valida, CON
-- obbligatoria ma scaduta, POSTA obbligatoria e valida.
SELECT pg_temp.matrice_natura(natura, 'FORNITURA', false, NULL, NULL),
       pg_temp.matrice_natura(natura, 'CON',       true,  DATE '2000-01-01', DATE '2000-12-31'),
       pg_temp.matrice_natura(natura, 'POSTA',     true,  NULL, NULL),
       pg_temp.matrice_ruolo(tipo_ruolo, 'FORNITURA', false, NULL, NULL),
       pg_temp.matrice_ruolo(tipo_ruolo, 'CON',       true,  DATE '2000-01-01', DATE '2000-12-31'),
       pg_temp.matrice_ruolo(tipo_ruolo, 'POSTA',     true,  NULL, NULL)
  FROM _f;

-- La singolare, per confrontare il suo rifiuto col motivo del picker.
CREATE FUNCTION pg_temp.scrivi_soggetto(p_tipo config.tipi_indirizzi.codice_interno%TYPE)
RETURNS text LANGUAGE sql AS $f$
    SELECT dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)',
        (SELECT soggetto_id FROM _f),
        (SELECT base FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', p_tipo)))
$f$;

CREATE FUNCTION pg_temp.scrivi_ruolo(p_tipo config.tipi_indirizzi.codice_interno%TYPE)
RETURNS text LANGUAGE sql AS $f$
    SELECT dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzo_ruolo(%s, %L::jsonb)',
        (SELECT sr_id FROM _f),
        (SELECT base FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', p_tipo)))
$f$;

-- ============================================================
-- 1-2) Presidi: i picker leggono la check della madre
-- ============================================================
-- ⚠️ Per una BEGIN ATOMIC il legame si legge da pg_depend, non dal testo:
--   pg_get_functiondef stampa i nomi relativi al search_path della sessione,
--   e da zeroerp_app (che ha anagrafiche nel path) lo schema sparisce
--   (linee-guida-sql §5c).
CREATE FUNCTION pg_temp.dipende(p_da regprocedure, p_da_chi regprocedure) RETURNS boolean
LANGUAGE sql AS $f$
    SELECT EXISTS (SELECT 1 FROM pg_depend d
                    WHERE d.classid = 'pg_proc'::regclass AND d.objid = p_da::oid
                      AND d.refclassid = 'pg_proc'::regclass AND d.refobjid = p_da_chi::oid)
$f$;

SELECT ok(
    pg_temp.dipende('anagrafiche.fn_tipi_indirizzo_proponibili_natura(bigint)',
                    'anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(bigint, integer[], integer, date, uuid)')
    AND pg_temp.dipende('anagrafiche.fn_tipi_indirizzo_proponibili_soggetto(uuid)',
                        'anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto(bigint, integer[], integer, date, uuid)'),
    '1) i picker del soggetto e della natura leggono la check della madre');

SELECT ok(
    -- rev 2026-11-17 (20261116-18): la meta' sul contesto prende la natura in coda,
    --   il picker sul tipo di ruolo il soggetto.
    pg_temp.dipende('anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(integer, uuid)',
                    'anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto(integer, integer[], integer, date, bigint, bigint)')
    AND pg_temp.dipende('anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(bigint, bigint)',
                        'anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto(integer, integer[], integer, date, bigint, bigint)'),
    '2) i picker del ruolo e del tipo di ruolo leggono la check della madre');

-- ============================================================
-- 3-6) La natura
-- ============================================================
SELECT is(
    (SELECT count(*)::integer FROM anagrafiche.fn_tipi_indirizzo_proponibili_natura((SELECT natura FROM _f))),
    (SELECT count(*)::integer FROM config.tipi_indirizzi),
    '3) una riga per tipo del catalogo');

SELECT results_eq(
    format($$SELECT ammesso, reason
               FROM anagrafiche.fn_tipi_indirizzo_proponibili_natura(%s)
              WHERE tipo_indirizzo_id IN (%s, %s)
              ORDER BY ammesso DESC$$,
           (SELECT natura FROM _f), pg_temp.tipo('FORNITURA'), pg_temp.tipo('CON')),
    $$VALUES (true, NULL::text), (false, 'TIPO_NON_AMMESSO_DALLA_NATURA')$$,
    '4) la riga scaduta: FORNITURA ammesso, CON spento col motivo della natura');

SELECT results_eq(
    format($$SELECT obbligatorio
               FROM anagrafiche.fn_tipi_indirizzo_proponibili_natura(%s)
              WHERE tipo_indirizzo_id IN (%s, %s)
              ORDER BY tipo_indirizzo_id = %s DESC$$,
           (SELECT natura FROM _f), pg_temp.tipo('POSTA'), pg_temp.tipo('CON'), pg_temp.tipo('POSTA')),
    $$VALUES (true), (false)$$,
    '5) obbligatorio: POSTA si'', CON no (la sua riga e'' scaduta)');

SELECT is(
    (SELECT bool_and(NOT (NOT ammesso AND seguente))
       FROM (SELECT ammesso,
                    lead(ammesso) OVER (ORDER BY ord) AS seguente
               FROM anagrafiche.fn_tipi_indirizzo_proponibili_natura((SELECT natura FROM _f))
                    WITH ORDINALITY AS t(tipo_indirizzo_id, obbligatorio, ammesso, motivo_codice,
                                         reason, reason_key, reason_valori, motivi, ord)) x
      WHERE seguente IS NOT NULL),
    true,
    '6) prima gli ammessi, poi gli altri');

-- ============================================================
-- 7-12) Il soggetto: il picker dice cio' che la singolare fa
-- ============================================================
SELECT is(
    (SELECT ammesso FROM anagrafiche.fn_tipi_indirizzo_proponibili_soggetto((SELECT soggetto_id FROM _f))
      WHERE tipo_indirizzo_id = pg_temp.tipo('FORNITURA')),
    true,
    '7) prima di scriverlo: FORNITURA ammesso');

-- Fixture: la singolare scrive FORNITURA (si ferma se non passa).
DO $w$ BEGIN
    IF pg_temp.scrivi_soggetto('FORNITURA') IS NOT NULL THEN
        RAISE EXCEPTION 'fixture: FORNITURA sul soggetto non scritto';
    END IF;
END $w$;
SELECT is(
    (SELECT reason FROM anagrafiche.fn_tipi_indirizzo_proponibili_soggetto((SELECT soggetto_id FROM _f))
      WHERE tipo_indirizzo_id = pg_temp.tipo('FORNITURA')),
    'TIPO_GIA_PRESENTE',
    '8) scritto FORNITURA: il picker lo spegne con TIPO_GIA_PRESENTE');

SELECT is(
    (SELECT motivo_codice FROM anagrafiche.fn_tipi_indirizzo_proponibili_soggetto((SELECT soggetto_id FROM _f))
      WHERE tipo_indirizzo_id = pg_temp.tipo('FORNITURA')),
    pg_temp.scrivi_soggetto('FORNITURA'),
    '9) ... e il codice e'' quello che la singolare solleva');

SELECT is(
    (SELECT motivo_codice FROM anagrafiche.fn_tipi_indirizzo_proponibili_soggetto((SELECT soggetto_id FROM _f))
      WHERE tipo_indirizzo_id = pg_temp.tipo('CON')),
    pg_temp.scrivi_soggetto('CON'),
    '10) CON: il codice del picker e'' quello che la singolare solleva');

SELECT is(
    (SELECT reason_valori FROM anagrafiche.fn_tipi_indirizzo_proponibili_soggetto((SELECT soggetto_id FROM _f))
      WHERE tipo_indirizzo_id = pg_temp.tipo('CON')),
    (SELECT jsonb_build_array(COALESCE(tsd.descrizione, tsd.codice_interno), ti.descrizione)
       FROM _f
       JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = _f.natura
       JOIN config.tipi_indirizzi ti ON ti.codice_interno = 'CON'),
    '11) i valori del motivo: la natura e il tipo');

SELECT is(
    (SELECT count(*)::integer
       FROM anagrafiche.fn_tipi_indirizzo_proponibili_soggetto('00000000-0000-0000-0000-000000000001'::uuid)),
    0,
    '12) un soggetto che non c''e'': nessuna riga');

-- ============================================================
-- 13-14) La natura senza matrice: tutto ammesso, come per il guard
-- ============================================================
DELETE FROM config.tipi_soggetto_dettaglio_tipi_indirizzo
 WHERE tipo_soggetto_dettaglio_id = (SELECT natura FROM _f);

SELECT is(
    (SELECT count(*) FILTER (WHERE ammesso)::integer
       FROM anagrafiche.fn_tipi_indirizzo_proponibili_natura((SELECT natura FROM _f))),
    (SELECT count(*)::integer FROM config.tipi_indirizzi),
    '13) natura senza matrice: tutti i tipi ammessi');

SELECT is(pg_temp.scrivi_soggetto('CON'), NULL,
          '14) ... e la singolare accetta CON');

-- ============================================================
-- 15-21) Il tipo di ruolo e il ruolo
-- ============================================================
SELECT results_eq(
    format($$SELECT ammesso, reason
               FROM anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(%s, NULL::uuid)
              WHERE tipo_indirizzo_id IN (%s, %s)
              ORDER BY ammesso DESC$$,
           (SELECT tipo_ruolo FROM _f), pg_temp.tipo('FORNITURA'), pg_temp.tipo('CON')),
    $$VALUES (true, NULL::text), (false, 'TIPO_NON_AMMESSO_DAL_RUOLO')$$,
    '15) tipo di ruolo: FORNITURA ammesso, CON spento col motivo del ruolo');

SELECT results_eq(
    format($$SELECT obbligatorio
               FROM anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(%s, NULL::uuid)
              WHERE tipo_indirizzo_id IN (%s, %s)
              ORDER BY tipo_indirizzo_id = %s DESC$$,
           (SELECT tipo_ruolo FROM _f), pg_temp.tipo('POSTA'), pg_temp.tipo('CON'), pg_temp.tipo('POSTA')),
    $$VALUES (true), (false)$$,
    '16) tipo di ruolo: obbligatorio, POSTA si'', CON no');

-- Fixture: la singolare del ruolo scrive FORNITURA (si ferma se non passa).
DO $w$ BEGIN
    IF pg_temp.scrivi_ruolo('FORNITURA') IS NOT NULL THEN
        RAISE EXCEPTION 'fixture: FORNITURA sul ruolo non scritto';
    END IF;
END $w$;
SELECT is(
    (SELECT motivo_codice
       FROM anagrafiche.fn_tipi_indirizzo_proponibili_ruolo((SELECT sr_id FROM _f), NULL)
      WHERE tipo_indirizzo_id = pg_temp.tipo('FORNITURA')),
    pg_temp.scrivi_ruolo('FORNITURA'),
    '17) ruolo, scritto FORNITURA: spento col codice che la singolare solleva');

SELECT is(
    (SELECT ammesso
       FROM anagrafiche.fn_tipi_indirizzo_proponibili_ruolo((SELECT sr_id FROM _f), (SELECT istanza_id FROM _f))
      WHERE tipo_indirizzo_id = pg_temp.tipo('FORNITURA')),
    true,
    '18) ruolo, sull''istanza: FORNITURA ammesso (un''altra chiave)');

SELECT is(
    (SELECT count(*)::integer FROM anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(-1, NULL)),
    0,
    '19) un ruolo che non c''e'': nessuna riga');

DELETE FROM config.tipi_ruolo_tipi_indirizzo WHERE tipo_ruolo_id = (SELECT tipo_ruolo FROM _f);

SELECT is(
    (SELECT count(*) FILTER (WHERE ammesso)::integer
       FROM anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo((SELECT tipo_ruolo FROM _f), NULL::uuid)),
    (SELECT count(*)::integer FROM config.tipi_indirizzi),
    '20) tipo di ruolo senza matrice: tutti i tipi ammessi');

SELECT is(pg_temp.scrivi_ruolo('CON'), NULL,
          '21) ... e la singolare del ruolo accetta CON');

-- ============================================================
-- 22-25) La chiave che non c'e', e la chiave NULL
-- ============================================================
-- Una natura (o un tipo di ruolo) inesistente non e' una natura senza
-- matrice: la check, senza righe di matrice, ammetterebbe tutto. NULL e' il
-- form senza natura scelta, e resta «tutti ammessi», come il guard.
-- L'id che non c'e' si costruisce (max + 1), non si suppone.
SELECT is(
    (SELECT count(*)::integer FROM anagrafiche.fn_tipi_indirizzo_proponibili_natura(
                (SELECT COALESCE(max(id), 0) + 1 FROM config.tipi_soggetto_dettaglio))),
    0,
    '22) una natura che non c''e'': nessuna riga');

SELECT is(
    (SELECT count(*) FILTER (WHERE ammesso)::integer
       FROM anagrafiche.fn_tipi_indirizzo_proponibili_natura(NULL::bigint)),
    (SELECT count(*)::integer FROM config.tipi_indirizzi),
    '23) natura NULL: tutti i tipi ammessi');

SELECT is(
    (SELECT count(*)::integer FROM anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(
                (SELECT COALESCE(max(id), 0) + 1 FROM config.tipi_ruoli), NULL::uuid)),
    0,
    '24) un tipo di ruolo che non c''e'': nessuna riga');

SELECT is(
    (SELECT count(*) FILTER (WHERE ammesso)::integer
       FROM anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(NULL::integer, NULL::uuid)),
    (SELECT count(*)::integer FROM config.tipi_indirizzi),
    '25) tipo di ruolo NULL: tutti i tipi ammessi');

SELECT * FROM finish();
ROLLBACK;
