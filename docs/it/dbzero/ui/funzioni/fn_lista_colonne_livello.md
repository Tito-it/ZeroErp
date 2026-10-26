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
-- Regola:
--   - grant dai profili applicabili all'utente sotto la veste
--     (p_veste NULL = tutte le vesti, come ui.fn_veste_corrente);
--   - fra piu' grant: il profilo piu' specifico (priorita asc), a parita'
--     il piu' restrittivo (BLOCCATO > LETTURA > TUTTO);
--   - senza grant: sensibile -> BLOCCATO, altrimenti TUTTO.
--
-- ⚠️ Una riga per OGNI colonna attiva, anche BLOCCATA: il filtro lo fa
--   chi legge. Utente NULL o senza profili: nessun grant, restano i
--   livelli di ripiego (fail-closed sulle sensibili).
BEGIN
  RETURN QUERY
  WITH pa AS MATERIALIZED (
    -- Una sola chiamata al risolutore dei profili, qualunque sia il
    -- numero di colonne.
    SELECT p.profilo_accesso_id, p.priorita
      FROM script.fn_get_profili_accesso_applicabili(p_auth_user_id, p_veste) p
  ),
  concesso AS (
    SELECT DISTINCT ON (lcp.colonna_id)
           lcp.colonna_id,
           lcp.livello_accesso
      FROM ui.lista_colonna_permesso lcp
      JOIN pa
        ON pa.profilo_accesso_id = lcp.profilo_accesso_id
      JOIN ui.lista_colonna lcg
        ON lcg.id       = lcp.colonna_id
       AND lcg.lista_id = p_lista_id
     ORDER BY lcp.colonna_id,
              pa.priorita ASC,
              CASE lcp.livello_accesso
                WHEN 'BLOCCATO' THEN 1
                WHEN 'LETTURA'  THEN 2
                WHEN 'TUTTO'    THEN 3
              END ASC
  )
  SELECT lc.id,
         lc.codice,
         COALESCE(
           c.livello_accesso,
           (CASE WHEN lc.sensibile THEN 'BLOCCATO' ELSE 'TUTTO' END)::config.livello_accesso
         )
    FROM ui.lista_colonna lc
    LEFT JOIN concesso c
      ON c.colonna_id = lc.id
   WHERE lc.lista_id = p_lista_id
     AND lc.attivo   = TRUE;
END;
$function$

COMMENT ON FUNCTION ui.fn_lista_colonne_livello(p_lista_id integer, p_auth_user_id integer, p_veste config.ruolo_applicativo)
IS 'Livello effettivo (TUTTO, LETTURA, BLOCCATO) di un utente su ogni colonna attiva di una lista, sotto una veste (NULL = tutte). Fra piu'' grant vince il profilo piu'' specifico (priorita asc), a parita'' il piu'' restrittivo; senza grant la colonna sensibile e'' BLOCCATO, le altre TUTTO. Una riga per ogni colonna attiva, anche BLOCCATA: filtra chi legge. L''emittente fiscale non entra: i grant sono per profilo d''accesso. Estratta il 2026-09-23 dai passi 4-5 di fn_resolve_lista_config (regola del 2), secondo consumatore fn_lista_colonne_ricerca_full. Brief: brief-db-ricerca-full-colonne-permessi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
