-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test F1-DB-T2 (parte 2/2): guard tipo_utenza / classe_utenza
-- su contratti_utilities (trgfn_contratti_utilities_guard_tipo_classe).
--
-- Nota: il trigger trgfn_contratti_snapshot_precontrattuali crea
-- automaticamente una riga in contratti_utilities al momento
-- dell'INSERT del contratto (se esistono precontrattuali). I test
-- cancellano lo snapshot automatico per poi tentare insert mirati.
--
-- Elenco test (1..7):
--   1) Precondizione: esiste BA + utility con dimensione
--   2) Utility con dimensione: tipo+classe coerenti -> ok
--   3) Utility con dimensione: entrambi NULL -> E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI
--   4) Precondizione: esiste un tipo_utenza diverso per test incoerenza
--   5) Utility con dimensione: classe NON coerente col tipo -> E_CONTRATTO_CLASSE_TIPO_INCOERENTE
--   6) Precondizione: esiste BA + utility senza dimensione
--   7) Utility senza dimensione: tipo/classe NOT NULL -> E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI
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

SELECT plan(7);

-- Precondizioni comuni
CREATE TEMP TABLE tmp_ctx_stato_draft AS
SELECT id AS stato_id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT';

-- BA su utility CON dimensione tipo/classe (per i test 2/3/4)
CREATE TEMP TABLE tmp_ctx_ba_with_dim AS
SELECT ba.id AS billing_account_id,
       ba.istanza_utility_id,
       ba.utility_id
  FROM anagrafiche.billing_account ba
 WHERE EXISTS (
     SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
 )
 ORDER BY ba.id
 LIMIT 1;

-- Classe/tipo coerenti per la utility del BA with_dim
CREATE TEMP TABLE tmp_ctx_tipo_classe_coerenti AS
SELECT cu.id AS classe_utenza_id, cu.tipo_utenza_id
  FROM config.classi_utenze cu
  JOIN config.tipi_utenze tu ON tu.id = cu.tipo_utenza_id
 WHERE tu.utility_id = (SELECT utility_id FROM tmp_ctx_ba_with_dim)
 ORDER BY cu.id
 LIMIT 1;

-- Tipo diverso per forzare l'incoerenza. Se nel DB esiste gia' un tipo
-- distinto lo riusiamo, altrimenti ne inseriamo uno di appoggio nella TX
-- (ROLLBACK lo pulisce a fine test).
INSERT INTO config.tipi_utenze(codice, descrizione, descrizione_breve, utility_id)
SELECT 'PGTAP_TIPO_DIVERSO', 'Tipo utenza di test pgTAP', 'PGTAP', utility_id
  FROM tmp_ctx_ba_with_dim
 WHERE NOT EXISTS (
     SELECT 1 FROM config.tipi_utenze tu
      WHERE tu.id <> (SELECT tipo_utenza_id FROM tmp_ctx_tipo_classe_coerenti)
 );

CREATE TEMP TABLE tmp_ctx_tipo_diverso AS
SELECT tu.id AS tipo_utenza_id
  FROM config.tipi_utenze tu
 WHERE tu.id <> (SELECT tipo_utenza_id FROM tmp_ctx_tipo_classe_coerenti)
 ORDER BY tu.id
 LIMIT 1;

-- BA su utility SENZA dimensione (per il test 6)
CREATE TEMP TABLE tmp_ctx_ba_no_dim AS
SELECT ba.id AS billing_account_id,
       ba.istanza_utility_id,
       ba.utility_id
  FROM anagrafiche.billing_account ba
 WHERE NOT EXISTS (
     SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
 )
 ORDER BY ba.id
 LIMIT 1;

-- 1) Precondizione utility CON dimensione
SELECT isnt(
    (SELECT COUNT(*)::int FROM tmp_ctx_ba_with_dim),
    0,
    '(precondizione) esiste BA su utility con dimensione tipo/classe'
);

-- Creo il contratto base per i test 2/3/4 su utility CON dimensione.
-- Il trigger di snapshot potrebbe creare automaticamente una riga in
-- contratti_utilities se esistono precontrattuali; la cancelliamo dopo
-- per avere uno slate pulito (UNIQUE contratto_id).
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
    valido_dal, valido_al
)
SELECT 'PGTAP_CONTR_UTIL_WD', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       sd.stato_id, '2055-01-01', '2055-12-31'
  FROM tmp_ctx_ba_with_dim ba, tmp_ctx_stato_draft sd;

