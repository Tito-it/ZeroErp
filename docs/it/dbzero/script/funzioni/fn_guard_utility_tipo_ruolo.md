{% include-markdown "it/dbzero/script/manual/fn_guard_utility_tipo_ruolo.md" %}
# ⚙️ Funzione `fn_guard_utility_tipo_ruolo`

```sql
CREATE FUNCTION fn_guard_utility_tipo_ruolo(p_utility_id integer, p_tipo_ruolo_id integer, p_context text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_utility_tipo_ruolo(p_utility_id integer, p_tipo_ruolo_id integer, p_context text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_has_matrix boolean := false;
  v_is_allowed boolean := false;
BEGIN
  -- Guard parametri numerici ID: null o <= 0 non ammessi.
  IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.fn_guard_utility_tipo_ruolo',
      'ERRORE_PARAMETRI',
      jsonb_build_object(
        'detail', 'p_utility_id obbligatorio e > 0',
        'p_utility_id', p_utility_id,
        'context', p_context
      ),
      NULL::uuid,
      concat('p_utility_id non valido: ', p_utility_id::text, ' context: ', p_context)
    );
  END IF;

  IF p_tipo_ruolo_id IS NULL OR p_tipo_ruolo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.fn_guard_utility_tipo_ruolo',
      'ERRORE_PARAMETRI',
      jsonb_build_object(
        'detail', 'p_tipo_ruolo_id obbligatorio e > 0',
        'p_tipo_ruolo_id', p_tipo_ruolo_id,
        'context', p_context
      ),
      NULL::uuid,
      concat('p_tipo_ruolo_id non valido: ', p_tipo_ruolo_id::text, ' context: ', p_context)
    );
  END IF;

  -- 1) Esiste matrice attiva/valida per utility?
  SELECT EXISTS (
    SELECT 1
    FROM config.utilities_tipi_ruolo m
    WHERE m.utility_id = p_utility_id
      AND m.attivo = true
      AND (m.valido_dal IS NULL OR m.valido_dal <= CURRENT_DATE)
      AND (m.valido_al IS NULL OR m.valido_al >= CURRENT_DATE)
  )
  INTO v_has_matrix;

  -- Fail-open: nessuna regola attiva/valida -> nessun vincolo.
  IF NOT v_has_matrix THEN
    RETURN;
  END IF;

  -- 2) Se matrice presente, il ruolo deve essere esplicitamente ammesso.
  SELECT EXISTS (
    SELECT 1
    FROM config.utilities_tipi_ruolo m
    WHERE m.utility_id = p_utility_id
      AND m.tipo_ruolo_id = p_tipo_ruolo_id
      AND m.attivo = true
      AND (m.valido_dal IS NULL OR m.valido_dal <= CURRENT_DATE)
      AND (m.valido_al IS NULL OR m.valido_al >= CURRENT_DATE)
  )
  INTO v_is_allowed;

  IF NOT v_is_allowed THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      'script.fn_guard_utility_tipo_ruolo',
      'E_GENERICO',
      jsonb_build_object(
        'detail', 'Tipo ruolo non ammesso per utility in base alla matrice configurata',
        'utility_id', p_utility_id,
        'tipo_ruolo_id', p_tipo_ruolo_id,
        'context', p_context
      ),
      NULL::uuid,
      concat('Tipo ruolo non ammesso per utility: ', p_utility_id::text, 
      ' tipo_ruolo_id: ', p_tipo_ruolo_id::text)
    );
  END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_guard_utility_tipo_ruolo(p_utility_id integer, p_tipo_ruolo_id integer, p_context text)
IS 'Guard utility->tipo_ruolo: se matrice utility assente fail-open; se presente ammette solo ruoli configurati attivi/validi.';
```

---
{% include-markdown "signature-core.md" %}
