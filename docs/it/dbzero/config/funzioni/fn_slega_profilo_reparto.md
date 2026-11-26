# ⚙️ Funzione `fn_slega_profilo_reparto`

```sql
CREATE FUNCTION fn_slega_profilo_reparto(p_profilo_accesso_id integer, p_unita_organizzativa_id integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_slega_profilo_reparto(p_profilo_accesso_id integer, p_unita_organizzativa_id integer)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente config.user_emittenti_fiscali.auth_user_id%TYPE;
    v_tolti integer;  -- un conteggio: nessuna colonna di cui sia il riflesso
BEGIN
    -- Il permesso, prima di ogni altra cosa.
    v_utente := script.fn_utente_di_sessione('config.fn_slega_profilo_reparto');
    PERFORM script.fn_guard_super_admin(v_utente);

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
IS 'Il verbo con cui il SUPER_ADMIN toglie il legame di un reparto (unità organizzativa) da quel profilo di accesso; ritorna quanti legami ha tolto, 0 se non ce n''era. SECURITY DEFINER: in prima riga chiede il SUPER_ADMIN all''utente di sessione (script.fn_guard_super_admin: E_PERMESSO_NEGATO, anche senza utente). Argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. Il contrario di config.fn_lega_profilo_reparto. config.profili_accesso_bindings è in sola lettura per l''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
