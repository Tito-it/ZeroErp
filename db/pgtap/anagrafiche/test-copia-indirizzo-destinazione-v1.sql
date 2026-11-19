-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La copia di un indirizzo verso il ruolo va sulla chiave di DESTINAZIONE: il
-- ruolo (istanza NULL) o una sua istanza. I due verbi (dalla riga del ruolo,
-- dalla riga del soggetto del ruolo), il BB che scrive, e il ritiro del motivo
-- di riga del ruolo.
--   Brief: brief-db-copia-indirizzo-destinazione §4, §4.1 (D-1 … D-4), giro 1.
--   ChangeSet 20261117-29 … -32; registro in config/azioni_riga.csv.
--
-- Elenco test (plan 28):
--   presidio
--    1) la firma a tre argomenti del verbo del ruolo non esiste piu'
--    2) ... e resta una sola fn_copia_indirizzo_ruolo
--    3) la check di riga del ruolo e' ritirata
--    4) la vista di azioni del ruolo e' ritirata
--    5) i due verbi scrivono dal BB, il BB dalla singolare: nessuna INSERT
--    6) l'azione COPIA_INDIRIZZO_RUOLO e' spenta nel registro
--   dalla riga del ruolo
--    7) dal ruolo a una sua istanza: la riga nasce sull'istanza
--    8) ... e non sul ruolo
--    9) da un'istanza al ruolo
--   10) da un'istanza a un'altra istanza dello stesso soggetto: il tipo che la
--       sorgente ha gia' sulla sua chiave si copia, perche' manca sulla destinazione
--   11) ... con tutte le colonne della forma
--   12) un tipo presente sulla destinazione e assente sulla sorgente:
--       E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE
--   13) due tipi, il secondo gia' presente sulla destinazione: rifiutata
--   14) ... e il primo non e' rimasto scritto (tutto o niente)
--   15) verso un'istanza di un altro soggetto: E_ISTANZA_ALTRO_SOGGETTO
--   16) la sorgente di un altro ruolo: E_INDIRIZZO_RUOLO_NON_TROVATO
--   17) un ruolo che non c'e': E_SOGGETTO_RUOLO_NON_TROVATO
--   18) l'elenco vuoto: E_SCRIPT_CHIAMATA_NON_VALIDA
--   19) due tipi: gli id nell'ordine dei tipi
--   20) destinazione piena e sorgente con tipi liberi: il picker della
--       destinazione non ne ammette nessuno, quello della sorgente si'
--   21) ... e la copia la rifiuta la singolare col motivo del tipo (D-4 a)
--   dalla riga del soggetto del ruolo (il gemello)
--   22) dal soggetto al ruolo: lo stesso dettaglio
--   23) dal soggetto a un'istanza del ruolo
--   24) un tipo gia' presente sulla destinazione: E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE
--   25) la riga di un altro soggetto: E_INDIRIZZO_SOGGETTO_NON_TROVATO
--   26) verso un'istanza di un altro soggetto: E_ISTANZA_ALTRO_SOGGETTO
--   27) un ruolo che non c'e': E_SOGGETTO_RUOLO_NON_TROVATO
--   28) l'elenco vuoto: E_SCRIPT_CHIAMATA_NON_VALIDA
--
-- Scopo:
--  - ogni caso si COSTRUISCE (regola zero): le matrici si tolgono (fallback
--    permissivo), la seconda istanza dello stesso soggetto e le sorgenti le
--    scrive il test; un pre-stato diverso da quello atteso ferma il test nella
--    fixture, non lo fa passare a vuoto;
--  - i casi 10 e 12 distinguono la regola nuova dalla vecchia: con la copia
--    sulla chiave della sorgente il 10 sarebbe rifiutato e il 12 scritto;
--  - «destinazione piena» si costruisce riempiendo tutti i tipi del catalogo
--    sull'istanza, non contando quelli di oggi.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- I builder aprono e richiudono da se' la finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(28);

-- ============================================================
-- Fixture
-- ============================================================
-- ⚠️ Le colonne delle tabelle temporanee hanno il tipo esplicito: %TYPE nel DDL
--   di tabella non si scrive (linee-guida-sql §5g).
CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT a.soggetto_ruolo_id AS sr_a, a.istanza_utility_id AS ist_a,
       b.soggetto_ruolo_id AS sr_b, b.istanza_utility_id AS ist_b,
       script.fn_stato_id_da_iso2('IT') AS it_id
  FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP copia destinazione A') a,
       dbops.fn_pgtap_crea_cliente_ba('pgTAP copia destinazione B') b;

