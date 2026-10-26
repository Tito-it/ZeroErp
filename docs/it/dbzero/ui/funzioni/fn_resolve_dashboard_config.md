{% include-markdown "it/dbzero/ui/manual/fn_resolve_dashboard_config.md" %}
# ⚙️ Funzione `fn_resolve_dashboard_config`

```sql
CREATE FUNCTION fn_resolve_dashboard_config(p_dashboard_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_resolve_dashboard_config(p_dashboard_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: risolve la configurazione effettiva di una dashboard per un utente.
-- Cascata preset -> merge widget nuovi -> filtro permessi via resolver.
-- Ritorna JSONB pronto per il frontend. Zero interpretazione di
-- deep_link/contatore_key/soglia (campi opachi restituiti freschi).
-- 2026-09-23: la veste la legge ui.fn_veste_corrente(), building block
-- condiviso con il risolutore delle liste e con la ricerca libera.
DECLARE
  v_dashboard_id     ui.dashboard_definizione.id%TYPE;
  v_config_widget    JSONB;    -- widget della configurazione candidata
  v_dimensione_max   INTEGER  := 8;   -- fallback catalogo grezzo (brief §3c)
  v_profili_ids      INTEGER[];
  v_widget_nuovi     INTEGER  := 0;

  -- Mappe permessi aggregate (resolve once, §3b), GUC-aware fail-closed
  v_area_map         JSONB    := '{}'::JSONB;   -- { schema_db: 'LIVELLO' }
  v_azioni_map       JSONB    := '{}'::JSONB;   -- { permission_codename: bool }

  -- Veste corrente dalla GUC. NULL = tutte le vesti, anche per un valore
  -- fuori dominio: la regola sta nel building block (2026-09-23).
  v_ruolo_guc        config.ruolo_applicativo := ui.fn_veste_corrente();

  -- Snapshot preset di base dalla preferenza utente (DEF-2)
  v_pref_preset_base_id    ui.dashboard_preferenza_utente.preset_base_id%TYPE;
  v_pref_preset_base_ts    ui.dashboard_preferenza_utente.preset_base_data_update%TYPE;
  v_pref_preset_ignored_at ui.dashboard_preferenza_utente.preset_aggiornato_ignored_at%TYPE;
  v_preset_data_update     ui.dashboard_preset.data_update%TYPE;
  v_preset_aggiornato      BOOLEAN := FALSE;
BEGIN
  -- -------------------------------------------------------
  -- 0. Recupera dashboard_id dal codice
  -- -------------------------------------------------------
  SELECT id INTO v_dashboard_id
    FROM ui.dashboard_definizione
   WHERE codice = p_dashboard_codice
     AND attivo = TRUE;

  IF v_dashboard_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'ui.fn_resolve_dashboard_config',
      'E_UI_DASHBOARD_NON_TROVATA',
      jsonb_build_object('detail', format('codice dashboard: ''%s''', p_dashboard_codice)),
      NULL,
      p_dashboard_codice
    );
  END IF;

  -- -------------------------------------------------------
  -- 1. Profili applicabili (GUC-aware) + mappe permessi (resolve once)
  --    Le mappe sono l'autorita per il gating (coprono super-admin,
  --    override utente, veste corrente). Fail-closed su non-OPERATORE.
  -- -------------------------------------------------------
  SELECT ARRAY_AGG(profilo_accesso_id)
    INTO v_profili_ids
    FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id, v_ruolo_guc);

  IF v_profili_ids IS NULL THEN
    v_profili_ids := ARRAY[]::INTEGER[];
  END IF;

  v_area_map   := script.fn_get_user_permissions_map(p_auth_user_id);
  v_azioni_map := script.fn_get_user_actions_map(p_auth_user_id);

  -- -------------------------------------------------------
  -- 2. Cascata: trova la configurazione candidata
  -- -------------------------------------------------------

  -- 2a. Preferenza personale utente
  SELECT
      (pu.configurazione -> 'widget'),
      COALESCE((pu.configurazione ->> 'dimensione_max')::INTEGER, 8),
      pu.preset_base_id,
      pu.preset_base_data_update,
      pu.preset_aggiornato_ignored_at
    INTO v_config_widget, v_dimensione_max,
         v_pref_preset_base_id, v_pref_preset_base_ts, v_pref_preset_ignored_at
    FROM ui.dashboard_preferenza_utente pu
   WHERE pu.auth_user_id = p_auth_user_id
     AND pu.dashboard_id = v_dashboard_id;

  -- 2b. Preset di ruolo (priorita ASC: AD_HOC prio 1 > REPARTO/PORTALE prio 2)
  IF v_config_widget IS NULL AND array_length(v_profili_ids, 1) > 0 THEN
    SELECT
        (
          SELECT jsonb_agg(
            jsonb_build_object(
              'codice',   w.codice,
              'ordine',   pw.ordine,
              'visibile', pw.visibile
            )
            ORDER BY pw.ordine
          )
          FROM ui.dashboard_preset_widget pw
          JOIN ui.widget w ON w.id = pw.widget_id
         WHERE pw.preset_id = lp.id
           AND w.attivo = TRUE
        ),
        COALESCE(lp.dimensione_max, 8)
      INTO v_config_widget, v_dimensione_max
      FROM ui.dashboard_preset lp
      JOIN script.fn_get_profili_accesso_applicabili(p_auth_user_id, v_ruolo_guc) pa
        ON pa.profilo_accesso_id = lp.profilo_accesso_id
     WHERE lp.dashboard_id = v_dashboard_id
       AND lp.ambito       = 'ruolo'
       AND lp.is_default   = TRUE
       AND lp.attivo       = TRUE
     ORDER BY pa.priorita ASC
     LIMIT 1;
  END IF;

  -- 2c. Preset di emittente fiscale
  IF v_config_widget IS NULL AND p_emittente_fiscale_id IS NOT NULL THEN
    SELECT
        (
          SELECT jsonb_agg(
            jsonb_build_object(
              'codice',   w.codice,
              'ordine',   pw.ordine,
              'visibile', pw.visibile
            )
            ORDER BY pw.ordine
          )
          FROM ui.dashboard_preset_widget pw
          JOIN ui.widget w ON w.id = pw.widget_id
         WHERE pw.preset_id = lp.id
           AND w.attivo = TRUE
        ),
        COALESCE(lp.dimensione_max, 8)
      INTO v_config_widget, v_dimensione_max
      FROM ui.dashboard_preset lp
     WHERE lp.dashboard_id         = v_dashboard_id
       AND lp.ambito               = 'emittente_fiscale'
       AND lp.emittente_fiscale_id = p_emittente_fiscale_id
       AND lp.is_default           = TRUE
       AND lp.attivo               = TRUE
     LIMIT 1;
  END IF;

  -- 2d. Preset di sistema
  IF v_config_widget IS NULL THEN
    SELECT
        (
          SELECT jsonb_agg(
            jsonb_build_object(
              'codice',   w.codice,
              'ordine',   pw.ordine,
              'visibile', pw.visibile
            )
            ORDER BY pw.ordine
          )
          FROM ui.dashboard_preset_widget pw
          JOIN ui.widget w ON w.id = pw.widget_id
         WHERE pw.preset_id = lp.id
           AND w.attivo = TRUE
        ),
        COALESCE(lp.dimensione_max, 8)
      INTO v_config_widget, v_dimensione_max
      FROM ui.dashboard_preset lp
     WHERE lp.dashboard_id = v_dashboard_id
       AND lp.ambito       = 'sistema'
       AND lp.is_default   = TRUE
       AND lp.attivo       = TRUE
     LIMIT 1;
  END IF;

  -- 2e. Catalogo grezzo (fallback finale "mai vuota"): tutti i widget
  --     attivi del pool della dashboard, ordinati per ordine_default.
  IF v_config_widget IS NULL THEN
    SELECT jsonb_agg(
      jsonb_build_object(
        'codice',   w.codice,
        'ordine',   dw.ordine_default,
        'visibile', TRUE
      )
      ORDER BY dw.ordine_default
    )
    INTO v_config_widget
    FROM ui.dashboard_widget dw
    JOIN ui.widget w ON w.id = dw.widget_id
   WHERE dw.dashboard_id = v_dashboard_id
     AND w.attivo        = TRUE;
  END IF;

  IF v_config_widget IS NULL THEN
    v_config_widget := '[]'::JSONB;
  END IF;

  -- -------------------------------------------------------
  -- 2.5 DEF-2: flag preset_aggiornato. TRUE sse il preset di base
  --     e' piu' recente dello snapshot salvato E l'utente non ha
  --     ancora ignorato (o il preset e' cambiato dopo l'ignore).
  -- -------------------------------------------------------
  IF v_pref_preset_base_id IS NOT NULL AND v_pref_preset_base_ts IS NOT NULL THEN
    SELECT lp.data_update
      INTO v_preset_data_update
      FROM ui.dashboard_preset lp
     WHERE lp.id = v_pref_preset_base_id;
  END IF;

  v_preset_aggiornato :=
        v_pref_preset_base_ts IS NOT NULL
    AND v_preset_data_update  IS NOT NULL
    AND v_preset_data_update  > v_pref_preset_base_ts
    AND (
          v_pref_preset_ignored_at IS NULL
      OR  v_pref_preset_ignored_at < v_preset_data_update
    );

  -- -------------------------------------------------------
  -- 3. Merge automatico widget nuovi dal pool della dashboard
  --    (presenti in dashboard_widget ma assenti dalla configurazione)
  -- -------------------------------------------------------
  SELECT
    v_config_widget || COALESCE(
      jsonb_agg(
        jsonb_build_object(
          'codice',   w.codice,
          'ordine',   dw.ordine_default + 10000,
          'visibile', FALSE
        )
      ),
      '[]'::JSONB
    ),
    COUNT(*)::INTEGER
  INTO v_config_widget, v_widget_nuovi
  FROM ui.dashboard_widget dw
  JOIN ui.widget w ON w.id = dw.widget_id
 WHERE dw.dashboard_id = v_dashboard_id
   AND w.attivo        = TRUE
   AND w.codice NOT IN (
     SELECT elem ->> 'codice'
       FROM jsonb_array_elements(v_config_widget) AS elem
   );

  -- -------------------------------------------------------
  -- 4. Assemblaggio finale + filtro permessi + arricchimento.
  --    - Tiene solo widget del pool della dashboard, attivi (§4.6).
  --    - Filtro permessi (§3b): drop se area BLOCCATA o azione negata.
  --    - Arricchisce dai campi freschi di ui.widget (deep_link,
  --      contatore_key, soglia, etichetta*, tipo_widget) — la
  --      preferenza porta solo il codice (§3d).
  -- -------------------------------------------------------
  SELECT jsonb_agg(
      jsonb_build_object(
        'codice',             w.codice,
        'ordine',             (elem ->> 'ordine')::INTEGER,
        'visibile',           (elem ->> 'visibile')::BOOLEAN,
        'tipo_widget',        w.tipo_widget::text,
        'etichetta',          w.etichetta,
        'etichetta_i18n_key', w.etichetta_i18n_key,
        'deep_link',          w.deep_link,
        'contatore_key',      w.contatore_key,
        'soglia',             w.soglia
      )
      ORDER BY (elem ->> 'ordine')::INTEGER
    )
    INTO v_config_widget
    FROM jsonb_array_elements(v_config_widget) AS elem
    JOIN ui.widget w
      ON w.codice = elem ->> 'codice'
     AND w.attivo = TRUE
    -- membership nel pool della dashboard (drop widget staccati/rimossi)
    JOIN ui.dashboard_widget dw
      ON dw.dashboard_id = v_dashboard_id
     AND dw.widget_id   = w.id
    -- decodifica area/azione per il lookup nelle mappe (§3b)
    LEFT JOIN config.aree_funzionali af ON af.id = w.area_id
    LEFT JOIN config.azioni_processo ap ON ap.id = w.azione_id
   WHERE
     -- gate area: NULL = non gated; altrimenti livello <> BLOCCATO
     (
       w.area_id IS NULL
       OR COALESCE(v_area_map ->> af.schema_db, 'BLOCCATO') <> 'BLOCCATO'
     )
     -- gate azione: NULL = non gated; altrimenti abilitata
     AND (
       w.azione_id IS NULL
       OR COALESCE((v_azioni_map ->> ap.permission_codename)::BOOLEAN, FALSE)
     );

  IF v_config_widget IS NULL THEN
    v_config_widget := '[]'::JSONB;
  END IF;

  -- -------------------------------------------------------
  -- 5. Ritorna il JSONB finale (contratto FE)
  -- -------------------------------------------------------
  RETURN jsonb_build_object(
    'widget',            v_config_widget,
    'dimensione_max',    v_dimensione_max,
    'widget_nuovi',      v_widget_nuovi,
    'preset_aggiornato', v_preset_aggiornato
  );

END;
$function$

COMMENT ON FUNCTION ui.fn_resolve_dashboard_config(p_dashboard_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'Risolve la configurazione effettiva di una dashboard per un utente: cascata preset (GUC-aware, deterministica per priorita), merge widget nuovi, filtro permessi via resolver script.* (mappe aggregate, fail-closed non-OPERATORE), arricchimento campi opachi (deep_link/contatore_key/soglia). Ritorna JSONB { widget[], dimensione_max, widget_nuovi, preset_aggiornato }. Mirror di ui.fn_resolve_lista_config (brief-db-dashboard-home §3). 2026-09-23: la veste la legge ui.fn_veste_corrente(), building block condiviso con fn_resolve_lista_config e fn_lista_colonne_ricerca_full. Brief: brief-db-ricerca-full-colonne-permessi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
