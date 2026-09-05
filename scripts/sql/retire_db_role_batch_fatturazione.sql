\set ON_ERROR_STOP on

-- ============================================================================
-- ZeroErp — RITIRO del ruolo batch: zeroerp_batch_fatturazione   (R-2)
-- ----------------------------------------------------------------------------
-- Vedi: docs/it/dev/work-in-progress/brief-db-processi-automatici-identita-e-perimetro.md
--       §12.2 (R-2) e §12.5 — provisioning: scripts/sql/provision_db_role_batch_fatturazione.sql
--
-- ── ⭐ CHE COSA SI STA TOGLIENDO, E PERCHE' ORA SI PUO' ─────────────────────
--   `zeroerp_batch_fatturazione` ha `BYPASSRLS`: il batch, connesso con quel
--   ruolo, vede e scrive TUTTE le aziende. Era il disegno giusto quando un
--   processo automatico non aveva un'identita' propria — non c'era altro modo
--   di dirgli «puoi lavorare».
--   ⇒ Adesso ce l'ha: ogni processo di DOMINIO ha un utente tecnico per
--   azienda, con la whitelist emittenti (`dbops.vw_processi_roster`). Il
--   perimetro lo puo' dare la RLS, che e' il posto giusto — il database — invece
--   della buona volonta' di una query.
--   ⛔ Finche' il ruolo esiste, le policy RLS su quel canale NON SI APPLICANO:
--   un errore di perimetro nel batch non verrebbe fermato da niente.
--
-- ── 🔴 L'ORDINE NON E' NEGOZIABILE: PRIMA IL BACKEND ────────────────────────
--   Questo script si lancia DOPO che il backend ha smesso di usare il ruolo.
--   Lanciarlo prima **ferma la fatturazione**: le connessioni che ripuntano a
--   quel ruolo falliscono all'autenticazione.
--   Quello che deve arrivare prima (perimetro backend, non nostro):
--     1. i tre call-site smettono di ripuntare la connessione al ruolo batch e
--        impostano invece `app.current_user_id` / `app.ruolo_applicativo` con
--        l'identita' tecnica del processo — `run_fatturazione_batch.py`,
--        `draina_coda_stampa.py`, `coda_lavori/drainer_service.py`;
--     2. `document_generation_service._guard_canale_sistema` viene RISCRITTO:
--        oggi solleva se la connessione NON e' `BYPASSRLS`, cioe' si rompe
--        apposta nel mondo nuovo. La domanda giusta diventa «c'e' un'identita'
--        tecnica dichiarata?», non «questa sessione bypassa?» (R-4);
--     3. `settings.py` non porta piu' le credenziali del ruolo batch.
--
-- ── ✅ COME SI VEDE CHE E' CHIUSO ───────────────────────────────────────────
--   `SELECT * FROM dbops.vw_processi_che_bypassano;`  ->  nessuna riga.
--   La vista legge `pg_roles` in diretta (`rolbypassrls AND rolcanlogin AND NOT
--   rolsuper`): non c'e' nessun seed da ripulire, sparisce il ruolo e sparisce
--   la riga.
--
-- ── ⚠️ SI LANCIA COME `postgres` ────────────────────────────────────────────
--   `DROP ROLE` di un ruolo con `BYPASSRLS` vuole il superuser, come la sua
--   creazione. Liquibase gira come `zeroerp` e non puo' farlo: per questo il
--   ritiro sta qui e non in un changeSet, esattamente come il provisioning.
--
--   psql -h <host> -U postgres -d <db> -v batch_role=zeroerp_batch_fatturazione \
--        -f scripts/sql/retire_db_role_batch_fatturazione.sql
--
-- ⛔ NON e' reversibile con un rollback: per tornare indietro si rilancia il
--   provisioning (che ricrea ruolo e grant) e si rimette la password.
-- ============================================================================

\echo [ZeroErp] Ritiro ruolo batch (R-2)
\echo [ZeroErp] Required vars: batch_role

\if :{?batch_role}
\else
\echo ERROR: missing -v batch_role=...
\quit 1
\endif

-- ---------------------------------------------------------------------------
-- Cancello 1 — il ruolo esiste? Se non c'e', il lavoro e' gia' fatto.
-- ---------------------------------------------------------------------------
DO $esiste$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'batch_role') THEN
        RAISE NOTICE 'Ruolo % assente: gia'' ritirato, niente da fare.', :'batch_role';
    END IF;
END
$esiste$;

-- ---------------------------------------------------------------------------
-- Cancello 2 — nessuno lo sta usando ADESSO.
-- ⛔ Si ferma invece di procedere: una sessione aperta con quel ruolo e' un
--   processo che sta lavorando, e toglierglielo sotto i piedi lo fa fallire a
--   meta'. ⚠️ E dice quante sono, invece di un «no» muto.
-- ---------------------------------------------------------------------------
DO $sessioni$
DECLARE
    v_aperte integer;
BEGIN
    SELECT count(*) INTO v_aperte
      FROM pg_stat_activity
     WHERE usename = :'batch_role';

    IF v_aperte > 0 THEN
        RAISE EXCEPTION
            'Ritiro annullato: % sessioni sono connesse come %. Fermare i processi che lo usano e rilanciare.',
            v_aperte, :'batch_role';
    END IF;
END
$sessioni$;

-- ---------------------------------------------------------------------------
-- Cancello 3 — il ruolo non deve POSSEDERE oggetti.
-- ⚠️ `DROP OWNED BY` qui sotto toglie i PRIVILEGI concessi al ruolo, ma
--   cancellerebbe anche gli oggetti di sua proprieta'. Il provisioning non gliene
--   fa creare nessuno (grant espliciti, nessuna membership di zeroerp_app): se
--   ne risulta uno, e' successo qualcosa che va guardato prima, non travolto.
-- ---------------------------------------------------------------------------
DO $proprieta$
DECLARE
    v_oggetti integer;
BEGIN
    SELECT count(*) INTO v_oggetti
      FROM pg_class c
      JOIN pg_roles r ON r.oid = c.relowner
     WHERE r.rolname = :'batch_role';

    IF v_oggetti > 0 THEN
        RAISE EXCEPTION
            'Ritiro annullato: % oggetti risultano di proprieta'' di %. Vanno riassegnati a mano (REASSIGN OWNED) dopo aver capito da dove vengono.',
            v_oggetti, :'batch_role';
    END IF;
END
$proprieta$;

-- ---------------------------------------------------------------------------
-- Il ritiro vero e proprio.
-- `DROP OWNED BY` revoca i privilegi che il provisioning gli aveva concesso
-- (SELECT schema-wide + DML sul perimetro di scrittura del batch); senza,
-- `DROP ROLE` fallirebbe con «altri oggetti dipendono dal ruolo».
-- ---------------------------------------------------------------------------
DO $ritiro$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'batch_role') THEN
        EXECUTE format('DROP OWNED BY %I', :'batch_role');
        EXECUTE format('DROP ROLE %I', :'batch_role');
        RAISE NOTICE 'Ruolo % ritirato.', :'batch_role';
    END IF;
END
$ritiro$;

-- ---------------------------------------------------------------------------
-- Verifica finale: il presidio deve essere vuoto.
-- ⭐ Non si guarda `pg_roles` a mano: si interroga la vista che il cantiere ha
--   acceso apposta, cosi' la prova e' la stessa che leggera' chiunque altro.
-- ---------------------------------------------------------------------------
\echo [ZeroErp] Presidio dbops.vw_processi_che_bypassano (atteso: nessuna riga)
SELECT ruolo, stato, nota FROM dbops.vw_processi_che_bypassano;
