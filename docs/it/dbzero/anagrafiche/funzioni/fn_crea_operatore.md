{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_operatore.md" %}
# ⚙️ Funzione `fn_crea_operatore`

```sql
CREATE FUNCTION fn_crea_operatore(p_soggetto_id uuid, p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_is_super_admin boolean, p_valido_dal date, p_valido_al date, p_comune_nascita_id integer, p_indirizzo_resid_dettaglio_id bigint, p_indirizzo_domfisc_dettaglio_id bigint, p_riusa_auth_user_id integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_operatore(p_soggetto_id uuid DEFAULT NULL::uuid, p_cognome text DEFAULT NULL::text, p_nome text DEFAULT NULL::text, p_codice_fiscale text DEFAULT NULL::text, p_username text DEFAULT NULL::text, p_email text DEFAULT NULL::text, p_password_hash text DEFAULT NULL::text, p_qualifica_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_data_nascita date DEFAULT NULL::date, p_sesso character DEFAULT NULL::bpchar, p_is_super_admin boolean DEFAULT false, p_valido_dal date DEFAULT script.fn_data_operativa(), p_valido_al date DEFAULT NULL::date, p_comune_nascita_id integer DEFAULT NULL::integer, p_indirizzo_resid_dettaglio_id bigint DEFAULT NULL::bigint, p_indirizzo_domfisc_dettaglio_id bigint DEFAULT NULL::bigint, p_riusa_auth_user_id integer DEFAULT NULL::integer)
 RETURNS TABLE(auth_user_id integer, username text, credenziale_riusata boolean)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Il verbo con cui il SUPER_ADMIN crea un operatore. E' la strada
--   dell'endpoint di amministrazione.
--
-- Regole:
--   - SECURITY DEFINER: il permesso e' qui, in prima riga, e chiede lo stesso
--     controllo dell'endpoint, il SUPER_ADMIN (script.fn_guard_super_admin:
--     E_PERMESSO_NEGATO, anche senza utente);
--   - la creazione la fa la primitiva anagrafiche.fn_applica_crea_operatore,
--     che l'app non esegue.
DECLARE
    v_utente config.user_emittenti_fiscali.auth_user_id%TYPE;
BEGIN
    -- Il permesso, prima di ogni altra cosa.
    v_utente := script.fn_utente_di_sessione('anagrafiche.fn_crea_operatore');
    PERFORM script.fn_guard_super_admin(v_utente);

    RETURN QUERY
    SELECT o.auth_user_id, o.username, o.credenziale_riusata
      FROM anagrafiche.fn_applica_crea_operatore(p_soggetto_id, p_cognome, p_nome, p_codice_fiscale, p_username, p_email, p_password_hash, p_qualifica_id, p_unita_organizzativa_id, p_data_nascita, p_sesso, p_is_super_admin, p_valido_dal, p_valido_al, p_comune_nascita_id, p_indirizzo_resid_dettaglio_id, p_indirizzo_domfisc_dettaglio_id, p_riusa_auth_user_id) o;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_operatore(p_soggetto_id uuid, p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_is_super_admin boolean, p_valido_dal date, p_valido_al date, p_comune_nascita_id integer, p_indirizzo_resid_dettaglio_id bigint, p_indirizzo_domfisc_dettaglio_id bigint, p_riusa_auth_user_id integer)
IS 'Il verbo con cui il SUPER_ADMIN crea un operatore in una transazione. SECURITY DEFINER: in prima riga chiede il SUPER_ADMIN all''utente di sessione (script.fn_guard_super_admin: E_PERMESSO_NEGATO, anche senza utente), lo stesso controllo dell''endpoint. La creazione la fa la primitiva anagrafiche.fn_applica_crea_operatore, che l''applicazione non esegue. Due strade sul soggetto: una persona nuova (nasce persona fisica privata, con codice fiscale e sesso obbligatori) o un soggetto persona fisica esistente (p_soggetto_id). La credenziale dell''email, se c''è, si riusa solo col consenso del chiamante (p_riusa_auth_user_id, E_CREDENZIALE_DA_CONFERMARE finché non arriva), mai se è di un''altra persona fisica (E_CREDENZIALE_ALTRA_PERSONA) o ha già una veste operatore (E_CREDENZIALE_GIA_OPERATORE: il rimedio è il reinvito); altrimenti nasce. Poi il rapporto e la veste OPERATORE SPENTA con anagrafiche.fn_crea_risorsa_umana (la accende l''attivazione dell''invito), il SUPER_ADMIN se richiesto, gli indirizzi di residenza e domicilio fiscale. Ritorna la credenziale, lo username e se è stata riusata. Il nome storico anagrafiche.fn_crea_operatore_v2 è un involucro di questa funzione, e l''applicazione non lo esegue.';
```

</div>

---
{% include-markdown "signature-core.md" %}
