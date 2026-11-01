{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_operatore_v2.md" %}
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
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- integer/text espliciti: colonne di django.auth_user (niente %TYPE).
    v_auth_user_id     integer;
    v_username         text;
    v_riusata          boolean := false;
    v_soggetto_id      anagrafiche.soggetti.id%TYPE;
    v_ru_id            anagrafiche.risorse_umane.id%TYPE;
    v_tipo_soggetto_id config.tipi_soggetto_dettaglio.tipo_soggetto_id%TYPE;
    v_veste_attiva     anagrafiche.identita_digitali.attivo%TYPE;
    v_trovata          integer;   -- la credenziale dell'email, se c'era (django: niente %TYPE)
    v_vesti            jsonb;
    v_dettaglio_pr     config.tipi_soggetto_dettaglio.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: orchestratore della creazione di un operatore.
    --   Due flussi sul soggetto (A: nuovo / B: esistente).
    --   ⭐ Rev 20260925-42 (brief-db-blocco-login-per-credenziale §5.2):
    --   - la credenziale dell'email, se c'e', si RIUSA (D-6):
    --     password, username e nome restano i suoi;
    --   - la veste OPERATORE nasce SPENTA, sempre: la accende
    --     l'attivazione dell'invito (regola unica, R-2);
    --   - una credenziale che ha gia' una veste OPERATORE (attiva
    --     o spenta) si rifiuta: il rimedio e' il (re)invito.
    --   ⭐ Rev 20260925-51 (§12.7 del brief), il riuso non e' piu' silenzioso:
    --   - se la credenziale ha una veste su una PERSONA FISICA diversa
    --     dall'operatore, e' un'altra persona: E_CREDENZIALE_ALTRA_PERSONA;
    --   - negli altri casi il riuso vuole il CONSENSO: p_riusa_auth_user_id
    --     deve dichiarare la credenziale trovata, altrimenti
    --     E_CREDENZIALE_DA_CONFERMARE: username e vesti li legge
            --     script.fn_get_credenziale_per_email, come il dialog (rev 20260927-41).
    --   ⭐ Rev 20261009-27 (brief-db-sesso-senza-default): p_sesso senza
    --   default ('M' prima); nel flusso A il soggetto nasce PRIVATO (PR),
    --   chiesto per nome a fn_crea_soggetto_pf, che non lo cabla piu'. Il
    --   sesso del PR e' obbligatorio: lo rifiuta il guard
    --   trgfn_soggetti_guard_sesso_policy, prima dello step 2-bis.
    -- Ritorna: la credenziale, il suo username EFFETTIVO, e se e'
    --   stata riusata (allora la password passata e' ignorata).
    -- =========================================================

    -- ============ Guard comuni ============
    -- ⚠️ Username e password_hash NON si validano qui: servono solo
    --   se la credenziale va creata, e allora li valida
    --   fn_crea_auth_user. Sulla credenziale riusata non servono.
    IF p_email IS NULL OR TRIM(p_email) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore_v2',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_email'),
            NULL::uuid, 'Email obbligatoria.'
        );
    END IF;

    IF p_qualifica_id IS NULL OR p_qualifica_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore_v2',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_qualifica_id'),
            NULL::uuid, 'Qualifica obbligatoria.'
        );
    END IF;

    -- ============ Step 1: la credenziale — riusata o creata ============
    -- La regola «quale credenziale ha questa email» sta in un posto
    -- solo, senza distinguere maiuscole e minuscole (D-9).
    v_auth_user_id := script.fn_get_auth_user_id_for_email(p_email);

    IF v_auth_user_id IS NOT NULL THEN
        -- ⭐ Serializza due creazioni sulla stessa credenziale: la
        --   seconda rilegge le vesti DOPO il COMMIT della prima.
        PERFORM 1
          FROM django.auth_user au
         WHERE au.id = v_auth_user_id
           FOR UPDATE;

        -- ⛔ Gia' operatore (attiva o spenta): con la veste che nasce
        --   spenta l'unique WHERE attivo qui non scatterebbe mai, e il
        --   duplicato scoppierebbe all'attivazione. DISABILITATO non
        --   conta: si ritira (R-5).
        SELECT bool_or(idg.attivo)
          INTO v_veste_attiva
          FROM anagrafiche.identita_digitali idg
         WHERE idg.auth_user_id = v_auth_user_id
           AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo;

        IF v_veste_attiva IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_CREDENZIALE_GIA_OPERATORE',
                jsonb_build_object('campo',        'email',
                                   'auth_user_id', v_auth_user_id,
                                   'veste_attiva', v_veste_attiva),
                NULL::uuid,
                TRIM(p_email));
        END IF;

        -- ⛔ Rev 20260925-51 — ALTRA PERSONA, dove il modello lo sa dire: una
        --   veste della credenziale sta su un soggetto PERSONA FISICA che non
        --   e' l'operatore (flusso B: un altro soggetto; flusso A: un altro
        --   codice fiscale). Con lo STESSO codice fiscale nel flusso A non si
        --   solleva qui: e' la stessa persona, e fn_crea_soggetto_pf dira'
        --   E_ADMIN_CF_DUPLICATO (va usato il soggetto esistente).
        --   Vesti su un'azienda, o nessuna veste: non decidibile -> consenso.
        IF EXISTS (
            SELECT 1
              FROM anagrafiche.identita_digitali idg
              JOIN anagrafiche.soggetti_ruoli sr         ON sr.id  = idg.soggetto_ruolo_id
              JOIN anagrafiche.soggetti s                ON s.id   = sr.soggetto_id
              JOIN config.tipi_soggetto_dettaglio tsd    ON tsd.id = s.tipo_soggetto_dettaglio_id
             WHERE idg.auth_user_id = v_auth_user_id
               AND tsd.tipo_soggetto_id = 'PF'
               AND CASE WHEN p_soggetto_id IS NOT NULL
                        THEN s.id <> p_soggetto_id
                        ELSE s.id_fiscale_univoco_cf_piva IS DISTINCT FROM UPPER(TRIM(p_codice_fiscale))
                   END
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_CREDENZIALE_ALTRA_PERSONA',
                jsonb_build_object('campo',        'email',
                                   'auth_user_id', v_auth_user_id),
                NULL::uuid,
                TRIM(p_email));
        END IF;

        v_riusata := true;
        v_trovata := v_auth_user_id;
    ELSE
        SELECT anagrafiche.fn_crea_auth_user(
            p_username      := p_username,
            p_email         := p_email,
            p_password_hash := p_password_hash,
            p_first_name    := COALESCE(p_nome, ''),
            p_last_name     := COALESCE(p_cognome, '')
        ) INTO v_auth_user_id;
    END IF;

    -- ============ Step 2: Soggetto (flusso A o B) ============
    IF p_soggetto_id IS NOT NULL THEN
        -- Flusso B: soggetto esistente
        SELECT tsd.tipo_soggetto_id
          INTO v_tipo_soggetto_id
          FROM anagrafiche.soggetti s
          JOIN config.tipi_soggetto_dettaglio tsd
            ON tsd.id = s.tipo_soggetto_dettaglio_id
         WHERE s.id = p_soggetto_id;

        IF v_tipo_soggetto_id IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('p_soggetto_id', p_soggetto_id),
                NULL::uuid,
                'Soggetto con id=' || p_soggetto_id || ' non trovato.'
            );
        END IF;

        IF v_tipo_soggetto_id <> 'PF' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('p_soggetto_id', p_soggetto_id,
                                  'tipo_soggetto_id', v_tipo_soggetto_id),
                NULL::uuid,
                'Soggetto deve essere Persona Fisica (PF). Trovato: ' || v_tipo_soggetto_id || '.'
            );
        END IF;

        v_soggetto_id := p_soggetto_id;

    ELSE
        -- Flusso A: crea soggetto PF nuovo
        IF p_cognome IS NULL OR TRIM(p_cognome) = '' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_cognome'),
                NULL::uuid, 'Cognome obbligatorio per creazione soggetto nuovo.'
            );
        END IF;

        IF p_nome IS NULL OR TRIM(p_nome) = '' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_nome'),
                NULL::uuid, 'Nome obbligatorio per creazione soggetto nuovo.'
            );
        END IF;

        IF p_codice_fiscale IS NULL OR TRIM(p_codice_fiscale) = '' THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('parametro', 'p_codice_fiscale'),
                NULL::uuid,
                'Codice fiscale obbligatorio per creazione soggetto nuovo.'
            );
        END IF;

        -- ⭐ Rev 20261009-27: l'operatore e' una persona fisica PRIVATA
        --   (PF pura: niente P.IVA, cfr. script.fn_guard_soggetto_pf_pura).
        SELECT tsd.id
          INTO v_dettaglio_pr
          FROM config.tipi_soggetto_dettaglio tsd
         WHERE tsd.codice_interno = 'PR';

        IF v_dettaglio_pr IS NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_operatore_v2',
                'E_CODICE',
                jsonb_build_object('codice_interno', 'PR'),
                NULL::uuid,
                'PR', 'config.tipi_soggetto_dettaglio'
            );
        END IF;

        SELECT anagrafiche.fn_crea_soggetto_pf(
            p_cognome                    := p_cognome,
            p_nome                       := p_nome,
            p_codice_fiscale             := p_codice_fiscale,
            p_email                      := p_email,
            p_data_nascita               := p_data_nascita,
            p_sesso                      := p_sesso,
            p_comune_nascita_id          := p_comune_nascita_id,
            p_tipo_soggetto_dettaglio_id := v_dettaglio_pr
        ) INTO v_soggetto_id;
    END IF;

    -- ============ Step 2-bis: il CONSENSO al riuso (rev 20260925-51) ============
    -- ⭐ Dopo il soggetto, e non prima: i rifiuti definitivi (flusso A
    --   incompleto, CF gia' presente, soggetto non PF) parlano per primi, e
    --   l'admin non conferma qualcosa che verrebbe rifiutato comunque.
    -- La dichiarazione deve dire la credenziale che c'e' (stampo della
    --   dichiarazione di pagamenti.fn_posta_contabile, D13): NULL se l'email
    --   e' nuova, l'id trovato se esiste. Qualunque differenza — nessun
    --   consenso, un'altra credenziale, una credenziale sparita nel frattempo —
    --   ferma PRIMA che il riuso diventi definitivo.
    IF p_riusa_auth_user_id IS DISTINCT FROM v_trovata THEN
        -- ⭐ Rev 20260927-41 (§17 del brief): username e vesti dal building
        --   block che legge anche il dialog di conferma del backend: rifiuto e
        --   dialog mostrano la stessa cosa (regola del 2). Zero righe se l'email
        --   non ha credenziale (v_trovata NULL): SELECT INTO azzera le variabili,
        --   e le vesti tornano all'array vuoto di prima.
        SELECT c.username, c.vesti
          INTO v_username, v_vesti
          FROM script.fn_get_credenziale_per_email(p_email) c;
        v_vesti := COALESCE(v_vesti, '[]'::jsonb);

        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_operatore_v2',
            'E_CREDENZIALE_DA_CONFERMARE',
            jsonb_build_object('campo',                'email',
                               'auth_user_id',         v_trovata,
                               'username',             v_username,
                               'vesti',                v_vesti,
                               'riusa_auth_user_id',   p_riusa_auth_user_id),
            NULL::uuid,
            TRIM(p_email),
            COALESCE(v_username, '-'));
    END IF;

    -- ============ Step 3: risorsa umana + veste OPERATORE SPENTA ============
    -- ⭐ p_attivo := false, sempre (R-2): la veste la accende
    --   l'attivazione dell'invito. La risorsa umana nasce attiva.
    SELECT anagrafiche.fn_crea_risorsa_umana_v2(
        p_soggetto_id            := v_soggetto_id,
        p_qualifica_id           := p_qualifica_id,
        p_unita_organizzativa_id := p_unita_organizzativa_id,
        p_valido_dal             := p_valido_dal,
        p_valido_al              := p_valido_al,
        p_auth_user_id           := v_auth_user_id,
        p_is_super_admin         := p_is_super_admin,
        p_attivo                 := false
    ) INTO v_ru_id;

    -- ============ Step 4: indirizzi soggetto (invariato) ============
    IF p_indirizzo_resid_dettaglio_id IS NOT NULL THEN
        -- Rev 2026-10-18 (D-4 di Tid): la madre prende l'indirizzo in jsonb.
        PERFORM anagrafiche.fn_crea_indirizzo_soggetto(
            v_soggetto_id,
            jsonb_build_object('tipo_indirizzo_codice_interno',  'RES',
                               'indirizzo_dettaglio_id', p_indirizzo_resid_dettaglio_id));

        PERFORM anagrafiche.fn_crea_indirizzo_soggetto(
            v_soggetto_id,
            jsonb_build_object('tipo_indirizzo_codice_interno',  'DOMFISC',
                               'indirizzo_dettaglio_id', COALESCE(
                                   p_indirizzo_domfisc_dettaglio_id,
                                   p_indirizzo_resid_dettaglio_id)));
    END IF;

    -- ============ Ritorno: lo username EFFETTIVO ============
    SELECT au.username
      INTO v_username
      FROM django.auth_user au
     WHERE au.id = v_auth_user_id;

    RETURN QUERY SELECT v_auth_user_id, v_username, v_riusata;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_operatore_v2(p_soggetto_id uuid, p_cognome text, p_nome text, p_codice_fiscale text, p_username text, p_email text, p_password_hash text, p_qualifica_id integer, p_unita_organizzativa_id integer, p_data_nascita date, p_sesso character, p_is_super_admin boolean, p_valido_dal date, p_valido_al date, p_comune_nascita_id integer, p_indirizzo_resid_dettaglio_id bigint, p_indirizzo_domfisc_dettaglio_id bigint, p_riusa_auth_user_id integer)