ALTER TABLE _f ADD COLUMN sogg_a uuid, ADD COLUMN sogg_b uuid, ADD COLUMN ist2 bigint,
               ADD COLUMN natura_a bigint, ADD COLUMN natura_b bigint, ADD COLUMN tipo_ruolo integer;
UPDATE _f SET sogg_a = (SELECT sr.soggetto_id FROM anagrafiche.soggetti_ruoli sr WHERE sr.id = _f.sr_a),
              sogg_b = (SELECT sr.soggetto_id FROM anagrafiche.soggetti_ruoli sr WHERE sr.id = _f.sr_b),
              tipo_ruolo = (SELECT sr.tipo_ruolo_id FROM anagrafiche.soggetti_ruoli sr WHERE sr.id = _f.sr_a);
UPDATE _f SET natura_a = (SELECT s.tipo_soggetto_dettaglio_id FROM anagrafiche.soggetti s WHERE s.id = _f.sogg_a),
              natura_b = (SELECT s.tipo_soggetto_dettaglio_id FROM anagrafiche.soggetti s WHERE s.id = _f.sogg_b);

-- La seconda istanza dello stesso soggetto A, fittizia, col suo billing account
-- (un'istanza vuole il BA): dal BB, sulla prima utility senza PdP e con la
-- categoria del BA della prima istanza.
-- ⚠️ La finestra dei differiti si apre come nel builder: il guard «istanza con
--   BA» scatta sull'INSERT dell'istanza, prima che il BA esista.
SET CONSTRAINTS ALL DEFERRED;
DO $w$
DECLARE
    v_ist anagrafiche.billing_account.istanza_utility_id%TYPE;
BEGIN
    SELECT b.istanza_utility_id
      INTO v_ist
      FROM anagrafiche.fn_crea_billing_account(
               p_soggetto_ruolo_id           := (SELECT sr_a FROM _f),
               p_utility_id                  := (SELECT ba.utility_id FROM anagrafiche.billing_account ba
                                                  WHERE ba.istanza_utility_id = (SELECT ist_a FROM _f)
                                                  ORDER BY ba.id LIMIT 1),
               p_campi                       := jsonb_build_object(
                   'codice',               'PGTAP-CPDEST-IST2',
                   'categoria_cliente_id', (SELECT cc.id FROM anagrafiche.categorie_clienti cc
                                             ORDER BY cc.id LIMIT 1),
                   'valuta_id',            dbops.fn_pgtap_valuta()),
               p_istanza                     := jsonb_build_object('codice', 'PGTAP-CPDEST-IST2'),
               p_emittente_soggetto_ruolo_id := NULL) b;
    UPDATE _f SET ist2 = v_ist;
END $w$;
SET CONSTRAINTS ALL IMMEDIATE;

-- Le forme: una libera nazionale, un dettaglio.
CREATE TEMP TABLE _el ON COMMIT DROP AS
SELECT (SELECT jsonb_strip_nulls(jsonb_build_object('indirizzo_libero', 'Via pgTAP destinazione 1',
                                                    'stato_id', _f.it_id) || to_jsonb(fm))
          FROM dbops.fn_pgtap_indirizzo_libero_forma(_f.it_id) fm) AS nazionale,
       dbops.fn_pgtap_crea_indirizzo_dettaglio('pgTAP copia destinazione') AS dettaglio_id
  FROM _f;

-- Le matrici delle due nature e del tipo di ruolo si tolgono: tutti i tipi ammessi.
DELETE FROM config.tipi_soggetto_dettaglio_tipi_indirizzo
 WHERE tipo_soggetto_dettaglio_id IN (SELECT natura_a FROM _f UNION SELECT natura_b FROM _f);
DELETE FROM config.tipi_ruolo_tipi_indirizzo
 WHERE tipo_ruolo_id = (SELECT tipo_ruolo FROM _f);

CREATE FUNCTION pg_temp.tipo(p_codice config.tipi_indirizzi.codice_interno%TYPE)
RETURNS config.tipi_indirizzi.id%TYPE LANGUAGE sql AS
$f$ SELECT id FROM config.tipi_indirizzi WHERE codice_interno = p_codice $f$;

-- L'indirizzo del ruolo A di un tipo su una chiave (istanza NULL = il ruolo).
CREATE FUNCTION pg_temp.ind_r(p_codice config.tipi_indirizzi.codice_interno%TYPE,
                              p_istanza anagrafiche.indirizzi.istanza_utility_id%TYPE)
RETURNS anagrafiche.indirizzi.id%TYPE LANGUAGE sql AS
$f$ SELECT i.id FROM anagrafiche.indirizzi i
     WHERE i.soggetto_ruolo_id = (SELECT sr_a FROM _f) AND i.tipo_indirizzo_id = pg_temp.tipo(p_codice)
       AND i.istanza_utility_id IS NOT DISTINCT FROM p_istanza $f$;

CREATE FUNCTION pg_temp.forma_r(p_indirizzo anagrafiche.indirizzi.id%TYPE)
RETURNS jsonb LANGUAGE sql AS
$f$ SELECT jsonb_build_object(
               'indirizzo_dettaglio_id', i.indirizzo_dettaglio_id, 'indirizzo_libero', i.indirizzo_libero,
               'stato_id', i.stato_id, 'comune_id', i.comune_id, 'codice_postale_id', i.codice_postale_id,
               'administrative_area', i.administrative_area, 'locality', i.locality,
               'sublocality', i.sublocality, 'postal_code', i.postal_code)
      FROM anagrafiche.indirizzi i WHERE i.id = p_indirizzo $f$;

-- Il codice d'errore della copia di una riga del ruolo A verso una chiave del ruolo A.
CREATE FUNCTION pg_temp.copia_r(p_indirizzo anagrafiche.indirizzi.id%TYPE, p_tipi text[],
                                p_destinazione anagrafiche.indirizzi.istanza_utility_id%TYPE)
RETURNS text LANGUAGE sql AS
$f$ SELECT dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_copia_indirizzo_ruolo(%s, %s, %L::text[], %s::bigint)',
        (SELECT sr_a FROM _f), p_indirizzo, p_tipi, COALESCE(p_destinazione::text, 'NULL'))) $f$;

