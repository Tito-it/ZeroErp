-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: workflow approvazione prezzo sul preventivo (Sprint E listini v5
-- §14.6): il guard PER RIGA e, dal 2026-09-24, la regola del documento.
-- Riferimenti: 20260422-07 (preventivi_righe_guard_pending) e 20260924-20…-24
-- (script.fn_check_prezzi_autorizzati, Regole 2 e 3 di
-- trgfn_preventivi_guard_transizione).
--
-- Contesto:
--   Workflow L3 approvazione prezzo out-of-policy. Righe preventivo in
--   stato_approvazione_prezzo='PENDING' sono frozen nei campi struttura
--   finche' non transiscono ad APPROVED/REJECTED/NULL.
--   ⚠️ rev 2026-09-24 (brief-db-preventivi-congelamento-pricing): la regola
--   del DOCUMENTO e' cambiata, e i test 1, 3 e 10 con lei. Prima il trigger
--   a10 (ritirato) bloccava il solo PENDING e solo verso ACCETTATO; ora un
--   prezzo non autorizzato — PENDING o REJECTED (D-1) — non esce dalla
--   bozza (D-2), e l'annullamento resta sempre possibile. Il perimetro
--   intero della regola sta in script/test-fn-check-prezzi-autorizzati-v1:
--   qui resta il suo filo col workflow della riga.
--   ⚠️ E dalla stessa revisione il mondo si COSTRUISCE (mondo cliente +
--   articolo): prima pescava un billing account e ART_TEST_BASE dai dati,
--   e in CI moriva nel fixture (ERRORE_FIXTURE in baseline-rossi-ci).
--
-- Indice test (1..10):
--    1. DRAFT -> EMESSO con riga PENDING -> BLOCCA (prezzo in attesa)
--    2. DRAFT -> EMESSO -> ACCETTATO con riga APPROVED -> OK
--    3. DRAFT -> EMESSO con riga REJECTED -> BLOCCA (D-1: prima passava)
--    4. UPDATE prezzo_unitario su riga PENDING -> raise E_RIGA_PREZZO_PENDENTE
--    5. UPDATE quantita su riga PENDING -> raise E_RIGA_PREZZO_PENDENTE
--    6. UPDATE simultaneo stato_approvazione=APPROVED + prezzo_unitario
--       su riga PENDING -> raise (il cambio prezzo non e' allowlisted)
--    7. UPDATE meta (campo audit/payload) su riga PENDING -> OK
--    8. UPDATE stato_approvazione PENDING -> APPROVED (solo workflow) -> OK
--    9. UPDATE prezzo_unitario su riga NON in approvazione (stato NULL)
--       -> OK (trigger no-op per OLD != PENDING)
--   10. DRAFT -> ANNULLATO con riga PENDING -> OK (via d'uscita, D-2)
--
-- ⚠️ rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): lo stato del
--   preventivo si cambia solo dal verbo vendite.fn_cambia_stato_preventivo; un
--   UPDATE diretto lo ferma la porta (E_DOC_STATO_SOLO_DAL_VERBO) prima del
--   guard di transizione. I passaggi dei test 1, 2, 3 e 10 si chiedono al verbo,
--   che arriva al guard e prende il suo motivo; l'operatore riceve
--   emetti_preventivo, il permesso dell'emissione. Attese invariate.
--
-- Setup: 4 preventivi + righe con stati diversi pre-impostati, sul mondo
-- costruito (dbops.fn_pgtap_crea_mondo_cliente) e un articolo costruito
-- (dbops.fn_pgtap_crea_articolo).
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
-- Il mondo si costruisce (rev 2026-09-24): azienda di chi agisce + cliente
-- fatturabile legato a lei. Istanza e utility vengono dallo STESSO billing
-- account, cosi' descrivono lo stesso rapporto.
CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP approvazione prezzo');

CREATE TEMP TABLE _t_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-APPR-ART', false) AS articolo_id;

CREATE TEMP TABLE _t_ctx AS
SELECT
    (SELECT articolo_id FROM _t_art) AS articolo_id,
    (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = (SELECT articolo_id FROM _t_art)) AS uom_id,
    (SELECT m.utility_id FROM _t_mondo m) AS utility_id,
    (SELECT m.istanza_utility_id FROM _t_mondo m) AS istanza_utility_id,
    (SELECT m.billing_account_id FROM _t_mondo m) AS billing_account_id,
    -- ⚠️ E l'IVA: `iva_id` e' obbligatorio sulle righe di preventivo, e
    --   dall'emissione in poi una riga con prezzo senza aliquota e' rifiutata.
    (SELECT i.id FROM config.iva i
      WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
      ORDER BY i.id LIMIT 1) AS iva_id,
    (SELECT m.emittente_fiscale_id FROM _t_mondo m) AS emittente_fiscale_id,
    (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'DRAFT' LIMIT 1) AS stato_draft_id,
    (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'EMESSO' LIMIT 1) AS stato_emesso_id,
    (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'ACCETTATO' LIMIT 1) AS stato_accettato_id;

DO $pgtap$
BEGIN
    IF (SELECT articolo_id IS NULL OR utility_id IS NULL OR stato_draft_id IS NULL
               OR stato_emesso_id IS NULL OR stato_accettato_id IS NULL
               OR emittente_fiscale_id IS NULL OR iva_id IS NULL FROM _t_ctx) THEN
        RAISE EXCEPTION 'Fixture incompleta (mondo, articolo, IVA o stati_doc_preventivi): impossibile eseguire test.';
    END IF;
END
$pgtap$;

-- 4 preventivi distinti per isolamento: uno per scenario che richiede
-- EXISTS check diverso sul trigger di transizione.
CREATE TEMP TABLE _t_prev (tag text, preventivo_id bigint, riga_id bigint);

-- ⛔ PADRE E FIGLIO IN DUE STATEMENT SEPARATI, e non e' uno stile.
--   Fino al 2026-09-09 questi quattro blocchi erano una CTE sola
--   (`WITH ins_p AS (INSERT INTO preventivi …), ins_r AS (INSERT INTO
--   preventivi_righe …)`). Da quando `vendite.preventivi_righe` ha la sua
--   policy (slice 20260909-27..30) quella forma NON PUO' funzionare: le CTE che
--   scrivono condividono la stessa snapshot, quindi il preventivo appena
--   inserito NON e' visibile al ramo che inserisce la riga. La policy della
--   riga risolve il perimetro passando dalla testata
--   (`fn_scope_ef_whitelist_via_preventivo`), non la trova, il perimetro
--   risolve a NULL e il `WITH CHECK` nega — fail-closed, che e' il
--   comportamento giusto.
--   ⚠️ Il sintomo mente: l'errore parla di violazione RLS sulla RIGA e sembra un
--   problema di whitelist o di permessi. Non lo e': e' visibilita' dentro lo
--   statement. ⛔ Non si corregge la policy — nel percorso applicativo reale la
--   testata nasce in uno step e le righe in quello dopo.
--   ⭐ In `LANGUAGE sql` non c'e' modo di concatenare due scritture se non con
--   una CTE: serve plpgsql con due INSERT e una variabile in mezzo.
DO $fixture$
DECLARE
    c            record;
    v_prev_id    vendite.preventivi.id%TYPE;
    v_riga_id    vendite.preventivi_righe.id%TYPE;
    v_caso       record;
BEGIN
    SELECT * INTO c FROM _t_ctx;

    FOR v_caso IN
        SELECT * FROM (VALUES
            ('p_pending',  'pnd', 'PENDING'),
            ('p_approved', 'app', 'APPROVED'),
            ('p_rejected', 'rej', 'REJECTED'),
            -- ⚠️ stato NULL: riga NON in approvazione, baseline libero (test 9).
            ('p_null',     'nul', NULL)
        ) AS v(tag, sigla, stato)
    LOOP
        -- 1) La testata.
        INSERT INTO vendite.preventivi (
            numero, stato_doc_preventivo_id, utility_id, istanza_utility_id,
            billing_account_id, data, emittente_fiscale_id
        )
        VALUES (
            'pgtap_appr_' || v_caso.sigla || '_'
                || substring(md5(clock_timestamp()::text) from 1 for 6),
            c.stato_draft_id, c.utility_id, c.istanza_utility_id,
            c.billing_account_id, script.fn_data_operativa(), c.emittente_fiscale_id
        )
        RETURNING id INTO v_prev_id;

        -- 2) La riga: statement SUO, cosi' la policy vede la testata.
        INSERT INTO vendite.preventivi_righe (
            preventivo_id, articolo_id, quantita, qta_operativa, uom_operativa_id,
            prezzo_unitario, iva_id, stato_approvazione_prezzo
        )
        VALUES (
            v_prev_id, c.articolo_id, 1, 1, c.uom_id,
            100, c.iva_id, v_caso.stato::config.stato_approvazione_prezzo
        )
        RETURNING id INTO v_riga_id;

        INSERT INTO _t_prev (tag, preventivo_id, riga_id)
        VALUES (v_caso.tag, v_prev_id, v_riga_id);
    END LOOP;
