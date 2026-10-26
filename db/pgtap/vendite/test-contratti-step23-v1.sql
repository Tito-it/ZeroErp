-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §11): il contratto ha la porta sulla colonna di
--   stato (E_DOC_STATO_SOLO_DAL_VERBO). Le due attivazioni del setup (ATT, LV) passano dalla
--   fixture dbops.fn_pgtap_porta_a_stato (il verbo, con emetti_contratto concessa); i test 4 e 5
--   dal verbo vendite.fn_cambia_stato_contratto (prima UPDATE diretti dello stato); il 4 con
--   throws_like sulla frase di E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE (P0001 da solo passerebbe
--   anche su un rifiuto del verbo). Stessi esiti attesi.
-- pgTAP test per Zero ERP
--
-- Test: Step 2.3 — Trigger freeze listino_versione_id + lock post-attivazione
--       Migrations:
--         20260515-13 (freeze listino_versione_id su DRAFT→ATTIVO)
--         20260515-14 (lock post-attivazione testata + righe)
--
-- Indice test (1..13):
--   Struttura:
--   1)  Trigger freeze_listino_versione presente su contratti
--   2)  Le quattro colonne di pricing nel lock di testata fuori bozza (rev 2026-10-10: ritirato
--       trg_contratti_a10_lock_post_attivazione_upd, brief-db-testata-dopo-emissione fase 2)
--   3)  Il BB delle righe (trg_contratti_righe_a05_doc_righe_lock_fuori_bozza) presente su contratti_righe (rev 22-09)
--
--   Freeze versione e guard negoziato puro:
--   4)  DRAFT→ATTIVO senza listino + nessuna AGGIUNTA -> errore E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE
--   5)  DRAFT→ATTIVO senza listino + AGGIUNTA con prezzo -> ok
--   6)  (COND) DRAFT→ATTIVO con listino + versione attiva -> listino_versione_id fissato
--
--   Lock post-attivazione testata (contratti ATTIVI):
--   7)  UPDATE listino_id su contratto ATTIVO -> bloccato
--   8)  UPDATE valore_variazione_globale su contratto ATTIVO -> bloccato
--   9)  UPDATE valore_variazione_globale su contratto DRAFT -> ok
--
--   Lock post-attivazione righe:
--   10) INSERT riga su contratto ATTIVO -> bloccato
--   11) UPDATE riga su contratto ATTIVO -> bloccato
--   12) DELETE riga su contratto ATTIVO -> bloccato
--   13) INSERT riga su contratto DRAFT -> ok
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

-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo); fixture
--   costruito invece che preso dai dati. Cliente su una utility senza tipi_utenze,
--   legato dal z90 all'emittente di chi agisce; listino (versione ATTIVA da oggi)
--   sulla stessa utility. Effetto: il test 6 non va piu' in skip. Un cliente nuovo
--   non ha contratti che si sovrappongano a quelli del fixture.
CREATE TEMP TABLE tmp_s23_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'step23',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_s23_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_s23_cli), 'step23');

CREATE TEMP TABLE tmp_s23_ctx AS
SELECT
    c.billing_account_id                                           AS ba_id,
    c.istanza_utility_id,
    c.utility_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'  LIMIT 1) AS id_draft,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO' LIMIT 1) AS id_attivo,
    (SELECT listino_id FROM tmp_s23_listino)                                             AS listino_id
  FROM tmp_s23_cli c;

-- 3 articoli per i test righe
CREATE TEMP TABLE tmp_s23_arts AS
SELECT id, row_number() OVER (ORDER BY id) AS rn
  FROM catalogo.articoli a
 WHERE a.attivo = TRUE AND a.is_composito = FALSE
   -- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): l'articolo
   --   sta nel PERIMETRO delle righe: senza tipologia (decide la natura, la utility del
   --   cliente non conta) e con UNA_TANTUM/FISSA ammessa, chiesto alla sede unica.
   AND a.listino_tipologia_id IS NULL
   AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                WHERE e.tipo_erogazione = 'UNA_TANTUM' AND e.fonte_quantita_attesa = 'FISSA')
 ORDER BY id
 LIMIT 3;

-- Versione attiva del listino (per test 6 — condizionale)
CREATE TEMP TABLE tmp_s23_lv AS
SELECT lv.id AS versione_id
  FROM vendite.listini_versioni lv
 WHERE lv.listino_id = (SELECT listino_id FROM tmp_s23_ctx LIMIT 1)
   AND lv.validita @> script.fn_data_operativa()
   AND lv.attivo = TRUE
 LIMIT 1;

-- Contratto ATT: DRAFT, senza listino, con riga AGGIUNTA.
-- Verrà transitato ad ATTIVO durante il setup (dopo insert riga).
-- Usato per: test 7, 8, 10, 11, 12.
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_S23_ATT',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2070-01-01', '2070-12-31'
  FROM tmp_s23_ctx c;

-- Insert riga AGGIUNTA su ATT (mentre è DRAFT: lock non scatta)
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT ca.id, a.id, 'AGGIUNTA', 99.00, 1.00, 'UNA_TANTUM'
  FROM vendite.contratti ca, tmp_s23_arts a
 WHERE ca.numero = 'PGTAP_S23_ATT' AND a.rn = 1;

