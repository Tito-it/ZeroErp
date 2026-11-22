{% include-markdown "it/dbzero/ui/manual/fn_dashboard_da_codice.md" %}
# ⚙️ Funzione `fn_dashboard_da_codice`

```sql
CREATE FUNCTION fn_dashboard_da_codice(p_dashboard_codice character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_dashboard_da_codice(p_dashboard_codice character varying)
 RETURNS ui.dashboard_definizione
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: la riga della dashboard con questo codice, se esiste ed e' accesa.
-- Dashboard assente o spenta: E_UI_DASHBOARD_NON_TROVATA, col codice nella frase.
DECLARE
  v_dashboard ui.dashboard_definizione%ROWTYPE;
BEGIN
  SELECT dd.*
    INTO v_dashboard
    FROM ui.dashboard_definizione dd
   WHERE dd.codice = p_dashboard_codice
     AND dd.attivo = TRUE;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'ui.fn_dashboard_da_codice',
      'E_UI_DASHBOARD_NON_TROVATA',
      jsonb_build_object('detail', format('codice dashboard: ''%s''', p_dashboard_codice)),
      NULL,
      p_dashboard_codice
    );
  END IF;

  RETURN v_dashboard;
END;
$function$

COMMENT ON FUNCTION ui.fn_dashboard_da_codice(p_dashboard_codice character varying)
IS 'La riga di ui.dashboard_definizione con questo codice, se esiste ed e'' accesa; altrimenti E_UI_DASHBOARD_NON_TROVATA, col codice nella frase. Building block: sede unica della lettura di una dashboard per codice, gemello di ui.fn_lista_da_codice. La usano ui.fn_resolve_dashboard_config e il backend; chi vuole «nessuna dashboard» al posto del rifiuto intercetta il codice. STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
