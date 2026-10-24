{% include-markdown "it/dbzero/script/manual/fn_get_permessi_effettivi_oggetti.md" %}
# ⚙️ Funzione `fn_get_permessi_effettivi_oggetti`

```sql
CREATE FUNCTION fn_get_permessi_effettivi_oggetti(p_auth_user_id integer, p_app_label character varying, p_model_name character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_permessi_effettivi_oggetti(p_auth_user_id integer, p_app_label character varying DEFAULT NULL::character varying, p_model_name character varying DEFAULT NULL::character varying)
 RETURNS TABLE(app_label character varying, model_name character varying, area_schema_db character varying, livello_override config.livello_accesso, livello_area config.livello_accesso, livello_specifico config.livello_accesso, livello config.livello_accesso, limitato_da_area boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la catena degli oggetti di un operatore, col tetto d'area
--   (brief-db-permessi-tetto-area). Sede unica: la leggono
--   fn_resolve_livello_oggetto, fn_get_user_object_permissions_map e il
--   pannello permessi.
DECLARE
    v_ctx_ruolo    anagrafiche.identita_digitali.ruolo_applicativo%TYPE;
    v_has_identita boolean;   -- flag calcolato (fn_has_identita_attiva)
    v_is_super     boolean;   -- flag calcolato (fn_is_super_admin)
BEGIN
    -- 0. Gate contesto GUC (fail-closed su non-OPERATORE).
    v_ctx_ruolo := NULLIF(
        current_setting('app.ruolo_applicativo', true), ''
    )::config.ruolo_applicativo;

    IF v_ctx_ruolo IS NOT NULL
       AND v_ctx_ruolo <> 'OPERATORE'::config.ruolo_applicativo THEN
        v_has_identita := false;
        v_is_super     := false;
    ELSE
        -- 1-2. Identita' OPERATORE attiva, super admin.
        v_has_identita := script.fn_has_identita_attiva(
                              p_auth_user_id,
                              'OPERATORE'::config.ruolo_applicativo);
        v_is_super     := v_has_identita
                          AND script.fn_is_super_admin(p_auth_user_id);
    END IF;

    RETURN QUERY
    WITH voci AS (
        -- Tutto il catalogo degli oggetti (mappa di /me/, pannello).
        SELECT amo.app_label AS v_app, amo.model_name AS v_modello
          FROM config.area_model_overrides amo
         WHERE p_app_label IS NULL AND p_model_name IS NULL
        UNION ALL
        -- Un solo oggetto (resolver puntuale), a catalogo o no.
        SELECT p_app_label, p_model_name
         WHERE p_app_label IS NOT NULL OR p_model_name IS NOT NULL
    ),
    con_area AS (
        -- 3. L'area e' quella dell'oggetto, non quella del chiamante (R4).
        SELECT v.v_app, v.v_modello,
               script.fn_area_di_oggetto(v.v_app, v.v_modello) AS v_area
          FROM voci v
    ),
    livelli AS (
        SELECT d.l_area,
               script.fn_resolve_livello_area(p_auth_user_id, d.l_area) AS l_livello
          FROM (SELECT DISTINCT ca.v_area AS l_area FROM con_area ca) d
    ),
    grezzi AS (
        SELECT ca.v_app, ca.v_modello, ca.v_area,
               uoo.livello AS g_override, l.l_livello
          FROM con_area ca
          LEFT JOIN livelli l
            ON l.l_area IS NOT DISTINCT FROM ca.v_area
          LEFT JOIN config.user_override_oggetti uoo
            ON uoo.auth_user_id = p_auth_user_id
           AND uoo.app_label    = ca.v_app
           AND uoo.model_name   = ca.v_modello
           AND uoo.validita @> (SELECT script.fn_data_operativa())
    ),
    calcolo AS (
        -- 4. Senza tetto (la catena di ieri) e col tetto.
        SELECT g.*,
               CASE
                   WHEN NOT v_has_identita THEN 'BLOCCATO'::config.livello_accesso
                   WHEN v_is_super          THEN 'TUTTO'::config.livello_accesso
                   ELSE COALESCE(g.g_override, g.l_livello,
                                 'BLOCCATO'::config.livello_accesso)
               END AS c_specifico,
               CASE
                   WHEN NOT v_has_identita THEN 'BLOCCATO'::config.livello_accesso
                   WHEN v_is_super          THEN 'TUTTO'::config.livello_accesso
                   ELSE script.fn_livello_con_tetto_area(g.g_override, g.l_livello)
               END AS c_effettivo
          FROM grezzi g
    )
    SELECT c.v_app, c.v_modello, c.v_area, c.g_override, c.l_livello,
           c.c_specifico, c.c_effettivo,
           c.c_effettivo IS DISTINCT FROM c.c_specifico
      FROM calcolo c;
END;
$function$

COMMENT ON FUNCTION script.fn_get_permessi_effettivi_oggetti(p_auth_user_id integer, p_app_label character varying, p_model_name character varying)
IS 'Gli oggetti effettivi di un operatore, col tetto d''area (brief-db-permessi-tetto-area, D-1…D-3). Per ogni oggetto: area_schema_db (script.fn_area_di_oggetto: l''area e'' quella dell''oggetto, R4), livello_override (l''override valido, grezzo), livello_area (script.fn_resolve_livello_area), livello_specifico (la catena senza tetto: override, altrimenti area), livello (script.fn_livello_con_tetto_area: il piu'' restrittivo fra override e area) e limitato_da_area (l''override allarga e il tetto lo ferma: dormiente, D-3). Gate di contesto e identita'' OPERATORE assente -> BLOCCATO; super admin -> TUTTO, prima del tetto. p_app_label e p_model_name NULL -> tutto il catalogo config.area_model_overrides (un override esiste solo per un oggetto a catalogo); altrimenti una riga per l''oggetto chiesto, a catalogo o no. Sede UNICA della catena degli oggetti: la leggono script.fn_resolve_livello_oggetto, script.fn_get_user_object_permissions_map e il pannello permessi (backend). plpgsql, STABLE, INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
