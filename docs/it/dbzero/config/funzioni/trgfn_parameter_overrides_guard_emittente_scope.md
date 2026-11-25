{% include-markdown "it/dbzero/config/manual/trgfn_parameter_overrides_guard_emittente_scope.md" %}
# ⚙️ Funzione `trgfn_parameter_overrides_guard_emittente_scope`

```sql
CREATE FUNCTION trgfn_parameter_overrides_guard_emittente_scope()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_parameter_overrides_guard_emittente_scope()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: un override per emittente si scrive, si modifica e si
--   cancella solo dentro il perimetro emittente di chi agisce.
--   Si giudicano la riga di prima e quella di dopo.
-- Tabella senza row level security: il BB
--   script.trgfn_guard_emittente_scope non basta (il perche' e'
--   nell'header del changeSet 20261124-13).
-- Brief: brief-db-emittente-del-super-admin §3.1 (R-DB-1).
-- =========================================================
DECLARE
    v_auth_user_id   anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_ef_prima       config.parameter_overrides.emittente_fiscale_id%TYPE;
    v_ef_dopo        config.parameter_overrides.emittente_fiscale_id%TYPE;
    v_ruolo_sessione pg_catalog.pg_roles.rolname%TYPE;
    -- Esito del controllo «la RLS non la filtrerebbe»: nessuna colonna.
    v_fuori_rls      boolean;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        v_ef_prima := OLD.emittente_fiscale_id;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        v_ef_dopo := NEW.emittente_fiscale_id;
    END IF;

    -- Nessun padrone, ne' prima ne' dopo: niente da proteggere.
    IF num_nonnulls(v_ef_prima, v_ef_dopo) = 0 THEN
        IF TG_OP = 'DELETE' THEN
            RETURN OLD;
        END IF;
        RETURN NEW;
    END IF;

    v_auth_user_id := script.fn_utente_di_sessione(
        'config.trgfn_parameter_overrides_guard_emittente_scope');

    IF v_auth_user_id IS NULL THEN
        -- Il ruolo di sessione, non il login (come il BB, rev 2026-10-15):
        -- un utente personale che lavora come proprietario (SET role) e'
        -- il proprietario; una DEFINER cambia current_user, non `role`.
        v_ruolo_sessione := coalesce(nullif(current_setting('role'), 'none'), session_user);

        SELECT r.rolsuper
            OR r.rolbypassrls
            OR pg_has_role(current_user, c.relowner, 'USAGE')
          INTO v_fuori_rls
          FROM pg_catalog.pg_roles r
          CROSS JOIN pg_catalog.pg_class c
         WHERE r.rolname = current_user
           AND c.oid = TG_RELID;

        IF current_user = v_ruolo_sessione AND coalesce(v_fuori_rls, false) THEN
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END IF;

        PERFORM script.fn_log_and_raise_error(
            'database',
            'config.trgfn_parameter_overrides_guard_emittente_scope',
            'E_SCOPE_SENZA_UTENTE',
            jsonb_build_object(
                'detail', 'Scrittura senza utente in sessione su un override per emittente',
                'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'operazione', TG_OP,
                'emittente_prima', v_ef_prima,
                'emittente_dopo', v_ef_dopo,
                'db_user', current_user,
                'session_user', session_user,
                'dentro_definer', current_user <> v_ruolo_sessione),
            NULL::uuid,
            TG_TABLE_SCHEMA::text,
            TG_TABLE_NAME::text);
    END IF;

    -- La riga di prima: chi non ha quell'azienda non la modifica e
    -- non la cancella, anche se l'emittente non cambia.
    IF v_ef_prima IS NOT NULL
       AND NOT script.fn_check_user_emittente_scope(v_auth_user_id, v_ef_prima) THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'config.trgfn_parameter_overrides_guard_emittente_scope',
            'E_SCOPE_EMITTENTE',
            jsonb_build_object(
                'detail', 'Utente non autorizzato per l''emittente dell''override esistente',
                'auth_user_id', v_auth_user_id,
                'emittente_fiscale_id', v_ef_prima,
                'riga', 'prima',
                'operazione', TG_OP,
                'override_id', OLD.id,
                'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
            NULL::uuid,
            format('Utente %s non autorizzato per emittente fiscale %s su %s.%s',
                   v_auth_user_id, v_ef_prima, TG_TABLE_SCHEMA, TG_TABLE_NAME));
    END IF;

    -- La riga di dopo: se e' la stessa azienda e' gia' giudicata.
    IF v_ef_dopo IS NOT NULL
       AND v_ef_dopo IS DISTINCT FROM v_ef_prima
       AND NOT script.fn_check_user_emittente_scope(v_auth_user_id, v_ef_dopo) THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'config.trgfn_parameter_overrides_guard_emittente_scope',
            'E_SCOPE_EMITTENTE',
            jsonb_build_object(
                'detail', 'Utente non autorizzato per l''emittente dell''override scritto',
                'auth_user_id', v_auth_user_id,
                'emittente_fiscale_id', v_ef_dopo,
                'riga', 'dopo',
                'operazione', TG_OP,
                'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME),
            NULL::uuid,
            format('Utente %s non autorizzato per emittente fiscale %s su %s.%s',
                   v_auth_user_id, v_ef_dopo, TG_TABLE_SCHEMA, TG_TABLE_NAME));
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION config.trgfn_parameter_overrides_guard_emittente_scope()
IS 'Guard di perimetro emittente di config.parameter_overrides (a10, BEFORE INSERT OR UPDATE OR DELETE): la riga di prima (UPDATE, DELETE) e quella di dopo (INSERT, UPDATE) con emittente_fiscale_id valorizzato devono stare nel perimetro di chi agisce secondo script.fn_check_user_emittente_scope, altrimenti E_SCOPE_EMITTENTE; anche l''UPDATE del solo valore si giudica. Emittente NULL (override per utente, gruppo, categoria, funzione): nessun padrone, passa. Senza utente in sessione passa solo, fuori da una SECURITY DEFINER, la sessione che la RLS non filtrerebbe (superuser, BYPASSRLS, proprietario della tabella anche per appartenenza), altrimenti E_SCOPE_SENZA_UTENTE. Non e'' il BB script.trgfn_guard_emittente_scope perche'' la tabella non ha la RLS: il BB lavora accanto a una policy, e da solo lascerebbe passare l''UPDATE a emittente invariato, il DELETE e la sessione senza utente. In «tutti gli emittenti» il super admin passa (bypass di fn_check_user_emittente_scope).';
```

</div>

---
{% include-markdown "signature-core.md" %}
