-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- pgtap-runner: owner
-- pgtap-runner-motivo: RI-COLLOCATO col Lotto 2 (brief-db-magazzino-lotto-2-motore,
--   D-L2-b, sezione 7). Il soggetto sono i VINCOLI del ledger (CHECK, UNIQUE,
--   guard tipizzato, guard del verso), che si fanno scattare con INSERT
--   DIRETTI su magazzino.movimenti — e dal Lotto 2 l'app ha SELECT soltanto:
--   scrive solo la primitiva (DEFINER del proprietario). Come app ogni INSERT
--   darebbe 42501 prima del vincolo: e' la forma 3 del criterio del runner
--   («il test collauda un guard che solo uno scrittore privilegiato puo' far
--   scattare»). Le asserzioni sono INVARIATE; il contesto operatore resta
--   impostato (i guard di scope e le fixture lo vogliono). Il comportamento
--   della primitiva ha i suoi file (test-fn-scrivi-movimento-*).
--
-- Test: i vincoli del ledger magazzino.movimenti nella forma decisa dal
--   Lotto 1 (brief-db-magazzino-lotto-1-terreno-vuoto, sezioni 4.4, 4.9, 7).
--   SOSTITUISCE test-movimenti-vincoli-v1, che asseriva i CHECK sulle coppie
--   magazzino_id_dest / ubicazione_from-to e scriveva doc_*: colonne che il
--   20260915-05 elimina — quel file era rosso per costruzione.
--
-- ⚠️ Fixture COSTRUITA (regola zero, corollario sui test): il dominio e' vuoto
--   e un test che pesca dalla popolazione e' muto in CI. Azienda + operatore
--   dall'helper, magazzino con quell'emittente, lotto, asset, un inventario
--   con una riga (la sorgente INVENTARIO_RIGA) e un trasferimento con una riga
--   (la sorgente TRASFERIMENTO_RIGA della coppia OUT/IN).
-- ⚠️ Girava come l'applicazione fino al Lotto 2; ora come owner (vedi il
--   marcatore in testa). Il contesto operatore e' impostato lo stesso: il
--   guard di scope di magazzini e del ledger legge le GUC, e l'operatore ha
--   l'emittente nel perimetro perche' e' l'helper a darglielo.
--
-- Elenco test (plan 16):
--   La sorgente e' obbligatoria e a catalogo (D-1, D-6, D-9):
--    1) senza sorgente_tipo_id -> 23502 (NOT NULL)
--    2) sorgente_tipo_id inesistente -> il guard tipizzato (E_SORG_CONF), non la FK
--    3) sorgente_riga verso un record che non c'e' -> E_SORG_NOT_FOUND
--    4) nessuna chiave -> E_SORG_KEY_MISSING (il BEFORE ROW oscura il CHECK)
--    5) entrambe le chiavi -> 23514 chk_mag_movimenti_sorgente_chiave
--   Lotto e seriale sono chiavi (M-5):
--    6) asset con |qta| <> 1 -> 23514 chk_mag_movimenti_asset_qta_unitaria
--   Il verso sta nella quantita' (M-1):
--    7) qta = 0 -> P0001 dal guard del verso, NON 23514
--    8) ...e il CHECK qta <> 0 esiste ancora in pg_constraint (seconda rete)
--    9) verso incoerente (carico con qta negativa) -> la frase di E_MAG_MOVIMENTO_VERSO_INCOERENTE
--   L'identita' e' l'operazione-per-tranche (D-4, D-L1-c):
--   10) il movimento buono passa
--   11) la stessa operazione scritta due volte -> 23505 uq_mag_movimenti_identita (NULLS NOT DISTINCT)
--   12) stessa sorgente, tranche diversa (lotto) -> passa
--   13) le due righe OUT/IN di un trasferimento NON collidono (causali diverse)
--   Lo storno (M-8):
--   14) storno_di_movimento_id: il primo storno passa
--   15) ...il secondo sullo stesso movimento -> 23505 uq_mag_movimenti_storno_di
--   La forma:
--   16) le colonne del riferimento libero e delle coppie non esistono piu'
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture
-- ============================================================
-- ⚠️ Azienda e operatore COSTRUITI, e il contesto puntato su di lui: senza,
--   il guard di scope di magazzini rifiuterebbe la scrittura (P-7).
CREATE TEMP TABLE _mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo));
END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

CREATE TEMP TABLE _fix (
    mag_a  bigint, mag_b bigint, art uuid, lotto bigint, asset bigint,
    inv_riga bigint, trasf_riga bigint,
    cau_inv bigint, cau_out bigint, cau_in bigint, cau_storno_neg bigint,
    src_inv bigint, src_trasf bigint
);

