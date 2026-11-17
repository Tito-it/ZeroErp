-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Gli indirizzi obbligatori che una natura chiede e il soggetto non ha:
-- la lettura per il form del cambio di natura, e i due building block «che
-- cosa manca» che leggono anche i guard. Il cambio di natura porta con se'
-- gli indirizzi nello stesso salvataggio (Tid, 2026-11-17).
--   Brief: brief-db-fornitore-privato-indirizzi §12.5, giro 5.
--   ChangeSet 20261116-39 … -43; il nome della lettura dal 20261116-44 (§13.3).
--
-- Elenco test (plan 11):
--   presidi
--    1) i guard leggono i building block dei mancanti; la lettura li compone
--    2) una firma sola per nome, e il nome di script non ha omonimi in anagrafiche
--   la lettura (righe costruite: consegna obbligatoria per il fornitore e
--   vietata al privato; corrispondenza obbligatoria per la ditta)
--    3) natura di oggi, soggetto completo: niente
--    4) natura proposta: il ruolo chiede la consegna, il soggetto la corrispondenza
--    5) la riga col ripiego lo riporta
--    6) natura NULL: sul soggetto niente, sul ruolo la natura non conta
--    7) soggetto che non esiste: niente
--   il salvataggio, come lo fara' il backend (natura, poi gli indirizzi
--   elencati, nella stessa transazione)
--    8) senza la consegna del ruolo: rifiutato, col codice del ruolo
--    9) con tutti gli indirizzi elencati: passa
--   10) ... e sulla natura nuova non manca piu' niente
--   11) ... i guard dicono lo stesso: riscrivere ruolo e soggetto passa
--
-- Scopo: ogni ramo si COSTRUISCE (soggetti dai builder, il fornitore dalla
-- madre del flusso Fornitori, le righe di matrice dal test: regola zero).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture: cataloghi e helper
-- ============================================================
CREATE FUNCTION pg_temp.tipo(p_codice config.tipi_indirizzi.codice_interno%TYPE)
RETURNS config.tipi_indirizzi.id%TYPE LANGUAGE sql AS
$f$ SELECT id FROM config.tipi_indirizzi WHERE codice_interno = p_codice $f$;

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

-- La lettura come testo, nel suo ordine: «S» per il soggetto, il codice del
-- ruolo per un ruolo, poi «TIPO>RIPIEGO».
CREATE FUNCTION pg_temp.mancanti(
    p_soggetto anagrafiche.soggetti.id%TYPE,
    p_natura   anagrafiche.soggetti.tipo_soggetto_dettaglio_id%TYPE)
RETURNS text LANGUAGE sql AS $f$  -- un testo composto, non il riflesso di una colonna
    SELECT COALESCE(string_agg(COALESCE(tr.codice_interno, 'S') || ':' || t.codice_interno
                               || '>' || COALESCE(r.codice_interno, '-'), ',' ORDER BY m.n), '')
      FROM anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli(p_soggetto, p_natura)
           WITH ORDINALITY AS m(soggetto_ruolo_id, tipo_ruolo_id, tipo_indirizzo_id, ripiego_tipo_indirizzo_id, n)
      JOIN config.tipi_indirizzi t ON t.id = m.tipo_indirizzo_id
      LEFT JOIN config.tipi_indirizzi r ON r.id = m.ripiego_tipo_indirizzo_id
      LEFT JOIN config.tipi_ruoli tr ON tr.id = m.tipo_ruolo_id
$f$;

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

-- Il privato dal builder; il fornitore privato dal verbo del flusso Fornitori.
CREATE TEMP TABLE _s ON COMMIT DROP AS
SELECT dbops.fn_pgtap_crea_soggetto_pf('Mancanti', 'Privato', pg_temp.natura('PR')) AS pr;

SET CONSTRAINTS ALL DEFERRED;
CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT (SELECT soggetto_ruolo_id FROM anagrafiche.fn_crea_fornitore(
            s.pr, '{}'::jsonb, NULL,
            jsonb_build_array(pg_temp.el('FATT', 'Via Mancanti pgTAP 1')))) AS fo
  FROM _s s;
SET CONSTRAINTS ALL IMMEDIATE;

-- Le righe del test: per il fornitore la consegna obbligatoria, senza
-- ripiego; il privato non la ammette (riga della natura spenta), la ditta
-- si'. La ditta, in piu', vuole la corrispondenza sul soggetto.
SELECT pg_temp.matrice_ruolo('FO', 'CON', true, NULL);
UPDATE config.tipi_soggetto_dettaglio_tipi_indirizzo
   SET attivo = false
 WHERE tipo_soggetto_dettaglio_id = pg_temp.natura('PR') AND tipo_indirizzo_id = pg_temp.tipo('CON');
UPDATE config.tipi_soggetto_dettaglio_tipi_indirizzo
   SET obbligatorio = true, fallback_tipo_indirizzo_id = NULL
 WHERE tipo_soggetto_dettaglio_id = pg_temp.natura('DI') AND tipo_indirizzo_id = pg_temp.tipo('POSTA');

