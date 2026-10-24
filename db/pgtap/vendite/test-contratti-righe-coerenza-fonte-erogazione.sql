-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.contratti_righe — coerenza fonte_quantita_attesa × tipo_erogazione
--       Migrations: 20260519-05 (backfill + NOT NULL + CHECK), 20260519-06 (trigger normalize)
--
-- Indice test (1..15):
--   Struttura:
--   1) fonte_quantita_attesa obbligatoria sulle righe che non sono ESCLUSIONE (CHECK)
--   2) FK fk_contratti_righe_erogazione_fonte su config.erogazioni_fonti presente
--      (20261007-54: la matrice e' un dato, i CHECK si sono ritirati)
--   3) Trigger trg_contratti_righe_a10_default_fonte_qta_ins_upd presente
--   4) Setup fixture OK (contratto DRAFT + almeno 1 articolo trovato)
--
--   Comportamento della FK — 7 combinazioni fuori vocabolario (skip se no fixture):
--   5)  CANONE     + TIMESHEET  → raises P0001 (perimetro)
--   6)  CANONE     + LETTURE    → raises P0001 (perimetro)
--   7)  UNA_TANTUM + TIMESHEET  → raises P0001 (perimetro)
--   8)  UNA_TANTUM + LETTURE    → raises P0001 (perimetro)
--   9)  ORARIO     + LETTURE    → raises P0001 (perimetro)
--   10) CONSUMO    + FISSA      → raises P0001 (perimetro)
--   11) CONSUMO    + TIMESHEET  → raises P0001 (perimetro)
--
--   Comportamento normalize trigger — INSERT (skip se < 4 articoli):
--   12) INSERT CANONE  + fonte NULL → la fonte dell'articolo (FISSA)
--   13) INSERT CONSUMO + fonte NULL → la fonte dell'articolo (LETTURE)
--   14) INSERT ORARIO → rifiutato: nessuno lo ammette (rev 2026-10-07)
--
--   Comportamento normalize trigger — UPDATE tipo (skip se < 4 articoli):
--   15) UPDATE tipo CANONE→CONSUMO, fonte=FISSA → la fonte dell'articolo (MANUALE)
--
--   TG_ARGV[3] fonte_nullability_col — trgfn_qta_from_operativa (migration 20260519-08/09):
--   16) INSERT AGGIUNTA CONSUMO+LETTURE, qta_operativa NULL → no raise (fonte governa)
--   17) INSERT AGGIUNTA CANONE+FISSA,   qta_operativa NULL → E_QTA_MISSING (comportamento invariato)
-- ------------------------------------------------------------
--
-- Nota sui test CHECK (5-11):
--   Fonte ESPLICITA vietata (non NULL): normalize non tocca valori non-NULL su INSERT.
--   ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.7, giro B1): la
--   matrice non e' piu' un CHECK ma config.erogazioni_fonti, e la riga vi si lega con
--   la FK fk_contratti_righe_erogazione_fonte → errore atteso 23503 (era 23514).
--   ⚠️ Rev 2026-10-07 (sera, giro B3): prima della FK parla il guard del PERIMETRO
--   dell'articolo (script.trgfn_righe_guard_erogazione_perimetro): ogni combinazione di
--   tipologie e nature sta nel vocabolario, quindi una fuori vocabolario e' anche fuori
--   perimetro → P0001 col codice E_RIGA_EROGAZIONE_FUORI_PERIMETRO. La FK resta la rete
--   (presenza: test 2), non piu' raggiungibile da una scrittura normale.
--
-- Nota sui test normalize (12-15):
--   I WITH-DML devono stare al top-level (non dentro CASE — vincolo PG).
--   Setup esegue gli INSERT/UPDATE nella sezione fixture; le assertions usano
--   CASE WHEN NOT EXISTS su tmp_norm_fonte (skippa se fixture indisponibile).
--   Usa 4 articoli distinti (seq 1-4) per rispettare uq_contrighe_one_aggiunta_per_articolo.
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
-- ⭐ Rev 2026-10-07: il mondo si COSTRUISCE, non si cerca. Prima il file prendeva
--   il primo billing account e i primi articoli attivi del database: su
--   zeroerp_ci ricostruito da zero (nessun billing account) i casi 5-17 finivano
--   nello skip, e su dbdev l'articolo dei casi 5-11 era lo stesso del caso 12
--   (vedi sotto). Ora il cliente con il suo billing account viene da
--   dbops.fn_pgtap_crea_cliente_ba, e i sette articoli da
--   dbops.fn_pgtap_crea_articolo, uno per ruolo:
--     n = 0      casi 5-11 (le combinazioni fuori vocabolario)
--     n = 1..4   casi 12-15 (normalize)
--     n = 5..6   casi 16-17 (qta_operativa NULL)
--   ⛔ Un articolo per ruolo, e nessuno in comune: uq_contrighe_one_aggiunta_per_articolo
--   vieta due AGGIUNTA sullo stesso (contratto, articolo). Prima l'articolo dei
--   casi 5-11 era anche quello del caso 12, quindi aveva gia' un'AGGIUNTA. Finche'
--   la matrice era un CHECK, il CHECK scattava prima dell'indice univoco (23514);
--   dal 20261007-54 e' una FK, che scatta DOPO: vinceva l'unique (23505) e la FK
--   non veniva mai esercitata.

