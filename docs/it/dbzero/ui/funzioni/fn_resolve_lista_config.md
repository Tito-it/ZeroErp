{% include-markdown "it/dbzero/ui/manual/fn_resolve_lista_config.md" %}

# ⚙️ Funzione `fn_resolve_lista_config`

```sql
CREATE FUNCTION ui.fn_resolve_lista_config(
  p_lista_codice         VARCHAR,
  p_auth_user_id         INTEGER,
  p_emittente_fiscale_id INTEGER
) RETURNS JSONB
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION ui.fn_resolve_lista_config(
  p_lista_codice         VARCHAR,
  p_auth_user_id         INTEGER,
  p_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE
)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $fn$
DECLARE
  v_lista_id       INTEGER;
  v_config_colonne JSONB;
  v_ordinamento    JSONB;
  v_filtri         JSONB;
  v_pagina_dim     INTEGER := 25;
  v_profili_ids    INTEGER[];
  v_colonne_nuove  INTEGER := 0;
  v_permessi       JSONB   := '{}'::JSONB;
BEGIN
  -- 0. Recupera lista_id dal codice
  SELECT id INTO v_lista_id
    FROM ui.lista_definizione
   WHERE codice = p_lista_codice AND attivo = TRUE;

  IF v_lista_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'ui.fn_resolve_lista_config', 'E_UI_LISTA_NON_TROVATA',
      jsonb_build_object('detail', format('codice lista: ''%s''', p_lista_codice)),
      NULL, p_lista_codice);
  END IF;

  -- 1. Risolvi profili applicabili
  SELECT ARRAY_AGG(profilo_accesso_id) INTO v_profili_ids
    FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id);
  IF v_profili_ids IS NULL THEN v_profili_ids := ARRAY[]::INTEGER[]; END IF;

  -- 2. Cascata: preferenza utente > preset ruolo > preset emittente > preset sistema > catalogo
  -- 2a. Preferenza personale
  SELECT (pu.configurazione -> 'colonne'), (pu.configurazione -> 'ordinamento'),
         (pu.configurazione -> 'filtri'), COALESCE((pu.configurazione ->> 'pagina_dimensione')::INTEGER, 25)
    INTO v_config_colonne, v_ordinamento, v_filtri, v_pagina_dim
    FROM ui.lista_preferenza_utente pu
   WHERE pu.auth_user_id = p_auth_user_id AND pu.lista_id = v_lista_id;

  -- 2b-2d. Preset profilo / emittente / sistema (omesso per brevità — logica identica)
  -- ... (vedi sorgente Liquibase per il codice completo)

  -- 3. Merge colonne nuove dal catalogo (visibile=false)
  SELECT v_config_colonne || COALESCE(jsonb_agg(...), '[]'::JSONB), COUNT(*)::INTEGER
    INTO v_config_colonne, v_colonne_nuove
    FROM ui.lista_colonna lc
   WHERE lc.lista_id = v_lista_id AND lc.attivo = TRUE
     AND lc.codice NOT IN (SELECT elem ->> 'codice' FROM jsonb_array_elements(v_config_colonne));

  -- 4. Permessi effettivi per colonna (DISTINCT ON priorita + restrittivita)
  IF array_length(v_profili_ids, 1) > 0 THEN
    SELECT jsonb_object_agg(colonna_codice, livello) INTO v_permessi
      FROM (SELECT DISTINCT ON (lc.codice) lc.codice, lcp.livello_accesso
              FROM ui.lista_colonna lc
              JOIN ui.lista_colonna_permesso lcp ON lcp.colonna_id = lc.id
              JOIN script.fn_get_profili_accesso_applicabili(p_auth_user_id) pa
                ON pa.profilo_accesso_id = lcp.profilo_accesso_id
             WHERE lc.lista_id = v_lista_id
             ORDER BY lc.codice, pa.priorita ASC,
                      CASE lcp.livello_accesso WHEN 'BLOCCATO' THEN 1
                                               WHEN 'LETTURA'  THEN 2 ELSE 3 END ASC) sub;
  END IF;

  -- 5. Applica permessi + normalizzazione obbligatorie + rimuove BLOCCATE
  SELECT jsonb_agg(jsonb_build_object(
      'codice', elem->>'codice', 'ordine', (elem->>'ordine')::INTEGER,
      'larghezza', (elem->>'larghezza')::INTEGER, 'visibile', visibile_norm,
      'fissata', fissata_norm,
      'esportabile', CASE WHEN livello_eff = 'LETTURA' THEN FALSE ELSE esportabile END,
      'tipo_colonna', tipo_colonna::text)
    ORDER BY (elem->>'ordine')::INTEGER)
    INTO v_config_colonne
    FROM (SELECT elem, lc.tipo_colonna, lc.esportabile,
                 COALESCE(v_permessi->>(elem->>'codice'),
                          CASE WHEN lc.sensibile THEN 'BLOCCATO' ELSE 'TUTTO' END) AS livello_eff,
                 CASE WHEN lc.tipo_colonna IN ('identificatore','azione') THEN TRUE
                      ELSE (elem->>'visibile')::BOOLEAN END AS visibile_norm,
                 CASE WHEN lc.tipo_colonna = 'identificatore' THEN TRUE
                      ELSE (elem->>'fissata')::BOOLEAN END AS fissata_norm
            FROM jsonb_array_elements(v_config_colonne) AS elem
            LEFT JOIN ui.lista_colonna lc ON lc.lista_id = v_lista_id
               AND lc.codice = elem->>'codice' AND lc.attivo = TRUE
           WHERE lc.id IS NOT NULL) sub
   WHERE livello_eff <> 'BLOCCATO';

  -- 6. Ritorna JSONB finale
  RETURN jsonb_build_object(
    'colonne',          COALESCE(v_config_colonne, '[]'::JSONB),
    'ordinamento',      COALESCE(v_ordinamento,    '[]'::JSONB),
    'filtri',           COALESCE(v_filtri,          '{}'::JSONB),
    'pagina_dimensione', v_pagina_dim,
    'colonne_nuove',    v_colonne_nuove
  );
END;
$fn$;

COMMENT ON FUNCTION ui.fn_resolve_lista_config(VARCHAR, INTEGER, INTEGER)
IS 'Risolve la configurazione effettiva di una lista per un utente: cascata preset, merge nuove colonne, normalizzazione obbligatorie, filtro autorizzativo. Ritorna JSONB per il frontend.';
```

---
{% include-markdown "signature-core.md" %}
