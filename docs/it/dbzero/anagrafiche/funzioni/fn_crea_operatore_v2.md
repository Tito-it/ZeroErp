# ⚙️ Funzione `fn_crea_operatore_v2`

```sql
CREATE FUNCTION fn_crea_operatore_v2(p_soggetto_id uuid, p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_is_super_admin boolean, p_valido_dal date, p_valido_al date, p_comune_nascita_id integer, p_indirizzo_resid_dettaglio_id bigint, p_indirizzo_domfisc_dettaglio_id bigint, p_riusa_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_operatore_v2(p_soggetto_id uuid DEFAULT NULL::uuid, p_cognome text DEFAULT NULL::text, p_nome text DEFAULT NULL::text, p_codice_fiscale text DEFAULT NULL::text, p_username text DEFAULT NULL::text, p_email text DEFAULT NULL::text, p_password_hash text DEFAULT NULL::text, p_qualifica_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_data_nascita date DEFAULT NULL::date, p_sesso character DEFAULT NULL::bpchar, p_is_super_admin boolean DEFAULT false, p_valido_dal date DEFAULT script.fn_data_operativa(), p_valido_al date DEFAULT NULL::date, p_comune_nascita_id integer DEFAULT NULL::integer, p_indirizzo_resid_dettaglio_id bigint DEFAULT NULL::bigint, p_indirizzo_domfisc_dettaglio_id bigint DEFAULT NULL::bigint, p_riusa_auth_user_id integer DEFAULT NULL::integer)
 RETURNS TABLE(auth_user_id integer, username text, credenziale_riusata boolean)
 LANGUAGE sql
AS $function$
    -- Involucro del nome storico: lo chiama il backend finche' non passa a
    -- anagrafiche.fn_crea_operatore. Nessuna regola qui: tutto e' nel verbo.
    SELECT * FROM anagrafiche.fn_crea_operatore(p_soggetto_id, p_cognome, p_nome, p_codice_fiscale, p_username, p_email, p_password_hash, p_qualifica_id, p_unita_organizzativa_id, p_data_nascita, p_sesso, p_is_super_admin, p_valido_dal, p_valido_al, p_comune_nascita_id, p_indirizzo_resid_dettaglio_id, p_indirizzo_domfisc_dettaglio_id, p_riusa_auth_user_id);
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_operatore_v2(p_soggetto_id uuid, p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_is_super_admin boolean, p_valido_dal date, p_valido_al date, p_comune_nascita_id integer, p_indirizzo_resid_dettaglio_id bigint, p_indirizzo_domfisc_dettaglio_id bigint, p_riusa_auth_user_id integer)
IS 'Involucro del nome storico di anagrafiche.fn_crea_operatore, con la stessa firma e lo stesso risultato: lo chiama il backend finche'' non passa al nome nuovo, poi si ritira. Nessuna regola propria.';
```

</div>

---
{% include-markdown "signature-core.md" %}
