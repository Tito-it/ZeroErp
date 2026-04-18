{% include-markdown "it/dbzero/script/manual/fn_get_ruolo_sistema.md" %}
# ⚙️ Funzione `fn_get_ruolo_sistema`

```sql
CREATE FUNCTION fn_get_ruolo_sistema(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_ruolo_sistema(p_auth_user_id integer)
 RETURNS config.ruolo_sistema
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- DEPRECATO (§4.6.C.1). Wrapper retrocompatibile che
    -- ricostruisce ruolo_sistema dal nuovo modello:
    --   - Nessuna identita OPERATORE usabile -> DISABILITATO
    --   - SUPER_ADMIN binding attivo        -> ADMIN
    --   - Altrimenti                         -> OPERATIVO
    -- Mantenere fino a PR2 (refactor Python PermissionResolver
    -- + test). Rimuovere in §4.6.H.3 o successivo.
    -- =========================================================

    IF p_auth_user_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- Copre sia "nessun record" sia "ruolo DISABILITATO"
    -- sia "finestra scaduta": tutto si traduce in
    -- DISABILITATO per retrocompat semantica.
    -- Helper DRY §4.6.B.0.
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN 'DISABILITATO'::config.ruolo_sistema;
    END IF;

    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN 'ADMIN'::config.ruolo_sistema;
    END IF;

    RETURN 'OPERATIVO'::config.ruolo_sistema;
END
$function$

COMMENT ON FUNCTION script.fn_get_ruolo_sistema(p_auth_user_id integer)
IS 'DEPRECATO §4.6.C.1: wrapper retrocompatibile che ricostruisce ruolo_sistema dal nuovo modello (identita_digitali + binding SUPER_ADMIN). Mantenuto fino a PR2 backend. Nuovi chiamanti: usare fn_is_super_admin + check identita.';
```

---
{% include-markdown "signature-core.md" %}
