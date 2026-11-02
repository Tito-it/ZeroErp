-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c): la famiglia della distinta e' DISTINTA_INCASSO, e la sua tabella viene dalla sorgente (config.fn_sorgente_tabella).
-- pgTAP test per Zero ERP
-- Test: la distinta contabile prende il numero dal REGISTRO, e sa di chi e'
--       (brief-db-distinta-numerata-sul-registro, D1..D6 — L15)
--
-- Elenco test (plan 19):
--  1) ⛔ B NON e' l'emittente di default dell'installazione (il presidio anti-coincidenza)
--  2) La famiglia DISTINTA e' a catalogo com'e' dichiarata
--  3) Ogni emittente attivo ha un registro DISTINTA con l'anno nel numero
--  4) ⭐ Manuale CON canale di B: DIS-<sigla B>-<anno>-<7 cifre>, registro e anno scritti insieme
--  5) La seconda di B e' +1
--  6) ⭐ La prima di A e' 0000001 sul SUO registro: nessuna collisione con B
--  7) ⭐ data_contabile 31/12 e 2/1 -> due anni, e il secchio nuovo riparte da 1
--  8) ⭐ Senza canale, come B -> l'emittente e' B (livello 3: la riserva e' di chi agisce)
--  9) ⛔ Senza canale e senza emittente in sessione -> E_CONTABILE_EMITTENTE_OBBLIGATORIO
-- 10) ⛔ Emittente A + canale di B -> E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE
-- 11) Un codice fornito e' rispettato: registro_id e anno restano NULL
-- 12) ⭐ PRESIDIO SEDE UNICA: nessuna delle tre madri passa `codice` nell'INSERT
-- 13) ⭐ ...e il gemello «esiste»: le tre madri sono le UNICHE a inserire distinte
-- 14) La composizione si prova sui VALORI: DIS-ACME-2026-0000001
-- 15) ⛔ UPDATE che sposta una distinta di B sul canale di A -> rifiuto (livello 1)
-- 16) ⛔ La colonna e' NOT NULL: e' il vincolo che parla su un UPDATE a NULL
-- 17) ⛔ UPDATE … SET emittente = NULL -> rifiutato, il trigger NON ri-riempie dalla sessione
-- 18) ⭐ D3: l'operatore di A NON vede la distinta senza canale di B
-- 19) ⭐ ...e nemmeno le sue righe: il ramo «senza canale = di tutti» non esiste piu'
--
-- Scopo:
--  - collaudare il numeratore sul registro (D1/D2) e la sede unica di D4 dal
--    percorso REALE: gli INSERT diretti e la madre fn_get_or_create, come
--    utente applicativo, con la RLS attiva. Ogni caso si COSTRUISCE: due
--    aziende, i loro conti, i loro canali — niente viene pescato;
--  - ⛔ il test 1 esiste perche' il PRIMO emittente creato dall'helper e' il
--    default dell'installazione sullo scratch: lavorando da B — che non lo e'
--    mai — i test 6 e 10 non possono passare per coincidenza;
--  - ⭐ il test 12 e' il presidio della decisione D5: il no-op del numeratore
--    su un codice fornito serve alle fixture, NON alle madri. Perimetro =
--    l'elenco delle tre madri per nome, e il 13 e' il suo gemello «esiste»:
--    un quarto scrittore fa rosso, e si dichiara aggiungendolo all'elenco;
--  - i test 18/19 sono il verso di §3.3 del brief: cio' che oggi si vede
--    diversamente, ed e' voluto. Correzione e sistemazione NON stanno qui:
--    le loro fixture esistono gia' nei file delle madri e si asseriscono li'.
--
-- ⚠️ Nessun test sui trigger GENERATI dall'automazione (require_attivo sul
--    registro): nome hashato, e su dev arrivano coi job pgAgent. Sono
--    presidiati per famiglia da test-registri-per-emittente-v1.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ DUE aziende in DUE istruzioni, e il contesto sulla SECONDA: sullo scratch
--   la prima creata e' il DEFAULT dell'installazione (bootstrap), su dbdev lo e'
--   un'altra — B non lo e' mai (memoria «due aziende»).
CREATE TEMP TABLE _mondi AS SELECT 'A' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();
INSERT INTO _mondi              SELECT 'B',         * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione, da B.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'B')); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(19);

