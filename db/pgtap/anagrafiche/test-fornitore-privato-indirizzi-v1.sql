-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il privato puo' essere fornitore senza inventarsi una sede legale, e gli
-- indirizzi del RUOLO rispettano la natura del soggetto: il guard, la check
-- della madre singolare, i due picker, l'auto-clone, il cambio di natura.
--   Brief: brief-db-fornitore-privato-indirizzi §4.2, §8.2, §8.3-bis (la (C)),
--   D-4 di Tid del 2026-11-16; giri 1 e 2. ChangeSet 20261116-17 … -21;
--   riga 13 di config/tipi_ruolo_tipi_indirizzo.csv; codice
--   E_CAMBIO_NATURA_INDIRIZZI_RUOLO_NON_AMMESSI in config/codici_errore.csv e
--   config/messaggi_errore.csv.
--
-- Elenco test (plan 24):
--   la nascita
--    1) privato, ditta individuale e societa' fornitori: tutti completi
--   presidi «la regola sta in un posto solo»
--    2) i tre lettori di «obbligatorio per il ruolo» leggono il building block
--    3) il guard del ruolo legge il predicato della natura, non la matrice
--    4) una firma sola per nome, con la natura e il soggetto in coda
--   il contratto del seed (la (C))
--    5) per il fornitore la sede legale non e' obbligatoria, e resta ammessa
--   il building block (matrice costruita: SEDEOP obbligatorio per FO)
--    6) natura che ammette il tipo: obbligatorio
--    7) natura che non lo ammette: non obbligatorio; natura NULL: obbligatorio
--   la check sul contesto
--    8) privato e sede legale: il motivo della natura, col codice del guard del soggetto
--    9) ... coi valori natura e tipo, per descrizione
--   10) natura NULL: nessun motivo
--   il fornitore privato, dal verbo del flusso Fornitori
--   11) il privato ha la fatturazione sul ruolo e nessuna sede legale
--   12) la singolare: sede legale sul ruolo di un privato, rifiutata
--   13) la strada che salta la madre: parla il guard, con la frase della natura
--   14) la ditta individuale ha la sede legale sul ruolo (ammessa)
--   i picker
--   15) sul ruolo salvato del privato: la sede legale spenta col codice della singolare
--   16) sul tipo di ruolo, col privato: sede legale spenta, fatturazione obbligatoria
--   17) sul tipo di ruolo, soggetto non ancora scelto: la sede legale ammessa
--   18) sul tipo di ruolo, soggetto che non c'e': nessuna riga
--   l'auto-clone (SEDEOP obbligatorio costruito)
--   19) sul privato: SEDEOP non si copia
--   20) sulla societa': SEDEOP si copia
--   il cambio di natura (D-4)
--   21) ditta fornitore con la sede legale sul ruolo verso privato: il motivo del ruolo
--   22) ... coi valori natura, tipo, ruolo, quanti
--   23) ... e l'UPDATE e' rifiutato con la sua frase
--   24) tolta la sede legale dal ruolo, il cambio non ha piu' motivi
--
-- Scopo:
--  - ogni ramo si COSTRUISCE: i soggetti nascono dai builder
--    (fn_pgtap_crea_soggetto_pf e _pg, sulle madri), i fornitori dalla madre
--    fn_crea_fornitore; la riga obbligatoria che la natura del privato non
--    ammette (SEDEOP per FO) la scrive il test (regola zero: niente si
--    appoggia alle righe di oggi). Il seed serve come catalogo dei tipi e
--    delle nature, e il 5) ne asserisce il contratto deciso (la (C)).
--  - i rifiuti si asseriscono sul CODICE (dbops.fn_pgtap_codice_errore); la
--    frase solo dove parla il guard da una strada che salta la madre.
-- Il requisito degli obbligatori sulla natura (il ripiego, il guard alla
--   cancellazione) lo prova test-indirizzi-obbligatori-ripiego-e-cancellazione-v1
--   (giro 4 del brief, 20261116-29 … -38).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(24);

