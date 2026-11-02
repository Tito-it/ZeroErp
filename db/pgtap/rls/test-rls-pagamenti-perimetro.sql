-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il perimetro degli incassi — dal CONTO, non dalla fattura
--
-- Elenco test (plan 19):
--  1) Riferimenti minimi presenti: due emittenti, due operatori, una fattura
--  2) L'operatore A vede la propria distinta
--  3) ...e NON vede quella dell'altro emittente
--  4) L'operatore B vede la propria e non quella di A
--  5) ⭐ La riga DA ABBINARE, che fattura non ha, resta visibile al suo emittente
--  6) ...e invisibile all'altro
--  7) ⭐ La distinta INTERNA e' del suo emittente: B NON la vede (rev 2026-09-15, D3)
--  8) ⭐ ...e nemmeno la sua RIGA: la testata e' di A, e la fattura pure
--  9) ⭐ La riga DA_ABBINARE su una distinta MANUALE senza canale si SCRIVE
-- 10) ⭐ ...e A la VEDE dalla sola testata: ne' fattura ne' canale, ma l'emittente c'e' (rev 2026-09-15)
-- 11) ⭐ ...e B NON la vede: quella riga porta l'attribuzione della sua testata (rev 2026-09-15, D3)
-- 12) 🔴 L'operatore B non puo' scrivere una riga sulla distinta di A
-- 13) 🔴 L'operatore B non puo' aprire una distinta sul canale di A
-- 14) Senza ruolo applicativo non si vede niente: il cancello e' quello
-- 15) ⭐ La policy sui CANALI esiste, ed e' FOR ALL
-- 16) Creare un canale sul PROPRIO conto: PASSA — e' la prova che conta
-- 17) 🔴 Sul conto di un ALTRO emittente: rifiutato
-- 18) ...e l'altro emittente non lo vede
-- 19) Assert finale cleanup
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
--  - ⭐ **dal 2026-08-28 copre anche i CANALI** (test 15-18). `enti_incasso`
--    porta il conto su cui atterra il denaro — cioe' di chi sono i soldi prima
--    che esista una fattura — e fino a quel giorno non aveva row security:
--    l'elenco dei canali, IBAN compreso, sarebbe stato comune a tutti. ⭐ E il
--    test 16 e' quello che conta davvero: una policy che protegge e impedisce
--    di lavorare e' peggio del difetto che chiude;
--  - ⭐ presidiare i due casi che il perimetro dal conto esiste per servire: la
--    riga «da abbinare» (test 5), che con un predicato via fattura sarebbe
--    invisibile a TUTTI, e la distinta interna (test 7/8);
--  - 🔴 e presidiare il caso che il lotto 6 ha ROTTO alla prima applicazione
--    (test 9): la riga DA_ABBINARE sul lotto di lavoro di un operatore, cioe'
--    una distinta MANUALE senza canale (D12-a). Le prime due strade non la
--    coprivano e il WITH CHECK la rifiutava con 42501 — un perimetro che
--    impedisce la lavorazione invece di proteggerla. L'hanno segnalato due
--    pgTAP gia' verdi, e questo file non lo copriva: e' la ragione per cui i
--    test 9, 10 e 11 esistono. Correzione in avanti: changeSet 20260822-24.
--
--  ⭐ REV 2026-09-15 (brief distinta-numerata-sul-registro, D3): LA DISTINTA SA
--    DI CHI E'. Porta emittente_soggetto_ruolo_id (risolto in una sede sola:
--    dato, canale, operatore in sessione, o rifiuto) e la policy passa da
--    quella colonna (20260915-31); il ramo «senza canale = di tutti» e' sparito
--    dalla testata e dai satelliti (20260915-32). Cosi' i test 7, 8, 10 e 11
--    hanno CAMBIATO VERSO — non sono stati tolti: una distinta interna e' del
--    suo emittente come il lotto o l'atto da cui nasce, e le sue righe la
--    seguono per la sola testata, senza bisogno della fattura. Il perimetro
--    «dal conto» resta vero per costruzione: il canale deve essere
--    dell'emittente della riga (livello 1 della sede unica).
--
-- Piano: brief-db-posting-e-abbinamento-rata.md
--        §2.3 S3-4/S3-5 · Decisione: brief madre D5 · lotto 6
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (2026-09-12). Fino a quel giorno il
--   file pescava fra i dati ESISTENTI due emittenti con un operatore ciascuno,
--   una fattura del primo e una filiale bancaria: su un database ricostruito
--   dai changelog non c'e' niente di tutto questo, e le 18 asserzioni sul
--   perimetro degli incassi restavano collaudate solo su dbdev. Ora:
--     - due aziende con `dbops.fn_pgtap_crea_emittente_operatore()`, PRIMA di
--       aprire il contesto;
--     - un cliente di A con `dbops.fn_pgtap_crea_cliente_ba()` chiamata NEL
--       CONTESTO di A e senza terzo parametro: il legame BA -> emittente lo
--       scrive il trigger z90 verso l'emittente di chi agisce (rev 20260912-38
--       dell'helper: l'INSERT del BA non fa RETURNING, che sotto la RLS non
--       vedrebbe la riga non ancora mappata);
--     - la fattura di A, scritta da A come la scriverebbe l'applicazione;
--     - una banca vera (ruolo BANK_B: il guard delle filiali rifiuta il resto)
--       con la sua filiale, per i conti di incasso.
--   Il file resta sul runner APPLICATIVO: e' l'unico modo in cui queste policy
--   si possono esercitare (vedi sopra, il FORCE farebbe ricorsione).
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'B' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione, e qui non e'
--    una formalita' — senza, la RLS di questo lotto non viene esercitata.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'A')); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(19);

