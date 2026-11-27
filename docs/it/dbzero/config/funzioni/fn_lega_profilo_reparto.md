{% include-markdown "it/dbzero/config/manual/fn_lega_profilo_reparto.md" %}
# ⚙️ Funzione `fn_lega_profilo_reparto`

```sql
CREATE FUNCTION fn_lega_profilo_reparto(p_profilo_accesso_id integer, p_unita_organizzativa_id integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_lega_profilo_reparto(p_profilo_accesso_id integer, p_unita_organizzativa_id integer)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente config.user_emittenti_fiscali.auth_user_id%TYPE;
    v_id config.profili_accesso_bindings.id%TYPE;
BEGIN
    -- Il permesso, prima di ogni altra cosa.
    v_utente := script.fn_utente_di_sessione('config.fn_lega_profilo_reparto');
    PERFORM script.fn_guard_super_admin(v_utente);

    -- =========================================================
    -- Scopo:
    --   Legare un reparto (unita' organizzativa) a un profilo
    --   di accesso. Ritorna l'id del binding.
    --
    -- Regole:
    --   - lo stesso profilo gia' legato: ritorna quel binding;
    --   - un altro profilo gia' legato: lo dice il vincolo
    --     uq_profili_accesso_bindings_uo;
    --   - argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA.
    -- =========================================================
    IF p_profilo_accesso_id IS NULL OR p_unita_organizzativa_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_lega_profilo_reparto', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('profilo_accesso_id',     p_profilo_accesso_id,
                               'unita_organizzativa_id', p_unita_organizzativa_id),
            NULL::uuid,
            'config.fn_lega_profilo_reparto',
            'profilo o reparto mancanti');
    END IF;

    SELECT pab.id
      INTO v_id
      FROM config.profili_accesso_bindings pab
     WHERE pab.unita_organizzativa_id = p_unita_organizzativa_id
       AND pab.profilo_accesso_id     = p_profilo_accesso_id;

    IF v_id IS NOT NULL THEN
        RETURN v_id;
    END IF;

    INSERT INTO config.profili_accesso_bindings (profilo_accesso_id, unita_organizzativa_id)
    VALUES (p_profilo_accesso_id, p_unita_organizzativa_id)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION config.fn_lega_profilo_reparto(p_profilo_accesso_id integer, p_unita_organizzativa_id integer)
IS 'Il verbo con cui il SUPER_ADMIN lega un reparto (unità organizzativa) a un profilo di accesso, la riga di config.profili_accesso_bindings con unita_organizzativa_id; ritorna l''id del legame. SECURITY DEFINER: in prima riga chiede il SUPER_ADMIN all''utente di sessione (script.fn_guard_super_admin: E_PERMESSO_NEGATO, anche senza utente), lo stesso controllo dell''endpoint. Lo stesso profilo già legato ritorna quel legame, un altro profilo già legato lo rifiuta uq_profili_accesso_bindings_uo; argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. Coerenza e notifica dei permessi: i trigger della tabella. Il contrario: config.fn_slega_profilo_reparto. config.profili_accesso_bindings è in sola lettura per l''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
