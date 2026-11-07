-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-11-07 (brief-db-sorgente-documento-e-riga, giro T.4): la bolla si cancella solo da bozza VUOTA
--   (nessuna riga attiva, 20261106-88). Prima dell'8 la bolla 1 si svuota: il prelievo se ne va e la riga 1
--   si disattiva. Il figlio CANCELLA del 9 dichiara la riga disattivata invece del prelievo: la cascata dal
--   documento porta ormai solo righe disattivate, e il dettaglio resta provato dal 4-5. Attese invariate.
-- pgTAP test per Zero ERP
--
-- Il lato «in uscita» della provenienza polimorfa (S-9): script.trgfn_sorgente_in_uscita
--   e la sua convergenza dal catalogo (dbops.fn_sorgente_converge_uscita, 90_end).
--   Brief: brief-db-sorgente-documento-e-riga §6.2 S-9, §7.2 lotto 0, giro 0.2.
--   ChangeSet: 20261106-17, -18, -19, -21; codice E_SORG_ORIGINE_REFERENZIATA.
--
-- ⭐ Nel lotto 0 nessuna tabella vera monta il guard unico: i FIGLI sono due
--   tabelle temporanee che lo montano, una con BLOCCA e una con CANCELLA. Il lato
--   «in uscita» e' DEFINER (come una FK, vede anche cio' che la RLS nasconde): le
--   tabelle temporanee si concedono al proprietario, perche' le possa leggere.
--   Le origini si costruiscono: una bolla in bozza con due righe e un prelievo,
--   una seconda bolla, un preventivo in bozza.
--
-- Elenco test (plan 14):
--   1) ogni tabella che il catalogo dichiara (documento, righe, dettaglio) monta il
--        trigger, e nessun'altra
--   2) il trigger e' AFTER DELETE, per istruzione, con la tabella di transizione «vecchie»
--   3) la funzione e' SECURITY DEFINER con pg_catalog primo nel search_path
--   4) cancellare il prelievo da cui nasce un figlio BLOCCA -> E_SORG_ORIGINE_REFERENZIATA
--   5) ...e il prelievo c'e' ancora
--   6) cancellare la riga 2, da cui nasce un figlio CANCELLA: passa
--   7) ...e il figlio se n'e' andato con lei
--   8) cancellare la bolla (vuota) con un figlio BLOCCA sul documento -> rifiuto
--   9) ...e con un figlio che blocca e due che cancellano, non si cancella niente
--  10) tolto il figlio che blocca, la bolla si cancella
--  11) ...e se ne vanno i figli CANCELLA del documento e della riga disattivata
--  12) una bolla senza figli si cancella come prima
--  13) il preventivo (chiave uid) con un figlio BLOCCA su sorgente_uid -> rifiuto
--  14) la frase: il conteggio dei record che ne nascono, senza segnaposti grezzi
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ===== il catalogo e il montaggio =====
SELECT is_empty(
    $$WITH dichiarate AS (
          SELECT DISTINCT x.t::oid AS relid
            FROM config.sorgenti s
            CROSS JOIN LATERAL (VALUES (s.target_table), (s.righe_table), (s.dettaglio_table)) x(t)
           WHERE x.t IS NOT NULL),
      montate AS (
          SELECT DISTINCT tg.tgrelid AS relid
            FROM pg_trigger tg
           WHERE tg.tgfoid = 'script.trgfn_sorgente_in_uscita()'::regprocedure)
      SELECT relid::regclass::text FROM dichiarate EXCEPT SELECT relid::regclass::text FROM montate
      UNION ALL
      SELECT relid::regclass::text FROM montate EXCEPT SELECT relid::regclass::text FROM dichiarate$$,
    '1) il lato in uscita e'' montato su ogni tabella dichiarata dal catalogo, e su nessun''altra');

-- tgtype: 1 = ROW (deve mancare), 8 = DELETE, 2 = BEFORE (deve mancare)
SELECT is_empty(
    $$SELECT tg.tgrelid::regclass::text
        FROM pg_trigger tg
       WHERE tg.tgfoid = 'script.trgfn_sorgente_in_uscita()'::regprocedure
         AND NOT ((tg.tgtype & 1) = 0 AND (tg.tgtype & 2) = 0 AND (tg.tgtype & 8) = 8
                  AND (tg.tgtype & (4 | 16 | 32)) = 0 AND tg.tgoldtable = 'vecchie')$$,
    '2) ogni montaggio e'' AFTER DELETE, per istruzione, con la tabella di transizione «vecchie»');

