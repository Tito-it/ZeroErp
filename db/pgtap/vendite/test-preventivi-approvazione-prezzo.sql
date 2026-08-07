-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trigger guard Sprint E listini v5 §14.6
-- Riferimenti: migrations 20260422-06 (preventivi_guard_transizione_
-- approvazione) e 20260422-07 (preventivi_righe_guard_pending).
--
-- Contesto:
--   Workflow L3 approvazione prezzo out-of-policy. Righe preventivo in
--   stato_approvazione_prezzo='PENDING' sono frozen nei campi struttura
--   finche' non transiscono ad APPROVED/REJECTED/NULL. Il preventivo
--   non puo' essere ACCETTATO se ha ancora righe PENDING pendenti.
--
-- Indice test (1..10):
--    1. Transizione preventivo ad ACCETTATO con riga PENDING -> raise
--       E_PREVENTIVO_RIGHE_PRICING_PENDENTI
--    2. Transizione preventivo ad ACCETTATO con riga APPROVED -> OK
--    3. Transizione preventivo ad ACCETTATO con riga REJECTED -> OK
--    4. UPDATE prezzo_unitario su riga PENDING -> raise E_RIGA_PREZZO_PENDENTE
--    5. UPDATE quantita su riga PENDING -> raise E_RIGA_PREZZO_PENDENTE
--    6. UPDATE simultaneo stato_approvazione=APPROVED + prezzo_unitario
--       su riga PENDING -> raise (il cambio prezzo non e' allowlisted)
--    7. UPDATE meta (campo audit/payload) su riga PENDING -> OK
--    8. UPDATE stato_approvazione PENDING -> APPROVED (solo workflow) -> OK
--    9. UPDATE prezzo_unitario su riga NON in approvazione (stato NULL)
--       -> OK (trigger no-op per OLD != PENDING)
--   10. UPDATE stato_doc a DRAFT (non ACCETTATO) con riga PENDING
--       -> OK (fn_transizione early return, guard limitato a ACCETTATO)
--
-- Setup: 4 preventivi + righe con stati diversi pre-impostati.
-- Articolo fixture: ART_TEST_BASE (seed esistente). Utility: primo
-- utility attivo. BA: NULL (colonna nullable).
--
-- Ordine test: i test che modificano persistente la riga PENDING sono
-- in coda (test 8 cambia stato -> APPROVED). throws_ok rollbacka il
-- savepoint interno su raise, lives_ok fa persistere le modifiche.
--
-- BEGIN + ROLLBACK isolamento completo.
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

SELECT plan(10);

-- =========================================================
-- Setup fixture comuni
-- =========================================================
CREATE TEMP TABLE _t_ctx AS
SELECT
    (SELECT id     FROM catalogo.articoli WHERE codice = 'ART_TEST_BASE') AS articolo_id,
    (SELECT uom_id FROM catalogo.articoli WHERE codice = 'ART_TEST_BASE') AS uom_id,
    (SELECT id FROM config.utilities ORDER BY id LIMIT 1) AS utility_id,
    -- Emittente fiscale: il trigger BEFORE INSERT lo pretende quando la GUC
    -- app.current_user_id e' vuota, cioe' sempre in contesto pgTAP. La sua
    -- assenza teneva questo file a ERRORE_FIXTURE in baseline-rossi: falliva
    -- alla prima INSERT e non eseguiva NESSUNA asserzione (2026-08-05).
    (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1) AS emittente_fiscale_id,
    (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'DRAFT' LIMIT 1) AS stato_draft_id,
    -- EMESSO serve come tappa intermedia: la matrice non ammette
    -- DRAFT -> ACCETTATO, e dal 2026-08-05 il database la impone.
    (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'EMESSO' LIMIT 1) AS stato_emesso_id,
    (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'ACCETTATO' LIMIT 1) AS stato_accettato_id;

DO $pgtap$
BEGIN
    IF (SELECT articolo_id IS NULL OR utility_id IS NULL OR stato_draft_id IS NULL
               OR stato_emesso_id IS NULL OR stato_accettato_id IS NULL
               OR emittente_fiscale_id IS NULL FROM _t_ctx) THEN
        RAISE EXCEPTION 'Seed fixture mancante (ART_TEST_BASE / utility / stati_doc_preventivi); impossibile eseguire test.';
    END IF;
END
$pgtap$;

-- 4 preventivi distinti per isolamento: uno per scenario che richiede
-- EXISTS check diverso sul trigger di transizione.
CREATE TEMP TABLE _t_prev (tag text, preventivo_id bigint, riga_id bigint);

-- p_pending: riga stato=PENDING
WITH ins_p AS (
    INSERT INTO vendite.preventivi (
        numero, stato_doc_preventivo_id, utility_id, data, emittente_fiscale_id
    )
    SELECT 'pgtap_appr_pnd_' || substring(md5(clock_timestamp()::text) from 1 for 6),
           stato_draft_id, utility_id, CURRENT_DATE, emittente_fiscale_id
      FROM _t_ctx
    RETURNING id
),
ins_r AS (
    INSERT INTO vendite.preventivi_righe (
        preventivo_id, articolo_id, quantita, qta_operativa, uom_operativa_id,
        prezzo_unitario, stato_approvazione_prezzo
    )
    SELECT p.id, c.articolo_id, 1, 1, c.uom_id,
           100, 'PENDING'::config.stato_approvazione_prezzo
      FROM ins_p p, _t_ctx c
    RETURNING preventivo_id, id AS riga_id
)
INSERT INTO _t_prev (tag, preventivo_id, riga_id)
SELECT 'p_pending', preventivo_id, riga_id FROM ins_r;

-- p_approved: riga stato=APPROVED
WITH ins_p AS (
    INSERT INTO vendite.preventivi (numero, stato_doc_preventivo_id, utility_id, data, emittente_fiscale_id)
    SELECT 'pgtap_appr_app_' || substring(md5(clock_timestamp()::text) from 1 for 6),
           stato_draft_id, utility_id, CURRENT_DATE, emittente_fiscale_id FROM _t_ctx
    RETURNING id
),
ins_r AS (
    INSERT INTO vendite.preventivi_righe (
        preventivo_id, articolo_id, quantita, qta_operativa, uom_operativa_id,
        prezzo_unitario, stato_approvazione_prezzo
    )
    SELECT p.id, c.articolo_id, 1, 1, c.uom_id,
           100, 'APPROVED'::config.stato_approvazione_prezzo
      FROM ins_p p, _t_ctx c
    RETURNING preventivo_id, id AS riga_id
)
INSERT INTO _t_prev (tag, preventivo_id, riga_id)
SELECT 'p_approved', preventivo_id, riga_id FROM ins_r;

-- p_rejected: riga stato=REJECTED
WITH ins_p AS (
    INSERT INTO vendite.preventivi (numero, stato_doc_preventivo_id, utility_id, data, emittente_fiscale_id)
    SELECT 'pgtap_appr_rej_' || substring(md5(clock_timestamp()::text) from 1 for 6),
           stato_draft_id, utility_id, CURRENT_DATE, emittente_fiscale_id FROM _t_ctx
    RETURNING id
),
ins_r AS (
    INSERT INTO vendite.preventivi_righe (
        preventivo_id, articolo_id, quantita, qta_operativa, uom_operativa_id,
        prezzo_unitario, stato_approvazione_prezzo
    )
    SELECT p.id, c.articolo_id, 1, 1, c.uom_id,
           100, 'REJECTED'::config.stato_approvazione_prezzo
      FROM ins_p p, _t_ctx c
    RETURNING preventivo_id, id AS riga_id
)
INSERT INTO _t_prev (tag, preventivo_id, riga_id)
SELECT 'p_rejected', preventivo_id, riga_id FROM ins_r;

-- p_null: riga stato=NULL (non in approvazione, baseline libero)
WITH ins_p AS (
    INSERT INTO vendite.preventivi (numero, stato_doc_preventivo_id, utility_id, data, emittente_fiscale_id)
    SELECT 'pgtap_appr_nul_' || substring(md5(clock_timestamp()::text) from 1 for 6),
           stato_draft_id, utility_id, CURRENT_DATE, emittente_fiscale_id FROM _t_ctx
    RETURNING id
),
ins_r AS (
    INSERT INTO vendite.preventivi_righe (
        preventivo_id, articolo_id, quantita, qta_operativa, uom_operativa_id,
        prezzo_unitario
    )
    SELECT p.id, c.articolo_id, 1, 1, c.uom_id,
           100
      FROM ins_p p, _t_ctx c
    RETURNING preventivo_id, id AS riga_id
)
INSERT INTO _t_prev (tag, preventivo_id, riga_id)
SELECT 'p_null', preventivo_id, riga_id FROM ins_r;

-- =========================================================
-- I preventivi nascono in DRAFT, ma i test qui sotto verificano il guard
-- dell'APPROVAZIONE PREZZO, che scatta entrando in ACCETTATO. Serve quindi
-- portarli prima in EMESSO.
--
-- ⚠️ Perche' questo passo esiste (2026-08-05). Prima si saltava dritti da DRAFT
-- ad ACCETTATO: comodo, e fuori matrice — `DRAFT -> ACCETTATO` non e' in
-- config.transizioni_stati_preventivi. Funzionava solo perche' il preventivo
-- era l'unico documento la cui matrice non era imposta dal database. Da quando
-- c'e' vendite.trgfn_preventivi_guard_transizione (20260805-15) la scorciatoia
-- viene rifiutata, giustamente. Il significato dei test non cambia: cambia solo
-- che ci si arriva dalla porta invece che dalla finestra.
-- =========================================================
UPDATE vendite.preventivi
   SET stato_doc_preventivo_id = (SELECT stato_emesso_id FROM _t_ctx)
 WHERE id IN (SELECT preventivo_id FROM _t_prev);

-- =========================================================
-- 1) Transizione ad ACCETTATO con riga PENDING -> raise
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ UPDATE vendite.preventivi SET stato_doc_preventivo_id = %L::bigint WHERE id = %L::bigint $sql$,
        (SELECT stato_accettato_id FROM _t_ctx),
        (SELECT preventivo_id FROM _t_prev WHERE tag = 'p_pending')
    ),
    NULL, NULL,
    '1. Transizione preventivo ad ACCETTATO con riga PENDING -> raise E_PREVENTIVO_RIGHE_PRICING_PENDENTI'
);

