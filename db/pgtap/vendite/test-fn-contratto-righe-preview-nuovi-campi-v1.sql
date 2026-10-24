-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_contratto_righe_preview — 4 nuove colonne output
--       Migration: 20260519-07
--       (quantita, qta_operativa, tipo_erogazione, fonte_quantita_attesa)
--
-- Indice test (1..8):
--   Struttura:
--   1) RETURNS TABLE contiene colonna fonte_quantita_attesa (migration 07 applicata)
--   2) Fixture setup OK (contratto DRAFT + versione listino ATTIVA + 4 articoli)
--
--   Comportamento per origine DA_LISTINO (articolo seq=1, nessuna eccezione):
--   3) quantita IS NULL        (LEFT JOIN su cr → NULL)
--   4) tipo_erogazione IS NULL (LEFT JOIN su cr → NULL)
--
--   Comportamento per OVERRIDE (articolo seq=2, eccezione con valori noti):
--   5) fonte_quantita_attesa = 'FISSA'
--   6) tipo_erogazione = 'UNA_TANTUM' (rev 2026-10-07: era CANONE, fuori perimetro)
--
--   Comportamento per AGGIUNTA standalone:
--   7) CONSUMO + MANUALE → fonte_quantita_attesa = 'MANUALE' (articolo seq=3; rev 2026-10-07)
--   8) UNA_TANTUM + MANUALE → fonte_quantita_attesa = 'MANUALE' (articolo seq=4; rev 2026-10-07, B-D5)
--
-- Note:
--   Trigger trgfn_qta_from_operativa esige qta_operativa NOT NULL su INSERT solo con
--   la fonte FISSA (E_QTA_MISSING).
--   ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §D.4 punto 2,
--   20261007-28/-30): con una fonte a valle (MANUALE, LETTURE, TIMESHEET) la riga NON
--   porta quantita': lo dice il DB (E_RIGA_QUANTITA_CON_FONTE_A_VALLE e i CHECK
--   chk_*_quantita_per_fonte), non piu' il solo backend. Le AGGIUNTE MANUALE dei
--   test 7 e 8 nascono quindi senza quantita'.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ============================================================
-- Setup fixture
-- ============================================================

-- Contesto base: un billing_account, UoM, e stati doc
-- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): la tipologia
--   degli articoli del listino dev'essere fra quelle della utility del cliente.
-- 2026-10-08 (stesso brief, §F.2): il listino del documento e' della sua utility e del
--   suo emittente (guard nuovo). Il cliente si COSTRUISCE sulla prima utility che ammette
--   la tipologia del listino copiato (il primo attivo), legato dal z90 all'emittente di
--   chi agisce; prima era il primo billing account di quella utility fra i dati, con
--   l'emittente che i dati gli davano.
CREATE TEMP TABLE tmp_prv_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'preview nuovi campi',
    (SELECT ltu.utility_id FROM config.listini_tipologie_utilities ltu
      WHERE ltu.attivo
        AND ltu.tipologia_id = (SELECT l.tipologia_id FROM vendite.listini l
                                 WHERE l.attivo = TRUE ORDER BY l.id LIMIT 1)
      ORDER BY ltu.utility_id LIMIT 1));

CREATE TEMP TABLE tmp_prv_ctx AS
SELECT
    c.billing_account_id    AS ba_id,
    c.istanza_utility_id,
    c.utility_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT' LIMIT 1) AS id_draft,
    (SELECT id FROM catalogo.unita_misura WHERE attivo = TRUE ORDER BY id LIMIT 1) AS uom_id
FROM tmp_prv_cli c;

-- 4 articoli standalone distinti (non compositi)
-- ⚠️ Rev 2026-10-07 (giro B3): seq 1-2 stanno nel listino, quindi hanno la sua tipologia
--   (le righe di listino lo pretendono); seq 3-4 sono AGGIUNTE, senza tipologia (decide la
--   natura) e con le combinazioni del test nel PERIMETRO, chiesto alla sede unica.
CREATE TEMP TABLE tmp_prv_arts AS
WITH t AS (
    SELECT l.tipologia_id FROM vendite.listini l WHERE l.attivo = TRUE ORDER BY l.id LIMIT 1
), lis AS (
    SELECT a.id FROM catalogo.articoli a, t
     WHERE a.attivo = TRUE AND a.is_composito = FALSE
       AND a.listino_tipologia_id = t.tipologia_id
       AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                    WHERE e.tipo_erogazione = 'UNA_TANTUM' AND e.fonte_quantita_attesa = 'FISSA')
     ORDER BY a.id LIMIT 2
), agg AS (
    SELECT a.id FROM catalogo.articoli a
     WHERE a.attivo = TRUE AND a.is_composito = FALSE
       AND a.listino_tipologia_id IS NULL
       AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                    WHERE e.tipo_erogazione = 'CONSUMO' AND e.fonte_quantita_attesa = 'MANUALE')
       AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                    WHERE e.tipo_erogazione = 'UNA_TANTUM' AND e.fonte_quantita_attesa = 'MANUALE')
     ORDER BY a.id LIMIT 2
)
SELECT x.id AS articolo_id, ROW_NUMBER() OVER (ORDER BY x.ord, x.id) AS seq
  FROM (SELECT id, 1 AS ord FROM lis UNION ALL SELECT id, 2 FROM agg) x;

