{% include-markdown "it/dbzero/config/manual/trgfn_profili_accesso_bindings_guard_ultimo_super_admin.md" %}
# ⚙️ Funzione `trgfn_profili_accesso_bindings_guard_ultimo_super_admin`

```sql
CREATE FUNCTION trgfn_profili_accesso_bindings_guard_ultimo_super_admin()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_old_is_super_admin boolean := false;
    v_transition_risky   boolean := false;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Impedire che un'operazione su profili_accesso_bindings
    --   lasci il sistema senza alcun SUPER_ADMIN attivo.
    --
    -- Regole:
    --   1. Short-circuit: il trigger lavora solo se la vecchia
    --      riga puntava a un profilo SUPER_ADMIN ed era attiva.
    --      Tutte le altre transizioni non possono ridurre il
    --      numero di super admin raggiungibili.
    --   2. La transizione e' a rischio se:
    --      - DELETE
    --      - UPDATE con NEW.attivo = false
    --      - UPDATE con cambio profilo_accesso_id
    --      - UPDATE con cambio identita_digitale_id
    --   3. Se a rischio, verifica post-stato via
    --      fn_check_almeno_un_super_admin_attivo. Se false,
    --      raise E_PROFILO_ULTIMO_SUPER_ADMIN.
    -- =========================================================

    IF OLD.attivo = true THEN
        SELECT (pa.codice = 'SUPER_ADMIN')
          INTO v_old_is_super_admin
          FROM config.profili_accesso pa
         WHERE pa.id = OLD.profilo_accesso_id;
    END IF;

    IF NOT COALESCE(v_old_is_super_admin, false) THEN
        RETURN NULL;
    END IF;

    IF TG_OP = 'DELETE' THEN
        v_transition_risky := true;
    ELSIF TG_OP = 'UPDATE' THEN
        v_transition_risky :=
               NEW.attivo             = false
            OR NEW.profilo_accesso_id IS DISTINCT FROM OLD.profilo_accesso_id
            OR NEW.identita_digitale_id IS DISTINCT FROM OLD.identita_digitale_id;
    END IF;

    IF NOT v_transition_risky THEN
        RETURN NULL;
    END IF;

    IF NOT script.fn_check_almeno_un_super_admin_attivo() THEN
        PERFORM script.fn_log_and_raise_error(
            'config',
            TG_NAME,
            'E_PROFILO_ULTIMO_SUPER_ADMIN',
            jsonb_build_object(
                'op', TG_OP,
                'old_binding_id', OLD.id,
                'old_profilo_accesso_id', OLD.profilo_accesso_id,
                'old_identita_digitale_id', OLD.identita_digitale_id
            ),
            NULL::uuid,
            format('Operazione %s sul binding id=%s lascerebbe zero SUPER_ADMIN attivi', TG_OP, OLD.id)
        );
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin()
IS 'Guard anti-lockout: impedisce operazioni su profili_accesso_bindings che lascerebbero il sistema senza SUPER_ADMIN raggiungibili. Delega il check a script.fn_check_almeno_un_super_admin_attivo. Codice errore E_PROFILO_ULTIMO_SUPER_ADMIN.';
```

---
{% include-markdown "signature-core.md" %}
