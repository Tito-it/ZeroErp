-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il guard unico della provenienza, script.trgfn_guard_sorgente, e la grammatica
--   dei suoi argomenti, script.fn_sorgente_guard_argomenti.
--   Brief: brief-db-sorgente-documento-e-riga §4, §7.2 lotto 0 (guard unico, D-2).
--   ChangeSet: 20261106-15; codici in codici_errore.csv / messaggi_errore.csv.
--
-- ⭐ Nel lotto 0 il guard non lo monta nessuna tabella vera: lo montano qui
--   TRE tabelle temporanee con le colonne del modello, una per livello minimo
--   (DOCUMENTO, RIGA, DETTAGLIO), piu' una con sorgente_uid di testo. I documenti,
--   le righe e i prelievi si COSTRUISCONO: due bolle (tipo a chiave id, a tre
--   livelli), un preventivo (chiave uid, senza dettaglio).
--
-- Elenco test (plan 24):
--  livello DOCUMENTO
--   1) senza tipo: passa
--   2) bolla con sorgente_id: passa
--   3) bolla con sorgente_uid -> E_SORG_CHIAVE_NON_CONFORME
--   4) bolla con tutte e due le chiavi -> E_SORG_CHIAVE_NON_CONFORME
--   5) preventivo con sorgente_uid: passa
--   6) preventivo con sorgente_id -> E_SORG_CHIAVE_NON_CONFORME
--   7) bolla che non c'e' -> E_SORG_NOT_FOUND
--   8) bolla + una sua riga: passa
--   9) bolla + la riga di un'altra bolla -> E_SORG_RIGA_NON_DEL_DOCUMENTO
--  10) bolla + riga + un suo prelievo: passa
--  11) bolla + riga 2 + il prelievo della riga 1 -> E_SORG_DETTAGLIO_NON_DELLA_RIGA
--  12) bolla + prelievo senza la riga -> E_SORG_LIVELLO_NON_PREVISTO
--  13) preventivo + riga + dettaglio (il tipo non ne ha) -> E_SORG_LIVELLO_NON_PREVISTO
--  14) ⭐ un tipo senza righe con una riga, documento inesistente ->
--        E_SORG_LIVELLO_NON_PREVISTO: la forma parla prima dei dati
--  15) UPDATE in un'istruzione della sola sorgente_riga verso la riga di
--        un'altra bolla -> E_SORG_RIGA_NON_DEL_DOCUMENTO
--  livello RIGA
--  16) bolla senza riga -> E_SORG_LIVELLO_MANCANTE
--  17) ⭐ un tipo senza righe, senza riga: il livello minimo si ferma ai livelli
--        del tipo (l'errore e' E_SORG_NOT_FOUND, non il livello)
--  livello DETTAGLIO
--  18) bolla + riga senza prelievo -> E_SORG_LIVELLO_MANCANTE
--  19) preventivo + riga (il tipo non ha dettaglio): passa
--  gli argomenti e la forma
--  20) argomenti fuori grammatica -> E_SORG_CONF
--  21) sorgente_uid di testo che non e' un uuid -> E_SORG_FORMATO
--  22) fn_sorgente_guard_argomenti: default, maiuscole, valori fuori elenco, troppi
--  23) i cinque codici nuovi sono a catalogo, TECNICO, con il messaggio
--  24) la frase si compone: nessun segnaposto %s grezzo nel messaggio
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(24);

-- ===== il mondo =====
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('PGT-GSRC');

CREATE TEMP TABLE _fix (mag bigint, art uuid, lotto bigint);
DO $fix$
DECLARE v_mag bigint; v_art uuid; v_lotto bigint;
BEGIN
    v_mag := dbops.fn_pgtap_crea_magazzino('PGT-GSRC-MAG', false);
    v_art := dbops.fn_pgtap_crea_articolo('PGT-GSRC-LOTTI', true, true, false);
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo)
    VALUES (v_art, 'PGT-GSRC-L1', script.fn_data_operativa() - 1) RETURNING id INTO v_lotto;
    INSERT INTO _fix VALUES (v_mag, v_art, v_lotto);
END $fix$;