-- Il codice d'errore della copia di una riga del soggetto verso una chiave del ruolo A.
CREATE FUNCTION pg_temp.copia_s(p_indirizzo_soggetto anagrafiche.indirizzi_soggetti.id%TYPE, p_tipi text[],
                                p_destinazione anagrafiche.indirizzi.istanza_utility_id%TYPE)
RETURNS text LANGUAGE sql AS
$f$ SELECT dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo(%s, %s, %L::text[], %s::bigint)',
        (SELECT sr_a FROM _f), p_indirizzo_soggetto, p_tipi, COALESCE(p_destinazione::text, 'NULL'))) $f$;

-- Il pre-stato che i casi danno per scontato: se la fixture e' cambiata, ci si
-- ferma qui invece di provare un caso diverso da quello scritto.
DO $w$
DECLARE
    v_ist  anagrafiche.indirizzi.istanza_utility_id%TYPE := (SELECT ist_a FROM _f);
    v_ist2 anagrafiche.indirizzi.istanza_utility_id%TYPE := (SELECT ist2 FROM _f);
BEGIN
    IF pg_temp.ind_r('CON', NULL) IS NOT NULL OR pg_temp.ind_r('FORNITURA', NULL) IS NOT NULL
       OR pg_temp.ind_r('RES', NULL) IS NOT NULL OR pg_temp.ind_r('POSTA', NULL) IS NOT NULL
       OR pg_temp.ind_r('SPED', v_ist) IS NOT NULL OR pg_temp.ind_r('POSTA', v_ist) IS NOT NULL
       OR pg_temp.ind_r('CON', v_ist) IS NOT NULL OR pg_temp.ind_r('FATT', v_ist) IS NOT NULL
       OR EXISTS (SELECT 1 FROM anagrafiche.indirizzi i WHERE i.istanza_utility_id = v_ist2)
       OR EXISTS (SELECT 1 FROM anagrafiche.indirizzi_soggetti s
                   WHERE s.soggetto_id IN (SELECT sogg_a FROM _f UNION SELECT sogg_b FROM _f)
                     AND s.tipo_indirizzo_id = pg_temp.tipo('SEDEOP')) THEN
        RAISE EXCEPTION 'fixture: il cliente del builder ha gia'' indirizzi dei tipi usati dal test';
    END IF;

    -- Le due sorgenti del ruolo A: SPED sull'istanza, CON sul ruolo.
    PERFORM anagrafiche.fn_crea_indirizzo_ruolo((SELECT sr_a FROM _f),
        (SELECT nazionale FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'SPED',
                                                          'istanza_utility_id', v_ist));
    PERFORM anagrafiche.fn_crea_indirizzo_ruolo((SELECT sr_a FROM _f),
        (SELECT nazionale FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'CON'));
    -- Le sorgenti dei soggetti: SEDEOP dal dettaglio su A, SEDEOP libera su B.
    PERFORM anagrafiche.fn_crea_indirizzo_soggetto((SELECT sogg_a FROM _f),
        jsonb_build_object('tipo_indirizzo_codice_interno', 'SEDEOP',
                           'indirizzo_dettaglio_id', (SELECT dettaglio_id FROM _el)));
    PERFORM anagrafiche.fn_crea_indirizzo_soggetto((SELECT sogg_b FROM _f),
        (SELECT nazionale FROM _el) || jsonb_build_object('tipo_indirizzo_codice_interno', 'SEDEOP'));