SELECT ok(
    (SELECT p.prosecdef AND p.proconfig[1] LIKE 'search_path=pg_catalog%'
       FROM pg_proc p WHERE p.oid = 'script.trgfn_sorgente_in_uscita()'::regprocedure),
    '3) script.trgfn_sorgente_in_uscita e'' SECURITY DEFINER, con pg_catalog primo nel search_path');

-- ===== il mondo =====
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('PGT-SUSC');

CREATE TEMP TABLE _fix (mag bigint, art uuid, lotto bigint);
DO $fix$
DECLARE v_mag bigint; v_art uuid; v_lotto bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-SUSC-MAG', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-SUSC-LOTTI', true, true, false);
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo)
    VALUES (v_art, 'PGT-SUSC-L1', script.fn_data_operativa() - 1) RETURNING id INTO v_lotto;
    INSERT INTO _fix VALUES (v_mag, v_art, v_lotto);
END $fix$;

CREATE TEMP TABLE _b (ddt1 bigint, r1 bigint, r2 bigint, prel1 bigint, ddt2 bigint);
DO $b$
DECLARE v_d1 bigint; v_d2 bigint; v_r1 bigint; v_r2 bigint; v_p bigint; v_iva integer;
BEGIN
    SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1;
    v_d1 := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                    'VENDITA', (SELECT mag FROM _fix));
    v_d2 := dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),
                                    'VENDITA', (SELECT mag FROM _fix));
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_d1, 1, art, 'riga 1', 2, 2, 10, v_iva FROM _fix RETURNING id INTO v_r1;
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_d1, 2, art, 'riga 2', 1, 1, 10, v_iva FROM _fix RETURNING id INTO v_r2;
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id)
    SELECT v_r1, 2, lotto FROM _fix RETURNING id INTO v_p;
    INSERT INTO _b VALUES (v_d1, v_r1, v_r2, v_p, v_d2);
END $b$;

CREATE TEMP TABLE _p AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('PGT-SUSC-P', 'DRAFT');

CREATE TEMP TABLE _t AS
SELECT (SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA') AS ddt,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO')  AS prev;

-- I figli: tabelle temporanee col guard unico, concesse al proprietario (il lato
-- «in uscita» e' DEFINER).
CREATE TEMP TABLE _figli_blocca (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sorgente_tipo_id bigint, sorgente_id bigint, sorgente_uid uuid,
    sorgente_riga bigint, sorgente_dettaglio bigint);
CREATE TABLE pg_temp._figli_cancella (LIKE pg_temp._figli_blocca INCLUDING ALL);
CREATE TRIGGER trg_figli_blocca_a10_guard_sorgente_ins_upd BEFORE INSERT OR UPDATE ON pg_temp._figli_blocca
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'BLOCCA');
CREATE TRIGGER trg_figli_cancella_a10_guard_sorgente_ins_upd BEFORE INSERT OR UPDATE ON pg_temp._figli_cancella
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_guard_sorgente('DOCUMENTO', 'CANCELLA');
GRANT SELECT, DELETE ON pg_temp._figli_blocca, pg_temp._figli_cancella TO zeroerp_owner;

CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text)
RETURNS text AS $fn$
DECLARE v_codice text;
BEGIN
  EXECUTE p_sql;
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_codice, ''), SQLSTATE);
END $fn$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.messaggio_errore(p_sql text)
RETURNS text AS $fn$
BEGIN
  EXECUTE p_sql;
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  RETURN SQLERRM;
END $fn$ LANGUAGE plpgsql;

-- ===== il dettaglio e la riga =====
INSERT INTO pg_temp._figli_blocca (sorgente_tipo_id, sorgente_id, sorgente_riga, sorgente_dettaglio)
SELECT (SELECT ddt FROM _t), ddt1, r1, prel1 FROM _b;

SELECT is(pg_temp.codice_errore(format('DELETE FROM vendite.ddt_righe_prelievi WHERE id = %s', (SELECT prel1 FROM _b))),
    'E_SORG_ORIGINE_REFERENZIATA',
    '4) cancellare il prelievo da cui nasce un figlio BLOCCA -> E_SORG_ORIGINE_REFERENZIATA');

