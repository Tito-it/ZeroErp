{% include-markdown "it/dbzero/pratiche/manual/fn_log_evento_dominio.md" %}
# ⚙️ Funzione `fn_log_evento_dominio`

```sql
CREATE FUNCTION fn_log_evento_dominio(p_pratica_id bigint, p_flusso_id bigint, p_tipo_evento text, p_meta jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_log_evento_dominio(p_pratica_id bigint, p_flusso_id bigint, p_tipo_evento text, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo:
--   Canale controllato per registrare un evento di dominio
--   (DOMINIO_*) sul giornale pratiche append-only. Usato dagli
--   handler applicativi (es. vendita.push_preventivo) per
--   tracciare DOMINIO_COMMESSA_CREATA / DOMINIO_PREVENTIVO_EVASO.
-- Regole:
--   - mappa p_tipo_evento -> azione, p_meta -> dettaglio;
--   - origine fissa 'HANDLER'; tx_id = session tx_id (correlazione);
--   - la forma DOMINIO_* la garantisce chk_giornale_azione
--     (nome non conforme -> il constraint rifiuta l'INSERT).
-- Ritorna l'id della riga giornale inserita.
-- =========================================================
DECLARE
  v_id   bigint;
  v_meta jsonb := COALESCE(p_meta, '{}'::jsonb);
BEGIN
  -- Guard parametri ID: errore esplicito se nullo o non positivo.
  IF p_pratica_id IS NULL OR p_pratica_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_log_evento_dominio',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object('param', 'p_pratica_id', 'valore', p_pratica_id),
      NULL::uuid, 'p_pratica_id'
    );
  END IF;

  -- p_flusso_id e' opzionale (eventi a livello pratica): se valorizzato deve essere positivo.
  IF p_flusso_id IS NOT NULL AND p_flusso_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_log_evento_dominio',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object('param', 'p_flusso_id', 'valore', p_flusso_id),
      NULL::uuid, 'p_flusso_id'
    );
  END IF;

  IF p_tipo_evento IS NULL OR btrim(p_tipo_evento) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_log_evento_dominio',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object('param', 'p_tipo_evento'),
      NULL::uuid, 'p_tipo_evento'
    );
  END IF;

  -- INSERT controllato: la conformita' DOMINIO_* e' enforce dal CHECK.
  INSERT INTO pratiche.giornale
    (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
  VALUES (
    p_pratica_id,
    p_flusso_id,
    p_tipo_evento,
    'HANDLER',
    v_meta,
    dbops.fn_get_or_create_session_tx_id()
  )
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_log_evento_dominio(p_pratica_id bigint, p_flusso_id bigint, p_tipo_evento text, p_meta jsonb)
IS 'Canale append-only per eventi di dominio DOMINIO_* sul giornale pratiche (origine HANDLER). La forma DOMINIO_* e'' garantita da chk_giornale_azione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
