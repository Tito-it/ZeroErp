{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_risorsa_umana.md" %}
# ⚙️ Funzione `fn_crea_risorsa_umana`

```sql
CREATE FUNCTION fn_crea_risorsa_umana(p_soggetto_id uuid, p_qualifica_id integer, p_unita_organizzativa_id integer, p_valido_dal date, p_valido_al date, p_auth_user_id integer, p_is_super_admin boolean, p_attivo boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_risorsa_umana(p_soggetto_id uuid DEFAULT NULL::uuid, p_qualifica_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_valido_dal date DEFAULT script.fn_data_operativa(), p_valido_al date DEFAULT NULL::date, p_auth_user_id integer DEFAULT NULL::integer, p_is_super_admin boolean DEFAULT false, p_attivo boolean DEFAULT false)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sr_id        anagrafiche.soggetti_ruoli.id%TYPE;
    v_ru_id        anagrafiche.risorse_umane.id%TYPE;
    v_identita_id  anagrafiche.identita_digitali.id%TYPE;
    v_profilo_sa   config.profili_accesso_bindings.profilo_accesso_id%TYPE;
    v_valido_dal   anagrafiche.risorse_umane.valido_dal%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: crea il rapporto (risorsa umana) e, se arriva la
    --   credenziale, la veste OPERATORE (+ il binding SUPER_ADMIN se
    --   p_is_super_admin). La veste nasce SPENTA per default: la
    --   accende l'attivazione dell'invito.
    --   p_valido_dal NULL = il giorno operativo, per il rapporto e
    --   per la veste.
    -- =========================================================

    -- Validazione parametri obbligatori
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_soggetto_id'),
            NULL::uuid, 'Soggetto obbligatorio.'
        );
    END IF;

    IF p_qualifica_id IS NULL OR p_qualifica_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_qualifica_id'),
            NULL::uuid, 'Qualifica obbligatoria.'
        );
    END IF;

    -- Guard prerequisiti
    IF NOT EXISTS (
        SELECT 1 FROM config.qualifiche
         WHERE id = p_qualifica_id AND attivo = true
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('qualifica_id', p_qualifica_id),
            NULL::uuid, 'Qualifica non trovata o non attiva.'
        );
    END IF;

    IF p_unita_organizzativa_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM config.unita_organizzative
             WHERE id = p_unita_organizzativa_id AND attivo = true
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_risorsa_umana',
                'E_ADMIN_UO_NON_TROVATA',
                jsonb_build_object('campo', 'unita_organizzativa_id', 'unita_organizzativa_id', p_unita_organizzativa_id),
                NULL::uuid,
                'Unita'' organizzativa non trovata o non attiva.'
            );
        END IF;
    END IF;

    -- ⛔ Il SUPER_ADMIN e' un privilegio della veste: senza credenziale non
    --   c'e' una veste a cui legarlo, e chiederlo non si ignora in silenzio.
    IF p_is_super_admin AND p_auth_user_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_is_super_admin'),
            NULL::uuid, 'Il profilo SUPER_ADMIN si da'' solo a chi ha una credenziale.'
        );
    END IF;

    v_valido_dal := COALESCE(p_valido_dal, (SELECT script.fn_data_operativa()));

    IF p_auth_user_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM django.auth_user WHERE id = p_auth_user_id
        ) THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_risorsa_umana',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('auth_user_id', p_auth_user_id),
                NULL::uuid, 'auth_user non trovato.'
            );
        END IF;
    END IF;

    -- ⛔ Il profilo SUPER_ADMIN si RISOLVE, non si scrive (rev 20260923-10):
    --   per tipo, fra i profili attivi, esattamente uno, PRIMA di ogni
    --   scrittura. ⭐ Dal 20261019-17 la regola sta nel lettore
    --   config.fn_profilo_super_admin_id (R-BE-11, regola del 2): era scritta
    --   qui e nel backend.
    IF p_is_super_admin AND p_auth_user_id IS NOT NULL THEN
        v_profilo_sa := config.fn_profilo_super_admin_id();
    END IF;

    -- ⛔ Una credenziale ha al piu' una veste OPERATORE, accesa O SPENTA:
    --   l'indice unico vale solo per le accese, e la veste nasce spenta.
    --   Il rimedio e' il (re)invito, come in anagrafiche.fn_crea_operatore.
    IF p_auth_user_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM anagrafiche.identita_digitali idg
         WHERE idg.auth_user_id = p_auth_user_id
           AND idg.ruolo_applicativo = 'OPERATORE'
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana',
            'E_CREDENZIALE_GIA_OPERATORE',
            jsonb_build_object('campo', 'email', 'auth_user_id', p_auth_user_id),
            NULL::uuid,
            COALESCE((SELECT NULLIF(btrim(au.email), '') FROM django.auth_user au
                       WHERE au.id = p_auth_user_id), '(senza email)'));
    END IF;

    -- Step 1: soggetto_ruolo RIS_UMANA
    SELECT script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id, 'RIS_UMANA'
    ) INTO v_sr_id;

    -- ⛔ Una persona e' una risorsa umana sola (uq_risorse_umane_soggetto_ruolo,
    --   non parziale: vale anche per una risorsa spenta). Senza questo guard il
    --   secondo operatore sullo stesso soggetto arrivava al client come 23505,
    --   E_DATABASE. Il rimedio e' sulla risorsa che c'e' (reinvito, riattivazione),
    --   non una seconda. (rev 20261002-01)
    -- ⚠️ Il controllo e' sulla CHIAVE del vincolo (soggetto_ruolo_id), non su
    --   attivo: una risorsa disattivata occupa lo slot come una attiva.
    -- ⚠️ Il segnaposto e' la frase dell'operatore: ragione_sociale_completa e'
    --   nullable, quindi si ripiega su nome e cognome, poi su «Il soggetto» —
    --   mai una frase con un buco al posto del nome.
    IF EXISTS (
        SELECT 1 FROM anagrafiche.risorse_umane ru
         WHERE ru.soggetto_ruolo_id = v_sr_id
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana',
            'E_RISORSA_UMANA_GIA_PRESENTE',
            jsonb_build_object('campo',             'soggetto_id',
                               'soggetto_id',       p_soggetto_id,
                               'soggetto_ruolo_id', v_sr_id),
            NULL::uuid,
            COALESCE(
                (SELECT COALESCE(NULLIF(btrim(s.ragione_sociale_completa), ''),
                                 NULLIF(btrim(concat_ws(' ', s.nome, s.cognome)), ''),
                                 NULLIF(btrim(s.ragione_sociale), ''))
                   FROM anagrafiche.soggetti s
                  WHERE s.id = p_soggetto_id),
                'Il soggetto'));
    END IF;

    -- Step 2: risorsa umana
    INSERT INTO anagrafiche.risorse_umane (
        soggetto_ruolo_id, soggetto_id, qualifica_id,
        unita_organizzativa_id, valido_dal, valido_al, attivo
    )
    VALUES (
        v_sr_id, p_soggetto_id, p_qualifica_id,
        p_unita_organizzativa_id, v_valido_dal, p_valido_al, true
    )
    RETURNING id INTO v_ru_id;

    -- Step 3: identita_digitali OPERATORE, accesa o spenta come dice
    -- il chiamante (default spenta).
    IF p_auth_user_id IS NOT NULL THEN
        INSERT INTO anagrafiche.identita_digitali (
            soggetto_ruolo_id,
            auth_user_id,
            ruolo_applicativo,
            attivo,
            valido_dal,
            valido_al
        )
        VALUES (
            v_sr_id,
            p_auth_user_id,
            'OPERATORE'::config.ruolo_applicativo,
            p_attivo,
            v_valido_dal,
            p_valido_al
        )
        RETURNING id INTO v_identita_id;

        -- Step 4: binding SUPER_ADMIN se richiesto, sul profilo
        -- risolto nei guard (rev 20260923-10: era l'id 9100 cablato).
        IF p_is_super_admin THEN
            -- La primitiva del legame: il permesso lo ha chiesto il verbo
            -- che arriva qui (o nessuno, sul primo impianto e nelle fixture).
            -- attivo = true e' il DEFAULT della colonna.
            PERFORM config.fn_applica_lega_profilo_identita(v_profilo_sa, v_identita_id);
        END IF;
    END IF;

    RETURN v_ru_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_risorsa_umana(p_soggetto_id uuid, p_qualifica_id integer, p_unita_organizzativa_id integer, p_valido_dal date, p_valido_al date, p_auth_user_id integer, p_is_super_admin boolean, p_attivo boolean)
IS 'Primitiva: crea il rapporto di lavoro (anagrafiche.risorse_umane, attivo, sul ruolo RIS_UMANA del soggetto) e, se riceve la credenziale, la veste OPERATORE, spenta per default (p_attivo): la accende l''attivazione dell''invito. Con p_is_super_admin lega alla veste il profilo SUPER_ADMIN (config.fn_profilo_super_admin_id, config.fn_applica_lega_profilo_identita). p_valido_dal NULL vale il giorno operativo, per il rapporto e per la veste. Rifiuta: soggetto o qualifica mancanti, qualifica o reparto non attivi, credenziale inesistente, SUPER_ADMIN senza credenziale (E_ADMIN_VALIDAZIONE, E_ADMIN_UO_NON_TROVATA); un soggetto che è già una risorsa umana (E_RISORSA_UMANA_GIA_PRESENTE); una credenziale che ha già una veste OPERATORE, accesa o spenta (E_CREDENZIALE_GIA_OPERATORE). È il passo interno di anagrafiche.fn_applica_crea_operatore: non chiede permessi, e l''applicazione non la esegue. Ritorna l''id della risorsa umana.';
```

</div>

---
{% include-markdown "signature-core.md" %}