-- ============================================================
-- Fixture — due lati: A (l'emittente che ha una fattura) e B (l'altro)
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_rls_pagamenti_perimetro'::text AS test_scope;

-- La banca e la sua filiale: il soggetto-ruolo di una filiale DEVE essere una
-- banca (`trgfn_bank_guard_ruolo_bank_branches` pretende BANK_B).
CREATE TEMP TABLE tmp_banca AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('Banca pgTAP perimetro incassi'),
           'BANK_B'::character varying) AS banca_sr_id;

CREATE TEMP TABLE tmp_filiale AS
WITH b AS (
    INSERT INTO anagrafiche.bank_branches
        (soggetto_ruolo_id, bank_code, branch_code, name)
    SELECT banca_sr_id, 'PGTAP', 'PI' || banca_sr_id, 'Filiale pgTAP perimetro incassi'
      FROM tmp_banca
    RETURNING id
)
SELECT id AS bank_branch FROM b;

CREATE TEMP TABLE tmp_ab AS
SELECT (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'A')                          AS a_ef,
       (SELECT soggetto_ruolo_id    FROM _mondi WHERE lato = 'A')                          AS a_sr,
       (SELECT auth_user_id         FROM _mondi WHERE lato = 'A')                          AS a_user,
       (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'B')                          AS b_ef,
       (SELECT soggetto_ruolo_id    FROM _mondi WHERE lato = 'B')                          AS b_sr,
       (SELECT auth_user_id         FROM _mondi WHERE lato = 'B')                          AS b_user,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice = 'BANCA' ORDER BY c.id LIMIT 1)              AS centro_banca,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.is_fondo_fattura IS TRUE ORDER BY c.id LIMIT 1)      AS centro_fondo,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'DA_ABBINARE' ORDER BY s.id LIMIT 1)                     AS stato_da_abbinare,
       (SELECT bank_branch FROM tmp_filiale)                                               AS bank_branch;

-- Il cliente di A e la sua fattura, scritti nei panni di A: sotto la RLS di
-- vendite.fatture, «visibile» e «sua» sono la stessa cosa.
CREATE TEMP TABLE tmp_cliente AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('RLS perimetro incassi') c;

CREATE TEMP TABLE tmp_fattura AS
WITH f AS (
    INSERT INTO vendite.fatture
        (registro_id, emittente_soggetto_ruolo_id, billing_account_id, meta)
    SELECT script.fn_pgtap_registro_fattura(ab.a_sr), ab.a_sr, c.billing_account_id,
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
      FROM tmp_ab ab, tmp_cliente c
    RETURNING id, billing_account_id
)
SELECT id, billing_account_id FROM f;