-- =========================================================
-- 2) Transizione ad ACCETTATO con riga APPROVED -> OK
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE vendite.preventivi SET stato_doc_preventivo_id = %L::bigint WHERE id = %L::bigint $sql$,
        (SELECT stato_accettato_id FROM _t_ctx),
        (SELECT preventivo_id FROM _t_prev WHERE tag = 'p_approved')
    ),
    '2. Transizione ad ACCETTATO con riga APPROVED -> OK'
);

-- =========================================================
-- 3) Transizione ad ACCETTATO con riga REJECTED -> OK
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE vendite.preventivi SET stato_doc_preventivo_id = %L::bigint WHERE id = %L::bigint $sql$,
        (SELECT stato_accettato_id FROM _t_ctx),
        (SELECT preventivo_id FROM _t_prev WHERE tag = 'p_rejected')
    ),
    '3. Transizione ad ACCETTATO con riga REJECTED -> OK'
);

-- =========================================================
-- 4) UPDATE prezzo_unitario su riga PENDING -> raise
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ UPDATE vendite.preventivi_righe SET prezzo_unitario = 999 WHERE id = %L::bigint $sql$,
        (SELECT riga_id FROM _t_prev WHERE tag = 'p_pending')
    ),
    NULL, NULL,
    '4. UPDATE prezzo_unitario su riga PENDING -> raise E_RIGA_PREZZO_PENDENTE'
);