-- Listino con codice univoco (suffisso random)
CREATE TEMP TABLE tmp_prv_listino AS
WITH ins AS (
    INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP_PRV_' || substr(gen_random_uuid()::text, 1, 8),
           'Test preview nuovi campi', (SELECT utility_id FROM tmp_prv_ctx), l.tipologia_id,
           script.fn_pgtap_emittente_sr_operatore()
      FROM vendite.listini l
     WHERE l.attivo = TRUE
     ORDER BY l.id
     LIMIT 1
    RETURNING id
)
SELECT id FROM ins;

-- Versione ATTIVA con valido_dal nel passato → validita @> script.fn_data_operativa() = TRUE
-- Necessario perché fn_contratto_righe_preview fa lookup con validita @> script.fn_data_operativa().
CREATE TEMP TABLE tmp_prv_ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, stato)
    SELECT id,
           'PGTAP-PRV-V1-' || substr(gen_random_uuid()::text, 1, 4),
           '2020-01-01'::date,
           'ATTIVA'
      FROM tmp_prv_listino
    RETURNING id
)
SELECT id FROM ins;

-- 2 righe listino: articoli seq=1 (nessuna eccezione → DA_LISTINO)
--                               seq=2 (avrà OVERRIDE)
INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, a.articolo_id, ctx.uom_id, 100.00
  FROM tmp_prv_ver v, tmp_prv_arts a, tmp_prv_ctx ctx
 WHERE a.seq IN (1, 2);

-- Contratto DRAFT collegato al listino (listino_versione_id = NULL → lookup operativo)
CREATE TEMP TABLE tmp_prv_contratto AS
WITH ins AS (
    INSERT INTO vendite.contratti (
        numero, billing_account_id, istanza_utility_id, utility_id,
        stato_doc_contratto_id, listino_id, valido_dal, valido_al
    )
    SELECT 'PGTAP_PRV_CNT_' || substr(gen_random_uuid()::text, 1, 6),
           ctx.ba_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.id_draft, l.id,
           '2026-01-01'::date, '2026-12-31'::date
      FROM tmp_prv_ctx ctx, tmp_prv_listino l
     WHERE ctx.ba_id IS NOT NULL AND ctx.id_draft IS NOT NULL
    RETURNING id
)
SELECT id FROM ins;

-- OVERRIDE per articolo seq=2: valori noti per i test 5 e 6.
-- Entrambi qta_operativa e uom_operativa_id valorizzati → trigger early return,
-- quantita resta 3 come inserita.
INSERT INTO vendite.contratti_righe (
    contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
    tipo_erogazione, fonte_quantita_attesa,
    quantita, qta_operativa, uom_operativa_id
)
SELECT c.id, a.articolo_id, 'OVERRIDE', 80.00,
       'UNA_TANTUM', 'FISSA',
       3, 3, ctx.uom_id
  FROM tmp_prv_contratto c, tmp_prv_arts a, tmp_prv_ctx ctx
 WHERE a.seq = 2 AND c.id IS NOT NULL;

-- AGGIUNTA standalone: articolo seq=3, CONSUMO + MANUALE (test 7; rev 2026-10-07: le LETTURE
--   le ammette solo una tipologia a contatore)
-- qta_operativa e uom_operativa_id NON NULL → trigger early return.
INSERT INTO vendite.contratti_righe (
    contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
    tipo_erogazione, fonte_quantita_attesa,
    qta_operativa, uom_operativa_id
)
SELECT c.id, a.articolo_id, 'AGGIUNTA', 50.00,
       'CONSUMO', 'MANUALE',
       NULL, ctx.uom_id
  FROM tmp_prv_contratto c, tmp_prv_arts a, tmp_prv_ctx ctx
 WHERE a.seq = 3 AND c.id IS NOT NULL;

-- AGGIUNTA standalone: articolo seq=4 (test 8)
-- ⚠️ Rev 2026-10-07 (giro B3, decisione B-D5): DERIVATA_COMPONENTI e' del solo composito,
--   e seq=4 non lo e'. Il test prova che fonte e quantita' della riga arrivano alla preview:
--   UNA_TANTUM/MANUALE con quantita' 5 lo prova ugualmente. La fonte derivata sul composito
--   la prova vendite/offerte_commerciali/test_offerte_eccezioni_componenti.
-- ⚠️ Rev 2026-10-21 (brief-db-offerta-emissione-ed-erogazione §I.1, I-D1): DERIVATA_COMPONENTI
--   e' ritirata; il composito si eroga solo con la FISSA (I-D6). Solo commento.
-- ⚠️ Rev 2026-10-07 (§D.4 punto 2): MANUALE e' a valle, la riga nasce senza
--   quantita' (prima: quantita 5, qta_operativa 1). Il test 8 legge la fonte.
INSERT INTO vendite.contratti_righe (
    contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
    tipo_erogazione, fonte_quantita_attesa,
    quantita, qta_operativa, uom_operativa_id
)
SELECT c.id, a.articolo_id, 'AGGIUNTA', 100.00,
       'UNA_TANTUM', 'MANUALE',
       NULL, NULL, ctx.uom_id
  FROM tmp_prv_contratto c, tmp_prv_arts a, tmp_prv_ctx ctx
 WHERE a.seq = 4 AND c.id IS NOT NULL;

