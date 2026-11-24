-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Gli indirizzi obbligatori, giro 4: il requisito del ruolo sulla natura del
-- soggetto («vale il ripiego», Tid 2026-11-17) in una sede sola, e il
-- controllo che scatta anche quando si cancella un indirizzo, se ne cambia
-- il tipo (F-1) o cambia la natura del soggetto.
--   Brief: brief-db-fornitore-privato-indirizzi §8.4 (F-1), §9.5, giro 4.
--   ChangeSet 20261116-29 … -38.
--
-- Elenco test (plan 27):
--   presidi «il requisito sta in un posto solo»
--    1) i lettori leggono il requisito, nessuno la matrice del ruolo
--    2) i due trigger dei titolari chiamano i guard, che non hanno copie
--    3) i tre constraint trigger nuovi: differiti, sugli eventi giusti
--   il guard, chiamato da solo
--    4) ruolo o soggetto che non esistono: tace
--    5) id NULL: E_SCRIPT_CHIAMATA_NON_VALIDA, sui due layer
--   F-1, layer RUOLO (cliente: fatturazione, ripiego domicilio fiscale)
--    6) cancellare l'unica fatturazione: rifiutato, con la frase del ruolo
--    7) cambiarle il tipo: rifiutato
--    8) col domicilio fiscale, la fatturazione si cancella (vale il ripiego)
--    9) sostituire nella stessa transazione: passa
--   10) cancellare il ruolo coi suoi indirizzi: passa
--   F-1, layer SOGGETTO (societa': sede legale)
--   11) cancellare la sede legale: rifiutato, col codice del soggetto
--   12) cambiarle il tipo: rifiutato
--   13) sostituirla nella stessa transazione: passa
--   la regola del ripiego (matrice costruita: sede legale obbligatoria per il
--   fornitore, ripiego domicilio fiscale)
--   14) il requisito sulla societa': il tipo col ripiego
--   15) il requisito sul privato: il ripiego, da solo
--   16) natura NULL: il tipo col ripiego
--   17) obbligatorio per il ruolo: sul privato il ripiego si', il tipo no
--   18) il fornitore privato nasce completo
--   19) ... la copia gli scrive il domicilio fiscale
--   20) il picker del ruolo da assegnare: domicilio fiscale obbligatorio
--   21) cancellare quel domicilio fiscale: rifiutato, la frase nomina solo lui
--   22) ripiego che la natura vieta anche lui: la riga non chiede niente
--   23) ... e il privato toglie il domicilio fiscale del ruolo
--   il cambio di natura (righe costruite: consegna obbligatoria per il
--   fornitore, vietata al privato)
--   24) sul privato la riga non chiede niente
--   25) privato verso ditta senza consegna sul ruolo: rifiutato
--   26) ... la frase nomina il ruolo e la consegna
--   27) ... con la consegna scritta nella stessa transazione: passa
--
-- Scopo:
--  - ogni ramo si COSTRUISCE: soggetti dai builder (sulle madri), ruoli dalle
--    madri dei flussi (fn_crea_fornitore, la fixture del ruolo), le righe di
--    matrice che servono le scrive il test (regola zero). Il seed fa da
--    catalogo dei tipi, dei ruoli e delle nature.
--  - i rifiuti si asseriscono sul CODICE (dbops.fn_pgtap_codice_errore), la
--    frase dove dice che cosa manca.
--  - i trigger nuovi sono differiti: il file gira IMMEDIATE (scattano a fine
--    istruzione) e apre la finestra solo dove prova la transazione intera.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(27);

-- ============================================================
-- Fixture: cataloghi e helper
-- ============================================================
CREATE FUNCTION pg_temp.tipo(p_codice config.tipi_indirizzi.codice_interno%TYPE)
RETURNS config.tipi_indirizzi.id%TYPE LANGUAGE sql AS
$f$ SELECT id FROM config.tipi_indirizzi WHERE codice_interno = p_codice $f$;

CREATE FUNCTION pg_temp.nome(p_codice config.tipi_indirizzi.codice_interno%TYPE)
RETURNS text LANGUAGE sql AS  -- la descrizione fra caporali, come la frase la scrive
$f$ SELECT '«' || descrizione || '»' FROM config.tipi_indirizzi WHERE codice_interno = p_codice $f$;

