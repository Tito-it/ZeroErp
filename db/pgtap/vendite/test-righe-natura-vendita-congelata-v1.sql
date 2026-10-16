-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La natura di vendita di una riga e' quella con cui e' stata venduta:
-- nasce con la riga (dall'articolo, o dal documento d'origine), cambia solo
-- col cambio di articolo, e viaggia lungo preventivo -> ordine -> bolla anche
-- quando l'articolo, nel frattempo, ha cambiato natura in anagrafica.
-- Brief: brief-db-articoli-ammessi-per-documento (§8.6 A-4, §9.2)
-- ChangeSet: 20261013-07 -> -14
--
-- Elenco test (plan 15):
--  Struttura
--   1) ordini_righe.natura_vendita_id NOT NULL
--   2) ddt_righe.natura_vendita_id NOT NULL
--  Preventivo (modo ARTICOLO)
--   3) la natura viene dall'articolo, anche se chi scrive ne porta un'altra
--   4) l'articolo cambia natura: un UPDATE della riga non la tocca
--   5) scriverla a mano: E_RIGA_NATURA_VENDITA_IMMUTABILE (lock di colonna)
--  Preventivo -> ordine (fn_push_preventivo_a_ordine)
--   6) la riga d'ordine porta la natura del preventivo, non quella di oggi
--  Ordine (modo CHIAMANTE)
--   7) riga scritta a mano senza natura: quella dell'articolo
--   8) riga scritta con una natura: resta quella portata
--   9) un UPDATE con lo stesso articolo non la tocca
--  10) cambio di articolo verso un servizio: la natura si ricalcola dal nuovo
--      articolo, e la regola dell'ordine (solo merce, 20261013-42) la rifiuta
--  11) scriverla a mano: E_RIGA_NATURA_VENDITA_IMMUTABILE (lock di colonna)
--  Ordine -> bolla (fn_genera_ddt_da_ordine)
--  12) la riga di bolla porta la natura della riga d'ordine, non quella di oggi
--  Bolla (modo CHIAMANTE)
--  13) riga scritta a mano senza natura: quella dell'articolo
--  14) scriverla a mano: E_RIGA_NATURA_VENDITA_IMMUTABILE (lock di colonna)
--  Porta di manutenzione
--  15) dalla porta del lock (allow_lock_columns_override) la natura si scrive:
--      il BB non la rimette a OLD (20261013-14)
--
-- ⚠️ I test 5, 11 e 14 provano il lock di colonna, che e' un trigger GENERATO
--   da dbops.automation_lock_columns: in CI lo crea ci_apply, su dbdev il giro
--   delle automazioni (job delle 21:00, o
--   CALL maintenance.proc_automations_lock_columns_job()). Prima di quel giro
--   sono rossi su dbdev per costruzione.
-- La riconsegna (fn_genera_ddt_riconsegna) e' provata in
-- test-fn-genera-ddt-riconsegna-eredita-v1 (test 17), che costruisce il reso.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture
-- ============================================================
-- Le nature per destinazione, come le leggono le regole.
CREATE TEMP TABLE _nat AS
SELECT (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'ORDINE' AND nv.attivo ORDER BY nv.id LIMIT 1)   AS merce,
       (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'COMMESSA' AND nv.attivo ORDER BY nv.id LIMIT 1) AS servizio;

-- Tre articoli: M nasce merce e poi diventa servizio; S servizio; X merce.
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-NATC-M', false,
           p_natura_vendita_id => (SELECT merce FROM _nat))    AS m,
       dbops.fn_pgtap_crea_articolo('PGT-NATC-S', false,
           p_natura_vendita_id => (SELECT servizio FROM _nat)) AS s,
       dbops.fn_pgtap_crea_articolo('PGT-NATC-X', false,
           p_natura_vendita_id => (SELECT merce FROM _nat))    AS x;

CREATE TEMP TABLE _iva AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1) AS id;

CREATE TEMP TABLE _prev AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP natura congelata');

-- ============================================================
-- Struttura (1-2)
-- ============================================================
SELECT col_not_null('vendite', 'ordini_righe', 'natura_vendita_id',
    '1) ordini_righe.natura_vendita_id NOT NULL');
SELECT col_not_null('vendite', 'ddt_righe', 'natura_vendita_id',
    '2) ddt_righe.natura_vendita_id NOT NULL');

