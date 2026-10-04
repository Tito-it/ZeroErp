-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_push_offerta_a_contratto(p_offerta_id, p_pratica_id) (Step 8).
--       Push 1:1 offerta ACCETTATA -> contratto DRAFT.
--       Idempotenza obbligatoria: doppia invocazione -> E_OFFERTA_CONTRATTO_GIA_GENERATO.
--       Mutua esclusivita' (rev6): se l'offerta ha gia' un ordine -> E_OFFERTA_ORDINE_GIA_GENERATO.
--
-- Indice test (1..9):
--   1)  Funzione fn_push_offerta_a_contratto presente
--   2)  Push da ACCETTATA: contratto DRAFT generato
--   3)  contratto.offerta_id valorizzato e contratto.sorgente_uid = offerta.uid
--   4)  Utility copiata 1:1 (contratti_utilities ha 1 record per il contratto)
--   5)  Doppia invocazione su stessa offerta -> throws E_OFFERTA_CONTRATTO_GIA_GENERATO
--   6)  Push da BOZZA -> throws E_OFFERTA_PUSH_STATO_NON_AMMESSO
--   7)  Push da EMESSA -> throws E_OFFERTA_PUSH_STATO_NON_AMMESSO
--   8)  Push da RIFIUTATA -> throws E_OFFERTA_PUSH_STATO_NON_AMMESSO
--   9)  Push da ACCETTATA con ordine gia' generato (mutua esclusivita') ->
--       throws E_OFFERTA_ORDINE_GIA_GENERATO
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(10);

-- ============================================================
-- Setup fixture
-- ============================================================
CREATE TEMP TABLE tmp_push_ctx AS
SELECT
    (SELECT ba.id FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id)
      ORDER BY ba.id LIMIT 1) AS billing_account_id,
    (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id)
      ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
    (SELECT ba.utility_id FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id)
      ORDER BY ba.id LIMIT 1) AS utility_id,
    (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
    (SELECT l.id FROM vendite.listini l WHERE l.attivo IS TRUE ORDER BY l.id LIMIT 1) AS listino_id,
    (SELECT lv.id FROM vendite.listini_versioni lv WHERE lv.stato = 'ATTIVA' ORDER BY lv.id LIMIT 1) AS listino_versione_id_attiva,
    (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE ORDER BY a.id LIMIT 1) AS articolo_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA') AS stato_accettata_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'RIFIUTATA') AS stato_rifiutata_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT')   AS stato_draft_contratto_id,
    (SELECT id FROM config.sorgenti WHERE codice_interno = 'OFFERTA_COMMERCIALE') AS sorgente_ofc_id;

-- Offerta principale: BOZZA -> EMESSA -> ACCETTATA (per tests 2-5)
CREATE TEMP TABLE tmp_push_offerta_acc AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, validita_al,
        stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2098-01-01', DATE '2098-12-31',
           ctx.stato_bozza_id
      FROM tmp_push_ctx ctx
    RETURNING id, uid
)
SELECT id, uid FROM ins;

-- ⚠️ rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende, R5a): le righe
--   dell'offerta si scrivono solo in BOZZA (trg_offerte_commerciali_eccezioni_a05_
--   doc_bozza_ins_upd_dlt). L'eccezione nasce quindi PRIMA delle transizioni,
--   come in un'offerta vera; prima la si aggiungeva a offerta gia' ACCETTATA.
-- Eccezione OVERRIDE sull'offerta (per verificare che il push copi le righe)
INSERT INTO vendite.offerte_commerciali_eccezioni (
    offerta_id, articolo_id, tipo_eccezione,
    tipo_erogazione, fonte_quantita_attesa,
    prezzo_unitario, attivo
)
SELECT acc.id, ctx.articolo_id, 'OVERRIDE'::"vendite"."tipo_eccezione_contratto",
       'UNA_TANTUM', 'MANUALE', 200.00, TRUE
  FROM tmp_push_offerta_acc acc, tmp_push_ctx ctx
 WHERE ctx.articolo_id IS NOT NULL;

-- BOZZA -> EMESSA -> ACCETTATA
UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_push_ctx)
 WHERE id = (SELECT id FROM tmp_push_offerta_acc);

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_accettata_id FROM tmp_push_ctx)
 WHERE id = (SELECT id FROM tmp_push_offerta_acc);

-- Utility dell'offerta (per verifica copia 1:1)
INSERT INTO vendite.offerte_commerciali_utilities (
    offerta_id, istanza_utility_id, utility_id
)
SELECT acc.id, ctx.istanza_utility_id, ctx.utility_id
  FROM tmp_push_offerta_acc acc, tmp_push_ctx ctx;

