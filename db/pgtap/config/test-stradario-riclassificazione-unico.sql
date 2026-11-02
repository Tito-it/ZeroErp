-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Caso A: cambio nome completo della via (stesso tracciato)
-- Verifica che l'update su config.stradario produca storico
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

-- =========================================================
-- 1) Stradario di riferimento
-- =========================================================
CREATE TEMP TABLE tmp_stradario_a AS
SELECT id, stradario_generale_id, comune_id, codice_postale_id, storicizza
FROM config.stradario
ORDER BY id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_stradario_a) = 1,
    'Esiste almeno un record in config.stradario'
);

-- =========================================================
-- 2) Toponomastica per creare nuova via
-- =========================================================
CREATE TEMP TABLE tmp_toponomastica_a AS
SELECT id
FROM config.toponomastica
ORDER BY id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_toponomastica_a) = 1,
    'Esiste almeno un record in config.toponomastica'
);

-- =========================================================
-- 3) Nuova voce stradario_generale (nuovo nome via)
-- =========================================================
WITH ins AS (
    INSERT INTO config.stradario_generale (
        toponomastica_id,
        descrizione,
        descrizione_breve
    )
    SELECT
        t.id,
        'VIA TEST CASO A ' || to_char(now(), 'YYYYMMDDHH24MISS'),
        'TEST A ' || to_char(now(), 'HH24MISS')
    FROM tmp_toponomastica_a t
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_stradario_generale_new
FROM ins;

SELECT ok(
    (SELECT count(*) FROM tmp_stradario_generale_new) = 1,
    'Inserita nuova via in config.stradario_generale'
);

-- =========================================================
-- 4) Abilito storicizza (se necessario)
-- =========================================================
UPDATE config.stradario
SET storicizza = TRUE
WHERE id = (SELECT id FROM tmp_stradario_a);

SELECT ok(
    to_regclass('storico.stradario') IS NOT NULL,
    'Tabella storico.stradario presente'
);

-- =========================================================
-- 5) Cambio nome via (update stradario_generale_id)
-- =========================================================
CREATE TEMP TABLE tmp_ts_a AS
SELECT now() AS ts_pre;

UPDATE config.stradario
SET stradario_generale_id = (SELECT id FROM tmp_stradario_generale_new)
WHERE id = (SELECT id FROM tmp_stradario_a);

SELECT is(
    (SELECT stradario_generale_id FROM config.stradario WHERE id = (SELECT id FROM tmp_stradario_a)),
    (SELECT id FROM tmp_stradario_generale_new),
    'Aggiornato stradario_generale_id per il caso A'
);

SELECT lives_ok(
    $$
    DO $proc$
    DECLARE
      v_stradario_id integer;
    BEGIN
      SELECT id INTO v_stradario_id FROM tmp_stradario_a;
      CALL maintenance.proc_bump_indirizzi_dettaglio(v_stradario_id);
    END;
    $proc$;
    $$,
    'Rinormalizzazione indirizzi_dettaglio tramite procedura'
);