-- ============================================================
-- 1-2) Presidi
-- ============================================================
SELECT ok(
    pg_get_functiondef('anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(bigint, uuid)'::regprocedure)
        LIKE '%anagrafiche.fn_indirizzi_obbligatori_mancanti_ruolo(%'
    AND pg_get_functiondef('anagrafiche.fn_guard_indirizzi_obbligatori_ruolo(bigint, uuid)'::regprocedure)
        NOT LIKE '%fn_indirizzi_obbligatori_ruolo(%'
    AND pg_get_functiondef('anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(uuid, uuid)'::regprocedure)
        LIKE '%anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto(%'
    AND pg_get_functiondef('anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(uuid, uuid)'::regprocedure)
        !~ '(FROM|JOIN)\s+(config\.)?tipi_soggetto_dettaglio_tipi_indirizzo\M'
    AND pg_get_functiondef('anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli(uuid, bigint)'::regprocedure)
        LIKE '%fn_indirizzi_obbligatori_mancanti_ruolo(%'
    AND pg_get_functiondef('anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli(uuid, bigint)'::regprocedure)
        LIKE '%fn_indirizzi_obbligatori_mancanti_soggetto(%',
    '1) i guard leggono i building block dei mancanti, e la lettura del form li compone');

SELECT is(
    (SELECT array_agg(p.proname || '/' || p.pronargs ORDER BY p.proname)
       FROM pg_proc p
      WHERE p.pronamespace = 'anagrafiche'::regnamespace
        AND p.proname IN ('fn_indirizzi_obbligatori_mancanti',
                          'fn_indirizzi_obbligatori_mancanti_ruolo',
                          'fn_indirizzi_obbligatori_mancanti_soggetto',
                          'fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli')),
    ARRAY['fn_indirizzi_obbligatori_mancanti_ruolo/3',
          'fn_indirizzi_obbligatori_mancanti_soggetto/3',
          'fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli/2'],
    '2) una firma sola per nome, e il nome di script non ha omonimi in anagrafiche');

-- ============================================================
-- 3-7) La lettura
-- ============================================================
SELECT is(pg_temp.mancanti((SELECT pr FROM _s), pg_temp.natura('PR')), '',
    '3) sulla natura di oggi il privato fornitore non manca di niente');

SELECT is(pg_temp.mancanti((SELECT pr FROM _s), pg_temp.natura('DI')), 'S:POSTA>-,FO:CON>-',
    '4) sulla ditta proposta: prima la corrispondenza del soggetto, poi la consegna del ruolo');

SELECT pg_temp.matrice_ruolo('FO', 'CON', true, 'SPED');

SELECT is(pg_temp.mancanti((SELECT pr FROM _s), pg_temp.natura('DI')), 'S:POSTA>-,FO:CON>SPED',
    '5) la riga col ripiego lo riporta (la ditta e il fornitore ammettono la spedizione)');

SELECT is(pg_temp.mancanti((SELECT pr FROM _s), NULL), 'FO:CON>SPED',
    '6) natura NULL: sul soggetto niente; sul ruolo la natura non conta');

SELECT is(pg_temp.mancanti(gen_random_uuid(), pg_temp.natura('DI')), '',
    '7) soggetto che non esiste: niente');

-- Il ripiego torna via: il salvataggio sotto chiede la consegna.
SELECT pg_temp.matrice_ruolo('FO', 'CON', true, NULL);

-- ============================================================
-- 8-11) Il salvataggio, come lo fara' il backend
-- ============================================================
-- La natura prima, poi gli indirizzi: il guard del tipo li giudica sulla
-- natura nuova (la consegna, sul privato, non si scriverebbe).
CREATE TEMP TABLE _cambio ON COMMIT DROP AS
SELECT format('UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = %s, partita_iva = %L WHERE id = %L',
              pg_temp.natura('DI'), dbops.fn_pgtap_piva_libera(), (SELECT pr FROM _s)) AS q;

SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'DO $x$ BEGIN
             SET CONSTRAINTS ALL DEFERRED;
             EXECUTE %L;
             PERFORM anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb);
             SET CONSTRAINTS ALL IMMEDIATE;
         END $x$',
        (SELECT q FROM _cambio), (SELECT pr FROM _s), pg_temp.el('POSTA', 'Via Mancanti pgTAP 2'))),
    'E_INDIRIZZO_OBBLIGATORIO_MANCANTE',
    '8) la ditta con la corrispondenza ma senza la consegna del ruolo: rifiutato, col codice del ruolo');
SET CONSTRAINTS ALL IMMEDIATE;

SET CONSTRAINTS ALL DEFERRED;
DO $cambio$ BEGIN EXECUTE (SELECT q FROM _cambio); END $cambio$;
SELECT anagrafiche.fn_crea_indirizzo_soggetto(s.pr, pg_temp.el('POSTA', 'Via Mancanti pgTAP 2')) FROM _s s;
SELECT anagrafiche.fn_crea_indirizzo_ruolo(f.fo, pg_temp.el('CON', 'Via Mancanti pgTAP 3')) FROM _f f;
SELECT lives_ok('SET CONSTRAINTS ALL IMMEDIATE',
    '9) natura e indirizzi elencati nella stessa transazione: passa');

SELECT is(pg_temp.mancanti((SELECT pr FROM _s), pg_temp.natura('DI')), '',
    '10) ... e sulla natura nuova non manca piu'' niente');

SELECT lives_ok(
    format($$UPDATE anagrafiche.soggetti_ruoli SET tipo_ruolo_id = tipo_ruolo_id WHERE id = %s;
             UPDATE anagrafiche.soggetti SET tipo_soggetto_dettaglio_id = tipo_soggetto_dettaglio_id WHERE id = %L$$,
           (SELECT fo FROM _f), (SELECT pr FROM _s)),
    '11) ... e i guard dicono lo stesso: riscrivere il ruolo e il soggetto passa');

SELECT * FROM finish();
ROLLBACK;
