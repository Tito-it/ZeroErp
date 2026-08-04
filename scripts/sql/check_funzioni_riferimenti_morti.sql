-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- Zero ERP — controllo diagnostico (NON e' un changeSet)
--
-- Funzioni plpgsql con riferimenti che non si risolvono piu'.
--
-- USO:
--   set -a; . db/internal.env; set +a
--   psql -X -q -f scripts/sql/check_funzioni_riferimenti_morti.sql \
--        -o /tmp/riferimenti-morti.txt
--
-- Richiede l'estensione `plpgsql_check` (changeSet 20260804-36, contesto
-- provision). Se manca, il file fallisce subito e in modo eloquente.
--
-- Brief: docs/it/dev/work-in-progress/brief-db-bonifica-riferimenti-morti.md
--
-- v1 (2026-08-04) produsse 60 righe, di cui ~33 falsi positivi di DUE
-- tipi soli. La v2 li classifica invece di nasconderli: nessuna riga
-- sparisce, ognuna esce con la sua etichetta.
--
--   1) TRIGGER MULTI-TABELLA — la v1 validava una trigger function
--      contro UN SOLO trigger (il primo). Una funzione generica scritta
--      per tre tabelle veniva quindi controllata contro una sola, e i
--      rami delle altre due risultavano «errori».
--      ⚠️ Rimedio: si valida contro OGNI tabella su cui e' agganciata, e
--      l'errore vale solo se compare per TUTTE. Se compare per alcune e
--      non per altre, e' un ramo dedicato a un'altra tabella — cioe' il
--      comportamento voluto, non un difetto.
--
--   2) VARIADIC — `script.fn_log_and_raise_error(..., VARIADIC text[])`
--      ammette di omettere del tutto i valori variadici; plpgsql_check
--      non lo sa e segnala «la funzione non esiste».
--      ⚠️ Ma NON tutte queste righe sono false: se fra gli argomenti c'e'
--      un `bigint`, un `integer` o un `text[]`, il cast implicito a
--      `text` non esiste e la chiamata fallisce DAVVERO a runtime — il
--      guard solleva un errore incomprensibile invece del messaggio di
--      dominio. Si distingue guardando i TIPI: se sono tutti
--      testo-compatibili e' rumore, se ce n'e' uno che non lo e' e' un
--      difetto vero.
--      Il riconoscimento usa lo SQLSTATE 42883 (undefined_function), non
--      il testo del messaggio: cosi' non dipende dalla lingua del server.
--
--   3) TRANSITION TABLE — `REFERENCING NEW TABLE AS new_rows` crea una
--      relazione che esiste SOLO durante lo scatto del trigger. Il nome
--      non si indovina: si legge da `pg_trigger.tgnewtable/tgoldtable`.
--
--   4) SQL DINAMICO — un errore di sintassi dentro un `EXECUTE` e' quasi
--      sempre un segnaposto non ancora sostituito, non codice rotto.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION pg_temp.misura_funzioni_rotte()
RETURNS TABLE(classe text, schema_nome text, funzione text, argomenti text, esito text)
LANGUAGE plpgsql AS $misura$
DECLARE
  r          record;
  rel        record;
  m          text;
  v_relazioni int;
  v_tipi     text[];
