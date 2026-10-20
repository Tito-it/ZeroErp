{% include-markdown "it/dbzero/script/manual/fn_get_user_object_permissions_map.md" %}
# ⚙️ Funzione `fn_get_user_object_permissions_map`

```sql
CREATE FUNCTION fn_get_user_object_permissions_map(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_object_permissions_map(p_auth_user_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Mappa dei livelli EFFETTIVI degli oggetti del catalogo per
    --   un utente, in un solo roundtrip (alimenta /me/ ->
    --   permessi_oggetto).
    --
    -- Ritorna:
    --   JSONB { "anagrafiche.conto_bancario": "BLOCCATO",
    --           "vendite.fattura": "LETTURA", ... }
    --
    -- Regole (rev 20261004-58, brief-db-permessi-tetto-area R5):
    --   - una chiave per ogni oggetto di config.area_model_overrides
    --     (il catalogo: un override esiste solo per un suo oggetto);
    --   - il valore e' il livello col tetto d'area, dalla sede comune
    --     script.fn_get_permessi_effettivi_oggetti, non piu' l'override
    --     grezzo: il frontend LEGGE, non ricalcola la catena;
    --   - un oggetto fuori catalogo vale la sua area di app_label
    --     (la regola di fn_area_di_oggetto).
    -- =========================================================

    -- Guard: parametro obbligatorio e valido
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_user_object_permissions_map',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_auth_user_id', p_auth_user_id),
            NULL::uuid,
            'p_auth_user_id obbligatorio e > 0.'
        );
    END IF;

    RETURN (
        SELECT COALESCE(
            jsonb_object_agg(e.app_label || '.' || e.model_name, e.livello::text),
            '{}'::jsonb
        )
          FROM script.fn_get_permessi_effettivi_oggetti(p_auth_user_id) e
    );
END;
$function$

COMMENT ON FUNCTION script.fn_get_user_object_permissions_map(p_auth_user_id integer)
IS 'Mappa dei livelli EFFETTIVI degli oggetti per un utente ({"app_label.model_name": livello}), una chiave per ogni oggetto del catalogo config.area_model_overrides. Il valore e'' il livello col tetto d''area (il piu'' restrittivo fra override valido e area dell''oggetto), letto da script.fn_get_permessi_effettivi_oggetti, la stessa catena di script.fn_resolve_livello_oggetto: gate di contesto e identita'' OPERATORE assente -> BLOCCATO, super admin -> TUTTO. Un oggetto fuori catalogo vale la sua area di app_label (la regola di script.fn_area_di_oggetto). Alimenta /me/ -> permessi_oggetto (fn_get_user_profile): il frontend legge, non ricalcola. Rev 20261004-58 (brief-db-permessi-tetto-area R5): fino a questa revisione restituiva i soli override grezzi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
