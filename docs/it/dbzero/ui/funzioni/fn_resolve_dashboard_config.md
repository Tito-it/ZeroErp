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
-- Scopo: la configurazione effettiva di una dashboard per un utente, pronta
--   per il frontend. Cascata per chiave (widget, dimensione_max): la
--   preferenza, poi il preset di base (ui.fn_preset_di_base), poi il
--   catalogo. Poi il merge dei widget nuovi del pool e il filtro dei
--   permessi (mappe aggregate). Campi opachi (deep_link, contatore_key,
--   soglia) restituiti freschi, senza interpretarli.
-- Il banner: preset_base_cambiato se la base salvata non e' quella di oggi,
--   altrimenti preset_aggiornato (ui.fn_preset_aggiornato).
DECLARE
  v_dashboard_id     ui.dashboard_definizione.id%TYPE;
  v_config_widget    JSONB;    -- widget della configurazione candidata
  -- Il ripiego del catalogo grezzo (brief §3c): niente preset, o un preset
  -- senza dimensione.
  v_dimensione_catalogo CONSTANT ui.dashboard_preset.dimensione_max%TYPE := 8;
  v_dimensione_max   ui.dashboard_preset.dimensione_max%TYPE;
  v_widget_nuovi     INTEGER  := 0;

  -- Mappe permessi aggregate (resolve once, §3b), GUC-aware fail-closed
  v_area_map         JSONB    := '{}'::JSONB;   -- { schema_db: 'LIVELLO' }
  v_azioni_map       JSONB    := '{}'::JSONB;   -- { permission_codename: bool }

  -- Veste corrente dalla GUC. NULL = tutte le vesti, anche per un valore
  -- fuori dominio: la regola sta nel building block (2026-09-23).
  v_ruolo_guc        config.ruolo_applicativo := ui.fn_veste_corrente();

  -- 2026-11-01: le due chiavi della preferenza, ognuna per conto suo.
  --   NULL = chiave assente (o null): «come lo standard».
  v_pref_widget      ui.dashboard_preferenza_utente.configurazione%TYPE;
  v_pref_dimensione  ui.dashboard_preset.dimensione_max%TYPE;
  -- 2026-11-01: il preset di base (passi 2b-2d), letto anche quando c'e'
  --   una preferenza: e' lo standard delle chiavi che la preferenza non ha.
  v_preset_widget     JSONB;
  v_preset_dimensione ui.dashboard_preset.dimensione_max%TYPE;
  v_preset_livello    ui.dashboard_preset.ambito%TYPE;
  v_dimensione_standard ui.dashboard_preset.dimensione_max%TYPE;

  -- Snapshot preset di base dalla preferenza utente (DEF-2)
  v_pref_preset_base_id    ui.dashboard_preferenza_utente.preset_base_id%TYPE;
  v_pref_preset_base_ts    ui.dashboard_preferenza_utente.preset_base_contenuto_aggiornato_il%TYPE;
  v_pref_preset_ignored_at ui.dashboard_preferenza_utente.preset_aggiornato_ignored_at%TYPE;
  -- Il preset di base, scelto da ui.fn_preset_di_base: id e data del
  -- contenuto (l'ambito sta in v_preset_livello).
  v_base_id                ui.dashboard_preset.id%TYPE;
  v_base_contenuto         ui.dashboard_preset.contenuto_aggiornato_il%TYPE;
  -- Tipi espliciti: due esiti calcolati qui, nessuna colonna di cui siano il riflesso.
  v_preset_aggiornato      BOOLEAN := FALSE;
  v_preset_base_cambiato   BOOLEAN := FALSE;
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
  -- 1. Mappe permessi (resolve once). Le mappe sono l'autorita' per il
  --    gating (coprono super-admin, override utente, veste corrente).
  --    Fail-closed su non-OPERATORE. I profili applicabili li legge
  --    ui.fn_preset_di_base.
  -- -------------------------------------------------------
  v_area_map   := script.fn_get_user_permissions_map(p_auth_user_id);
  v_azioni_map := script.fn_get_user_actions_map(p_auth_user_id);

  -- -------------------------------------------------------
  -- 2. Cascata PER CHIAVE (2026-11-01): si leggono la preferenza e il
  --    preset di base, poi ogni chiave prende il primo dei due che la
  --    contiene, e il catalogo se nessuno dei due.
  --    ⚠️ Prima la cascata sceglieva un livello solo, il primo con i
  --    widget: una preferenza di soli widget rispondeva dimensione_max 8,
  --    scavalcando quella del preset.
  -- -------------------------------------------------------

  -- 2a. Preferenza personale utente: ogni chiave per conto suo.
  --     dimensione_max vale se e' un intero positivo: nessun cast che
  --     possa cadere (prima un valore non numerico fermava la funzione).
  SELECT
      NULLIF(pu.configurazione -> 'widget', 'null'::JSONB),
      CASE WHEN (pu.configurazione ->> 'dimensione_max') ~ '^[1-9][0-9]{0,8}$'
           THEN (pu.configurazione ->> 'dimensione_max')::INTEGER END,
      pu.preset_base_id,
      pu.preset_base_contenuto_aggiornato_il,
      pu.preset_aggiornato_ignored_at
    INTO v_pref_widget, v_pref_dimensione,
         v_pref_preset_base_id, v_pref_preset_base_ts, v_pref_preset_ignored_at
    FROM ui.dashboard_preferenza_utente pu
   WHERE pu.auth_user_id = p_auth_user_id
     AND pu.dashboard_id = v_dashboard_id;

  -- 2b. Il preset di base: lo sceglie ui.fn_preset_di_base, la sede comune
  --     a liste e dashboard (acceso e con almeno un widget acceso nel pool;
  --     il ruolo solo con la veste, l'azienda solo accesa, poi il sistema).
  --     Si cerca sempre, anche con una preferenza.
  SELECT b.preset_id, b.ambito, b.contenuto_aggiornato_il
    INTO v_base_id, v_preset_livello, v_base_contenuto
    FROM ui.fn_preset_di_base('dashboard', v_dashboard_id, p_auth_user_id, v_ruolo_guc,
                              p_emittente_fiscale_id) b;

  IF v_base_id IS NOT NULL THEN
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
        lp.dimensione_max
      INTO v_preset_widget, v_preset_dimensione
      FROM ui.dashboard_preset lp
     WHERE lp.id = v_base_id;
  END IF;

  -- La dimensione: la preferenza, poi il preset di base, poi il ripiego.
  v_dimensione_standard := COALESCE(v_preset_dimensione, v_dimensione_catalogo);
  v_dimensione_max      := COALESCE(v_pref_dimensione, v_dimensione_standard);

  v_config_widget := COALESCE(v_pref_widget, v_preset_widget);

  -- 2e. Catalogo grezzo (fallback finale "mai vuota"), solo per i widget:
  --     tutti i widget attivi del pool della dashboard, ordinati per
  --     ordine_default, se ne' la preferenza ne' un preset li hanno.
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
  -- 2.5 Il banner, gemello delle liste: preset_base_cambiato se la base
  --     salvata non e' quella di oggi; preset_aggiornato solo sulla base di
  --     oggi, dal contenuto che la scelta ha gia' letto.
  -- -------------------------------------------------------
  v_preset_base_cambiato := v_pref_preset_base_id IS NOT NULL
                            AND v_pref_preset_base_id IS DISTINCT FROM v_base_id;
  v_preset_aggiornato    := v_pref_preset_base_id IS NOT NULL
                            AND NOT v_preset_base_cambiato
                            AND ui.fn_preset_aggiornato(v_pref_preset_base_ts, v_base_contenuto,
                                                        v_pref_preset_ignored_at);

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
    -- ⭐ 2026-11-01: la dimensione SENZA la preferenza. Chiave ADDITIVA.
    'dimensione_max_standard', v_dimensione_standard,
    -- ⭐ 2026-11-01: per ogni chiave il livello da cui viene ('preferenza',
    --   un ambito di ui.ambito_preset o 'catalogo'), gemella delle liste: il
    --   FE rimanda al salvataggio solo le chiavi 'preferenza', piu' quella
    --   toccata. Chiave ADDITIVA.
    'origine', jsonb_build_object(
      'widget',         CASE WHEN v_pref_widget   IS NOT NULL THEN 'preferenza'
                             WHEN v_preset_widget IS NOT NULL THEN v_preset_livello::text
                             ELSE 'catalogo' END,
      'dimensione_max', CASE WHEN v_pref_dimensione   IS NOT NULL THEN 'preferenza'
                             WHEN v_preset_dimensione IS NOT NULL THEN v_preset_livello::text
                             ELSE 'catalogo' END
    ),
    'widget_nuovi',      v_widget_nuovi,
    'preset_aggiornato', v_preset_aggiornato,
    -- Il preset di base di oggi (id, ambito, data del contenuto), o null.
    --   Chiave ADDITIVA, gemella delle liste.
    'preset_base',       CASE WHEN v_base_id IS NULL THEN NULL
                              ELSE jsonb_build_object('id', v_base_id,
                                                      'ambito', v_preset_livello::text,
                                                      'contenuto_aggiornato_il', v_base_contenuto) END,
    'preset_base_cambiato', v_preset_base_cambiato
  );

END;
$function$

COMMENT ON FUNCTION ui.fn_resolve_dashboard_config(p_dashboard_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'La configurazione effettiva di una dashboard per un utente, pronta per il frontend, gemella di ui.fn_resolve_lista_config. Cascata per chiave: widget e dimensione_max vengono ognuna dal primo livello che la contiene: la preferenza (una chiave assente vuol dire «come lo standard»), poi il preset di base scelto da ui.fn_preset_di_base (acceso e con almeno un widget acceso nel pool della dashboard: il preset di ruolo del profilo piu'' prioritario, solo con la veste valorizzata; poi quello dell''azienda, se accesa; poi quello di sistema), poi il catalogo (tutti i widget accesi del pool). Poi il merge dei widget nuovi del pool, il filtro dei permessi per area e azione (mappe aggregate script.fn_get_user_permissions_map e fn_get_user_actions_map, fail-closed fuori dalla veste OPERATORE) e i campi opachi freschi (deep_link, contatore_key, soglia, etichette, tipo_widget). Uscite: widget, dimensione_max e dimensione_max_standard (senza la preferenza), origine (per chiave: preferenza, ruolo, emittente_fiscale, sistema o catalogo), widget_nuovi, preset_base (id, ambito e contenuto_aggiornato_il del preset di base di oggi, o null), preset_base_cambiato (la preferenza ha salvato una base che non e'' quella di oggi), preset_aggiornato (solo sulla base di oggi, ui.fn_preset_aggiornato). Dashboard assente o spenta: E_UI_DASHBOARD_NON_TROVATA. La veste la legge ui.fn_veste_corrente. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
