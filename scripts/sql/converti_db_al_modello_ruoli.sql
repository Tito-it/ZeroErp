\set ON_ERROR_STOP on
-- ============================================================================
-- ZeroErp — Conversione di un database ESISTENTE al modello dei ruoli di sistema
-- ----------------------------------------------------------------------------
-- Brief: docs/it/dev/work-done/brief-db-ruoli-di-sistema.md §6 (fase 3),
--        §7 D-1, §16
--
-- Per un database nato prima del modello, i cui oggetti sono di un utente
-- personale (su dbdev: `titodb`). Un database nuovo non ne ha bisogno: lo fa
-- nascere giusto scripts/sql/provision_zeroerp.sql.
--
-- Che cosa fa, in UNA transazione (o tutto o niente):
--   1. fase ruoli di provision_zeroerp.sql: i ruoli di sistema e la loro
--      postura, il database a zeroerp_owner, CONNECT a zeroerp_job e zeroerp_app;
--   2. REASSIGN OWNED dell'utente personale a zeroerp_owner;
--      ⚠️ REASSIGN OWNED prende anche gli oggetti CONDIVISI: gli ALTRI database
--      dell'utente (su dbdev `zeroerp_b2_test`) gli vengono restituiti;
--   3. i privilegi di default dell'utente personale ricopiati PER zeroerp_owner
--      (stessi destinatari, stessi diritti): gli oggetti nuovi nascono di
--      zeroerp_owner, e senza la copia zeroerp_app non li vedrebbe;
--   4. l'utente personale diventa MEMBRO di zeroerp_owner e ogni sua sessione su
--      questo database lavora come proprietario (`SET role`): D-1, «chi
--      personalizza aggiunge». Senza il `SET role` un oggetto creato da una sua
--      sessione nascerebbe suo e «un owner solo» si romperebbe al primo changeSet;
--   5. fasi pre e post di provision_zeroerp.sql: pgagent, EXECUTE di zeroerp_job
--      sulle procedure dei job, e la VERIFICA «un owner solo»;
--   6. la verifica che l'utente personale non possieda piu' niente qui.
--
-- Che cosa NON fa (fuori dal database, a mano, vedi brief §16):
--   * il demone pgAgent come zeroerp_job (unita' systemd e .pgpass);
--   * nessuna password: i ruoli di sistema devono gia' esistere (sono di
--     CLUSTER: su dbdev li ha creati lo scratch zeroerp_ruoli). Se manca un
--     ruolo, la fase ruoli si ferma (D-3);
--   * non tocca i vecchi privilegi di default DELL'utente personale: non crea
--     piu' niente a nome suo, e si ritirano con la fase 4.
--
-- Uso, da SUPERUSER, sul database da convertire, A PGAGENT FERMO e senza
-- sessioni dell'applicazione (prende un lock esclusivo su ogni tabella):
--   psql -d zeroerp -v utente_personale=titodb \
--        -f scripts/sql/converti_db_al_modello_ruoli.sql
-- Prova a vuoto (fa tutto, verifica tutto, poi ROLLBACK):
--   … -v solo_prova=1
--
-- ⚠️ I lock: REASSIGN OWNED blocca ogni relazione che passa di mano (con indici e
--   TOAST), tutte nella stessa transazione: sulla struttura di dbdev sono 4036
--   lock (misurato il 2026-10-15). La tabella dei lock e' dimensionata su
--   max_locks_per_transaction × (max_connections + max_prepared_transactions)
--   — su dbdev 64 × 50 = 3200 — e per quanto si e' visto il margine di memoria
--   condivisa la fa bastare, ma a cluster carico puo' non bastare piu'. Se la
--   conversione si ferma con «out of shared memory», si alza
--   max_locks_per_transaction (vuole un riavvio) e si rilancia: la transazione
--   e' annullata, non resta niente a meta'.
-- ============================================================================

-- ⛔ Ogni fermo e' un ERRORE VERO: `\quit 1` esce con 0.
\if :{?utente_personale}
\else
DO $$ BEGIN RAISE EXCEPTION 'manca -v utente_personale=<il proprietario di oggi>'; END $$;
\endif

SELECT rolsuper AS sono_superuser FROM pg_roles WHERE rolname = current_user \gset
\if :sono_superuser
\else
DO $$ BEGIN RAISE EXCEPTION 'la conversione gira da superuser'; END $$;
\endif

SELECT current_database() AS db_name \gset
SELECT set_config('zeroerp.conv_utente', :'utente_personale', false) \gset _x_

DO $controlli$
DECLARE
    v_utente text := current_setting('zeroerp.conv_utente');
