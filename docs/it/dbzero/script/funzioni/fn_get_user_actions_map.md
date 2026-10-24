{% include-markdown "it/dbzero/script/manual/fn_get_user_actions_map.md" %}
# ⚙️ Funzione `fn_get_user_actions_map`

```sql
CREATE FUNCTION fn_get_user_actions_map(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_actions_map(p_auth_user_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Mappa azioni_processo abilitate/disabilitate
    --   (single roundtrip). JSONB { "perm_codename": bool, ... }.
    --
    -- Catena (rev 20261004-56, brief-db-permessi-tetto-area):
    --   la legge da script.fn_get_permessi_effettivi_azioni, sede
    --   unica con fn_check_azione_processo: gate di contesto,
    --   identita', super admin, override -> profilo -> negata, e il
    --   tetto d'area. Qui solo le azioni attive.
    -- =========================================================

    -- 1. Guard parametro obbligatorio.
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_actions_map',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'p_auth_user_id obbligatorio e > 0.'
        );
    END IF;

    -- 2. Aggregazione dalla sede comune.
    RETURN (
        SELECT COALESCE(
            jsonb_object_agg(e.permission_codename, e.abilitata),
            '{}'::jsonb
        )
          FROM script.fn_get_permessi_effettivi_azioni(p_auth_user_id) e
         WHERE e.attivo = TRUE
    );
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_actions_map(p_auth_user_id integer)
IS 'Mappa delle azioni di processo di un utente, tutte le azioni attive in una chiamata ({permission_codename: bool}). Legge la catena da script.fn_get_permessi_effettivi_azioni, la stessa di script.fn_check_azione_processo: gate di contesto (veste diversa da OPERATORE -> tutto false), identita'' OPERATORE attiva, super admin -> true, override utente, ereditato dal profilo, default negata, e il TETTO D''AREA (livello_minimo_area dell''azione, script.fn_area_consente_azione). Rev 20261004-56 (brief-db-permessi-tetto-area R3): la catena non si riscrive qui.';
```

</div>

---
{% include-markdown "signature-core.md" %}
