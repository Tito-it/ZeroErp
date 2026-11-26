{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_fixture_crea_operatore.md" %}
# ⚙️ Funzione `fn_pgtap_fixture_crea_operatore`

```sql
CREATE FUNCTION fn_pgtap_fixture_crea_operatore(p_soggetto_id uuid, p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_is_super_admin boolean, p_valido_dal date, p_valido_al date, p_comune_nascita_id integer, p_indirizzo_resid_dettaglio_id bigint, p_indirizzo_domfisc_dettaglio_id bigint, p_riusa_auth_user_id integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_fixture_crea_operatore(p_soggetto_id uuid DEFAULT NULL::uuid, p_cognome text DEFAULT NULL::text, p_nome text DEFAULT NULL::text, p_codice_fiscale text DEFAULT NULL::text, p_username text DEFAULT NULL::text, p_email text DEFAULT NULL::text, p_password_hash text DEFAULT NULL::text, p_qualifica_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_data_nascita date DEFAULT NULL::date, p_sesso character DEFAULT NULL::bpchar, p_is_super_admin boolean DEFAULT false, p_valido_dal date DEFAULT script.fn_data_operativa(), p_valido_al date DEFAULT NULL::date, p_comune_nascita_id integer DEFAULT NULL::integer, p_indirizzo_resid_dettaglio_id bigint DEFAULT NULL::bigint, p_indirizzo_domfisc_dettaglio_id bigint DEFAULT NULL::bigint, p_riusa_auth_user_id integer DEFAULT NULL::integer)
 RETURNS TABLE(auth_user_id integer, username text, credenziale_riusata boolean)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo:
--   Fixture dei pgTAP: creare un operatore (anche SUPER_ADMIN) senza chiedere
--   permessi, solo dove sono ammessi i dati di sviluppo.
--
-- Regole:
--   - in PRODUZIONE: E_DATI_DI_SVILUPPO_IN_PRODUZIONE, prima di ogni scrittura;
--   - argomenti, regole e risultato: quelli di anagrafiche.fn_crea_operatore,
--     tramite la sua primitiva anagrafiche.fn_applica_crea_operatore.
DECLARE
    v_ambiente dbops.installazione.ambiente%TYPE;
BEGIN
    -- Il cancello: solo dove sono ammessi i dati di sviluppo.
    v_ambiente := script.fn_ambiente_installazione();
    IF NOT dbops.fn_dati_di_sviluppo_ammessi_su_valori(v_ambiente) THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_fixture_crea_operatore',
            'E_DATI_DI_SVILUPPO_IN_PRODUZIONE',
            jsonb_build_object('ambiente', v_ambiente),
            NULL::uuid,
            v_ambiente);
    END IF;

    RETURN QUERY
    SELECT o.auth_user_id, o.username, o.credenziale_riusata
      FROM anagrafiche.fn_applica_crea_operatore(p_soggetto_id, p_cognome, p_nome, p_codice_fiscale, p_username, p_email, p_password_hash, p_qualifica_id, p_unita_organizzativa_id, p_data_nascita, p_sesso, p_is_super_admin, p_valido_dal, p_valido_al, p_comune_nascita_id, p_indirizzo_resid_dettaglio_id, p_indirizzo_domfisc_dettaglio_id, p_riusa_auth_user_id) o;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_fixture_crea_operatore(p_soggetto_id uuid, p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_is_super_admin boolean, p_valido_dal date, p_valido_al date, p_comune_nascita_id integer, p_indirizzo_resid_dettaglio_id bigint, p_indirizzo_domfisc_dettaglio_id bigint, p_riusa_auth_user_id integer)
IS 'Fixture dei pgTAP: crea un operatore, anche SUPER_ADMIN, con la primitiva anagrafiche.fn_applica_crea_operatore, senza chiedere permessi; argomenti, regole e risultato sono quelli del verbo anagrafiche.fn_crea_operatore. SECURITY DEFINER ed eseguibile dall''applicazione, perché il primo SUPER_ADMIN di un test non ha nessuno da cui farsi creare: per questo parte solo dove sono ammessi i dati di sviluppo (dbops.fn_dati_di_sviluppo_ammessi_su_valori sull''ambiente dell''installazione), e in PRODUZIONE solleva E_DATI_DI_SVILUPPO_IN_PRODUZIONE. La usa dbops.fn_pgtap_crea_operatore_umano; un test non la chiama da sé.';
```

</div>

---
{% include-markdown "signature-core.md" %}
