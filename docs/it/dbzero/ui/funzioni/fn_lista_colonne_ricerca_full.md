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
--   - campo_sorgente valorizzato (il CHECK della colonna vieta il vuoto);
--   - livello effettivo <> BLOCCATO (LETTURA entra: si vede, si cerca).
--
-- Contesto dalla sessione: utente da app.current_user_id, veste da
-- ui.fn_veste_corrente(). L'emittente non entra nel livello di colonna.
-- ⚠️ Senza utente: nessun grant, le colonne sensibili escono.
-- L'utente dal BB script.fn_utente_di_sessione: un id che non e' l'id di
-- un utente e' una chiamata fuori contesto, E_SCRIPT_CHIAMATA_NON_VALIDA.
DECLARE
  v_lista_id     ui.lista_definizione.id%TYPE;
  -- integer: l'id di django.auth_user, tabella dell'applicazione: un changeSet non
  -- la cita con %TYPE (lo schema django e' del provisioning)
  v_auth_user_id integer;
BEGIN
  -- Lista assente o spenta: E_UI_LISTA_NON_TROVATA, sollevato dal BB.
  v_lista_id := (ui.fn_lista_da_codice(p_lista_codice)).id;

  -- Dopo la lista, come prima: l'utente dal BB (GUC assente o vuota: NULL).
  v_auth_user_id := script.fn_utente_di_sessione('ui.fn_lista_colonne_ricerca_full');

  RETURN QUERY
  SELECT lc.codice,
         lc.campo_sorgente
    FROM ui.lista_colonna lc
    JOIN ui.fn_lista_colonne_livello(v_lista_id, v_auth_user_id, ui.fn_veste_corrente()) lv
      ON lv.colonna_id = lc.id
   WHERE lc.lista_id         = v_lista_id
     AND lc.attivo           = TRUE
     AND lc.ricercabile_full = TRUE
     AND lc.campo_sorgente IS NOT NULL
     AND lv.livello_accesso <> 'BLOCCATO'
   ORDER BY lc.ordine_default, lc.codice;
END;
$function$

COMMENT ON FUNCTION ui.fn_lista_colonne_ricerca_full(p_lista_codice character varying)
IS 'Le colonne di una lista in cui l''utente corrente può fare la ricerca libera, con il campo_sorgente da interrogare: accese, ricercabile_full, con un campo sorgente, a un livello effettivo diverso da BLOCCATO (LETTURA entra). Il livello viene da ui.fn_lista_colonne_livello, lo stesso di ui.fn_resolve_lista_config: non si cerca in una colonna che la lista non mostra. Utente dal building block script.fn_utente_di_sessione, veste da ui.fn_veste_corrente(); l''emittente non entra nel livello di colonna. Senza utente (GUC assente o vuota) nessun grant: le colonne sensibili escono. Un app.current_user_id che non è l''id di un utente: E_SCRIPT_CHIAMATA_NON_VALIDA, dal building block. Lista assente o spenta: E_UI_LISTA_NON_TROVATA, dal building block ui.fn_lista_da_codice. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
