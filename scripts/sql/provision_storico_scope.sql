\set ON_ERROR_STOP on

-- ============================================================================
-- ZeroErp — Provisioning dello SCOPE CONGELATO sulle shadow di storico
-- ----------------------------------------------------------------------------
-- Brief: docs/it/dev/work-in-progress/brief-db-rls-storico-scope-congelato.md §4b
--
-- PERCHÉ ESISTE. Le shadow `storico.*` nascono dall'automazione, e su dev il job
-- pgAgent le crea come `postgres`: 68 su 121 (2026-09-11) non appartengono al
-- migratore. `ALTER TABLE` e `CREATE POLICY` li fa solo il proprietario, quindi i
-- changeSet (-27 arma, -29 converge, -31 backfill) le SALTANO con WARN nell'audit,
-- e il trigger -28 si FERMA (preCondition) finché una shadow è senza le colonne.
-- Questo script, da superuser, chiude il buco — e lo chiude PER SEMPRE:
--
--   1. riassegna al migratore la proprietà delle shadow che non sono sue, così
--      che da qui in avanti grant, colonne e policy convergano da Liquibase
--      (fn_grant_storico_shadows, fn_storico_arma_scope_tutte) senza un
--      passaggio da superuser a ogni volta;
--   2. arma tutte le shadow (colonne, indice, RLS e policy dove la mappa dice),
--      agendo COME il migratore (SET ROLE): la primitiva lavora solo dove è
--      proprietaria;
--   3. rifà il backfill delle versioni già scritte, se la funzione (-30) esiste
--      già — altrimenti lo fa il -31 al migrate.
--
-- ⚠️ Col modello dei ruoli di sistema (brief-db-ruoli-di-sistema) non serve piu'
--   di regola: pgAgent si collega come zeroerp_job e le procedure dei job sono
--   SECURITY DEFINER di zeroerp_owner, quindi le shadow nascono sue. Resta per
--   un database dove qualcuno abbia creato shadow da superuser — il -31 in
--   ci_apply lo segnala con un NOTICE che rimanda qui.
--
-- ⚠️ La riassegnazione NON cambia la semantica della RLS: il superuser bypassa
--   comunque, il migratore è già proprietario delle madri e delle altre 52
--   shadow. Toglie una disuniformità, non un privilegio.
--
-- Uso (come superuser, sul database bersaglio):
--   sudo -u postgres psql -X -d zeroerp \
--        -f scripts/sql/provision_storico_scope.sql
--   Il migratore e' zeroerp_owner, ruolo di sistema: non si passa (fino al
--   2026-10-15 era `-v migrator_role`, default `titodb`, che oggi ridarebbe le
--   shadow a un utente personale e romperebbe «un owner solo»).
--
-- Verifica: db/pgtap/storico/test-storico-scope-congelato-v1.sql
-- ============================================================================

\echo [ZeroErp] Provisioning scope congelato sulle shadow storico.*
\set migrator_role zeroerp_owner

-- ⚠️ Le variabili psql NON si interpolano dentro un blocco DO (è una stringa
--   dollar-quoted): il ruolo passa per un GUC di sessione. Trovato alla prima
--   corsa (2026-09-11): «errore di sintassi a o presso ":"».
SELECT set_config('zeroerp.migratore', :'migrator_role', false);

-- 1) Proprietà al migratore, dove non lo è già.
DO $own$
DECLARE
    v_migratore text := current_setting('zeroerp.migratore');
    r           record;
    v_n         int := 0;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = v_migratore) THEN
        RAISE EXCEPTION 'ruolo migratore % assente', v_migratore;
    END IF;
    FOR r IN
        SELECT c.oid::regclass AS sto, pg_get_userbyid(c.relowner) AS owner
          FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'storico' AND c.relkind IN ('r', 'p')
           AND pg_get_userbyid(c.relowner) <> v_migratore
         ORDER BY 1
    LOOP
        EXECUTE format('ALTER TABLE %s OWNER TO %I', r.sto, v_migratore);
        v_n := v_n + 1;
    END LOOP;
    RAISE NOTICE '[ZeroErp] shadow riassegnate a %: %', v_migratore, v_n;
END
$own$;

-- 2) Colonne, indice, RLS e policy — la stessa primitiva dei changeSet.
--    ⚠️ COME IL MIGRATORE, non come superuser: la primitiva agisce solo dove
--    «proprietario = chi esegue» (è la sua difesa contro le shadow altrui), e
--    dopo la riassegnazione il proprietario è il migratore. Alla prima corsa
--    (2026-09-11) da `postgres` le saltava TUTTE: saltate_owner 121.
SET ROLE :"migrator_role";
SELECT dbops.fn_storico_arma_scope_tutte(false) AS arma;

-- 3) Il backfill delle versioni già scritte — se la funzione c'è già. Nasce dal
--    changeSet -30, che nell'ordine viene DOPO il -28: se il migrate si è
--    fermato lì, qui non c'è ancora, e il backfill lo farà il -31 al migrate.
SELECT 'SELECT dbops.fn_storico_backfill_scope_tutte() AS backfill'
 WHERE to_regproc('dbops.fn_storico_backfill_scope_tutte') IS NOT NULL
\gexec
SELECT CASE WHEN to_regproc('dbops.fn_storico_backfill_scope_tutte') IS NULL
            THEN '[ZeroErp] backfill saltato: la funzione nasce dal changeSet -30, lo fara'' il -31 al migrate'
            ELSE '[ZeroErp] backfill eseguito' END AS nota_backfill;
RESET ROLE;

-- 4) Controllo finale — la STESSA domanda della preCondition del -28: shadow
--    di una madre col trigger di storico senza le due colonne. Deve essere 0.
SELECT count(*) AS shadow_senza_colonne_con_madre
  FROM pg_catalog.pg_class c
  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'storico' AND c.relkind = 'r'
   AND EXISTS (SELECT 1 FROM pg_catalog.pg_class mc
                 JOIN pg_catalog.pg_trigger t ON t.tgrelid = mc.oid AND NOT t.tgisinternal
                 JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
                WHERE mc.relname = c.relname AND p.proname = 'trgfn_storico_generic')
   AND (   NOT EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                        WHERE a.attrelid = c.oid AND a.attname = 'origine_schema' AND NOT a.attisdropped)
        OR NOT EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                        WHERE a.attrelid = c.oid AND a.attname = 'scope_emittente_fiscale_id' AND NOT a.attisdropped));

-- 5) Informativo: le shadow ORFANE, senza una madre col trigger. Nessun passo
--    le tocca (il marcatore è il trigger) e la -28 non le conta. Registrate nel
--    brief come debito: madre cancellata, rinominata, o storicizzazione tolta.
SELECT c.relname AS shadow_orfana, pg_get_userbyid(c.relowner) AS owner
  FROM pg_catalog.pg_class c
  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'storico' AND c.relkind = 'r'
   AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_class mc
                     JOIN pg_catalog.pg_trigger t ON t.tgrelid = mc.oid AND NOT t.tgisinternal
                     JOIN pg_catalog.pg_proc p ON p.oid = t.tgfoid
                    WHERE mc.relname = c.relname AND p.proname = 'trgfn_storico_generic')
 ORDER BY 1;

\echo [ZeroErp] Fatto. Se shadow_senza_colonne_con_madre e' 0, il changeSet 20260911-28 puo' passare.
