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
--   altrimenti le chiavi di origine 'preferenza' il cui contenuto nel preset
--   e' cambiato dopo lo snapshot (ui.fn_preset_aggiornato).
-- Righe scritte prima del guard di forma: nessun cast cade (ui.fn_intero_da_jsonb),
--   una voce senza codice o fuori dal pool si salta, un codice ripetuto vale una
--   volta (la prima), un campo che manca prende il default del pool.
DECLARE
  v_dashboard_id     ui.dashboard_definizione.id%TYPE;
  v_config_widget    JSONB;    -- widget della configurazione candidata
  -- Il ripiego del catalogo grezzo: niente preset, o un preset
  -- senza dimensione.
  v_dimensione_catalogo CONSTANT ui.dashboard_preset.dimensione_max%TYPE := 8;
  v_dimensione_max   ui.dashboard_preset.dimensione_max%TYPE;
  v_widget_nuovi     INTEGER  := 0;
  -- I codici mergiati dal pool al passo 3: il passo 4-bis li riconta DOPO il
  -- filtro dei permessi, come le liste.
  v_codici_mergiati  ui.widget.codice%TYPE[] := ARRAY[]::varchar[];

  -- Mappe permessi aggregate (lette una volta), GUC-aware fail-closed
  v_area_map         JSONB    := '{}'::JSONB;   -- { schema_db: 'LIVELLO' }
  v_azioni_map       JSONB    := '{}'::JSONB;   -- { permission_codename: bool }

  -- La veste corrente dalla GUC; NULL se assente o fuori dominio (la regola
  --   sta nel building block): senza veste il preset di ruolo non concorre.
  v_ruolo_guc        config.ruolo_applicativo := ui.fn_veste_corrente();

  -- Le due chiavi della preferenza, ognuna per conto suo.
  --   NULL = chiave assente (o null): «come lo standard».
  v_pref_widget      ui.dashboard_preferenza_utente.configurazione%TYPE;
  v_pref_dimensione  ui.dashboard_preset.dimensione_max%TYPE;
  -- Il preset di base (passo 2b), letto anche quando c'e' una
  --   preferenza: e' lo standard delle chiavi che la preferenza non ha.
  v_preset_widget     JSONB;
  v_preset_dimensione ui.dashboard_preset.dimensione_max%TYPE;
  v_preset_livello    ui.dashboard_preset.ambito%TYPE;
  v_dimensione_standard ui.dashboard_preset.dimensione_max%TYPE;

  -- Il preset di base salvato con la preferenza e il suo snapshot ({chiave: data}).
  v_pref_preset_base_id    ui.dashboard_preferenza_utente.preset_base_id%TYPE;
  v_pref_preset_base_ts    ui.dashboard_preferenza_utente.preset_base_contenuto_aggiornato_il%TYPE;
  -- Il preset di base, scelto da ui.fn_preset_di_base: id e data del
  -- contenuto per chiave (l'ambito sta in v_preset_livello).
  v_base_id                ui.dashboard_preset.id%TYPE;
  v_base_contenuto         ui.dashboard_preset.contenuto_aggiornato_il%TYPE;
  -- jsonb nudo: da dove viene ogni chiave, calcolato qui; e' l'uscita origine.
  v_origine                JSONB;
  -- Tipi espliciti: esiti calcolati qui, nessuna colonna di cui siano il riflesso.
  v_preset_aggiornato_chiavi TEXT[] := ARRAY[]::TEXT[];
  v_preset_base_cambiato   BOOLEAN := FALSE;
BEGIN
  -- -------------------------------------------------------
  -- 0. La dashboard accesa per codice (ui.fn_dashboard_da_codice): assente
  --    o spenta, E_UI_DASHBOARD_NON_TROVATA.
  -- -------------------------------------------------------
  v_dashboard_id := (ui.fn_dashboard_da_codice(p_dashboard_codice)).id;

  -- -------------------------------------------------------
  -- 1. Mappe permessi (resolve once). Le mappe sono l'autorita' per il
  --    gating (coprono super-admin, override utente, veste corrente).
  --    Fail-closed su non-OPERATORE. I profili applicabili li legge
  --    ui.fn_preset_di_base.
  -- -------------------------------------------------------
  v_area_map   := script.fn_get_user_permissions_map(p_auth_user_id);
  v_azioni_map := script.fn_get_user_actions_map(p_auth_user_id);

  -- -------------------------------------------------------
  -- 2. Cascata per chiave: si leggono la preferenza e il preset di base,
  --    poi ogni chiave prende il primo dei due che la contiene, e il
  --    catalogo se nessuno dei due. Una preferenza di soli widget non
  --    scavalca la dimensione del preset.
  -- -------------------------------------------------------

  -- 2a. Preferenza personale utente: ogni chiave per conto suo.
  --     dimensione_max vale se e' un intero da 1 a 100 (i due BB): nessun
  --     cast che possa cadere; widget vale se e' un elenco. Legge anche preset_base_id e lo snapshot, per il
  --     banner (passo 4-bis).
  SELECT
      CASE WHEN jsonb_typeof(pu.configurazione -> 'widget') = 'array'
           THEN pu.configurazione -> 'widget' END,
      CASE WHEN ui.fn_dimensione_max_ammessa(ui.fn_intero_da_jsonb(pu.configurazione -> 'dimensione_max'))
           THEN ui.fn_intero_da_jsonb(pu.configurazione -> 'dimensione_max') END,
      pu.preset_base_id,
      pu.preset_base_contenuto_aggiornato_il
    INTO v_pref_widget, v_pref_dimensione,
         v_pref_preset_base_id, v_pref_preset_base_ts
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

  -- 2e. Catalogo grezzo, solo per i widget: tutti i widget attivi del pool
  --     della dashboard, ordinati per ordine_default, se ne' la preferenza ne'
  --     un preset li hanno. Dopo il filtro dei permessi l'elenco puo' restare
  --     vuoto: e' un esito, e lo stato vuoto lo dice il frontend.
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
    COUNT(*)::INTEGER,
    COALESCE(array_agg(w.codice), ARRAY[]::varchar[])
  INTO v_config_widget, v_widget_nuovi, v_codici_mergiati
  FROM ui.dashboard_widget dw
  JOIN ui.widget w ON w.id = dw.widget_id
 WHERE dw.dashboard_id = v_dashboard_id
   AND w.attivo        = TRUE
   -- NOT EXISTS e non NOT IN: una voce senza codice darebbe un NULL
   -- nell'elenco, e il NOT IN non sarebbe mai vero.
   AND NOT EXISTS (
     SELECT 1
       FROM jsonb_array_elements(v_config_widget) AS elem
      WHERE elem ->> 'codice' = w.codice
   );

  -- -------------------------------------------------------
  -- 4. Assemblaggio finale + filtro permessi + arricchimento.
  --    - Tiene solo widget del pool della dashboard, attivi.
  --    - Filtro permessi: drop se area BLOCCATA o azione negata.
  --    - Arricchisce dai campi freschi di ui.widget (deep_link,
  --      contatore_key, soglia, etichetta*, tipo_widget) — la
  --      preferenza porta solo il codice.
  --    - Nessun cast che cada: ordine dal BB della misura, un campo che
  --      manca (o di tipo sbagliato) prende il default del pool (ordine
  --      del pool, visibile); un codice ripetuto vale una volta (la prima).
  -- -------------------------------------------------------
  SELECT jsonb_agg(
      jsonb_build_object(
        'codice',             s.codice,
        'ordine',             s.ordine_norm,
        'visibile',           s.visibile_norm,
        'tipo_widget',        s.tipo_widget::text,
        'etichetta',          s.etichetta,
        'etichetta_i18n_key', s.etichetta_i18n_key,
        'deep_link',          s.deep_link,
        'contatore_key',      s.contatore_key,
        'soglia',             s.soglia
      )
      ORDER BY s.ordine_norm, s.ord
    )
    INTO v_config_widget
    FROM (
    SELECT DISTINCT ON (w.id)
           e.ord, w.codice, w.tipo_widget, w.etichetta, w.etichetta_i18n_key,
           w.deep_link, w.contatore_key, w.soglia,
           COALESCE(ui.fn_intero_da_jsonb(e.elem -> 'ordine'), dw.ordine_default) AS ordine_norm,
           CASE WHEN jsonb_typeof(e.elem -> 'visibile') = 'boolean'
                THEN (e.elem -> 'visibile')::BOOLEAN
                ELSE TRUE END                                                  AS visibile_norm
    FROM jsonb_array_elements(v_config_widget) WITH ORDINALITY AS e(elem, ord)
    JOIN ui.widget w
      ON w.codice = e.elem ->> 'codice'
     AND w.attivo = TRUE
    -- membership nel pool della dashboard (drop widget staccati/rimossi)
    JOIN ui.dashboard_widget dw
      ON dw.dashboard_id = v_dashboard_id
     AND dw.widget_id   = w.id
    -- decodifica area/azione per il lookup nelle mappe
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
     )
    ORDER BY w.id, e.ord
    ) s;

  IF v_config_widget IS NULL THEN
    v_config_widget := '[]'::JSONB;
  END IF;

  -- -------------------------------------------------------
  -- 4-ter. widget_nuovi DOPO il filtro di area e azione, come le liste al
  --   passo 5-bis: il badge dice le card che l'utente puo' davvero trovare,
  --   non quelle mergiate dal pool.
  -- -------------------------------------------------------
  IF v_widget_nuovi > 0 THEN
    SELECT COUNT(*)::INTEGER
      INTO v_widget_nuovi
      FROM jsonb_array_elements(v_config_widget) AS elem
     WHERE (elem ->> 'codice') = ANY (v_codici_mergiati);
  END IF;

  -- Per ogni chiave il livello da cui viene ('preferenza', un ambito di
  --   ui.ambito_preset o 'catalogo'), gemella delle liste: il FE rimanda al
  --   salvataggio solo le chiavi 'preferenza', piu' quella toccata. Il
  --   banner guarda solo le chiavi 'preferenza'.
  v_origine := jsonb_build_object(
    'widget',         CASE WHEN v_pref_widget   IS NOT NULL THEN 'preferenza'
                           WHEN v_preset_widget IS NOT NULL THEN v_preset_livello::text
                           ELSE 'catalogo' END,
    'dimensione_max', CASE WHEN v_pref_dimensione   IS NOT NULL THEN 'preferenza'
                           WHEN v_preset_dimensione IS NOT NULL THEN v_preset_livello::text
                           ELSE 'catalogo' END
  );

  -- -------------------------------------------------------
  -- 4-bis. Il banner. preset_base_cambiato: la preferenza ha salvato
  --   una base che non e' quella di oggi, un esito suo (propone il
  --   riallineamento). preset_aggiornato_chiavi: solo sulla base di oggi,
  --   le chiavi di origine 'preferenza' il cui contenuto nel preset e'
  --   cambiato dopo lo snapshot; una chiave che segue gia' il preset non
  --   accende niente. preset_aggiornato: almeno una. Chiudere il banner e'
  --   riscrivere preset_base_id: lo snapshot si riallinea.
  -- -------------------------------------------------------
  v_preset_base_cambiato := v_pref_preset_base_id IS NOT NULL
                            AND v_pref_preset_base_id IS DISTINCT FROM v_base_id;
  IF v_pref_preset_base_id IS NOT NULL AND NOT v_preset_base_cambiato THEN
    v_preset_aggiornato_chiavi := ui.fn_preset_aggiornato(
        v_pref_preset_base_ts, v_base_contenuto,
        ARRAY(SELECT o.key FROM jsonb_each_text(v_origine) AS o
               WHERE o.value = 'preferenza' ORDER BY o.key));
  END IF;

  -- -------------------------------------------------------
  -- 5. Ritorna il JSONB finale (contratto FE)
  -- -------------------------------------------------------
  RETURN jsonb_build_object(
    'widget',            v_config_widget,
    'dimensione_max',    v_dimensione_max,
    -- La dimensione senza la preferenza. Chiave ADDITIVA.
    'dimensione_max_standard', v_dimensione_standard,
    -- Per chiave, il livello da cui viene. Chiave ADDITIVA.
    'origine',           v_origine,
    'widget_nuovi',      v_widget_nuovi,
    'preset_aggiornato', cardinality(v_preset_aggiornato_chiavi) > 0,
    -- Le chiavi in banner, ordinate; vuoto se nessuna. Chiave ADDITIVA.
    'preset_aggiornato_chiavi', to_jsonb(v_preset_aggiornato_chiavi),
    -- Il preset di base di oggi (id, ambito, data del contenuto per chiave),
    --   o null. Chiave ADDITIVA, gemella delle liste.
    'preset_base',       CASE WHEN v_base_id IS NULL THEN NULL
                              ELSE jsonb_build_object('id', v_base_id,
                                                      'ambito', v_preset_livello::text,
                                                      'contenuto_aggiornato_il', v_base_contenuto) END,
    'preset_base_cambiato', v_preset_base_cambiato
  );

