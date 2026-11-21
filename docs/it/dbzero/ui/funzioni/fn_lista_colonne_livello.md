{% include-markdown "it/dbzero/ui/manual/fn_lista_colonne_livello.md" %}
# ⚙️ Funzione `fn_lista_colonne_livello`

```sql
CREATE FUNCTION fn_lista_colonne_livello(p_lista_id integer, p_auth_user_id integer, p_veste config.ruolo_applicativo)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_lista_colonne_livello(p_lista_id integer, p_auth_user_id integer, p_veste config.ruolo_applicativo)
 RETURNS TABLE(colonna_id integer, codice character varying, livello_accesso config.livello_accesso)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il livello effettivo (TUTTO, LETTURA, BLOCCATO) che un utente ha
-- su ogni colonna attiva di una lista, sotto una veste.
--
-- Regola, per ogni veste:
--   - grant dai profili applicabili all'utente sotto quella veste;
--   - fra piu' grant: il profilo piu' specifico (priorita asc), a parita'
--     il piu' restrittivo;
--   - senza grant: sensibile -> BLOCCATO, altrimenti TUTTO.
-- Le vesti: p_veste; con p_veste NULL, tutte le vesti utilizzabili
-- dell'utente, e per ogni colonna vale il livello piu' restrittivo fra
-- loro (il ripiego non allarga mai).
--
-- ⚠️ Una riga per OGNI colonna attiva, anche BLOCCATA: il filtro lo fa
--   chi legge. Utente NULL o senza vesti: nessun grant, restano i
--   livelli di ripiego (fail-closed sulle sensibili).
DECLARE
  -- Dal piu' restrittivo al piu' largo: l'indice ordina i livelli.
  v_ordine ui.lista_colonna_permesso.livello_accesso%TYPE[] :=
    ARRAY['BLOCCATO', 'LETTURA', 'TUTTO']::config.livello_accesso[];
  v_vesti  anagrafiche.identita_digitali.ruolo_applicativo%TYPE[];
BEGIN
  IF p_veste IS NOT NULL THEN
    v_vesti := ARRAY[p_veste];
  ELSE
    v_vesti := ARRAY(
      SELECT DISTINCT idg.ruolo_applicativo
        FROM anagrafiche.identita_digitali idg
       WHERE idg.auth_user_id = p_auth_user_id
         AND script.fn_veste_utilizzabile(idg.id));
  END IF;

  RETURN QUERY
  WITH pa AS MATERIALIZED (
    -- Una chiamata al risolutore dei profili per veste, qualunque sia
    -- il numero di colonne.
    SELECT v.veste, p.profilo_accesso_id, p.priorita
      FROM unnest(v_vesti) AS v(veste)
      CROSS JOIN LATERAL script.fn_get_profili_accesso_applicabili(p_auth_user_id, v.veste) p
  ),
  concesso AS (
    SELECT DISTINCT ON (pa.veste, lcp.colonna_id)
           pa.veste,
           lcp.colonna_id,
           lcp.livello_accesso
      FROM ui.lista_colonna_permesso lcp
      JOIN pa
        ON pa.profilo_accesso_id = lcp.profilo_accesso_id
      JOIN ui.lista_colonna lcg
        ON lcg.id       = lcp.colonna_id
       AND lcg.lista_id = p_lista_id
     ORDER BY pa.veste,
              lcp.colonna_id,
              pa.priorita ASC,
              array_position(v_ordine, lcp.livello_accesso) ASC
  ),
  colonna AS (
    SELECT lc.id,
           lc.codice,
           (CASE WHEN lc.sensibile THEN 'BLOCCATO' ELSE 'TUTTO' END)::config.livello_accesso AS ripiego
      FROM ui.lista_colonna lc
     WHERE lc.lista_id = p_lista_id
       AND lc.attivo   = TRUE
  )
  SELECT c.id,
         c.codice,
         COALESCE(
           (SELECT COALESCE(k.livello_accesso, c.ripiego)
              FROM unnest(v_vesti) AS v(veste)
              LEFT JOIN concesso k
                ON k.veste      = v.veste
               AND k.colonna_id = c.id
             ORDER BY array_position(v_ordine, COALESCE(k.livello_accesso, c.ripiego)) ASC
             LIMIT 1),
           c.ripiego)
    FROM colonna c;
END;
$function$

COMMENT ON FUNCTION ui.fn_lista_colonne_livello(p_lista_id integer, p_auth_user_id integer, p_veste config.ruolo_applicativo)
IS 'Il livello effettivo (TUTTO, LETTURA, BLOCCATO) di un utente su ogni colonna attiva di una lista, una riga per colonna, anche BLOCCATA. Sotto una veste: il grant del profilo più specifico (a parità il più restrittivo), senza grant BLOCCATO per una colonna sensibile e TUTTO per le altre. Con p_veste NULL conta ogni veste utilizzabile dell''utente (script.fn_veste_utilizzabile), e per ogni colonna vale il livello più restrittivo fra loro: il ripiego non allarga mai. Utente NULL o senza vesti: i livelli senza grant. La leggono ui.fn_resolve_lista_config, ui.fn_ordinamento_lista e ui.fn_lista_colonne_ricerca_full.';
```

</div>

---
{% include-markdown "signature-core.md" %}
