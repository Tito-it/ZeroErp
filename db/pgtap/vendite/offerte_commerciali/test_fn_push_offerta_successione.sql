-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-26 (brief-modello-documento-vendita §11): A esce dalla bozza (1-bis) con dbops.fn_pgtap_porta_a_stato, non piu' con l'UPDATE diretto dello stato che la porta del contratto ora rifiuta.
--
-- Test: vendite.fn_push_offerta_a_contratto(p_offerta_id, p_pratica_id,
--       p_chiudi_contratto_esistente) — percorso SUCCESSIONE su overlap.
--       Il push e' consumatore del meccanismo generico (brief §3.4):
--       advisory lock + fn_contratto_sovrapposto + routing + backstop.
--
-- Riferimento: brief-db-offerta-push-successione-contratto-overlap.md §4
--
-- Indice test (1..6):
--   1)    push offerta A (ACCETTATA) -> contratto DRAFT creato (baseline incumbent)
--   1-bis) promosso ad ATTIVO, A partecipa all'overlap (vedi testata)
--   2)  push offerta B sovrapposta, chiudi=false -> throws E_CONTRATTO_OVERLAP_ESISTENTE
--   3)  dopo il fallimento (2) nessun contratto creato per l'offerta B
--   4)  push offerta B sovrapposta, chiudi=true -> contratto creato
--   5)  successione: il vecchio contratto A e' accorciato a (B.validita_dal - 1)
--   6)  push offerta C non sovrapposta, chiamata a 2 argomenti (default false) -> creato
--
-- Fixture: tre offerte ACCETTATE sullo stesso BA/istanza/utility.
--   A [2098-01-01..2098-12-31], B [2098-06-01..2098-12-31] (overlap su A),
--   C [2099-01-01..2099-12-31] (libera dopo la successione).
--
-- ⭐ CORRETTO IL 2026-08-24 — il contratto A si porta ad ATTIVO prima di
--   spingere B, e senza quel passo il test era ROSSO. La ragione non e' una
--   svista di fixture: e' una REGOLA DI DOMINIO che il test non aveva
--   recepito. Dal 2026-06-02 (changeSet 20260602-18, brief «Overlap contratti:
--   escludere i DRAFT dal vincolo») la partecipazione all'overlap e' decisa da
--   `vendite.contratti.partecipa_overlap_snapshot`, colonna **GENERATED**:
--
--       partecipa_overlap_snapshot = NOT is_abortito AND NOT is_draft
--
--   Un contratto in BOZZA quindi **non blocca** nessuno, di proposito. Il test
--   pretendeva l'opposto: il test 1 asserisce che A nasce in DRAFT e il test 2
--   pretendeva che quello stesso DRAFT facesse scattare l'overlap — due cose
--   che dal 02/06 non possono essere vere insieme.
--
--   ⚠️ E ne discende un fatto che vale oltre questo file: `fn_push_offerta_a_contratto`
--   crea SEMPRE il contratto in DRAFT, quindi il suo guard di overlap — e con
--   lui tutto il ramo `p_chiudi_contratto_esistente` — puo' scattare solo
--   contro un incumbent gia' promosso. Che e' realistico, ed e' ora quello che
--   questo test misura.
--
--   ⛔ Il test era invisibile: il file vive in una sottocartella, e fino al
--   2026-08-24 i presidi pgTAP guardavano un livello solo. Vedi
--   brief-db-pgtap-rami-ciechi.md
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;
SELECT plan(7);

-- ============================================================
-- Setup fixture (contesto come test_fn_push_offerta_a_contratto)
-- ============================================================
-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza
--   tipi_utenze (evita il guard tipo/classe sui satelliti utilities), legato
--   dal z90 all'emittente di chi agisce (contesto gia' aperto); listino, con la
--   sua versione ATTIVA da oggi, sulla stessa utility.
CREATE TEMP TABLE tmp_pushsucc_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'push offerta successione',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_pushsucc_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_pushsucc_cli), 'push offerta successione');

CREATE TEMP TABLE tmp_pushsucc_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_pushsucc_cli) AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_pushsucc_cli) AS istanza_utility_id,
    (SELECT utility_id FROM tmp_pushsucc_cli) AS utility_id,
    script.fn_pgtap_emittente_operatore() AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_pushsucc_listino) AS listino_id,
    (SELECT listino_versione_id FROM tmp_pushsucc_listino) AS listino_versione_id_attiva,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')     AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')    AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'ACCETTATA') AS stato_accettata_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT')   AS stato_draft_contratto_id;

