{% include-markdown "it/dbzero/ui/manual/fn_resolve_lista_config.md" %}
# ⚙️ Funzione `fn_resolve_lista_config`

```sql
CREATE FUNCTION fn_resolve_lista_config(p_lista_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_resolve_lista_config(p_lista_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Risolve la configurazione effettiva di una lista per un utente.
-- Applica cascata preset, merge nuove colonne, normalizzazione obbligatorie
-- e filtro autorizzativo colonna. Ritorna JSONB pronto per il frontend.
--
-- DB-3: step 2b usa JOIN + ORDER BY pa.priorita per cascata deterministica.
-- DB-4: legge app.ruolo_applicativo dalla GUC per filtrare la veste corrente.
--       Fallback sicuro: GUC assente/vuota/non-ENUM -> NULL -> tutte le vesti.
-- F.2:  step 5 aggiunge etichetta_i18n_key al JSONB colonna.
-- DEF-2: step 2.5 calcola preset_aggiornato (flag banner "novita' preset").
-- DB-A:  step 5 aggiunge priorita (peso ritiro dinamico FE), letta fresca
--        da ui.lista_colonna (attributo globale, non overridabile).
-- 2026-09-23: la veste la legge ui.fn_veste_corrente() e il livello di
--        colonna lo calcola ui.fn_lista_colonne_livello(): due building
--        block condivisi con la ricerca libera (fn_lista_colonne_ricerca_full).
-- 2026-09-25: la riga della lista la legge ui.fn_lista_da_codice() (BB
--        condiviso con la ricerca libera e col backend), e il JSONB porta
--        ricerca_min_caratteri, la soglia della ricerca libera della lista.
-- 2026-09-30: la misura di pagina dal catalogo ui.misure_pagina (brief-db-
--        misure-pagina-catalogo): via il 25 scritto cinque volte, e la misura
--        che risponde e' sempre una del catalogo (passo 5-ter).
DECLARE
  -- La riga della lista, letta una volta dal BB: id, multi_emittente (P-2b,
  -- 2026-08-18), perimetro_emittente (2026-09-02), ricerca_min_caratteri
  -- (2026-09-25) vengono tutti da qui.
  v_lista            ui.lista_definizione%ROWTYPE;
  v_lista_id         ui.lista_definizione.id%TYPE;
  v_config_colonne   JSONB;
  v_ordinamento      ui.lista_preset.ordinamento_default%TYPE;
  v_filtri           ui.lista_preset.filtri_default%TYPE;
  -- La misura scelta (preferenza o preset); NULL = nessuna scelta. Quella che
  -- risponde la decide il passo 5-ter, dal catalogo.
  v_pagina_dim       ui.lista_preset.pagina_dimensione%TYPE;
  v_profili_ids      INTEGER[];
  v_colonne_nuove    INTEGER := 0;
  -- I codici mergiati dal catalogo al passo 3. Servono al passo 5-bis per
  -- ricontarli DOPO il filtro dei permessi: senza, il contatore annuncia
  -- colonne che la funzione ha appena tolto (brief §4-ter).
  v_codici_mergiati  TEXT[]  := ARRAY[]::TEXT[];

  -- DB-4: veste corrente dalla GUC. NULL = tutte le vesti, anche per un
  --   valore fuori dominio: la regola sta nel building block (2026-09-23).
  v_ruolo_guc        config.ruolo_applicativo := ui.fn_veste_corrente();

  -- DEF-2: snapshot preset di base dalla preferenza utente
  v_pref_preset_base_id    ui.lista_preferenza_utente.preset_base_id%TYPE;
  v_pref_preset_base_ts    ui.lista_preferenza_utente.preset_base_data_update%TYPE;
  v_pref_preset_ignored_at ui.lista_preferenza_utente.preset_aggiornato_ignored_at%TYPE;
  -- DEF-2: data_update corrente del preset di base (lookup step 2.5)
  v_preset_data_update     ui.lista_preset.data_update%TYPE;
  -- DEF-2: flag risultato
  v_preset_aggiornato      BOOLEAN := FALSE;
BEGIN
  -- -------------------------------------------------------
  -- 0. La riga della lista dal codice (2026-09-25: dal BB)
  -- -------------------------------------------------------
  -- ⚠️ Una lettura sola: multi_emittente, perimetro_emittente e la soglia
  --   della ricerca si prendono da questa riga. Una seconda query sulla
  --   stessa riga sarebbe un round-trip in piu' su una funzione che gira a
  --   ogni apertura di lista. Lista assente o spenta: E_UI_LISTA_NON_TROVATA,
  --   sollevato dal BB.
  v_lista    := ui.fn_lista_da_codice(p_lista_codice);
  v_lista_id := v_lista.id;

  -- -------------------------------------------------------
  -- 1. Risolvi profili applicabili (DB-4: GUC-aware)
  --    v_ruolo_guc NULL = tutte le vesti (fallback legacy sicuro)
  -- -------------------------------------------------------
  SELECT ARRAY_AGG(profilo_accesso_id)
    INTO v_profili_ids
    FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id, v_ruolo_guc);

  IF v_profili_ids IS NULL THEN
    v_profili_ids := ARRAY[]::INTEGER[];
  END IF;

  -- -------------------------------------------------------
  -- 2. Cascata: trova la configurazione candidata
  -- -------------------------------------------------------

  -- 2a. Preferenza personale utente
  --     DEF-2: legge anche preset_base_id, preset_base_data_update,
  --     preset_aggiornato_ignored_at per il calcolo del flag al step 2.5.
  SELECT
      (pu.configurazione -> 'colonne'),
      (pu.configurazione -> 'ordinamento'),
      (pu.configurazione -> 'filtri'),
      -- Nessun cast che possa cadere: un valore che intero non e' vale «nessuna
      -- scelta» (lo rifiuta alla scrittura il guard della preferenza).
      CASE WHEN (pu.configurazione ->> 'pagina_dimensione') ~ '^[0-9]{1,9}$'
           THEN (pu.configurazione ->> 'pagina_dimensione')::INTEGER END,
      pu.preset_base_id,
      pu.preset_base_data_update,
      pu.preset_aggiornato_ignored_at
    INTO v_config_colonne, v_ordinamento, v_filtri, v_pagina_dim,
         v_pref_preset_base_id, v_pref_preset_base_ts, v_pref_preset_ignored_at
    FROM ui.lista_preferenza_utente pu
   WHERE pu.auth_user_id = p_auth_user_id
     AND pu.lista_id    = v_lista_id;

  -- 2b. Preset di profilo (DB-3: JOIN + ORDER BY pa.priorita ASC)
  --     AD_HOC (prio=1) prevale su REPARTO/PORTALE (prio=2)
  IF v_config_colonne IS NULL AND array_length(v_profili_ids, 1) > 0 THEN
    SELECT
        (
          SELECT jsonb_agg(
            jsonb_build_object(
              'codice',    lc.codice,
              'ordine',    pc.ordine,
              'larghezza', COALESCE(pc.larghezza, lc.larghezza_default),
              'visibile',  pc.visibile,
              'fissata',   pc.fissata
            )
            ORDER BY pc.ordine
          )
          FROM ui.lista_preset_colonna pc
          JOIN ui.lista_colonna lc ON lc.id = pc.colonna_id
         WHERE pc.preset_id = lp.id
           AND lc.attivo = TRUE
        ),
        lp.ordinamento_default,
        lp.filtri_default,
        lp.pagina_dimensione
      INTO v_config_colonne, v_ordinamento, v_filtri, v_pagina_dim
      FROM ui.lista_preset lp
      JOIN script.fn_get_profili_accesso_applicabili(p_auth_user_id, v_ruolo_guc) pa
        ON pa.profilo_accesso_id = lp.profilo_accesso_id
     WHERE lp.lista_id   = v_lista_id
       AND lp.ambito     = 'ruolo'
       AND lp.is_default = TRUE
       AND lp.attivo     = TRUE
     ORDER BY pa.priorita ASC
     LIMIT 1;
  END IF;

  -- 2c. Preset di emittente fiscale
  IF v_config_colonne IS NULL AND p_emittente_fiscale_id IS NOT NULL THEN
    SELECT
        (
          SELECT jsonb_agg(
            jsonb_build_object(
              'codice',    lc.codice,
              'ordine',    pc.ordine,
              'larghezza', COALESCE(pc.larghezza, lc.larghezza_default),
              'visibile',  pc.visibile,
              'fissata',   pc.fissata
            )
            ORDER BY pc.ordine
          )
          FROM ui.lista_preset_colonna pc
          JOIN ui.lista_colonna lc ON lc.id = pc.colonna_id
         WHERE pc.preset_id = lp.id
           AND lc.attivo = TRUE
        ),
        lp.ordinamento_default,
        lp.filtri_default,
        lp.pagina_dimensione
      INTO v_config_colonne, v_ordinamento, v_filtri, v_pagina_dim
      FROM ui.lista_preset lp
     WHERE lp.lista_id             = v_lista_id
       AND lp.ambito               = 'emittente_fiscale'
       AND lp.emittente_fiscale_id = p_emittente_fiscale_id
       AND lp.is_default           = TRUE
       AND lp.attivo               = TRUE
     LIMIT 1;
  END IF;

  -- 2d. Preset di sistema
  IF v_config_colonne IS NULL THEN
    SELECT
        (
          SELECT jsonb_agg(
            jsonb_build_object(
              'codice',    lc.codice,
              'ordine',    pc.ordine,
              'larghezza', COALESCE(pc.larghezza, lc.larghezza_default),
              'visibile',  pc.visibile,
              'fissata',   pc.fissata
            )
            ORDER BY pc.ordine
          )
          FROM ui.lista_preset_colonna pc
          JOIN ui.lista_colonna lc ON lc.id = pc.colonna_id
         WHERE pc.preset_id = lp.id
           AND lc.attivo = TRUE
        ),
        lp.ordinamento_default,
        lp.filtri_default,
        lp.pagina_dimensione
      INTO v_config_colonne, v_ordinamento, v_filtri, v_pagina_dim
      FROM ui.lista_preset lp
     WHERE lp.lista_id   = v_lista_id
       AND lp.ambito     = 'sistema'
       AND lp.is_default = TRUE
       AND lp.attivo     = TRUE
     LIMIT 1;
  END IF;

  -- 2e. Catalogo grezzo (fallback finale)
  IF v_config_colonne IS NULL THEN
    SELECT jsonb_agg(
      jsonb_build_object(
        'codice',    lc.codice,
        'ordine',    lc.ordine_default,
        'larghezza', lc.larghezza_default,
        'visibile',  TRUE,
        'fissata',   (lc.tipo_colonna = 'identificatore')
      )
      ORDER BY lc.ordine_default
    )
    INTO v_config_colonne
    FROM ui.lista_colonna lc
   WHERE lc.lista_id = v_lista_id
     AND lc.attivo   = TRUE;
  END IF;

  IF v_config_colonne IS NULL THEN
    v_config_colonne := '[]'::JSONB;
  END IF;

  -- -------------------------------------------------------
  -- 2.5 DEF-2: lookup data_update corrente del preset di base.
  --     Solo se la preferenza utente ha preset_base_id non-null
  --     E uno snapshot valorizzato (preset_base_data_update).
  --     Poi calcola il flag: TRUE sse il preset e' piu' recente
  --     dello snapshot E l'utente non ha ancora ignorato
  --     (o il preset e' cambiato di nuovo dopo l'ignore).
  -- -------------------------------------------------------
  IF v_pref_preset_base_id IS NOT NULL AND v_pref_preset_base_ts IS NOT NULL THEN
    SELECT lp.data_update
      INTO v_preset_data_update
      FROM ui.lista_preset lp
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
  -- 3. Merge automatico colonne nuove dal catalogo
  --    (presenti in catalogo ma assenti dalla configurazione)
  -- -------------------------------------------------------
  SELECT
    v_config_colonne || COALESCE(
      jsonb_agg(
        jsonb_build_object(
          'codice',    lc.codice,
          'ordine',    lc.ordine_default + 10000,
          'larghezza', lc.larghezza_default,
          'visibile',  FALSE,
          'fissata',   (lc.tipo_colonna = 'identificatore')
        )
      ),
      '[]'::JSONB
    ),
    COUNT(*)::INTEGER,
    COALESCE(array_agg(lc.codice), ARRAY[]::TEXT[])
  INTO v_config_colonne, v_colonne_nuove, v_codici_mergiati
  FROM ui.lista_colonna lc
 WHERE lc.lista_id = v_lista_id
   AND lc.attivo   = TRUE
   AND lc.codice NOT IN (
     SELECT elem ->> 'codice'
       FROM jsonb_array_elements(v_config_colonne) AS elem
   );

  -- -------------------------------------------------------
  -- 4. Livello effettivo per colonna (2026-09-23).
  --    Non si calcola piu' qui: lo da' ui.fn_lista_colonne_livello, letto
  --    nel passo 5 (grant del profilo piu' specifico, a parita' il piu'
  --    restrittivo; senza grant sensibile -> BLOCCATO, altrimenti TUTTO).
  --    ⭐ E' lo stesso calcolo della ricerca libera: una sede, due lettori.
  --    Se divergessero, la ricerca troverebbe righe per il valore di una
  --    colonna che la lista non mostra.
  -- -------------------------------------------------------

  -- -------------------------------------------------------
  -- 5. Applica permessi + normalizzazione colonne obbligatorie
  --    - tipo 'identificatore' e 'azione': forzate visibile=true
  --    - sensibile=TRUE senza grant esplicito: BLOCCATO (regola nel BB)
  --    - colonne BLOCCATE: rimosse
  --    - colonne LETTURA: esportabile=false
  --    - F.2: aggiunge etichetta_i18n_key (NULL se non valorizzata)
  --    - DB-A: aggiunge priorita (fresca da ui.lista_colonna, non dal candidato)
  -- -------------------------------------------------------
  SELECT jsonb_agg(
      jsonb_build_object(
        'codice',             elem ->> 'codice',
        'ordine',             (elem ->> 'ordine')::INTEGER,
        'larghezza',          (elem ->> 'larghezza')::INTEGER,
        'visibile',           visibile_norm,
        'fissata',            fissata_norm,
        'esportabile',        CASE WHEN livello_eff = 'LETTURA' THEN FALSE ELSE esportabile END,
        'tipo_colonna',       tipo_colonna::text,
        'etichetta_i18n_key', etichetta_i18n_key,
        'priorita',           priorita
      )
      ORDER BY (elem ->> 'ordine')::INTEGER
    )
    INTO v_config_colonne
    FROM (
      SELECT
        elem,
        lc.tipo_colonna,
        lc.esportabile,
        lc.etichetta_i18n_key,
        lc.priorita,
        lv.livello_accesso::text        AS livello_eff,
        CASE
          WHEN lc.tipo_colonna IN ('identificatore', 'azione')
            THEN TRUE
          ELSE (elem ->> 'visibile')::BOOLEAN
        END                             AS visibile_norm,
        CASE
          WHEN lc.tipo_colonna = 'identificatore'
            THEN TRUE
          ELSE (elem ->> 'fissata')::BOOLEAN
        END                             AS fissata_norm
      FROM jsonb_array_elements(v_config_colonne) AS elem
      LEFT JOIN ui.lista_colonna lc
        ON lc.lista_id = v_lista_id
       AND lc.codice   = elem ->> 'codice'
       AND lc.attivo   = TRUE
      -- Il livello: una riga per ogni colonna attiva della lista.
      JOIN ui.fn_lista_colonne_livello(v_lista_id, p_auth_user_id, v_ruolo_guc) lv
        ON lv.colonna_id = lc.id
      WHERE lc.id IS NOT NULL
    ) sub
    WHERE livello_eff <> 'BLOCCATO';

  IF v_config_colonne IS NULL THEN
    v_config_colonne := '[]'::JSONB;
  END IF;

  -- -------------------------------------------------------
  -- 5-bis. Ricalcolo di `colonne_nuove` DOPO il filtro dei permessi.
  --
  --   Il passo 3 conta le colonne mergiate dal catalogo; il passo 5 qui sopra
  --   ne toglie quelle BLOCCATO. Senza questo ricalcolo il contatore annuncia
  --   una colonna che la funzione ha appena rimosso: chi guarda vede il badge
  --   «c'e' una personalizzazione nuova», apre il pannello e non trova nulla,
  --   senza modo di distinguere fra «cerco male», «e' rotto» ed «esiste ma non
  --   mi e' concessa».
  --
  --   ⚠️ Il contatore deve dire cio' che l'utente puo' davvero TROVARE, non
  --   cio' che e' stato mergiato. I due numeri divergono ogni volta che una
  --   colonna e' `sensibile = TRUE` senza un grant in ui.lista_colonna_permesso.
  --
  --   Difetto trovato dal team BE il 2026-08-17
  --   (brief-db-dash-competenza-gruppi-cliente-e-ricerca.md §4-ter). Era
  --   LATENTE su OGNI lista, non su una sola, e non si era mai visto perche'
  --   nessuno aveva mai seminato una colonna sensibile.
  --
  --   ⚠️ La posizione e' l'intera correzione: nella funzione ci sono DUE
  --   blocchi `IF v_config_colonne IS NULL THEN`, e l'altro sta PRIMA del
  --   filtro dei permessi. Ricontare li' non correggerebbe nulla.
  -- -------------------------------------------------------
  IF v_colonne_nuove > 0 THEN
    SELECT COUNT(*)::INTEGER
      INTO v_colonne_nuove
      FROM jsonb_array_elements(v_config_colonne) AS elem
     WHERE (elem ->> 'codice') = ANY (v_codici_mergiati);
  END IF;

  -- -------------------------------------------------------
  -- 5-ter. La misura di pagina (2026-09-30): quella scelta se e' nel catalogo,
  --   altrimenti il default PAGINA del catalogo. Chiude anche il NULL del
  --   ripiego 2e (il SELECT INTO del passo 2a a zero righe azzera la misura).
  -- -------------------------------------------------------
  v_pagina_dim := CASE WHEN ui.fn_misura_pagina_ammessa(v_pagina_dim) THEN v_pagina_dim
                       ELSE ui.fn_misura_pagina_default('PAGINA') END;

  -- -------------------------------------------------------
  -- 6. Ritorna il JSONB finale
  -- -------------------------------------------------------
  RETURN jsonb_build_object(
    'colonne',           v_config_colonne,
    'ordinamento',       COALESCE(v_ordinamento, '[]'::JSONB),
    'filtri',            COALESCE(v_filtri, '{}'::JSONB),
    'pagina_dimensione', v_pagina_dim,
    -- ⭐ 2026-09-25: la soglia della ricerca libera, una proprieta' della
    --   LISTA (non del preset, non dell'utente): sotto questo numero di
    --   caratteri il termine non si manda. E' la stessa colonna che legge il
    --   BB di ricerca del backend: una sede, due lettori. Chiave ADDITIVA.
    'ricerca_min_caratteri', v_lista.ricerca_min_caratteri,
    'colonne_nuove',     v_colonne_nuove,
    'preset_aggiornato', v_preset_aggiornato,
    -- ⭐ P-2b: la lista dichiara se sa reggere piu' emittenti.
    --   Chiave ADDITIVA: i consumatori che non la leggono non si accorgono
    --   di niente. COALESCE difensivo — la colonna e' NOT NULL DEFAULT false,
    --   ma se la SELECT non ha trovato la riga siamo gia' usciti con errore.
    -- ⚠️ NON E' UN PERMESSO: non dice cosa l'utente puo' vedere (quello lo
    --   decidono lo scope e la RLS), dice se la SCHERMATA e' leggibile nella
    --   condizione in cui sta per essere aperta. Chi la usa come controllo di
    --   autorizzazione crea una seconda via d'accesso accanto a quella vera.
    'multi_emittente',   COALESCE(v_lista.multi_emittente, false),
    -- ⭐ 2026-09-02 — IL TERZO CASO, e senza di lui il flag sopra risponde a
    --   una domanda che per certe liste non esiste. `multi_emittente` dice
    --   «so dire da quale emittente arriva ogni riga»; su un catalogo GLOBALE
    --   — le famiglie di documento, le liste tecniche di `ui` — non c'e'
    --   nessun emittente da dire, e la risposta corretta non e' ne' si' ne' no:
    --   e' che la domanda non si applica.
    -- ⛔ Senza questa chiave l'unico modo di far entrare il super admin in una
    --   lista globale era dichiararla multi_emittente = true, cioe' vantare una
    --   capacita' che quella lista non ha — e la vista di certificazione
    --   dbops.vw_liste_multi_emittente_non_certificate lo intercetta, come deve.
    -- ⚠️ La regola per chi legge: si entra senza scegliere un emittente quando
    --   la lista SA DIRLO (multi_emittente) OPPURE quando non c'e' niente da
    --   dire (perimetro_emittente = false). Sono due ragioni diverse per lo
    --   stesso gesto, e vanno tenute distinte: la prima e' una capacita'
    --   conquistata, la seconda e' la natura del dato.
    'perimetro_emittente', COALESCE(v_lista.perimetro_emittente, true)
  );

END;
$function$

COMMENT ON FUNCTION ui.fn_resolve_lista_config(p_lista_codice character varying, p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'Risolve configurazione lista per un utente: cascata preset (GUC-aware, deterministica per priorita), merge nuove colonne, normalizzazione, filtro autorizzativo, etichetta_i18n_key. DEF-2 (2026-05-11): preset_aggiornato. DB-A (2026-06-02): priorita per colonna (peso ritiro dinamico FE), letta fresca da ui.lista_colonna (attributo globale, non overridabile). P-2b (2026-08-18): l''envelope porta anche multi_emittente, la capacita'' dichiarata dalla lista di reggere piu'' emittenti. Chiave ADDITIVA, letta nella SELECT che gia'' recuperava la lista (nessun round-trip in piu''). ⚠️ NON e'' un permesso: non decide cosa l''utente puo'' vedere — quello lo decidono lo scope e la RLS — ma se la SCHERMATA e'' leggibile nella condizione in cui sta per essere aperta. Brief perimetro-emittente P-2b. 2026-09-23: la veste la legge ui.fn_veste_corrente() e il livello di colonna lo calcola ui.fn_lista_colonne_livello(), building block condivisi con la ricerca libera (fn_lista_colonne_ricerca_full): una sede per il calcolo, perche'' la ricerca non trovi righe per una colonna che la lista non mostra. Brief: brief-db-ricerca-full-colonne-permessi. 2026-09-25: la riga della lista la legge ui.fn_lista_da_codice(), building block condiviso con la ricerca libera e col backend (una lettura sola, stesso E_UI_LISTA_NON_TROVATA), e il JSONB porta ricerca_min_caratteri: la soglia della ricerca libera, proprieta'' della lista (ui.lista_definizione.ricerca_min_caratteri), la stessa che legge il BB di ricerca del backend. Brief: brief-db-be-fe-ricerca-soglia-per-lista.';
```

</div>

---
{% include-markdown "signature-core.md" %}