-- ============================================================
-- Fixture: cataloghi e helper
-- ============================================================
CREATE FUNCTION pg_temp.tipo(p_codice config.tipi_indirizzi.codice_interno%TYPE)
RETURNS config.tipi_indirizzi.id%TYPE LANGUAGE sql AS
$f$ SELECT id FROM config.tipi_indirizzi WHERE codice_interno = p_codice $f$;

CREATE FUNCTION pg_temp.natura(p_codice config.tipi_soggetto_dettaglio.codice_interno%TYPE)
RETURNS config.tipi_soggetto_dettaglio.id%TYPE LANGUAGE sql AS
$f$ SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = p_codice $f$;

CREATE FUNCTION pg_temp.codici(p_motivi jsonb) RETURNS text[] LANGUAGE sql AS
$f$ SELECT COALESCE(array_agg(m ->> 'codice' ORDER BY o), '{}')
      FROM jsonb_array_elements(p_motivi) WITH ORDINALITY AS e(m, o) $f$;

-- Una riga di matrice del ruolo nello stato voluto (l'id non ha default).
CREATE FUNCTION pg_temp.matrice_ruolo(
    p_tipo_ruolo config.tipi_ruolo_tipi_indirizzo.tipo_ruolo_id%TYPE,
    p_tipo       config.tipi_indirizzi.codice_interno%TYPE,
    p_obbl       config.tipi_ruolo_tipi_indirizzo.obbligatorio%TYPE)
RETURNS void LANGUAGE plpgsql AS $f$
DECLARE v_tipo config.tipi_indirizzi.id%TYPE :=
            (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = p_tipo);
BEGIN
    DELETE FROM config.tipi_ruolo_tipi_indirizzo
     WHERE tipo_ruolo_id = p_tipo_ruolo AND tipo_indirizzo_id = v_tipo;
    INSERT INTO config.tipi_ruolo_tipi_indirizzo
           (id, tipo_ruolo_id, tipo_indirizzo_id, obbligatorio, attivo)
    VALUES ((SELECT COALESCE(max(id), 0) + 1 FROM config.tipi_ruolo_tipi_indirizzo),
            p_tipo_ruolo, v_tipo, p_obbl, true);
END $f$;

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
CREATE FUNCTION pg_temp.el(p_tipo config.tipi_indirizzi.codice_interno%TYPE, p_via text)
RETURNS jsonb LANGUAGE sql AS $f$
    SELECT jsonb_build_object('tipo_indirizzo_codice_interno', p_tipo,
                              'indirizzo_libero',              p_via,
                              'stato_id',                      script.fn_stato_id_da_iso2('IT'))
           || (SELECT jsonb_strip_nulls(to_jsonb(frm))
                 FROM dbops.fn_pgtap_indirizzo_libero_forma(script.fn_stato_id_da_iso2('IT')) frm)
$f$;

-- ⚠️ Le colonne delle tabelle temporanee hanno il tipo esplicito: %TYPE nel DDL
--   di tabella non si scrive (linee-guida-sql §5g). Ognuna e' il tipo della
--   colonna di cui e' il riflesso.
CREATE TEMP TABLE _ref ON COMMIT DROP AS
SELECT (SELECT id FROM config.tipi_ruoli WHERE codice_interno = 'FO') AS fo,
       pg_temp.natura('PR') AS pr,
       pg_temp.natura('DI') AS di,
       (SELECT COALESCE(descrizione, codice_interno) FROM config.tipi_soggetto_dettaglio
         WHERE codice_interno = 'PR') AS pr_nome,
       (SELECT descrizione FROM config.tipi_indirizzi WHERE codice_interno = 'SEDELEG') AS sedeleg_nome,
       (SELECT descrizione FROM config.tipi_ruoli WHERE codice_interno = 'FO') AS fo_nome;

-- La societa', il privato e la ditta individuale, completi coi loro obbligatori
-- sul soggetto: dai due builder, che li costruiscono dalle madri e richiudono
-- da se' la finestra differita (rev 2026-11-17, riga 7-bis, 20261116-22).
CREATE TEMP TABLE _s ON COMMIT DROP AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('pgTAP fornitore privato societa''') AS sc,
       dbops.fn_pgtap_crea_soggetto_pf('Fornitore', 'Privato', pg_temp.natura('PR')) AS pr,
       dbops.fn_pgtap_crea_soggetto_pf('Fornitore', 'Ditta', pg_temp.natura('DI')) AS di;

-- I ruoli nascono nella finestra differita: il guard degli obbligatori del
-- ruolo giudica alla richiusura (1).
SET CONSTRAINTS ALL DEFERRED;

-- I tre fornitori, dal verbo del flusso Fornitori: il privato con la sola
-- fatturazione, la ditta con fatturazione e sede legale, la societa' con la
-- sola sede legale (la fatturazione la clona il verbo).
CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT (SELECT soggetto_ruolo_id FROM anagrafiche.fn_crea_fornitore(
            s.pr, '{}'::jsonb, NULL,
            jsonb_build_array(pg_temp.el('FATT', 'Via Privato pgTAP 2')))) AS sr_pr,
       (SELECT soggetto_ruolo_id FROM anagrafiche.fn_crea_fornitore(
            s.di, '{}'::jsonb, NULL,
            jsonb_build_array(pg_temp.el('FATT', 'Via Ditta pgTAP 2'),
                              pg_temp.el('SEDELEG', 'Via Ditta pgTAP 3')))) AS sr_di,
       (SELECT soggetto_ruolo_id FROM anagrafiche.fn_crea_fornitore(
            s.sc, '{}'::jsonb, NULL,
            jsonb_build_array(pg_temp.el('SEDELEG', 'Via Societa pgTAP 3')))) AS sr_sc
  FROM _s s;

-- ============================================================
-- 1) Il requisito degli obbligatori, a fine finestra
-- ============================================================
-- I guard differiti di soggetto e ruolo giudicano qui, sulla matrice di
-- questo momento: per questo la riga SEDEOP obbligatoria si costruisce dopo
-- (6-7), quando i tre ruoli sono gia' giudicati.
SELECT lives_ok('SET CONSTRAINTS ALL IMMEDIATE',
    '1) privato, ditta individuale e societa'' fornitori: tutti completi');

