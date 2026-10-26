{% include-markdown "it/dbzero/ui/manual/fn_lista_colonne_ricerca_full.md" %}
# ⚙️ Funzione `fn_lista_colonne_ricerca_full`

```sql
CREATE FUNCTION fn_lista_colonne_ricerca_full(p_lista_codice character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_lista_colonne_ricerca_full(p_lista_codice character varying)
 RETURNS TABLE(codice character varying, campo_sorgente character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: le colonne di una lista in cui l'utente corrente puo' fare la
-- ricerca libera, con il campo della vista da interrogare.
--
-- Condizioni, tutte insieme:
--   - colonna attiva e `ricercabile_full`;
--   - campo_sorgente valorizzato (NULL e '' sono entrambi «vuoto»);
--   - livello effettivo <> BLOCCATO (LETTURA entra: si vede, si cerca).
--
-- Contesto dalla sessione: utente da app.current_user_id, veste da
-- ui.fn_veste_corrente(). L'emittente non entra nel livello di colonna.
-- ⚠️ Senza utente: nessun grant, le colonne sensibili escono.
-- 2026-09-25: la lista dal codice la legge ui.fn_lista_da_codice(), il BB
-- condiviso col risolutore delle liste (stesso E_UI_LISTA_NON_TROVATA).
DECLARE
  v_lista_id     ui.lista_definizione.id%TYPE;
  v_auth_user_id ui.lista_preferenza_utente.auth_user_id%TYPE := NULLIF(current_setting('app.current_user_id', true), '')::integer;
BEGIN
  -- Lista assente o spenta: E_UI_LISTA_NON_TROVATA, sollevato dal BB.
  v_lista_id := (ui.fn_lista_da_codice(p_lista_codice)).id;

  RETURN QUERY
  SELECT lc.codice,
         lc.campo_sorgente
    FROM ui.lista_colonna lc
    JOIN ui.fn_lista_colonne_livello(v_lista_id, v_auth_user_id, ui.fn_veste_corrente()) lv
      ON lv.colonna_id = lc.id
   WHERE lc.lista_id         = v_lista_id
     AND lc.attivo           = TRUE
     AND lc.ricercabile_full = TRUE
     AND COALESCE(btrim(lc.campo_sorgente), '') <> ''
     AND lv.livello_accesso <> 'BLOCCATO'
   ORDER BY lc.ordine_default, lc.codice;
END;
$function$

COMMENT ON FUNCTION ui.fn_lista_colonne_ricerca_full(p_lista_codice character varying)
IS 'Colonne di una lista in cui l''utente corrente puo'' fare la ricerca libera, con il campo_sorgente da interrogare: attive, ricercabile_full, campo_sorgente valorizzato (NULL e stringa vuota sono vuoto), livello effettivo diverso da BLOCCATO (LETTURA entra). Il livello viene da ui.fn_lista_colonne_livello, lo stesso di fn_resolve_lista_config: non si cerca in una colonna che la lista non mostra. Utente da app.current_user_id, veste da ui.fn_veste_corrente(); l''emittente non entra nel livello di colonna. Senza utente nessun grant: le colonne sensibili escono. Lista assente o spenta: E_UI_LISTA_NON_TROVATA, dal building block ui.fn_lista_da_codice (2026-09-25), lo stesso del risolutore. Richiesta del team BE, 2026-09-23. Brief: brief-db-ricerca-full-colonne-permessi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