DO $fix$
DECLARE
    v_ef   magazzino.magazzini.emittente_fiscale_id%TYPE;
    v_ind  anagrafiche.indirizzi_dettaglio.id%TYPE;
    v_art  catalogo.articoli.id%TYPE;
    v_ma   magazzino.magazzini.id%TYPE;
    v_mb   magazzino.magazzini.id%TYPE;
    v_lot  magazzino.lotti.id%TYPE;
    v_ast  magazzino.assets.id%TYPE;
    v_inv  magazzino.inventari.id%TYPE;
    v_ir   magazzino.inventari_righe.id%TYPE;
    v_tr   magazzino.trasferimenti.id%TYPE;
    v_trr  magazzino.trasferimenti_righe.id%TYPE;
BEGIN
    SELECT emittente_fiscale_id INTO v_ef FROM _mondo;
    -- ⚠️ ORDER BY sempre: senza, la riga che esce dipende dal planner.
    -- L'indirizzo si FABBRICA (dato di macchina: zero righe su un DB da zero);
    -- l'articolo e' uno dei seed ONERE_* di catalogo, presente per contratto.
    v_ind := dbops.fn_pgtap_crea_indirizzo_dettaglio('vincoli v2');
    SELECT a.id INTO v_art FROM catalogo.articoli a WHERE a.attivo ORDER BY a.id LIMIT 1;
    IF v_art IS NULL THEN
        RAISE EXCEPTION 'fixture: serve almeno un articolo attivo (seed di catalogo)';
    END IF;

    v_ma := magazzino.fn_crea_magazzino('PGT-MV2-A', 'pgTAP movimenti v2 A', v_ind, '{}'::jsonb, v_ef);
    v_mb := magazzino.fn_crea_magazzino('PGT-MV2-B', 'pgTAP movimenti v2 B', v_ind, '{}'::jsonb, v_ef);

    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo)
    VALUES (v_art, 'PGT-L-1', script.fn_data_operativa()) RETURNING id INTO v_lot;

    INSERT INTO magazzino.assets (articolo_id, seriale, stato_id, ownership_id, emittente_fiscale_id)
    VALUES (v_art, 'PGT-SN-' || v_ma::text,
            (SELECT s.id FROM config.stati_assets s WHERE s.attivo ORDER BY s.id LIMIT 1),
            (SELECT o.id FROM config.assets_ownership o WHERE o.attivo ORDER BY o.id LIMIT 1),
            v_ef)
    RETURNING id INTO v_ast;

    -- Le sorgenti: una riga di inventario e una riga di trasferimento.
    INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_ma) RETURNING id INTO v_inv;
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata)
    VALUES (v_inv, v_art, 5) RETURNING id INTO v_ir;
    INSERT INTO magazzino.trasferimenti (magazzino_id_from, magazzino_id_to)
    VALUES (v_ma, v_mb) RETURNING id INTO v_tr;
    INSERT INTO magazzino.trasferimenti_righe (trasferimento_id, articolo_id, qta)
    VALUES (v_tr, v_art, 2) RETURNING id INTO v_trr;

    INSERT INTO _fix
    SELECT v_ma, v_mb, v_art, v_lot, v_ast, v_ir, v_trr,
           (SELECT id FROM magazzino.causali WHERE codice_interno = 'INV_INIZIALE'),
           (SELECT id FROM magazzino.causali WHERE codice_interno = 'TRASF_OUT'),
           (SELECT id FROM magazzino.causali WHERE codice_interno = 'TRASF_IN'),
           (SELECT id FROM magazzino.causali WHERE codice_interno = 'STORNO_NEG'),
           (SELECT id FROM config.sorgenti WHERE codice_interno = 'INVENTARIO_RIGA'),
           (SELECT id FROM config.sorgenti WHERE codice_interno = 'TRASFERIMENTO_RIGA');
END $fix$;

-- ============================================================
-- 1..5 La sorgente
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_riga)
       SELECT art, mag_a, cau_inv, 5, inv_riga FROM _fix $$,
    '23502', NULL,
    '1) senza sorgente_tipo_id: NOT NULL — non esiste un movimento senza operazione (D-6)');

SELECT throws_like(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga)
       SELECT art, mag_a, cau_inv, 5, 999999, inv_riga FROM _fix $$,
    '%Configurazione sorgente mancante%',
    '2) sorgente_tipo_id inesistente: parla il guard tipizzato (E_SORG_CONF), prima della FK');

SELECT throws_like(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga)
       SELECT art, mag_a, cau_inv, 5, src_inv, 999999999 FROM _fix $$,
    '%Riferimento sorgente non trovato%',
    '3) sorgente_riga verso un record che non c''e'': E_SORG_NOT_FOUND');

SELECT throws_like(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id)
       SELECT art, mag_a, cau_inv, 5, src_inv FROM _fix $$,
    '%Chiave sorgente mancante%',
    '4) nessuna chiave: E_SORG_KEY_MISSING — il BEFORE ROW oscura il CHECK');

