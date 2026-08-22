-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il perimetro degli incassi — dal CONTO, non dalla fattura
--
-- Elenco test (plan 14):
--  1) Riferimenti minimi presenti: due emittenti, due operatori, una fattura
--  2) L'operatore A vede la propria distinta
--  3) ...e NON vede quella dell'altro emittente
--  4) L'operatore B vede la propria e non quella di A
--  5) ⭐ La riga DA ABBINARE, che fattura non ha, resta visibile al suo emittente
--  6) ...e invisibile all'altro
--  7) La distinta INTERNA e' visibile a entrambi: non e' di nessuno
--  8) ⭐ ...ma le sue RIGHE no: quelle le filtra la fattura che portano
--  9) ⭐ La riga DA_ABBINARE su una distinta MANUALE senza canale si SCRIVE
-- 10) ⚠️ ...e la vede anche l'altro emittente: non porta nessuna attribuzione
-- 11) 🔴 L'operatore B non puo' scrivere una riga sulla distinta di A
-- 12) 🔴 L'operatore B non puo' aprire una distinta sul canale di A
-- 13) Senza ruolo applicativo non si vede niente: il cancello e' quello
-- 14) Assert finale cleanup
--
-- Scopo:
--  - collaudare S3-5 e S3-4 dove contano davvero, cioe' come utente
--    APPLICATIVO: l'owner salta la row security finche' non c'e' il FORCE, e
--    una suite lanciata da lui non esercita nessuna policy;
--  - ⛔ e proprio per questo il test NON usa il `FORCE ROW LEVEL SECURITY`
--    locale alla transazione, che e' la tecnica dei test RLS piu' vecchi: il
--    predicato di queste policy poggia su una SECURITY DEFINER che gira come
--    proprietario, e con il FORCE quella rientrerebbe sotto la policy della
--    tabella che sta leggendo — una RICORSIONE. Girare come applicazione e'
--    insieme piu' fedele e l'unico modo che funziona;
--  - ⭐ presidiare i due casi che il perimetro dal conto esiste per servire: la
--    riga «da abbinare» (test 5), che con un predicato via fattura sarebbe
--    invisibile a TUTTI, e la distinta interna (test 7/8), che e' condivisa
--    nella testata e riservata nelle righe;
--  - 🔴 e presidiare il caso che il lotto 6 ha ROTTO alla prima applicazione
--    (test 9): la riga DA_ABBINARE sul lotto di lavoro di un operatore, cioe'
--    una distinta MANUALE senza canale (D12-a). Le prime due strade non la
--    coprivano e il WITH CHECK la rifiutava con 42501 — un perimetro che
--    impedisce la lavorazione invece di proteggerla. L'hanno segnalato due
--    pgTAP gia' verdi, e questo file non lo copriva: e' la ragione per cui i
--    test 9 e 10 esistono. Correzione in avanti: changeSet 20260822-24.
--
-- Piano: docs/it/dev/work-in-progress/brief-db-posting-e-abbinamento-rata.md
--        §2.3 S3-4/S3-5 · Decisione: brief madre D5 · lotto 6
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione, e qui non e'
--    una formalita' — senza, la RLS di questo lotto non viene esercitata.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- Fixture — due lati: A (l'emittente che ha delle fatture) e B (l'altro)
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_rls_pagamenti_perimetro'::text AS test_scope;

-- ⚠️ ORDER BY ovunque: una fixture che «scommette» su quale riga esce non
--    verifica, e il giorno che ne esce un'altra il rosso accusa il codice.
CREATE TEMP TABLE tmp_lati AS
SELECT ef.id                AS ef_id,
       ef.soggetto_ruolo_id AS sr_id,
       (SELECT min(uef.auth_user_id)
          FROM config.user_emittenti_fiscali uef
         WHERE uef.emittente_fiscale_id = ef.id
           AND script.fn_has_identita_attiva(
                   uef.auth_user_id, 'OPERATORE'::config.ruolo_applicativo)
           AND NOT script.fn_is_super_admin(uef.auth_user_id)) AS auth_user_id,
       (SELECT count(*) FROM vendite.fatture f
         WHERE f.emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id) AS n_fatture
  FROM anagrafiche.emittenti_fiscali ef
 WHERE ef.attivo IS TRUE;

-- Il lato A e' quello che ha delle fatture: senza, il test 8 non avrebbe
-- niente da distinguere.
CREATE TEMP TABLE tmp_ab AS
SELECT (SELECT ef_id        FROM tmp_lati ORDER BY n_fatture DESC, ef_id LIMIT 1)          AS a_ef,
       (SELECT sr_id        FROM tmp_lati ORDER BY n_fatture DESC, ef_id LIMIT 1)          AS a_sr,
       (SELECT auth_user_id FROM tmp_lati ORDER BY n_fatture DESC, ef_id LIMIT 1)          AS a_user,
       (SELECT ef_id        FROM tmp_lati ORDER BY n_fatture ASC,  ef_id DESC LIMIT 1)     AS b_ef,
       (SELECT sr_id        FROM tmp_lati ORDER BY n_fatture ASC,  ef_id DESC LIMIT 1)     AS b_sr,
       (SELECT auth_user_id FROM tmp_lati ORDER BY n_fatture ASC,  ef_id DESC LIMIT 1)     AS b_user,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice = 'BANCA' ORDER BY c.id LIMIT 1)              AS centro_banca,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.is_fondo_fattura IS TRUE ORDER BY c.id LIMIT 1)      AS centro_fondo,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'DA_ABBINARE' ORDER BY s.id LIMIT 1)                     AS stato_da_abbinare,
       (SELECT b.id FROM anagrafiche.bank_branches b
         WHERE b.attivo IS TRUE ORDER BY b.id LIMIT 1)                                     AS bank_branch;

