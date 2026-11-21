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
-- Scopo: la configurazione effettiva di una lista per un utente, pronta
--   per il frontend.
-- Cascata per chiave: colonne, ordinamento, filtri e pagina_dimensione
--   vengono ognuna dal primo livello che la contiene: la preferenza, poi il
--   preset di base (ui.fn_preset_di_base), poi il catalogo. Poi il merge
--   delle colonne nuove, la normalizzazione, il filtro dei permessi di
--   colonna (ui.fn_lista_colonne_livello) e la misura di pagina dal catalogo.
-- Il banner: preset_base_cambiato se la base salvata non e' quella di oggi,
--   altrimenti le chiavi di origine 'preferenza' il cui contenuto nel preset
--   e' cambiato dopo lo snapshot (ui.fn_preset_aggiornato).
DECLARE
  -- La riga della lista, letta una volta dal BB: id, multi_emittente,
  -- perimetro_emittente e ricerca_min_caratteri vengono tutti da qui.
  v_lista            ui.lista_definizione%ROWTYPE;
  v_lista_id         ui.lista_definizione.id%TYPE;
  v_config_colonne   JSONB;
  v_ordinamento      ui.lista_preset.ordinamento_default%TYPE;
  v_filtri           ui.lista_preset.filtri_default%TYPE;
  -- La misura che risponde: la decide il passo 5-ter, dal catalogo.
  v_pagina_dim       ui.lista_preset.pagina_dimensione%TYPE;
  v_colonne_nuove    INTEGER := 0;
  -- I codici mergiati dal catalogo al passo 3. Servono al passo 5-bis per
  -- ricontarli DOPO il filtro dei permessi: senza, il contatore annuncia
  -- colonne che la funzione ha appena tolto.
  v_codici_mergiati  TEXT[]  := ARRAY[]::TEXT[];

  -- La veste corrente dalla GUC; NULL se assente o fuori dominio (la regola
  --   sta nel building block): senza veste il preset di ruolo non concorre.
  v_ruolo_guc        config.ruolo_applicativo := ui.fn_veste_corrente();

  -- Le quattro chiavi della preferenza, ognuna per conto suo.
  --   NULL = chiave assente (o null): «come lo standard».
  v_pref_colonne     ui.lista_preferenza_utente.configurazione%TYPE;
  v_pref_ordinamento ui.lista_preferenza_utente.configurazione%TYPE;
  v_pref_filtri      ui.lista_preferenza_utente.configurazione%TYPE;
  v_pref_pagina      ui.lista_preset.pagina_dimensione%TYPE;
  -- Il preset di base (passo 2b), letto anche quando c'e' una
  --   preferenza: e' lo standard delle chiavi che la preferenza non ha.
  v_preset_colonne     JSONB;
  v_preset_ordinamento ui.lista_preset.ordinamento_default%TYPE;
  v_preset_filtri      ui.lista_preset.filtri_default%TYPE;
  v_preset_pagina      ui.lista_preset.pagina_dimensione%TYPE;
  v_preset_livello     ui.lista_preset.ambito%TYPE;
  -- La misura senza la preferenza, e da dove viene.
  v_pagina_standard    ui.lista_preset.pagina_dimensione%TYPE;
  -- Tipi espliciti: un esito e un'etichetta calcolati qui, nessuna colonna
  -- di cui siano il riflesso (l'etichetta e' un ambito_preset reso a testo,
  -- oppure 'preferenza' o 'catalogo').
  v_pref_pagina_ok     BOOLEAN;
  v_preset_pagina_ok   BOOLEAN;
  v_origine_pagina     TEXT;

  -- Il preset di base salvato con la preferenza e il suo snapshot ({chiave: data}).
  v_pref_preset_base_id    ui.lista_preferenza_utente.preset_base_id%TYPE;
  v_pref_preset_base_ts    ui.lista_preferenza_utente.preset_base_contenuto_aggiornato_il%TYPE;
  -- Il preset di base, scelto da ui.fn_preset_di_base: id e data del
  -- contenuto per chiave (l'ambito sta in v_preset_livello).
  v_base_id                ui.lista_preset.id%TYPE;
  v_base_contenuto         ui.lista_preset.contenuto_aggiornato_il%TYPE;
  -- jsonb nudo: da dove viene ogni chiave, calcolato qui; e' l'uscita origine.
  v_origine                JSONB;
  -- Tipi espliciti: esiti calcolati qui, nessuna colonna di cui siano il riflesso.
  v_preset_aggiornato_chiavi TEXT[] := ARRAY[]::TEXT[];
  v_preset_base_cambiato   BOOLEAN := FALSE;
BEGIN
  -- -------------------------------------------------------
  -- 0. La riga della lista dal codice (dal BB)
  -- -------------------------------------------------------
  -- ⚠️ Una lettura sola: multi_emittente, perimetro_emittente e la soglia
  --   della ricerca si prendono da questa riga. Una seconda query sulla
  --   stessa riga sarebbe un round-trip in piu' su una funzione che gira a
  --   ogni apertura di lista. Lista assente o spenta: E_UI_LISTA_NON_TROVATA,
  --   sollevato dal BB.
  v_lista    := ui.fn_lista_da_codice(p_lista_codice);
  v_lista_id := v_lista.id;

  -- 1. I profili applicabili li legge ui.fn_preset_di_base, che sceglie il
  --    preset di base; il livello di colonna li legge per conto suo
  --    (ui.fn_lista_colonne_livello).

  -- -------------------------------------------------------
  -- 2. Cascata per chiave: si leggono la preferenza e il preset di base,
  --    poi ogni chiave prende il primo dei due che la contiene, e il
  --    catalogo se nessuno dei due. Una preferenza di sole colonne non
  --    scavalca l'ordinamento, i filtri e la misura del preset.
  -- -------------------------------------------------------

  -- 2a. Preferenza personale utente: ogni chiave per conto suo.
  --     Chiave assente o null = «come lo standard» (NULLIF sul null JSON).
  --     Legge anche preset_base_id e lo snapshot, per il banner (passo 5-quater).
  SELECT
      NULLIF(pu.configurazione -> 'colonne',     'null'::JSONB),
      NULLIF(pu.configurazione -> 'ordinamento', 'null'::JSONB),
      NULLIF(pu.configurazione -> 'filtri',      'null'::JSONB),
      -- Nessun cast che possa cadere: un valore che intero non e' vale «nessuna
      -- scelta» (lo rifiuta alla scrittura il guard della preferenza).
      CASE WHEN (pu.configurazione ->> 'pagina_dimensione') ~ '^[0-9]{1,9}$'
           THEN (pu.configurazione ->> 'pagina_dimensione')::INTEGER END,
      pu.preset_base_id,
      pu.preset_base_contenuto_aggiornato_il
    INTO v_pref_colonne, v_pref_ordinamento, v_pref_filtri, v_pref_pagina,
         v_pref_preset_base_id, v_pref_preset_base_ts
    FROM ui.lista_preferenza_utente pu
   WHERE pu.auth_user_id = p_auth_user_id
     AND pu.lista_id    = v_lista_id;

  -- 2b. Il preset di base: lo sceglie ui.fn_preset_di_base, la sede comune
  --     a liste e dashboard (acceso e con almeno una colonna attiva; il
  --     ruolo solo con la veste, l'azienda solo accesa, poi il sistema). Si
  --     cerca sempre, anche con una preferenza: e' lo standard delle chiavi
  --     che la preferenza non ha, e la base del banner.
  SELECT b.preset_id, b.ambito, b.contenuto_aggiornato_il
    INTO v_base_id, v_preset_livello, v_base_contenuto
    FROM ui.fn_preset_di_base('lista', v_lista_id, p_auth_user_id, v_ruolo_guc,
                              p_emittente_fiscale_id) b;

  IF v_base_id IS NOT NULL THEN
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
      INTO v_preset_colonne, v_preset_ordinamento, v_preset_filtri, v_preset_pagina
      FROM ui.lista_preset lp
     WHERE lp.id = v_base_id;
  END IF;

  -- Le tre chiavi semplici: la preferenza, poi il preset di base.
  v_ordinamento := COALESCE(v_pref_ordinamento, v_preset_ordinamento);
  v_filtri      := COALESCE(v_pref_filtri,      v_preset_filtri);
  v_config_colonne := COALESCE(v_pref_colonne, v_preset_colonne);

  -- 2e. Catalogo grezzo (fallback finale), solo per le colonne: se ne' la
  --     preferenza ne' un preset le hanno.
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
  -- 4. Il livello effettivo per colonna lo da' ui.fn_lista_colonne_livello,
  --    letto nel passo 5 (grant del profilo piu' specifico, a parita' il piu'
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
  --    - aggiunge etichetta_i18n_key (NULL se non valorizzata)
  --    - aggiunge priorita (fresca da ui.lista_colonna, non dal candidato)
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
  -- 5-ter. La misura di pagina, per chiave.
  --   Lo standard: la misura del preset di base se e' nel catalogo,
  --   altrimenti il default PAGINA del catalogo. Risponde la misura della
  --   preferenza se e' nel catalogo, altrimenti lo standard: una misura
  --   salvata e poi uscita dal catalogo non e' piu' una scelta che vale, e
  --   origine non la dice 'preferenza' (il FE non la rimanda).
  -- -------------------------------------------------------
  v_pref_pagina_ok   := COALESCE(ui.fn_misura_pagina_ammessa(v_pref_pagina), FALSE);
  v_preset_pagina_ok := COALESCE(ui.fn_misura_pagina_ammessa(v_preset_pagina), FALSE);

  v_pagina_standard := CASE WHEN v_preset_pagina_ok THEN v_preset_pagina
                            ELSE ui.fn_misura_pagina_default('PAGINA') END;
  v_pagina_dim      := CASE WHEN v_pref_pagina_ok THEN v_pref_pagina
                            ELSE v_pagina_standard END;
  v_origine_pagina  := CASE WHEN v_pref_pagina_ok   THEN 'preferenza'
                            WHEN v_preset_pagina_ok THEN v_preset_livello::text
                            ELSE 'catalogo' END;

  -- Per ognuna delle quattro chiavi, il livello da cui viene: 'preferenza',
  --   un ambito di ui.ambito_preset ('ruolo', 'emittente_fiscale',
  --   'sistema') o 'catalogo'. Il FE rimanda al salvataggio solo le chiavi
  --   'preferenza', piu' quella toccata: senza, salvare una chiave congela
  --   anche le altre tre. Il banner guarda solo le chiavi 'preferenza'.
  v_origine := jsonb_build_object(
    'colonne',     CASE WHEN v_pref_colonne   IS NOT NULL THEN 'preferenza'
                        WHEN v_preset_colonne IS NOT NULL THEN v_preset_livello::text
                        ELSE 'catalogo' END,
    'ordinamento', CASE WHEN v_pref_ordinamento IS NOT NULL THEN 'preferenza'
                        ELSE COALESCE(v_preset_livello::text, 'catalogo') END,
    'filtri',      CASE WHEN v_pref_filtri IS NOT NULL THEN 'preferenza'
                        ELSE COALESCE(v_preset_livello::text, 'catalogo') END,
    'pagina_dimensione', v_origine_pagina
  );

  -- -------------------------------------------------------
  -- 5-quater. Il banner. preset_base_cambiato: la preferenza ha salvato
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
  -- 6. Ritorna il JSONB finale
  -- -------------------------------------------------------
  RETURN jsonb_build_object(
    'colonne',           v_config_colonne,
    'ordinamento',       COALESCE(v_ordinamento, '[]'::JSONB),
    'filtri',            COALESCE(v_filtri, '{}'::JSONB),
    'pagina_dimensione', v_pagina_dim,
    -- La misura che la cascata darebbe senza la preferenza (il drawer:
    --   «Come lo standard (N)»). Chiave ADDITIVA.
    'pagina_dimensione_standard', v_pagina_standard,
    -- Per chiave, il livello da cui viene (passo 5-ter). Chiave ADDITIVA.
    'origine',           v_origine,
    -- La soglia della ricerca libera, una proprieta' della
    --   LISTA (non del preset, non dell'utente): sotto questo numero di
    --   caratteri il termine non si manda. E' la stessa colonna che legge il
    --   BB di ricerca del backend: una sede, due lettori. Chiave ADDITIVA.
    'ricerca_min_caratteri', v_lista.ricerca_min_caratteri,
    'colonne_nuove',     v_colonne_nuove,
    'preset_aggiornato', cardinality(v_preset_aggiornato_chiavi) > 0,
    -- Le chiavi in banner, ordinate; vuoto se nessuna. Chiave ADDITIVA.
    'preset_aggiornato_chiavi', to_jsonb(v_preset_aggiornato_chiavi),
    -- Il preset di base di oggi (id, ambito, data del contenuto per chiave),
    --   o null: il BE lo salva con la preferenza. Chiave ADDITIVA.
    'preset_base',       CASE WHEN v_base_id IS NULL THEN NULL
                              ELSE jsonb_build_object('id', v_base_id,
                                                      'ambito', v_preset_livello::text,
                                                      'contenuto_aggiornato_il', v_base_contenuto) END,
    -- La base salvata non e' quella di oggi: il banner propone il
    --   riallineamento. Chiave ADDITIVA.
    'preset_base_cambiato', v_preset_base_cambiato,
    -- ⭐ La lista dichiara se sa reggere piu' emittenti.
    --   Chiave ADDITIVA: i consumatori che non la leggono non si accorgono
    --   di niente. COALESCE difensivo — la colonna e' NOT NULL DEFAULT false,
    --   ma se la SELECT non ha trovato la riga siamo gia' usciti con errore.
    -- ⚠️ NON E' UN PERMESSO: non dice cosa l'utente puo' vedere (quello lo
    --   decidono lo scope e la RLS), dice se la SCHERMATA e' leggibile nella
    --   condizione in cui sta per essere aperta. Chi la usa come controllo di
    --   autorizzazione crea una seconda via d'accesso accanto a quella vera.
    'multi_emittente',   COALESCE(v_lista.multi_emittente, false),
    -- ⭐ Il terzo caso, e senza di lui il flag sopra risponde a
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
IS 'La configurazione effettiva di una lista per un utente, pronta per il frontend. Cascata per chiave: colonne, ordinamento, filtri e pagina_dimensione vengono ognuna dal primo livello che la contiene: la preferenza (una chiave assente vuol dire «come lo standard»), poi il preset di base scelto da ui.fn_preset_di_base (acceso e con almeno una colonna attiva: il preset di ruolo del profilo piu'' prioritario, solo con la veste valorizzata; poi quello dell''azienda, se accesa; poi quello di sistema), poi il catalogo. Poi il merge delle colonne nuove (colonne_nuove le conta dopo il filtro dei permessi), la normalizzazione (identificatori e azioni visibili, identificatori fissati), il filtro dei permessi di colonna (ui.fn_lista_colonne_livello: BLOCCATO esce, LETTURA non si esporta), etichetta_i18n_key e priorita fresche dal catalogo, e la misura di pagina dal catalogo ui.misure_pagina. Uscite: colonne, ordinamento, filtri, pagina_dimensione e pagina_dimensione_standard (la misura senza la preferenza), origine (per chiave: preferenza, ruolo, emittente_fiscale, sistema o catalogo; il FE rimanda al salvataggio solo le chiavi preferenza), ricerca_min_caratteri (la soglia della ricerca libera della lista), colonne_nuove, preset_base (id, ambito e contenuto_aggiornato_il, la data del contenuto per chiave, del preset di base di oggi, o null: il BE lo salva con la preferenza), preset_base_cambiato (la preferenza ha salvato una base che non e'' quella di oggi), preset_aggiornato_chiavi (solo sulla base di oggi: le chiavi di origine preferenza il cui contenuto nel preset e'' cambiato dopo lo snapshot salvato con la preferenza, ui.fn_preset_aggiornato; vuoto se nessuna; chiudere il banner e'' riscrivere preset_base_id) e preset_aggiornato (almeno una), multi_emittente (la lista sa dire l''emittente di ogni riga: non e'' un permesso) e perimetro_emittente (false: catalogo globale, la domanda dell''emittente non si applica). La riga della lista la legge ui.fn_lista_da_codice (E_UI_LISTA_NON_TROVATA), la veste ui.fn_veste_corrente. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
