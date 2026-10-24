-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard transizione stato su vendite.contratti
--       (migration 20260426-05, aggiornato 20260514-02).
--
-- Indice test (1..9):
--   1) DRAFT -> ATTIVO ammesso
--   2) ATTIVO -> DRAFT vietato (E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA)
--   3) ATTIVO -> CESSATO con valido_al NULL vietato
--   4) ATTIVO -> CESSATO con valido_al futuro AMMESSO  [invertito 20260514]
--   5) ATTIVO -> CESSATO con valido_al passato VIETATO (E_CONTRATTO_VALIDO_AL_RETROATTIVO) [invertito]
--   6) CESSATO -> ATTIVO vietato (stato terminale)
--   7) ATTIVO -> ATTIVO no-op ammesso (WHEN distinct filter)
--   8) ATTIVO -> CESSATO con valido_al = script.fn_data_operativa() ammesso  [nuovo]
--   9) Job automatico (GUC app.cessazione_automatica=true): valido_al passato ammesso [nuovo]
--
-- Strategia fixture:
--   - Clona BA da seed esistente (utility commercio, no tipi_utenze)
--     per non incrociare il guard tipo_classe.
--   - Crea contratti modalita' A (listino + variazione globale) con
--     periodi disgiunti per non violare ex_contratti_no_overlap.
--   - SOSPESO escluso dai test: non in scope per il guard attuale.
--
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i contratti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima nascevano
--   gia' ATTIVO o CESSATO). _D (valido_al 2019, passato) arriva a CESSATO per la
--   strada del job notturno (GUC app.cessazione_automatica, come al test 9): la
--   cessazione manuale retroattiva e' vietata, ed e' il caso del test 5.
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

SELECT plan(9);

-- ============================================================
-- Setup fixture: BA + lookup stati
-- ============================================================
-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.6.5): il
--   cliente e il billing account sono COSTRUITI (dbops.fn_pgtap_crea_cliente_ba),
--   come il listino. Prima erano «il primo BA per id» del DB: su un database
--   ricostruito da zero (CI) non c'e' nessun BA e il file era nel registro dei
--   rossi di CI per questo.
CREATE TEMP TABLE tmp_ctx_ba AS
SELECT billing_account_id, istanza_utility_id, utility_id
  FROM dbops.fn_pgtap_crea_cliente_ba(
    'guard transizione contratto',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_ctx_stati AS
SELECT
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT')   AS id_draft,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO')  AS id_attivo,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'CESSATO') AS id_cessato;

-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.2, A-D2): il
--   listino e' COSTRUITO, con una versione valida da oggi. Prima era «il primo
--   listino attivo per id» del DB, e il fixture ci ATTIVA dei contratti: da quel
--   giorno un contratto con un listino senza versione in vigore non si attiva
--   piu', e l'esito dipendeva da cosa c'era sulla macchina.
CREATE TEMP TABLE tmp_ctx_listino AS
SELECT listino_id FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_ctx_ba), 'guard transizione contratto');

-- ============================================================
-- Slot fixture: 6 contratti modalita' A su periodi disgiunti.
--   _A   DRAFT  2080-01-01..2080-12-31 (test 1: DRAFT->ATTIVO)
--   _B   ATTIVO 2081-01-01..2081-12-31 (test 2,3; valido_al futuro per test 4)
--   _C   ATTIVO 2020-01-01..2020-12-31 (test 5: valido_al passato; test 9: GUC bypass)
--   _D   CESSATO 2019-01-01..2019-12-31 (test 6: terminale)
--   _E   ATTIVO 2082-01-01..2082-12-31 (test 7: no-op)
--   _F   ATTIVO script.fn_data_operativa()-30..script.fn_data_operativa() (test 8: valido_al = oggi)
-- ============================================================

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_A', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       DATE '2080-01-01', DATE '2080-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_B', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       DATE '2081-01-01', DATE '2081-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_C', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       DATE '2020-01-01', DATE '2020-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_D', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       DATE '2019-01-01', DATE '2019-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_E', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       DATE '2082-01-01', DATE '2082-12-31',
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al,
    listino_id, tipo_variazione_globale, valore_variazione_globale
)
SELECT 'PGTAP_GUARD_F', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       script.fn_data_operativa() - 30, script.fn_data_operativa(),
       l.listino_id, 'PERCENTUALE', -10
  FROM tmp_ctx_ba ba, tmp_ctx_listino l;