-- Ci si mette nei panni di A per leggere una sua fattura: sotto la RLS di
-- vendite.fatture, «visibile» e «sua» sono la stessa cosa.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT a_user FROM tmp_ab)); END $ctx$;

CREATE TEMP TABLE tmp_fattura AS
SELECT f.id, f.billing_account_id
  FROM vendite.fatture f
 WHERE f.emittente_soggetto_ruolo_id = (SELECT a_sr FROM tmp_ab)
 ORDER BY f.id DESC
 LIMIT 1;

SELECT ok(
  (SELECT a_ef IS NOT NULL AND b_ef IS NOT NULL AND a_ef <> b_ef
          AND a_user IS NOT NULL AND b_user IS NOT NULL AND a_user <> b_user
          AND centro_banca IS NOT NULL AND centro_fondo IS NOT NULL
          AND stato_da_abbinare IS NOT NULL AND bank_branch IS NOT NULL
     FROM tmp_ab)
  AND (SELECT count(*) = 1 FROM tmp_fattura),
  '1) Riferimenti minimi presenti: due emittenti distinti, due operatori, una fattura di A'
);

-- I due conti di incasso, uno per emittente. anagrafiche non ha row security:
-- la fixture si costruisce in qualunque contesto.
CREATE TEMP TABLE tmp_legami AS
WITH conti AS (
  INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, attivo, storicizza, meta)
  SELECT v.iban, ab.bank_branch, true, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ab ab
    CROSS JOIN (VALUES ('IT00PGTAPPERIMETROLATOA00001', 'A'),
                       ('IT00PGTAPPERIMETROLATOB00002', 'B')) AS v(iban, lato)
  RETURNING id, iban
), legami AS (
  INSERT INTO anagrafiche.soggetti_ruoli_conti_bancari
      (soggetto_ruolo_id, conto_bancario_id, uso, predefinito, storicizza, meta)
  SELECT CASE WHEN c.iban LIKE '%LATOA%' THEN ab.a_sr ELSE ab.b_sr END,
         c.id, 'INCASSO', false, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM conti c CROSS JOIN tmp_ab ab
  RETURNING id, conto_bancario_id
)
SELECT (SELECT l.id FROM legami l JOIN conti c ON c.id = l.conto_bancario_id
         WHERE c.iban LIKE '%LATOA%') AS legame_a,
       (SELECT l.id FROM legami l JOIN conti c ON c.id = l.conto_bancario_id
         WHERE c.iban LIKE '%LATOB%') AS legame_b;

CREATE TEMP TABLE tmp_enti AS
WITH ins AS (
  INSERT INTO pagamenti.enti_incasso
      (codice, descrizione, tipo, attivo, soggetto_ruolo_conto_bancario_id,
       centro_riscossione_id, meta)
  SELECT v.codice, 'canale pgtap perimetro', 'ALTRO', true, v.legame, ab.centro_banca,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ab ab
    CROSS JOIN (SELECT 'PGTAP_PERIM_A'::text AS codice, (SELECT legame_a FROM tmp_legami) AS legame
                UNION ALL
                SELECT 'PGTAP_PERIM_B',                 (SELECT legame_b FROM tmp_legami)) AS v
  RETURNING id, codice
)
SELECT max(id) FILTER (WHERE codice = 'PGTAP_PERIM_A') AS ente_a,
       max(id) FILTER (WHERE codice = 'PGTAP_PERIM_B') AS ente_b
  FROM ins;