-- ============================================================
-- 2-4) Presidi
-- ============================================================
SELECT ok(
    pg_get_functiondef('anagrafiche.fn_crea_indirizzi_ruolo(bigint, jsonb)'::regprocedure)
        LIKE '%anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(%'
    AND pg_get_functiondef('anagrafiche.fn_crea_indirizzi_ruolo(bigint, jsonb)'::regprocedure)
        NOT LIKE '%fn_tipo_indirizzo_ammesso_per_ruolo%'
    AND pg_get_functiondef('anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(bigint, bigint)'::regprocedure)
        LIKE '%fn_tipo_indirizzo_obbligatorio_per_ruolo(%'
    AND pg_get_functiondef('anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(bigint, bigint)'::regprocedure)
        NOT LIKE '%tipi_ruolo_tipi_indirizzo%'
    AND pg_get_functiondef('anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(integer, uuid)'::regprocedure)
        LIKE '%fn_tipo_indirizzo_obbligatorio_per_ruolo(%'
    AND pg_get_functiondef('anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(integer, uuid)'::regprocedure)
        NOT LIKE '%tipi_ruolo_tipi_indirizzo%',
    '2) i tre lettori di «obbligatorio per il ruolo» leggono il building block');

SELECT ok(
    pg_get_functiondef('anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo()'::regprocedure)
        LIKE '%anagrafiche.fn_tipo_indirizzo_ammesso_per_natura(%'
    AND pg_get_functiondef('anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo()'::regprocedure)
        NOT LIKE '%tipi_soggetto_dettaglio_tipi_indirizzo%',
    '3) il guard del ruolo legge il predicato della natura, non la matrice');

