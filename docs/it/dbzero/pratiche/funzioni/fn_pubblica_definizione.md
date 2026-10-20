{% include-markdown "it/dbzero/pratiche/manual/fn_pubblica_definizione.md" %}
# ⚙️ Funzione `fn_pubblica_definizione`

```sql
CREATE FUNCTION fn_pubblica_definizione(p_definizione_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_pubblica_definizione(p_definizione_id integer)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pratiche', 'script', 'config', 'dbops', 'pg_temp'
AS $function$
-- Scopo: validare e pubblicare una BOZZA, ritirando la precedente
--        PUBBLICATA dello stesso scope (atomico).
-- SECURITY DEFINER: gli UPDATE su workflow_definizioni girano come owner.
DECLARE
  v_tipo_id   pratiche.workflow_definizioni.tipo_prestazione_id%TYPE;
  v_emittente pratiche.workflow_definizioni.emittente_fiscale_id%TYPE;
  v_stato     pratiche.workflow_definizioni.stato%TYPE;
  v_n_attivi  integer;
  v_has_cycle boolean;
BEGIN
  IF p_definizione_id IS NULL OR p_definizione_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_pubblica_definizione', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','p_definizione_id','valore',p_definizione_id),
      NULL::uuid, 'p_definizione_id obbligatorio e > 0');
  END IF;

  SELECT wd.tipo_prestazione_id, wd.emittente_fiscale_id, wd.stato
    INTO v_tipo_id, v_emittente, v_stato
    FROM pratiche.workflow_definizioni wd
   WHERE wd.id = p_definizione_id;
  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_pubblica_definizione', 'E_VALORE_MANCANTE',
      jsonb_build_object('definizione_id', p_definizione_id),
      NULL::uuid, concat('workflow_definizioni id ', p_definizione_id));
  END IF;

  -- (a) deve essere in BOZZA.
  IF v_stato <> 'BOZZA' THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_pubblica_definizione', 'E_DEFINIZIONE_NON_PUBBLICABILE',
      jsonb_build_object('definizione_id', p_definizione_id, 'stato', v_stato),
      NULL::uuid, p_definizione_id::text,
      concat('non e'' in BOZZA (stato ', v_stato, ')'));
  END IF;

  -- (b) almeno uno step attivo.
  SELECT count(*) INTO v_n_attivi
    FROM pratiche.template_flussi tf
   WHERE tf.definizione_id = p_definizione_id AND tf.attivo;
  IF v_n_attivi = 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_pubblica_definizione', 'E_DEFINIZIONE_NON_PUBBLICABILE',
      jsonb_build_object('definizione_id', p_definizione_id),
      NULL::uuid, p_definizione_id::text, 'nessuno step attivo nella definizione');
  END IF;

  -- (c) nessun ciclo nel grafo dei prerequisiti (chiusura transitiva).
  WITH RECURSIVE closure(start_node, cur) AS (
    SELECT p.template_flusso_id, p.prerequisito_id
      FROM pratiche.template_flussi_prerequisiti p
      JOIN pratiche.template_flussi t
           ON t.id = p.template_flusso_id AND t.definizione_id = p_definizione_id
    UNION
    SELECT c.start_node, p.prerequisito_id
      FROM closure c
      JOIN pratiche.template_flussi_prerequisiti p ON p.template_flusso_id = c.cur
      JOIN pratiche.template_flussi t
           ON t.id = p.template_flusso_id AND t.definizione_id = p_definizione_id
  )
  SELECT EXISTS (SELECT 1 FROM closure WHERE start_node = cur) INTO v_has_cycle;
  IF v_has_cycle THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_pubblica_definizione', 'E_DEFINIZIONE_NON_PUBBLICABILE',
      jsonb_build_object('definizione_id', p_definizione_id),
      NULL::uuid, p_definizione_id::text, 'ciclo nel grafo dei prerequisiti');
  END IF;

  -- Ritira la precedente PUBBLICATA dello scope, poi pubblica.
  UPDATE pratiche.workflow_definizioni
     SET stato = 'RITIRATA'
   WHERE tipo_prestazione_id = v_tipo_id
     AND emittente_fiscale_id IS NOT DISTINCT FROM v_emittente
     AND stato = 'PUBBLICATA';

  UPDATE pratiche.workflow_definizioni
     SET stato = 'PUBBLICATA'
   WHERE id = p_definizione_id;

  RETURN p_definizione_id;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_pubblica_definizione(p_definizione_id integer)
IS 'Valida una BOZZA e la pubblica, ritirando in transazione la precedente PUBBLICATA dello scope (una sola per scope). Validazioni fail-fast DEFINIZIONE_NON_PUBBLICABILE (511): non-BOZZA, nessuno step attivo, ciclo prerequisiti. SECURITY DEFINER (search_path fisso): gli UPDATE passano senza grant diretto; autorizzazione al gate app-layer (AdminAPIView).';
```

</div>

---
{% include-markdown "signature-core.md" %}
