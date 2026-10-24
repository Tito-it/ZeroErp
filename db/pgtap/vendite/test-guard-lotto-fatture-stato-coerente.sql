-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: guard di coerenza stato lotto <-> stato fatture
--       vendite.fn_guard_lotto_fatture_stato_coerente
--       + constraint trigger DEFERRED su fatture / fatturazione_lotti /
--         fatturazione_lotti_fatture
-- Brief: brief-db-guard-coerenza-stato-lotto-fatture §4.2
-- ------------------------------------------------------------
-- Indice test
--  1) Riferimenti minimi presenti
--  2) Lotto creato
--  3) Fatture test create (ok / critical)
--  4) Ponte lotto-fatture creato
--  5) Stato iniziale allineato => guard NON solleva
--  6) Lotto avanzato a EMESSA senza sync => guard SOLLEVA (caso incidente)
--  7) Dopo fn_sync_lotto_fatture_stato => guard NON solleva (non-regressione)
--  8) L eccezione critical e davvero rimasta indietro (anti-test-vacuo del 7)
--  9) La vista di sorveglianza non elenca l eccezione
-- 10) Lotto senza fatture => guard NON solleva
-- 11) I 3 constraint trigger esistono, sono CONSTRAINT e DEFERRED
-- 12) End-to-end con SET CONSTRAINTS IMMEDIATE: l'UPDATE che disallinea fallisce
-- ------------------------------------------------------------
-- NOTA SUL PERCHE' DI QUESTA STRUTTURA
-- Un CONSTRAINT TRIGGER DEFERRABLE INITIALLY DEFERRED scatta al COMMIT. Questo
-- file, come 140 pgTAP su 144, chiude in ROLLBACK: i trigger non scatterebbero
-- MAI da soli. Un test che si limitasse a disallineare e sperare nel fallimento
-- passerebbe senza aver verificato nulla -- il modo peggiore di fallire.
-- Quindi:
--   - i test 5..10 chiamano il guard DIRETTAMENTE (logica, deterministica);
--   - il test 11 verifica il CABLAGGIO su pg_catalog (trigger giusti, sulle
--     tabelle giuste, davvero constraint e davvero deferred);
--   - il test 12 forza `SET CONSTRAINTS ALL IMMEDIATE` per esercitare la catena
--     completa trigger -> trgfn -> guard.
-- ------------------------------------------------------------
BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

CREATE TEMP TABLE tmp_costanti_glf AS
SELECT ('pgtap_guard_lotto_fatt_' || to_char(clock_timestamp(), 'YYMMDDHH24MISS'))::text AS test_scope;

-- ⭐ IL CLIENTE SI COSTRUISCE (rev 2026-10-24, brief-modello-documento-vendita
--   Q-4). Prima billing account, utility ed emittente erano «il primo BA del
--   database con un emittente»: su un database ricostruito (CI, lo scratch) non
--   c'e', e il file moriva al test 1 senza provare il guard. Il mondo nasce
--   nell'azienda di chi agisce (il contesto e' gia' aperto).
CREATE TEMP TABLE tmp_mondo_glf AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('guard lotto fatture');

-- ⚠️ Il builder esce IMMEDIATE (il suo contratto). Questo file lavora apposta
--   con i trigger DIFFERITI e chiama il guard a mano (vedi la nota in testa):
--   la finestra differita si riapre subito dopo, come prescrive il builder.
SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE tmp_refs_glf AS
SELECT
  (SELECT m.registro_id
     FROM vendite.tipi_doc_fiscale_registri m
     JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1) AS registro_id,
  (SELECT w.billing_account_id FROM tmp_mondo_glf w) AS billing_account_id,
  (SELECT w.utility_id FROM tmp_mondo_glf w) AS utility_id,
  (SELECT m.tipo_doc_fiscale_id
     FROM vendite.tipi_doc_fiscale_registri m
     JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE ORDER BY m.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT w.emittente_soggetto_ruolo_id FROM tmp_mondo_glf w) AS emittente_soggetto_ruolo_id,
  (SELECT s.id FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1) AS stato_draft_id,
  (SELECT s.id FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'EMESSA' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1) AS stato_emessa_id;


