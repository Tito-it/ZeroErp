# ⚙️ Funzione `fn_slega_profilo_identita`

```sql
CREATE FUNCTION fn_slega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_slega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tolti integer;  -- un conteggio: nessuna colonna di cui sia il riflesso
BEGIN
    -- =========================================================
    -- Scopo:
    --   Togliere il binding di un'identita' digitale da quel
    --   profilo di accesso. Ritorna quanti binding ha tolto.
    --
    -- Regole:
    --   - solo il binding verso QUEL profilo;
    --   - nessun binding: ritorna 0, non e' un errore;
    --   - l'ultimo super admin lo protegge il trigger della
    --     tabella;
    --   - argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA.
    -- =========================================================
    IF p_profilo_accesso_id IS NULL OR p_identita_digitale_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_slega_profilo_identita', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('profilo_accesso_id',   p_profilo_accesso_id,
                               'identita_digitale_id', p_identita_digitale_id),
            NULL::uuid,
            'config.fn_slega_profilo_identita',
            'profilo o identita'' mancanti');
    END IF;

    DELETE FROM config.profili_accesso_bindings pab
     WHERE pab.identita_digitale_id = p_identita_digitale_id
       AND pab.profilo_accesso_id   = p_profilo_accesso_id;

    GET DIAGNOSTICS v_tolti = ROW_COUNT;
    RETURN v_tolti;
END;
$function$

COMMENT ON FUNCTION config.fn_slega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
IS 'MADRE (2026-10-19): toglie il binding di un''identita'' digitale da QUEL profilo di accesso (un''identita'' che ha un altro profilo non perde l''altro); ritorna quanti binding ha tolto, 0 se non ce n''era (idempotente). Il contrario di config.fn_lega_profilo_identita. L''ultimo super admin attivo lo protegge il trigger della tabella (trgfn_profili_accesso_bindings_guard_ultimo_super_admin, anche sul DELETE), per ogni scrittore. Argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. Non controlla il permesso (backend). INVOKER. Sede unica del DELETE di AmmSoftwareRepository._set_super_admin_binding (ramo enabled = false). R-BE-7, D-16c di Tid, brief-db-processi-accensione-per-ambiente §6.16.';
```

---
{% include-markdown "signature-core.md" %}