-- Offerta in BOZZA (per test 6)
CREATE TEMP TABLE tmp_push_offerta_bozza AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, NULL, DATE '2099-01-01', ctx.stato_bozza_id
      FROM tmp_push_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

-- Offerta in EMESSA (per test 7)
CREATE TEMP TABLE tmp_push_offerta_emessa AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2100-01-01', ctx.stato_bozza_id
      FROM tmp_push_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_push_ctx)
 WHERE id = (SELECT id FROM tmp_push_offerta_emessa);

-- Offerta in RIFIUTATA (per test 8): bypassata via INSERT diretto
CREATE TEMP TABLE tmp_push_offerta_rif AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2101-01-01', ctx.stato_rifiutata_id
      FROM tmp_push_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

-- Offerta in ACCETTATA con ORDINE gia' generato (per test 9): INSERT diretto in
-- ACCETTATA + ordine collegato via documento_origine ('OFFERTA', id).
CREATE TEMP TABLE tmp_push_offerta_ord AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2102-01-01', ctx.stato_accettata_id
      FROM tmp_push_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

-- GUC vuota: l'INSERT su vendite.ordini supera i guard emittente/scope senza
-- restrizione (stesso approccio del test fn_available_actions_offerta).
-- ⛔ 2026-09-04 — QUI IL TEST SPEGNEVA IL GUARD, e adesso non piu'.
--   La riga rimossa era `set_config('app.current_user_id', '', true)`: senza
--   utente in sessione `script.trgfn_guard_emittente_scope` usciva subito con
--   RETURN NEW, e le fixture entravano senza che nessuno guardasse l'emittente.
--   La fase 6 di `brief-db-processi-automatici-identita-e-perimetro` chiude quel
--   ramo — una sessione applicativa senza utente non scrive piu'.
--   ⇒ Il contesto operatore del preambolo RESTA valido per tutto il file, e le
--     fixture prendono l'emittente su cui quell'operatore puo' davvero scrivere
--     (`script.fn_pgtap_emittente_operatore()`).
--   ⭐ Non e' una riparazione di comodo: prima questo file collaudava il
--     comportamento di una porta aperta, adesso attraversa il guard come lo
--     attraversa l'applicazione.

-- Ordine collegato all'offerta (documento_origine OFFERTA). BA=NULL + emittente
-- esplicito = niente guard emittente<->BA da soddisfare.
INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza,
    documento_origine_tipo, documento_origine_id
)
SELECT
    (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1),
    NULL::bigint,
    ctx.emittente_fiscale_id,
    (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT' AND attivo IS TRUE LIMIT 1),
    (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1),
    DATE '2102-01-02', false,
    'OFFERTA', (SELECT id FROM tmp_push_offerta_ord)
  FROM tmp_push_ctx ctx;

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'vendite'
           AND p.proname = 'fn_push_offerta_a_contratto'
    ),
    '1) vendite.fn_push_offerta_a_contratto presente'
);

-- ============================================================
-- 2) Push da ACCETTATA: contratto DRAFT generato
-- ============================================================
CREATE TEMP TABLE tmp_push_contratto_id AS
SELECT vendite.fn_push_offerta_a_contratto(
    (SELECT id FROM tmp_push_offerta_acc),
    NULL::bigint
) AS contratto_id;

SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.contratti c
          JOIN tmp_push_contratto_id tc ON c.id = tc.contratto_id
          JOIN tmp_push_ctx ctx ON TRUE
         WHERE c.stato_doc_contratto_id = ctx.stato_draft_contratto_id
    ),
    '2) fn_push_offerta_a_contratto: contratto creato in stato DRAFT'
);

-- ============================================================
-- 3) contratto.offerta_id valorizzato + sorgente_uid = offerta.uid
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.contratti c
          JOIN tmp_push_contratto_id tc ON c.id = tc.contratto_id
          JOIN tmp_push_offerta_acc oa ON TRUE
          JOIN tmp_push_ctx ctx ON TRUE
         WHERE c.offerta_id   = oa.id
           AND c.sorgente_uid = oa.uid
           AND c.sorgente_tipo_id = ctx.sorgente_ofc_id
    ),
    '3) contratto.offerta_id, sorgente_uid e sorgente_tipo_id valorizzati correttamente'
);

-- ============================================================
-- 4) Utility copiata 1:1 (contratti_utilities ha 1 record per il contratto)
-- ============================================================
SELECT ok(
    (SELECT COUNT(*) = 1
       FROM vendite.contratti_utilities cu
       JOIN tmp_push_contratto_id tc ON cu.contratto_id = tc.contratto_id),
    '4) utility copiata 1:1: contratti_utilities ha 1 record per il contratto DRAFT'
);