-- Tre offerte in BOZZA (marker in meta->>'pgtap_succ')
INSERT INTO vendite.offerte_commerciali (
    emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
    listino_id, listino_versione_id, validita_dal, validita_al,
    stato_doc_offerta_id, meta
)
SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id, ctx.utility_id,
       ctx.listino_id, ctx.listino_versione_id_attiva, v.dal, v.al,
       ctx.stato_bozza_id, jsonb_build_object('pgtap_succ', v.tag)
  FROM tmp_pushsucc_ctx ctx,
       (VALUES
            ('A', '2098-01-01'::date, '2098-12-31'::date),
            ('B', '2098-06-01'::date, '2098-12-31'::date),
            ('C', '2099-01-01'::date, '2099-12-31'::date)
       ) AS v(tag, dal, al);

-- Transizioni BOZZA -> EMESSA -> ACCETTATA (guard transizione richiede i passi)
UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_emessa_id FROM tmp_pushsucc_ctx)
 WHERE meta->>'pgtap_succ' IN ('A','B','C');

UPDATE vendite.offerte_commerciali
   SET stato_doc_offerta_id = (SELECT stato_accettata_id FROM tmp_pushsucc_ctx)
 WHERE meta->>'pgtap_succ' IN ('A','B','C');

-- Push offerta A (baseline): crea il contratto incumbent
CREATE TEMP TABLE tmp_pushsucc_a AS
SELECT vendite.fn_push_offerta_a_contratto(
    (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'A'),
    NULL::bigint,
    false
) AS contratto_id;

-- ============================================================
-- 1) Contratto A creato in stato DRAFT
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.contratti c
          JOIN tmp_pushsucc_a ta ON c.id = ta.contratto_id
         WHERE c.stato_doc_contratto_id = (SELECT stato_draft_contratto_id FROM tmp_pushsucc_ctx)
    ),
    '1) push offerta A -> contratto DRAFT creato (incumbent)'
);

-- ============================================================
-- ⭐ A ESCE DALLA BOZZA: senza, non partecipa all'overlap (vedi testata).
--   DRAFT -> ATTIVO e' una transizione ammessa da
--   config.transizioni_stati_contratti, quindi passa dal guard di transizione
--   invece di aggirarlo. Dal giro 8 (porta sul contratto) dalla fixture, che
--   passa dal verbo vendite.fn_cambia_stato_contratto.
-- ============================================================
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, contratto_id, 'ATTIVO')
  FROM tmp_pushsucc_a;

-- ⚠️ Si verifica che la promozione abbia davvero acceso la partecipazione:
--   se un domani la colonna generata cambiasse formula, i test 2-5
--   tornerebbero a misurare il caso sbagliato in silenzio.
SELECT is(
    (SELECT c.partecipa_overlap_snapshot
       FROM vendite.contratti c JOIN tmp_pushsucc_a ta ON c.id = ta.contratto_id),
    true,
    '1-bis) promosso ad ATTIVO, il contratto A partecipa all''overlap'
);

-- ============================================================
-- 2) Push offerta B sovrapposta, chiudi=false -> throws E_CONTRATTO_OVERLAP_ESISTENTE
-- ============================================================
SELECT throws_ok(
    format(
        $q$SELECT vendite.fn_push_offerta_a_contratto(%s, NULL::bigint, false)$q$,
        (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'B')
    ),
    'P0001', NULL,
    '2) push offerta sovrapposta con chiudi=false -> throws E_CONTRATTO_OVERLAP_ESISTENTE'
);

-- ============================================================
-- 3) Dopo il fallimento nessun contratto creato per l'offerta B
-- ============================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM vendite.contratti
         WHERE offerta_id = (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'B')
    ),
    '3) overlap con chiudi=false -> nessun contratto creato per l''offerta B'
);

-- ============================================================
-- 4) Push offerta B con chiudi=true -> contratto creato
-- ============================================================
SELECT ok(
    vendite.fn_push_offerta_a_contratto(
        (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'B'),
        NULL::bigint,
        true
    ) IS NOT NULL,
    '4) push offerta sovrapposta con chiudi=true -> contratto creato (successione)'
);

-- ============================================================
-- 5) Il vecchio contratto A e' accorciato a (B.validita_dal - 1) = 2098-05-31
-- ============================================================
SELECT is(
    (SELECT valido_al FROM vendite.contratti
      WHERE offerta_id = (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'A')),
    '2098-05-31'::date,
    '5) successione -> vecchio contratto A accorciato a validita_dal del nuovo - 1'
);

-- ============================================================
-- 6) Push offerta C non sovrapposta (chiamata a 2 argomenti, default false) -> creato
-- ============================================================
SELECT ok(
    vendite.fn_push_offerta_a_contratto(
        (SELECT id FROM vendite.offerte_commerciali WHERE meta->>'pgtap_succ' = 'C'),
        NULL::bigint
    ) IS NOT NULL,
    '6) push offerta senza overlap (chiamata a 2 argomenti, default chiudi=false) -> contratto creato'
);

SELECT * FROM finish();
ROLLBACK;
