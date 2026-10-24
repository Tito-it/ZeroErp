-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: emittente e utility di preventivo, offerta e contratto non si
--   cambiano, nemmeno in bozza: in bozza si cambia il cliente, dentro la
--   stessa utility (B-4 ed E-3 di Tid). Lo dice il montaggio del lock di
--   testata con una terna «ferma sempre» ('-'), e la capability lo legge da li'.
--   Brief: docs/it/dev/work-in-progress/brief-db-indirizzi-documento-seguono-il-cliente.md (§8.7)
--   ChangeSet 20261018-65 … -68.
--
-- Elenco test (plan 18):
--  LA GRAMMATICA E LA DECISIONE
--   1) una terna con '-' e' ferma sempre (stati vuoti); le altre no
--   2) '-' insieme a degli stati e' un montaggio sbagliato; ' - ' da solo no
--   3) la decisione: la colonna ferma sempre si ferma anche in bozza; le altre in bozza passano,
--      fuori bozza come prima; con lo stato NULL si ferma ogni colonna nominata
--  I MONTAGGI
--   4) le colonne ferme sempre delle sei testate: utility ed emittente di preventivo, offerta e
--      contratto, coi due codici nuovi; DDT, reso e ordine nessuna
--  IN BOZZA, SUI DOCUMENTI VERI
--   5) preventivo: il cliente passa su un'altra utility -> E_DOC_UTILITY_IMMUTABILE
--   6) preventivo: un altro emittente -> E_DOC_EMITTENTE_IMMUTABILE, prima del guard emittente/BA
--   7) offerta: utility
--   8) offerta: emittente
--   9) contratto: utility
--  10) contratto: emittente
--  11) preventivo: il cliente cambia dentro la stessa utility, e passa
--  12) offerta: idem
--  13) contratto: idem, e riscrivere utility ed emittente allo stesso valore passa
--  LA CAPABILITY LEGGE IL MONTAGGIO
--  14) preventivo in bozza: testata modificabile, utility ed emittente fra i non modificabili, il cliente no
--  15) offerta in bozza: idem
--  16) contratto in bozza: idem
--  17) la capability del preventivo non porta piu' la sua lista «sempre»
--  18) i due codici sono a catalogo, CONFLITTO_STATO, col messaggio
--
-- Scopo:
--  - ⭐ i documenti si COSTRUISCONO (tre clienti fabbricati: A e B sulla stessa
--    utility, C su un'altra), non si cercano;
--  - i rifiuti si leggono dal canale CONSTRAINT (P0001 + codice);
--  - ⚠️ 6, 8, 10 usano un emittente che non esiste (-1): e' il punto. Se a
--    parlare fosse il guard emittente/BA (_a10_) o la FK, il codice sarebbe un
--    altro; il lock _a05_ parla prima di tutti.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

-- Due utility diverse dal catalogo, scelte per ordine.
CREATE TEMP TABLE _u AS
SELECT (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1)          AS prima,
       (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1 OFFSET 1) AS seconda;

CREATE TEMP TABLE _c AS
SELECT 'A' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('fermi A', (SELECT prima FROM _u), (SELECT soggetto_ruolo_id FROM _m)) c
UNION ALL
SELECT 'B' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('fermi B', (SELECT prima FROM _u), (SELECT soggetto_ruolo_id FROM _m)) c
UNION ALL
SELECT 'C' AS lato, c.* FROM dbops.fn_pgtap_crea_cliente_ba('fermi C', (SELECT seconda FROM _u), (SELECT soggetto_ruolo_id FROM _m)) c;

SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE _l AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT prima FROM _u), 'emittente e utility fermi');

CREATE TEMP TABLE _doc (chiave text PRIMARY KEY, id bigint);

DO $fixture$
DECLARE
    a    record;
    v_id bigint;
