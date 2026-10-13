-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: refactor quantita/qta_operativa su vendite.offerte_commerciali_eccezioni.
--       Migrations 20260531-07 (chk nonzero), 20260531-09 (fn generica
--       default fonte), 20260531-10 (bind default fonte offerte + rebind
--       contratti), 20260531-11 (bind qta_from_operativa su offerte).
--
-- L'offerta diventa lo specchio del contratto: stessa conversione UoM
-- (qta_operativa -> quantita) e stesso default fonte da tipo_erogazione.
--
-- Indice test (1..13):
--   Struttura/specularita':
--   1) trigger qta_from_operativa presente su offerte
--   2) trigger default_fonte presente su offerte
--   3) funzione generica script.trgfn_righe_default_fonte_qta presente
--   4) vecchia vendite.trgfn_contratti_righe_default_fonte_qta ASSENTE
--   5) trigger contratti ri-bindato alla funzione generica script.*
--   6) chk_offerte_eccezioni_qta_operativa_nonzero presente
--   Fixture:
--   7) offerta BOZZA creata + articoli di test
--   Comportamento:
--   8)  FISSA qta_operativa=5 -> quantita=5 (conversione, factor 1)
--   9)  default fonte: CANONE senza fonte -> trigger imposta FISSA
--   10) non-FISSA (CONSUMO+MANUALE) qta_operativa NULL -> no raise (fonte governa)
--   11) FISSA qta_operativa NULL -> E_QTA_MISSING (P0001)
--   12) factor!=1 (art ...0101/uom 2): qta_operativa=2, factor NULL -> quantita=12, snapshot=6
--   13) qta_operativa=0 -> check_violation 23514
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(13);

-- ============================================================
-- 1) trigger qta_from_operativa presente
-- ============================================================
SELECT has_trigger('vendite','offerte_commerciali_eccezioni',
    'trg_offerte_eccezioni_a10_qta_from_operativa_ins_upd',
    '1) trigger qta_from_operativa presente su offerte (20260531-11)');

-- ============================================================
-- 2) trigger default_fonte presente
-- ============================================================
SELECT has_trigger('vendite','offerte_commerciali_eccezioni',
    'trg_offerte_eccezioni_a10_default_fonte_qta_ins_upd',
    '2) trigger default_fonte presente su offerte (20260531-10)');

-- ============================================================
-- 3) funzione generica presente
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='script' AND p.proname='trgfn_righe_default_fonte_qta'),
    '3) script.trgfn_righe_default_fonte_qta presente (generica)');

-- ============================================================
-- 4) vecchia funzione vendite.* rimossa
-- ============================================================
SELECT ok(
    NOT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='vendite' AND p.proname='trgfn_contratti_righe_default_fonte_qta'),
    '4) vendite.trgfn_contratti_righe_default_fonte_qta rimossa (deduplicazione)');

-- ============================================================
-- 5) trigger contratti ri-bindato alla funzione generica
-- ============================================================
SELECT is(
    (SELECT n.nspname || '.' || p.proname
       FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
       JOIN pg_namespace n ON n.oid=p.pronamespace
      WHERE t.tgrelid='vendite.contratti_righe'::regclass
        AND t.tgname='trg_contratti_righe_a10_default_fonte_qta_ins_upd'),
    'script.trgfn_righe_default_fonte_qta',
    '5) trigger contratti default_fonte ri-bindato a script.trgfn_righe_default_fonte_qta');

-- ============================================================
-- 6) chk nonzero presente
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM pg_constraint c
             JOIN pg_class r ON r.oid=c.conrelid
             JOIN pg_namespace n ON n.oid=r.relnamespace
            WHERE n.nspname='vendite' AND r.relname='offerte_commerciali_eccezioni'
              AND c.conname='chk_offerte_eccezioni_qta_operativa_nonzero'),
    '6) chk_offerte_eccezioni_qta_operativa_nonzero presente');

-- ============================================================
-- Fixture: offerta BOZZA + articoli distinti (uq one_aggiunta_per_articolo)
-- ============================================================
-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): le righe
--   stanno nel PERIMETRO dell'articolo, e la sua tipologia dev'essere fra quelle della
--   utility del cliente. L'articolo f6 (UdM operativa a fattore 6, il cuore del test) si
--   sceglie PRIMA, fra quelli che ammettono UNA_TANTUM/FISSA, e il billing account e' il
--   primo la cui utility ne ammette la tipologia. Gli altri articoli sono senza tipologia
--   e ammettono UNA_TANTUM/FISSA. L'erogazione, CANONE per caso, ora e' UNA_TANTUM (stessa
--   fonte FISSA); il caso 10 passa da CONSUMO/LETTURE a CONSUMO/MANUALE, sempre «fonte non
--   FISSA», che e' cio' che il caso prova.
CREATE TEMP TABLE tmp_oe_f6 AS
SELECT (SELECT m.articolo_id FROM catalogo.articoli_uom_operativa m
       JOIN catalogo.articoli a ON a.id=m.articolo_id
      WHERE m.uom_id=2 AND m.factor_to_base=6 AND m.attivo IS TRUE AND a.attivo IS TRUE
        AND (m.valido_dal IS NULL OR m.valido_dal <= script.fn_data_operativa())
        AND (m.valido_al  IS NULL OR m.valido_al  >= script.fn_data_operativa())
        AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                     WHERE e.tipo_erogazione = 'UNA_TANTUM' AND e.fonte_quantita_attesa = 'FISSA')
      LIMIT 1) AS articolo_f6_id;