CREATE FUNCTION pg_temp.natura(p_codice config.tipi_soggetto_dettaglio.codice_interno%TYPE)
RETURNS config.tipi_soggetto_dettaglio.id%TYPE LANGUAGE sql AS
$f$ SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = p_codice $f$;

CREATE FUNCTION pg_temp.ruolo(p_codice config.tipi_ruoli.codice_interno%TYPE)
RETURNS config.tipi_ruoli.id%TYPE LANGUAGE sql AS
$f$ SELECT id FROM config.tipi_ruoli WHERE codice_interno = p_codice $f$;

-- Una riga di matrice del ruolo nello stato voluto (l'id non ha default).
CREATE FUNCTION pg_temp.matrice_ruolo(
    p_ruolo   config.tipi_ruoli.codice_interno%TYPE,
    p_tipo    config.tipi_indirizzi.codice_interno%TYPE,
    p_obbl    config.tipi_ruolo_tipi_indirizzo.obbligatorio%TYPE,
    p_ripiego config.tipi_indirizzi.codice_interno%TYPE)
RETURNS void LANGUAGE plpgsql AS $f$
BEGIN
    DELETE FROM config.tipi_ruolo_tipi_indirizzo
     WHERE tipo_ruolo_id = pg_temp.ruolo(p_ruolo) AND tipo_indirizzo_id = pg_temp.tipo(p_tipo);
    INSERT INTO config.tipi_ruolo_tipi_indirizzo
           (id, tipo_ruolo_id, tipo_indirizzo_id, obbligatorio, fallback_tipo_indirizzo_id, attivo)
    VALUES ((SELECT COALESCE(max(id), 0) + 1 FROM config.tipi_ruolo_tipi_indirizzo),
            pg_temp.ruolo(p_ruolo), pg_temp.tipo(p_tipo), p_obbl, pg_temp.tipo(p_ripiego), true);
END $f$;

-- Il requisito come testo: «TIPO>RIPIEGO» per riga, nell'ordine della funzione.
CREATE FUNCTION pg_temp.requisito(
    p_ruolo  config.tipi_ruoli.codice_interno%TYPE,
    p_natura config.tipi_soggetto_dettaglio.id%TYPE)
RETURNS text LANGUAGE sql AS $f$  -- un testo composto, non il riflesso di una colonna
    SELECT string_agg(t.codice_interno || '>' || COALESCE(r.codice_interno, '-'), ','
                      ORDER BY o.tipo_indirizzo_id)
      FROM anagrafiche.fn_indirizzi_obbligatori_ruolo(
               pg_temp.ruolo(p_ruolo), p_natura, script.fn_data_operativa()) o
      JOIN config.tipi_indirizzi t ON t.id = o.tipo_indirizzo_id
      LEFT JOIN config.tipi_indirizzi r ON r.id = o.ripiego_tipo_indirizzo_id
$f$;

CREATE FUNCTION pg_temp.messaggio_di(p_sql text) RETURNS text LANGUAGE plpgsql AS $f$
DECLARE v_msg text;  -- valore della diagnostica
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
    RETURN v_msg;
END $f$;

-- Un indirizzo libero valido per l'Italia, del tipo dato.
CREATE FUNCTION pg_temp.el(p_tipo config.tipi_indirizzi.codice_interno%TYPE,
                           p_via  anagrafiche.indirizzi.indirizzo_libero%TYPE)
RETURNS jsonb LANGUAGE sql AS $f$
    SELECT jsonb_build_object('tipo_indirizzo_codice_interno', p_tipo,
                              'indirizzo_libero',              p_via,
                              'stato_id',                      script.fn_stato_id_da_iso2('IT'))
           || (SELECT jsonb_strip_nulls(to_jsonb(frm))
                 FROM dbops.fn_pgtap_indirizzo_libero_forma(script.fn_stato_id_da_iso2('IT')) frm)
$f$;

-- La societa' (sede legale sul soggetto) e il privato, dai builder sulle
-- madri; ognuno richiude da se' la finestra differita.
CREATE TEMP TABLE _s ON COMMIT DROP AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('pgTAP obbligatori giro 4 societa''') AS sc,
       dbops.fn_pgtap_crea_soggetto_pf('Obbligatori', 'Privato', pg_temp.natura('PR')) AS pr;

-- ============================================================
-- 1-3) Presidi
-- ============================================================
SELECT ok(
    pg_get_functiondef('anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(integer, bigint, integer, date)'::regprocedure)
        LIKE '%fn_indirizzi_obbligatori_ruolo(%'
    AND pg_get_functiondef('anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(integer, bigint, integer, date)'::regprocedure)
        !~ '(FROM|JOIN)\s+(config\.)?tipi_ruolo_tipi_indirizzo\M'
    -- rev 2026-11-17 (giro 5, 20261116-41): il guard arriva al requisito
    --   attraverso i mancanti del ruolo (fn_indirizzi_obbligatori_mancanti_ruolo).
    AND pg_get_functiondef('anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(bigint, uuid, integer)'::regprocedure)
        LIKE '%anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo(%'
    -- ⚠️ BEGIN ATOMIC: pg_get_functiondef stampa i nomi rispetto al search_path
    --   di chi legge (linee-guida-sql §5c); col runner lo schema non c'e'.
    AND pg_get_functiondef('anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo(bigint, bigint, date)'::regprocedure)
        LIKE '%fn_indirizzi_obbligatori_ruolo(%'
    AND pg_get_functiondef('anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(bigint, uuid, integer)'::regprocedure)
        !~ '(FROM|JOIN)\s+(config\.)?tipi_ruolo_tipi_indirizzo\M'
    AND pg_get_functiondef('dbops.fn_pgtap_crea_soggetto_ruolo(uuid, character varying, integer)'::regprocedure)
        LIKE '%anagrafiche.fn_indirizzi_obbligatori_ruolo(%'
    AND pg_get_functiondef('dbops.fn_pgtap_crea_soggetto_ruolo(uuid, character varying, integer)'::regprocedure)
        !~ '(FROM|JOIN)\s+(config\.)?tipi_ruolo_tipi_indirizzo\M',
    '1) i lettori leggono il requisito, nessuno la matrice del ruolo');

