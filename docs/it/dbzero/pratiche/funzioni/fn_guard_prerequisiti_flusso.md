{% include-markdown "it/dbzero/pratiche/manual/fn_guard_prerequisiti_flusso.md" %}
# ⚙️ Funzione `fn_guard_prerequisiti_flusso`

```sql
CREATE FUNCTION fn_guard_prerequisiti_flusso(p_pratica_id bigint, p_template_flusso_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_guard_prerequisiti_flusso(p_pratica_id bigint, p_template_flusso_id integer)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_non_soddisfatti text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Guard fail-fast (fn_guard_*): solleva errore se esistono
  --   prerequisiti non soddisfatti per il template flusso.
  --
  -- Dipendenze:
  --   - pratiche.fn_check_prerequisiti_flusso()
  --   - script.fn_log_and_raise_error()
  --   - config.messaggi_errore: PRATICHE_PREREQUISITI_NON_SODDISFATTI
  -- =========================================================

  -- Raccoglie i codici dei prerequisiti non soddisfatti
  SELECT string_agg(codice, ', ')
    INTO v_non_soddisfatti
    FROM pratiche.fn_check_prerequisiti_flusso(p_pratica_id, p_template_flusso_id)
   WHERE NOT soddisfatto;

  IF v_non_soddisfatti IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'fn_guard_prerequisiti_flusso',
      'E_PRATICHE_PREREQUISITI_NON_SODDISFATTI',
      jsonb_build_object(
        'pratica_id', p_pratica_id,
        'template_flusso_id', p_template_flusso_id,
        'prerequisiti_mancanti', v_non_soddisfatti
      ),
      NULL::uuid,
      v_non_soddisfatti
    );
  END IF;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_guard_prerequisiti_flusso(p_pratica_id bigint, p_template_flusso_id integer)
IS 'Guard fail-fast: solleva eccezione se prerequisiti non soddisfatti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
