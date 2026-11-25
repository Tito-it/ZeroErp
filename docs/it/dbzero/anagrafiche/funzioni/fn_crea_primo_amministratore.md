{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_primo_amministratore.md" %}
# ⚙️ Funzione `fn_crea_primo_amministratore`

```sql
CREATE FUNCTION fn_crea_primo_amministratore(p_cognome text, p_nome text, p_codice_fiscale text, p_sesso character, p_email text, p_username text, p_password_hash text, p_indirizzo_residenza jsonb, p_indirizzo_domicilio_fiscale jsonb, p_data_nascita date, p_comune_nascita_id integer, p_riusa_auth_user_id integer)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_primo_amministratore(p_cognome text, p_nome text, p_codice_fiscale text, p_sesso character, p_email text, p_username text, p_password_hash text, p_indirizzo_residenza jsonb, p_indirizzo_domicilio_fiscale jsonb DEFAULT NULL::jsonb, p_data_nascita date DEFAULT NULL::date, p_comune_nascita_id integer DEFAULT NULL::integer, p_riusa_auth_user_id integer DEFAULT NULL::integer)
 RETURNS TABLE(auth_user_id integer, username text, credenziale_riusata boolean)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    c_chi CONSTANT text := 'anagrafiche.fn_crea_primo_amministratore';
    v_qualifica_id config.qualifiche.id%TYPE;
    v_auth_user_id integer;   -- django.auth_user.id: niente %TYPE
    v_username     text;      -- idem
    v_riusata      boolean;
    v_soggetto_id  anagrafiche.soggetti.id%TYPE;
    v_identita_id  anagrafiche.identita_digitali.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il primo SUPER_ADMIN di un'installazione nuova, che entra
    --   subito: operatore, legame SUPER_ADMIN, veste accesa.
    --
    -- Regole:
    --   - DEFINER senza guard di permesso: lo chiude la
    --     condizione, «nessuna veste ha un legame SUPER_ADMIN,
    --     acceso o spento»;
    --   - la condizione si legge sotto il lock dei legami, che
    --     serializza due nascite concorrenti;
    --   - tutto o niente: e' una funzione sola.
    -- =========================================================

    -- 1. Il lock, poi la condizione: letta sotto il lock, la
    --    seconda chiamata concorrente vede il legame della prima.
    LOCK TABLE config.profili_accesso_bindings IN SHARE ROW EXCLUSIVE MODE;

    IF EXISTS (
        SELECT 1
          FROM config.profili_accesso_bindings pab
          JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
         WHERE pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
           AND pab.identita_digitale_id IS NOT NULL
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_PRIMO_AMMINISTRATORE_GIA_PRESENTE',
            '{}'::jsonb,
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. La qualifica, per codice e non per id.
    SELECT q.id
      INTO v_qualifica_id
      FROM config.qualifiche q
     WHERE q.codice_interno = 'AMMINISTRATORE'
       AND q.attivo;

    IF v_qualifica_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', c_chi, 'E_CODICE',
            jsonb_build_object('codice_interno', 'AMMINISTRATORE'),
            NULL::uuid,
            'AMMINISTRATORE', 'config.qualifiche');
    END IF;

    -- 3. L'operatore: flusso A, legame SUPER_ADMIN, veste spenta.
    --    Gli indirizzi non passano di qui: fn_crea_operatore_v2 li
    --    vuole come dettagli gia' risolti.
    SELECT o.auth_user_id, o.username, o.credenziale_riusata
      INTO v_auth_user_id, v_username, v_riusata
      FROM anagrafiche.fn_crea_operatore_v2(
               p_cognome            := p_cognome,
               p_nome               := p_nome,
               p_codice_fiscale     := p_codice_fiscale,
               p_username           := p_username,
               p_email              := p_email,
               p_password_hash      := p_password_hash,
               p_qualifica_id       := v_qualifica_id,
               p_data_nascita       := p_data_nascita,
               p_sesso              := p_sesso,
               p_is_super_admin     := true,
               p_comune_nascita_id  := p_comune_nascita_id,
               p_riusa_auth_user_id := p_riusa_auth_user_id) o;

    -- 4. La veste: una sola OPERATORE per credenziale (la madre
    --    rifiuta una credenziale che ne ha gia' una).
    SELECT idg.id, sr.soggetto_id
      INTO v_identita_id, v_soggetto_id
      FROM anagrafiche.identita_digitali idg
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = idg.soggetto_ruolo_id
     WHERE idg.auth_user_id = v_auth_user_id
       AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo;

    -- 5. Gli indirizzi, nella forma che il comando sa scrivere.
    PERFORM anagrafiche.fn_crea_indirizzi_operatore(
        v_soggetto_id, p_indirizzo_residenza, p_indirizzo_domicilio_fiscale);

    -- 6. La veste si accende: nessuno puo' invitare il primo.
    PERFORM anagrafiche.fn_accendi_veste(
        v_identita_id, v_auth_user_id,
        ARRAY['OPERATORE']::config.ruolo_applicativo[]);

    RETURN QUERY SELECT v_auth_user_id, v_username, v_riusata;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_primo_amministratore(p_cognome text, p_nome text, p_codice_fiscale text, p_sesso character, p_email text, p_username text, p_password_hash text, p_indirizzo_residenza jsonb, p_indirizzo_domicilio_fiscale jsonb, p_data_nascita date, p_comune_nascita_id integer, p_riusa_auth_user_id integer)
IS 'Crea il primo SUPER_ADMIN di un''installazione nuova, che entra subito: un operatore con soggetto privato (PR) nuovo, la qualifica AMMINISTRATORE (per codice_interno; E_CODICE se manca), il legame al profilo SUPER_ADMIN e la veste OPERATORE accesa, senza invito. Si apre solo se nessuna veste ha un legame verso un profilo SUPER_ADMIN, acceso o spento: altrimenti E_PRIMO_AMMINISTRATORE_GIA_PRESENTE. Un sistema che ha avuto un amministratore e lo ha perso non si riapre da qui: il recupero passa dal proprietario del database, con le scritture che migliorano la garanzia di script.fn_check_almeno_un_super_admin_attivo. La condizione si legge sotto LOCK TABLE config.profili_accesso_bindings IN SHARE ROW EXCLUSIVE MODE, che serializza la nascita di un legame da qualunque strada. SECURITY DEFINER e senza guard di permesso, perche'' non c''e'' ancora nessuno che possa averlo: la condizione e'' l''unica cosa che lo chiude. Compone anagrafiche.fn_crea_operatore_v2 (credenziale nuova, o riuso col consenso di p_riusa_auth_user_id; i suoi rifiuti valgono qui), anagrafiche.fn_crea_indirizzi_operatore (residenza e domicilio fiscale in jsonb, nella forma di fn_crea_indirizzo_soggetto, senza tipo; il domicilio fiscale che manca e'' la residenza) e anagrafiche.fn_accendi_veste. Quali indirizzi sono obbligatori lo dice la configurazione dei tipi d''indirizzo, col suo guard differito al COMMIT. Riceve l''hash Django della password: il database non lo calcola. Le colonne d''audit portano il proprietario: nessuna persona e'' autenticata. Ritorna TABLE(auth_user_id, username effettivo, credenziale_riusata), come fn_crea_operatore_v2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