-- ============================================================
-- 5) Doppia invocazione -> throws E_OFFERTA_CONTRATTO_GIA_GENERATO
-- ============================================================
SELECT throws_ok(
    format(
        $q$SELECT vendite.fn_push_offerta_a_contratto(%s, NULL::bigint)$q$,
        (SELECT id FROM tmp_push_offerta_acc)
    ),
    'P0001', NULL,
    '5) Doppia invocazione su stessa offerta ACCETTATA -> throws E_OFFERTA_CONTRATTO_GIA_GENERATO (idempotenza pattern A)'
);

-- ============================================================
-- 6) Push da BOZZA -> throws E_OFFERTA_PUSH_STATO_NON_AMMESSO
-- ============================================================
SELECT throws_ok(
    format(
        $q$SELECT vendite.fn_push_offerta_a_contratto(%s, NULL::bigint)$q$,
        (SELECT id FROM tmp_push_offerta_bozza)
    ),
    'P0001', NULL,
    '6) Push da BOZZA -> throws E_OFFERTA_PUSH_STATO_NON_AMMESSO'
);

-- ============================================================
-- 7) Push da EMESSA -> throws E_OFFERTA_PUSH_STATO_NON_AMMESSO
-- ============================================================
SELECT throws_ok(
    format(
        $q$SELECT vendite.fn_push_offerta_a_contratto(%s, NULL::bigint)$q$,
        (SELECT id FROM tmp_push_offerta_emessa)
    ),
    'P0001', NULL,
    '7) Push da EMESSA -> throws E_OFFERTA_PUSH_STATO_NON_AMMESSO'
);

-- ============================================================
-- 8) Push da RIFIUTATA -> throws E_OFFERTA_PUSH_STATO_NON_AMMESSO
-- ============================================================
SELECT throws_ok(
    format(
        $q$SELECT vendite.fn_push_offerta_a_contratto(%s, NULL::bigint)$q$,
        (SELECT id FROM tmp_push_offerta_rif)
    ),
    'P0001', NULL,
    '8) Push da RIFIUTATA -> throws E_OFFERTA_PUSH_STATO_NON_AMMESSO'
);

-- ============================================================
-- 9) Push da ACCETTATA con ordine gia' generato (mutua esclusivita') ->
--    throws E_OFFERTA_ORDINE_GIA_GENERATO. Contratto e ordine sono alternativi:
--    l'offerta ha gia' un ordine ('OFFERTA', id) -> il push a contratto fallisce.
-- ============================================================
SELECT throws_ok(
    format(
        $q$SELECT vendite.fn_push_offerta_a_contratto(%s, NULL::bigint)$q$,
        (SELECT id FROM tmp_push_offerta_ord)
    ),
    'P0001', NULL,
    '9) Push da ACCETTATA con ordine gia generato -> throws E_OFFERTA_ORDINE_GIA_GENERATO (mutua esclusivita)'
);

-- ============================================================
-- 10) ⭐ IL BERSAGLIO — e NON e' l'offerta.
--     Il rifiuto di idempotenza deve dire dove andare, e dove andare e' il
--     CONTRATTO gia' generato: l'offerta l'operatore ce l'ha davanti, e' da
--     li' che ha premuto il pulsante.
--     ⚠️ Il verbo in un'istruzione separata dall'asserzione, come sempre.
--     Brief: brief-db-bersaglio-errore §6 L6.
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.push_off_bersaglio(p_offerta_id bigint)
RETURNS text AS $fn$
-- ⚠️ `text` esplicito: e' un canale dell'eccezione, non il valore di una colonna.
DECLARE v_bers text;
BEGIN
  PERFORM vendite.fn_push_offerta_a_contratto(p_offerta_id, NULL::bigint);
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_bers = PG_DATATYPE_NAME;
  RETURN COALESCE(v_bers, '');
END $fn$ LANGUAGE plpgsql;

CREATE TEMP TABLE tmp_push_bersaglio AS
SELECT pg_temp.push_off_bersaglio((SELECT id FROM tmp_push_offerta_acc)) AS bersaglio;

SELECT is(
    (SELECT bersaglio FROM tmp_push_bersaglio),
    'CONTRATTO:' || (SELECT contratto_id FROM tmp_push_contratto_id)::text,
    '10) il rifiuto porta il bersaglio sul CONTRATTO gia'' generato, non sull''offerta'
);

SELECT * FROM finish();
ROLLBACK;
