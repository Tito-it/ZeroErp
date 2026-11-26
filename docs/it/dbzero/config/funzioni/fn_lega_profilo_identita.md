{% include-markdown "it/dbzero/config/manual/fn_lega_profilo_identita.md" %}
# ⚙️ Funzione `fn_lega_profilo_identita`

```sql
CREATE FUNCTION fn_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Il verbo con cui il SUPER_ADMIN lega un'identita' digitale a un profilo
--   di accesso. E' la strada dell'endpoint di amministrazione.
--
-- Regole:
--   - SECURITY DEFINER: il permesso e' qui, in prima riga, e chiede lo stesso
--     controllo dell'endpoint, il SUPER_ADMIN (script.fn_guard_super_admin:
--     E_PERMESSO_NEGATO, anche senza utente);
--   - il legame lo scrive la primitiva config.fn_applica_lega_profilo_identita,
--     che l'app non esegue.
DECLARE
    v_utente config.user_emittenti_fiscali.auth_user_id%TYPE;
BEGIN
    -- Il permesso, prima di ogni altra cosa.
    v_utente := script.fn_utente_di_sessione('config.fn_lega_profilo_identita');
    PERFORM script.fn_guard_super_admin(v_utente);

    RETURN config.fn_applica_lega_profilo_identita(p_profilo_accesso_id, p_identita_digitale_id);
END;
$function$

COMMENT ON FUNCTION config.fn_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
IS 'Il verbo con cui il SUPER_ADMIN lega un''identità digitale a un profilo di accesso; ritorna l''id del legame. SECURITY DEFINER: in prima riga chiede il SUPER_ADMIN all''utente di sessione (script.fn_guard_super_admin: E_PERMESSO_NEGATO, anche senza utente), lo stesso controllo dell''endpoint. Il legame lo scrive la primitiva config.fn_applica_lega_profilo_identita, che l''applicazione non esegue: lo stesso profilo già legato ritorna quel legame, un altro profilo lo rifiuta uq_profili_accesso_bindings_identita, argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. config.profili_accesso_bindings è in sola lettura per l''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