SELECT ok(
    pg_get_functiondef('anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required()'::regprocedure)
        LIKE '%anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(%'
    AND pg_get_functiondef('anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required()'::regprocedure)
        !~ '(FROM|JOIN)\s+(config\.)?tipi_ruolo_tipi_indirizzo\M'
    AND pg_get_functiondef('anagrafiche.trgfn_soggetti_guard_indirizzi_required()'::regprocedure)
        LIKE '%anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(%'
    AND pg_get_functiondef('anagrafiche.trgfn_soggetti_guard_indirizzi_required()'::regprocedure)
        !~ '(FROM|JOIN)\s+(config\.)?tipi_soggetto_dettaglio_tipi_indirizzo\M',
    '2) i due trigger dei titolari chiamano i guard, senza copie della regola');

-- Una riga per montaggio, come testo: tabella, funzione, differito,
-- inizialmente differito, e gli eventi (D)elete, (U)pdate, (I)nsert.
SELECT is(
    (SELECT string_agg(format('%s.%s:%s:%s%s:%s%s%s', n.nspname, c.relname, p.proname,
                              t.tgdeferrable, t.tginitdeferred,
                              CASE WHEN t.tgtype & 8 <> 0 THEN 'D' ELSE '' END,
                              CASE WHEN t.tgtype & 16 <> 0 THEN 'U' ELSE '' END,
                              CASE WHEN t.tgtype & 4 <> 0 THEN 'I' ELSE '' END),
                       ' ' ORDER BY p.proname)
       FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
       JOIN pg_proc p ON p.oid = t.tgfoid
      WHERE p.oid IN ('anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo()'::regprocedure,
                      'anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto()'::regprocedure,
                      'anagrafiche.trgfn_soggetti_guard_obbligatori_ruoli()'::regprocedure)),
    'anagrafiche.indirizzi:trgfn_indirizzi_guard_obbligatori_ruolo:tt:DU'
    || ' anagrafiche.indirizzi_soggetti:trgfn_indirizzi_soggetti_guard_obbligatori_soggetto:tt:DU'
    || ' anagrafiche.soggetti:trgfn_soggetti_guard_obbligatori_ruoli:tt:U',
    '3) i tre constraint trigger nuovi: differiti, una volta sola, sugli eventi giusti');