BEGIN
  CREATE TEMP TABLE IF NOT EXISTS tmp_raw(
    nsp text, pro text, args text, relid oid, msg text
  ) ON COMMIT DROP;
  DELETE FROM tmp_raw;

  FOR r IN
    SELECT p.oid                                     AS oid,
           n.nspname::text                           AS nsp,
           p.proname::text                           AS pro,
           pg_get_function_identity_arguments(p.oid) AS args,
           (p.prorettype = 'trigger'::regtype)       AS is_trg
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid = p.pronamespace
      JOIN pg_language  l ON l.oid = p.prolang
     WHERE l.lanname = 'plpgsql'
       AND n.nspname NOT IN ('pg_catalog', 'information_schema')
       AND n.nspname NOT LIKE 'pg\_%'
       -- fuori tutto cio' che appartiene a un'estensione: non e' codice
       -- che manteniamo noi (PostGIS, topology, pgagent).
       AND NOT EXISTS (SELECT 1 FROM pg_depend d
                        WHERE d.objid = p.oid AND d.deptype = 'e')
     ORDER BY n.nspname, p.proname
  LOOP
    IF r.is_trg THEN
      -- Trigger function: si valida contro OGNI tabella su cui e'
      -- agganciata. Zero tabelle = orfana, e non e' validabile.
      v_relazioni := 0;
      FOR rel IN
        SELECT DISTINCT tg.tgrelid
          FROM pg_trigger tg
         WHERE tg.tgfoid = r.oid AND NOT tg.tgisinternal
      LOOP
        v_relazioni := v_relazioni + 1;
        BEGIN
          FOR m IN SELECT c FROM plpgsql_check_function(
                     r.oid::regprocedure, relid => rel.tgrelid::regclass,
                     fatal_errors => false) AS c
          LOOP
            IF m LIKE 'error:%' THEN
              INSERT INTO tmp_raw VALUES (r.nsp, r.pro, r.args, rel.tgrelid, m);
            END IF;
          END LOOP;
        EXCEPTION WHEN OTHERS THEN
          INSERT INTO tmp_raw VALUES (r.nsp, r.pro, r.args, rel.tgrelid,
                                      'error:CHECK-KO:' || SQLERRM);
        END;
      END LOOP;

      IF v_relazioni = 0 THEN
        classe := 'ORFANA'; schema_nome := r.nsp; funzione := r.pro;
        argomenti := r.args;
        esito := 'trigger function senza alcun trigger agganciato: non validabile, e gia'' di per se'' un residuo';
        RETURN NEXT;
      END IF;

    ELSE
      BEGIN
        FOR m IN SELECT c FROM plpgsql_check_function(
                   r.oid::regprocedure, fatal_errors => false) AS c
        LOOP
          IF m LIKE 'error:%' THEN
            INSERT INTO tmp_raw VALUES (r.nsp, r.pro, r.args, NULL, m);
          END IF;
        END LOOP;
      EXCEPTION WHEN OTHERS THEN
        INSERT INTO tmp_raw VALUES (r.nsp, r.pro, r.args, NULL,
                                    'error:CHECK-KO:' || SQLERRM);
      END;
    END IF;
  END LOOP;

  -- ── Classificazione ──────────────────────────────────────────────
  FOR r IN
    SELECT t.nsp, t.pro, t.args, t.msg,
           count(*)                                   AS visto_su,
           (SELECT count(DISTINCT tg.tgrelid)
              FROM pg_trigger tg
              JOIN pg_proc p2 ON p2.oid = tg.tgfoid
              JOIN pg_namespace n2 ON n2.oid = p2.pronamespace
             WHERE n2.nspname = t.nsp AND p2.proname = t.pro
               AND NOT tg.tgisinternal)                AS tabelle_totali
      FROM tmp_raw t
     GROUP BY t.nsp, t.pro, t.args, t.msg
     ORDER BY t.nsp, t.pro, t.msg
  LOOP
    schema_nome := r.nsp; funzione := r.pro; argomenti := r.args; esito := r.msg;

    -- (1) Errore visto solo su ALCUNE delle tabelle del trigger: e' il
    --     ramo dedicato a un'altra tabella, non un difetto.
    IF r.tabelle_totali > 1 AND r.visto_su < r.tabelle_totali THEN
      classe := 'FP_RAMO_ALTRA_TABELLA';

    -- (1-bis) «relazione X non esiste» dove X e' una TRANSITION TABLE
    --     dichiarata nel CREATE TRIGGER (`REFERENCING NEW TABLE AS ...`).
    --     Esiste solo durante lo scatto del trigger, plpgsql_check non la
    --     vede. Il nome non si indovina: si legge da pg_trigger, che lo
    --     conserva in tgnewtable/tgoldtable.
    ELSIF r.msg ~ '^error:42P01:' AND EXISTS (
            SELECT 1
              FROM pg_trigger tg
              JOIN pg_proc p3      ON p3.oid = tg.tgfoid
              JOIN pg_namespace n3 ON n3.oid = p3.pronamespace
             WHERE n3.nspname = r.nsp AND p3.proname = r.pro
               AND NOT tg.tgisinternal
               AND substring(r.msg from '"([^"]+)"')
                   IN (tg.tgnewtable::text, tg.tgoldtable::text))
    THEN
      classe := 'FP_TRANSITION_TABLE';

    -- (1-ter) Errore di SINTASSI dentro un EXECUTE: e' SQL costruito a
    --     runtime, con dentro segnaposto che non sono SQL valido finche'
    --     non vengono sostituiti. plpgsql_check prova a interpretarlo
    --     comunque.
    ELSIF r.msg ~ '^error:42601:' AND r.msg LIKE '%:EXECUTE:%' THEN
      classe := 'FP_SQL_DINAMICO';

    -- (2) «funzione non esiste» (SQLSTATE 42883): falso positivo SOLO se
    --     tutti i tipi passati sono testo-compatibili — allora e' la
    --     variadic che plpgsql_check non sa risolvere. Se c'e' un tipo
    --     non testuale, il cast non esiste e la chiamata fallisce davvero.
    ELSIF r.msg ~ '^error:42883:' AND r.msg LIKE '%(%)%' THEN
      v_tipi := string_to_array(
                  btrim(substring(r.msg from '\(([^)]*)\)')), ', ');
      IF NOT EXISTS (
           SELECT 1 FROM unnest(v_tipi) AS x(t)
            WHERE btrim(x.t) NOT IN ('unknown','text','name','jsonb','uuid',
                                     'character varying','"unknown"'))
      THEN
        classe := 'FP_VARIADIC';
      ELSE
        classe := 'REALE';
      END IF;

    ELSE
      classe := 'REALE';
    END IF;

    RETURN NEXT;
  END LOOP;
END
$misura$;

\pset pager off

-- ⚠️ Si materializza UNA VOLTA: la funzione valida ~500 funzioni una per
-- una, interrogarla tre volte triplicherebbe il lavoro per niente.
CREATE TEMP TABLE misura AS SELECT * FROM pg_temp.misura_funzioni_rotte();

-- 1) Il conto per classe: la scala del problema, senza rumore.
SELECT classe, count(*) AS righe, count(DISTINCT schema_nome||'.'||funzione) AS funzioni
  FROM misura GROUP BY classe ORDER BY 1;

-- 2) SOLO i difetti veri, che sono la lista di lavoro.
SELECT schema_nome, funzione, argomenti, esito
  FROM misura WHERE classe IN ('REALE', 'ORFANA')
 ORDER BY classe, schema_nome, funzione;

-- 3) I falsi positivi, per controllarli a campione invece di fidarsi
--    della classificazione.
SELECT classe, schema_nome, funzione, esito
  FROM misura WHERE classe LIKE 'FP\_%'
 ORDER BY classe, schema_nome, funzione;
