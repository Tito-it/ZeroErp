# ⚙️ Funzione `fn_guard_emittente_fiscale_utilities_required`

```sql
CREATE FUNCTION fn_guard_emittente_fiscale_utilities_required(p_emittente_soggetto_ruolo_id bigint, p_context text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_emittente_fiscale_utilities_required(p_emittente_soggetto_ruolo_id bigint, p_context text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_emittente_attivo boolean := false;
  v_has_utility boolean := false;
BEGIN
  IF p_emittente_soggetto_ruolo_id IS NULL OR p_emittente_soggetto_ruolo_id <= 0 THEN
    RETURN;
  END IF;

  SELECT ef.attivo
    INTO v_emittente_attivo
    FROM anagrafiche.emittenti_fiscali ef
   WHERE ef.soggetto_ruolo_id = p_emittente_soggetto_ruolo_id;

  IF COALESCE(v_emittente_attivo, false) IS NOT TRUE THEN
    RETURN;
  END IF;

  SELECT EXISTS (
    SELECT 1
      FROM anagrafiche.emittenti_fiscali_utilities efu
     WHERE efu.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id
       AND efu.attivo IS TRUE
  )
    INTO v_has_utility;

  IF NOT v_has_utility THEN
    PERFORM script.fn_log_and_raise_error(
      'anagrafiche',
      'fn_guard_emittente_fiscale_utilities_required',
      'E_CONFIG_MANCANTE',
      jsonb_build_object(
        'detail', 'Matrice utility obbligatoria mancante per emittente fiscale attivo',
        'emittente_soggetto_ruolo_id', p_emittente_soggetto_ruolo_id,
        'context', p_context
      ),
      NULL::uuid,
      concat(
        'Nessuna utility attiva configurata per emittente fiscale ',
        p_emittente_soggetto_ruolo_id::text
      )
    );
  END IF;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_emittente_fiscale_utilities_required(p_emittente_soggetto_ruolo_id bigint, p_context text)
IS 'Verifica che ogni emittente fiscale attivo abbia almeno una utility attiva configurata in anagrafiche.emittenti_fiscali_utilities. Errore: E_CONFIG_MANCANTE.';
```

---
{% include-markdown "signature-core.md" %}