-- Cattura i risultati della preview per i test comportamentali.
CREATE TEMP TABLE tmp_prv_rows AS
SELECT *
  FROM vendite.fn_contratto_righe_preview(
      (SELECT id FROM tmp_prv_contratto LIMIT 1)
  );

-- ============================================================
SELECT plan(8);
-- ============================================================

-- ============================================================
-- 1) Struttura: la migrazione 07 ha aggiunto fonte_quantita_attesa al RETURNS TABLE
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1
          FROM pg_catalog.pg_proc p
          JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'vendite'
           AND p.proname = 'fn_contratto_righe_preview'
           AND pg_get_function_result(p.oid) LIKE '%fonte_quantita_attesa%'
    ),
    '1) RETURNS TABLE contiene fonte_quantita_attesa (migration 20260519-07)'
);

-- ============================================================
-- 2) Fixture setup OK
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM tmp_prv_contratto WHERE id IS NOT NULL)
    AND (SELECT COUNT(*) FROM tmp_prv_arts) >= 4
    AND EXISTS(SELECT 1 FROM tmp_prv_ver WHERE id IS NOT NULL),
    '2) fixture: contratto DRAFT + versione listino ATTIVA + 4 articoli disponibili'
);

-- ============================================================
-- 3) DA_LISTINO puro (articolo seq=1, nessuna eccezione): quantita IS NULL
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_rows WHERE origine = 'DA_LISTINO')
    THEN skip('3) nessuna riga DA_LISTINO nella preview — skip')
    ELSE is(
        (SELECT pr.quantita
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 1
          LIMIT 1),
        NULL::numeric,
        '3) DA_LISTINO puro (seq=1): quantita IS NULL (LEFT JOIN su cr → NULL)'
    )
END;

-- ============================================================
-- 4) DA_LISTINO puro (articolo seq=1): tipo_erogazione IS NULL
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_rows WHERE origine = 'DA_LISTINO')
    THEN skip('4) nessuna riga DA_LISTINO nella preview — skip')
    ELSE is(
        (SELECT pr.tipo_erogazione
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 1
          LIMIT 1),
        NULL::varchar,
        '4) DA_LISTINO puro (seq=1): tipo_erogazione IS NULL (LEFT JOIN su cr → NULL)'
    )
END;

-- ============================================================
-- 5) OVERRIDE (articolo seq=2): fonte_quantita_attesa = 'FISSA'
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_rows WHERE origine = 'OVERRIDE')
    THEN skip('5) nessuna riga OVERRIDE nella preview — skip')
    ELSE is(
        (SELECT pr.fonte_quantita_attesa
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 2
          LIMIT 1),
        'FISSA',
        '5) OVERRIDE (seq=2): fonte_quantita_attesa = FISSA (da cr.fonte_quantita_attesa)'
    )
END;

-- ============================================================
-- 6) OVERRIDE (articolo seq=2): tipo_erogazione = 'UNA_TANTUM'
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_rows WHERE origine = 'OVERRIDE')
    THEN skip('6) nessuna riga OVERRIDE nella preview — skip')
    ELSE is(
        (SELECT pr.tipo_erogazione
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 2
          LIMIT 1),
        'UNA_TANTUM',
        '6) OVERRIDE (seq=2): tipo_erogazione = UNA_TANTUM (da cr.tipo_erogazione)'
    )
END;

-- ============================================================
-- 7) AGGIUNTA CONSUMO+MANUALE (articolo seq=3): fonte = 'MANUALE'
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_arts WHERE seq = 3)
    THEN skip('7) meno di 3 articoli disponibili — skip AGGIUNTA MANUALE')
    ELSE is(
        (SELECT pr.fonte_quantita_attesa
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 3
          LIMIT 1),
        'MANUALE',
        '7) AGGIUNTA standalone CONSUMO+MANUALE (seq=3): fonte_quantita_attesa = MANUALE'
    )
END;

-- ============================================================
-- 8) AGGIUNTA UNA_TANTUM+MANUALE (articolo seq=4): la fonte arriva alla preview
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_prv_arts WHERE seq = 4)
    THEN skip('8) meno di 4 articoli disponibili — skip AGGIUNTA UNA_TANTUM+MANUALE')
    ELSE is(
        (SELECT pr.fonte_quantita_attesa
           FROM tmp_prv_rows pr
           JOIN tmp_prv_arts a ON a.articolo_id = pr.articolo_id AND a.seq = 4
          LIMIT 1),
        'MANUALE',
        '8) AGGIUNTA standalone UNA_TANTUM+MANUALE (seq=4): fonte_quantita_attesa = MANUALE'
    )
END;

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
