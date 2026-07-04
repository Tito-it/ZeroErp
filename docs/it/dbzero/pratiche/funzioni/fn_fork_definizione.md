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
-- Scopo: creare l'edizione di un emittente a partire da una
--        definizione (di solito il preset), con provenance per il
--        rilevamento drift. Wrapper di fn_copia_definizione.
-- SECURITY DEFINER: la DML interna (via fn_copia) gira come owner.
BEGIN
  IF p_emittente_fiscale_id IS NULL OR p_emittente_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche', 'pratiche.fn_fork_definizione', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','p_emittente_fiscale_id',
                         'valore',p_emittente_fiscale_id),
      NULL::uuid,
      'il fork richiede un emittente valido; per una nuova versione dello stesso scope usare fn_nuova_versione_definizione');
  END IF;

  RETURN pratiche.fn_copia_definizione(p_definizione_id, p_emittente_fiscale_id, true);
END;
$function$

COMMENT ON FUNCTION pratiche.fn_fork_definizione(p_definizione_id integer, p_emittente_fiscale_id bigint)
IS 'Crea l''edizione di un emittente a partire da una definizione (di solito il preset), in stato BOZZA, con provenance (preset_origine_id/versione_origine) per il drift. Wrapper di fn_copia_definizione(..., true). Guard: emittente NOT NULL. SECURITY DEFINER (search_path fisso): la DML interna passa senza grant diretto; autorizzazione al gate app-layer (AdminAPIView).';
```

---
{% include-markdown "signature-core.md" %}