-- Due bolle in bozza: la prima con due righe e un prelievo sulla riga 1, la
-- seconda con una riga.
CREATE TEMP TABLE _b (ddt1 bigint, ddt1_uid uuid, r1 bigint, r2 bigint, prel1 bigint, ddt2 bigint, r3 bigint);
DO $b$
DECLARE v_d1 bigint; v_d2 bigint; v_r1 bigint; v_r2 bigint; v_r3 bigint; v_p bigint; v_iva integer;
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
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, prezzo_unitario, iva_id)
    SELECT v_d2, 1, art, 'riga 3', 1, 1, 10, v_iva FROM _fix RETURNING id INTO v_r3;
    INSERT INTO vendite.ddt_righe_prelievi (ddt_riga_id, qta, lotto_id)
    SELECT v_r1, 2, lotto FROM _fix RETURNING id INTO v_p;
    INSERT INTO _b VALUES (v_d1, (SELECT d.uid FROM vendite.ddt d WHERE d.id = v_d1), v_r1, v_r2, v_p, v_d2, v_r3);
END $b$;

CREATE TEMP TABLE _p AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('PGT-GSRC-P', 'DRAFT');

CREATE TEMP TABLE _t AS
SELECT (SELECT id FROM config.sorgenti WHERE codice_interno = 'DDT_VENDITA')      AS ddt,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO')       AS prev,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'ATTIVITA_CONSUMI') AS consumi;

-- Le tabelle che montano il guard, una per livello minimo.
CREATE TEMP TABLE _prov (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sorgente_tipo_id bigint, sorgente_id bigint, sorgente_uid uuid,
    sorgente_riga bigint, sorgente_dettaglio bigint);
CREATE TABLE pg_temp._prov_riga (LIKE pg_temp._prov INCLUDING ALL);
CREATE TABLE pg_temp._prov_dett (LIKE pg_temp._prov INCLUDING ALL);
CREATE TABLE pg_temp._prov_testo (sorgente_tipo_id bigint, sorgente_uid text);
CREATE TABLE pg_temp._prov_boh (LIKE pg_temp._prov INCLUDING ALL);

CREATE TRIGGER trg_prov_a10_guard_sorgente_ins_upd BEFORE INSERT OR UPDATE ON pg_temp._prov
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_guard_sorgente();
CREATE TRIGGER trg_prov_riga_a10_guard_sorgente_ins_upd BEFORE INSERT OR UPDATE ON pg_temp._prov_riga
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_guard_sorgente('RIGA');
CREATE TRIGGER trg_prov_dett_a10_guard_sorgente_ins_upd BEFORE INSERT OR UPDATE ON pg_temp._prov_dett
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_guard_sorgente('DETTAGLIO', 'BLOCCA');
CREATE TRIGGER trg_prov_testo_a10_guard_sorgente_ins_upd BEFORE INSERT OR UPDATE ON pg_temp._prov_testo
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_guard_sorgente();
CREATE TRIGGER trg_prov_boh_a10_guard_sorgente_ins_upd BEFORE INSERT OR UPDATE ON pg_temp._prov_boh
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_guard_sorgente('BOH');

-- Il codice dell'errore sollevato (il canale CONSTRAINT dell'eccezione).
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

-- Un INSERT nella tabella del livello DOCUMENTO.
CREATE OR REPLACE FUNCTION pg_temp.ins(p_tab text, p_tipo bigint, p_id bigint, p_uid uuid,
                                       p_riga bigint, p_dett bigint)
RETURNS text LANGUAGE sql AS $fn$
  SELECT format('INSERT INTO pg_temp.%I (sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga, sorgente_dettaglio) '
                'VALUES (%L, %L, %L, %L, %L)', p_tab, p_tipo, p_id, p_uid, p_riga, p_dett);
$fn$;

-- ===== livello DOCUMENTO =====
SELECT lives_ok(pg_temp.ins('_prov', NULL, NULL, NULL, NULL, NULL),
    '1) senza tipo: passa');

SELECT lives_ok(pg_temp.ins('_prov', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), NULL, NULL, NULL),
    '2) la bolla con sorgente_id: passa');

SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov', (SELECT ddt FROM _t), NULL, (SELECT ddt1_uid FROM _b), NULL, NULL)),
    'E_SORG_CHIAVE_NON_CONFORME',
    '3) la bolla con sorgente_uid (il tipo dice id) -> E_SORG_CHIAVE_NON_CONFORME');

SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), (SELECT ddt1_uid FROM _b), NULL, NULL)),
    'E_SORG_CHIAVE_NON_CONFORME',
    '4) la bolla con tutte e due le chiavi -> E_SORG_CHIAVE_NON_CONFORME');

SELECT lives_ok(pg_temp.ins('_prov', (SELECT prev FROM _t), NULL, (SELECT preventivo_uid FROM _p), NULL, NULL),
    '5) il preventivo con sorgente_uid: passa');

SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov', (SELECT prev FROM _t), (SELECT preventivo_id FROM _p), NULL, NULL, NULL)),
    'E_SORG_CHIAVE_NON_CONFORME',
    '6) il preventivo con sorgente_id (il tipo dice uid) -> E_SORG_CHIAVE_NON_CONFORME');

SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov', (SELECT ddt FROM _t), -1, NULL, NULL, NULL)),
    'E_SORG_NOT_FOUND',
    '7) una bolla che non c''e'' -> E_SORG_NOT_FOUND');

SELECT lives_ok(pg_temp.ins('_prov', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), NULL, (SELECT r1 FROM _b), NULL),
    '8) la bolla e una sua riga: passa');

SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), NULL, (SELECT r3 FROM _b), NULL)),
    'E_SORG_RIGA_NON_DEL_DOCUMENTO',
    '9) la bolla e la riga di un''altra bolla -> E_SORG_RIGA_NON_DEL_DOCUMENTO');

SELECT lives_ok(pg_temp.ins('_prov', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), NULL, (SELECT r1 FROM _b), (SELECT prel1 FROM _b)),
    '10) la bolla, la riga e un suo prelievo: passa');

SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), NULL, (SELECT r2 FROM _b), (SELECT prel1 FROM _b))),
    'E_SORG_DETTAGLIO_NON_DELLA_RIGA',
    '11) la riga 2 col prelievo della riga 1 -> E_SORG_DETTAGLIO_NON_DELLA_RIGA');

SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), NULL, NULL, (SELECT prel1 FROM _b))),
    'E_SORG_LIVELLO_NON_PREVISTO',
    '12) un prelievo senza la sua riga -> E_SORG_LIVELLO_NON_PREVISTO');

SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov', (SELECT prev FROM _t), NULL, (SELECT preventivo_uid FROM _p), (SELECT preventivo_riga_id FROM _p), 1)),
    'E_SORG_LIVELLO_NON_PREVISTO',
    '13) il preventivo con un dettaglio (il tipo non ne ha) -> E_SORG_LIVELLO_NON_PREVISTO');

SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov', (SELECT consumi FROM _t), -1, NULL, 1, NULL)),
    'E_SORG_LIVELLO_NON_PREVISTO',
    '14) un tipo senza righe con una riga, documento inesistente: parla la forma (E_SORG_LIVELLO_NON_PREVISTO)');

-- 15) UPDATE in un'istruzione sola, della sola riga
INSERT INTO pg_temp._prov (sorgente_tipo_id, sorgente_id, sorgente_riga)
SELECT (SELECT ddt FROM _t), ddt1, r2 FROM _b;
SELECT is(pg_temp.codice_errore(format(
        'UPDATE pg_temp._prov SET sorgente_riga = %s WHERE sorgente_riga = %s',
        (SELECT r3 FROM _b), (SELECT r2 FROM _b))),
    'E_SORG_RIGA_NON_DEL_DOCUMENTO',
    '15) UPDATE della sola sorgente_riga verso la riga di un''altra bolla -> E_SORG_RIGA_NON_DEL_DOCUMENTO');

-- ===== livello RIGA =====
SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov_riga', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), NULL, NULL, NULL)),
    'E_SORG_LIVELLO_MANCANTE',
    '16) livello RIGA, la bolla senza riga -> E_SORG_LIVELLO_MANCANTE');

SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov_riga', (SELECT consumi FROM _t), -1, NULL, NULL, NULL)),
    'E_SORG_NOT_FOUND',
    '17) livello RIGA, un tipo senza righe: il minimo si ferma ai livelli del tipo (E_SORG_NOT_FOUND, non il livello)');

