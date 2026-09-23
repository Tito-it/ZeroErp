{% include-markdown "it/dbzero/anagrafiche/manual/fn_crea_risorsa_umana_v2.md" %}
# ⚙️ Funzione `fn_crea_risorsa_umana_v2`

```sql
CREATE FUNCTION fn_crea_risorsa_umana_v2(p_soggetto_id uuid, p_qualifica_id integer, p_unita_organizzativa_id integer, p_valido_dal date, p_valido_al date, p_auth_user_id integer, p_is_super_admin boolean, p_attivo boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_risorsa_umana_v2(p_soggetto_id uuid DEFAULT NULL::uuid, p_qualifica_id integer DEFAULT NULL::integer, p_unita_organizzativa_id integer DEFAULT NULL::integer, p_valido_dal date DEFAULT CURRENT_DATE, p_valido_al date DEFAULT NULL::date, p_auth_user_id integer DEFAULT NULL::integer, p_is_super_admin boolean DEFAULT false, p_attivo boolean DEFAULT true)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sr_id        anagrafiche.soggetti_ruoli.id%TYPE;
    v_ru_id        anagrafiche.risorse_umane.id%TYPE;
    v_identita_id  anagrafiche.identita_digitali.id%TYPE;
    v_profilo_sa   config.profili_accesso_bindings.profilo_accesso_id%TYPE;
    v_n_profili_sa integer;
BEGIN
    -- =========================================================
    -- Scopo (v2 multi-face native, Chunk A Fase 7 2026-04-29):
    --   Crea risorsa_umana + identita_digitali OPERATORE
    --   (+ binding SUPER_ADMIN se p_is_super_admin=true).
    --   Niente piu' enum legacy ruolo_sistema; il chiamante
    --   esprime direttamente "is super admin?" + "attiva?".
    --
    -- Body identico a v1 salvo:
    --   Step 3: identita_digitali.attivo = p_attivo
    --           (era hardcoded true in v1).
    --   Step 4: IF p_is_super_admin invece di
    --           IF p_ruolo_sistema='ADMIN'.
    -- =========================================================

    -- Validazione parametri obbligatori
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_soggetto_id'),
            NULL::uuid, 'Soggetto obbligatorio.'
        );
    END IF;

    IF p_qualifica_id IS NULL OR p_qualifica_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
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
            'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
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
                'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
                'E_ADMIN_UO_NON_TROVATA',
                jsonb_build_object('campo', 'unita_organizzativa_id', 'unita_organizzativa_id', p_unita_organizzativa_id),
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
                'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
                'E_ADMIN_VALIDAZIONE',
                jsonb_build_object('auth_user_id', p_auth_user_id),
                NULL::uuid, 'auth_user non trovato.'
            );
        END IF;
    END IF;

    -- ⛔ Il profilo SUPER_ADMIN si RISOLVE, non si scrive (rev 20260923-10).
    --   Fino a questa revisione il binding usava l'id cablato 9100: vero solo
    --   perche' il seed di config.profili_accesso porta l'id esplicito. La
    --   chiave stabile e' l'enum `tipo` (linee-guida-sql §6d, punto 1: e' la
    --   stessa dei guard anti-lockout e di script.fn_is_super_admin); `codice`
    --   e' modificabile e non ha lock.
    -- ⚠️ Il modello non vieta DUE profili di tipo SUPER_ADMIN, e sceglierne uno
    --   per id sarebbe un'ambiguita', non una scelta: si pretende esattamente
    --   un profilo attivo, e si solleva PRIMA di ogni scrittura.
    IF p_is_super_admin AND p_auth_user_id IS NOT NULL THEN
        SELECT count(*), min(pa.id)
          INTO v_n_profili_sa, v_profilo_sa
          FROM config.profili_accesso pa
         WHERE pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
           AND pa.attivo;

        IF v_n_profili_sa <> 1 THEN
            PERFORM script.fn_log_and_raise_error(
                'database', 'anagrafiche.fn_crea_risorsa_umana_v2',
                'E_CONFIG_MANCANTE',
                jsonb_build_object('tipo_profilo_accesso', 'SUPER_ADMIN',
                                   'profili_attivi', v_n_profili_sa),
                NULL::uuid,
                'un solo profilo di accesso SUPER_ADMIN attivo (trovati '
                    || v_n_profili_sa::text || ')'
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

    -- Step 3: identita_digitali OPERATORE.
    -- Differenza vs v1: attivo = p_attivo (default true).
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
            COALESCE(p_valido_dal, CURRENT_DATE),
            p_valido_al
        )
        RETURNING id INTO v_identita_id;

        -- Step 4: binding SUPER_ADMIN se richiesto, sul profilo
        -- risolto nei guard (rev 20260923-10: era l'id 9100 cablato).
        -- Differenza vs v1: predicato boolean diretto invece
        -- di confronto con enum legacy.
        IF p_is_super_admin THEN
            INSERT INTO config.profili_accesso_bindings (
                profilo_accesso_id,
                identita_digitale_id,
                attivo
            )
            VALUES (
                v_profilo_sa,
                v_identita_id,
                true
            );
        END IF;
    END IF;

    RETURN v_ru_id;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_crea_risorsa_umana_v2(p_soggetto_id uuid, p_qualifica_id integer, p_unita_organizzativa_id integer, p_valido_dal date, p_valido_al date, p_auth_user_id integer, p_is_super_admin boolean, p_attivo boolean)
IS 'Building block multi-face native (v2 Chunk A Fase 7 2026-04-29). Sostituisce v1 (firma con p_ruolo_sistema config.ruolo_sistema) con p_is_super_admin/p_attivo. Body invariato salvo: identita_digitali.attivo=p_attivo (era hardcoded true) e binding SUPER_ADMIN gated su p_is_super_admin invece di p_ruolo_sistema=ADMIN. v1 droppata in Chunk B post BE migrato. ⛔ Rev 20260923-10: il profilo del binding SUPER_ADMIN si RISOLVE per config.profili_accesso.tipo = SUPER_ADMIN fra i profili attivi (chiave stabile, linee-guida-sql §6d), non piu'' con l''id cablato 9100; se i profili attivi di quel tipo non sono esattamente uno solleva E_CONFIG_MANCANTE prima di ogni scrittura.';
```

---
{% include-markdown "signature-core.md" %}