-- Gli stati di partenza, per la matrice e sotto i guard veri (rev 2026-10-24).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', k.id, 'ATTIVO')
  FROM vendite.contratti k
 WHERE k.numero IN ('PGTAP_GUARD_B', 'PGTAP_GUARD_C', 'PGTAP_GUARD_D',
                    'PGTAP_GUARD_E', 'PGTAP_GUARD_F')
 ORDER BY k.numero;

-- _D a CESSATO col valido_al passato: la strada del job (test 9), con la GUC
-- rimessa a vuoto subito dopo — i test 5 e successivi la vogliono spenta.
SELECT set_config('app.cessazione_automatica', 'true', true);
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti', k.id, 'CESSATO')
  FROM vendite.contratti k
 WHERE k.numero = 'PGTAP_GUARD_D';
SELECT set_config('app.cessazione_automatica', '', true);

-- ============================================================
-- 1) DRAFT -> ATTIVO ammesso
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_A'$$,
    '1) DRAFT -> ATTIVO e'' una transizione ammessa dal workflow contratti'
);

-- ============================================================
-- 2) ATTIVO -> DRAFT vietato (PGTAP_GUARD_B e'' ATTIVO)
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_draft FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_B'$$,
    'P0001',
    NULL,
    '2) ATTIVO -> DRAFT bloccato (irreversibile)'
);

-- ============================================================
-- 3) ATTIVO -> CESSATO con valido_al NULL vietato
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati),
             valido_al = NULL
       WHERE numero = 'PGTAP_GUARD_B'$$,
    'P0001',
    NULL,
    '3) ATTIVO -> CESSATO con valido_al NULL bloccato (E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA)'
);

-- ============================================================
-- 4) ATTIVO -> CESSATO con valido_al futuro AMMESSO
--    (PGTAP_GUARD_B ha valido_al = 2081-12-31 nel futuro)
--    Regola post-fix: valido_al >= script.fn_data_operativa() ammessa.
--    La cessazione e' immediata; il contratto risulta CESSATO con
--    data fine futura (informativa).
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_B'$$,
    '4) ATTIVO -> CESSATO con valido_al futuro AMMESSO (cessazione programmata)'
);

-- ============================================================
-- 5) ATTIVO -> CESSATO con valido_al passato VIETATO
--    (PGTAP_GUARD_C ha valido_al = 2020-12-31, nel passato)
--    Regola post-fix: cessazione manuale retroattiva bloccata.
--    Errore specifico: E_CONTRATTO_VALIDO_AL_RETROATTIVO (449).
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_C'$$,
    'P0001',
    NULL,
    '5) ATTIVO -> CESSATO con valido_al passato BLOCCATO (E_CONTRATTO_VALIDO_AL_RETROATTIVO)'
);

-- ============================================================
-- 6) CESSATO -> ATTIVO vietato (PGTAP_GUARD_D e'' CESSATO)
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_D'$$,
    'P0001',
    NULL,
    '6) CESSATO -> ATTIVO bloccato (stato terminale)'
);

-- ============================================================
-- 7) ATTIVO -> ATTIVO no-op ammesso (WHEN distinct filter)
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_E'$$,
    '7) ATTIVO -> ATTIVO (no-op) non deve invocare il guard'
);

-- ============================================================
-- 8) ATTIVO -> CESSATO con valido_al = script.fn_data_operativa() ammesso
--    (PGTAP_GUARD_F ha valido_al = script.fn_data_operativa())
--    Caso "cesso il contratto oggi": valido_al = oggi >= oggi.
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati)
       WHERE numero = 'PGTAP_GUARD_F'$$,
    '8) ATTIVO -> CESSATO con valido_al = script.fn_data_operativa() ammesso (cessazione immediata oggi)'
);

-- ============================================================
-- 9) Job automatico (GUC app.cessazione_automatica = true):
--    valido_al passato ammesso — simula fn_apply_chiusura_scadenze.
--    PGTAP_GUARD_C e'' ancora ATTIVO (test 5 era throws_ok, rollback a savepoint).
-- ============================================================
SELECT lives_ok(
    $body$
    DO $inner$
    BEGIN
        PERFORM set_config('app.cessazione_automatica', 'true', true);
        UPDATE vendite.contratti
           SET stato_doc_contratto_id = (SELECT id_cessato FROM tmp_ctx_stati)
         WHERE numero = 'PGTAP_GUARD_C';
    END
    $inner$
    $body$,
    '9) GUC cessazione_automatica=true: valido_al passato ammesso (simula job pgAgent)'
);

SELECT * FROM finish();
ROLLBACK;