-- ===== livello DETTAGLIO =====
SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov_dett', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), NULL, (SELECT r1 FROM _b), NULL)),
    'E_SORG_LIVELLO_MANCANTE',
    '18) livello DETTAGLIO, la bolla con la riga e senza prelievo -> E_SORG_LIVELLO_MANCANTE');

SELECT lives_ok(pg_temp.ins('_prov_dett', (SELECT prev FROM _t), NULL, (SELECT preventivo_uid FROM _p), (SELECT preventivo_riga_id FROM _p), NULL),
    '19) livello DETTAGLIO, il preventivo con la riga (il tipo non ha dettaglio): passa');

-- ===== argomenti e forma =====
SELECT is(pg_temp.codice_errore(pg_temp.ins('_prov_boh', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), NULL, NULL, NULL)),
    'E_SORG_CONF',
    '20) un guard montato con argomenti fuori grammatica -> E_SORG_CONF');

SELECT is(pg_temp.codice_errore(format(
        'INSERT INTO pg_temp._prov_testo (sorgente_tipo_id, sorgente_uid) VALUES (%s, %L)',
        (SELECT prev FROM _t), 'PRV-0001')),
    'E_SORG_FORMATO',
    '21) sorgente_uid di testo che non e'' un uuid -> E_SORG_FORMATO');

SELECT results_eq(
    $$SELECT a.livello_minimo, a.azione_cancellazione, a.valido
        FROM (VALUES (1, ARRAY[]::text[]), (2, ARRAY[' riga ', 'cancella']),
                     (3, ARRAY['BOH']), (4, ARRAY['RIGA', 'BLOCCA', 'TERZO'])) v(n, args)
        CROSS JOIN LATERAL script.fn_sorgente_guard_argomenti(v.args) a
       ORDER BY v.n$$,
    $$VALUES ('DOCUMENTO', 'BLOCCA', true), ('RIGA', 'CANCELLA', true),
             ('BOH', 'BLOCCA', false), ('RIGA', 'BLOCCA', false)$$,
    '22) fn_sorgente_guard_argomenti: default, maiuscole e spazi, fuori elenco, troppi');

SELECT results_eq(
    $$SELECT c.codice::text, c.classe::text, m.messaggio IS NOT NULL
        FROM config.codici_errore c
        LEFT JOIN config.messaggi_errore m ON m.codice = c.codice AND m.lingua = 'it'
       WHERE c.codice IN ('E_SORG_CHIAVE_NON_CONFORME', 'E_SORG_RIGA_NON_DEL_DOCUMENTO',
                          'E_SORG_DETTAGLIO_NON_DELLA_RIGA', 'E_SORG_LIVELLO_NON_PREVISTO',
                          'E_SORG_LIVELLO_MANCANTE')
       ORDER BY 1$$,
    $$VALUES ('E_SORG_CHIAVE_NON_CONFORME', 'TECNICO', true),
             ('E_SORG_DETTAGLIO_NON_DELLA_RIGA', 'TECNICO', true),
             ('E_SORG_LIVELLO_MANCANTE', 'TECNICO', true),
             ('E_SORG_LIVELLO_NON_PREVISTO', 'TECNICO', true),
             ('E_SORG_RIGA_NON_DEL_DOCUMENTO', 'TECNICO', true)$$,
    '23) i cinque codici nuovi sono a catalogo, TECNICO, con il messaggio');

SELECT ok(
    pg_temp.messaggio_errore(pg_temp.ins('_prov', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), NULL, (SELECT r3 FROM _b), NULL))
        LIKE 'La riga % non è una riga del documento di origine DDT_VENDITA %'
    AND strpos(pg_temp.messaggio_errore(pg_temp.ins('_prov', (SELECT ddt FROM _t), (SELECT ddt1 FROM _b), NULL, (SELECT r3 FROM _b), NULL)), '%s') = 0,
    '24) la frase di E_SORG_RIGA_NON_DEL_DOCUMENTO si compone, senza segnaposti grezzi');

SELECT * FROM finish();
ROLLBACK;
