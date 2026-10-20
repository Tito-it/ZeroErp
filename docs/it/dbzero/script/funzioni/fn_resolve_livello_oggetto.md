{% include-markdown "it/dbzero/script/manual/fn_resolve_livello_oggetto.md" %}
# ⚙️ Funzione `fn_resolve_livello_oggetto`

```sql
CREATE FUNCTION fn_resolve_livello_oggetto(p_auth_user_id integer, p_app_label character varying, p_model_name character varying, p_area_schema_db character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_livello_oggetto(p_auth_user_id integer, p_app_label character varying, p_model_name character varying, p_area_schema_db character varying)
 RETURNS config.livello_accesso
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_livello config.user_override_oggetti.livello%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Risolve il livello di accesso per un singolo model
    --   Django (app_label + model_name), col tetto d'area.
    --
    -- Catena (rev 20261004-57, brief-db-permessi-tetto-area):
    --   la legge da script.fn_get_permessi_effettivi_oggetti, sede
    --   unica: gate di contesto, identita' OPERATORE attiva, super
    --   admin (prima del tetto), poi il piu' restrittivo fra
    --   l'override sull'oggetto e il livello della SUA area
    --   (script.fn_area_di_oggetto, script.fn_livello_con_tetto_area).
    --
    -- ⚠️ p_area_schema_db e' SUPERATO (R4): l'area la ricava la
    --   funzione dall'oggetto, perche' col tetto un'area sbagliata
    --   sarebbe un tetto sbagliato. Il parametro resta nella firma
    --   (i chiamanti passano per posizione); il ritiro lo decide Tid.
    -- =========================================================

    -- Nessun oggetto: niente da risolvere, BLOCCATO. Senza questa riga
    -- la sede comune leggerebbe i due NULL come «tutto il catalogo».
    IF p_app_label IS NULL AND p_model_name IS NULL THEN
        RETURN 'BLOCCATO'::config.livello_accesso;
    END IF;

    SELECT e.livello
      INTO v_livello
      FROM script.fn_get_permessi_effettivi_oggetti(
               p_auth_user_id, p_app_label, p_model_name) e;

    RETURN COALESCE(v_livello, 'BLOCCATO'::config.livello_accesso);
END
$function$

COMMENT ON FUNCTION script.fn_resolve_livello_oggetto(p_auth_user_id integer, p_app_label character varying, p_model_name character varying, p_area_schema_db character varying)
IS 'Risolve il livello di accesso per un model (app_label + model_name) col TETTO D''AREA: il piu'' restrittivo fra l''override utente sull''oggetto e il livello della sua area (l''override puo'' solo restringere, mai allargare). Legge la catena da script.fn_get_permessi_effettivi_oggetti (sede unica, con fn_get_user_object_permissions_map e il pannello permessi): gate di contesto (app.ruolo_applicativo diversa da OPERATORE -> BLOCCATO), identita'' OPERATORE attiva, super admin -> TUTTO (prima del tetto), area dell''oggetto da script.fn_area_di_oggetto, script.fn_livello_con_tetto_area. ⚠️ p_area_schema_db e'' superato: l''area la ricava la funzione e il parametro non si legge piu'' (resta in firma, il ritiro lo decide Tid). Oggetto NULL -> BLOCCATO. La chiamano il backend (PermissionResolver.get_livello_oggetto) e script.fn_guard_livello. Rev 20261004-57 (brief-db-permessi-tetto-area R4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