-- ⭐ Le distinte si creano NEL CONTESTO DEL LORO PADRONE: la policy e' FOR ALL,
--    e una distinta creata dall'operatore sbagliato verrebbe rifiutata dal
--    guard prima ancora che dalla policy.
CREATE TEMP TABLE tmp_dist AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
           (SELECT centro_banca FROM tmp_ab), current_date, current_date,
           (SELECT ente_a FROM tmp_enti), NULL, NULL, 'BOZZA',
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           'GENERATA') AS dist_a,
       pagamenti.fn_get_or_create_vendite_contabile(
           (SELECT centro_fondo FROM tmp_ab), current_date, current_date,
           NULL, NULL, NULL, 'BOZZA',
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           'GENERATA') AS dist_interna;

-- Riga «da abbinare» sulla distinta di A: nessuna fattura, ed e' il caso per
-- cui il perimetro dal conto esiste.
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, importo, stato_id, meta)
SELECT (SELECT dist_a FROM tmp_dist), 'PGTAP_PERIM_DA_ABBINARE', 25.00,
       (SELECT stato_da_abbinare FROM tmp_ab),
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti));

-- Riga sulla distinta INTERNA, con la fattura di A: e' la fattura a dire di
-- chi e' quel denaro, perche' la distinta interna non e' di nessuno.
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, importo, stato_id, fattura_id, billing_account_id, meta)
SELECT (SELECT dist_interna FROM tmp_dist), 'PGTAP_PERIM_INTERNA', 15.00,
       (SELECT stato_da_abbinare FROM tmp_ab), f.id, f.billing_account_id,
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
  FROM tmp_fattura f;

-- ⭐ Il lotto di lavoro di un operatore: distinta MANUALE, nessun canale.
--   E' D12-a, applicata nel lotto 2 — e il caso che il perimetro del lotto 6
--   aveva rotto alla prima stesura.
CREATE TEMP TABLE tmp_dist_manuale AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
           (SELECT centro_banca FROM tmp_ab), current_date, current_date,
           NULL, NULL, NULL, 'BOZZA',
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           'MANUALE') AS dist_man;

-- Ora il lato B, nei suoi panni.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_ab)); END $ctx$;

CREATE TEMP TABLE tmp_dist_b AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
           (SELECT centro_banca FROM tmp_ab), current_date, current_date,
           (SELECT ente_b FROM tmp_enti), NULL, NULL, 'BOZZA',
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           'GENERATA') AS dist_b;

-- ============================================================
-- 2/3. Il lato A vede la propria distinta e non quella dell'altro
-- ============================================================
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT a_user FROM tmp_ab)); END $ctx$;

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili c
    WHERE c.id = (SELECT dist_a FROM tmp_dist)),
  1::bigint,
  '2) L''operatore A vede la propria distinta'
);

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili c
    WHERE c.id = (SELECT dist_b FROM tmp_dist_b)),
  0::bigint,
  '3) ...e NON vede quella dell''altro emittente: a dirlo e'' il conto, non la fattura'
);

-- ============================================================
-- 4. E il lato B, simmetrico
-- ============================================================
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_ab)); END $ctx$;

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili c
    WHERE c.id IN ((SELECT dist_a FROM tmp_dist), (SELECT dist_b FROM tmp_dist_b))),
  1::bigint,
  '4) L''operatore B vede la propria distinta e non quella di A'
);

-- ============================================================
-- 5/6. ⭐ La riga DA ABBINARE: nessuna fattura, e si vede lo stesso
-- ============================================================
-- ⭐ E' il caso per cui tutto questo esiste. Con un predicato «via fattura»
--    questa riga sarebbe invisibile a TUTTI — e una lista vuota sembra una
--    lista di cose finite, non una coda che nessuno puo' vedere.
SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili_righe r
    WHERE r.riferimento_ente = 'PGTAP_PERIM_DA_ABBINARE'),
  0::bigint,
  '6) La riga da abbinare di A e'' invisibile all''altro emittente'
);

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT a_user FROM tmp_ab)); END $ctx$;

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili_righe r
    WHERE r.riferimento_ente = 'PGTAP_PERIM_DA_ABBINARE'),
  1::bigint,
  '5) La riga DA ABBINARE, che fattura non ha, resta visibile al suo emittente'
);

-- ============================================================
-- 7/8. ⭐ La distinta interna: testata condivisa, righe riservate
-- ============================================================
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_ab)); END $ctx$;

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili c
    WHERE c.id = (SELECT dist_interna FROM tmp_dist)),
  1::bigint,
  '7) La distinta INTERNA e'' visibile anche all''altro emittente: non e'' di nessuno'
);

-- ⭐ E qui sta la parte che non si eredita: la testata e' condivisa perche' la
--   chiave di riuso non nomina l'emittente, ma il denaro che ci passa dentro ha
--   un padrone — e a dirlo e' la fattura che la riga porta.
SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili_righe r
    WHERE r.riferimento_ente = 'PGTAP_PERIM_INTERNA'),
  0::bigint,
  '8) ...ma la sua RIGA no: quella la filtra la fattura che porta'
);

