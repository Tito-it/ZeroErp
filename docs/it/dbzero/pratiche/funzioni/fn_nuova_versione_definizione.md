{% include-markdown "it/dbzero/pratiche/manual/fn_nuova_versione_definizione.md" %}
# ⚙️ Funzione `fn_nuova_versione_definizione`

```sql
CREATE FUNCTION fn_nuova_versione_definizione(p_definizione_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_nuova_versione_definizione(p_definizione_id integer)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pratiche', 'script', 'config', 'dbops', 'pg_temp'
AS $function$
-- Scopo: creare una nuova versione BOZZA nello stesso scope, derivata
--        dalla PUBBLICATA corrente. Per modificare in sicurezza
--        un'edizione gia' pubblicata. SECURITY DEFINER.
DECLARE
  v_tipo_id   pratiche.workflow_definizioni.tipo_prestazione_id%TYPE;
  v_emittente pratiche.workflow_definizioni.emittente_fiscale_id%TYPE;
  v_stato     pratiche.workflow_definizioni.stato%TYPE;
  v_found     boolean;
BEGIN
  SELECT wd.tipo_prestazione_id, wd.emittente_fiscale_id, wd.stato, true
    INTO v_tipo_id, v_emittente, v_stato, v_found
    FROM pratiche.workflow_definizioni wd
   WHERE wd.id = p_definizione_id;

  IF v_found IS NOT TRUE THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_nuova_versione_definizione', 'E_VALORE_MANCANTE',
      jsonb_build_object('definizione_sorgente_id', p_definizione_id),
      NULL::uuid, concat('workflow_definizioni id ', p_definizione_id));
  END IF;

  -- (1) La nuova versione si deriva SOLO da una PUBBLICATA.
  IF v_stato <> 'PUBBLICATA' THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_nuova_versione_definizione', 'E_DEFINIZIONE_NO_PUBBLICATA',
      jsonb_build_object('definizione_id', p_definizione_id, 'stato', v_stato),
      NULL::uuid, p_definizione_id::text);
  END IF;

  -- (2) Invariante ≤1 BOZZA per scope.
  IF EXISTS (
       SELECT 1 FROM pratiche.workflow_definizioni wd
        WHERE wd.tipo_prestazione_id  = v_tipo_id
          AND wd.emittente_fiscale_id IS NOT DISTINCT FROM v_emittente
          AND wd.stato = 'BOZZA'
     ) THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_nuova_versione_definizione', 'E_DEFINIZIONE_BOZZA_ESISTENTE',
      jsonb_build_object('tipo_prestazione_id', v_tipo_id,
                         'emittente_fiscale_id', v_emittente),
      NULL::uuid,
      v_tipo_id::text,
      COALESCE(v_emittente::text, 'preset'));
  END IF;

  RETURN pratiche.fn_copia_definizione(p_definizione_id, v_emittente, false);
END;
$function$

COMMENT ON FUNCTION pratiche.fn_nuova_versione_definizione(p_definizione_id integer)
IS 'Crea una nuova versione BOZZA nello stesso scope, derivata dalla PUBBLICATA corrente (la sorgente DEVE essere PUBBLICATA: da BOZZA/RITIRATA -> DEFINIZIONE_NO_PUBBLICATA 516). Guard invariante ≤1 BOZZA per scope (DEFINIZIONE_BOZZA_ESISTENTE 515). Wrapper di fn_copia_definizione(..., false). SECURITY DEFINER (search_path fisso).';
```

</div>

---
{% include-markdown "signature-core.md" %}