SELECT ok(
  (SELECT a_ef IS NOT NULL AND b_ef IS NOT NULL AND a_ef <> b_ef
          AND a_user IS NOT NULL AND b_user IS NOT NULL AND a_user <> b_user
          AND centro_banca IS NOT NULL AND centro_fondo IS NOT NULL
          AND stato_da_abbinare IS NOT NULL AND bank_branch IS NOT NULL
     FROM tmp_ab)
  AND (SELECT count(*) = 1 FROM tmp_fattura),
  '1) Riferimenti costruiti: due emittenti distinti, due operatori, una fattura di A'
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

-- ⭐ Ogni canale si crea NEL CONTESTO DEL SUO PADRONE, come le distinte qui
--    sotto. ⚠️ Fino al 2026-08-28 i due si creavano in un INSERT solo, sotto un
--    contesto qualunque: `enti_incasso` non aveva row security e nessuno se ne
--    accorgeva. Con la policy del lotto 10 quell'INSERT verrebbe rifiutato —
--    ed e' giusto: nell'applicazione un canale lo crea chi ne e' padrone.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT a_user FROM tmp_ab)); END $ctx$;

CREATE TEMP TABLE tmp_ente_a AS
WITH ins AS (
  INSERT INTO pagamenti.enti_incasso
      (codice, descrizione, tipo, attivo, soggetto_ruolo_conto_bancario_id,
       centro_riscossione_id, meta)
  SELECT 'PGTAP_PERIM_A', 'canale pgtap perimetro', 'ALTRO', true,
         (SELECT legame_a FROM tmp_legami), ab.centro_banca,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ab ab
  RETURNING id
) SELECT id AS ente_a FROM ins;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_ab)); END $ctx$;

CREATE TEMP TABLE tmp_ente_b AS
WITH ins AS (
  INSERT INTO pagamenti.enti_incasso
      (codice, descrizione, tipo, attivo, soggetto_ruolo_conto_bancario_id,
       centro_riscossione_id, meta)
  SELECT 'PGTAP_PERIM_B', 'canale pgtap perimetro', 'ALTRO', true,
         (SELECT legame_b FROM tmp_legami), ab.centro_banca,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ab ab
  RETURNING id
) SELECT id AS ente_b FROM ins;

CREATE TEMP TABLE tmp_enti AS
SELECT (SELECT ente_a FROM tmp_ente_a) AS ente_a,
       (SELECT ente_b FROM tmp_ente_b) AS ente_b;

-- ⚠️ Si torna nei panni di A: da qui in poi il file lavora dal suo lato, e un
--    contesto lasciato su B farebbe fallire la creazione della distinta di A
--    con un messaggio che parla di un'altra cosa («canale inesistente»).
--    ⭐ E' la stessa ragione per cui il guard del canale meriterebbe di essere
--    SECURITY DEFINER: sotto RLS «non lo vedo» diventa «non esiste».
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT a_user FROM tmp_ab)); END $ctx$;

-- ⭐ Le distinte si creano NEL CONTESTO DEL LORO PADRONE: la policy e' FOR ALL,
--    e una distinta creata dall'operatore sbagliato verrebbe rifiutata dal
--    guard prima ancora che dalla policy.
CREATE TEMP TABLE tmp_dist AS
-- ⚠️ Argomenti NOMINALI: dal lotto 7 la funzione ha otto parametri e non nove
--    (p_compensazione_id e' sparito girando il verso del legame, D15-e). Una
--    chiamata posizionale sarebbe da riscrivere a ogni cambio di firma.
SELECT pagamenti.fn_get_or_create_vendite_contabile(
           p_centro_riscossione_id => (SELECT centro_banca FROM tmp_ab),
           p_data_contabile        => script.fn_data_operativa(),
           p_data_registrazione    => script.fn_data_operativa(),
           p_ente_incasso_id       => (SELECT ente_a FROM tmp_enti),
           p_codice_stato_interno  => 'BOZZA',
           p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           p_origine               => 'GENERATA') AS dist_a,
       pagamenti.fn_get_or_create_vendite_contabile(
           p_centro_riscossione_id => (SELECT centro_fondo FROM tmp_ab),
           p_data_contabile        => script.fn_data_operativa(),
           p_data_registrazione    => script.fn_data_operativa(),
           p_codice_stato_interno  => 'BOZZA',
           p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           p_origine               => 'GENERATA') AS dist_interna;

-- Riga «da abbinare» sulla distinta di A: nessuna fattura, ed e' il caso per
-- cui il perimetro dal conto esiste.
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, importo, stato_id, meta)
SELECT (SELECT dist_a FROM tmp_dist), 'PGTAP_PERIM_DA_ABBINARE', 25.00,
       (SELECT stato_da_abbinare FROM tmp_ab),
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti));

-- Riga sulla distinta INTERNA, con la fattura di A. ⭐ Rev 2026-09-15: la
-- distinta interna non e' piu' «di nessuno» — e' nata nei panni di A ed e' di
-- A (livello 3 della sede unica); la fattura e' la seconda strada, non l'unica.
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
           p_centro_riscossione_id => (SELECT centro_banca FROM tmp_ab),
           p_data_contabile        => script.fn_data_operativa(),
           p_data_registrazione    => script.fn_data_operativa(),
           p_codice_stato_interno  => 'BOZZA',
           p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           p_origine               => 'MANUALE') AS dist_man;

