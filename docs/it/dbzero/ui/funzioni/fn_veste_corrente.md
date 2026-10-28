{% include-markdown "it/dbzero/ui/manual/fn_veste_corrente.md" %}
# ⚙️ Funzione `fn_veste_corrente`

```sql
CREATE FUNCTION fn_veste_corrente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_veste_corrente()
 RETURNS config.ruolo_applicativo
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la veste corrente della sessione, per la configurazione delle
-- schermate (liste, dashboard, ricerca libera).
--
-- NULL = tutte le vesti dell'utente. Lo e' per GUC assente, vuota o con
-- un valore fuori dal dominio di config.ruolo_applicativo (bug del
-- middleware, variabile d'ambiente sbagliata): mai eccezione.
--
-- ⚠️ Semantica di PRESENTAZIONE, non di permesso: le funzioni di
--   `script` che decidono un accesso sono fail-closed sulla veste.
DECLARE
  v_raw TEXT := NULLIF(current_setting('app.ruolo_applicativo', true), '');
BEGIN
  IF v_raw IS NULL THEN
    RETURN NULL;
  END IF;

  RETURN v_raw::config.ruolo_applicativo;
EXCEPTION WHEN invalid_text_representation THEN
  RETURN NULL;
END;
$function$

COMMENT ON FUNCTION ui.fn_veste_corrente()
IS 'Veste corrente della sessione per la configurazione delle schermate: legge la GUC app.ruolo_applicativo e la converte in config.ruolo_applicativo. NULL = tutte le vesti dell''utente, sia per GUC assente o vuota sia per un valore fuori dominio: mai eccezione. Estratta il 2026-09-23 dalle due copie identiche in fn_resolve_lista_config e fn_resolve_dashboard_config (regola del 2), terzo consumatore fn_lista_colonne_ricerca_full. ⚠️ Semantica di presentazione, non di permesso: le funzioni di script che decidono un accesso sono fail-closed sulla veste. Brief: brief-db-ricerca-full-colonne-permessi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