END $w$;

CREATE FUNCTION pg_temp.ind_s(p_soggetto anagrafiche.indirizzi_soggetti.soggetto_id%TYPE)
RETURNS anagrafiche.indirizzi_soggetti.id%TYPE LANGUAGE sql AS
$f$ SELECT s.id FROM anagrafiche.indirizzi_soggetti s
     WHERE s.soggetto_id = p_soggetto AND s.tipo_indirizzo_id = pg_temp.tipo('SEDEOP') $f$;

-- ============================================================
-- 1-6) Presidio
-- ============================================================
SELECT hasnt_function('anagrafiche', 'fn_copia_indirizzo_ruolo', ARRAY['bigint', 'bigint', 'text[]'],
                      '1) la firma a tre argomenti del verbo del ruolo non esiste piu''');

SELECT is((SELECT count(*)::int FROM pg_proc p
            WHERE p.pronamespace = 'anagrafiche'::regnamespace
              AND p.proname = 'fn_copia_indirizzo_ruolo'),
          1, '2) ... e resta una sola fn_copia_indirizzo_ruolo');

SELECT hasnt_function('anagrafiche', 'fn_check_copia_indirizzo_ruolo',
                      '3) la check di riga del ruolo e'' ritirata');

SELECT hasnt_view('anagrafiche', 'vw_indirizzi_ruolo_azioni',
                  '4) la vista di azioni del ruolo e'' ritirata');

SELECT ok(
    position('anagrafiche.fn_crea_copie_indirizzo_ruolo(' IN
             pg_get_functiondef('anagrafiche.fn_copia_indirizzo_ruolo(bigint, bigint, text[], bigint)'::regprocedure)) > 0
    AND position('anagrafiche.fn_crea_copie_indirizzo_ruolo(' IN
             pg_get_functiondef('anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo(bigint, bigint, text[], bigint)'::regprocedure)) > 0
    AND position('anagrafiche.fn_crea_indirizzo_ruolo(' IN
             pg_get_functiondef('anagrafiche.fn_crea_copie_indirizzo_ruolo(bigint, jsonb, bigint, text[])'::regprocedure)) > 0
    AND pg_get_functiondef('anagrafiche.fn_copia_indirizzo_ruolo(bigint, bigint, text[], bigint)'::regprocedure) !~* 'INSERT\s+INTO'
    AND pg_get_functiondef('anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo(bigint, bigint, text[], bigint)'::regprocedure) !~* 'INSERT\s+INTO'
    AND pg_get_functiondef('anagrafiche.fn_crea_copie_indirizzo_ruolo(bigint, jsonb, bigint, text[])'::regprocedure) !~* 'INSERT\s+INTO',
    '5) i due verbi scrivono dal BB, il BB dalla singolare: nessuna INSERT');

SELECT is((SELECT r.attivo FROM config.azioni_riga r WHERE r.codice_interno = 'COPIA_INDIRIZZO_RUOLO'),
          false, '6) l''azione COPIA_INDIRIZZO_RUOLO e'' spenta nel registro');

-- ============================================================
-- 7-21) Dalla riga del ruolo
-- ============================================================
DO $w$ BEGIN
    IF pg_temp.copia_r(pg_temp.ind_r('CON', NULL), ARRAY['POSTA'], (SELECT ist_a FROM _f)) IS NOT NULL THEN
        RAISE EXCEPTION 'fixture: copia CON (ruolo) -> POSTA (istanza) rifiutata';
    END IF;