-- ⚠️ Rev 2026-10-07 (sera, brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): la
--   riga sta nel PERIMETRO dell'articolo (vendite.fn_articolo_erogazioni). L'articolo del
--   builder e' MERCE senza tipologia, che ammette solo UNA_TANTUM: a ogni ruolo si da',
--   alla nascita, la classificazione che ammette la combinazione del suo caso. Il cliente
--   e' ENE (prima utility), che ammette la tipologia CONSUMO.
--     n = 0     MERCE: le sette combinazioni fuori vocabolario sono anche fuori perimetro
--     n = 1, 4, 6  natura SERVIZIO_RICORRENTE: CANONE/FISSA (e CONSUMO/MANUALE)
--     n = 2, 5  tipologia CONSUMO: CONSUMO/LETTURE
--     n = 3     MERCE: ORARIO non lo ammette nessuno (non esposto, brief §B.4)
CREATE TEMP TABLE tmp_fonte_arts AS
SELECT g AS n, dbops.fn_pgtap_crea_articolo('PGTAP-FONTE-EROG-' || g,
           p_listino_tipologia_id => CASE WHEN g IN (2, 5) THEN
               (SELECT id FROM config.listini_tipologie WHERE codice = 'CONSUMO') END,
           p_natura_vendita_id    => CASE WHEN g IN (1, 4, 6) THEN
               (SELECT id FROM config.nature_vendita
                 WHERE codice_interno = 'SERVIZIO_RICORRENTE') END) AS articolo_id
  FROM generate_series(0, 6) g;

CREATE TEMP TABLE tmp_fonte_ctx AS
SELECT
    ba.billing_account_id   AS ba_id,
    ba.istanza_utility_id,
    ba.utility_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT' LIMIT 1) AS id_draft,
    (SELECT articolo_id FROM tmp_fonte_arts WHERE n = 0) AS articolo_id
FROM dbops.fn_pgtap_crea_cliente_ba('pgTAP fonte erogazione') ba;

-- Contratto DRAFT senza listino (date 2075 per non collidere con altri pgTAP)
INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_FONTE_CNT', c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2075-01-01'::date, '2075-12-31'::date
FROM tmp_fonte_ctx c
WHERE c.ba_id IS NOT NULL AND c.id_draft IS NOT NULL;

-- 4 articoli distinti per i test normalize (12-15).
CREATE TEMP TABLE tmp_norm_arts AS
SELECT articolo_id, n AS seq FROM tmp_fonte_arts WHERE n BETWEEN 1 AND 4;

-- ============================================================
-- Pre-esecuzione test normalize 12-15:
-- Gli INSERT/UPDATE con WITH-DML devono stare al top level (non dentro CASE).
-- La tabella tmp_norm_fonte raccoglie (test_num, fonte_value) da RETURNING.
-- Il CASE WHEN NOT EXISTS delle asserzioni resta come rete: con la fixture
-- costruita una riga mancante e' un difetto, e lo skip lo direbbe.
-- ============================================================

CREATE TEMP TABLE tmp_norm_fonte (test_num int, fonte_value text);