-- ============================================================
-- Fixture — il catalogo, la banca, i conti e i canali dei due lati
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_distinta_numerazione_registro'::text AS test_scope,
       extract(year FROM script.fn_data_operativa())::int         AS anno_corrente;

CREATE TEMP TABLE tmp_ab AS
SELECT (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'A') AS a_ef,
       (SELECT soggetto_ruolo_id    FROM _mondi WHERE lato = 'A') AS a_sr,
       (SELECT auth_user_id         FROM _mondi WHERE lato = 'A') AS a_user,
       (SELECT emittente_codice     FROM _mondi WHERE lato = 'A') AS a_sigla,
       (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'B') AS b_ef,
       (SELECT soggetto_ruolo_id    FROM _mondi WHERE lato = 'B') AS b_sr,
       (SELECT auth_user_id         FROM _mondi WHERE lato = 'B') AS b_user,
       (SELECT emittente_codice     FROM _mondi WHERE lato = 'B') AS b_sigla,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1) AS centro_banca,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'CASSA' ORDER BY c.id LIMIT 1) AS centro_cassa,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'BOZZA' ORDER BY s.id LIMIT 1)                    AS stato_bozza,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'DA_ABBINARE' ORDER BY s.id LIMIT 1)              AS stato_da_abbinare;

-- La banca e la sua filiale: il soggetto-ruolo di una filiale DEVE essere una
-- banca (`trgfn_bank_guard_ruolo_bank_branches` pretende BANK_B).
CREATE TEMP TABLE tmp_banca AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(
           dbops.fn_pgtap_crea_soggetto_pg('Banca pgTAP distinta numerazione'),
           'BANK_B'::character varying) AS banca_sr_id;

CREATE TEMP TABLE tmp_filiale AS
WITH b AS (
    INSERT INTO anagrafiche.bank_branches
        (soggetto_ruolo_id, bank_code, branch_code, name)
    SELECT banca_sr_id, 'PGTAP', 'DN' || banca_sr_id, 'Filiale pgTAP distinta numerazione'
      FROM tmp_banca
    RETURNING id
)
SELECT id AS bank_branch FROM b;

-- I due conti di incasso, uno per emittente. anagrafiche non ha row security.
CREATE TEMP TABLE tmp_legami AS
WITH conti AS (
  INSERT INTO anagrafiche.conti_bancari (iban, bank_branch_id, attivo, storicizza, meta)
  SELECT v.iban, f.bank_branch, true, false,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_filiale f
    CROSS JOIN (VALUES ('IT00PGTAPDISTINTANUMLATOA001', 'A'),
                       ('IT00PGTAPDISTINTANUMLATOB002', 'B')) AS v(iban, lato)
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

-- ⭐ Ogni canale si crea NEL CONTESTO DEL SUO PADRONE: enti_incasso ha la RLS.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT a_user FROM tmp_ab)); END $ctx$;

CREATE TEMP TABLE tmp_ente_a AS
WITH ins AS (
  INSERT INTO pagamenti.enti_incasso
      (codice, descrizione, tipo, attivo, soggetto_ruolo_conto_bancario_id,
       centro_riscossione_id, meta)
  SELECT 'PGTAP_DISNUM_A', 'canale pgtap distinta numerazione A', 'ALTRO', true,
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
  SELECT 'PGTAP_DISNUM_B', 'canale pgtap distinta numerazione B', 'ALTRO', true,
         (SELECT legame_b FROM tmp_legami), ab.centro_banca,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ab ab
  RETURNING id
) SELECT id AS ente_b FROM ins;

