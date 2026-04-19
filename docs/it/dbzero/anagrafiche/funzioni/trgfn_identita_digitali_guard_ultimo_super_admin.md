{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_identita_digitali_guard_ultimo_super_admin.md" %}
# ⚙️ Funzione `trgfn_identita_digitali_guard_ultimo_super_admin`

```sql
CREATE FUNCTION trgfn_identita_digitali_guard_ultimo_super_admin()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_was_super_admin boolean := false;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Impedire disattivazioni di identita_digitali che
    --   lascerebbero il sistema senza SUPER_ADMIN attivi.
    --
    -- Regole:
    --   1. Short-circuit: solo transizione attivo true -> false.
    --   2. Short-circuit 2: solo se l'identita disattivata
    --      portava almeno un binding SUPER_ADMIN attivo.
    --      Altrimenti il count non puo' peggiorare.
    --   3. Se a rischio, verifica post-stato via fn_check.
    --      Se false, raise E_PROFILO_ULTIMO_SUPER_ADMIN.
    -- =========================================================

    IF NOT (OLD.attivo = true AND NEW.attivo = false) THEN
        RETURN NULL;
    END IF;

    SELECT EXISTS (
        SELECT 1
          FROM config.profili_accesso_bindings pab
          JOIN config.profili_accesso          pa
            ON pa.id = pab.profilo_accesso_id
         WHERE pab.identita_digitale_id = OLD.id
           AND pab.attivo = true
           AND pa.codice  = 'SUPER_ADMIN'
           AND pa.attivo  = true
    )
    INTO v_was_super_admin;

    IF NOT v_was_super_admin THEN
        RETURN NULL;
    END IF;

    IF NOT script.fn_check_almeno_un_super_admin_attivo() THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            TG_NAME,
            'E_PROFILO_ULTIMO_SUPER_ADMIN',
            jsonb_build_object(
                'op', TG_OP,
                'identita_digitale_id', OLD.id,
                'auth_user_id', OLD.auth_user_id,
                'ruolo_applicativo', OLD.ruolo_applicativo
            ),
            NULL::uuid,
            format('Disattivazione identita_digitali id=%s lascerebbe zero SUPER_ADMIN attivi', OLD.id)
        );
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin()
IS 'Guard anti-lockout: impedisce di disattivare un''identita che portava l''ultimo binding SUPER_ADMIN attivo. Delega il check a script.fn_check_almeno_un_super_admin_attivo. Codice errore E_PROFILO_ULTIMO_SUPER_ADMIN.';
```

---
{% include-markdown "signature-core.md" %}