END;
$function$

COMMENT ON FUNCTION ui.fn_resolve_dashboard_config(p_dashboard_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'La configurazione effettiva di una dashboard per un utente, pronta per il frontend, gemella di ui.fn_resolve_lista_config. Cascata per chiave: widget e dimensione_max vengono ognuna dal primo livello che la contiene: la preferenza (una chiave assente vuol dire «come lo standard»; dimensione_max vale da 1 a 100, ui.fn_dimensione_max_ammessa), poi il preset di base scelto da ui.fn_preset_di_base (acceso e con almeno un widget acceso nel pool della dashboard: il preset di ruolo del profilo più prioritario, solo con la veste valorizzata; poi quello dell''azienda, se accesa; poi quello di sistema), poi il catalogo (tutti i widget accesi del pool). Poi il merge dei widget nuovi del pool, il filtro dei permessi per area e azione (mappe aggregate script.fn_get_user_permissions_map e fn_get_user_actions_map, fail-closed fuori dalla veste OPERATORE) e i campi opachi freschi (deep_link, contatore_key, soglia, etichette, tipo_widget). Una riga della preferenza fuori forma non fa cadere la funzione: ordine e dimensione passano da ui.fn_intero_da_jsonb, un campo che manca prende il default del pool, una voce senza codice o fuori dal pool si salta, un codice ripetuto vale una volta. Uscite: widget, dimensione_max e dimensione_max_standard (senza la preferenza), origine (per chiave: preferenza, ruolo, emittente_fiscale, sistema o catalogo), widget_nuovi (le card nuove del pool che l''utente può vedere: contate dopo il filtro dei permessi), preset_base (id, ambito e contenuto_aggiornato_il, la data del contenuto per chiave, del preset di base di oggi, o null), preset_base_cambiato (la preferenza ha salvato una base che non è quella di oggi), preset_aggiornato_chiavi (solo sulla base di oggi: le chiavi di origine preferenza il cui contenuto nel preset è cambiato dopo lo snapshot salvato con la preferenza, ui.fn_preset_aggiornato; vuoto se nessuna; chiudere il banner è riscrivere preset_base_id) e preset_aggiornato (almeno una). Dashboard assente o spenta: E_UI_DASHBOARD_NON_TROVATA. La veste la legge ui.fn_veste_corrente. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