IS 'Orchestratore della creazione di un operatore (flusso A: soggetto PF nuovo; flusso B: soggetto esistente). ⭐ Rev 20260925-42 (brief-db-blocco-login-per-credenziale §5.2): (1) la credenziale dell''email, se esiste, si RIUSA (D-6, una persona una credenziale) senza toccarne password, username e nome — la cerca script.fn_get_auth_user_id_for_email, senza distinguere maiuscole e minuscole; altrimenti la crea fn_crea_auth_user; (2) la veste OPERATORE nasce SPENTA, sempre (regola unica dell''invito, R-2): la accende l''attivazione, e p_attivo e'' uscito dalla firma; (3) una credenziale che ha gia'' una veste OPERATORE, attiva o spenta, si rifiuta con E_CREDENZIALE_GIA_OPERATORE (il rimedio e'' il reinvito). ⭐ Rev 20260925-51 (§12.7): il riuso non e'' piu'' silenzioso — una credenziale con una veste su una PERSONA FISICA diversa dall''operatore si rifiuta (E_CREDENZIALE_ALTRA_PERSONA); negli altri casi serve il consenso, p_riusa_auth_user_id = la credenziale trovata, altrimenti E_CREDENZIALE_DA_CONFERMARE (dichiarazione di cio'' che si e'' visto, come pagamenti.fn_posta_contabile). ⭐ Rev 20260927-41 (§17): username e vesti della credenziale trovata li legge script.fn_get_credenziale_per_email, la stessa funzione del dialog di conferma del backend; nel contesto dell''errore restano per il log, che al client non arriva. ⭐ Rev 20261009-27 (brief-db-sesso-senza-default): p_sesso senza default (era ''M''); nel flusso A il soggetto nasce privato (PR), e il sesso e'' obbligatorio per il guard trgfn_soggetti_guard_sesso_policy (E_SESSO_OBBLIGATORIO); nel flusso B il sesso non si legge. Ritorna TABLE(auth_user_id, username effettivo, credenziale_riusata): con credenziale_riusata = true la password passata e'' stata IGNORATA. Si legge con SELECT * FROM. INVOKER. Rev 2026-10-18 (D-4 di Tid): gli indirizzi di residenza e domicilio fiscale passano a anagrafiche.fn_crea_indirizzo_soggetto in jsonb (contratto nuovo della madre).';
```

</div>

---
{% include-markdown "signature-core.md" %}