SELECT is(
    (SELECT array_agg(p.proname || '/' || p.pronargs ORDER BY p.proname)
       FROM pg_proc p
      WHERE p.pronamespace = 'anagrafiche'::regnamespace
        AND p.proname IN ('fn_check_tipo_indirizzo_ruolo_su_contesto',
                          'fn_tipi_indirizzo_proponibili_tipo_ruolo',
                          'fn_tipi_indirizzo_proponibili_ruolo',
                          'fn_tipo_indirizzo_obbligatorio_per_ruolo')),
    ARRAY['fn_check_tipo_indirizzo_ruolo_su_contesto/6',
          'fn_tipi_indirizzo_proponibili_ruolo/2',
          'fn_tipi_indirizzo_proponibili_tipo_ruolo/2',
          'fn_tipo_indirizzo_obbligatorio_per_ruolo/4'],
    '4) una firma sola per nome, con la natura e il soggetto in coda');

-- ============================================================
-- 5) Il contratto del seed: la (C)
-- ============================================================
SELECT ok(
    NOT anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(
            (SELECT fo FROM _ref), NULL, pg_temp.tipo('SEDELEG'), script.fn_data_operativa())
    AND anagrafiche.fn_tipo_indirizzo_ammesso_per_ruolo(
            (SELECT fo FROM _ref), pg_temp.tipo('SEDELEG'), script.fn_data_operativa()),
    '5) per il fornitore la sede legale non e'' obbligatoria, e resta ammessa (come il cliente)');

-- ============================================================
-- 6-7) Il building block, su una riga obbligatoria costruita
-- ============================================================
-- SEDEOP: ammesso dalla societa', non dal privato (matrice delle nature).
SELECT pg_temp.matrice_ruolo((SELECT fo FROM _ref), 'SEDEOP', true);

SELECT ok(
    anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(
        (SELECT fo FROM _ref), pg_temp.natura('SC'), pg_temp.tipo('SEDEOP'), script.fn_data_operativa()),
    '6) natura che ammette il tipo: obbligatorio');

SELECT ok(
    NOT anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(
            (SELECT fo FROM _ref), (SELECT pr FROM _ref), pg_temp.tipo('SEDEOP'), script.fn_data_operativa())
    AND anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo(
            (SELECT fo FROM _ref), NULL, pg_temp.tipo('SEDEOP'), script.fn_data_operativa()),
    '7) natura che non ammette il tipo: non obbligatorio; natura NULL: obbligatorio');

-- ============================================================
-- 8-10) La check sul contesto
-- ============================================================
SELECT is(
    pg_temp.codici(anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto(
        (SELECT fo FROM _ref), '{}', pg_temp.tipo('SEDELEG'), script.fn_data_operativa(),
        NULL, (SELECT pr FROM _ref))),
    ARRAY['E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO'],
    '8) privato e sede legale: il motivo della natura, col codice del guard del soggetto');

SELECT is(
    anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto(
        (SELECT fo FROM _ref), '{}', pg_temp.tipo('SEDELEG'), script.fn_data_operativa(),
        NULL, (SELECT pr FROM _ref)) -> 0 -> 'valori',
    (SELECT jsonb_build_array(pr_nome, sedeleg_nome) FROM _ref),
    '9) ... coi valori natura e tipo, per descrizione');

SELECT is(
    anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto(
        (SELECT fo FROM _ref), '{}', pg_temp.tipo('SEDELEG'), script.fn_data_operativa(), NULL, NULL),
    '[]'::jsonb,
    '10) natura NULL: nessun motivo');

-- ============================================================
-- 11-14) Il fornitore privato, dal verbo del flusso Fornitori
-- ============================================================
SELECT is(
    (SELECT array_agg(ti.codice_interno::text ORDER BY ti.codice_interno)
       FROM anagrafiche.indirizzi i
       JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id
      WHERE i.soggetto_ruolo_id = (SELECT sr_pr FROM _f)),
    ARRAY['FATT'],
    '11) il privato ha la fatturazione sul ruolo e nessuna sede legale');

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzo_ruolo(%s, %L::jsonb)',
        (SELECT sr_pr FROM _f), pg_temp.el('SEDELEG', 'Via Privato pgTAP 9'))),
    'E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO',
    '12) la singolare: sede legale sul ruolo di un privato, rifiutata');