-- ============================================================
-- Preventivo (3-5)
-- ============================================================
CREATE TEMP TABLE _pr AS
WITH ins AS (
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id,
                                          prezzo_unitario, qta_operativa, natura_vendita_id)
    SELECT (SELECT preventivo_id FROM _prev), (SELECT m FROM _art), (SELECT id FROM _iva),
           10, 2, (SELECT servizio FROM _nat)
    RETURNING id, natura_vendita_id
)
SELECT * FROM ins;

SELECT is((SELECT natura_vendita_id FROM _pr), (SELECT merce FROM _nat),
    '3) preventivo: la natura viene dall''articolo, non da chi scrive');

-- Da qui M e' un servizio in anagrafica: le righe gia' scritte non lo sanno.
-- ⛔ rev 2026-10-13 (A-10): M e' gia' usato (la riga di preventivo), e un
--   articolo usato non cambia natura; il caso resta vero dalla porta
--   amministratore, e il builder passa dal verbo.
SELECT dbops.fn_pgtap_articolo_correggi_struttura(
    (SELECT m FROM _art), jsonb_build_object('natura_vendita_id', (SELECT servizio FROM _nat)));

UPDATE vendite.preventivi_righe SET qta_operativa = 3 WHERE id = (SELECT id FROM _pr);

SELECT is((SELECT natura_vendita_id FROM vendite.preventivi_righe WHERE id = (SELECT id FROM _pr)),
          (SELECT merce FROM _nat),
    '4) preventivo: l''articolo cambia natura, un UPDATE della riga non la tocca');

SELECT throws_like(
    format($$UPDATE vendite.preventivi_righe SET natura_vendita_id = %s WHERE id = %s$$,
           (SELECT servizio FROM _nat), (SELECT id FROM _pr)),
    '%natura di vendita della riga non%',
    '5) preventivo: scriverla a mano e'' rifiutato (E_RIGA_NATURA_VENDITA_IMMUTABILE)');

-- ============================================================
-- Preventivo -> ordine (6)
-- ============================================================
SELECT dbops.fn_pgtap_porta_a_stato('vendite.preventivi'::regclass,
                                    (SELECT preventivo_id FROM _prev), 'ACCETTATO');

CREATE TEMP TABLE _ord AS
SELECT vendite.fn_push_preventivo_a_ordine((SELECT preventivo_id FROM _prev)) AS id;

CREATE TEMP TABLE _or AS
SELECT orr.id, orr.natura_vendita_id
  FROM vendite.ordini_righe orr
 WHERE orr.preventivo_riga_id = (SELECT id FROM _pr);

SELECT is((SELECT natura_vendita_id FROM _or), (SELECT merce FROM _nat),
    '6) push: la riga d''ordine porta la natura del preventivo, non quella che l''articolo ha oggi');

-- ============================================================
-- Ordine (7-11)
-- ============================================================
CREATE TEMP TABLE _or_man AS
WITH ins AS (
    INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, iva_id,
                                      prezzo_unitario, qta_operativa)
    SELECT (SELECT id FROM _ord), 90, (SELECT x FROM _art), 'pgTAP riga a mano', (SELECT id FROM _iva), 5, 1
    RETURNING id, natura_vendita_id
)
SELECT * FROM ins;

SELECT is((SELECT natura_vendita_id FROM _or_man), (SELECT merce FROM _nat),
    '7) ordine: riga scritta senza natura, prende quella dell''articolo');

CREATE TEMP TABLE _or_port AS
WITH ins AS (
    INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, iva_id,
                                      prezzo_unitario, qta_operativa, natura_vendita_id)
    SELECT (SELECT id FROM _ord), 91, (SELECT s FROM _art), 'pgTAP riga con natura', (SELECT id FROM _iva), 5, 1,
           (SELECT merce FROM _nat)
    RETURNING id, natura_vendita_id
)
SELECT * FROM ins;

SELECT is((SELECT natura_vendita_id FROM _or_port), (SELECT merce FROM _nat),
    '8) ordine: riga scritta con una natura, resta quella portata (modo CHIAMANTE)');

UPDATE vendite.ordini_righe SET qta_operativa = 4 WHERE id = (SELECT id FROM _or);

SELECT is((SELECT natura_vendita_id FROM vendite.ordini_righe WHERE id = (SELECT id FROM _or)),
          (SELECT merce FROM _nat),
    '9) ordine: un UPDATE con lo stesso articolo non la tocca');