CREATE TEMP TABLE tmp_enti AS
SELECT (SELECT ente_a FROM tmp_ente_a) AS ente_a,
       (SELECT ente_b FROM tmp_ente_b) AS ente_b;

-- I registri DISTINTA dei due lati: li ha creati il trigger z90 alla nascita
-- degli emittenti (registri_fatturazione non ha RLS).
CREATE TEMP TABLE tmp_registri AS
SELECT (SELECT r.id FROM vendite.registri_fatturazione r
         WHERE r.famiglia_documento = 'DISTINTA_INCASSO'
           AND r.emittente_soggetto_ruolo_id = (SELECT a_sr FROM tmp_ab)) AS reg_a,
       (SELECT r.id FROM vendite.registri_fatturazione r
         WHERE r.famiglia_documento = 'DISTINTA_INCASSO'
           AND r.emittente_soggetto_ruolo_id = (SELECT b_sr FROM tmp_ab)) AS reg_b;

-- ============================================================
-- 1) ⛔ B non e' il default dell'installazione
-- ============================================================
-- ⚠️ Senza questo test, i casi «A parte da 1» e «canale di B» passerebbero
--   anche se la sede unica cadesse sul default invece che sul dato.
SELECT ok(
  NOT EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali_billing_account m
               WHERE m.is_default IS TRUE
                 AND m.emittente_soggetto_ruolo_id = (SELECT b_sr FROM tmp_ab))
  AND (SELECT a_ef <> b_ef AND a_user <> b_user AND centro_banca IS NOT NULL
          AND centro_cassa IS NOT NULL AND stato_bozza IS NOT NULL
          AND stato_da_abbinare IS NOT NULL FROM tmp_ab)
  AND (SELECT ente_a IS NOT NULL AND ente_b IS NOT NULL FROM tmp_enti),
  '1) B non e'' l''emittente di default dell''installazione, e la fixture e'' completa'
);

-- ============================================================
-- 2) La famiglia e' a catalogo com'e' dichiarata
-- ============================================================
SELECT is(
  (SELECT concat_ws('|', t.schema_tabella, t.nome_tabella, fd.colonna_numero,
                    COALESCE(fd.colonna_billing_account, '<null>'),
                    COALESCE(fd.colonna_serie, '<null>'),
                    fd.prefisso_default, fd.lunghezza_default,
                    fd.anno_nel_numero_default, fd.presidia_data_documento, fd.attivo)
     FROM vendite.famiglie_documento fd
     CROSS JOIN LATERAL config.fn_sorgente_tabella(fd.codice_interno) t
    WHERE fd.codice_interno = 'DISTINTA_INCASSO'),
  'pagamenti|vendite_contabili|codice|<null>|<null>|DIS-|7|t|f|t',
  '2) La famiglia DISTINTA: pagamenti.vendite_contabili/codice, senza BA ne'' serie, DIS-/7, anno nel numero, senza presidio di data'
);

-- ============================================================
-- 3) Ogni emittente attivo ha un registro DISTINTA con l'anno nel numero
-- ============================================================
-- ⭐ Conteggio DERIVATO, nessun nome: vale anche per gli emittenti che le
--   fixture creano (trigger z90) e per quelli del seed (20260915-34).
SELECT is(
  (SELECT count(*) FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE
      AND NOT EXISTS (SELECT 1 FROM vendite.registri_fatturazione r
                       WHERE r.famiglia_documento = 'DISTINTA_INCASSO'
                         AND r.emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id
                         AND r.attivo IS TRUE
                         AND r.anno_nel_numero IS TRUE)),
  0::bigint,
  '3) Ogni emittente attivo ha un registro DISTINTA attivo con l''anno nel numero'
);