SELECT ok(EXISTS (SELECT 1 FROM vendite.ddt_righe_prelievi WHERE id = (SELECT prel1 FROM _b)),
    '5) ...e il prelievo c''e'' ancora');

INSERT INTO pg_temp._figli_cancella (sorgente_tipo_id, sorgente_id, sorgente_riga)
SELECT (SELECT ddt FROM _t), ddt1, r2 FROM _b;

SELECT lives_ok(format('DELETE FROM vendite.ddt_righe WHERE id = %s', (SELECT r2 FROM _b)),
    '6) cancellare la riga 2, da cui nasce un figlio CANCELLA: passa');

SELECT is((SELECT count(*)::int FROM pg_temp._figli_cancella WHERE sorgente_riga = (SELECT r2 FROM _b)), 0,
    '7) ...e il figlio della riga se n''e'' andato con lei');

-- ===== il documento =====
-- rev 2026-11-07 (giro T.4): la bolla si cancella solo da bozza vuota. Si
-- svuota: via il figlio del prelievo e il prelievo, la riga 1 disattivata. Il
-- figlio che blocca dichiara il documento.
DELETE FROM pg_temp._figli_blocca;
DELETE FROM vendite.ddt_righe_prelievi WHERE id = (SELECT prel1 FROM _b);
UPDATE vendite.ddt_righe SET attivo = false WHERE id = (SELECT r1 FROM _b);
INSERT INTO pg_temp._figli_blocca (sorgente_tipo_id, sorgente_id)
SELECT (SELECT ddt FROM _t), ddt1 FROM _b;

SELECT is(pg_temp.codice_errore(format('DELETE FROM vendite.ddt WHERE id = %s', (SELECT ddt1 FROM _b))),
    'E_SORG_ORIGINE_REFERENZIATA',
    '8) cancellare la bolla con un figlio BLOCCA -> rifiuto');

INSERT INTO pg_temp._figli_cancella (sorgente_tipo_id, sorgente_id)
SELECT (SELECT ddt FROM _t), ddt1 FROM _b;
INSERT INTO pg_temp._figli_cancella (sorgente_tipo_id, sorgente_id, sorgente_riga)
SELECT (SELECT ddt FROM _t), ddt1, r1 FROM _b;

SELECT is(
    pg_temp.codice_errore(format('DELETE FROM vendite.ddt WHERE id = %s', (SELECT ddt1 FROM _b)))
      || '|' || (SELECT count(*) FROM pg_temp._figli_cancella)::text
      || '|' || (SELECT count(*) FROM vendite.ddt WHERE id = (SELECT ddt1 FROM _b))::text,
    'E_SORG_ORIGINE_REFERENZIATA|2|1',
    '9) un figlio blocca e due seguirebbero: non si cancella niente, ne'' la bolla ne'' i figli');

DELETE FROM pg_temp._figli_blocca;

SELECT lives_ok(format('DELETE FROM vendite.ddt WHERE id = %s', (SELECT ddt1 FROM _b)),
    '10) tolto il figlio che blocca, la bolla si cancella');

SELECT is((SELECT count(*)::int FROM pg_temp._figli_cancella), 0,
    '11) ...e i figli CANCELLA del documento e della riga disattivata se ne vanno con lei');

SELECT lives_ok(format('DELETE FROM vendite.ddt WHERE id = %s', (SELECT ddt2 FROM _b)),
    '12) una bolla senza figli si cancella come prima');

-- ===== un documento a chiave uid =====
INSERT INTO pg_temp._figli_blocca (sorgente_tipo_id, sorgente_uid)
SELECT (SELECT prev FROM _t), preventivo_uid FROM _p;

SELECT is(pg_temp.codice_errore(format('DELETE FROM vendite.preventivi WHERE id = %s', (SELECT preventivo_id FROM _p))),
    'E_SORG_ORIGINE_REFERENZIATA',
    '13) il preventivo con un figlio BLOCCA su sorgente_uid -> rifiuto');

SELECT ok(
    pg_temp.messaggio_errore(format('DELETE FROM vendite.preventivi WHERE id = %s', (SELECT preventivo_id FROM _p)))
        LIKE '%Non si può cancellare: 1 registrazioni dichiarano di nascere da qui.%',
    '14) la frase porta il conteggio dei record che ne nascono');

SELECT * FROM finish();
ROLLBACK;