BEGIN
    IF current_database() IN ('postgres', 'template0', 'template1') THEN
        RAISE EXCEPTION 'si lancia sul database da convertire, non su %', current_database();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = v_utente) THEN
        RAISE EXCEPTION 'l''utente personale % non esiste', v_utente;
    END IF;
    IF v_utente IN ('zeroerp_owner', 'zeroerp_job', 'zeroerp_app', 'zeroerp_log') THEN
        RAISE EXCEPTION '% e'' un ruolo di sistema, non un utente personale', v_utente;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = v_utente AND rolsuper) THEN
        RAISE EXCEPTION 'l''utente personale % e'' superuser: REASSIGN OWNED prenderebbe oggetti di sistema', v_utente;
    END IF;
    -- ⛔ Il demone pgAgent non deve girare durante la conversione: tiene aperta
    --   una sessione e i suoi job farebbero DDL a meta' strada.
    IF EXISTS (SELECT 1 FROM pg_stat_activity
                WHERE datname = current_database() AND pid <> pg_backend_pid()
                  AND query ~* 'pgagent\.') THEN
        RAISE EXCEPTION 'c''e'' una sessione che lavora su pgagent: fermare il demone prima (systemctl stop pgagent)';
    END IF;
END
$controlli$;

BEGIN;

-- ── 1. I ruoli di sistema e il database ─────────────────────────────────────
\set fase ruoli
\ir provision_zeroerp.sql

-- ── 2. La proprieta' ────────────────────────────────────────────────────────
-- Gli ALTRI database dell'utente, prima che REASSIGN OWNED li prenda.
CREATE TEMP TABLE conv_altri_db ON COMMIT DROP AS
SELECT datname FROM pg_database
 WHERE datdba = (SELECT oid FROM pg_roles WHERE rolname = :'utente_personale')
   AND datname <> current_database();

\echo [ZeroErp] conversione: REASSIGN OWNED BY :utente_personale TO zeroerp_owner
SELECT format('REASSIGN OWNED BY %I TO zeroerp_owner', :'utente_personale')
\gexec

SELECT format('ALTER DATABASE %I OWNER TO %I', datname, :'utente_personale')
  FROM conv_altri_db
\gexec

-- ── 3. I privilegi di default, ricopiati per zeroerp_owner ──────────────────
-- Stessi destinatari e stessi diritti dell'utente personale, schema per schema.
-- Il destinatario «utente personale» si salta: diventa membro dell'owner.
\echo [ZeroErp] conversione: privilegi di default per zeroerp_owner
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE zeroerp_owner%s GRANT %s ON %s TO %I%s',
              CASE WHEN d.defaclnamespace = 0 THEN ''
                   ELSE format(' IN SCHEMA %I', d.defaclnamespace::regnamespace) END,
              a.privilege_type,
              CASE d.defaclobjtype WHEN 'r' THEN 'TABLES'
                                   WHEN 'S' THEN 'SEQUENCES'
                                   WHEN 'f' THEN 'FUNCTIONS'
                                   WHEN 'T' THEN 'TYPES'
                                   WHEN 'n' THEN 'SCHEMAS' END,
              pg_get_userbyid(a.grantee),
              CASE WHEN a.is_grantable THEN ' WITH GRANT OPTION' ELSE '' END)
  FROM pg_default_acl d
 CROSS JOIN LATERAL aclexplode(d.defaclacl) a
 WHERE d.defaclrole = (SELECT oid FROM pg_roles WHERE rolname = :'utente_personale')
   AND a.grantee <> d.defaclrole
   AND a.grantee <> 0   -- PUBLIC: nessuno dei default del progetto lo nomina
 ORDER BY 1
\gexec

-- ── 4. L'utente personale lavora come proprietario ──────────────────────────
\echo [ZeroErp] conversione: :utente_personale membro di zeroerp_owner, con SET role
SELECT format('GRANT zeroerp_owner TO %I WITH INHERIT TRUE, SET TRUE', :'utente_personale')
\gexec
SELECT format('ALTER ROLE %I IN DATABASE %I SET role = %L',
              :'utente_personale', current_database(), 'zeroerp_owner')
\gexec

-- ── 5. pgagent, le procedure dei job, e «un owner solo» ─────────────────────
\set fase pre
\ir provision_zeroerp.sql
\set fase post
\ir provision_zeroerp.sql

-- ── 6. L'utente personale non possiede piu' niente qui ──────────────────────
DO $verifica$
DECLARE
    v_n int;
BEGIN
    SELECT count(*) INTO v_n
      FROM pg_shdepend s
     WHERE s.refobjid = (SELECT oid FROM pg_roles WHERE rolname = current_setting('zeroerp.conv_utente'))
       AND s.deptype = 'o'
       AND s.dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
       -- i suoi vecchi privilegi di default restano apposta (vedi in testa)
       AND s.classid <> 'pg_default_acl'::regclass;
    IF v_n > 0 THEN
        RAISE EXCEPTION 'l''utente personale possiede ancora % oggetti in questo database', v_n;
    END IF;
    RAISE NOTICE 'l''utente personale non possiede piu'' niente in %', current_database();
END
$verifica$;

\if :{?solo_prova}
\echo [ZeroErp] conversione: PROVA A VUOTO, tutto verificato, ROLLBACK
ROLLBACK;
\else
COMMIT;
\echo [ZeroErp] conversione completata: ora pgAgent come zeroerp_job (brief §16)
\endif