-- ============================================================
-- 4) ⭐ Manuale CON canale di B: la forma, e le tre colonne insieme
-- ============================================================
CREATE TEMP TABLE tmp_dist_b1 AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
           p_centro_riscossione_id => (SELECT centro_banca FROM tmp_ab),
           p_data_contabile        => script.fn_data_operativa(),
           p_data_registrazione    => script.fn_data_operativa(),
           p_ente_incasso_id       => (SELECT ente_b FROM tmp_enti),
           p_codice_stato_interno  => 'BOZZA',
           p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           p_origine               => 'MANUALE') AS id;

SELECT is(
  (SELECT concat_ws('|',
              c.codice ~ ('^DIS-' || ab.b_sigla || '-\d{4}-\d{7}$'),
              c.emittente_soggetto_ruolo_id = ab.b_sr,
              c.registro_id = (SELECT reg_b FROM tmp_registri),
              c.anno = vendite.fn_get_anno_registro(c.data_contabile),
              right(c.codice, 7))
     FROM pagamenti.vendite_contabili c, tmp_ab ab
    WHERE c.id = (SELECT id FROM tmp_dist_b1)),
  't|t|t|t|0000001',
  '4) Con il canale di B: DIS-<sigla B>-<anno>-0000001, emittente B, sul registro di B, anno da data_contabile'
);

-- ============================================================
-- 5) La seconda di B e' +1
-- ============================================================
-- ⚠️ data_contabile DIVERSA nello stesso anno: cosi' la chiave di riuso non
--   ridà la testata di prima, e nasce davvero una seconda distinta.
CREATE TEMP TABLE tmp_dist_b2 AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
           p_centro_riscossione_id => (SELECT centro_banca FROM tmp_ab),
           p_data_contabile        => script.fn_data_operativa() - 1,
           p_data_registrazione    => script.fn_data_operativa(),
           p_ente_incasso_id       => (SELECT ente_b FROM tmp_enti),
           p_codice_stato_interno  => 'BOZZA',
           p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           p_origine               => 'MANUALE') AS id;

SELECT is(
  (SELECT right(c.codice, 7)::int FROM pagamenti.vendite_contabili c
    WHERE c.id = (SELECT id FROM tmp_dist_b2)),
  2,
  '5) La seconda distinta di B prende il progressivo 2'
);

-- ============================================================
-- 6) ⭐ La prima di A e' 0000001 sul SUO registro
-- ============================================================
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT a_user FROM tmp_ab)); END $ctx$;

CREATE TEMP TABLE tmp_dist_a1 AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
           p_centro_riscossione_id => (SELECT centro_banca FROM tmp_ab),
           p_data_contabile        => script.fn_data_operativa(),
           p_data_registrazione    => script.fn_data_operativa(),
           p_ente_incasso_id       => (SELECT ente_a FROM tmp_enti),
           p_codice_stato_interno  => 'BOZZA',
           p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           p_origine               => 'MANUALE') AS id;

SELECT is(
  (SELECT concat_ws('|',
              c.codice ~ ('^DIS-' || ab.a_sigla || '-\d{4}-0000001$'),
              c.registro_id = (SELECT reg_a FROM tmp_registri),
              c.registro_id <> (SELECT reg_b FROM tmp_registri))
     FROM pagamenti.vendite_contabili c, tmp_ab ab
    WHERE c.id = (SELECT id FROM tmp_dist_a1)),
  't|t|t',
  '6) La prima di A e'' 0000001 sul registro di A: due emittenti, due sezionali, nessuna collisione sulla stringa'
);

-- ============================================================
-- 7) ⭐ 31/12 e 2/1: due anni, e il secchio nuovo riparte da 1
-- ============================================================
-- Nel contesto di B, che ha gia' due numeri nell'anno corrente: il 31/12
-- dell'anno prima apre un secchio nuovo (1), il 2/1 continua quello corrente (3).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_ab)); END $ctx$;