-- ⛔ IL REGISTRO SI ALLINEA ALL'EMITTENTE, e prima non lo faceva.
--   La riga sopra sceglieva «un registro qualunque» accanto a un emittente che
--   viene da un'altra parte: che i due coincidessero era un CASO, e dal
--   2026-08-30 vendite.trgfn_fatture_guard_registro_emittente non lo ammette
--   piu'. L'helper risponde con il registro di QUESTO emittente, creandolo se
--   non ce n'e' uno — la riga vive nella transazione del test.
UPDATE tmp_refs_glf SET registro_id = script.fn_pgtap_registro_fattura(emittente_soggetto_ruolo_id);
SELECT ok(
  (SELECT registro_id IS NOT NULL AND billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL AND tipo_doc_fiscale_id IS NOT NULL
      AND valuta_id IS NOT NULL AND emittente_soggetto_ruolo_id IS NOT NULL
      AND stato_draft_id IS NOT NULL AND stato_emessa_id IS NOT NULL
     FROM tmp_refs_glf),
  '1) Riferimenti minimi presenti'
);

-- ------------------------------------------------------------
-- Fixture: un lotto con tre fatture (ok / critical / da-escludere)
-- ------------------------------------------------------------
CREATE TEMP TABLE tmp_lotto_glf AS
SELECT vendite.fn_create_fatturazione_lotto(
    p_competenza_mese            => date_trunc('month', script.fn_data_operativa())::date,
    p_tipo_doc_fiscale_id        => (SELECT tipo_doc_fiscale_id FROM tmp_refs_glf),
    p_utility_id                 => (SELECT utility_id FROM tmp_refs_glf),
    p_billing_account_id         => (SELECT billing_account_id FROM tmp_refs_glf),
    p_lock_batch_id              => NULL,
    p_meta                       => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_glf)),
    p_emittente_soggetto_ruolo_id=> (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_glf)
  ) AS lotto_id;

SELECT ok(
  (SELECT lotto_id IS NOT NULL AND lotto_id > 0 FROM tmp_lotto_glf),
  '2) Lotto creato'
);

CREATE TEMP TABLE tmp_fatture_glf AS
WITH base AS (
  SELECT r.registro_id, r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.stato_draft_id, r.valuta_id,
         c.test_scope
    FROM tmp_refs_glf r CROSS JOIN tmp_costanti_glf c
), ins AS (
  INSERT INTO vendite.fatture (
    registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
    tipo_doc_fiscale_id, stato_doc_fiscale_id, valuta_id, totale_a_pagare,
    critical, meta
  )
  SELECT b.registro_id, script.fn_data_operativa(), b.emittente_soggetto_ruolo_id, b.billing_account_id,
         b.tipo_doc_fiscale_id, b.stato_draft_id, b.valuta_id, v.importo,
         v.critical,
         jsonb_build_object('test_scope', b.test_scope, 'case', v.caso)
    FROM base b
    CROSS JOIN (VALUES (10.00, FALSE, 'ok'),
                       (12.00, TRUE,  'critical')) AS v(importo, critical, caso)
  RETURNING id, critical, stato_doc_fiscale_id, meta ->> 'case' AS caso
)
SELECT * FROM ins;

SELECT is(
  (SELECT count(*)::int FROM tmp_fatture_glf), 2,
  '3) Fatture test create (ok / critical)'
);

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id, meta)
SELECT (SELECT lotto_id FROM tmp_lotto_glf),
       f.id,
       f.stato_doc_fiscale_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_glf))
  FROM tmp_fatture_glf f;

SELECT is(
  (SELECT count(*)::int FROM vendite.fatturazione_lotti_fatture
    WHERE lotto_id = (SELECT lotto_id FROM tmp_lotto_glf)), 2,
  '4) Ponte lotto-fatture creato'
);

-- ------------------------------------------------------------
-- 5) Stato iniziale: tutto DRAFT, lotto DRAFT => coerente
-- ------------------------------------------------------------
SELECT lives_ok(
  format('SELECT vendite.fn_guard_lotto_fatture_stato_coerente(%s)',
         (SELECT lotto_id FROM tmp_lotto_glf)),
  '5) Stato allineato => guard non solleva'
);

