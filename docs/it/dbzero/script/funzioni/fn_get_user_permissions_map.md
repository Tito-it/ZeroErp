{% include-markdown "it/dbzero/script/manual/fn_get_user_permissions_map.md" %}
# ⚙️ Funzione `fn_get_user_permissions_map`

```sql
CREATE FUNCTION fn_get_user_permissions_map(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_permissions_map(p_auth_user_id integer)
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
    --   Restituisce la mappa livello accesso per tutte le aree
    --   funzionali attive, in un solo roundtrip DB.
    --
    -- Ritorna:
    --   JSONB { "anagrafiche": "TUTTO", "vendite": "LETTURA", ... }
    --
    -- Catena (refactor §4.6.B.8):
    --   1. Assenza identita OPERATORE attiva -> tutte BLOCCATO
    --   2. fn_is_super_admin -> tutte TUTTO
    --   3. Override utente area + profilo reparto (legacy)
    --   4. Default -> BLOCCATO
    -- =========================================================

    -- Guard: parametro obbligatorio
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_permissions_map',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'p_auth_user_id obbligatorio e > 0.'
        );
    END IF;

    -- 1. Identita OPERATORE attiva (helper DRY §4.6.B.0).
    --    Pre-calcolata per uso nel CASE della jsonb_object_agg
    --    (una sola chiamata invece di una per riga).
    v_has_identita := script.fn_has_identita_attiva(
                          p_auth_user_id,
                          'OPERATORE'::config.ruolo_applicativo);

    -- 2. Super admin flag (pre-calcolato per uso nel CASE)
    v_is_super := script.fn_is_super_admin(p_auth_user_id);

    -- 3. UO per la catena profili_reparto (legacy RUA).
    --    Nota §4.8: quando generalizziamo il resolver su
    --    profili_accesso, questa JOIN diventera' lookup su
    --    bindings identita -> profili REPARTO.
    SELECT ru.unita_organizzativa_id
      INTO v_uo_id
      FROM anagrafiche.risorse_umane_auth_user rau
      JOIN anagrafiche.risorse_umane ru
        ON ru.id = rau.risorsa_umana_id
     WHERE rau.auth_user_id = p_auth_user_id;

    RETURN (
        SELECT COALESCE(
            jsonb_object_agg(
                af.schema_db,
                CASE
                    WHEN NOT v_has_identita
                        THEN 'BLOCCATO'
                    WHEN v_is_super
                        THEN 'TUTTO'
                    ELSE COALESCE(
                        uoa.livello,
                        pra.livello,
                        'BLOCCATO'::config.livello_accesso
                    )::text
                END
            ),
            '{}'::jsonb
        )
          FROM config.aree_funzionali af
          LEFT JOIN config.user_override_aree uoa
            ON uoa.auth_user_id = p_auth_user_id
           AND uoa.area_id = af.id
           AND uoa.validita @> CURRENT_DATE
          LEFT JOIN config.profili_reparto_aree pra
            ON pra.unita_organizzativa_id = v_uo_id
           AND pra.area_id = af.id
         WHERE af.attivo = TRUE
    );
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_permissions_map(p_auth_user_id integer)
IS 'Mappa permessi aree set-based. Refactor §4.6.B.8: gate identita OPERATORE attiva, bypass fn_is_super_admin, catena override+reparto legacy invariata (rinvio §4.8).';
```

---
{% include-markdown "signature-core.md" %}
