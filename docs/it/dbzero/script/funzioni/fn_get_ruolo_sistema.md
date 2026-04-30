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
    -- DEPRECATA (§4.6.C.1, deprecation warning Fase 7
    -- 2026-04-29). Wrapper retrocompatibile che ricostruisce
    -- ruolo_sistema dal nuovo modello multi-face:
    --   - Nessuna identita OPERATORE usabile -> DISABILITATO
    --   - SUPER_ADMIN binding attivo        -> ADMIN
    --   - Altrimenti                         -> OPERATIVO
    --
    -- Migrazione consigliata per chiamanti:
    --   ruolo_sistema = 'ADMIN'        -> script.fn_is_super_admin(au_id)
    --   ruolo_sistema = 'DISABILITATO' -> NOT script.fn_has_identita_attiva(au_id, 'OPERATORE')
    --   ruolo_sistema = 'OPERATIVO'    -> fn_has_identita_attiva AND NOT fn_is_super_admin
    --
    -- Rimozione pianificata: Sprint N+2 (post merge BE+FE).
    -- Vedi WIP analisi-refactor.frontend-amm-software §Fase 7.
    -- =========================================================
    RAISE WARNING
        'script.fn_get_ruolo_sistema is DEPRECATED (Fase 7 cleanup). Migrate to script.fn_is_super_admin / script.fn_has_identita_attiva. Drop planned 2 sprints from 2026-04-29. Caller p_auth_user_id=%',
        p_auth_user_id;

    IF p_auth_user_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- Copre "nessun record" + "ruolo DISABILITATO" + "finestra
    -- scaduta": tutto si traduce in DISABILITATO per
    -- retrocompat semantica.
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
IS 'DEPRECATA §4.6.C.1 + Fase 7 (2026-04-29 deprecation warning). Wrapper retrocompatibile che ricostruisce ruolo_sistema dal nuovo modello multi-face (identita_digitali + binding SUPER_ADMIN). Solleva RAISE WARNING ad ogni chiamata fino al drop pianificato (Sprint N+2). Migrazione: usare fn_is_super_admin + fn_has_identita_attiva direttamente.';
```

---
{% include-markdown "signature-core.md" %}