-- ============================================================
-- 4-5) Il guard, chiamato da solo
-- ============================================================
SELECT lives_ok(
    $$SELECT anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(999999999999, NULL::uuid),
             anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(gen_random_uuid(), NULL::uuid)$$,
    '4) ruolo o soggetto che non esistono (cancellati nella transazione): tace');

SELECT is(
    dbops.fn_pgtap_codice_errore('SELECT anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(NULL, NULL)')
        || '/' || dbops.fn_pgtap_codice_errore('SELECT anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(NULL, NULL)'),
    'E_SCRIPT_CHIAMATA_NON_VALIDA/E_SCRIPT_CHIAMATA_NON_VALIDA',
    '5) id NULL: E_SCRIPT_CHIAMATA_NON_VALIDA, sui due layer');

-- ============================================================
-- 6-10) F-1, layer RUOLO: il cliente della societa'
-- ============================================================
-- Il ruolo dalla fixture: nasce con la sola fatturazione (il primo tipo del
-- requisito, sul seed: fatturazione col ripiego domicilio fiscale).
CREATE TEMP TABLE _r ON COMMIT DROP AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s.sc, 'CL') AS cl
  FROM _s s;

SELECT is(
    pg_temp.messaggio_di(format(
        'DELETE FROM anagrafiche.indirizzi WHERE soggetto_ruolo_id = %s AND tipo_indirizzo_id = %s',
        (SELECT cl FROM _r), pg_temp.tipo('FATT'))),
    format('Il ruolo %s richiede l''indirizzo %s / %s.',
           (SELECT descrizione FROM config.tipi_ruoli WHERE codice_interno = 'CL'),
           pg_temp.nome('FATT'), pg_temp.nome('DOMFISC')),
    '6) cancellare l''unica fatturazione: rifiutato, la frase nomina il ruolo, il tipo e il ripiego');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE anagrafiche.indirizzi SET tipo_indirizzo_id = %s WHERE soggetto_ruolo_id = %s AND tipo_indirizzo_id = %s',
        pg_temp.tipo('SPED'), (SELECT cl FROM _r), pg_temp.tipo('FATT'))),
    'E_INDIRIZZO_OBBLIGATORIO_MANCANTE',
    '7) cambiare tipo all''unica fatturazione: rifiutato');

SELECT anagrafiche.fn_crea_indirizzo_ruolo(r.cl, pg_temp.el('DOMFISC', 'Via Cliente pgTAP 2')) FROM _r r;

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'DELETE FROM anagrafiche.indirizzi WHERE soggetto_ruolo_id = %s AND tipo_indirizzo_id = %s',
        (SELECT cl FROM _r), pg_temp.tipo('FATT'))),
    NULL,
    '8) col domicilio fiscale sul ruolo, la fatturazione si cancella (vale il ripiego)');

-- Sostituire: cancella e riscrivi, nella stessa transazione.
SET CONSTRAINTS ALL DEFERRED;
DELETE FROM anagrafiche.indirizzi
 WHERE soggetto_ruolo_id = (SELECT cl FROM _r) AND tipo_indirizzo_id = pg_temp.tipo('DOMFISC');
SELECT anagrafiche.fn_crea_indirizzo_ruolo(r.cl, pg_temp.el('FATT', 'Via Cliente pgTAP 3')) FROM _r r;
SELECT lives_ok('SET CONSTRAINTS ALL IMMEDIATE',
    '9) sostituire l''obbligatorio nella stessa transazione: passa');

-- Il ruolo coi suoi indirizzi: la FK e' NO ACTION, prima gli indirizzi.
SELECT lives_ok(
    format($$WITH via AS (DELETE FROM anagrafiche.indirizzi WHERE soggetto_ruolo_id = %1$s)
             DELETE FROM anagrafiche.soggetti_ruoli WHERE id = %1$s$$,
           (SELECT cl FROM _r)),
    '10) cancellare il ruolo coi suoi indirizzi: passa (il ruolo che non c''e'' piu'' tace)');

