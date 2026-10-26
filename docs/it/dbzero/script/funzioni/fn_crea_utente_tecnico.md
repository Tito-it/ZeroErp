{% include-markdown "it/dbzero/script/manual/fn_crea_utente_tecnico.md" %}
# ⚙️ Funzione `fn_crea_utente_tecnico`

```sql
CREATE FUNCTION fn_crea_utente_tecnico(p_processo_codice text, p_emittente_codice character varying, p_profilo_codice character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

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

    -- ⭐ Rev 2026-09-05: «non esiste» e «esiste ma non e' eleggibile» erano lo
    --   STESSO errore, e mandano a cercare in due posti diversi: il primo nel
    --   seed del catalogo, il secondo nella riga che c'e' gia'.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_crea_utente_tecnico',
            'E_PROCESSO_NON_TROVATO',
            jsonb_build_object('processo_codice', p_processo_codice),
            NULL::uuid, p_processo_codice);
    END IF;

    IF NOT v_processo.attivo
       OR v_processo.obsoleto_dal IS NOT NULL
       OR v_processo.classe <> 'DOMINIO'
       OR v_processo.canale NOT IN ('PGAGENT', 'COMMAND', 'CODA_AUTOMATICA') THEN
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
    -- Rev 2026-10-18 (D-1 di Tid): lo stato proposto, non 'IT' nel codice.
    v_stato_id := script.fn_stato_proposto_id('script.fn_crea_utente_tecnico');

    -- ⭐ Lo username porta ENTRAMBI: e' un badge per posto di
    --   lavoro, e il posto di lavoro qui e' (processo, emittente).
    --   Cosi' resta unico e leggibile quando gli emittenti sono N.
    v_username := p_processo_codice || '@' || p_emittente_codice;

    -- ⚠️ NON confondere questo guard col guard 4 qui sopra, e i due codici
    --   NON sono intercambiabili perche' i loro messaggi hanno un numero
    --   DIVERSO di segnaposto:
    --     guard 4  E_UTENTE_TECNICO_GIA_ESISTE     1 %s  «esiste ed e' ATTIVO»
    --     qui      E_UTENTE_TECNICO_DA_RIATTIVARE  2 %s  «esiste ed e' SPENTO»
    --   ⛔ Rinominarne uno «per uniformita'» fa crashare format(). E' successo:
    --     una sostituzione globale del nome ha toccato anche il guard 4, e a
    --     prenderlo e' stato il presidio
    --     db/pgtap/script/test-catalogo-messaggi-errore-completo.sql.
    -- ⛔ IL MURO CHE NON PARLAVA. Il guard sul duplicato piu' sopra guarda
    --   dbops.processi_identita.attivo; lo username NO, e il suo UNIQUE su
    --   django.auth_user non ha condizioni. ⇒ Disattivare il legame — che e' la
    --   via documentata per sostituire l'utente di un processo — liberava il
    --   guard e lasciava in piedi `auth_user_username_key`: un 23505 NUDO, che
    --   non dice quale regola sia stata toccata.
    --   ⭐ Qui ci si ferma prima, e si indica il verbo giusto: l'utente non va
    --     rifatto, va RIATTIVATO (script.fn_riattiva_utente_tecnico).
    IF EXISTS (SELECT 1 FROM django.auth_user au WHERE au.username = v_username) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_crea_utente_tecnico',
            'E_UTENTE_TECNICO_DA_RIATTIVARE',
            jsonb_build_object('processo_codice',  p_processo_codice,
                               'emittente_codice', p_emittente_codice,
                               'username',         v_username),
            NULL::uuid, p_processo_codice, p_emittente_codice);
    END IF;

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
    --    (BB anagrafiche.fn_crea_contatto, rev 2026-10-17)
    PERFORM anagrafiche.fn_crea_contatto(
        v_soggetto_id, NULL,
        jsonb_build_object('tipo_contatto_id', v_tipo_contatto_id,
                           'nominativo',       'Processo automatico: ' || v_username,
                           'is_default',       true));

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
        -- rev 2026-10-18: il BB del binding (regola del 2).
        PERFORM config.fn_lega_profilo_identita(v_profilo.id, v_identita_id);
    END IF;

    -- 7. Il legame processo -> utente.
    INSERT INTO dbops.processi_identita
        (processo_id, auth_user_id)
    VALUES (v_processo.id, v_auth_user_id);

    RETURN v_auth_user_id;
END;
$function$

COMMENT ON FUNCTION script.fn_crea_utente_tecnico(p_processo_codice text, p_emittente_codice character varying, p_profilo_codice character varying)
IS 'Crea l''utente tecnico di un processo automatico PER UN EMITTENTE: utente Django con password inutilizzabile e username processo@emittente, soggetto dedicato col suo contatto, soggetto_ruolo PROC_AUTO, identita'' OPERATORE col flag tecnica, la riga di perimetro in config.user_emittenti_fiscali e il legame in dbops.processi_identita. Ritorna l''auth_user_id. ⭐ L''emittente e'' OBBLIGATORIO e costitutivo: config.user_emittenti_fiscali e'' 1-a-1 sull''utente, quindi un processo che serve N emittenti ha N utenti tecnici. ⚠️ D-9 resta: la funzione non SCEGLIE l''emittente, lo riceve da chi scrive la chiamata. Il profilo e'' facoltativo e di norma non si passa; se indicato dev''essere AD_HOC. ⛔ Mai SUPER_ADMIN. ⭐ Rev 2026-09-05 (R-E strada B): accetta anche il canale CODA_AUTOMATICA; il canale CODA «umano» resta rifiutato, perche'' li'' l''identita'' la porta l''operatore che accoda. ⭐ Rev 2026-09-05 (DB-6): due guard che prima non parlavano. «Processo inesistente» e «processo non eleggibile» erano lo STESSO errore e mandavano a cercare in due posti diversi: adesso il primo e'' E_PROCESSO_NON_TROVATO. E lo username duplicato alzava un 23505 NUDO: adesso e'' E_UTENTE_TECNICO_DA_RIATTIVARE, che indica il verbo giusto — script.fn_riattiva_utente_tecnico. Brief: brief-db-processi-automatici-residui-be, DB-6 e DB-8. Rev 2026-10-17: il contatto lo scrive il BB anagrafiche.fn_crea_contatto (regola del 2, brief-db-processi-accensione-per-ambiente 2b-1 lotto 3); comportamento invariato. Rev 2026-10-18: il binding del profilo chiesto lo scrive il BB config.fn_lega_profilo_identita (regola del 2, brief-db-processi-accensione-per-ambiente 2b-1 lotto 8); comportamento invariato. Rev 2026-10-18 (D-1 di Tid): lo stato del soggetto tecnico e'' lo stato proposto (script.fn_stato_proposto_id), non piu'' ''IT'' scritto nel corpo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
