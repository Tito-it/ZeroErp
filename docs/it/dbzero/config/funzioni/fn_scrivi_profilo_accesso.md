{% include-markdown "it/dbzero/config/manual/fn_scrivi_profilo_accesso.md" %}
# ⚙️ Funzione `fn_scrivi_profilo_accesso`

```sql
CREATE FUNCTION fn_scrivi_profilo_accesso(p_tipo config.tipo_profilo_accesso, p_codice character varying, p_descrizione text, p_aree jsonb, p_azioni jsonb, p_campi jsonb)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_scrivi_profilo_accesso(p_tipo config.tipo_profilo_accesso, p_codice character varying, p_descrizione text, p_aree jsonb DEFAULT NULL::jsonb, p_azioni jsonb DEFAULT NULL::jsonb, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Il verbo con cui il SUPER_ADMIN scrive un profilo di accesso, con le sue
--   aree e azioni. E' la strada dell'endpoint del profilo di reparto.
--
-- Regole:
--   - SECURITY DEFINER: il permesso e' qui, in prima riga, e chiede lo stesso
--     controllo dell'endpoint, il SUPER_ADMIN (script.fn_guard_super_admin:
--     E_PERMESSO_NEGATO, anche senza utente);
--   - le regole del profilo stanno nella primitiva
--     config.fn_applica_scrivi_profilo_accesso, che l'app non esegue.
DECLARE
    v_utente config.user_emittenti_fiscali.auth_user_id%TYPE;
BEGIN
    -- Il permesso, prima di ogni altra cosa.
    v_utente := script.fn_utente_di_sessione('config.fn_scrivi_profilo_accesso');
    PERFORM script.fn_guard_super_admin(v_utente);

    RETURN config.fn_applica_scrivi_profilo_accesso(p_tipo, p_codice, p_descrizione, p_aree, p_azioni, p_campi);
END;
$function$

COMMENT ON FUNCTION config.fn_scrivi_profilo_accesso(p_tipo config.tipo_profilo_accesso, p_codice character varying, p_descrizione text, p_aree jsonb, p_azioni jsonb, p_campi jsonb)
IS 'Il verbo con cui il SUPER_ADMIN scrive un profilo di accesso per codice, con le sue aree e azioni; ritorna l''id. SECURITY DEFINER: in prima riga chiede il SUPER_ADMIN all''utente di sessione (script.fn_guard_super_admin: E_PERMESSO_NEGATO, anche senza utente), lo stesso controllo dell''endpoint. Le regole le tiene la primitiva config.fn_applica_scrivi_profilo_accesso, che l''applicazione non esegue: crea o aggiorna per codice, sostituisce aree (p_aree: elenco di {area_id, livello}) e azioni (p_azioni: elenco di {azione_id, abilitata}) se indicate, NULL = invariate; p_campi ammette attivo e richiede_secondo_fattore (E_CAMPO_NON_AMMESSO); un codice di un altro tipo, argomenti mancanti o elenchi malformati: E_SCRIPT_CHIAMATA_NON_VALIDA. Non scrive legami (config.fn_lega_profilo_identita, config.fn_lega_profilo_reparto). config.profili_accesso, config.profili_accesso_aree e config.profili_accesso_azioni sono in sola lettura per l''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