CREATE TEMP TABLE tmp_dist_anni AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
           p_centro_riscossione_id => (SELECT centro_banca FROM tmp_ab),
           p_data_contabile        => make_date((SELECT anno_corrente FROM tmp_costanti) - 1, 12, 31),
           p_data_registrazione    => script.fn_data_operativa(),
           p_ente_incasso_id       => (SELECT ente_b FROM tmp_enti),
           p_codice_stato_interno  => 'BOZZA',
           p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           p_origine               => 'MANUALE') AS id_dicembre,
       pagamenti.fn_get_or_create_vendite_contabile(
           p_centro_riscossione_id => (SELECT centro_banca FROM tmp_ab),
           p_data_contabile        => make_date((SELECT anno_corrente FROM tmp_costanti), 1, 2),
           p_data_registrazione    => script.fn_data_operativa(),
           p_ente_incasso_id       => (SELECT ente_b FROM tmp_enti),
           p_codice_stato_interno  => 'BOZZA',
           p_meta                  => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti)),
           p_origine               => 'MANUALE') AS id_gennaio;

SELECT is(
  (SELECT concat_ws(' ',
              (SELECT c.anno || '/' || right(c.codice, 7)::int FROM pagamenti.vendite_contabili c
                WHERE c.id = (SELECT id_dicembre FROM tmp_dist_anni)),
              (SELECT c.anno || '/' || right(c.codice, 7)::int FROM pagamenti.vendite_contabili c
                WHERE c.id = (SELECT id_gennaio FROM tmp_dist_anni)))),
  (SELECT (anno_corrente - 1) || '/1 ' || anno_corrente || '/3' FROM tmp_costanti),
  '7) Il 31/12 apre il secchio dell''anno prima e riparte da 1; il 2/1 continua quello corrente'
);

-- ============================================================
-- 8) ⭐ Senza canale, come B: livello 3, la riserva e' di chi agisce
-- ============================================================
CREATE TEMP TABLE tmp_dist_b_cassa AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili
      (centro_riscossione_id, data_contabile, data_registrazione, stato_id, origine, meta)
  SELECT ab.centro_cassa, script.fn_data_operativa(), script.fn_data_operativa(), ab.stato_bozza, 'MANUALE',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ab ab
  RETURNING id, emittente_soggetto_ruolo_id, codice
) SELECT * FROM ins;

SELECT is(
  (SELECT emittente_soggetto_ruolo_id FROM tmp_dist_b_cassa),
  (SELECT b_sr FROM tmp_ab),
  '8) Senza canale, l''emittente e'' quello dell''operatore in sessione (livello 3)'
);

-- ============================================================
-- 9) ⛔ Senza canale e senza emittente in sessione: rifiuto parlante
-- ============================================================
-- ⭐ Arriva la NOSTRA frase e non E_SCOPE_SENZA_UTENTE ne' un 42501: i BEFORE
--   ROW scattano prima della WITH CHECK, e fra i BEFORE a10_emittente precede
--   a10_guard_emittente_scope — e' l'ordine alfabetico di L3 che qui si misura.
-- ⚠️ La GUC si svuota e si RIMETTE subito dopo: transazione unica.
SELECT set_config('app.current_user_id', '', true);

SELECT throws_like(
  format(
    $sql$INSERT INTO pagamenti.vendite_contabili
            (centro_riscossione_id, data_contabile, data_registrazione, stato_id, origine)
         VALUES (%s, script.fn_data_operativa(), script.fn_data_operativa(), %s, 'MANUALE')$sql$,
    (SELECT centro_cassa FROM tmp_ab), (SELECT stato_bozza FROM tmp_ab)),
  '%indicare l''emittente%',
  '9) Senza canale e senza emittente in sessione: E_CONTABILE_EMITTENTE_OBBLIGATORIO, con la frase per il form'
);

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT b_user FROM tmp_ab)); END $ctx$;

