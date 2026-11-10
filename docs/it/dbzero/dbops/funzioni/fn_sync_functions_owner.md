{% include-markdown "it/dbzero/dbops/manual/fn_sync_functions_owner.md" %}
# ⚙️ Funzione `fn_sync_functions_owner`

```sql
CREATE FUNCTION fn_sync_functions_owner()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `postgres`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_sync_functions_owner()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    r              dbops.sec_functions_owner%ROWTYPE;
    v_regproc      regprocedure;
    v_owner_oid    oid;
    v_owner_name   text;
    v_required_oid oid;
BEGIN

-- ------------------------------------------------------------
-- dbops.fn_sync_functions_owner()
-- Sincronizza l'owner delle funzioni "sensibili" in base alla
-- tabella dbops.sec_functions_owner.
--
-- NOTE:
--  - Va idealmente posseduta da postgres e SECURITY DEFINER
--    per poter cambiare owner ad altre funzioni.
--  - RISERVATA al migratore (dal 2026-09-26): chi la esegue decide
--    chi possiede le DEFINER di postgres. La guardia sta QUI e non
--    nell'ACL: EXECUTE a PUBLIC resta, e con la guardia non compra
--    niente. Brief: brief-db-registro-owner-e-sync-riservati-al-migratore.
-- ------------------------------------------------------------

    -- ⛔ session_user, NON current_user: dentro una SECURITY DEFINER
    --    current_user e' il PROPRIETARIO (postgres, superuser) e la
    --    guardia sarebbe sempre aperta. Limite dichiarato: session_user
    --    e' il ruolo di LOGIN, un SET ROLE non lo cambia.
    --    Passa chi e' membro del proprietario dello schema dbops (il
    --    migratore, in ogni ambiente) e un superuser. Fail-closed.
    -- ⛔ Il rifiuto e' un RAISE nudo (42501), fuori dal canale di log:
    --    fn_log_error_only e fn_ensure_logconn sono fra le funzioni che
    --    questa sync protegge.
    --    La domanda sta in dbops.fn_sessione_del_migratore (estratta
    --    il 2026-09-29, regola del 2: la chiede anche lo sblocco del
    --    secondo fattore).
    IF NOT dbops.fn_sessione_del_migratore() THEN
        RAISE EXCEPTION USING
            ERRCODE = 'insufficient_privilege',
            MESSAGE = format('dbops.fn_sync_functions_owner: riservata a chi possiede lo schema dbops (il migratore) o a un superuser; sessione %s.', session_user),
            HINT    = 'Si esegue dal migrate (90_end/20251123-04) o dalla provision-post. Il registro dbops.sec_functions_owner lo scrive solo il migratore.';
    END IF;

    FOR r IN
        SELECT *
        FROM dbops.sec_functions_owner
        ORDER BY schema_name, function_name, arg_types
    LOOP
        -- Costruisco la signature per to_regprocedure:
        -- se arg_types = '' → nessun argomento
        IF r.arg_types = '' THEN
            v_regproc := to_regprocedure(
                format('%I.%I()',
                    r.schema_name,
                    r.function_name)
            );
        ELSE
            v_regproc := to_regprocedure(
                format('%I.%I(%s)',
                    r.schema_name,
                    r.function_name,
                    r.arg_types)
            );
        END IF;

        IF v_regproc IS NULL THEN
            RAISE WARNING
                'fn_sync_functions_owner: funzione non trovata: %.%(%).',
                r.schema_name, r.function_name, r.arg_types;
            CONTINUE;
        END IF;

        -- Owner corrente
        SELECT p.proowner, pg_get_userbyid(p.proowner)
        INTO v_owner_oid, v_owner_name
        FROM pg_proc p
        WHERE p.oid = v_regproc;

        -- Owner richiesto
        SELECT oid
        INTO v_required_oid
        FROM pg_roles
        WHERE rolname = r.required_owner;

        IF v_required_oid IS NULL THEN
            RAISE WARNING
                'fn_sync_functions_owner: ruolo richiesto "%" non esiste (%.%(%)).',
                r.required_owner, r.schema_name, r.function_name, r.arg_types;
            CONTINUE;
        END IF;

        -- Se già coincide → niente da fare
        IF v_owner_oid = v_required_oid THEN
            CONTINUE;
        END IF;

        -- TENTO ALTER FUNCTION OWNER TO ...
        BEGIN
            EXECUTE format(
                'ALTER FUNCTION %s OWNER TO %I',
                v_regproc,
                r.required_owner
            );

            RAISE NOTICE
                'fn_sync_functions_owner: cambiato owner funzione %.%(%): % -> %.',
                r.schema_name, r.function_name, r.arg_types,
                v_owner_name, r.required_owner;

        EXCEPTION
            WHEN insufficient_privilege THEN
                RAISE WARNING
                    'fn_sync_functions_owner: privilegi insufficienti per ALTER FUNCTION %.%(%): owner attuale %, richiesto %.',
                    r.schema_name, r.function_name, r.arg_types,
                    v_owner_name, r.required_owner;
            WHEN others THEN
                RAISE WARNING
                    'fn_sync_functions_owner: errore inatteso su funzione %.%(%): % %.',
                    r.schema_name, r.function_name, r.arg_types,
                    SQLSTATE, SQLERRM;
        END;
    END LOOP;
END;
$function$

COMMENT ON FUNCTION dbops.fn_sync_functions_owner()
IS 'Allinea il proprietario delle funzioni elencate in dbops.sec_functions_owner al ruolo richiesto (ALTER FUNCTION ... OWNER TO). Non solleva su un singolo cambio non riuscito: lo segnala con un WARNING e prosegue. Eseguita a ogni migrate (90_end) e dalla passata post del provisioning come postgres. SECURITY DEFINER di postgres, con search_path fissato a pg_catalog, public, pg_temp nella definizione: un CREATE OR REPLACE che lo dimentica lo azzera. Riservata al migratore con una guardia nel corpo: la esegue solo chi e'' membro del proprietario dello schema dbops, o un superuser; gli altri ricevono 42501 (RAISE nudo, fuori dal canale di log che la sync protegge). La domanda la fa dbops.fn_sessione_del_migratore, che legge session_user perche'' dentro una DEFINER current_user e'' il proprietario: limite dichiarato, session_user e'' il ruolo di login e un SET ROLE non lo cambia. EXECUTE a PUBLIC resta per scelta: la difesa non e'' nell''ACL, che il loop dei grant riscrive e il cambio di proprietario rimappa. Il registro e'' in sola lettura per l''applicazione. Per cambiare una funzione di postgres un changeSet la prende in prestito: cambia required_owner, chiama la sync, fa il suo lavoro e la restituisce; la sync stessa, che non si presta a se'' stessa, passa da una copia di servizio temporanea.';
```

</div>

---
{% include-markdown "signature-core.md" %}
