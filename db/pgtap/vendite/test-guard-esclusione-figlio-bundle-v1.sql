-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: §6.1 Guard ESCLUSIONE su figlio bundle vietata
--       Migration: 20260516-05
--
-- Indice test (1..5):
--   Struttura:
--   1)  La check per tipo di riga compone la regola: i suoi motivi
--       (script.fn_check_articolo_riga_su_contesto dal 2026-10-14, Lotto 4) chiamano
--       script.fn_check_esclusione_articolo_documento (rev 2026-10-13, Lotto 3b)
--   2)  Trigger trg_contratti_righe_a10_guard_articolo_ammesso_ins_upd presente, sul guard di
--       tabella script.trgfn_righe_guard_articolo_ammesso
--
--   ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b): il guard
--   dedicato (script.trgfn_righe_guard_esclusione_figlio_bundle) e' ritirato; il figlio
--   di bundle e' il primo motivo dell'ESCLUSIONE nella check per tipo di riga, che il
--   guard di tabella solleva. Codice e messaggio invariati: i test 3-5 non cambiano.
--
--   rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende): la funzione e'
--   generica per contratto e offerta (script); le esclusioni nascono VUOTE
--   (prima portavano qta_operativa 1, che la regola nuova rifiuta).
--
--   Comportamento (COND: skip se nessun bundle in listini_righe_componenti):
--   3)  ESCLUSIONE su figlio bundle nel listino del contratto → raise P0001
--   4)  ESCLUSIONE su padre bundle (articolo padre composito) → ammessa
--   5)  ESCLUSIONE su articolo standalone (non figlio bundle) → ammessa
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

-- Trova un bundle con componenti attivi in una versione operativa.
-- Se non esiste alcun bundle nel DB, i test 3-5 vengono skippati.
CREATE TEMP TABLE tmp_esc_bundle AS
SELECT
    lrc.articolo_figlio_id  AS figlio_id,
    lrc.articolo_padre_id   AS padre_id,
    lv.listino_id           AS listino_id,
    lv.id                   AS listino_versione_id
  FROM vendite.listini_righe_componenti lrc
  JOIN vendite.listini_versioni lv ON lv.id = lrc.listino_versione_id
 WHERE lrc.attivo  = TRUE
   AND lrc.validita @> script.fn_data_operativa()
   AND lv.attivo   = TRUE
   AND lv.stato    IN ('ATTIVA', 'CHIUSA')
   AND lv.validita @> script.fn_data_operativa()
   -- 2026-10-08 (§F.2): un bundle di un listino dell'emittente di chi agisce, perche'
   --   il contratto del fixture e' suo.
   AND EXISTS (SELECT 1 FROM vendite.listini l
                WHERE l.id = lv.listino_id
                  AND l.emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore())
 ORDER BY lrc.id
 LIMIT 1;

-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo). Il listino e'
--   quello del bundle trovato nei dati (il soggetto del test), quindi il CLIENTE si
--   costruisce sulla sua utility, legato dal z90 all'emittente di chi agisce; prima
--   era il primo billing account in assoluto. Senza bundle la utility e' NULL, il
--   builder prende la prima, e il contratto non nasce comunque.
CREATE TEMP TABLE tmp_esc_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'esclusione figlio bundle',
    (SELECT l.utility_id FROM vendite.listini l
      WHERE l.id = (SELECT listino_id FROM tmp_esc_bundle LIMIT 1)));

CREATE TEMP TABLE tmp_esc_ctx AS
SELECT
    c.billing_account_id    AS ba_id,
    c.istanza_utility_id,
    c.utility_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'  LIMIT 1) AS id_draft,
    (SELECT id FROM catalogo.unita_misura WHERE attivo = TRUE ORDER BY id LIMIT 1) AS uom_id
  FROM tmp_esc_cli c;

-- Articolo standalone nel listino del bundle (non è figlio di bundle)
CREATE TEMP TABLE tmp_esc_standalone AS
SELECT lr.articolo_id
  FROM vendite.listini_righe lr
 WHERE lr.listino_versione_id = (SELECT listino_versione_id FROM tmp_esc_bundle LIMIT 1)
   AND lr.attivo              = TRUE
   AND NOT EXISTS (
       SELECT 1 FROM vendite.listini_righe_componenti lrc2
        WHERE lrc2.listino_versione_id = lr.listino_versione_id
          AND lrc2.articolo_figlio_id  = lr.articolo_id
          AND lrc2.attivo              = TRUE
   )
 LIMIT 1;