-- ------------------------------------------------------------
-- 6) IL CASO DELL'INCIDENTE: il lotto avanza, le fatture no.
--    E' esattamente cio' che produce un dry-run della pipeline BE.
-- ------------------------------------------------------------
UPDATE vendite.fatturazione_lotti
   SET stato_doc_fiscale_id = (SELECT stato_emessa_id FROM tmp_refs_glf)
 WHERE id = (SELECT lotto_id FROM tmp_lotto_glf);

SELECT throws_ok(
  format('SELECT vendite.fn_guard_lotto_fatture_stato_coerente(%s)',
         (SELECT lotto_id FROM tmp_lotto_glf)),
  'P0001',
  NULL,
  '6) Lotto avanzato senza sync => guard solleva E_LOTTO_FATTURE_STATO_INCOERENTE'
);

-- ------------------------------------------------------------
-- 7) Riallineamento con la funzione canonica => guard verde.
--    Non-regressione: il percorso reale della pipeline non e' ostacolato.
--
-- ⚠️ PREPARAZIONE OBBLIGATORIA DAL 2026-07-31 (piano satelliti I.4). Il sync
--    porta a EMESSA la sola fattura non critical — il caso 'ok' —
--    e da oggi vendite.trgfn_fatture_guard_uscita_draft pretende che chi lascia
--    la bozza sia completo: indirizzo obbligatorio dell'ambito FATTURE piu'
--    intestazione fiscale congelata delle due parti. Senza queste due
--    scritture il sync fallirebbe con E_FATTURA_NON_EMETTIBILE_INCOMPLETA e il
--    test 7 diventerebbe rosso per una ragione che non sta esaminando.
--    L'altra fattura (critical) resta volutamente nuda: il sync non la tocca,
--    ed e' proprio cio' che il test 8 verifica.
--    ⚠️ Adeguamento 2026-08-04 (D-M): le eccezioni erano DUE, `esclusa` e
--    `critical`. Il flag `esclusa` e' stato eliminato perche' dormiente
--    (nessuno lo valorizzava), quindi la terza fattura della fixture e' sparita
--    con lui: senza il flag sarebbe stata una fattura come le altre, il sync
--    l'avrebbe allineata e — non essendo preparata con indirizzo e
--    intestazione — avrebbe fatto fallire il test 7 con
--    E_FATTURA_NON_EMETTIBILE_INCOMPLETA, cioe' per una ragione che il test
--    non sta esaminando.
-- ------------------------------------------------------------
INSERT INTO vendite.fatture_indirizzi (fattura_id, tipo_indirizzo_id, snapshot)
SELECT f.id,
       (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT'),
       '{"intestazione":"Cliente pgTAP","via":"Via Guard Coerenza"}'::jsonb
  FROM tmp_fatture_glf f
 WHERE f.caso = 'ok';

UPDATE vendite.fatture
   -- ⚠️ con la sede del cedente: senza, la fattura non lascia DRAFT
   --   (20261021-13, brief-db-modelli-documento-standard §10.7 R-5).
   SET emittente_snapshot = '{"denominazione":"Emittente pgTAP","sede":{"via":"Via Cedente 1","cap":"83100"}}'::jsonb,
       cliente_snapshot   = '{"denominazione":"Cliente pgTAP"}'::jsonb
 WHERE id = (SELECT id FROM tmp_fatture_glf WHERE caso = 'ok');

SELECT vendite.fn_sync_lotto_fatture_stato(
  (SELECT lotto_id FROM tmp_lotto_glf),
  (SELECT stato_emessa_id FROM tmp_refs_glf)
);

SELECT lives_ok(
  format('SELECT vendite.fn_guard_lotto_fatture_stato_coerente(%s)',
         (SELECT lotto_id FROM tmp_lotto_glf)),
  '7) Dopo fn_sync_lotto_fatture_stato => guard non solleva'
);

-- ------------------------------------------------------------
-- 8) ANTI-TEST-VACUO: il 7 vale solo se le due eccezioni sono
--    DAVVERO rimaste indietro. Se il sync le avesse allineate,
--    il 7 passerebbe senza dimostrare nulla sulle eccezioni.
-- ------------------------------------------------------------
SELECT ok(
  (SELECT bool_and(f.stato_doc_fiscale_id = (SELECT stato_draft_id FROM tmp_refs_glf))
     FROM vendite.fatturazione_lotti_fatture lf
     JOIN vendite.fatture f ON f.id = lf.fattura_id
    WHERE lf.lotto_id = (SELECT lotto_id FROM tmp_lotto_glf)
      AND COALESCE(f.critical, FALSE) IS TRUE),
  '8) Fattura critical rimasta a DRAFT mentre il lotto e'' EMESSA (eccezione reale)'
);

