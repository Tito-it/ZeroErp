{% include-markdown "it/dbzero/script/manual/fn_get_user_actions_map.md" %}
# ⚙️ Funzione `fn_get_user_actions_map`

```sql
CREATE FUNCTION fn_get_user_actions_map(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_actions_map(p_auth_user_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_has_identita  boolean;
    v_is_super      boolean;
    v_uo_id         anagrafiche.risorse_umane.unita_organizzativa_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Ritorna la mappa completa delle azioni di processo
    --   abilitate/disabilitate per l'utente.
    --
    -- Ritorna:
    --   JSONB {"genera_fatture_lotti": true,
    --          "reset_lotto_draft": false, ...}
    --
    -- Catena (refactor §4.6.B.9):
    --   1. Assenza identita OPERATORE attiva -> tutte false
    --   2. fn_is_super_admin -> tutte true
    --   3. Override utente azione + profilo reparto (legacy)
    --   4. Default -> false
    -- =========================================================

    -- Guard: parametro obbligatorio e valido
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_actions_map',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'p_auth_user_id obbligatorio e > 0.'
        );
    END IF;

    -- 1. Identita OPERATORE attiva (helper DRY §4.6.B.0).
    --    Pre-calcolata per uso nel CASE della jsonb_object_agg.
    v_has_identita := script.fn_has_identita_attiva(
                          p_auth_user_id,
                          'OPERATORE'::config.ruolo_applicativo);

    -- 2. Super admin flag
    v_is_super := script.fn_is_super_admin(p_auth_user_id);

    -- 3. UO per la catena profili_reparto (legacy RUA)
    SELECT ru.unita_organizzativa_id
      INTO v_uo_id
      FROM anagrafiche.risorse_umane_auth_user rau
      JOIN anagrafiche.risorse_umane ru
        ON ru.id = rau.risorsa_umana_id
     WHERE rau.auth_user_id = p_auth_user_id;

    RETURN (
        SELECT COALESCE(
            jsonb_object_agg(
                ap.permission_codename,
                CASE
                    WHEN NOT v_has_identita
                        THEN false
                    WHEN v_is_super
                        THEN true
                    ELSE COALESCE(
                        uoa.abilitata,
                        pra.abilitata,
                        false
                    )
                END
            ),
            '{}'::jsonb
        )
          FROM config.azioni_processo ap
          LEFT JOIN config.user_override_azioni uoa
            ON uoa.auth_user_id = p_auth_user_id
           AND uoa.azione_id = ap.id
           AND uoa.validita @> CURRENT_DATE
          LEFT JOIN config.profili_reparto_azioni pra
            ON pra.unita_organizzativa_id = v_uo_id
           AND pra.azione_id = ap.id
         WHERE ap.attivo = TRUE
    );
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_actions_map(p_auth_user_id integer)
IS 'Mappa azioni processo set-based. Refactor §4.6.B.9: gate identita OPERATORE attiva, bypass fn_is_super_admin, catena override+reparto legacy invariata (rinvio §4.8).';
```

---
{% include-markdown "signature-core.md" %}