-- Ora il lato B, nei suoi panni.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_ab)); END $ctx$;

CREATE TEMP TABLE tmp_dist_b AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
           p_centro_riscossione_id => (SELECT centro_banca FROM tmp_ab),
           p_data_contabile        => script.fn_data_operativa(),
           p_data_registrazione    => script.fn_data_operativa(),
           p_ente_incasso_id       => (SELECT ente_b FROM tmp_enti),
           p_codice_stato_interno  => 'BOZZA',
           p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           p_origine               => 'GENERATA') AS dist_b;

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
-- 7/8. ⭐ La distinta interna: del suo emittente, testata e righe
-- ============================================================
-- ⭐ Rev 2026-09-15 (D3): fino a quel giorno la testata era «di nessuno» e
--   visibile a tutti (chiave di riuso senza emittente). Ora e' nata nei panni
--   di A e porta l'emittente di A in colonna: B non la vede, e la riga la
--   segue — per la testata, prima ancora che per la fattura.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_ab)); END $ctx$;

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili c
    WHERE c.id = (SELECT dist_interna FROM tmp_dist)),
  0::bigint,
  '7) La distinta INTERNA e'' del suo emittente: B non la vede (D3)'
);

-- Entrambe le strade della riga puntano ad A (testata e fattura): per B e'
-- invisibile due volte. Il verso «ne' documento ne' canale» e' il test 10/11.
SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili_righe r
    WHERE r.riferimento_ente = 'PGTAP_PERIM_INTERNA'),
  0::bigint,
  '8) ...e nemmeno la sua RIGA: la testata e'' di A, e la fattura pure'
);

-- ============================================================
-- 9/10/11. ⭐ Ne' documento ne' canale: la riga che si stava perdendo
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

-- ⭐ Rev 2026-09-15 (D3): fino a quel giorno questa riga «si vedeva da entrambi
--   i lati» perche' non portava nessuna attribuzione — ne' fattura ne' canale.
--   Ora la sua TESTATA sa di chi e' (l'operatore in sessione, livello 3 della
--   sede unica), e la riga la segue per la strada 1 della policy — la sola
--   testata, senza fattura. A la vede; B no. La lavorabilita' che il lotto 6
--   aveva rotto resta intera (test 9), senza il ramo «di tutti».
SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili_righe r
    WHERE r.riferimento_ente = 'PGTAP_PERIM_MANUALE'),
  1::bigint,
  '10) ...e A la VEDE dalla sola testata: ne'' fattura ne'' canale, ma l''emittente c''e'''
);

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_ab)); END $ctx$;

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili_righe r
    WHERE r.riferimento_ente = 'PGTAP_PERIM_MANUALE'),
  0::bigint,
  '11) ...e B NON la vede: porta l''attribuzione della sua testata (D3)'
);

-- ============================================================
-- 12/13. 🔴 La scrittura fuori perimetro viene rifiutata, e lo dice
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
  '12) L''operatore B non puo'' scrivere una riga sulla distinta di A'
);

SELECT throws_like(
  format(
    $sql$INSERT INTO pagamenti.vendite_contabili
            (codice, centro_riscossione_id, data_contabile, data_registrazione,
             stato_id, ente_incasso_id, origine)
         VALUES ('PGTAP-PERIM-KO', %s, script.fn_data_operativa(), script.fn_data_operativa(), %s, %s, 'GENERATA')$sql$,
    (SELECT centro_banca FROM tmp_ab),
    (SELECT s.id FROM pagamenti.vendite_contabili_stati s
      WHERE s.codice_interno = 'BOZZA' ORDER BY s.id LIMIT 1),
    (SELECT ente_a FROM tmp_enti)
  ),
  '%scope emittente%',
  '13) L''operatore B non puo'' aprire una distinta sul canale di A, e il messaggio lo dice'
);

-- ============================================================
-- 14. Il cancello e' `app.ruolo_applicativo`
-- ============================================================
-- Qui si verifica il cancello del RUOLO. (Dal changeSet 20261004-82 chiude
--    anche l'utente vuoto: le funzioni di scope rispondono false con l'utente
--    NULL — brief-db-esclusioni-implicite, Q-1. Prima quel caso era «job
--    batch, nessun filtro», ed e' per questo che il test non lo usava.)
SELECT set_config('app.ruolo_applicativo', '', false);

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili c
    WHERE c.id IN ((SELECT dist_a FROM tmp_dist), (SELECT dist_b FROM tmp_dist_b),
                   (SELECT dist_interna FROM tmp_dist))),
  0::bigint,
  '14) Senza ruolo applicativo non si vede niente: il cancello e'' fail-closed'
);

