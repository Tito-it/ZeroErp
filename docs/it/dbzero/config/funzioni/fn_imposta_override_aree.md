{% include-markdown "it/dbzero/config/manual/fn_imposta_override_aree.md" %}
# ⚙️ Funzione `fn_imposta_override_aree`

```sql
CREATE FUNCTION fn_imposta_override_aree(p_auth_user_id integer, p_aree jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_imposta_override_aree(p_auth_user_id integer, p_aree jsonb)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Il verbo con cui il SUPER_ADMIN sostituisce gli override di un utente
--   sulle aree con l'elenco dato (vuoto = nessun override). E' la strada
--   dell'endpoint di amministrazione.
--
-- Regole:
--   - SECURITY DEFINER: il permesso e' qui, in prima riga, e chiede lo stesso
--     controllo dell'endpoint, il SUPER_ADMIN (script.fn_guard_super_admin:
--     E_PERMESSO_NEGATO, anche senza utente);
--   - gli override li scrive la primitiva config.fn_applica_imposta_override,
--     che l'app non esegue.
DECLARE
    v_utente config.user_override_aree.auth_user_id%TYPE;
BEGIN
    -- Il permesso, prima di ogni altra cosa.
    v_utente := script.fn_utente_di_sessione('config.fn_imposta_override_aree');
    PERFORM script.fn_guard_super_admin(v_utente);

    RETURN config.fn_applica_imposta_override(
        'config.user_override_aree'::regclass, p_auth_user_id, p_aree);
END;
$function$

COMMENT ON FUNCTION config.fn_imposta_override_aree(p_auth_user_id integer, p_aree jsonb)
IS 'Il verbo con cui il SUPER_ADMIN sostituisce gli override di un utente sulle aree (config.user_override_aree) con l''elenco p_aree, anche vuoto (= nessun override); ritorna quanti ne scrive. SECURITY DEFINER: in prima riga chiede il SUPER_ADMIN all''utente di sessione (script.fn_guard_super_admin: E_PERMESSO_NEGATO, anche senza utente), lo stesso controllo dell''endpoint. Un elemento: area_id e livello (obbligatori), motivo, valido_dal, valido_al; una chiave assente prende il DEFAULT (valido_dal = la data operativa), una chiave a null scrive NULL (valido_dal NULL = senza inizio). Chiave estranea: E_CAMPO_NON_AMMESSO; utente NULL, elenco o elemento malformati: E_SCRIPT_CHIAMATA_NON_VALIDA. Due righe sulla stessa area: uq_user_override_aree_user_area; area inesistente: fk_user_override_aree_area; date: trgfn_guard_date_validita. Scrive la primitiva config.fn_applica_imposta_override, che l''applicazione non esegue. Non invalida la cache dei permessi (backend). config.user_override_aree è in sola lettura per l''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