WITH cp AS (
    SELECT id
    FROM config.codici_postali
    WHERE id <> (SELECT codice_postale_id FROM tmp_stradario_a)
    ORDER BY id
    LIMIT 1
),
ins AS (
    INSERT INTO config.stradario (comune_id, stradario_generale_id, codice_postale_id, storicizza)
    SELECT
        (SELECT comune_id FROM tmp_stradario_a),
        (SELECT stradario_generale_id FROM tmp_stradario_a),
        cp.id,
        false
    FROM cp
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_stradario_alt
FROM ins;

SELECT ok(
    NOT EXISTS (
        SELECT 1
        FROM anagrafiche.indirizzi_dettaglio idd
        WHERE idd.stradario_id = (SELECT id FROM tmp_stradario_a)
    )
    OR EXISTS (
        SELECT 1
        FROM anagrafiche.indirizzi_dettaglio idd
        WHERE idd.stradario_id = (SELECT id FROM tmp_stradario_a)
          AND idd.indirizzo_normalizzato IS NOT NULL
    ),
    'indirizzi_dettaglio coerenti (indirizzo_normalizzato valorizzato se presenti)'
);

SELECT ok(
    NOT EXISTS (
        SELECT 1
        FROM anagrafiche.indirizzi_dettaglio idd
        JOIN script.vw_indirizzo_completo ic
          ON ic.id_stradario = idd.stradario_id
        WHERE idd.stradario_id = (SELECT id FROM tmp_stradario_a)
          AND idd.via_norm IS DISTINCT FROM upper(trim(ic.tipo_toponimo || ' ' || ic.nome_strada))
    ),
    'via_norm coerente con vw_indirizzo_completo (se presenti civici)'
);

SELECT ok(
    NOT EXISTS (
        SELECT 1
        FROM anagrafiche.indirizzi_dettaglio idd
        JOIN script.vw_indirizzo_completo ic
          ON ic.id_stradario = idd.stradario_id
        WHERE idd.stradario_id = (SELECT id FROM tmp_stradario_a)
          AND idd.indirizzo_normalizzato IS DISTINCT FROM trim(both ' ' from (
              upper(trim(ic.tipo_toponimo || ' ' || ic.nome_strada))
              || CASE WHEN idd.civico_norm <> '' THEN ', ' || idd.civico_norm ELSE '' END
              || CASE WHEN idd.palazzina   IS NOT NULL AND idd.palazzina <> '' THEN ', Pal.' || idd.palazzina ELSE '' END
              || CASE WHEN idd.scala       IS NOT NULL AND idd.scala <> '' THEN ', Scala ' || idd.scala ELSE '' END
              || CASE WHEN idd.piano       IS NOT NULL AND idd.piano <> '' THEN ', Piano ' || idd.piano ELSE '' END
              || CASE WHEN idd.interno     IS NOT NULL AND idd.interno <> '' THEN ', Int.' || idd.interno ELSE '' END
          ))
    ),
    'indirizzo_normalizzato coerente con i campi normalizzati (se presenti civici)'
);

SELECT ok(
    NOT EXISTS (
        SELECT 1
        FROM anagrafiche.indirizzi_dettaglio idd
        JOIN script.vw_indirizzo_completo ic
          ON ic.id_stradario = idd.stradario_id
        WHERE idd.stradario_id = (SELECT id FROM tmp_stradario_a)
          AND idd.indirizzo_normalizzato IS DISTINCT FROM trim(both ' ' from (
              upper(trim(ic.tipo_toponimo || ' ' || ic.nome_strada))
              || CASE
                  WHEN idd.civico IS NOT NULL AND idd.civico <> 0 THEN
                    CASE
                      WHEN idd.estensione_civico IS NOT NULL AND idd.estensione_civico <> '' THEN
                        ', ' || upper(idd.civico::text || CASE WHEN left(idd.estensione_civico, 1) <> '/' THEN '/' || idd.estensione_civico ELSE idd.estensione_civico END)
                      ELSE
                        ', ' || upper(idd.civico::text)
                    END
                  ELSE
                    ', SNC'
                END
              || CASE WHEN idd.palazzina   IS NOT NULL AND idd.palazzina <> '' THEN ', Pal.' || idd.palazzina ELSE '' END
              || CASE WHEN idd.scala       IS NOT NULL AND idd.scala <> '' THEN ', Scala ' || idd.scala ELSE '' END
              || CASE WHEN idd.piano       IS NOT NULL AND idd.piano <> '' THEN ', Piano ' || idd.piano ELSE '' END
              || CASE WHEN idd.interno     IS NOT NULL AND idd.interno <> '' THEN ', Int.' || idd.interno ELSE '' END
          ))
    ),
    'indirizzo_normalizzato coerente con la logica di normalizzazione (se presenti civici)'
);

SELECT CASE
  WHEN EXISTS (
      SELECT 1
      FROM anagrafiche.indirizzi_dettaglio
      WHERE stradario_id = (SELECT id FROM tmp_stradario_a)
  )
  AND EXISTS (
      SELECT 1
      FROM tmp_stradario_alt
  )
  THEN throws_ok(
      $$
      UPDATE anagrafiche.indirizzi_dettaglio
      SET stradario_id = (SELECT id FROM tmp_stradario_alt LIMIT 1)
      WHERE id = (
          SELECT id
          FROM anagrafiche.indirizzi_dettaglio
          WHERE stradario_id = (SELECT id FROM tmp_stradario_a)
          ORDER BY id
          LIMIT 1
      );
      $$,
      NULL,
      NULL,
      'Guard attivo: cambio stradario_id senza manutenzione bloccato'
  )
  ELSE ok(true, 'Guard test skipped: nessun indirizzo o stradario alternativo')
END;

-- =========================================================
-- 6) Verifica storico: snapshot con vecchio stradario_generale_id
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
        FROM storico.stradario s
        WHERE s.stradario_id = (SELECT id FROM tmp_stradario_a)
          AND s.snapshot ->> 'stradario_generale_id' = (SELECT stradario_generale_id::text FROM tmp_stradario_a)
    ),
    'Storico stradario contiene snapshot con stradario_generale_id precedente'
);

-- =========================================================
-- 7) Verifica fn_get_snapshot_as_of
--    ⚠️ ts_pre e' now() (timestamptz) e si passa COM'E': dal 20260920-05
--    p_as_of e' timestamptz. Il vecchio `ts_pre::timestamp` spogliava
--    l'istante del fuso e la funzione lo rivestiva col TimeZone della
--    sessione — un giro che tornava solo se i due fusi coincidevano.
-- =========================================================
SELECT is(
    (
        script.fn_get_snapshot_as_of(
            'config',
            'stradario',
            (SELECT id::text FROM tmp_stradario_a),
            'stradario_id',
            (SELECT ts_pre FROM tmp_ts_a)
        ) ->> 'stradario_generale_id'
    ),
    (SELECT stradario_generale_id::text FROM tmp_stradario_a),
    'fn_get_snapshot_as_of: ritorna stradario_generale_id precedente'
);

-- =========================================================
-- Cleanup: ripristino e rimuovo la via di test
-- =========================================================
UPDATE config.stradario
SET stradario_generale_id = (SELECT stradario_generale_id FROM tmp_stradario_a),
    storicizza = (SELECT storicizza FROM tmp_stradario_a)
WHERE id = (SELECT id FROM tmp_stradario_a);

DELETE FROM config.stradario_generale
WHERE id = (SELECT id FROM tmp_stradario_generale_new);

DELETE FROM config.stradario
WHERE id IN (SELECT id FROM tmp_stradario_alt);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
