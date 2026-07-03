{% include-markdown "it/dbzero/pratiche/manual/fn_nuova_versione_definizione.md" %}
# ⚙️ Funzione `fn_nuova_versione_definizione`

```sql
CREATE FUNCTION fn_nuova_versione_definizione(p_definizione_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_nuova_versione_definizione(p_definizione_id integer)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: creare una nuova versione BOZZA nello stesso scope della
--        sorgente (stesso emittente, preset incluso). Per modificare
--        in sicurezza un'edizione gia' pubblicata.
DECLARE
  v_emittente pratiche.workflow_definizioni.emittente_fiscale_id%TYPE;
  v_found     boolean;
BEGIN
  SELECT wd.emittente_fiscale_id, true
    INTO v_emittente, v_found
    FROM pratiche.workflow_definizioni wd
   WHERE wd.id = p_definizione_id;

  IF v_found IS NOT TRUE THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_nuova_versione_definizione', 'E_VALORE_MANCANTE',
      jsonb_build_object('definizione_sorgente_id', p_definizione_id),
      NULL::uuid, concat('workflow_definizioni id ', p_definizione_id));
  END IF;

  RETURN pratiche.fn_copia_definizione(p_definizione_id, v_emittente, false);
END;
$function$

COMMENT ON FUNCTION pratiche.fn_nuova_versione_definizione(p_definizione_id integer)
IS 'Crea una nuova versione BOZZA nello stesso scope (tipo+emittente) della definizione sorgente, senza provenance. Per modificare in sicurezza un''edizione pubblicata (bozza -> modifica -> fn_pubblica_definizione, che ritira la precedente). Wrapper di fn_copia_definizione(..., false).';
```

---
{% include-markdown "signature-core.md" %}