-- =========================================================
-- 5) UPDATE quantita su riga PENDING -> raise
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ UPDATE vendite.preventivi_righe SET quantita = 5 WHERE id = %L::bigint $sql$,
        (SELECT riga_id FROM _t_prev WHERE tag = 'p_pending')
    ),
    NULL, NULL,
    '5. UPDATE quantita su riga PENDING -> raise E_RIGA_PREZZO_PENDENTE'
);

-- =========================================================
-- 6) UPDATE simultaneo stato_approvazione + prezzo -> raise
-- Transizione workflow sola sarebbe OK (test 8); combinata con
-- modifica struttura il trigger deve rilevare e bloccare.
-- =========================================================
SELECT throws_ok(
    format(
        $sql$ UPDATE vendite.preventivi_righe
                 SET stato_approvazione_prezzo = 'APPROVED'::config.stato_approvazione_prezzo,
                     prezzo_unitario = 777
               WHERE id = %L::bigint $sql$,
        (SELECT riga_id FROM _t_prev WHERE tag = 'p_pending')
    ),
    NULL, NULL,
    '6. UPDATE stato+prezzo simultaneo su PENDING -> raise (prezzo non allowlisted)'
);

-- =========================================================
-- 7) UPDATE meta (payload allowlisted) su riga PENDING -> OK
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE vendite.preventivi_righe
                 SET meta = jsonb_build_object('pgtap', 'test_7')
               WHERE id = %L::bigint $sql$,
        (SELECT riga_id FROM _t_prev WHERE tag = 'p_pending')
    ),
    '7. UPDATE meta su riga PENDING -> OK (campo allowlisted)'
);