-- L'UPDATE diretto del tipo salta la madre: parla il guard della tabella.
SELECT is(
    pg_temp.messaggio_di(format(
        'UPDATE anagrafiche.indirizzi SET tipo_indirizzo_id = %s
          WHERE soggetto_ruolo_id = %s AND tipo_indirizzo_id = %s',
        pg_temp.tipo('SEDELEG'), (SELECT sr_pr FROM _f), pg_temp.tipo('FATT'))),
    (SELECT format('Il tipo soggetto %s non prevede l''indirizzo «%s».', pr_nome, sedeleg_nome) FROM _ref),
    '13) la strada che salta la madre: parla il guard, con la frase della natura');

SELECT ok(
    EXISTS (SELECT 1 FROM anagrafiche.indirizzi i
             WHERE i.soggetto_ruolo_id = (SELECT sr_di FROM _f)
               AND i.tipo_indirizzo_id = pg_temp.tipo('SEDELEG')),
    '14) la ditta individuale ha la sede legale sul ruolo (ammessa dalla sua natura)');

-- ============================================================
-- 15-18) I picker
-- ============================================================
SELECT is(
    (SELECT p.ammesso::text || '/' || p.motivo_codice
       FROM anagrafiche.fn_tipi_indirizzo_proponibili_ruolo((SELECT sr_pr FROM _f), NULL) p
      WHERE p.tipo_indirizzo_id = pg_temp.tipo('SEDELEG')),
    'false/' || dbops.fn_pgtap_codice_errore(format(
        'SELECT anagrafiche.fn_crea_indirizzo_ruolo(%s, %L::jsonb)',
        (SELECT sr_pr FROM _f), pg_temp.el('SEDELEG', 'Via Privato pgTAP 9'))),
    '15) sul ruolo salvato del privato: la sede legale spenta col codice della singolare');

SELECT results_eq(
    format($$SELECT ti.codice_interno::text, p.ammesso, p.obbligatorio, p.reason
               FROM anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(%s, %L) p
               JOIN config.tipi_indirizzi ti ON ti.id = p.tipo_indirizzo_id
              WHERE ti.codice_interno IN ('FATT', 'SEDELEG')
              ORDER BY ti.codice_interno$$,
           (SELECT fo FROM _ref), (SELECT pr FROM _s)),
    $$VALUES ('FATT'::text, true, true, NULL::text),
             ('SEDELEG'::text, false, false, 'TIPO_NON_AMMESSO_DALLA_NATURA'::text)$$,
    '16) sul tipo di ruolo, col privato: sede legale spenta, fatturazione obbligatoria');

SELECT is(
    (SELECT p.ammesso
       FROM anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo((SELECT fo FROM _ref), NULL::uuid) p
      WHERE p.tipo_indirizzo_id = pg_temp.tipo('SEDELEG')),
    true,
    '17) sul tipo di ruolo, soggetto non ancora scelto: la sede legale ammessa');

SELECT is(
    (SELECT count(*)::integer
       FROM anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(
                (SELECT fo FROM _ref), '00000000-0000-0000-0000-000000000000'::uuid)),
    0,
    '18) sul tipo di ruolo, soggetto che non c''e'': nessuna riga');

-- ============================================================
-- 19-20) L'auto-clone, con SEDEOP obbligatorio (riga costruita al 6-7)
-- ============================================================
SELECT anagrafiche.fn_crea_indirizzi_ruolo(
           f.sr_pr, jsonb_build_array(pg_temp.el('POSTA', 'Via Privato pgTAP 4'))) FROM _f f;
SELECT anagrafiche.fn_crea_indirizzi_ruolo(
           f.sr_sc, jsonb_build_array(pg_temp.el('POSTA', 'Via Societa pgTAP 4'))) FROM _f f;