END
$fixture$;

-- =========================================================
-- 1-3) La regola del DOCUMENTO (rev 2026-09-24)
-- ⚠️ Fino a questa revisione qui i quattro preventivi passavano TUTTI in
--   EMESSO, e i test guardavano solo l'ingresso in ACCETTATO — il perimetro
--   del trigger a10, ora ritirato. Da D-2 un prezzo non autorizzato non esce
--   gia' dalla bozza: la porta che conta e' DRAFT -> EMESSO.
-- ⚠️ throws_like sulla FRASE e non throws_ok(..., NULL, NULL): quella forma
--   passava con QUALUNQUE errore, anche uno della fixture.
-- =========================================================
-- ⚠️ rev 2026-10-25 (giro 6): i passaggi si chiedono al VERBO
--   vendite.fn_cambia_stato_preventivo, che arriva al guard di transizione:
--   un UPDATE diretto lo ferma prima la porta (E_DOC_STATO_SOLO_DAL_VERBO).
--   L'operatore riceve emetti_preventivo: si prova il prezzo, non il permesso.
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_preventivo');
END $az$;

SELECT throws_like(
    format(
        $sql$ SELECT * FROM vendite.fn_cambia_stato_preventivo(%L::bigint, 'EMESSO') $sql$,
        (SELECT preventivo_id FROM _t_prev WHERE tag = 'p_pending')
    ),
    '%prezzi ancora in attesa di approvazione%',
    '1. DRAFT -> EMESSO con riga PENDING -> BLOCCA (prezzo in attesa)'
);