-- ============================================================
-- 10) ⛔ Emittente A + canale di B: dissenso
-- ============================================================
SELECT throws_like(
  format(
    $sql$INSERT INTO pagamenti.vendite_contabili
            (centro_riscossione_id, emittente_soggetto_ruolo_id, ente_incasso_id,
             data_contabile, data_registrazione, stato_id, origine)
         VALUES (%s, %s, %s, script.fn_data_operativa(), script.fn_data_operativa(), %s, 'MANUALE')$sql$,
    (SELECT centro_banca FROM tmp_ab), (SELECT a_sr FROM tmp_ab),
    (SELECT ente_b FROM tmp_enti), (SELECT stato_bozza FROM tmp_ab)),
  '%non di %',
  '10) Emittente A indicato con il canale di B: E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE'
);

-- ============================================================
-- 11) Un codice fornito e' rispettato
-- ============================================================
CREATE TEMP TABLE tmp_dist_ko AS
WITH ins AS (
  INSERT INTO pagamenti.vendite_contabili
      (codice, centro_riscossione_id, data_contabile, data_registrazione, stato_id, origine, meta)
  SELECT 'PGTAP-DIS-KO', ab.centro_cassa, script.fn_data_operativa(), script.fn_data_operativa(), ab.stato_bozza, 'MANUALE',
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_ab ab
  RETURNING id, codice, registro_id, anno, emittente_soggetto_ruolo_id
) SELECT * FROM ins;

SELECT is(
  (SELECT concat_ws('|', codice, registro_id IS NULL, anno IS NULL,
                    emittente_soggetto_ruolo_id = (SELECT b_sr FROM tmp_ab))
     FROM tmp_dist_ko),
  'PGTAP-DIS-KO|t|t|t',
  '11) Un codice fornito e'' rispettato (no-op del numeratore): registro e anno NULL, l''emittente si risolve lo stesso'
);

-- ============================================================
-- 12/13) ⭐ Il presidio della sede unica, e il suo gemello «esiste»
-- ============================================================
-- Perimetro = l'ELENCO delle tre madri, per nome (i presidi sul testo hanno
-- perimetro elenco). Un INSERT che porta `codice` fra le colonne e' una
-- seconda sede del numero.
CREATE TEMP TABLE tmp_madri AS
SELECT n.nspname || '.' || p.proname AS fn,
       p.prosrc ~ 'INSERT\s+INTO\s+pagamenti\.vendite_contabili\s*\('                          AS inserisce,
       p.prosrc ~ 'INSERT\s+INTO\s+pagamenti\.vendite_contabili\s*\(\s*[^)]*\mcodice\M'        AS passa_codice
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname IN ('pagamenti', 'vendite', 'script', 'dbops');

SELECT is(
  (SELECT COALESCE(string_agg(fn, ', ' ORDER BY fn), '')
     FROM tmp_madri
    WHERE fn IN ('pagamenti.fn_get_or_create_vendite_contabile',
                 'pagamenti.fn_conferma_sistemazione',
                 'pagamenti.fn_crea_distinta_correzione')
      AND passa_codice),
  '',
  '12) Nessuna delle tre madri passa `codice` nell''INSERT: il numero ha una sede sola (D5)'
);

SELECT is(
  (SELECT string_agg(fn, ', ' ORDER BY fn) FROM tmp_madri WHERE inserisce),
  'pagamenti.fn_conferma_sistemazione, pagamenti.fn_crea_distinta_correzione, pagamenti.fn_get_or_create_vendite_contabile',
  '13) Le tre madri sono le UNICHE funzioni che inseriscono distinte: un quarto scrittore fa rosso e si dichiara qui'
);

-- ============================================================
-- 14) La composizione si prova sui VALORI
-- ============================================================
SELECT is(
  vendite.fn_componi_numero_documento('DIS-', 'ACME-2026-', 1, 7, NULL),
  'DIS-ACME-2026-0000001',
  '14) La composizione: prefisso DIS-, corpo <sigla>-<anno>-, 7 cifre'
);

