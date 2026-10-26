{% include-markdown "it/dbzero/script/manual/fn_resolve_livello_area.md" %}
# ⚙️ Funzione `fn_resolve_livello_area`

```sql
CREATE FUNCTION fn_resolve_livello_area(p_auth_user_id integer, p_area_schema_db character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_livello_area(p_auth_user_id integer, p_area_schema_db character varying)
 RETURNS config.livello_accesso
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_livello    config.user_override_aree.livello%TYPE;
    v_ctx_ruolo  anagrafiche.identita_digitali.ruolo_applicativo%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Risolve livello accesso area per un'area funzionale.
    --
    -- Catena (context-aware dal 21-04-2026):
    --   0. Gate GUC: se app.ruolo_applicativo popolata e
    --      != OPERATORE -> BLOCCATO (fail-closed).
    --   1. Assenza identita OPERATORE attiva -> BLOCCATO
    --   2. fn_is_super_admin -> TUTTO
    --   3. Override utente area (se valido temporalmente)
    --   4. Ereditato dal profilo: fn_get_permessi_ereditati_aree
    --      (sola veste OPERATORE; AD_HOC 1 > REPARTO 2 > PORTALE 3)
    --   5. Default -> BLOCCATO
    -- Rev 20260925-83: il passo 4 non riscrive lo spareggio, lo
    -- legge dal building block (sede unica, D-2) — e con esso la
    -- veste OPERATORE (D-1): prima contavano i profili di tutte le
    -- vesti dell'utente.
    -- =========================================================

    -- 0. Gate contesto GUC (fail-closed su non-OPERATORE).
    v_ctx_ruolo := NULLIF(
        current_setting('app.ruolo_applicativo', true), ''
    )::config.ruolo_applicativo;

    IF v_ctx_ruolo IS NOT NULL
       AND v_ctx_ruolo <> 'OPERATORE'::config.ruolo_applicativo THEN
        RETURN 'BLOCCATO'::config.livello_accesso;
    END IF;

    -- 1. Identita OPERATORE attiva (helper DRY).
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN 'BLOCCATO'::config.livello_accesso;
    END IF;

    -- 2. Super admin? Bypass totale.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN 'TUTTO'::config.livello_accesso;
    END IF;

    -- 3. Override utente area (invariato).
    SELECT uoa.livello
      INTO v_livello
      FROM config.user_override_aree uoa
      JOIN config.aree_funzionali af ON af.id = uoa.area_id
     WHERE uoa.auth_user_id = p_auth_user_id
       AND af.schema_db = p_area_schema_db
       AND uoa.validita @> (SELECT script.fn_data_operativa());

    IF FOUND THEN
        RETURN v_livello;
    END IF;

    -- 4. Ereditato dal profilo: una riga al massimo per area
    --    (DISTINCT ON nel building block, schema_db unico).
    SELECT e.livello
      INTO v_livello
      FROM script.fn_get_permessi_ereditati_aree(p_auth_user_id) e
      JOIN config.aree_funzionali af
        ON af.id = e.area_id
     WHERE af.schema_db = p_area_schema_db;

    IF FOUND THEN
        RETURN v_livello;
    END IF;

    -- 5. Default sicuro.
    RETURN 'BLOCCATO'::config.livello_accesso;
END
$function$

COMMENT ON FUNCTION script.fn_resolve_livello_area(p_auth_user_id integer, p_area_schema_db character varying)
IS 'Risolve il livello di accesso di un utente su un''area. Catena: gate di contesto (app.ruolo_applicativo valorizzata e diversa da OPERATORE -> BLOCCATO), identita'' OPERATORE attiva, super admin -> TUTTO, override utente valido, ereditato dal profilo (script.fn_get_permessi_ereditati_aree: sola veste OPERATORE, AD_HOC > REPARTO > PORTALE), default BLOCCATO. Rev 20260925-83 (brief-db-pgtap-permessi-ereditati, D-1 e D-2): il passo 4 non riscrive lo spareggio e non conta piu'' i profili delle altre vesti dell''utente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