-- Test 12: CANONE + fonte NULL → aspettato FISSA (articolo seq=1)
WITH ins AS (
    INSERT INTO vendite.contratti_righe
        (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, prezzo_unitario, qta_operativa)
    SELECT c.id, na.articolo_id, 'AGGIUNTA', 'CANONE', 100, 1
      FROM vendite.contratti c, tmp_norm_arts na
     WHERE c.numero = 'PGTAP_FONTE_CNT' AND na.seq = 1
    RETURNING fonte_quantita_attesa
)
INSERT INTO tmp_norm_fonte SELECT 12, fonte_quantita_attesa FROM ins;

-- Test 13: CONSUMO + fonte NULL → aspettato LETTURE (articolo seq=2)
-- ⚠️ Rev 2026-10-07 (20261007-28/-30, §D.4 punto 2): LETTURE e' una fonte a valle,
--   la riga non porta quantita' → qta_operativa NULL.
WITH ins AS (
    INSERT INTO vendite.contratti_righe
        (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, prezzo_unitario, qta_operativa)
    SELECT c.id, na.articolo_id, 'AGGIUNTA', 'CONSUMO', 100, NULL
      FROM vendite.contratti c, tmp_norm_arts na
     WHERE c.numero = 'PGTAP_FONTE_CNT' AND na.seq = 2
    RETURNING fonte_quantita_attesa
)
INSERT INTO tmp_norm_fonte SELECT 13, fonte_quantita_attesa FROM ins;

-- Test 14: ORARIO (articolo seq=3) — rev 2026-10-07: nessuna tipologia ne' natura lo
--   ammette (non esposto, §B.4 del brief), quindi la riga e' RIFIUTATA dal guard del
--   perimetro: l'asserzione e' un throws, non piu' un INSERT di setup.

-- Test 15: INSERT CANONE+FISSA (articolo seq=4), poi UPDATE tipo→CONSUMO.
-- Rev 2026-10-07: CONSUMO+FISSA esce dal perimetro dell'articolo (SERVIZIO_RICORRENTE),
--   e la fonte diventa quella che l'ARTICOLO ammette per CONSUMO: MANUALE (prima: LETTURE,
--   il default del vocabolario, che la natura non ammette).
-- ⛔ Rev 2026-10-07: due istruzioni, non una. Con INSERT e UPDATE nella stessa
--   WITH l'UPDATE lavora sulla fotografia presa PRIMA dell'istruzione e non vede
--   la riga appena inserita: aggiornava zero righe, e il caso 15 finiva SEMPRE
--   nello skip («meno di 4 articoli»), anche con gli articoli.
CREATE TEMP TABLE tmp_riga_15 (id bigint);  -- vendite.contratti_righe.id (%TYPE non vale in DDL)

WITH ins AS (
    INSERT INTO vendite.contratti_righe
        (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
    SELECT c.id, na.articolo_id, 'AGGIUNTA', 'CANONE', 'FISSA', 100, 1
      FROM vendite.contratti c, tmp_norm_arts na
     WHERE c.numero = 'PGTAP_FONTE_CNT' AND na.seq = 4
    RETURNING id
)
INSERT INTO tmp_riga_15 SELECT id FROM ins;

-- ⚠️ Rev 2026-10-07 (§D.4 punto 2): la fonte riallineata (MANUALE) e' a valle, e la
--   quantita' della FISSA si svuota nello stesso UPDATE (altrimenti
--   E_RIGA_QUANTITA_CON_FONTE_A_VALLE: lo prova test-righe-quantita-per-fonte-v1).
WITH upd AS (
    UPDATE vendite.contratti_righe
       SET tipo_erogazione = 'CONSUMO', qta_operativa = NULL, quantita = NULL
     WHERE id IN (SELECT id FROM tmp_riga_15)
    RETURNING fonte_quantita_attesa
)
INSERT INTO tmp_norm_fonte SELECT 15, fonte_quantita_attesa FROM upd;

-- ============================================================
-- Articoli per test 16/17 (fuori da tmp_norm_arts e dai casi 5-11)
-- Servono per INSERT separati: unica AGGIUNTA per (contratto, articolo).
CREATE TEMP TABLE tmp_fonte_arts_ext AS
SELECT articolo_id, n - 4 AS seq FROM tmp_fonte_arts WHERE n IN (5, 6);
-- ============================================================

-- ============================================================
SELECT plan(17);
-- ============================================================

