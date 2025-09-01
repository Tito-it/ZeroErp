# ⚙️ Funzione `fn_get_conto_bancario_predefinito`

```sql
CREATE FUNCTION fn_get_conto_bancario_predefinito(p_soggetto_ruolo_id bigint, p_uso character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_conto_bancario_predefinito(p_soggetto_ruolo_id bigint, p_uso character varying)
 RETURNS TABLE(conto_bancario_id bigint, fonte character varying, soggetto_ruolo_conto_id bigint, soggetto_conto_id bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_uso VARCHAR := COALESCE(p_uso, 'GENERICO');
BEGIN
  -- 1) Prova uso richiesto
  RETURN QUERY
  SELECT v.conto_bancario_id, v.fonte, v.soggetto_ruolo_conto_id, v.soggetto_conto_id
    FROM anagrafiche.vw_conti_bancari_per_ruolo v
   WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
     AND v.uso = v_uso
   LIMIT 1;
  IF FOUND THEN
    RETURN;
  END IF;

  -- 2) Fallback a GENERICO (se l’uso richiesto non è GENERICO)
  IF v_uso <> 'GENERICO' THEN
    RETURN QUERY
    SELECT v.conto_bancario_id, v.fonte, v.soggetto_ruolo_conto_id, v.soggetto_conto_id
      FROM anagrafiche.vw_conti_bancari_per_ruolo v
     WHERE v.soggetto_ruolo_id = p_soggetto_ruolo_id
       AND v.uso = 'GENERICO'
     LIMIT 1;
  END IF;
END$function$
```

---
{% include-markdown "signature-core.md" %}