SELECT is(
    (SELECT count(*)::integer FROM anagrafiche.indirizzi i
      WHERE i.soggetto_ruolo_id = (SELECT sr_pr FROM _f)
        AND i.tipo_indirizzo_id = pg_temp.tipo('SEDEOP')),
    0,
    '19) sul privato: l''obbligatorio che la natura vieta non si copia');

SELECT is(
    (SELECT count(*)::integer FROM anagrafiche.indirizzi i
      WHERE i.soggetto_ruolo_id = (SELECT sr_sc FROM _f)
        AND i.tipo_indirizzo_id = pg_temp.tipo('SEDEOP')),
    1,
    '20) sulla societa'': lo stesso obbligatorio si copia');

-- La riga SEDEOP torna facoltativa: serviva ai 6-7 e ai 19-20. Dal giro 4
-- (20261116-35) cancellare un indirizzo del ruolo ricontrolla gli
-- obbligatori, e il 24 toglie la sede legale dal ruolo della ditta, che la
-- sede operativa obbligatoria non l'ha mai avuta (la riga e' nata dopo il
-- ruolo).
SELECT pg_temp.matrice_ruolo((SELECT fo FROM _ref), 'SEDEOP', false);

-- ============================================================
-- 21-24) Il cambio di natura (D-4): la ditta fornitore diventa privato
-- ============================================================
-- La P.IVA proposta e' NULL: il motivo della P.IVA non entra, e resta solo
-- quello degli indirizzi del ruolo (la ditta ha DOMFISC sul soggetto, che il
-- privato ammette).
SELECT is(
    pg_temp.codici(anagrafiche.fn_check_cambio_natura_soggetto(
        s.di, (SELECT pr FROM _ref), NULL, so.cliente_pa, so.split_payment)),
    ARRAY['E_CAMBIO_NATURA_INDIRIZZI_RUOLO_NON_AMMESSI'],
    '21) ditta fornitore con la sede legale sul ruolo verso privato: il motivo del ruolo')
  FROM _s s JOIN anagrafiche.soggetti so ON so.id = s.di;

SELECT is(
    anagrafiche.fn_check_cambio_natura_soggetto(
        s.di, (SELECT pr FROM _ref), NULL, so.cliente_pa, so.split_payment) -> 0 -> 'valori',
    (SELECT jsonb_build_array(pr_nome, sedeleg_nome, fo_nome, '1') FROM _ref),
    '22) ... coi valori natura, tipo, ruolo, quanti')
  FROM _s s JOIN anagrafiche.soggetti so ON so.id = s.di;

-- ⚠️ La P.IVA scritta la svuota solo il SUPER_ADMIN, e il suo rifiuto parla per primo (fase a05,
--   rev 2026-11-24, brief-db-revisione-anagrafiche §20): il cambio verso il privato, che la deve
--   togliere, lo fa lui, perche' a parlare sia il motivo del ruolo.
CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-fornitore-privato', true);
SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa));

SELECT is(
    pg_temp.messaggio_di(format(
        'UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = %s, partita_iva = NULL WHERE id = %L',
        (SELECT pr FROM _ref), (SELECT di FROM _s))),
    (SELECT format('Il tipo soggetto %s non ammette l''indirizzo «%s» del ruolo %s (indirizzi da togliere: 1).',
                   pr_nome, sedeleg_nome, fo_nome) FROM _ref),
    '23) ... e l''UPDATE e'' rifiutato con la sua frase');

DELETE FROM anagrafiche.indirizzi
 WHERE soggetto_ruolo_id = (SELECT sr_di FROM _f)
   AND tipo_indirizzo_id = pg_temp.tipo('SEDELEG');

SELECT is(
    anagrafiche.fn_check_cambio_natura_soggetto(
        s.di, (SELECT pr FROM _ref), NULL, so.cliente_pa, so.split_payment),
    '[]'::jsonb,
    '24) tolta la sede legale dal ruolo, il cambio non ha piu'' motivi')
  FROM _s s JOIN anagrafiche.soggetti so ON so.id = s.di;

SELECT * FROM finish();
ROLLBACK;