-- ============================================================
-- 15) ⛔ Spostare una distinta di B sul canale di A: rifiuto (livello 1 su UPDATE)
-- ============================================================
SELECT throws_like(
  format(
    $sql$UPDATE pagamenti.vendite_contabili SET ente_incasso_id = %s WHERE id = %s$sql$,
    (SELECT ente_a FROM tmp_enti), (SELECT id FROM tmp_dist_b1)),
  '%non di %',
  '15) Un UPDATE che sposta la distinta di B sul canale di A e'' rifiutato: il canale deve essere dell''emittente della riga'
);

-- ============================================================
-- 16/17) ⛔ L'emittente a NULL: il trigger NON ri-riempie, e qualcuno rifiuta
-- ============================================================
-- ⚠️ Chi rifiuta dipende da chi scrive: come applicazione la WITH CHECK della
--   policy scatta PRIMA del NOT NULL (fn_scope_ef_whitelist_via_sr con NULL e'
--   false: 42501), come proprietario parla il NOT NULL (23502). Un
--   throws_ok su un solo SQLSTATE sarebbe verde per un runner e rosso per
--   l'altro. ⇒ Il vincolo si asserisce sulla STRUTTURA (16), e la sostanza —
--   l'UPDATE non passa e la colonna non viene ri-riempita in silenzio dalla
--   sessione — si misura catturando i due soli esiti leciti (17).
SELECT col_not_null('pagamenti', 'vendite_contabili', 'emittente_soggetto_ruolo_id',
  '16) emittente_soggetto_ruolo_id e'' NOT NULL: e'' il vincolo che parla su un UPDATE a NULL');

DO $$
BEGIN
    UPDATE pagamenti.vendite_contabili
       SET emittente_soggetto_ruolo_id = NULL
     WHERE id = (SELECT id FROM tmp_dist_b1);
    PERFORM set_config('pgtap.emittente_null', 'PASSATO', true);
EXCEPTION
    WHEN not_null_violation OR insufficient_privilege THEN
        PERFORM set_config('pgtap.emittente_null', 'RIFIUTATO:' || SQLSTATE, true);
END $$;

SELECT matches(
  current_setting('pgtap.emittente_null', true),
  '^RIFIUTATO:(23502|42501)$',
  '17) UPDATE … SET emittente = NULL e'' rifiutato (NOT NULL o WITH CHECK): il trigger non ri-riempie dalla sessione'
);

-- ============================================================
-- 18/19) ⭐ D3: la distinta senza canale di B, e le sue righe, non si vedono da A
-- ============================================================
-- La riga, scritta da B: nessuna fattura, nessun canale — il caso che prima
-- cadeva nel ramo «di tutti».
INSERT INTO pagamenti.vendite_contabili_righe
    (contabile_id, riferimento_ente, importo, stato_id, meta)
SELECT (SELECT id FROM tmp_dist_b_cassa), 'PGTAP_DISNUM_RIGA_B', 12.00,
       (SELECT stato_da_abbinare FROM tmp_ab),
       jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti));

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT a_user FROM tmp_ab)); END $ctx$;

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili c
    WHERE c.id = (SELECT id FROM tmp_dist_b_cassa)),
  0::bigint,
  '18) L''operatore di A non vede la distinta senza canale di B: e'' del suo emittente, non di tutti'
);

SELECT is(
  (SELECT count(*) FROM pagamenti.vendite_contabili_righe r
    WHERE r.riferimento_ente = 'PGTAP_DISNUM_RIGA_B'),
  0::bigint,
  '19) ...e nemmeno la sua riga: il ramo «senza canale = di tutti» non esiste piu'''
);

SELECT * FROM finish();
ROLLBACK;
