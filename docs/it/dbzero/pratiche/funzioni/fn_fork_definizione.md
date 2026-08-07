{% include-markdown "it/dbzero/pratiche/manual/fn_fork_definizione.md" %}
# ⚙️ Funzione `fn_fork_definizione`

```sql
CREATE FUNCTION fn_fork_definizione(p_definizione_id integer, p_emittente_fiscale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_fork_definizione(p_definizione_id integer, p_emittente_fiscale_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pratiche', 'script', 'config', 'dbops', 'pg_temp'
AS $function$
-- Scopo: creare l'edizione di un emittente da una definizione (di
--        solito il preset), in BOZZA, con provenance per il drift.
--        SECURITY DEFINER: la DML interna (via fn_copia) gira come owner.
DECLARE
  v_tipo_id pratiche.workflow_definizioni.tipo_prestazione_id%TYPE;
BEGIN
  IF p_emittente_fiscale_id IS NULL OR p_emittente_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_fork_definizione', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','p_emittente_fiscale_id',
                         'valore',p_emittente_fiscale_id),
      NULL::uuid,
      'il fork richiede un emittente valido; per una nuova versione dello stesso scope usare fn_nuova_versione_definizione');
  END IF;

  -- Scope destinazione = tipo della sorgente + emittente. Se la
  -- sorgente non esiste, il guard bozza si salta e fn_copia solleva
  -- E_VALORE_MANCANTE.
  SELECT wd.tipo_prestazione_id INTO v_tipo_id
    FROM pratiche.workflow_definizioni wd
   WHERE wd.id = p_definizione_id;

  IF v_tipo_id IS NOT NULL AND EXISTS (
       SELECT 1 FROM pratiche.workflow_definizioni wd
        WHERE wd.tipo_prestazione_id  = v_tipo_id
          AND wd.emittente_fiscale_id IS NOT DISTINCT FROM p_emittente_fiscale_id
          AND wd.stato = 'BOZZA'
     ) THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_fork_definizione', 'E_DEFINIZIONE_BOZZA_ESISTENTE',
      jsonb_build_object('tipo_prestazione_id', v_tipo_id,
                         'emittente_fiscale_id', p_emittente_fiscale_id),
      NULL::uuid,
      v_tipo_id::text,
      p_emittente_fiscale_id::text);
  END IF;

  RETURN pratiche.fn_copia_definizione(p_definizione_id, p_emittente_fiscale_id, true);
END;
$function$

COMMENT ON FUNCTION pratiche.fn_fork_definizione(p_definizione_id integer, p_emittente_fiscale_id bigint)
IS 'Crea l''edizione di un emittente da una definizione (di solito il preset), in BOZZA, con provenance per il drift. Wrapper di fn_copia_definizione(..., true). Guard: emittente NOT NULL; scope destinazione senza BOZZA aperta (DEFINIZIONE_BOZZA_ESISTENTE 515, invariante ≤1 BOZZA per scope). SECURITY DEFINER (search_path fisso): DML interna senza grant diretto; autorizzazione al gate app-layer (AdminAPIView).';
```

---
{% include-markdown "signature-core.md" %}