-- Transizione ATT → ATTIVO (freeze trigger scatta: listino_id NULL + riga AGGIUNTA → ok)
-- rev 2026-10-26 (§11): dalla fixture degli stati (il verbo), non con un UPDATE.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.id, 'ATTIVO')
  FROM vendite.contratti c
 WHERE c.numero = 'PGTAP_S23_ATT';

-- Contratto NEG_PURO: DRAFT, senza listino, senza righe (per test 4)
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_S23_NEG_PURO',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2071-01-01', '2071-12-31'
  FROM tmp_s23_ctx c;

-- Contratto NEG_OK: DRAFT, senza listino, con riga AGGIUNTA (per test 5)
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_S23_NEG_OK',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2072-01-01', '2072-12-31'
  FROM tmp_s23_ctx c;

-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT ca.id, a.id, 'AGGIUNTA', 50.00, 1.00, 'UNA_TANTUM'
  FROM vendite.contratti ca, tmp_s23_arts a
 WHERE ca.numero = 'PGTAP_S23_NEG_OK' AND a.rn = 2;

-- Contratto DRAFT: DRAFT, senza listino (per test 9 e 13)
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_S23_DRAFT',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2073-01-01', '2073-12-31'
  FROM tmp_s23_ctx c;

-- Contratto LV: DRAFT, con listino (per test 6 — condizionale)
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al, listino_id)
SELECT 'PGTAP_S23_LV',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2074-01-01', '2074-12-31', c.listino_id
  FROM tmp_s23_ctx c
 WHERE c.listino_id IS NOT NULL;

-- Transizione LV → ATTIVO nel fixture (condizionale: solo se versione attiva disponibile).
-- Il freeze trigger imposta listino_versione_id dal risultato della ricerca versione.
-- Se versione non trovata il test 6 fa skip.
-- rev 2026-10-26 (§11): dalla fixture degli stati (il verbo), non con un UPDATE.
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.id, 'ATTIVO')
  FROM vendite.contratti c
 WHERE c.numero = 'PGTAP_S23_LV'
   AND EXISTS (SELECT 1 FROM tmp_s23_lv WHERE versione_id IS NOT NULL);

-- ============================================================
SELECT plan(13);
-- ============================================================

-- ============================================================
-- 1) Trigger freeze_listino_versione presente su contratti
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace ns ON ns.oid = c.relnamespace
         WHERE ns.nspname = 'vendite'
           AND c.relname  = 'contratti'
           AND t.tgname   = 'trg_contratti_a10_freeze_listino_versione_upd'
    ),
    '1) Trigger trg_contratti_a10_freeze_listino_versione_upd presente'
);

-- ============================================================
-- 2) Le quattro colonne di pricing sono bloccate fuori bozza
--    rev 2026-10-10 (brief-db-testata-dopo-emissione, fase 2): il lock
--    post-attivazione (solo ATTIVO, fascia a10) e' ritirato; le blocca il
--    building block di testata in ogni stato fuori bozza, e parla prima del
--    guard del listino. Si chiede al montaggio, col lettore.
-- ============================================================
SELECT ok(
    (SELECT bool_and(NOT script.fn_doc_colonna_modificabile('vendite.contratti'::regclass, c.col::name, s.stato))
       FROM (VALUES ('listino_id'), ('listino_versione_id'), ('tipo_variazione_globale'),
                    ('valore_variazione_globale')) AS c(col),
            (VALUES ('ATTIVO'), ('CESSATO'), ('ANNULLATO')) AS s(stato))
    AND NOT EXISTS (SELECT 1 FROM pg_trigger t
                     WHERE t.tgrelid = 'vendite.contratti'::regclass
                       AND t.tgname = 'trg_contratti_a10_lock_post_attivazione_upd'),
    '2) listino, versione e variazioni globali bloccati fuori bozza in ogni stato dal lock di testata; il lock post-attivazione non c''e'' piu'''
);

-- ============================================================
-- 3) Il BB delle righe e' montato su contratti_righe
--    rev 2026-09-22: trg_contratti_righe_a10_lock_post_attivazione_ins_upd_dlt e la
--    sua funzione sono ritirati (20260922-06); la regola «righe solo in bozza» e'
--    il building block vendite.trgfn_doc_righe_lock_fuori_bozza, fascia _a05_.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace ns ON ns.oid = c.relnamespace
         WHERE ns.nspname = 'vendite'
           AND c.relname  = 'contratti_righe'
           AND t.tgname   = 'trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt'
    ),
    '3) Trigger trg_contratti_righe_a05_doc_righe_lock_fuori_bozza presente su contratti_righe'
);