-- ============================================================
-- 15-18. ⭐ I CANALI DI INCASSO — il perimetro della configurazione
-- ============================================================
-- ⚠️ Si asserisce il comando oltre all'esistenza: una policy FOR SELECT con lo
--    stesso nome passerebbe un controllo di sola presenza e renderebbe la
--    tabella di scrittura impossibile.
SELECT is(
  (SELECT p.cmd FROM pg_policies p
    WHERE p.schemaname = 'pagamenti' AND p.tablename = 'enti_incasso'
      AND p.policyname = 'rls_enti_incasso_perimetro_incasso'),
  'ALL',
  '15) La policy sui canali esiste ed e'' FOR ALL, non FOR SELECT'
);

-- Il conto di incasso di ciascun lato: e' da li' che il canale prende il suo
-- padrone (D5).
CREATE TEMP TABLE tmp_conti AS
SELECT (SELECT min(src.id) FROM anagrafiche.soggetti_ruoli_conti_bancari src
         WHERE src.soggetto_ruolo_id = (SELECT a_sr FROM tmp_ab) AND src.uso = 'INCASSO') AS conto_a,
       (SELECT min(src.id) FROM anagrafiche.soggetti_ruoli_conti_bancari src
         WHERE src.soggetto_ruolo_id = (SELECT b_sr FROM tmp_ab) AND src.uso = 'INCASSO') AS conto_b;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT a_user FROM tmp_ab)); END $ctx$;

-- ⭐ 16) LA PROVA CHE CONTA: la policy non deve chiudere la scrittura.
SELECT CASE WHEN (SELECT conto_a FROM tmp_conti) IS NULL
       THEN skip('16) nessun conto di INCASSO sull''emittente A: caso non misurabile', 1)
       ELSE lives_ok(
         format(
           $sql$INSERT INTO pagamenti.enti_incasso
                   (codice, descrizione, tipo, attivo, centro_riscossione_id,
                    soggetto_ruolo_id, soggetto_ruolo_conto_bancario_id)
                VALUES ('PGTAP_CANALE_A', 'Canale di prova A', 'ALTRO', true, %s, %s, %s)$sql$,
           (SELECT centro_banca FROM tmp_ab), (SELECT a_sr FROM tmp_ab),
           (SELECT conto_a FROM tmp_conti)),
         '16) Creare un canale sul PROPRIO conto PASSA: la policy protegge senza impedire di lavorare')
       END;

-- 🔴 17) Sul conto di un altro emittente: rifiutato dalla WITH CHECK.
-- ⚠️ 42501 e' insufficient_privilege: e' cosi' che una policy rifiuta una
--    scrittura, e dichiararlo distingue il rifiuto dal crash di un guard.
SELECT CASE WHEN (SELECT conto_b FROM tmp_conti) IS NULL
       THEN skip('17) nessun conto di INCASSO sull''emittente B: caso non misurabile', 1)
       ELSE throws_ok(
         format(
           $sql$INSERT INTO pagamenti.enti_incasso
                   (codice, descrizione, tipo, attivo, centro_riscossione_id,
                    soggetto_ruolo_id, soggetto_ruolo_conto_bancario_id)
                VALUES ('PGTAP_CANALE_B', 'Canale di prova B', 'ALTRO', true, %s, %s, %s)$sql$,
           (SELECT centro_banca FROM tmp_ab), (SELECT a_sr FROM tmp_ab),
           (SELECT conto_b FROM tmp_conti)),
         '42501',
         NULL,
         '17) Un canale sul conto di un ALTRO emittente e'' rifiutato: il perimetro morde in scrittura')
       END;

-- 18) E in lettura l'altro emittente non lo vede.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_ab)); END $ctx$;

SELECT is(
  (SELECT count(*) FROM pagamenti.enti_incasso e WHERE e.codice = 'PGTAP_CANALE_A'),
  0::bigint,
  '18) Il canale di A e'' invisibile a B: l''elenco dei canali non e'' piu'' comune'
);

-- ============================================================
-- 19. Cleanup
-- ============================================================
SELECT ok(true, '19) Cleanup: la transazione viene annullata, nessun residuo');

SELECT * FROM finish();
ROLLBACK;