-- 2) Il controllo dell'1: coi prezzi approvati il preventivo esce dalla
--    bozza ed e' accettabile. Prima l'emissione, poi la verifica sull'ultimo
--    passo.
SELECT * FROM vendite.fn_cambia_stato_preventivo(
    (SELECT preventivo_id FROM _t_prev WHERE tag = 'p_approved'), 'EMESSO');

SELECT lives_ok(
    format(
        $sql$ SELECT * FROM vendite.fn_cambia_stato_preventivo(%L::bigint, 'ACCETTATO') $sql$,
        (SELECT preventivo_id FROM _t_prev WHERE tag = 'p_approved')
    ),
    '2. DRAFT -> EMESSO -> ACCETTATO con riga APPROVED -> OK'
);

-- 3) Il REJECTED ora BLOCCA (D-1). Fino al 2026-09-24 questo test diceva il
--    contrario — «ad ACCETTATO con riga REJECTED -> OK» — e fissava proprio il
--    buco: un prezzo rifiutato dal responsabile usciva col documento.
SELECT throws_like(
    format(
        $sql$ SELECT * FROM vendite.fn_cambia_stato_preventivo(%L::bigint, 'EMESSO') $sql$,
        (SELECT preventivo_id FROM _t_prev WHERE tag = 'p_rejected')
    ),
    '%prezzi rifiutati dal responsabile%',
    '3. DRAFT -> EMESSO con riga REJECTED -> BLOCCA (D-1: prima passava)'
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
-- 10) La via d'uscita: un preventivo con una riga PENDING si ANNULLA sempre.
-- ⚠️ rev 2026-09-24: fino a questa revisione il test diceva «ad EMESSO con
--   riga PENDING -> OK (guard solo su ACCETTATO)», cioe' fissava il perimetro
--   del trigger a10 ritirato. Da D-2 l'emissione e' bloccata (test 1): quello
--   che deve restare aperto e' l'annullamento.
-- =========================================================
SELECT lives_ok(
    format(
        $sql$ SELECT * FROM vendite.fn_cambia_stato_preventivo(%L::bigint, 'ANNULLATO') $sql$,
        (SELECT preventivo_id FROM _t_prev WHERE tag = 'p_rejected')
    ),
    '10. DRAFT -> ANNULLATO con riga REJECTED -> OK (via d''uscita, D-2)'
);

SELECT * FROM finish();
ROLLBACK;