END $w$;
SELECT isnt(pg_temp.ind_r('POSTA', (SELECT ist_a FROM _f)), NULL,
            '7) dal ruolo a una sua istanza: la riga nasce sull''istanza');
SELECT is(pg_temp.ind_r('POSTA', NULL), NULL, '8) ... e non sul ruolo');

DO $w$ BEGIN
    IF pg_temp.copia_r(pg_temp.ind_r('SPED', (SELECT ist_a FROM _f)), ARRAY['FORNITURA'], NULL) IS NOT NULL THEN
        RAISE EXCEPTION 'fixture: copia SPED (istanza) -> FORNITURA (ruolo) rifiutata';
    END IF;
END $w$;
SELECT isnt(pg_temp.ind_r('FORNITURA', NULL), NULL, '9) da un''istanza al ruolo');

SELECT is(pg_temp.copia_r(pg_temp.ind_r('SPED', (SELECT ist_a FROM _f)), ARRAY['SPED'], (SELECT ist2 FROM _f)),
          NULL,
          '10) da un''istanza a un''altra dello stesso soggetto: il tipo della sorgente, assente sulla destinazione, si copia');
SELECT is(pg_temp.forma_r(pg_temp.ind_r('SPED', (SELECT ist2 FROM _f))),
          pg_temp.forma_r(pg_temp.ind_r('SPED', (SELECT ist_a FROM _f))),
          '11) ... con tutte le colonne della forma');

SELECT is(pg_temp.copia_r(pg_temp.ind_r('SPED', (SELECT ist_a FROM _f)), ARRAY['CON'], NULL),
          'E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE',
          '12) un tipo presente sulla destinazione e assente sulla sorgente: E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE');

SELECT is(pg_temp.copia_r(pg_temp.ind_r('SPED', (SELECT ist_a FROM _f)), ARRAY['RES', 'CON'], NULL),
          'E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE',
          '13) due tipi, il secondo gia'' presente sulla destinazione: rifiutata');
SELECT is(pg_temp.ind_r('RES', NULL), NULL, '14) ... e il primo non e'' rimasto scritto (tutto o niente)');

SELECT is(pg_temp.copia_r(pg_temp.ind_r('CON', NULL), ARRAY['FATT'], (SELECT ist_b FROM _f)),
          'E_ISTANZA_ALTRO_SOGGETTO',
          '15) verso un''istanza di un altro soggetto: E_ISTANZA_ALTRO_SOGGETTO');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_copia_indirizzo_ruolo(%s, %s, ARRAY[''RES''], NULL::bigint)',
        (SELECT sr_b FROM _f), pg_temp.ind_r('CON', NULL))),
    'E_INDIRIZZO_RUOLO_NON_TROVATO',
    '16) la sorgente di un altro ruolo: E_INDIRIZZO_RUOLO_NON_TROVATO');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_copia_indirizzo_ruolo(-1, %s, ARRAY[''RES''], NULL::bigint)',
        pg_temp.ind_r('CON', NULL))),
    'E_SOGGETTO_RUOLO_NON_TROVATO',
    '17) un ruolo che non c''e'': E_SOGGETTO_RUOLO_NON_TROVATO');

SELECT is(pg_temp.copia_r(pg_temp.ind_r('CON', NULL), '{}'::text[], NULL),
          'E_SCRIPT_CHIAMATA_NON_VALIDA',
          '18) l''elenco vuoto: E_SCRIPT_CHIAMATA_NON_VALIDA');

CREATE TEMP TABLE _ids ON COMMIT DROP AS
SELECT x.id, x.ord
  FROM unnest(anagrafiche.fn_copia_indirizzo_ruolo(
           (SELECT sr_a FROM _f), pg_temp.ind_r('CON', NULL), ARRAY['RES', 'DOMFISC'], (SELECT ist2 FROM _f)))
       WITH ORDINALITY AS x(id, ord);

-- Le righe nuove si rileggono in un'istruzione dopo: quella che le scrive non le vede.
SELECT is(
    (SELECT string_agg(ti.codice_interno, ',' ORDER BY x.ord)
       FROM _ids x
       JOIN anagrafiche.indirizzi i ON i.id = x.id
       JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id
      WHERE i.istanza_utility_id = (SELECT ist2 FROM _f)),
    'RES,DOMFISC',
    '19) due tipi: gli id nell''ordine dei tipi, sulla destinazione');