BEGIN
    SELECT * INTO a FROM _c WHERE lato = 'A';

    INSERT INTO vendite.preventivi
        (stato_doc_preventivo_id, utility_id, istanza_utility_id, billing_account_id,
         data, emittente_fiscale_id, valuta_id)
    VALUES
        ((SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT'),
         a.utility_id, a.istanza_utility_id, a.billing_account_id,
         script.fn_data_operativa(), (SELECT emittente_fiscale_id FROM _m),
         (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1))
    RETURNING id INTO v_id;
    INSERT INTO _doc VALUES ('PREV', v_id);

    INSERT INTO vendite.offerte_commerciali
        (emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
         listino_id, validita_dal, validita_al, stato_doc_offerta_id)
    VALUES
        ((SELECT emittente_fiscale_id FROM _m), a.billing_account_id, a.istanza_utility_id, a.utility_id,
         (SELECT listino_id FROM _l), script.fn_data_operativa(), script.fn_data_operativa() + 365,
         (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA'))
    RETURNING id INTO v_id;
    INSERT INTO _doc VALUES ('OFF', v_id);

    SELECT k.contratto_id INTO v_id
      FROM vendite.fn_create_contratto(
             jsonb_build_object(
               'billing_account_id',   a.billing_account_id,
               'emittente_fiscale_id', (SELECT emittente_fiscale_id FROM _m),
               'istanza_utility_id',   a.istanza_utility_id,
               'utility_id',           a.utility_id,
               'valido_dal',           make_date(2063, 1, 1),
               'valido_al',            make_date(2063, 12, 31)),
             NULL) AS k;
    INSERT INTO _doc VALUES ('CON', v_id);
END
$fixture$;

CREATE FUNCTION pg_temp.doc(p text) RETURNS bigint
LANGUAGE sql STABLE AS $f$ SELECT id FROM _doc WHERE chiave = p $f$;

-- Scopo: il codice di dominio di un'istruzione che fallisce (P0001 + CONSTRAINT),
--   'PASSA' se non fallisce. Il cambio si annulla in ogni caso: i test dopo
--   ripartono dallo stesso documento.
CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_s text; v_c text; v_esito text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        v_esito := 'PASSA';
        RAISE EXCEPTION USING ERRCODE = 'P0099', MESSAGE = 'annulla';
    EXCEPTION
        WHEN SQLSTATE 'P0099' THEN NULL;
        WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
            v_esito := CASE WHEN v_s = 'P0001' AND coalesce(v_c, '') <> '' THEN v_c
                            ELSE v_s || coalesce(' ' || nullif(v_c, ''), '') END;
    END;
    RETURN v_esito;
END
$f$;

-- Scopo: l'UPDATE che porta il documento sul cliente del lato (BA, istanza, utility).
CREATE FUNCTION pg_temp.sposta(p_tabella text, p_id bigint, p_lato text) RETURNS text
LANGUAGE sql STABLE AS $f$
  SELECT format('UPDATE vendite.%I SET billing_account_id = %s, istanza_utility_id = %s, utility_id = %s WHERE id = %s',
                p_tabella, c.billing_account_id, c.istanza_utility_id, c.utility_id, p_id)
    FROM _c c WHERE c.lato = p_lato;
$f$;

-- Scopo: la testata nella capability, in una forma confrontabile.
CREATE FUNCTION pg_temp.cap(p_cap jsonb) RETURNS text
LANGUAGE sql IMMUTABLE AS $f$
  SELECT concat_ws('|', p_cap ->> 'can_edit_testata',
                   (p_cap -> 'non_editable_fields' ? 'utility_id')::text,
                   (p_cap -> 'non_editable_fields' ? 'emittente_fiscale_id')::text,
                   (p_cap -> 'non_editable_fields' ? 'billing_account_id')::text,
                   (p_cap -> 'non_editable_fields' ? 'istanza_utility_id')::text);
$f$;

-- ============================================================
-- 1-3) LA GRAMMATICA E LA DECISIONE
-- ============================================================
CREATE TEMP TABLE _r AS
SELECT script.fn_doc_lock_regola('TESTATA',
         ARRAY['X', 'B', 'a', 'E_A', '', 'b', 'E_B', '-', 'c', 'E_C', 'S1']) AS regola;

SELECT is(
    (SELECT regola -> 'colonne' FROM _r),
    jsonb_build_array(
        jsonb_build_object('colonna', 'a', 'codice', 'E_A', 'ferma_sempre', false, 'stati_ammessi', '[]'::jsonb),
        jsonb_build_object('colonna', 'b', 'codice', 'E_B', 'ferma_sempre', true,  'stati_ammessi', '[]'::jsonb),
        jsonb_build_object('colonna', 'c', 'codice', 'E_C', 'ferma_sempre', false, 'stati_ammessi', jsonb_build_array('S1'))),
    '1) la terna con ''-'' e'' ferma sempre, con gli stati vuoti; le altre no');

SELECT is(
    ARRAY[(script.fn_doc_lock_regola('TESTATA', ARRAY['X', 'B', 'a', 'E_A', '-,S1']) ->> 'errore') IS NOT NULL,
          (script.fn_doc_lock_regola('TESTATA', ARRAY['X', 'B', 'a', 'E_A', 'S1, -']) ->> 'errore') IS NOT NULL,
          (script.fn_doc_lock_regola('TESTATA', ARRAY['X', 'B', 'a', 'E_A', ' - ']) -> 'colonne' -> 0 ->> 'ferma_sempre')::boolean],
    ARRAY[true, true, true],
    '2) ''-'' mescolato a degli stati e'' un montaggio sbagliato; '' - '' da solo e'' una colonna ferma sempre');

SELECT is(
    (SELECT concat_ws(' ; ',
              coalesce(script.fn_doc_lock_colonna_bloccata(regola, 'B',  ARRAY['a', 'b', 'c']), 'NULL'),
              coalesce(script.fn_doc_lock_colonna_bloccata(regola, 'B',  ARRAY['a', 'c']),      'NULL'),
              coalesce(script.fn_doc_lock_colonna_bloccata(regola, 'S1', ARRAY['c']),           'NULL'),
              coalesce(script.fn_doc_lock_colonna_bloccata(regola, 'S1', ARRAY['b', 'c']),      'NULL'),
              coalesce(script.fn_doc_lock_colonna_bloccata(regola, 'S2', ARRAY['c', 'a']),      'NULL'),
              coalesce(script.fn_doc_lock_colonna_bloccata(regola, NULL, ARRAY['c']),           'NULL'))
       FROM _r),
    'b ; NULL ; NULL ; b ; a ; c',
    '3) in bozza si ferma solo la colonna ferma sempre; fuori bozza come prima (la prima nell''ordine del montaggio); lo stato NULL ferma tutto');

-- ============================================================
-- 4) I MONTAGGI
-- ============================================================
SELECT is(
    (SELECT string_agg(x.tabella || '.' || (e ->> 'colonna') || '=' || (e ->> 'codice'), ', '
                       ORDER BY x.tabella, e ->> 'colonna')
       FROM (VALUES ('ddt'), ('resi'), ('ordini'), ('preventivi'), ('offerte_commerciali'), ('contratti')) AS x(tabella)
       CROSS JOIN LATERAL script.fn_doc_lock_montaggi(('vendite.' || x.tabella)::regclass) AS m
       CROSS JOIN LATERAL jsonb_array_elements(m.regola -> 'colonne') AS e
      WHERE m.regola ->> 'building_block' = 'TESTATA'
        AND (e ->> 'ferma_sempre')::boolean),
    'contratti.emittente_fiscale_id=E_DOC_EMITTENTE_IMMUTABILE, contratti.utility_id=E_DOC_UTILITY_IMMUTABILE, '
    'offerte_commerciali.emittente_fiscale_id=E_DOC_EMITTENTE_IMMUTABILE, offerte_commerciali.utility_id=E_DOC_UTILITY_IMMUTABILE, '
    'preventivi.emittente_fiscale_id=E_DOC_EMITTENTE_IMMUTABILE, preventivi.utility_id=E_DOC_UTILITY_IMMUTABILE',
    '4) ferme sempre: utility ed emittente di preventivo, offerta e contratto, coi codici nuovi; DDT, reso e ordine nessuna');

-- ============================================================
-- 5-13) IN BOZZA, SUI DOCUMENTI VERI
-- ============================================================
SELECT is(pg_temp.esito(pg_temp.sposta('preventivi', pg_temp.doc('PREV'), 'C')),
          'E_DOC_UTILITY_IMMUTABILE',
          '5) preventivo in bozza: il cliente di un''altra utility non passa, la utility e'' ferma');