-- ============================================================
-- 11-13) F-1, layer SOGGETTO: la sede legale della societa'
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'DELETE FROM anagrafiche.indirizzi_soggetti WHERE soggetto_id = %L AND tipo_indirizzo_id = %s',
        (SELECT sc FROM _s), pg_temp.tipo('SEDELEG'))),
    'E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO',
    '11) cancellare la sede legale della societa'': rifiutato, col codice del soggetto');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE anagrafiche.indirizzi_soggetti SET tipo_indirizzo_id = %s WHERE soggetto_id = %L AND tipo_indirizzo_id = %s',
        pg_temp.tipo('SEDEOP'), (SELECT sc FROM _s), pg_temp.tipo('SEDELEG'))),
    'E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO',
    '12) cambiarle il tipo: rifiutato');

SET CONSTRAINTS ALL DEFERRED;
DELETE FROM anagrafiche.indirizzi_soggetti
 WHERE soggetto_id = (SELECT sc FROM _s) AND tipo_indirizzo_id = pg_temp.tipo('SEDELEG');
SELECT anagrafiche.fn_crea_indirizzo_soggetto(s.sc, pg_temp.el('SEDELEG', 'Via Societa pgTAP 2')) FROM _s s;
SELECT lives_ok('SET CONSTRAINTS ALL IMMEDIATE',
    '13) sostituire la sede legale nella stessa transazione: passa');

-- ============================================================
-- 14-22) La regola del ripiego, su una riga costruita
-- ============================================================
-- Per il fornitore: sede legale obbligatoria col ripiego domicilio fiscale,
-- che il ruolo ammette (riga facoltativa). Il privato non ammette la sede
-- legale, ammette il domicilio fiscale; la societa' li ammette tutti e due.
SELECT pg_temp.matrice_ruolo('FO', 'DOMFISC', false, NULL);
SELECT pg_temp.matrice_ruolo('FO', 'SEDELEG', true, 'DOMFISC');

SELECT is(pg_temp.requisito('FO', pg_temp.natura('SC')),
          'SEDELEG>DOMFISC,FATT>SEDELEG',
          '14) il requisito sulla societa'': il tipo col suo ripiego, riga per riga');

SELECT is(pg_temp.requisito('FO', pg_temp.natura('PR')),
          'DOMFISC>-,FATT>-',
          '15) sul privato: al posto della sede legale il domicilio fiscale, da solo; la fatturazione senza il ripiego che la natura vieta');

SELECT is(pg_temp.requisito('FO', NULL),
          'SEDELEG>DOMFISC,FATT>SEDELEG',
          '16) natura NULL: la natura non conta');

SELECT ok(
    anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(
        pg_temp.ruolo('FO'), pg_temp.natura('PR'), pg_temp.tipo('DOMFISC'), script.fn_data_operativa())
    AND NOT anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(
        pg_temp.ruolo('FO'), pg_temp.natura('PR'), pg_temp.tipo('SEDELEG'), script.fn_data_operativa()),
    '17) obbligatorio per il ruolo, sul privato: il ripiego si'', il tipo che la natura vieta no');

-- Il fornitore privato dal verbo del flusso Fornitori, con la sola fatturazione.
SET CONSTRAINTS ALL DEFERRED;
CREATE TEMP TABLE _fo ON COMMIT DROP AS
SELECT (SELECT soggetto_ruolo_id FROM anagrafiche.fn_crea_fornitore(
            s.pr, '{}'::jsonb, NULL,
            jsonb_build_array(pg_temp.el('FATT', 'Via Privato pgTAP 2')))) AS pr
  FROM _s s;
SELECT lives_ok('SET CONSTRAINTS ALL IMMEDIATE',
    '18) il fornitore privato nasce completo');

SELECT is(
    (SELECT count(*)::integer FROM anagrafiche.indirizzi i
      WHERE i.soggetto_ruolo_id = (SELECT pr FROM _fo)
        AND i.tipo_indirizzo_id = pg_temp.tipo('DOMFISC')),
    1,
    '19) ... la copia degli obbligatori gli ha scritto il domicilio fiscale');

SELECT results_eq(
    format($$SELECT ti.codice_interno::text, p.ammesso, p.obbligatorio
               FROM anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(%s, %L) p
               JOIN config.tipi_indirizzi ti ON ti.id = p.tipo_indirizzo_id
              WHERE ti.codice_interno IN ('DOMFISC', 'SEDELEG')
              ORDER BY ti.codice_interno$$,
           pg_temp.ruolo('FO'), (SELECT pr FROM _s)),
    $$VALUES ('DOMFISC'::text, true, true), ('SEDELEG'::text, false, false)$$,
    '20) il picker del ruolo da assegnare, sul privato: domicilio fiscale obbligatorio, sede legale spenta');