-- =========================================================
-- 8) UPDATE stato_approvazione PENDING -> APPROVED -> OK
-- Ultima fra i test su riga p_pending perche' la transizione
-- e' persistente (lives_ok non rollbacka).
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE vendite.preventivi_righe
                 SET stato_approvazione_prezzo = 'APPROVED'::config.stato_approvazione_prezzo
               WHERE id = %L::bigint $sql$,
        (SELECT riga_id FROM _t_prev WHERE tag = 'p_pending')
    ),
    '8. UPDATE stato_approvazione PENDING -> APPROVED -> OK (workflow allowlisted)'
);

-- =========================================================
-- 9) UPDATE prezzo su riga NON in approvazione (stato NULL) -> OK
-- Trigger no-op perche' OLD.stato_approvazione_prezzo IS DISTINCT FROM 'PENDING'
-- (NULL vs 'PENDING' -> distinct -> early return).
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ UPDATE vendite.preventivi_righe SET prezzo_unitario = 200 WHERE id = %L::bigint $sql$,
        (SELECT riga_id FROM _t_prev WHERE tag = 'p_null')
    ),
    '9. UPDATE prezzo su riga stato=NULL -> OK (trigger no-op)'
);

-- =========================================================
-- 10) Transizione stato_doc ad uno stato != ACCETTATO con righe
-- PENDING presenti -> OK. Early return nella fn transizione:
-- il guard si applica SOLO alla transizione ACCETTATO, non alle
-- altre (es. passaggio a EMESSO, RIFIUTATO, ANNULLATO).
-- Uso un preventivo fresh per evitare interferenze con test 1.
-- =========================================================
CREATE TEMP TABLE _t_prev_draft2 AS
WITH ins_p AS (
    INSERT INTO vendite.preventivi (numero, stato_doc_preventivo_id, utility_id, data, emittente_fiscale_id)
    SELECT 'pgtap_appr_drt_' || substring(md5(clock_timestamp()::text) from 1 for 6),
           stato_draft_id, utility_id, CURRENT_DATE, emittente_fiscale_id FROM _t_ctx
    RETURNING id
),
ins_r AS (
    INSERT INTO vendite.preventivi_righe (
        preventivo_id, articolo_id, quantita, qta_operativa, uom_operativa_id,
        prezzo_unitario, stato_approvazione_prezzo
    )
    SELECT p.id, c.articolo_id, 1, 1, c.uom_id,
           100, 'PENDING'::config.stato_approvazione_prezzo
      FROM ins_p p, _t_ctx c
    RETURNING preventivo_id
)
SELECT preventivo_id FROM ins_r;

-- Recupero un stato != ACCETTATO (EMESSO id=2 dal seed).
SELECT lives_ok(
    format(
        $sql$ UPDATE vendite.preventivi SET stato_doc_preventivo_id = (
                  SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'EMESSO' LIMIT 1
              ) WHERE id = %L::bigint $sql$,
        (SELECT preventivo_id FROM _t_prev_draft2)
    ),
    '10. Transizione ad EMESSO con riga PENDING -> OK (guard solo su ACCETTATO)'
);

SELECT * FROM finish();
ROLLBACK;