DELETE FROM vendite.contratti_utilities
 WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_CONTR_UTIL_WD');

-- 2) Utility CON dimensione: tipo+classe coerenti
SELECT lives_ok(
    $$INSERT INTO vendite.contratti_utilities(
          contratto_id, istanza_utility_id, utility_id,
          tipo_utenza_id, classe_utenza_id)
      SELECT c.id, ba.istanza_utility_id, ba.utility_id,
             tc.tipo_utenza_id, tc.classe_utenza_id
        FROM vendite.contratti c
           , tmp_ctx_ba_with_dim ba
           , tmp_ctx_tipo_classe_coerenti tc
       WHERE c.numero = 'PGTAP_CONTR_UTIL_WD'$$,
    'Utility con dimensione + tipo/classe coerenti: insert ammesso'
);

-- Reset per il test successivo
DELETE FROM vendite.contratti_utilities
 WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_CONTR_UTIL_WD');

-- 3) Utility CON dimensione + entrambi NULL
SELECT throws_ok(
    $$INSERT INTO vendite.contratti_utilities(
          contratto_id, istanza_utility_id, utility_id,
          tipo_utenza_id, classe_utenza_id)
      SELECT c.id, ba.istanza_utility_id, ba.utility_id,
             NULL, NULL
        FROM vendite.contratti c, tmp_ctx_ba_with_dim ba
       WHERE c.numero = 'PGTAP_CONTR_UTIL_WD'$$,
    'P0001',
    NULL,
    'Utility con dimensione + tipo/classe NULL bloccato (E_CONTRATTO_UTILITY_TIPO_CLASSE_OBBLIGATORI)'
);

-- 4) Precondizione: esiste un tipo_utenza diverso da quello della classe usata.
-- Se fallisce, il test 5 non puo' esercitare il ramo "incoerenza".
SELECT isnt(
    (SELECT COUNT(*)::int FROM tmp_ctx_tipo_diverso),
    0,
    '(precondizione) esiste almeno un tipo_utenza diverso da quello della classe di test'
);

-- 5) Utility CON dimensione + classe su tipo diverso da quello dichiarato
SELECT throws_ok(
    $$INSERT INTO vendite.contratti_utilities(
          contratto_id, istanza_utility_id, utility_id,
          tipo_utenza_id, classe_utenza_id)
      SELECT c.id, ba.istanza_utility_id, ba.utility_id,
             td.tipo_utenza_id, tc.classe_utenza_id
        FROM vendite.contratti c
           , tmp_ctx_ba_with_dim ba
           , tmp_ctx_tipo_classe_coerenti tc
           , tmp_ctx_tipo_diverso td
       WHERE c.numero = 'PGTAP_CONTR_UTIL_WD'$$,
    'P0001',
    NULL,
    'Classe su tipo diverso bloccato (E_CONTRATTO_CLASSE_TIPO_INCOERENTE)'
);

-- 6) Precondizione utility SENZA dimensione
SELECT isnt(
    (SELECT COUNT(*)::int FROM tmp_ctx_ba_no_dim),
    0,
    '(precondizione) esiste BA su utility senza dimensione tipo/classe'
);

-- Creo il contratto base per il test 6 su utility SENZA dimensione
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
    valido_dal, valido_al
)
SELECT 'PGTAP_CONTR_UTIL_ND', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
       sd.stato_id, '2056-01-01', '2056-12-31'
  FROM tmp_ctx_ba_no_dim ba, tmp_ctx_stato_draft sd;

DELETE FROM vendite.contratti_utilities
 WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_CONTR_UTIL_ND');

-- 7) Utility SENZA dimensione + tipo/classe NOT NULL
SELECT throws_ok(
    $$INSERT INTO vendite.contratti_utilities(
          contratto_id, istanza_utility_id, utility_id,
          tipo_utenza_id, classe_utenza_id)
      SELECT c.id, ba.istanza_utility_id, ba.utility_id,
             tc.tipo_utenza_id, tc.classe_utenza_id
        FROM vendite.contratti c, tmp_ctx_ba_no_dim ba, tmp_ctx_tipo_classe_coerenti tc
       WHERE c.numero = 'PGTAP_CONTR_UTIL_ND'$$,
    'P0001',
    NULL,
    'Utility senza dimensione + tipo/classe NOT NULL bloccato (E_CONTRATTO_UTILITY_SENZA_DIMENSIONE_TIPO_CLASSE_VIETATI)'
);

SELECT * FROM finish();
ROLLBACK;