SELECT is(
    pg_temp.messaggio_di(format(
        'DELETE FROM anagrafiche.indirizzi WHERE soggetto_ruolo_id = %s AND tipo_indirizzo_id = %s',
        (SELECT pr FROM _fo), pg_temp.tipo('DOMFISC'))),
    format('Il ruolo %s richiede l''indirizzo %s.',
           (SELECT descrizione FROM config.tipi_ruoli WHERE codice_interno = 'FO'), pg_temp.nome('DOMFISC')),
    '21) cancellare quel domicilio fiscale: rifiutato, la frase nomina solo il ripiego');

-- Il ripiego che la natura vieta anche lui: la sede operativa (il ruolo la
-- ammette, il privato no).
SELECT pg_temp.matrice_ruolo('FO', 'SEDEOP', false, NULL);
SELECT pg_temp.matrice_ruolo('FO', 'SEDELEG', true, 'SEDEOP');

SELECT is(pg_temp.requisito('FO', pg_temp.natura('PR')),
          'FATT>-',
          '22) tipo e ripiego vietati dalla natura: la riga non chiede niente');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'DELETE FROM anagrafiche.indirizzi WHERE soggetto_ruolo_id = %s AND tipo_indirizzo_id = %s',
        (SELECT pr FROM _fo), pg_temp.tipo('DOMFISC'))),
    NULL,
    '23) ... e il privato toglie il domicilio fiscale dal ruolo');

-- ============================================================
-- 24-27) Il cambio di natura
-- ============================================================
-- La riga del fornitore torna facoltativa; nasce la consegna obbligatoria,
-- senza ripiego. Il privato, per questo test, non ammette la consegna (riga
-- della natura spenta); la ditta individuale si'. Il fornitore privato (18)
-- non ce l'ha e non la deve; diventando ditta, la deve.
SELECT pg_temp.matrice_ruolo('FO', 'SEDELEG', false, NULL);
SELECT pg_temp.matrice_ruolo('FO', 'CON', true, NULL);
UPDATE config.tipi_soggetto_dettaglio_tipi_indirizzo
   SET attivo = false
 WHERE tipo_soggetto_dettaglio_id = pg_temp.natura('PR') AND tipo_indirizzo_id = pg_temp.tipo('CON');

-- Il cambio di natura: la partita IVA la ditta la pretende, e il privato non
-- l'ha ancora (si scrive, non si cambia).
CREATE TEMP TABLE _cambio ON COMMIT DROP AS
SELECT format('UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = %s, partita_iva = %L WHERE id = %L',
              pg_temp.natura('DI'), dbops.fn_pgtap_piva_libera(), (SELECT pr FROM _s)) AS q;

SELECT is(pg_temp.requisito('FO', pg_temp.natura('PR')),
          'FATT>-',
          '24) sul privato la consegna non si chiede: la natura la vieta');

SELECT is(
    dbops.fn_pgtap_codice_errore((SELECT q FROM _cambio)),
    'E_INDIRIZZO_OBBLIGATORIO_MANCANTE',
    '25) privato verso ditta, senza consegna sul ruolo: rifiutato (nessun indirizzo e'' cambiato)');

SELECT is(
    pg_temp.messaggio_di((SELECT q FROM _cambio)),
    format('Il ruolo %s richiede l''indirizzo %s.',
           (SELECT descrizione FROM config.tipi_ruoli WHERE codice_interno = 'FO'), pg_temp.nome('CON')),
    '26) ... la frase nomina il ruolo e la consegna');

SET CONSTRAINTS ALL DEFERRED;
DO $cambio$ BEGIN EXECUTE (SELECT q FROM _cambio); END $cambio$;
SELECT anagrafiche.fn_crea_indirizzo_ruolo(f.pr, pg_temp.el('CON', 'Via Privato pgTAP 5')) FROM _fo f;
SELECT lives_ok('SET CONSTRAINTS ALL IMMEDIATE',
    '27) ... con la consegna scritta nella stessa transazione: passa');

SELECT * FROM finish();
ROLLBACK;
