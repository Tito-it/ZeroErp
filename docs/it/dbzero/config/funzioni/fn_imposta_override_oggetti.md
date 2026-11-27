{% include-markdown "it/dbzero/config/manual/fn_imposta_override_oggetti.md" %}
# ⚙️ Funzione `fn_imposta_override_oggetti`

```sql
CREATE FUNCTION fn_imposta_override_oggetti(p_auth_user_id integer, p_oggetti jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_imposta_override_oggetti(p_auth_user_id integer, p_oggetti jsonb)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Il verbo con cui il SUPER_ADMIN sostituisce gli override di un utente
--   sugli oggetti con l'elenco dato. E' la strada dell'endpoint di
--   amministrazione.
--
-- Regole:
--   - SECURITY DEFINER: il permesso e' qui, in prima riga, e chiede lo stesso
--     controllo dell'endpoint, il SUPER_ADMIN (script.fn_guard_super_admin:
--     E_PERMESSO_NEGATO, anche senza utente);
--   - gli override li scrive la primitiva config.fn_applica_imposta_override,
--     che l'app non esegue.
DECLARE
    v_utente config.user_override_oggetti.auth_user_id%TYPE;
BEGIN
    -- Il permesso, prima di ogni altra cosa.
    v_utente := script.fn_utente_di_sessione('config.fn_imposta_override_oggetti');
    PERFORM script.fn_guard_super_admin(v_utente);

    RETURN config.fn_applica_imposta_override(
        'config.user_override_oggetti'::regclass, p_auth_user_id, p_oggetti);
END;
$function$

COMMENT ON FUNCTION config.fn_imposta_override_oggetti(p_auth_user_id integer, p_oggetti jsonb)
IS 'Il verbo con cui il SUPER_ADMIN sostituisce gli override di un utente sugli oggetti (config.user_override_oggetti) con l''elenco p_oggetti, anche vuoto (= nessun override); ritorna quanti ne scrive. SECURITY DEFINER: in prima riga chiede il SUPER_ADMIN all''utente di sessione (script.fn_guard_super_admin: E_PERMESSO_NEGATO, anche senza utente), lo stesso controllo dell''endpoint. Un elemento: app_label, model_name, livello (obbligatori), motivo, valido_dal, valido_al; una chiave assente prende il DEFAULT (valido_dal = la data operativa), una chiave a null scrive NULL (valido_dal NULL = senza inizio). Chiave estranea: E_CAMPO_NON_AMMESSO; utente NULL, elenco o elemento malformati: E_SCRIPT_CHIAMATA_NON_VALIDA. Oggetto fuori catalogo o riservato: fk_user_override_oggetti_catalogo; date: trgfn_guard_date_validita. Scrive la primitiva config.fn_applica_imposta_override, che l''applicazione non esegue. Non invalida la cache dei permessi (backend). config.user_override_oggetti è in sola lettura per l''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