-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. La utility e' la prima che ammette la
--   tipologia dell'articolo f6 (lo stesso predicato del giro B3, prima sul BA);
--   il cliente, legato dal z90 all'emittente di chi agisce, e il listino nascono
--   su di lei.
CREATE TEMP TABLE tmp_oe_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'qta from operativa offerte',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (
            SELECT 1 FROM catalogo.articoli a
             WHERE a.id = (SELECT articolo_f6_id FROM tmp_oe_f6)
               AND a.listino_tipologia_id IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                                WHERE ltu.utility_id = u.id
                                  AND ltu.tipologia_id = a.listino_tipologia_id
                                  AND ltu.attivo))
        AND EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                     WHERE ltu.utility_id = u.id AND ltu.attivo)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_oe_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_oe_cli), 'qta from operativa offerte');

CREATE TEMP TABLE tmp_oe_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_oe_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_oe_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_oe_cli) AS utility_id,
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_oe_listino) AS listino_id,
    (SELECT listino_versione_id FROM tmp_oe_listino) AS listino_versione_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno='BOZZA') AS stato_bozza_id,
    (SELECT articolo_f6_id FROM tmp_oe_f6) AS articolo_f6_id;

-- 4 articoli distinti factor=1 (esclude ...0101) per gli INSERT AGGIUNTA
CREATE TEMP TABLE tmp_oe_arts AS
SELECT a.id AS articolo_id, ROW_NUMBER() OVER (ORDER BY a.id) AS seq
  FROM catalogo.articoli a
 WHERE a.attivo IS TRUE AND a.is_composito = FALSE
   AND a.id <> '00000000-0000-0000-0000-000000000101'::uuid
   AND NOT EXISTS (SELECT 1 FROM catalogo.articoli_uom_operativa m
                    WHERE m.articolo_id=a.id AND m.factor_to_base<>1)
   -- rev 2026-10-07 (giro B3): senza tipologia, e UNA_TANTUM/FISSA e CONSUMO/MANUALE
   --   nel perimetro (il caso 10 usa il seq 3 a consumo)
   AND a.listino_tipologia_id IS NULL
   AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                WHERE e.tipo_erogazione = 'UNA_TANTUM' AND e.fonte_quantita_attesa = 'FISSA')
   AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                WHERE e.tipo_erogazione = 'CONSUMO' AND e.fonte_quantita_attesa = 'MANUALE')
 ORDER BY a.id LIMIT 4;

INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, validita_al,
    stato_doc_offerta_id, meta)
SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
       ctx.listino_id, ctx.listino_versione_id, DATE '2097-01-01', DATE '2097-12-31',
       ctx.stato_bozza_id, jsonb_build_object('pgtap_oe','qta')
  FROM tmp_oe_ctx ctx
 WHERE ctx.billing_account_id IS NOT NULL AND ctx.stato_bozza_id IS NOT NULL;

SELECT ok(
    EXISTS(SELECT 1 FROM vendite.offerte_commerciali WHERE meta->>'pgtap_oe'='qta')
    AND (SELECT COUNT(*) FROM tmp_oe_arts) >= 4,
    '7) fixture: offerta BOZZA creata + 4 articoli di test');

-- ============================================================
-- 8-9 / 12) INSERT top-level con RETURNING in tmp_oe_res
-- ============================================================
CREATE TEMP TABLE tmp_oe_res (label text, quantita numeric, fonte text, factor_to_base numeric);

-- 8) FISSA esplicita, qta_operativa=5 -> quantita=5 (art seq=1)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali_eccezioni
        (offerta_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
    SELECT o.id, na.articolo_id, 'AGGIUNTA', 'UNA_TANTUM', 'FISSA', 100, 5
      FROM vendite.offerte_commerciali o, tmp_oe_arts na
     WHERE o.meta->>'pgtap_oe'='qta' AND na.seq=1
    RETURNING quantita, fonte_quantita_attesa, factor_to_base
)
INSERT INTO tmp_oe_res SELECT 'fissa5', quantita, fonte_quantita_attesa, factor_to_base FROM ins;

