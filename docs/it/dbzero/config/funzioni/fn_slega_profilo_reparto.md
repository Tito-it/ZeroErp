# ⚙️ Funzione `fn_slega_profilo_reparto`

```sql
CREATE FUNCTION fn_slega_profilo_reparto(p_profilo_accesso_id integer, p_unita_organizzativa_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_slega_profilo_reparto(p_profilo_accesso_id integer, p_unita_organizzativa_id integer)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tolti integer;  -- un conteggio: nessuna colonna di cui sia il riflesso
BEGIN
    -- =========================================================
    -- Scopo:
    --   Togliere il binding di un reparto da quel profilo di
    --   accesso. Ritorna quanti binding ha tolto.
    --
    -- Regole:
    --   - solo il binding verso QUEL profilo;
    --   - nessun binding: ritorna 0, non e' un errore;
    --   - argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA.
    -- =========================================================
    IF p_profilo_accesso_id IS NULL OR p_unita_organizzativa_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_slega_profilo_reparto', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('profilo_accesso_id',     p_profilo_accesso_id,
                               'unita_organizzativa_id', p_unita_organizzativa_id),
            NULL::uuid,
            'config.fn_slega_profilo_reparto',
            'profilo o reparto mancanti');
    END IF;

    DELETE FROM config.profili_accesso_bindings pab
     WHERE pab.unita_organizzativa_id = p_unita_organizzativa_id
       AND pab.profilo_accesso_id     = p_profilo_accesso_id;

    GET DIAGNOSTICS v_tolti = ROW_COUNT;
    RETURN v_tolti;
END;
$function$

COMMENT ON FUNCTION config.fn_slega_profilo_reparto(p_profilo_accesso_id integer, p_unita_organizzativa_id integer)
IS 'MADRE (2026-10-19): toglie il binding di un reparto (unita'' organizzativa) da QUEL profilo di accesso; ritorna quanti binding ha tolto, 0 se non ce n''era (idempotente). Il contrario di config.fn_lega_profilo_reparto, gemella di config.fn_slega_profilo_identita. Nasce con la madre che lega, prima che qualcuno ne abbia bisogno: senza, il primo scrittore farebbe un DELETE suo. Argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. Non controlla il permesso (backend). INVOKER. R-BE-7, D-16c di Tid, brief-db-processi-accensione-per-ambiente §6.16.';
```

</div>

---
{% include-markdown "signature-core.md" %}