-- Contratto DRAFT con il listino del bundle (per test 3, 4, 5)
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, listino_id, valido_dal, valido_al)
SELECT 'PGTAP_ESC_CNT', c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, (SELECT listino_id FROM tmp_esc_bundle LIMIT 1),
       '2073-01-01'::date, '2073-12-31'::date
  FROM tmp_esc_ctx c
 WHERE (SELECT listino_id FROM tmp_esc_bundle LIMIT 1) IS NOT NULL;

-- ============================================================
SELECT plan(5);
-- ============================================================

-- ============================================================
-- 1) la check per tipo di riga compone la regola (rev 2026-10-13, Lotto 3b)
--    rev 2026-10-14 (Lotto 4, 20261014-02): i motivi stanno in
--    script.fn_check_articolo_riga_su_contesto, che la firma di sempre compone
--    col contesto del documento.
-- ============================================================
SELECT ok(
    (SELECT regexp_replace(prosrc, '--[^\n]*', '', 'g') ~ 'fn_check_esclusione_articolo_documento\s*\('
       FROM pg_proc
      WHERE oid = 'script.fn_check_articolo_riga_su_contesto(jsonb,uuid,bigint)'::regprocedure),
    '1) script.fn_check_articolo_riga_su_contesto compone script.fn_check_esclusione_articolo_documento'
);

-- ============================================================
-- 2) Trigger presente su vendite.contratti_righe
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'contratti_righe'
           AND t.tgname  = 'trg_contratti_righe_a10_guard_articolo_ammesso_ins_upd'
           AND t.tgfoid  = 'script.trgfn_righe_guard_articolo_ammesso()'::regprocedure
           AND NOT t.tgisinternal
    ),
    '2) Trigger trg_contratti_righe_a10_guard_articolo_ammesso_ins_upd presente'
);

-- ============================================================
-- 3) ESCLUSIONE su figlio bundle → raise P0001
--    COND: skip se nessun bundle disponibile nel DB
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_esc_bundle)
         OR NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_ESC_CNT')
    THEN skip('Nessun bundle in listini_righe_componenti o fixture non creata - skip', 1)
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.contratti_righe(
                contratto_id, articolo_id, tipo_eccezione)
              SELECT c.id, %L::uuid, 'ESCLUSIONE'
                FROM vendite.contratti c WHERE c.numero = 'PGTAP_ESC_CNT'$$,
            (SELECT figlio_id FROM tmp_esc_bundle LIMIT 1)
        ),
        'P0001',
        NULL,
        '3) ESCLUSIONE su figlio bundle → raise E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA'
    )
END;

-- ============================================================
-- 4) ESCLUSIONE su padre bundle → ammessa (LIVES_OK)
--    Il padre composito non è un figlio, l'ESCLUSIONE è valida
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_esc_bundle)
         OR NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_ESC_CNT')
    THEN skip('Nessun bundle disponibile o fixture non creata - skip', 1)
    ELSE lives_ok(
        format(
            $$INSERT INTO vendite.contratti_righe(
                contratto_id, articolo_id, tipo_eccezione)
              SELECT c.id, %L::uuid, 'ESCLUSIONE'
                FROM vendite.contratti c WHERE c.numero = 'PGTAP_ESC_CNT'$$,
            (SELECT padre_id FROM tmp_esc_bundle LIMIT 1)
        ),
        '4) ESCLUSIONE su padre bundle → ammessa (padre non è figlio)'
    )
END;

-- ============================================================
-- 5) ESCLUSIONE su articolo standalone (non figlio bundle) → ammessa
--    COND: skip se nessun articolo standalone trovato nel listino
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM tmp_esc_standalone)
         OR NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_ESC_CNT')
    THEN skip('Nessun standalone trovato nel listino o fixture non creata - skip', 1)
    ELSE lives_ok(
        format(
            $$INSERT INTO vendite.contratti_righe(
                contratto_id, articolo_id, tipo_eccezione)
              SELECT c.id, %L::uuid, 'ESCLUSIONE'
                FROM vendite.contratti c WHERE c.numero = 'PGTAP_ESC_CNT'$$,
            (SELECT articolo_id FROM tmp_esc_standalone LIMIT 1)
        ),
        '5) ESCLUSIONE su standalone non-figlio → ammessa'
    )
END;

SELECT * FROM finish();
ROLLBACK;
