{% include-markdown "it/dbzero/script/manual/fn_get_user_profile.md" %}
# ⚙️ Funzione `fn_get_user_profile`

```sql
CREATE FUNCTION fn_get_user_profile(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_profile(p_auth_user_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- jsonb: oggetti composti qui, nessuna colonna dietro.
    v_result                  jsonb;
    v_utente                  jsonb;
    -- Blocco identita
    v_identita_id             anagrafiche.identita_digitali.id%TYPE;
    v_ruolo_applicativo       anagrafiche.identita_digitali.ruolo_applicativo%TYPE;
    v_ruolo_applicativo_out   text;  -- output top-level GUC-aware (§20260421-05): viene da una GUC (testo) o dal ruolo, non da una colonna sola
    v_is_super_admin          boolean;  -- esito di fn_is_super_admin: nessuna colonna dietro
    -- Blocco risorse_umane
    v_risorsa_umana_id        anagrafiche.risorse_umane.id%TYPE;
    v_soggetto_ruolo_id       anagrafiche.risorse_umane.soggetto_ruolo_id%TYPE;
    v_qualifica_id            anagrafiche.risorse_umane.qualifica_id%TYPE;
    v_uo_id                   anagrafiche.risorse_umane.unita_organizzativa_id%TYPE;
    v_valido_dal              anagrafiche.risorse_umane.valido_dal%TYPE;
    v_valido_al               anagrafiche.risorse_umane.valido_al%TYPE;
    v_ru_attivo               anagrafiche.risorse_umane.attivo%TYPE;
    v_risorse_umane           jsonb;
    -- Blocco soggetto
    v_soggetto                jsonb;
    -- Blocco emittente
    v_emittente               jsonb;
    -- Variabili emittente lookup
    v_uef_id                  config.user_emittenti_fiscali.id%TYPE;
    v_ef_id                   anagrafiche.emittenti_fiscali.id%TYPE;
    v_ef_uid                  anagrafiche.emittenti_fiscali.uid%TYPE;
    v_ef_codice               anagrafiche.emittenti_fiscali.codice%TYPE;
    -- ⚠️ Fase 1 cantiere emittente (2026-08-02): era
    --   `anagrafiche.emittenti_fiscali.descrizione%TYPE`, cioe' un
    --   riferimento alla colonna che la Fase 4 elimina. Un %TYPE
    --   non somiglia a una lettura della colonna ma lo e' a tutti
    --   gli effetti: lasciato li', la DROP fallirebbe lontano da
    --   qui. Ora `text`, che e' anche il tipo della nuova sorgente
    --   (anagrafiche.soggetti.ragione_sociale_completa).
    v_ef_descrizione          text;
    v_ef_sr_id                anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    v_ef_regime               anagrafiche.emittenti_fiscali.regime_fiscale_rf%TYPE;
    v_ef_valuta_id            anagrafiche.emittenti_fiscali.valuta_id%TYPE;
    -- Qualifica e UO risolti
    v_qualifica_codice          config.qualifiche.codice%TYPE;
    v_qualifica_codice_interno  config.qualifiche.codice_interno%TYPE;
    v_qualifica_descrizione     config.qualifiche.descrizione%TYPE;
    v_uo_codice                 config.unita_organizzative.codice%TYPE;
    v_uo_codice_interno         config.unita_organizzative.codice_interno%TYPE;
    v_uo_descrizione            config.unita_organizzative.descrizione%TYPE;
BEGIN
    -- =========================================================
    -- Scopo (post Fase 7 step 3, 29-04-2026):
    --   Profilo utente completo (JSONB) post-rimozione chiave
    --   'ruolo_sistema'. Source of truth invariato: identita
    --   OPERATORE + risorse_umane via soggetto_ruolo. Top-level
    --   ruolo_applicativo GUC-aware (20260421-05); top-level
    --   is_super_admin context-aware (20260421-03).
    --
    -- ⭐ Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1):
    --   la veste OPERATORE e' quella di riferimento della credenziale
    --   (script.fn_veste_di_riferimento: l'accesa, o la spenta piu'
    --   recente), non una qualunque. Fino a R-DB-1 lo spegnimento
    --   scriveva DISABILITATO e le vesti spente uscivano dal JOIN da
    --   sole; ora restano OPERATORE, e un JOIN nudo poteva prendere la
    --   spenta accanto all'accesa e rifiutare il login. «Disabilitato»
    --   si legge solo da attivo.
    -- =========================================================

    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_profile',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'p_auth_user_id obbligatorio e > 0.'
        );
    END IF;

    -- 1. Query accorpata: auth_user + identita_digitali
    --    (OPERATORE) + risorse_umane + qualifica + UO.
    SELECT jsonb_build_object(
               'auth_user_id', au.id,
               'username',     au.username,
               'first_name',   au.first_name,
               'last_name',    au.last_name,
               'email',        au.email
           ),
           id.id,
           id.ruolo_applicativo,
           ru.id,
           ru.soggetto_ruolo_id,
           ru.qualifica_id,
           ru.unita_organizzativa_id,
           ru.valido_dal,
           ru.valido_al,
           ru.attivo,
           q.codice,
           q.codice_interno,
           q.descrizione,
           uo.codice,
           uo.codice_interno,
           uo.descrizione
      INTO v_utente,
           v_identita_id,
           v_ruolo_applicativo,
           v_risorsa_umana_id,
           v_soggetto_ruolo_id,
           v_qualifica_id,
           v_uo_id,
           v_valido_dal,
           v_valido_al,
           v_ru_attivo,
           v_qualifica_codice,
           v_qualifica_codice_interno,
           v_qualifica_descrizione,
           v_uo_codice,
           v_uo_codice_interno,
           v_uo_descrizione
      FROM django.auth_user au
      LEFT JOIN anagrafiche.identita_digitali id
        ON id.id = script.fn_veste_di_riferimento(
                       au.id, 'OPERATORE'::config.ruolo_applicativo)
      LEFT JOIN anagrafiche.risorse_umane ru
        ON ru.soggetto_ruolo_id = id.soggetto_ruolo_id
      LEFT JOIN config.qualifiche q
        ON q.id = ru.qualifica_id
      LEFT JOIN config.unita_organizzative uo
        ON uo.id = ru.unita_organizzativa_id
     WHERE au.id = p_auth_user_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_profile',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'auth_user con id=' || p_auth_user_id || ' non trovato.'
        );
    END IF;

    IF v_identita_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_profile',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'Nessuna identita OPERATORE per auth_user_id=' || p_auth_user_id || '.'
        );
    END IF;

    IF v_soggetto_ruolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_profile',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('identita_id', v_identita_id),
            NULL::uuid,
            'Nessun record risorse_umane per identita id=' || v_identita_id || '.'
        );
    END IF;

    -- Guard: veste OPERATORE non utilizzabile oggi.
    -- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile, D-4): un controllo
    --   solo, sul building block script.fn_veste_utilizzabile (veste accesa
    --   e nelle sue date, soggetto attivo, rapporto attivo e nelle sue
    --   date). Prima qui c'erano sei guard ricopiati, con un codice per la
    --   veste spenta e due per le date (non ancora valida, scaduta): la
    --   data non cambia cosa fa chi non entra (chiede all'amministratore,
    --   che le date le vede nel dettaglio), e i due codici delle date sono
    --   ritirati. Spenta o fuori date e' lo stesso esito.
    -- ⚠️ Dopo il controllo della risorsa umana mancante: un operatore senza
    --   rapporto e' un difetto di dati (E_ADMIN_VALIDAZIONE), non un accesso
    --   chiuso, e il building block lo darebbe solo come «non utilizzabile».
    -- ⭐ Il segnaposto e' lo username: e' la cosa che chi prova ad accedere
    --   riconosce.
    IF NOT script.fn_veste_utilizzabile(v_identita_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_profile',
            'E_UTENTE_DISABILITATO',
            jsonb_build_object(
                'auth_user_id', p_auth_user_id,
                'identita_id', v_identita_id,
                'risorsa_umana_id', v_risorsa_umana_id
            ),
            NULL::uuid,
            v_utente ->> 'username'
        );
    END IF;

    -- is_super_admin top-level (GUC-aware via fn_is_super_admin).
    v_is_super_admin := script.fn_is_super_admin(p_auth_user_id);

    -- Top-level ruolo_applicativo: GUC-first (veste del JWT
    -- corrente), fallback al ruolo dell'identita OPERATORE.
    v_ruolo_applicativo_out := COALESCE(
        NULLIF(current_setting('app.ruolo_applicativo', true), ''),
        v_ruolo_applicativo::text
    );

    v_risorse_umane := jsonb_build_object(
        'risorsa_umana_id',                v_risorsa_umana_id,
        'soggetto_ruolo_id',               v_soggetto_ruolo_id,
        'qualifica_id',                    v_qualifica_id,
        'qualifica_codice',                v_qualifica_codice,
        'qualifica_codice_interno',        v_qualifica_codice_interno,
        'qualifica_descrizione',           v_qualifica_descrizione,
        'unita_organizzativa_id',          v_uo_id,
        'unita_organizzativa_codice',      v_uo_codice,
        'unita_organizzativa_codice_interno', v_uo_codice_interno,
        'unita_organizzativa_descrizione', v_uo_descrizione,
        'valido_dal',                      v_valido_dal,
        'valido_al',                       v_valido_al,
        'attivo',                          v_ru_attivo
    );

    -- 2. Blocco soggetto via fn_get_soggetto_dati_by_ruolo
    SELECT row_to_json(t.*)::jsonb
      INTO v_soggetto
      FROM script.fn_get_soggetto_dati_by_ruolo(v_soggetto_ruolo_id) t;

    -- 3. Risolve emittente fiscale (priorita' whitelist -> gestore)
    --    ⚠️ Fase 1 cantiere emittente (2026-08-02):
    --    emittente_descrizione viene dalla ragione sociale del
    --    SOGGETTO dell'emittente, non piu' da ef.descrizione. I
    --    due rami del UNION ALL joinano entrambi soggetti_ruoli ->
    --    soggetti: il tipo resta text in tutti e due, quindi il
    --    UNION non cambia forma.
    v_emittente := NULL;

    SELECT x.user_emittente_fiscale_id,
           x.emittente_fiscale_id,
           x.emittente_fiscale_uid,
           x.emittente_codice,
           x.emittente_descrizione,
           x.emittente_soggetto_ruolo_id,
           x.regime_fiscale_rf,
           x.valuta_id
      INTO v_uef_id,
           v_ef_id,
           v_ef_uid,
           v_ef_codice,
           v_ef_descrizione,
           v_ef_sr_id,
           v_ef_regime,
           v_ef_valuta_id
      FROM (
          SELECT *
            FROM (
                SELECT 1 AS priorita,
                       uef.id  AS user_emittente_fiscale_id,
                       ef.id   AS emittente_fiscale_id,
                       ef.uid  AS emittente_fiscale_uid,
                       ef.codice AS emittente_codice,
                       s_ef.ragione_sociale_completa AS emittente_descrizione,
                       ef.soggetto_ruolo_id AS emittente_soggetto_ruolo_id,
                       ef.regime_fiscale_rf,
                       ef.valuta_id
                  FROM config.user_emittenti_fiscali uef
                  JOIN anagrafiche.emittenti_fiscali ef
                    ON ef.id = uef.emittente_fiscale_id
                  LEFT JOIN anagrafiche.soggetti_ruoli sr_ef
                    ON sr_ef.id = ef.soggetto_ruolo_id
                  LEFT JOIN anagrafiche.soggetti s_ef
                    ON s_ef.id = sr_ef.soggetto_id
                 WHERE uef.auth_user_id = p_auth_user_id
                   AND ef.attivo = true
                 ORDER BY uef.id
                 LIMIT 1
            ) whitelist

          UNION ALL

          SELECT *
            FROM (
                SELECT 2 AS priorita,
                       NULL::bigint AS user_emittente_fiscale_id,
                       ef.id   AS emittente_fiscale_id,
                       ef.uid  AS emittente_fiscale_uid,
                       ef.codice AS emittente_codice,
                       s_ef.ragione_sociale_completa AS emittente_descrizione,
                       ef.soggetto_ruolo_id AS emittente_soggetto_ruolo_id,
                       ef.regime_fiscale_rf,
                       ef.valuta_id
                  FROM anagrafiche.emittenti_fiscali_billing_account efba
                  JOIN anagrafiche.emittenti_fiscali ef
                    ON ef.soggetto_ruolo_id = efba.emittente_soggetto_ruolo_id
                  LEFT JOIN anagrafiche.soggetti_ruoli sr_ef
                    ON sr_ef.id = ef.soggetto_ruolo_id
                  LEFT JOIN anagrafiche.soggetti s_ef
                    ON s_ef.id = sr_ef.soggetto_id
                 WHERE efba.billing_account_id IS NULL
                   AND efba.is_default = true
                   AND ef.attivo = true
                 LIMIT 1
            ) fallback
      ) x
     ORDER BY x.priorita
     LIMIT 1;

    IF v_ef_id IS NOT NULL THEN
        DECLARE
            v_ef_soggetto jsonb;  -- riga di una funzione resa jsonb: nessuna colonna dietro
        BEGIN
            SELECT row_to_json(t.*)::jsonb
              INTO v_ef_soggetto
              FROM script.fn_get_soggetto_dati_by_ruolo(v_ef_sr_id) t;

            v_emittente := jsonb_build_object(
                'emittente_fiscale_id',      v_ef_id,
                'emittente_fiscale_uid',     v_ef_uid,
                'emittente_codice',          v_ef_codice,
                'emittente_descrizione',     v_ef_descrizione,
                'user_emittente_fiscale_id', v_uef_id,
                'regime_fiscale_rf',         v_ef_regime,
                'valuta_id',                 v_ef_valuta_id
            ) || COALESCE(v_ef_soggetto, '{}'::jsonb);
        END;
    END IF;

    -- 4. Risultato finale (post-rimozione chiave 'ruolo_sistema').
    v_result := jsonb_build_object(
        'utente',                   v_utente,
        'is_super_admin',           v_is_super_admin,
        'ruolo_applicativo',        v_ruolo_applicativo_out,
        'risorse_umane',            v_risorse_umane,
        'soggetto',                 v_soggetto,
        'emittente',                v_emittente,
        'permessi_area',            script.fn_get_user_permissions_map(p_auth_user_id),
        'azioni_abilitate',         script.fn_get_user_actions_map(p_auth_user_id),
        'permessi_oggetto',         script.fn_get_user_object_permissions_map(p_auth_user_id),
        -- rev 2026-09-25 (D-7): il flag e' della CREDENZIALE, e il default
        -- dell'assenza vive solo in fn_get_deve_cambiare_password.
        'deve_cambiare_password',   script.fn_get_deve_cambiare_password(p_auth_user_id)
    );

    RETURN v_result;
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_profile(p_auth_user_id integer)
IS 'Profilo utente completo (JSONB). Post Fase 7 step 3 (29-04-2026): rimossa la chiave ruolo_sistema dall''output - BE post-Fase 7 LANDED non la legge piu''. Top-level ruolo_applicativo GUC-aware (20260421-05); is_super_admin context-aware (20260421-03/04). Richiede identita OPERATORE (raise E_ADMIN_VALIDAZIONE altrimenti). La chiave emittente.emittente_descrizione porta la ragione_sociale_completa del soggetto emittente (Fase 1 cantiere emittente 2026-08-02: prima leggeva emittenti_fiscali.descrizione nuda, cioe'' l''etichetta interna). La chiave deve_cambiare_password e'' della CREDENZIALE (D-7, rev 2026-09-25): si legge da script.fn_get_deve_cambiare_password, non piu'' dall''identita OPERATORE. ⭐ Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): la veste OPERATORE e'' quella di riferimento della credenziale (script.fn_veste_di_riferimento: l''accesa, o la spenta piu'' recente), non una qualunque; spenta si legge solo da attivo (E_UTENTE_DISABILITATO), DISABILITATO non esiste piu'' nella tabella viva. Il segnaposto di E_UTENTE_DISABILITATO e'' lo username. Rev 2026-10-07 (brief-db-veste-utilizzabile, D-4): un solo guard, «la veste OPERATORE e'' utilizzabile oggi» (script.fn_veste_utilizzabile: veste accesa e nelle sue date, soggetto attivo, rapporto attivo e nelle sue date), con un solo codice, E_UTENTE_DISABILITATO; i due codici delle date sono ritirati. La risorsa umana mancante resta E_ADMIN_VALIDAZIONE e viene prima.';
```

</div>

---
{% include-markdown "signature-core.md" %}