-- ============================================================
-- 1) fonte_quantita_attesa obbligatoria, tranne sull'ESCLUSIONE
-- ============================================================
-- rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R1): il NOT
--   NULL di 20260519-05 scende al CHECK chk_contrighe_fonte_per_tipo_eccezione.
--   Un'esclusione non ha fonte: non si fattura. La regola completa la prova
--   test-righe-esclusione-solo-non-si-vende-v1.
SELECT is(
    (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
      WHERE c.conrelid = 'vendite.contratti_righe'::regclass
        AND c.conname  = 'chk_contrighe_fonte_per_tipo_eccezione'),
    'CHECK (((tipo_eccezione = ''ESCLUSIONE''::vendite.tipo_eccezione_contratto) OR (fonte_quantita_attesa IS NOT NULL)))',
    '1) fonte_quantita_attesa obbligatoria sulle righe che non sono ESCLUSIONE (20261004-40)'
);

-- ============================================================
-- 2) FK sul vocabolario presente (rev 2026-10-07: era il CHECK
--    chk_contrighe_coerenza_fonte_erogazione, ritirato da 20261007-54)
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1 FROM pg_constraint c
         WHERE c.conrelid  = 'vendite.contratti_righe'::regclass
           AND c.conname   = 'fk_contratti_righe_erogazione_fonte'
           AND c.contype   = 'f'
           AND c.confrelid = 'config.erogazioni_fonti'::regclass
    ),
    '2) FK fk_contratti_righe_erogazione_fonte su config.erogazioni_fonti presente (20261007-54)'
);

-- ============================================================
-- 3) Trigger normalize presente
-- ============================================================
SELECT has_trigger(
    'vendite',
    'contratti_righe',
    'trg_contratti_righe_a10_default_fonte_qta_ins_upd',
    '3) trigger trg_contratti_righe_a10_default_fonte_qta_ins_upd presente (20260519-06)'
);

-- ============================================================
-- 4) Setup fixture OK
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
    AND EXISTS(SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL),
    '4) fixture: contratto PGTAP_FONTE_CNT creato e almeno un articolo di test trovato'
);

-- ============================================================
-- 5-11) FK — 7 combinazioni fuori vocabolario
-- ============================================================

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('5) fixture non disponibile — skip CANONE+TIMESHEET')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'CANONE', 'TIMESHEET', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        'P0001', NULL,
        '5) CANONE+TIMESHEET → rifiutata dal perimetro dell''articolo (P0001)'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('6) fixture non disponibile — skip CANONE+LETTURE')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'CANONE', 'LETTURE', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        'P0001', NULL,
        '6) CANONE+LETTURE → rifiutata dal perimetro dell''articolo (P0001)'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('7) fixture non disponibile — skip UNA_TANTUM+TIMESHEET')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'UNA_TANTUM', 'TIMESHEET', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        'P0001', NULL,
        '7) UNA_TANTUM+TIMESHEET → rifiutata dal perimetro dell''articolo (P0001)'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('8) fixture non disponibile — skip UNA_TANTUM+LETTURE')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'UNA_TANTUM', 'LETTURE', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        'P0001', NULL,
        '8) UNA_TANTUM+LETTURE → rifiutata dal perimetro dell''articolo (P0001)'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('9) fixture non disponibile — skip ORARIO+LETTURE')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'ORARIO', 'LETTURE', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        'P0001', NULL,
        '9) ORARIO+LETTURE → rifiutata dal perimetro dell''articolo (P0001)'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('10) fixture non disponibile — skip CONSUMO+FISSA')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'CONSUMO', 'FISSA', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        'P0001', NULL,
        '10) CONSUMO+FISSA → rifiutata dal perimetro dell''articolo (P0001)'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_ctx WHERE articolo_id IS NOT NULL)
    THEN skip('11) fixture non disponibile — skip CONSUMO+TIMESHEET')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, qta_operativa)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'CONSUMO', 'TIMESHEET', 100, 1)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_ctx)
        ),
        'P0001', NULL,
        '11) CONSUMO+TIMESHEET → rifiutata dal perimetro dell''articolo (P0001)'
    )
END;

