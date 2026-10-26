{% include-markdown "it/dbzero/pratiche/manual/fn_guard_ripetibilita_flusso.md" %}
# ⚙️ Funzione `fn_guard_ripetibilita_flusso`

```sql
CREATE FUNCTION fn_guard_ripetibilita_flusso(p_pratica_id bigint, p_template_flusso_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_guard_ripetibilita_flusso(p_pratica_id bigint, p_template_flusso_id integer)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_codice         pratiche.template_flussi.codice%TYPE;
    v_ripetibilita   pratiche.template_flussi.ripetibilita%TYPE;
    v_ultimo_stato   config.stati_flussi_pratiche.codice_interno%TYPE;
    v_ultimo_esito   pratiche.flussi.esito%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Guard fail-fast (fn_guard_*): solleva errore se la
  --   regola di ripetibilita' del template vieta una nuova
  --   istanza nella pratica.
  --
  -- Dipendenze:
  --   - pratiche.fn_check_ripetibilita_flusso()
  --   - script.fn_log_and_raise_error()
  --   - config.messaggi_errore: PRATICHE_FLUSSO_NON_RIPETIBILE
  -- =========================================================

  IF pratiche.fn_check_ripetibilita_flusso(p_pratica_id, p_template_flusso_id) THEN
    RETURN;
  END IF;

  -- Contesto per il messaggio: regola + ultima istanza valida.
  SELECT tf.codice, tf.ripetibilita
    INTO v_codice, v_ripetibilita
    FROM pratiche.template_flussi tf
   WHERE tf.id = p_template_flusso_id;

  SELECT sfp.codice_interno, f.esito
    INTO v_ultimo_stato, v_ultimo_esito
    FROM pratiche.flussi f
    JOIN config.stati_flussi_pratiche sfp ON sfp.id = f.stato_id
   WHERE f.pratica_id         = p_pratica_id
     AND f.template_flusso_id = p_template_flusso_id
     AND sfp.codice_interno  <> 'ANNULLATO'
   ORDER BY f.id DESC
   LIMIT 1;

  PERFORM script.fn_log_and_raise_error(
    'pratiche',
    'pratiche.fn_guard_ripetibilita_flusso',
    'E_PRATICHE_FLUSSO_NON_RIPETIBILE',
    jsonb_build_object(
      'pratica_id', p_pratica_id,
      'template_flusso_id', p_template_flusso_id,
      'template_codice', v_codice,
      'ripetibilita', v_ripetibilita,
      'ultima_istanza_stato', v_ultimo_stato,
      'ultima_istanza_esito', v_ultimo_esito
    ),
    NULL::uuid,
    coalesce(v_codice, p_template_flusso_id::text),
    coalesce(v_ripetibilita, '?'),
    concat(coalesce(v_ultimo_stato, '?'),
           coalesce('/' || v_ultimo_esito, ''))
  );
END;
$function$

COMMENT ON FUNCTION pratiche.fn_guard_ripetibilita_flusso(p_pratica_id bigint, p_template_flusso_id integer)
IS 'Guard fail-fast: solleva PRATICHE_FLUSSO_NON_RIPETIBILE se la regola di ripetibilita'' del template vieta una nuova istanza nella pratica.';
```

</div>

---
{% include-markdown "signature-core.md" %}
