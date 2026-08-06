-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test F1-DB-T1 (parte 2/2): matrice categorie_clienti_listini.
-- Copre i vincoli: CHECK variazione, CHECK coerenza, CHECK date,
-- EXCLUDE no-overlap (inclusi i casi con classe_utenza_id NULL).
--
-- Elenco test (1..10):
--   1) CHECK: tipo_variazione = 'PERCENTUALE' ammesso
--   2) CHECK: tipo_variazione = 'PREZZO_FISSO' vietato nella matrice
--   3) CHECK: tipo NOT NULL con valore NULL -> fallisce (coerenza)
--   4) daterange: valido_al < valido_dal -> costruttore daterange fallisce (22000)
--   5) EXCLUDE: due righe attive stessa quadrupla + classe specifica si sovrappongono -> fallisce
--   6) EXCLUDE: due righe attive stessa quadrupla con classe NULL si sovrappongono -> fallisce
--   7) EXCLUDE: fallback NULL e classe specifica NON si considerano overlap (quadruple diverse)
--   8) EXCLUDE: righe attivo=false non partecipano al vincolo
--   9) Trigger set_validita: validita' daterange viene popolato
--  10) Variazione assente: tipo NULL + valore NULL ammesso
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

-- Precondizioni: costruiamo un contesto di test isolato.
-- Serve una categoria, una utility, un soggetto_ruolo emittente, un listino attivo.

CREATE TEMP TABLE tmp_ctx_cat AS
SELECT id AS categoria_cliente_id
  FROM anagrafiche.categorie_clienti
 WHERE codice = 'SILVER'
 LIMIT 1;

CREATE TEMP TABLE tmp_ctx_utility AS
SELECT id AS utility_id
  FROM config.utilities
 ORDER BY id
 LIMIT 1;

CREATE TEMP TABLE tmp_ctx_emittente AS
SELECT soggetto_ruolo_id
  FROM anagrafiche.emittenti_fiscali
 WHERE attivo IS TRUE
 ORDER BY id
 LIMIT 1;

CREATE TEMP TABLE tmp_ctx_classe AS
SELECT id AS classe_utenza_id
  FROM config.classi_utenze
 ORDER BY id
 LIMIT 1;

CREATE TEMP TABLE tmp_ctx_listino AS
SELECT id AS listino_id
  FROM vendite.listini
 WHERE attivo IS TRUE
 ORDER BY id
 LIMIT 1;

-- 1) PERCENTUALE con valore ammesso
SELECT lives_ok(
    $$INSERT INTO anagrafiche.categorie_clienti_listini(
          categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
          classe_utenza_id, listino_id,
          tipo_variazione, valore_variazione,
          valido_dal, valido_al
      )
      SELECT c.categoria_cliente_id, u.utility_id, e.soggetto_ruolo_id,
             cu.classe_utenza_id, l.listino_id,
             'PERCENTUALE', -10,
             '2030-01-01', '2030-12-31'
        FROM tmp_ctx_cat c, tmp_ctx_utility u, tmp_ctx_emittente e,
             tmp_ctx_classe cu, tmp_ctx_listino l$$,
    'PERCENTUALE con valore negativo (sconto) inserito correttamente'
);

-- 2) PREZZO_FISSO vietato nella matrice (ammesso solo in promo)
SELECT throws_ok(
    $$INSERT INTO anagrafiche.categorie_clienti_listini(
          categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
          classe_utenza_id, listino_id,
          tipo_variazione, valore_variazione,
          valido_dal, valido_al
      )
      SELECT c.categoria_cliente_id, u.utility_id, e.soggetto_ruolo_id,
             cu.classe_utenza_id, l.listino_id,
             'PREZZO_FISSO', 42,
             '2031-01-01', '2031-12-31'
        FROM tmp_ctx_cat c, tmp_ctx_utility u, tmp_ctx_emittente e,
             tmp_ctx_classe cu, tmp_ctx_listino l$$,
    '23514',
    NULL,
    'PREZZO_FISSO vietato nella matrice (chk_categ_cli_listini_tipo_variazione)'
);

-- 3) coerenza: tipo NOT NULL con valore NULL
SELECT throws_ok(
    $$INSERT INTO anagrafiche.categorie_clienti_listini(
          categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
          classe_utenza_id, listino_id,
          tipo_variazione, valore_variazione,
          valido_dal, valido_al
      )
      SELECT c.categoria_cliente_id, u.utility_id, e.soggetto_ruolo_id,
             cu.classe_utenza_id, l.listino_id,
             'PERCENTUALE', NULL,
             '2032-01-01', '2032-12-31'
        FROM tmp_ctx_cat c, tmp_ctx_utility u, tmp_ctx_emittente e,
             tmp_ctx_classe cu, tmp_ctx_listino l$$,
    '23514',
    NULL,
    'tipo_variazione senza valore_variazione viola chk_categ_cli_listini_variazione_coerente'
);

-- 4) date invertite: il costruttore daterange nel trigger set_validita rifiuta
-- con SQLSTATE 22000 prima che qualsiasi CHECK di coerenza venga valutato.
SELECT throws_ok(
    $$INSERT INTO anagrafiche.categorie_clienti_listini(
          categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
          classe_utenza_id, listino_id,
          valido_dal, valido_al
      )
      SELECT c.categoria_cliente_id, u.utility_id, e.soggetto_ruolo_id,
             cu.classe_utenza_id, l.listino_id,
             '2040-06-01', '2040-01-01'
        FROM tmp_ctx_cat c, tmp_ctx_utility u, tmp_ctx_emittente e,
             tmp_ctx_classe cu, tmp_ctx_listino l$$,
    '22000',
    NULL,
    'valido_al < valido_dal: daterange(valido_dal, valido_al) fallisce con 22000'
);

