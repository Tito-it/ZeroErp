-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-11-07 (brief-db-sorgente-documento-e-riga, giro T.5, 20261106-96/-97): le colonne parallele
--   della provenienza (ordini.documento_origine_*, contratti.offerta_id) sono ritirate; la fixture
--   scrive e il test legge la sola provenienza (sorgente_*), come i verbi. Attese invariate.
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   l'ordine collegato all'offerta porta documento_origine_tipo = OFFERTA_COMMERCIALE, il
--   codice della sorgente (era OFFERTA: ora la FK verso config.sorgenti lo rifiuta).
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): le offerte dei test 8 e 9
--   nascono in bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima
--   nascevano gia' RIFIUTATA e ACCETTATA).
-- rev 2026-10-26 (brief-modello-documento-vendita §13, giro 9): lo stato dell'offerta si
--   cambia solo dal verbo; le offerte ACCETTATA (test 2) ed EMESSA (test 7) si portano
--   avanti con dbops.fn_pgtap_porta_a_stato invece dell'UPDATE di stato.
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
-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): le righe di
--   offerta stanno nel PERIMETRO dell'articolo, e la tipologia dell'articolo dev'essere fra
--   quelle della utility del cliente. Gli articoli si COSTRUISCONO (dbops.fn_pgtap_crea_articolo:
--   MERCE senza tipologia, ammette UNA_TANTUM): prima erano i primi per id del database,
--   che su dbdev sono PRODOTTI, e la utility del cliente preso dai dati (TEL) non li prevede.
CREATE TEMP TABLE tmp_push_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-PUSHO-1') AS a1;

-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza
--   tipi_utenze (evita il guard tipo/classe sui satelliti utilities), legato
--   dal z90 all'emittente di chi agisce (contesto gia' aperto); listino, con la
--   sua versione ATTIVA da oggi, sulla stessa utility.
CREATE TEMP TABLE tmp_push_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'push offerta a contratto',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_push_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_push_cli), 'push offerta a contratto');

-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b, A-5):
--   l'OVERRIDE modifica una riga del listino, quindi l'articolo ci sta.
SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
    (SELECT listino_versione_id FROM tmp_push_listino), ARRAY[(SELECT a1 FROM tmp_push_art)]);

CREATE TEMP TABLE tmp_push_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_push_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_push_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_push_cli) AS utility_id,
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_push_listino) AS listino_id,
    (SELECT listino_versione_id FROM tmp_push_listino) AS listino_versione_id_attiva,
    (SELECT a1 FROM tmp_push_art) AS articolo_id,
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
    prezzo_unitario, attivo, qta_operativa
)
-- ⛔ rev 2026-10-13 (Lotto 3b): l'articolo prende la tipologia del listino, che
--   dipende dalla utility: erogazione e fonte le eredita il DB (NULL), la
--   quantita' c'e' solo se la fonte ereditata e' FISSA.
SELECT acc.id, ctx.articolo_id, 'OVERRIDE'::"vendite"."tipo_eccezione_contratto",
       NULL, NULL, 200.00, TRUE,
       (SELECT 1.00 FROM vendite.fn_articolo_erogazioni(ctx.articolo_id) e
         WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1)
  FROM tmp_push_offerta_acc acc, tmp_push_ctx ctx
 WHERE ctx.articolo_id IS NOT NULL;

-- ⚠️ rev 2026-10-11 (brief-db-testata-dopo-emissione §11, R-DB-3): anche la
--   fornitura si scrive solo in BOZZA (trg_offerte_commerciali_utilities_a05_
--   doc_bozza_ins_upd_dlt). Nasce quindi prima delle transizioni, come l'eccezione.
-- Utility dell'offerta (per verifica copia 1:1)
INSERT INTO vendite.offerte_commerciali_utilities (
    offerta_id, istanza_utility_id, utility_id
)
SELECT acc.id, ctx.istanza_utility_id, ctx.utility_id
  FROM tmp_push_offerta_acc acc, tmp_push_ctx ctx;

-- BOZZA -> EMESSA -> ACCETTATA, dal verbo (rev 2026-10-26, giro 9)
SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', a.id, 'ACCETTATA')
  FROM tmp_push_offerta_acc a;

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

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', e.id, 'EMESSA')
  FROM tmp_push_offerta_emessa e;

-- Offerta in RIFIUTATA (per test 8): nasce in BOZZA e arriva a RIFIUTATA per
-- la matrice (BOZZA -> EMESSA -> RIFIUTATA), rev 2026-10-24.
CREATE TEMP TABLE tmp_push_offerta_rif AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2101-01-01', ctx.stato_bozza_id
      FROM tmp_push_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', r.id, 'RIFIUTATA')
  FROM tmp_push_offerta_rif r;

-- Offerta in ACCETTATA con ORDINE gia' generato (per test 9): nasce in BOZZA,
-- arriva ad ACCETTATA per la matrice (rev 2026-10-24) + ordine collegato via
-- documento_origine ('OFFERTA_COMMERCIALE', id).
CREATE TEMP TABLE tmp_push_offerta_ord AS
WITH ins AS (
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id
    )
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
           ctx.listino_id, ctx.listino_versione_id_attiva,
           DATE '2102-01-01', ctx.stato_bozza_id
      FROM tmp_push_ctx ctx
    RETURNING id
)
SELECT id FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', o.id, 'ACCETTATA')
  FROM tmp_push_offerta_ord o;

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

-- Ordine collegato all'offerta (la provenienza: OFFERTA_COMMERCIALE + uid).
-- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-1/D-6): l'ordine ha sempre il
--   BA, ed e' quello dell'offerta da cui nasce, col suo ruolo. Prima nasceva col
--   BA NULL (per saltare il guard emittente<->BA) e col primo ruolo del database.
INSERT INTO vendite.ordini (
    soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
    stato_doc_ordine_id, valuta_id, data, storicizza,
    -- la provenienza, come la scrive il verbo (giro T.5 di brief-db-sorgente-documento-e-riga)
    sorgente_tipo_id, sorgente_uid
)
SELECT
    (SELECT c.soggetto_ruolo_id FROM tmp_push_cli c),
    ctx.billing_account_id,
    ctx.emittente_fiscale_id,
    (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT' AND attivo IS TRUE LIMIT 1),
    (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1),
    DATE '2102-01-02', false,
    (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'OFFERTA_COMMERCIALE'),
    (SELECT o.uid FROM vendite.offerte_commerciali o WHERE o.id = (SELECT id FROM tmp_push_offerta_ord))
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
-- 3) la provenienza del contratto: OFFERTA_COMMERCIALE + sorgente_uid = offerta.uid
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.contratti c
          JOIN tmp_push_contratto_id tc ON c.id = tc.contratto_id
          JOIN tmp_push_offerta_acc oa ON TRUE
          JOIN tmp_push_ctx ctx ON TRUE
         WHERE c.sorgente_uid = oa.uid
           AND c.sorgente_id IS NULL
           AND c.sorgente_tipo_id = ctx.sorgente_ofc_id
    ),
    '3) la provenienza del contratto: sorgente_tipo_id e sorgente_uid dell''offerta'
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
--    l'offerta ha gia' un ordine ('OFFERTA_COMMERCIALE', id) -> il push a contratto fallisce.
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