-- 🔴 rev 2026-10-13 (Lotto 3a): fino al -42 il test 10 cambiava l'articolo
--   della riga d'ordine in un servizio e leggeva la natura nuova. Da quando
--   l'ordine porta solo merce (D-1), su un ordine non c'e' un'altra natura
--   ammessa: il ricalcolo si vede dal rifiuto, che giudica la natura del
--   NUOVO articolo (se il BB non la ricalcolasse, la riga resterebbe merce e
--   passerebbe).
SELECT throws_like(
    format($$UPDATE vendite.ordini_righe SET articolo_id = %L WHERE id = %s$$,
           (SELECT s FROM _art), (SELECT id FROM _or_man)),
    '%vanno solo merci%',
    '10) ordine: cambio di articolo verso un servizio, la natura ricalcolata e'' rifiutata');

SELECT throws_like(
    format($$UPDATE vendite.ordini_righe SET natura_vendita_id = %s WHERE id = %s$$,
           (SELECT servizio FROM _nat), (SELECT id FROM _or)),
    '%natura di vendita della riga non%',
    '11) ordine: scriverla a mano e'' rifiutato (E_RIGA_NATURA_VENDITA_IMMUTABILE)');

-- ============================================================
-- Ordine -> bolla (12)
-- ============================================================
-- Solo la riga venuta dal preventivo: le altre due servono ai test sopra.
UPDATE vendite.ordini_righe SET attivo = false
 WHERE id IN ((SELECT id FROM _or_man), (SELECT id FROM _or_port));

SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini'::regclass, (SELECT id FROM _ord), 'CONFERMATO');

CREATE TEMP TABLE _ddt AS
SELECT vendite.fn_genera_ddt_da_ordine((SELECT id FROM _ord)) AS id;

SELECT is(
    (SELECT dr.natura_vendita_id
       FROM vendite.ordini_righe_fulfillment f
       JOIN vendite.ddt_righe dr ON dr.id = f.ddt_riga_id
      WHERE f.ordine_riga_id = (SELECT id FROM _or)),
    (SELECT merce FROM _nat),
    '12) genera bolla: la riga porta la natura della riga d''ordine, non quella di oggi');

-- ============================================================
-- Bolla (13-14)
-- ============================================================
CREATE TEMP TABLE _dr_man AS
WITH ins AS (
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa)
    SELECT (SELECT id FROM _ddt), 90, (SELECT x FROM _art), 'pgTAP riga a mano', 1
    RETURNING id, natura_vendita_id
)
SELECT * FROM ins;

SELECT is((SELECT natura_vendita_id FROM _dr_man), (SELECT merce FROM _nat),
    '13) bolla: riga scritta senza natura, prende quella dell''articolo');

SELECT throws_like(
    format($$UPDATE vendite.ddt_righe SET natura_vendita_id = %s WHERE id = %s$$,
           (SELECT servizio FROM _nat), (SELECT id FROM _dr_man)),
    '%natura di vendita della riga non%',
    '14) bolla: scriverla a mano e'' rifiutato (E_RIGA_NATURA_VENDITA_IMMUTABILE)');

-- ============================================================
-- Porta di manutenzione (15)
-- ============================================================
-- ⭐ La regola «non si scrive a mano» sta SOLO nel lock di colonna, con la sua
--   porta (zeroerp.allow_lock_columns_override). Il -08 la richiudeva in
--   silenzio rimettendo OLD a parita' di articolo; tolto dal 20261013-14.
--   La porta serve: la riga di preventivo a natura NULL (pregresso, colonna
--   nullable) si costruisce solo da qui (test-vw-preventivi-smistamento-v1).
--   Preventivo nuovo, in bozza: quello di sopra e' gia' ACCETTATO.
CREATE TEMP TABLE _prev_porta AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP natura porta');

CREATE TEMP TABLE _pr_porta AS
WITH ins AS (
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, iva_id,
                                          prezzo_unitario, qta_operativa)
    SELECT (SELECT preventivo_id FROM _prev_porta), (SELECT s FROM _art), (SELECT id FROM _iva),
           10, 1
    RETURNING id
)
SELECT * FROM ins;

SET LOCAL zeroerp.allow_lock_columns_override = 'on';
UPDATE vendite.preventivi_righe SET natura_vendita_id = NULL WHERE id = (SELECT id FROM _pr_porta);
SET LOCAL zeroerp.allow_lock_columns_override = 'off';

SELECT is((SELECT natura_vendita_id FROM vendite.preventivi_righe WHERE id = (SELECT id FROM _pr_porta)),
          NULL::bigint,
    '15) preventivo: dalla porta di manutenzione del lock la natura si scrive (il BB non la rimette a OLD)');

SELECT * FROM finish();
ROLLBACK;
