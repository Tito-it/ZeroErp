{% include-markdown "it/dbzero/config/manual/trgfn_credenziali_guard_ultimo_super_admin.md" %}
# ⚙️ Funzione `trgfn_credenziali_guard_ultimo_super_admin`

```sql
CREATE FUNCTION trgfn_credenziali_guard_ultimo_super_admin()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_credenziali_guard_ultimo_super_admin()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: impedire che il blocco dell'admin lasci il sistema senza
--   SUPER_ADMIN raggiungibili.
-- Regole (stampo di trgfn_identita_digitali_guard_ultimo_super_admin):
--   1. solo la transizione «non bloccata -> bloccata»;
--   2. solo se la credenziale portava un binding SUPER_ADMIN attivo;
--   3. verifica sullo stato DOPO via fn_check_almeno_un_super_admin_attivo.
DECLARE
    v_era_super_admin boolean := false;
BEGIN
    IF NEW.bloccata_at IS NULL THEN
        RETURN NULL;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.bloccata_at IS NOT NULL THEN
        RETURN NULL;
    END IF;

    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali    id
          JOIN config.profili_accesso_bindings  pab
            ON pab.identita_digitale_id = id.id
          JOIN config.profili_accesso           pa
            ON pa.id = pab.profilo_accesso_id
         WHERE id.auth_user_id = NEW.auth_user_id
           AND id.attivo  = true
           AND pab.attivo = true
           AND pa.attivo  = true
           AND pa.tipo    = 'SUPER_ADMIN'::config.tipo_profilo_accesso
    )
    INTO v_era_super_admin;

    IF NOT v_era_super_admin THEN
        RETURN NULL;
    END IF;

    IF NOT script.fn_check_almeno_un_super_admin_attivo() THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_PROFILO_ULTIMO_SUPER_ADMIN',
            jsonb_build_object('op',           TG_OP,
                               'auth_user_id', NEW.auth_user_id,
                               'bloccata_da',  NEW.bloccata_da),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION config.trgfn_credenziali_guard_ultimo_super_admin()
IS 'Guard anti-lockout sul blocco dell''amministratore: impedisce di bloccare la credenziale che porta l''ultimo SUPER_ADMIN raggiungibile. Terza porta della stessa regola dopo i guard su profili_accesso_bindings e identita_digitali: delega a script.fn_check_almeno_un_super_admin_attivo, che conosce il blocco (rev 2026-09-25). Solo la transizione non bloccata -> bloccata, solo se la credenziale portava un binding SUPER_ADMIN attivo. Codice E_PROFILO_ULTIMO_SUPER_ADMIN, lo stesso dei gemelli. Brief: brief-db-blocco-login-per-credenziale §3.3.';
```

</div>

---
{% include-markdown "signature-core.md" %}
