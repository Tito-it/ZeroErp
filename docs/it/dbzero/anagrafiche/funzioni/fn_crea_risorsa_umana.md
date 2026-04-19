{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_risorsa_umana.md" %}
# ⚙️ Funzione `fn_crea_risorsa_umana`

```sql
CREATE FUNCTION fn_crea_risorsa_umana(p_soggetto_id uuid, p_qualifica_id integer, p_unita_organizzativa_id integer, p_valido_dal date, p_valido_al date, p_auth_user_id integer, p_ruolo_sistema config.ruolo_sistema)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_risorsa_umana(p_soggetto_id uuid DEFAULT NULL::uuid, p_qualifica_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_valido_dal date DEFAULT CURRENT_DATE, p_valido_al date DEFAULT NULL::date, p_auth_user_id integer DEFAULT NULL::integer, p_ruolo_sistema config.ruolo_sistema DEFAULT 'OPERATIVO'::config.ruolo_sistema)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sr_id  anagrafiche.soggetti_ruoli.id%TYPE;
    v_ru_id  anagrafiche.risorse_umane.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo (refactor §4.6.D.3):
    --   Crea risorsa_umana + bridge legacy RUA. Il trigger
    --   trgfn_risorse_umane_auth_user_sync_identita (§4.6.D.4)
    --   scatta AFTER INSERT su RUA e propaga a
    --   identita_digitali OPERATORE + binding SUPER_ADMIN
    --   (se ruolo_sistema='ADMIN'). Al cutover §4.6.H la
    --   propagazione verra' fatta direttamente qui.
    --
    -- Parametri (invariati): vedi COMMENT.
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
                jsonb_build_object('unita_organizzativa_id', p_unita_organizzativa_id),
                NULL::uuid,
                'Unita'' organizzativa non trovata o non attiva.'
            );
        END IF;
    END IF;

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

    -- Step 1: soggetto_ruolo RIS_UMANA
    SELECT script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id, 'RIS_UMANA'
    ) INTO v_sr_id;

    -- Step 2: risorsa umana
    INSERT INTO anagrafiche.risorse_umane (
        soggetto_ruolo_id, soggetto_id, qualifica_id,
        unita_organizzativa_id, valido_dal, valido_al, attivo
    )
    VALUES (
        v_sr_id, p_soggetto_id, p_qualifica_id,
        p_unita_organizzativa_id, p_valido_dal, p_valido_al, true
    )
    RETURNING id INTO v_ru_id;

    -- Step 3: Bridge legacy RUA. Il trigger-ponte §4.6.D.4
    -- (trgfn_risorse_umane_auth_user_sync_identita) propaga
    -- AFTER INSERT su identita_digitali OPERATORE (UPSERT)
    -- e crea il binding SUPER_ADMIN se p_ruolo_sistema='ADMIN'.
    -- NOTA: questo evita la collisione UNIQUE
    -- uq_identita_digitali_auth_user che si avrebbe con
    -- doppio INSERT esplicito + trigger-ponte.
    IF p_auth_user_id IS NOT NULL THEN
        INSERT INTO anagrafiche.risorse_umane_auth_user (
            risorsa_umana_id, auth_user_id, ruolo_sistema, attivo
        )
        VALUES (v_ru_id, p_auth_user_id, p_ruolo_sistema, true);
    END IF;

    RETURN v_ru_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_risorsa_umana(p_soggetto_id uuid, p_qualifica_id integer, p_unita_organizzativa_id integer, p_valido_dal date, p_valido_al date, p_auth_user_id integer, p_ruolo_sistema config.ruolo_sistema)
IS 'Building block: crea risorsa_umana + bridge legacy RUA. Refactor §4.6.D.3: la propagazione a identita_digitali + binding SUPER_ADMIN avviene via trigger-ponte §4.6.D.4. Firma esterna invariata. Al cutover §4.6.H la funzione tornera'' a scrivere direttamente su identita_digitali.';
```

---
{% include-markdown "signature-core.md" %}