SELECT is(pg_temp.esito(format('UPDATE vendite.preventivi SET emittente_fiscale_id = -1 WHERE id = %s', pg_temp.doc('PREV'))),
          'E_DOC_EMITTENTE_IMMUTABILE',
          '6) preventivo in bozza: l''emittente e'' fermo, e il lock parla prima del guard emittente/BA');

SELECT is(pg_temp.esito(pg_temp.sposta('offerte_commerciali', pg_temp.doc('OFF'), 'C')),
          'E_DOC_UTILITY_IMMUTABILE',
          '7) offerta in bozza: la utility e'' ferma');

SELECT is(pg_temp.esito(format('UPDATE vendite.offerte_commerciali SET emittente_fiscale_id = -1 WHERE id = %s', pg_temp.doc('OFF'))),
          'E_DOC_EMITTENTE_IMMUTABILE',
          '8) offerta in bozza: l''emittente e'' fermo');

SELECT is(pg_temp.esito(pg_temp.sposta('contratti', pg_temp.doc('CON'), 'C')),
          'E_DOC_UTILITY_IMMUTABILE',
          '9) contratto in bozza: la utility e'' ferma');

SELECT is(pg_temp.esito(format('UPDATE vendite.contratti SET emittente_fiscale_id = -1 WHERE id = %s', pg_temp.doc('CON'))),
          'E_DOC_EMITTENTE_IMMUTABILE',
          '10) contratto in bozza: l''emittente e'' fermo');