-- 5) EXCLUDE: due righe attive stessa quadrupla con classe specifica si sovrappongono
SELECT throws_ok(
    $$INSERT INTO anagrafiche.categorie_clienti_listini(
          categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
          classe_utenza_id, listino_id,
          valido_dal, valido_al
      )
      SELECT c.categoria_cliente_id, u.utility_id, e.soggetto_ruolo_id,
             cu.classe_utenza_id, l.listino_id,
             '2030-06-01', '2030-12-31'
        FROM tmp_ctx_cat c, tmp_ctx_utility u, tmp_ctx_emittente e,
             tmp_ctx_classe cu, tmp_ctx_listino l$$,
    '23P01',
    NULL,
    'EXCLUDE blocca overlap su stessa quadrupla (classe specifica)'
);

-- 6) EXCLUDE anche con classe NULL: inseriamo prima NULL, poi secondo NULL sovrapposto
INSERT INTO anagrafiche.categorie_clienti_listini(
    categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
    classe_utenza_id, listino_id,
    valido_dal, valido_al
)
SELECT c.categoria_cliente_id, u.utility_id, e.soggetto_ruolo_id,
       NULL, l.listino_id,
       '2035-01-01', '2035-12-31'
  FROM tmp_ctx_cat c, tmp_ctx_utility u, tmp_ctx_emittente e, tmp_ctx_listino l;

SELECT throws_ok(
    $$INSERT INTO anagrafiche.categorie_clienti_listini(
          categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
          classe_utenza_id, listino_id,
          valido_dal, valido_al
      )
      SELECT c.categoria_cliente_id, u.utility_id, e.soggetto_ruolo_id,
             NULL, l.listino_id,
             '2035-06-01', '2036-06-30'
        FROM tmp_ctx_cat c, tmp_ctx_utility u, tmp_ctx_emittente e, tmp_ctx_listino l$$,
    '23P01',
    NULL,
    'EXCLUDE blocca overlap anche con classe_utenza_id NULL (stessa semantica fallback)'
);

-- 7) fallback NULL e classe specifica: quadruple diverse via COALESCE(-1) -> no overlap
SELECT lives_ok(
    $$INSERT INTO anagrafiche.categorie_clienti_listini(
          categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
          classe_utenza_id, listino_id,
          valido_dal, valido_al
      )
      SELECT c.categoria_cliente_id, u.utility_id, e.soggetto_ruolo_id,
             cu.classe_utenza_id, l.listino_id,
             '2035-03-01', '2035-09-30'
        FROM tmp_ctx_cat c, tmp_ctx_utility u, tmp_ctx_emittente e,
             tmp_ctx_classe cu, tmp_ctx_listino l$$,
    'Classe specifica e fallback NULL coesistono sullo stesso periodo (quadruple distinte)'
);

-- 8) righe attivo=false non partecipano al vincolo EXCLUDE
SELECT lives_ok(
    $$INSERT INTO anagrafiche.categorie_clienti_listini(
          categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
          classe_utenza_id, listino_id,
          valido_dal, valido_al, attivo
      )
      SELECT c.categoria_cliente_id, u.utility_id, e.soggetto_ruolo_id,
             cu.classe_utenza_id, l.listino_id,
             '2030-06-01', '2030-12-31', FALSE
        FROM tmp_ctx_cat c, tmp_ctx_utility u, tmp_ctx_emittente e,
             tmp_ctx_classe cu, tmp_ctx_listino l$$,
    'Riga con attivo=false non entra nell''EXCLUDE no-overlap'
);

-- 9) Trigger set_validita popola daterange.
-- Nota: il costruttore daterange('[]') normalizza automaticamente a '[)' con +1 giorno sul superiore.
SELECT is(
    (SELECT validita::text FROM anagrafiche.categorie_clienti_listini
      WHERE valido_dal = '2030-01-01' AND valido_al = '2030-12-31'
        AND tipo_variazione = 'PERCENTUALE' AND valore_variazione = -10
      LIMIT 1),
    '[2030-01-01,2031-01-01)',
    'Trigger set_validita sincronizza validita (daterange normalizzato [), +1gg su valido_al)'
);

-- 10) variazione assente (tipo NULL + valore NULL) ammessa
SELECT lives_ok(
    $$INSERT INTO anagrafiche.categorie_clienti_listini(
          categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id,
          classe_utenza_id, listino_id,
          valido_dal, valido_al
      )
      SELECT c.categoria_cliente_id, u.utility_id, e.soggetto_ruolo_id,
             cu.classe_utenza_id, l.listino_id,
             '2045-01-01', '2045-12-31'
        FROM tmp_ctx_cat c, tmp_ctx_utility u, tmp_ctx_emittente e,
             tmp_ctx_classe cu, tmp_ctx_listino l$$,
    'Variazione assente (tipo NULL + valore NULL) ammessa: usa prezzo base tal quale'
);

SELECT * FROM finish();
ROLLBACK;
