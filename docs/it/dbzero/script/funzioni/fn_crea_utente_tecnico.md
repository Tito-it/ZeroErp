# ⚙️ Funzione `fn_crea_utente_tecnico`

```sql
CREATE FUNCTION fn_crea_utente_tecnico(p_processo_codice text, p_emittente_codice character varying, p_profilo_codice character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_crea_utente_tecnico(p_processo_codice text, p_emittente_codice character varying, p_profilo_codice character varying DEFAULT NULL::character varying)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ Niente %TYPE su django.*.
    v_auth_user_id     integer;
    v_processo         dbops.processi%ROWTYPE;
    v_emittente        anagrafiche.emittenti_fiscali%ROWTYPE;
    v_profilo          config.profili_accesso%ROWTYPE;
    v_tipo_ruolo_id    config.tipi_ruoli.id%TYPE;
    v_tipo_contatto_id anagrafiche.contatti.tipo_contatto_id%TYPE;
    v_stato_id         anagrafiche.soggetti.stato_id%TYPE;
    v_soggetto_id      anagrafiche.soggetti.id%TYPE;
    v_sog_ruolo_id     anagrafiche.soggetti_ruoli.id%TYPE;
    v_identita_id      anagrafiche.identita_digitali.id%TYPE;
    v_username         text;
BEGIN
    -- Guard 1: il processo vuole davvero un utente tecnico.
    --   ⛔ I processi su canale CODA no: girano con lo scope
    --   dell'operatore che li accoda.
    SELECT * INTO v_processo
      FROM dbops.processi
     WHERE codice = p_processo_codice;

    IF NOT FOUND
       OR NOT v_processo.attivo
       OR v_processo.obsoleto_dal IS NOT NULL
       OR v_processo.classe <> 'DOMINIO'
       OR v_processo.canale NOT IN ('PGAGENT', 'COMMAND') THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_crea_utente_tecnico',
            'E_PROCESSO_NON_ELEGGIBILE_UTENTE_TECNICO',
            jsonb_build_object('processo_codice', p_processo_codice),
            NULL::uuid, p_processo_codice);
    END IF;

    -- Guard 2: l'emittente, OBBLIGATORIO e costitutivo.
    SELECT * INTO v_emittente
      FROM anagrafiche.emittenti_fiscali
     WHERE codice = p_emittente_codice;

    IF NOT FOUND OR NOT v_emittente.attivo THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_crea_utente_tecnico',
            'E_UTENTE_TECNICO_EMITTENTE_NON_VALIDO',
            jsonb_build_object('emittente_codice', p_emittente_codice),
            NULL::uuid, p_emittente_codice);
    END IF;

    -- Guard 3: il profilo, SE indicato — di norma non lo e'.
    IF p_profilo_codice IS NOT NULL THEN
        SELECT * INTO v_profilo
          FROM config.profili_accesso
         WHERE codice = p_profilo_codice;

        IF NOT FOUND
           OR NOT v_profilo.attivo
           OR v_profilo.tipo <> 'AD_HOC'::config.tipo_profilo_accesso THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.fn_crea_utente_tecnico',
                'E_UTENTE_TECNICO_PROFILO_VIETATO',
                jsonb_build_object('profilo_codice', p_profilo_codice),
                NULL::uuid, p_profilo_codice);
        END IF;
    END IF;

    -- Guard 4: uno per processo PER EMITTENTE. Ci si ferma prima
    --   dell'unique: un 23505 nudo non direbbe quale regola.
    IF EXISTS (
        SELECT 1
          FROM dbops.processi_identita pi
          JOIN config.user_emittenti_fiscali uef
            ON uef.auth_user_id = pi.auth_user_id
         WHERE pi.processo_id = v_processo.id
           AND pi.attivo
           AND uef.emittente_fiscale_id = v_emittente.id) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_crea_utente_tecnico',
            'E_UTENTE_TECNICO_GIA_ESISTE',
            jsonb_build_object('processo_codice', p_processo_codice,
                               'emittente_codice', p_emittente_codice),
            NULL::uuid, p_processo_codice);
    END IF;

    SELECT id INTO v_tipo_ruolo_id
      FROM config.tipi_ruoli WHERE codice_interno = 'PROC_AUTO';
    SELECT id INTO v_tipo_contatto_id
      FROM config.tipi_contatti WHERE codice_interno = 'PRINCIPALE';
    SELECT id INTO v_stato_id
      FROM config.stati WHERE codice_iso2 = 'IT';

    -- ⭐ Lo username porta ENTRAMBI: e' un badge per posto di
    --   lavoro, e il posto di lavoro qui e' (processo, emittente).
    --   Cosi' resta unico e leggibile quando gli emittenti sono N.
    v_username := p_processo_codice || '@' || p_emittente_codice;

    -- 1. L'utente Django, con password INUTILIZZABILE ('!' e' la
    --    convenzione Django per «non puo' autenticarsi»).
    INSERT INTO django.auth_user
        (password, is_superuser, username, first_name, last_name,
         email, is_staff, is_active, date_joined)
    VALUES ('!' || md5(random()::text || clock_timestamp()::text),
            false, v_username, '', '', '', false, true, now())
    RETURNING id INTO v_auth_user_id;

    -- 2. Il soggetto, uno per (processo, emittente).
    --    `codice` NULL -> lo genera trgfn_soggetti_gen_codice;
    --    `tipo_soggetto_dettaglio_id` NULL -> i guard differiti su
    --    indirizzi e dati societari escono da soli.
    INSERT INTO anagrafiche.soggetti
        (ragione_sociale, stato_id)
    VALUES ('Processo automatico: ' || v_username, v_stato_id)
    RETURNING id INTO v_soggetto_id;

    -- 3. Il contatto di riferimento: il guard differito sui
    --    contatti ammette esplicitamente `is_default` coi canali
    --    vuoti, ed e' la verita' — un processo canali non ne ha.
    INSERT INTO anagrafiche.contatti
        (soggetto_id, tipo_contatto_id, nominativo, is_default)
    VALUES (v_soggetto_id, v_tipo_contatto_id,
            'Processo automatico: ' || v_username, true);

    -- Padre e figlio in ISTRUZIONI SEPARATE: una CTE unica
    -- condividerebbe la stessa snapshot.
    INSERT INTO anagrafiche.soggetti_ruoli
        (soggetto_id, tipo_ruolo_id)
    VALUES (v_soggetto_id, v_tipo_ruolo_id)
    RETURNING id INTO v_sog_ruolo_id;

    -- 4. L'identita': OPERATORE (ogni policy RLS lo pretende in
    --    AND) + flag tecnica, che sceglie il ramo PROC_AUTO del
    --    guard di coerenza.
    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, tecnica)
    VALUES (v_sog_ruolo_id, v_auth_user_id,
            'OPERATORE'::config.ruolo_applicativo, true)
    RETURNING id INTO v_identita_id;

    -- 5. ⭐ IL PERIMETRO. Una riga sola, perche' la tabella e'
    --    1-a-1 sull'utente. Non e' il sistema che si concede un
    --    permesso: l'emittente e' arrivato come parametro, deciso
    --    da chi ha scritto la chiamata (D-9).
    INSERT INTO config.user_emittenti_fiscali
        (auth_user_id, emittente_fiscale_id)
    VALUES (v_auth_user_id, v_emittente.id);

    -- 6. Il binding SOLO se un profilo e' stato chiesto.
    IF p_profilo_codice IS NOT NULL THEN
        INSERT INTO config.profili_accesso_bindings
            (profilo_accesso_id, identita_digitale_id)
        VALUES (v_profilo.id, v_identita_id);
    END IF;

    -- 7. Il legame processo -> utente.
    INSERT INTO dbops.processi_identita
        (processo_id, auth_user_id)
    VALUES (v_processo.id, v_auth_user_id);

    RETURN v_auth_user_id;
END;
$function$

COMMENT ON FUNCTION script.fn_crea_utente_tecnico(p_processo_codice text, p_emittente_codice character varying, p_profilo_codice character varying)
IS 'Crea l''utente tecnico di un processo automatico PER UN EMITTENTE: utente Django con password inutilizzabile e username processo@emittente, soggetto dedicato col suo contatto, soggetto_ruolo PROC_AUTO, identita'' OPERATORE con flag tecnica, la riga di perimetro in config.user_emittenti_fiscali e il legame in dbops.processi_identita. Ritorna l''auth_user_id. ⭐ L''emittente e'' OBBLIGATORIO e costitutivo: config.user_emittenti_fiscali e'' 1-a-1 sull''utente (UNIQUE(auth_user_id), changeSet 20260408-11) e in questo modello solo il super admin e'' multi-emittente — quindi un processo che serve N emittenti ha N utenti tecnici. ⚠️ D-9 resta: la funzione non SCEGLIE l''emittente, lo riceve da chi scrive la chiamata. Il profilo e'' facoltativo e di norma non si passa (zero capability = minimo privilegio); se indicato dev''essere AD_HOC. ⛔ Mai SUPER_ADMIN. Brief: brief-db-processi-automatici-identita-e-perimetro §4.';
```

---
{% include-markdown "signature-core.md" %}