SELECT throws_ok(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga, sorgente_uid)
       SELECT art, mag_a, cau_inv, 5, src_inv, inv_riga, gen_random_uuid() FROM _fix $$,
    '23514', NULL,
    '5) entrambe le chiavi: chk_mag_movimenti_sorgente_chiave (esattamente una)');

-- ============================================================
-- 6 Lotto e seriale sono chiavi
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga, asset_id)
       SELECT art, mag_a, cau_inv, 5, src_inv, inv_riga, asset FROM _fix $$,
    '23514', NULL,
    '6) con un asset la quantita'' e'' uno: chk_mag_movimenti_asset_qta_unitaria');

-- ============================================================
-- 7..9 Il verso
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga)
       SELECT art, mag_a, cau_inv, 0, src_inv, inv_riga FROM _fix $$,
    'P0001', NULL,
    '7) qta = 0: parla il guard del verso (P0001), non il CHECK (23514)');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_constraint
             WHERE conrelid = 'magazzino.movimenti'::regclass
               AND conname  = 'chk_mag_movimenti_qta_non_zero'),
    '8) ...e chk_mag_movimenti_qta_non_zero esiste ancora: la seconda rete');

SELECT throws_like(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga)
       SELECT art, mag_a, cau_inv, -5, src_inv, inv_riga FROM _fix $$,
    '%Verso incoerente%INV_INIZIALE%',
    '9) carico con quantita'' negativa: la frase di E_MAG_MOVIMENTO_VERSO_INCOERENTE, con la causale');

-- ============================================================
-- 10..13 L'identita'
-- ============================================================
SELECT lives_ok(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga)
       SELECT art, mag_a, cau_inv, 5, src_inv, inv_riga FROM _fix $$,
    '10) il movimento buono (inventario iniziale +5 dalla riga di inventario) passa');

SELECT throws_ok(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga)
       SELECT art, mag_a, cau_inv, 5, src_inv, inv_riga FROM _fix $$,
    '23505', NULL,
    '11) la stessa operazione scritta due volte collide: uq_mag_movimenti_identita, NULLS NOT DISTINCT');

SELECT lives_ok(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga, lotto_id)
       SELECT art, mag_a, cau_inv, 3, src_inv, inv_riga, lotto FROM _fix $$,
    '12) stessa sorgente, tranche diversa (un lotto): passa');

SELECT lives_ok(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga, transfer_uid)
       SELECT art, mag_a, cau_out, -2, src_trasf, trasf_riga, '00000000-0000-0000-0000-00000000aa01'::uuid FROM _fix
       UNION ALL
       SELECT art, mag_b, cau_in,   2, src_trasf, trasf_riga, '00000000-0000-0000-0000-00000000aa01'::uuid FROM _fix $$,
    '13) le due righe OUT/IN di un trasferimento non collidono: la causale e'' il verbo (D-L1-c)');

-- ============================================================
-- 14..15 Lo storno
-- ============================================================
SELECT lives_ok(
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga, storno_di_movimento_id)
       SELECT f.art, f.mag_a, f.cau_storno_neg, -5, f.src_inv, f.inv_riga,
              (SELECT m.id FROM magazzino.movimenti m WHERE m.magazzino_id = f.mag_a AND m.qta = 5 AND m.lotto_id IS NULL ORDER BY m.id LIMIT 1)
         FROM _fix f $$,
    '14) lo storno del carico: causale STORNO_NEG, quantita'' opposta, legame al movimento');

SELECT throws_ok(
    -- ⚠️ Tranche DIVERSA (il lotto): cosi' l'identita' non collide e l'unico
    --   vincolo che puo' parlare e' uq_mag_movimenti_storno_di.
    $$ INSERT INTO magazzino.movimenti (articolo_id, magazzino_id, causale_id, qta, sorgente_tipo_id, sorgente_riga, storno_di_movimento_id, lotto_id)
       SELECT f.art, f.mag_a, f.cau_storno_neg, -5, f.src_inv, f.inv_riga,
              (SELECT m.id FROM magazzino.movimenti m WHERE m.magazzino_id = f.mag_a AND m.qta = 5 AND m.lotto_id IS NULL ORDER BY m.id LIMIT 1),
              f.lotto
         FROM _fix f $$,
    '23505', NULL,
    '15) un movimento si storna una volta sola: uq_mag_movimenti_storno_di');

-- ============================================================
-- 16 La forma
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM pg_attribute
      WHERE attrelid = 'magazzino.movimenti'::regclass AND NOT attisdropped
        AND attname IN ('doc_schema', 'doc_table', 'doc_id', 'doc_riga_id',
                        'lotto', 'seriale', 'magazzino_id_dest',
                        'ubicazione_id_from', 'ubicazione_id_to', 'attivo', 'uom_id')),
    0,
    '16) il riferimento libero, lotto/seriale testo, le coppie, attivo e uom_id non esistono piu''');

SELECT * FROM finish();
ROLLBACK;
