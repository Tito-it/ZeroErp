{% include-markdown "it/dbzero/script/manual/fn_get_permessi_effettivi_azioni.md" %}
# ⚙️ Funzione `fn_get_permessi_effettivi_azioni`

```sql
CREATE FUNCTION fn_get_permessi_effettivi_azioni(p_auth_user_id integer, p_permission_codename character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_permessi_effettivi_azioni(p_auth_user_id integer, p_permission_codename character varying DEFAULT NULL::character varying)
 RETURNS TABLE(permission_codename character varying, azione_id integer, area_id integer, attivo boolean, abilitata_specifica boolean, livello_area config.livello_accesso, livello_minimo_area config.livello_accesso, abilitata boolean, limitata_da_area boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la catena delle azioni di processo di un operatore, col tetto d'area
--   (brief-db-permessi-tetto-area). Sede unica: la leggono
--   fn_check_azione_processo, fn_get_user_actions_map e il pannello permessi.
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
        -- Tutto il catalogo (mappa, pannello).
        SELECT ap.permission_codename AS v_codename, ap.id AS v_azione_id,
               ap.area_id AS v_area_id, ap.attivo AS v_attivo,
               ap.livello_minimo_area AS v_minimo
          FROM config.azioni_processo ap
         WHERE p_permission_codename IS NULL
        UNION ALL
        -- Una sola azione (resolver puntuale): la riga c'e' anche per un
        -- codename fuori catalogo, e li' vale il default.
        SELECT q.codename, ap.id, ap.area_id, ap.attivo, ap.livello_minimo_area
          FROM (VALUES (p_permission_codename)) q(codename)
          LEFT JOIN config.azioni_processo ap
            ON ap.permission_codename = q.codename
         WHERE p_permission_codename IS NOT NULL
    ),
    livelli AS (
        -- Il livello d'area: dalla sede della catena d'area, una volta per area.
        SELECT d.l_area_id,
               script.fn_resolve_livello_area(p_auth_user_id, d.l_schema_db) AS l_livello
          FROM (SELECT DISTINCT v.v_area_id AS l_area_id, af.schema_db AS l_schema_db
                  FROM voci v
                  JOIN config.aree_funzionali af ON af.id = v.v_area_id) d
    ),
    specifiche AS (
        -- 3. La catena senza tetto: override valido -> profilo -> negata.
        SELECT v.*, l.l_livello,
               CASE
                   WHEN NOT v_has_identita THEN false
                   WHEN v_is_super          THEN true
                   ELSE COALESCE(uoa.abilitata, e.abilitata, false)
               END AS s_specifica
          FROM voci v
          LEFT JOIN livelli l
            ON l.l_area_id = v.v_area_id
          LEFT JOIN config.user_override_azioni uoa
            ON uoa.auth_user_id = p_auth_user_id
           AND uoa.azione_id    = v.v_azione_id
           AND uoa.validita @> (SELECT script.fn_data_operativa())
          LEFT JOIN script.fn_get_permessi_ereditati_azioni(p_auth_user_id) e
            ON e.azione_id = v.v_azione_id
    ),
    effettive AS (
        -- 4. Il tetto: il super admin lo precede, tutti gli altri lo subiscono.
        SELECT s.*,
               CASE
                   WHEN v_is_super THEN true
                   ELSE s.s_specifica
                        AND script.fn_area_consente_azione(s.l_livello, s.v_minimo)
               END AS s_effettiva
          FROM specifiche s
    )
    SELECT f.v_codename, f.v_azione_id, f.v_area_id, f.v_attivo,
           f.s_specifica, f.l_livello, f.v_minimo,
           f.s_effettiva,
           f.s_specifica AND NOT f.s_effettiva
      FROM effettive f;
END;
$function$

COMMENT ON FUNCTION script.fn_get_permessi_effettivi_azioni(p_auth_user_id integer, p_permission_codename character varying)
IS 'Le azioni di processo effettive di un operatore, col tetto d''area (brief-db-permessi-tetto-area, D-1…D-4). Per ogni azione: abilitata_specifica (la catena senza tetto: gate di contesto, identita'' OPERATORE attiva, super admin, override valido, ereditato dal profilo con script.fn_get_permessi_ereditati_azioni, default negata), livello_area (script.fn_resolve_livello_area sull''area dell''azione), livello_minimo_area, abilitata (= specifica E script.fn_area_consente_azione; il super admin precede il tetto) e limitata_da_area (specifica si'', area no: l''override o il profilo e'' dormiente, D-3). p_permission_codename NULL -> tutto il catalogo, attive e no; valorizzato -> una riga, anche per un codename fuori catalogo (negata). Sede UNICA della catena delle azioni: la leggono script.fn_check_azione_processo, script.fn_get_user_actions_map e il pannello permessi (backend). plpgsql, STABLE, INVOKER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