SELECT is(pg_temp.esito(pg_temp.sposta('preventivi', pg_temp.doc('PREV'), 'B')),
          'PASSA',
          '11) preventivo in bozza: il cliente cambia dentro la stessa utility');

SELECT is(pg_temp.esito(pg_temp.sposta('offerte_commerciali', pg_temp.doc('OFF'), 'B')),
          'PASSA',
          '12) offerta in bozza: il cliente cambia dentro la stessa utility');

SELECT is(pg_temp.esito(pg_temp.sposta('contratti', pg_temp.doc('CON'), 'B'))
          || ' ' ||
          pg_temp.esito(format('UPDATE vendite.contratti SET utility_id = utility_id, emittente_fiscale_id = emittente_fiscale_id WHERE id = %s',
                               pg_temp.doc('CON'))),
          'PASSA PASSA',
          '13) contratto in bozza: il cliente cambia dentro la stessa utility; utility ed emittente riscritti uguali passano (il lock guarda il cambio)');

-- ============================================================
-- 14-18) LA CAPABILITY LEGGE IL MONTAGGIO
-- ============================================================
SELECT is(pg_temp.cap(script.fn_available_actions_preventivo(pg_temp.doc('PREV'))),
          'true|true|true|false|false',
          '14) preventivo in bozza: testata modificabile; utility ed emittente non modificabili, il cliente si''');

SELECT is(pg_temp.cap(script.fn_available_actions_offerta(pg_temp.doc('OFF'))),
          'true|true|true|false|false',
          '15) offerta in bozza: idem');

SELECT is(pg_temp.cap(script.fn_available_actions_contratto(pg_temp.doc('CON'))),
          'true|true|true|false|false',
          '16) contratto in bozza: idem');

SELECT is(
    -- commenti tolti: la nota di revisione nel corpo nomina la lista ritirata
    (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'c_sempre_non_edit'
       FROM pg_proc p
      WHERE p.oid = 'script.fn_available_actions_preventivo'::regproc),
    false,
    '17) la capability del preventivo non porta piu'' la sua lista «sempre»: la utility ferma la dice il montaggio');

SELECT is(
    (SELECT string_agg(c.codice || ':' || c.classe || ':' || (m.messaggio IS NOT NULL)::text, ',' ORDER BY c.codice)
       FROM config.codici_errore c
       LEFT JOIN config.messaggi_errore m ON m.codice = c.codice AND m.lingua = 'it'
      WHERE c.codice IN ('E_DOC_EMITTENTE_IMMUTABILE', 'E_DOC_UTILITY_IMMUTABILE')),
    'E_DOC_EMITTENTE_IMMUTABILE:CONFLITTO_STATO:true,E_DOC_UTILITY_IMMUTABILE:CONFLITTO_STATO:true',
    '18) i due codici sono a catalogo, CONFLITTO_STATO, col messaggio');

SELECT * FROM finish();
ROLLBACK;