-- 9) default fonte: CANONE senza fonte -> FISSA (art seq=2)
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali_eccezioni
        (offerta_id, articolo_id, tipo_eccezione, tipo_erogazione, prezzo_unitario, qta_operativa)
    SELECT o.id, na.articolo_id, 'AGGIUNTA', 'UNA_TANTUM', 100, 1
      FROM vendite.offerte_commerciali o, tmp_oe_arts na
     WHERE o.meta->>'pgtap_oe'='qta' AND na.seq=2
    RETURNING quantita, fonte_quantita_attesa, factor_to_base
)
INSERT INTO tmp_oe_res SELECT 'deffonte', quantita, fonte_quantita_attesa, factor_to_base FROM ins;

-- 12) factor!=1 (art ...0101/uom 2): qta_operativa=2, factor NULL -> quantita=12, snapshot=6
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali_eccezioni
        (offerta_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa, uom_operativa_id)
    SELECT o.id, ctx.articolo_f6_id, 'AGGIUNTA', 'UNA_TANTUM', 'FISSA', 100, 2, 2
      FROM vendite.offerte_commerciali o, tmp_oe_ctx ctx
     WHERE o.meta->>'pgtap_oe'='qta' AND ctx.articolo_f6_id IS NOT NULL
    RETURNING quantita, fonte_quantita_attesa, factor_to_base
)
INSERT INTO tmp_oe_res SELECT 'f6', quantita, fonte_quantita_attesa, factor_to_base FROM ins;

SELECT is(
    (SELECT quantita FROM tmp_oe_res WHERE label='fissa5'),
    5::numeric,
    '8) FISSA qta_operativa=5 -> quantita=5 (conversione attiva sull''offerta)');

SELECT is(
    (SELECT fonte FROM tmp_oe_res WHERE label='deffonte'),
    'FISSA',
    '9) CANONE senza fonte -> default_fonte imposta FISSA (specularita'' contratto)');

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_oe_res WHERE label='f6')
    THEN skip('12) mapping factor!=1 (art ...0101/uom 2) non disponibile')
    ELSE ok(
        (SELECT quantita = 12 AND factor_to_base = 6 FROM tmp_oe_res WHERE label='f6'),
        '12) factor!=1: qta_operativa=2 -> quantita=12 e factor snapshot=6')
END;

-- ============================================================
-- 10) non-FISSA (CONSUMO+MANUALE) qta_operativa NULL -> no raise (art seq=3)
-- ============================================================
SELECT lives_ok(
    format(
        $$INSERT INTO vendite.offerte_commerciali_eccezioni
            (offerta_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario)
          VALUES (%s, %L::uuid, 'AGGIUNTA', 'CONSUMO', 'MANUALE', 50)$$,
        (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_oe'='qta'),
        (SELECT articolo_id FROM tmp_oe_arts WHERE seq=3)
    ),
    '10) CONSUMO+MANUALE, qta_operativa NULL -> no raise (fonte governa la nullabilita'')');

-- ============================================================
-- 11) FISSA qta_operativa NULL -> E_QTA_MISSING (art seq=4)
-- ============================================================
SELECT throws_ok(
    format(
        $$INSERT INTO vendite.offerte_commerciali_eccezioni
            (offerta_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario)
          VALUES (%s, %L::uuid, 'AGGIUNTA', 'UNA_TANTUM', 'FISSA', 100)$$,
        (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_oe'='qta'),
        (SELECT articolo_id FROM tmp_oe_arts WHERE seq=4)
    ),
    'P0001', NULL,
    '11) FISSA qta_operativa NULL -> E_QTA_MISSING (specularita'' contratto)');

-- ============================================================
-- 13) qta_operativa=0 -> check_violation 23514
-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b, A-5):
--   era un'OVERRIDE di un articolo fuori listino, scelta per non sbattere
--   sull'unicita' dell'AGGIUNTA dello stesso articolo; dal Lotto 3b l'OVERRIDE
--   pretende l'articolo nel listino e parlava prima del CHECK. Il soggetto e'
--   il CHECK: un'AGGIUNTA di un articolo costruito apposta (MERCE senza
--   tipologia: UNA_TANTUM/FISSA nel perimetro), che nessun listino contiene.
-- ============================================================
SELECT throws_ok(
    format(
        $$INSERT INTO vendite.offerte_commerciali_eccezioni
            (offerta_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
          VALUES (%s, %L::uuid, 'AGGIUNTA', 'UNA_TANTUM', 'FISSA', 100, 0)$$,
        (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_oe'='qta'),
        dbops.fn_pgtap_crea_articolo('PGT-OE-QZERO', false)
    ),
    '23514', NULL,
    '13) qta_operativa=0 -> chk_offerte_eccezioni_qta_operativa_nonzero (23514)');

SELECT * FROM finish();
ROLLBACK;