-- ============================================================
-- 12-14) Normalize trigger — INSERT con fonte NULL
--         Gli INSERT sono stati eseguiti nel setup (CTE top-level).
--         tmp_norm_fonte contiene il risultato del RETURNING.
-- ============================================================

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_norm_fonte WHERE test_num = 12)
    THEN skip('12) meno di 1 articolo disponibile — skip normalize CANONE')
    ELSE is(
        (SELECT fonte_value FROM tmp_norm_fonte WHERE test_num = 12),
        'FISSA',
        '12) INSERT CANONE + fonte NULL → la fonte dell''articolo per CANONE (FISSA)'
    )
END;

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_norm_fonte WHERE test_num = 13)
    THEN skip('13) meno di 2 articoli disponibili — skip normalize CONSUMO')
    ELSE is(
        (SELECT fonte_value FROM tmp_norm_fonte WHERE test_num = 13),
        'LETTURE',
        '13) INSERT CONSUMO + fonte NULL → la fonte dell''articolo per CONSUMO (LETTURE)'
    )
END;

SELECT throws_ok(
    format($$INSERT INTO vendite.contratti_righe
               (contratto_id, articolo_id, tipo_eccezione, tipo_erogazione, prezzo_unitario, qta_operativa)
             SELECT c.id, na.articolo_id, 'AGGIUNTA', 'ORARIO', 100, 1
               FROM vendite.contratti c, tmp_norm_arts na
              WHERE c.numero = 'PGTAP_FONTE_CNT' AND na.seq = 3$$),
    'P0001', NULL,
    '14) ORARIO: nessuna tipologia ne'' natura lo ammette (non esposto) → rifiutato dal perimetro');

-- ============================================================
-- 15) Normalize trigger — UPDATE tipo_erogazione con combo vietata
--     L''INSERT CANONE+FISSA e l''UPDATE a CONSUMO sono stati eseguiti nel setup.
--     Il trigger ha resettato fonte da FISSA a LETTURE (CONSUMO+FISSA è ❌).
-- ============================================================

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_norm_fonte WHERE test_num = 15)
    THEN skip('15) meno di 4 articoli disponibili — skip normalize UPDATE tipo')
    ELSE is(
        (SELECT fonte_value FROM tmp_norm_fonte WHERE test_num = 15),
        'MANUALE',
        '15) UPDATE tipo CANONE→CONSUMO con fonte FISSA → la fonte diventa quella che l''articolo ammette (MANUALE)'
    )
END;

-- ============================================================
-- 16) TG_ARGV[3] fonte_nullability_col: CONSUMO+LETTURE, qta_operativa NULL → no raise
--     Il trigger trgfn_qta_from_operativa con arg[3]='fonte_quantita_attesa' legge
--     la colonna fonte. 'LETTURE' != 'FISSA' → RETURN NEW senza raise.
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_arts_ext WHERE seq = 1)
    THEN skip('16) fixture non disponibile — skip qta NULL + LETTURE no raise')
    ELSE lives_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione,
                 tipo_erogazione, fonte_quantita_attesa, prezzo_unitario)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'CONSUMO', 'LETTURE', 50)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_arts_ext WHERE seq = 1)
        ),
        '16) AGGIUNTA CONSUMO+LETTURE, qta_operativa NULL → no raise (TG_ARGV[3] fonte governa)'
    )
END;

-- ============================================================
-- 17) TG_ARGV[3] fonte_nullability_col: CANONE+FISSA, qta_operativa NULL → E_QTA_MISSING
--     'FISSA' = 'FISSA' → la fonte non autorizza NULL → cade nel raise.
--     Verifica che il comportamento preesistente su FISSA sia invariato.
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT')
      OR NOT EXISTS (SELECT 1 FROM tmp_fonte_arts_ext WHERE seq = 2)
    THEN skip('17) fixture non disponibile — skip qta NULL + FISSA raise')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe
                (contratto_id, articolo_id, tipo_eccezione,
                 tipo_erogazione, fonte_quantita_attesa, prezzo_unitario)
              VALUES (%s, %L::uuid, 'AGGIUNTA', 'CANONE', 'FISSA', 100)$$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_FONTE_CNT'),
            (SELECT articolo_id FROM tmp_fonte_arts_ext WHERE seq = 2)
        ),
        NULL, NULL,
        '17) AGGIUNTA CANONE+FISSA, qta_operativa NULL → raise E_QTA_MISSING (invariato)'
    )
END;

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