-- ------------------------------------------------------------
-- 9) La vista di sorveglianza concorda col guard: nessuna riga.
-- ------------------------------------------------------------
SELECT is(
  (SELECT count(*)::int FROM vendite.vw_lotti_fatture_incoerenti
    WHERE lotto_id = (SELECT lotto_id FROM tmp_lotto_glf)), 0,
  '9) vw_lotti_fatture_incoerenti non elenca le eccezioni'
);

-- ------------------------------------------------------------
-- 10) Lotto senza fatture: nulla da confrontare, deve passare.
-- ------------------------------------------------------------
CREATE TEMP TABLE tmp_lotto_vuoto_glf AS
SELECT vendite.fn_create_fatturazione_lotto(
    p_competenza_mese            => (date_trunc('month', script.fn_data_operativa()) - interval '1 month')::date,
    p_tipo_doc_fiscale_id        => (SELECT tipo_doc_fiscale_id FROM tmp_refs_glf),
    p_utility_id                 => (SELECT utility_id FROM tmp_refs_glf),
    p_billing_account_id         => (SELECT billing_account_id FROM tmp_refs_glf),
    p_lock_batch_id              => NULL,
    p_meta                       => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_glf)),
    p_emittente_soggetto_ruolo_id=> (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_glf)
  ) AS lotto_id;

SELECT lives_ok(
  format('SELECT vendite.fn_guard_lotto_fatture_stato_coerente(%s)',
         (SELECT lotto_id FROM tmp_lotto_vuoto_glf)),
  '10) Lotto senza fatture => guard non solleva'
);

-- ------------------------------------------------------------
-- 11) CABLAGGIO: i tre trigger esistono, sono CONSTRAINT e DEFERRED.
--     tgconstraint <> 0 => constraint trigger; tgdeferrable/tginitdeferred
--     => differito. Senza questo, il guard potrebbe non essere agganciato.
-- ------------------------------------------------------------
SELECT is(
  (SELECT count(*)::int
     FROM pg_trigger t
     JOIN pg_class c ON c.oid = t.tgrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relname IN ('fatture', 'fatturazione_lotti', 'fatturazione_lotti_fatture')
      AND t.tgname LIKE '%def_guard_stato%'
      AND NOT t.tgisinternal
      AND t.tgconstraint <> 0
      AND t.tgdeferrable
      AND t.tginitdeferred), 3,
  '11) I 3 constraint trigger esistono, sono CONSTRAINT e INITIALLY DEFERRED'
);

-- ------------------------------------------------------------
-- 12) END-TO-END. A questo punto lo stato e' coerente, quindi si puo'
--     passare a IMMEDIATE senza far scattare violazioni pendenti.
--     Da qui il trigger valuta subito: l'UPDATE che disallinea deve
--     fallire da solo, senza chiamare il guard a mano.
-- ------------------------------------------------------------
SET CONSTRAINTS ALL IMMEDIATE;

SELECT throws_ok(
  format($q$ UPDATE vendite.fatturazione_lotti
                SET stato_doc_fiscale_id = %s
              WHERE id = %s $q$,
         (SELECT stato_draft_id FROM tmp_refs_glf),
         (SELECT lotto_id FROM tmp_lotto_glf)),
  'P0001',
  NULL,
  '12) Con constraint IMMEDIATE l''UPDATE che disallinea il lotto fallisce'
);

SET CONSTRAINTS ALL DEFERRED;

SELECT * FROM finish();
ROLLBACK;