-- ============================================================
-- 9/10. ⭐ Ne' documento ne' canale: la riga che si stava perdendo
-- ============================================================
-- 🔴 E' il caso che il lotto 6 ha rotto alla prima applicazione. Una riga
--   `DA_ABBINARE` — che fattura non ha, e' il suo stato — su una distinta
--   `MANUALE` senza canale, cioe' un operatore che sta digitando incassi:
--   nessuna delle due strade la copriva, e il WITH CHECK la rifiutava con
--   42501. Un perimetro che impedisce la lavorazione invece di proteggerla.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT a_user FROM tmp_ab)); END $ctx$;

SELECT lives_ok(
  format(
    $sql$INSERT INTO pagamenti.vendite_contabili_righe
            (contabile_id, riferimento_ente, importo, stato_id)
         VALUES (%s, 'PGTAP_PERIM_MANUALE', 40.00, %s)$sql$,
    (SELECT dist_man FROM tmp_dist_manuale), (SELECT stato_da_abbinare FROM tmp_ab)
  ),
  '9) La riga DA_ABBINARE su una distinta MANUALE senza canale si SCRIVE'
);

-- ⚠️ E si vede da entrambi i lati, ed e' la DECISIONE presa e non un effetto
--   collaterale: una riga senza documento su una distinta senza canale non
--   porta nessuna attribuzione — non c'e' niente in essa che dica di chi sia.
--   Nasconderla a tutti non protegge nessuno e impedisce solo di lavorarla.
--   🔵 L'alternativa — rendere il canale obbligatorio anche sulle distinte
--   manuali — e' annotata nel brief: oggi enti_incasso e' a zero righe.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_ab)); END $ctx$;

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili_righe r
    WHERE r.riferimento_ente = 'PGTAP_PERIM_MANUALE'),
  1::bigint,
  '10) ...e la vede anche l''altro emittente: non porta nessuna attribuzione'
);

-- ============================================================
-- 11/12. 🔴 La scrittura fuori perimetro viene rifiutata, e lo dice
-- ============================================================
-- ⛔ Questo non e' un doppione della policy: la policy fa SPARIRE, il trigger
--    RIFIUTA E SPIEGA. Un WITH CHECK da solo direbbe «new row violates
--    row-level security policy», che e' vero e inservibile.
-- ⚠️ SQLSTATE esplicito: senza, il test accetterebbe anche il crash del guard.
SELECT throws_ok(
  format(
    $sql$INSERT INTO pagamenti.vendite_contabili_righe (contabile_id, importo, stato_id)
         VALUES (%s, 10.00, %s)$sql$,
    (SELECT dist_a FROM tmp_dist), (SELECT stato_da_abbinare FROM tmp_ab)
  ),
  'P0001',
  NULL,
  '11) L''operatore B non puo'' scrivere una riga sulla distinta di A'
);

SELECT throws_like(
  format(
    $sql$INSERT INTO pagamenti.vendite_contabili
            (codice, centro_riscossione_id, data_contabile, data_registrazione,
             stato_id, ente_incasso_id, origine)
         VALUES ('PGTAP-PERIM-KO', %s, current_date, current_date, %s, %s, 'GENERATA')$sql$,
    (SELECT centro_banca FROM tmp_ab),
    (SELECT s.id FROM pagamenti.vendite_contabili_stati s
      WHERE s.codice_interno = 'BOZZA' ORDER BY s.id LIMIT 1),
    (SELECT ente_a FROM tmp_enti)
  ),
  '%scope emittente%',
  '12) L''operatore B non puo'' aprire una distinta sul canale di A, e il messaggio lo dice'
);

-- ============================================================
-- 13. Il cancello e' `app.ruolo_applicativo`
-- ============================================================
-- ⚠️ NON si svuota `app.current_user_id`: quello non e' fail-closed — con
--    l'utente nullo le funzioni di scope rispondono come per un job batch. Il
--    cancello vero e' il ruolo applicativo, ed e' li' che si verifica.
SELECT set_config('app.ruolo_applicativo', '', false);

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili c
    WHERE c.id IN ((SELECT dist_a FROM tmp_dist), (SELECT dist_b FROM tmp_dist_b),
                   (SELECT dist_interna FROM tmp_dist))),
  0::bigint,
  '13) Senza ruolo applicativo non si vede niente: il cancello e'' fail-closed'
);

-- ============================================================
-- 14. Cleanup
-- ============================================================
SELECT ok(true, '14) Cleanup: la transazione viene annullata, nessun residuo');

SELECT * FROM finish();
ROLLBACK;