-- La seconda istanza piena: si copia SPED nei tipi che le mancano.
DO $w$ BEGIN
    PERFORM anagrafiche.fn_copia_indirizzo_ruolo((SELECT sr_a FROM _f),
                pg_temp.ind_r('SPED', (SELECT ist2 FROM _f)), m.tipi, (SELECT ist2 FROM _f))
       FROM (SELECT array_agg(ti.codice_interno::text ORDER BY ti.id) AS tipi
               FROM config.tipi_indirizzi ti
              WHERE pg_temp.ind_r(ti.codice_interno, (SELECT ist2 FROM _f)) IS NULL) m
      WHERE m.tipi IS NOT NULL;
END $w$;

SELECT ok(
    NOT EXISTS (SELECT 1 FROM anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(
                                  (SELECT sr_a FROM _f), (SELECT ist2 FROM _f)) t WHERE t.ammesso)
    AND EXISTS (SELECT 1 FROM anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(
                                  (SELECT sr_a FROM _f), NULL) t WHERE t.ammesso),
    '20) destinazione piena e sorgente con tipi liberi: il picker della destinazione non ne ammette nessuno');

SELECT is(pg_temp.copia_r(pg_temp.ind_r('CON', NULL), ARRAY['FORNITURA'], (SELECT ist2 FROM _f)),
          'E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE',
          '21) ... e la copia la rifiuta la singolare col motivo del tipo');

-- ============================================================
-- 22-28) Dalla riga del soggetto del ruolo
-- ============================================================
DO $w$ BEGIN
    IF pg_temp.copia_s(pg_temp.ind_s((SELECT sogg_a FROM _f)), ARRAY['RES'], NULL) IS NOT NULL THEN
        RAISE EXCEPTION 'fixture: copia SEDEOP (soggetto) -> RES (ruolo) rifiutata';
    END IF;
END $w$;
SELECT is((pg_temp.forma_r(pg_temp.ind_r('RES', NULL)) ->> 'indirizzo_dettaglio_id')::bigint,
          (SELECT dettaglio_id FROM _el),
          '22) dal soggetto al ruolo: lo stesso dettaglio');

DO $w$ BEGIN
    IF pg_temp.copia_s(pg_temp.ind_s((SELECT sogg_a FROM _f)), ARRAY['FATT'], (SELECT ist_a FROM _f)) IS NOT NULL THEN
        RAISE EXCEPTION 'fixture: copia SEDEOP (soggetto) -> FATT (istanza) rifiutata';
    END IF;
END $w$;
SELECT isnt(pg_temp.ind_r('FATT', (SELECT ist_a FROM _f)), NULL,
            '23) dal soggetto a un''istanza del ruolo');

SELECT is(pg_temp.copia_s(pg_temp.ind_s((SELECT sogg_a FROM _f)), ARRAY['CON'], NULL),
          'E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE',
          '24) un tipo gia'' presente sulla destinazione: E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE');

SELECT is(pg_temp.copia_s(pg_temp.ind_s((SELECT sogg_b FROM _f)), ARRAY['DOMFISC'], NULL),
          'E_INDIRIZZO_SOGGETTO_NON_TROVATO',
          '25) la riga di un altro soggetto: E_INDIRIZZO_SOGGETTO_NON_TROVATO');

SELECT is(pg_temp.copia_s(pg_temp.ind_s((SELECT sogg_a FROM _f)), ARRAY['DOMFISC'], (SELECT ist_b FROM _f)),
          'E_ISTANZA_ALTRO_SOGGETTO',
          '26) verso un''istanza di un altro soggetto: E_ISTANZA_ALTRO_SOGGETTO');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo(-1, %s, ARRAY[''RES''], NULL::bigint)',
        pg_temp.ind_s((SELECT sogg_a FROM _f)))),
    'E_SOGGETTO_RUOLO_NON_TROVATO',
    '27) un ruolo che non c''e'': E_SOGGETTO_RUOLO_NON_TROVATO');

SELECT is(pg_temp.copia_s(pg_temp.ind_s((SELECT sogg_a FROM _f)), '{}'::text[], NULL),
          'E_SCRIPT_CHIAMATA_NON_VALIDA',
          '28) l''elenco vuoto: E_SCRIPT_CHIAMATA_NON_VALIDA');

SELECT * FROM finish();
ROLLBACK;
