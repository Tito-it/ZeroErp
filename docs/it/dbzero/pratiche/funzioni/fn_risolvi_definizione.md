{% include-markdown "it/dbzero/pratiche/manual/fn_risolvi_definizione.md" %}
# ⚙️ Funzione `fn_risolvi_definizione`

```sql
CREATE FUNCTION fn_risolvi_definizione(p_tipo_prestazione_id integer, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_risolvi_definizione(p_tipo_prestazione_id integer, p_emittente_fiscale_id bigint DEFAULT NULL::bigint)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: risolve l'edizione di workflow da pinnare/usare per un
--        tipo prestazione e uno scope emittente:
--        1) PUBBLICATA dell'emittente; 2) preset PUBBLICATA;
--        3) errore parlante 507. Un solo punto di risoluzione
--        (usato da auto-pin pratiche e auto-default template).
DECLARE
  v_definizione_id pratiche.workflow_definizioni.id%TYPE;
BEGIN
  -- Guard esplicito sul parametro id (no normalizzazione silenziosa).
  IF p_tipo_prestazione_id IS NULL OR p_tipo_prestazione_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche',
      'pratiche.fn_risolvi_definizione',
      'E_DEFINIZIONE_NON_TROVATA',
      jsonb_build_object(
        'motivo',               'parametro_tipo_invalido',
        'tipo_prestazione_id',  p_tipo_prestazione_id,
        'emittente_fiscale_id', p_emittente_fiscale_id
      ),
      NULL::uuid,
      COALESCE(p_tipo_prestazione_id::text, 'NULL'),
      COALESCE(p_emittente_fiscale_id::text, 'preset')
    );
  END IF;

  -- 1) Edizione pubblicata dell'emittente (fork — da Fase 2).
  IF p_emittente_fiscale_id IS NOT NULL THEN
    SELECT wd.id INTO v_definizione_id
      FROM pratiche.workflow_definizioni wd
     WHERE wd.tipo_prestazione_id  = p_tipo_prestazione_id
       AND wd.emittente_fiscale_id = p_emittente_fiscale_id
       AND wd.stato = 'PUBBLICATA';
    IF FOUND THEN
      RETURN v_definizione_id;
    END IF;
  END IF;

  -- 2) Preset pubblicato (emittente NULL).
  SELECT wd.id INTO v_definizione_id
    FROM pratiche.workflow_definizioni wd
   WHERE wd.tipo_prestazione_id = p_tipo_prestazione_id
     AND wd.emittente_fiscale_id IS NULL
     AND wd.stato = 'PUBBLICATA';
  IF FOUND THEN
    RETURN v_definizione_id;
  END IF;

  -- 3) Nessuna edizione risolvibile: errore parlante.
  PERFORM script.fn_log_and_raise_error(
    'pratiche',
    'pratiche.fn_risolvi_definizione',
    'E_DEFINIZIONE_NON_TROVATA',
    jsonb_build_object(
      'motivo',               'nessuna_pubblicata',
      'tipo_prestazione_id',  p_tipo_prestazione_id,
      'emittente_fiscale_id', p_emittente_fiscale_id
    ),
    NULL::uuid,
    p_tipo_prestazione_id::text,
    COALESCE(p_emittente_fiscale_id::text, 'preset')
  );
  RETURN NULL; -- irraggiungibile (la fn sopra solleva)
END;
$function$

COMMENT ON FUNCTION pratiche.fn_risolvi_definizione(p_tipo_prestazione_id integer, p_emittente_fiscale_id bigint)
IS 'Risolve l''edizione di workflow per (tipo prestazione, emittente): PUBBLICATA dell''emittente > preset PUBBLICATA > errore DEFINIZIONE_NON_TROVATA (507). Punto unico di risoluzione, usato dall''auto-pin delle pratiche e dall''auto-default dei template. VOLATILE perche'' il ramo di errore logga.';
```

</div>

---
{% include-markdown "signature-core.md" %}