-- ============================================================
-- 4) DRAFT→ATTIVO senza listino, senza righe AGGIUNTA -> errore
-- ============================================================
SELECT throws_like(
    $$SELECT * FROM vendite.fn_cambia_stato_contratto(
          (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_S23_NEG_PURO'), 'ATTIVO')$$,
    '%senza listino: impossibile attivare senza almeno una riga AGGIUNTA%',
    '4) DRAFT→ATTIVO senza listino + nessuna AGGIUNTA -> errore E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE'
);

-- ============================================================
-- 5) DRAFT→ATTIVO senza listino + AGGIUNTA con prezzo -> ok
-- ============================================================
SELECT lives_ok(
    $$SELECT * FROM vendite.fn_cambia_stato_contratto(
          (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_S23_NEG_OK'), 'ATTIVO')$$,
    '5) DRAFT→ATTIVO senza listino + AGGIUNTA con prezzo -> ok (freeze non blocca)'
);

-- ============================================================
-- 6) DRAFT→ATTIVO con listino + versione attiva -> listino_versione_id fissato
--    La transizione è avvenuta nel fixture; il test verifica solo il risultato.
--    SKIP se nessun contratto LV creato o nessuna versione attiva disponibile.
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_S23_LV')
         OR (SELECT versione_id FROM tmp_s23_lv LIMIT 1) IS NULL
    THEN skip('Nessun listino con versione attiva disponibile - skip test freeze versione', 1)
    ELSE ok(
        (SELECT listino_versione_id IS NOT NULL
           FROM vendite.contratti
          WHERE numero = 'PGTAP_S23_LV'),
        '6) DRAFT→ATTIVO con listino + versione attiva -> listino_versione_id fissato dal freeze trigger'
    )
END;

-- ============================================================
-- 7) UPDATE listino_id su contratto ATTIVO -> bloccato
--    2026-10-08 (§F.2): il listino nuovo e' quello coerente del fixture. Uno
--    qualunque dei dati lo rifiuterebbe prima il guard del listino del documento
--    («guard_l» < «lock_p»), con lo stesso SQLSTATE: il test sarebbe verde per il
--    motivo sbagliato.
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET listino_id = (SELECT listino_id FROM tmp_s23_ctx)
       WHERE numero = 'PGTAP_S23_ATT'$$,
    'P0001',
    NULL,
    '7) UPDATE listino_id su contratto ATTIVO -> bloccato (E_DOC_CONDIZIONI_FUORI_BOZZA dal 2026-10-10)'
);

-- ============================================================
-- 8) UPDATE valore_variazione_globale su contratto ATTIVO -> bloccato
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET valore_variazione_globale = -5
       WHERE numero = 'PGTAP_S23_ATT'$$,
    'P0001',
    NULL,
    '8) UPDATE valore_variazione_globale su contratto ATTIVO -> bloccato'
);

-- ============================================================
-- 9) UPDATE valore_variazione_globale su contratto DRAFT -> ok
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.contratti
         SET tipo_variazione_globale  = 'PERCENTUALE',
             valore_variazione_globale = -3
       WHERE numero = 'PGTAP_S23_DRAFT'$$,
    '9) UPDATE variazione globale su contratto DRAFT -> ok (lock non scatta)'
);

-- ============================================================
-- 10) INSERT riga su contratto ATTIVO -> bloccato
-- ============================================================
SELECT throws_ok(
    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate);
    --   senza, il P0001 atteso verrebbe dal guard nuovo e non da E_RIGA_DOC_NON_BOZZA.
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
             tipo_erogazione)
      SELECT ca.id, a.id, 'AGGIUNTA', 10.00, 1.00, 'UNA_TANTUM'
        FROM vendite.contratti ca, tmp_s23_arts a
       WHERE ca.numero = 'PGTAP_S23_ATT' AND a.rn = 2$$,
    'P0001',
    NULL,
    '10) INSERT riga su contratto ATTIVO -> bloccato E_RIGA_DOC_NON_BOZZA (BB, dal 22-09)'
);

-- ============================================================
-- 11) UPDATE riga su contratto ATTIVO -> bloccato
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.contratti_righe cr
         SET ordine = 99
        FROM vendite.contratti ca
       WHERE ca.numero = 'PGTAP_S23_ATT'
         AND cr.contratto_id = ca.id$$,
    'P0001',
    NULL,
    '11) UPDATE riga su contratto ATTIVO -> bloccato'
);

-- ============================================================
-- 12) DELETE riga su contratto ATTIVO -> bloccato
-- ============================================================
SELECT throws_ok(
    $$DELETE FROM vendite.contratti_righe cr
       USING vendite.contratti ca
       WHERE ca.numero = 'PGTAP_S23_ATT'
         AND cr.contratto_id = ca.id$$,
    'P0001',
    NULL,
    '12) DELETE riga su contratto ATTIVO -> bloccato'
);

-- ============================================================
-- 13) INSERT riga su contratto DRAFT -> ok
-- ============================================================
SELECT lives_ok(
    -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
             tipo_erogazione)
      SELECT ca.id, a.id, 'AGGIUNTA', 20.00, 1.00, 'UNA_TANTUM'
        FROM vendite.contratti ca, tmp_s23_arts a
       WHERE ca.numero = 'PGTAP_S23_DRAFT' AND a.rn = 3$$,
    '13) INSERT riga su contratto DRAFT -> ok (lock non scatta)'
);

SELECT * FROM finish();
ROLLBACK;
