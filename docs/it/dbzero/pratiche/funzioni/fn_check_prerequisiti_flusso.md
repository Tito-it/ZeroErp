{% include-markdown "it/dbzero/pratiche/manual/fn_check_prerequisiti_flusso.md" %}
# ⚙️ Funzione `fn_check_prerequisiti_flusso`

```sql
CREATE FUNCTION fn_check_prerequisiti_flusso(p_pratica_id bigint, p_template_flusso_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_check_prerequisiti_flusso(p_pratica_id bigint, p_template_flusso_id integer)
 RETURNS TABLE(prerequisito_id integer, codice character varying, descrizione text, soddisfatto boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Verifica se tutti i prerequisiti di un template flusso
  --   sono soddisfatti per la pratica indicata.
  --   Funzione fn_check_*: puro boolean per riga, no raise.
  --
  -- Regole (esito-aware, da 2026-06-08):
  --   - Un prerequisito e' soddisfatto se esiste almeno un
  --     flusso per la stessa pratica con quel template_flusso_id
  --     in stato COMPLETATO (codice_interno) E con esito
  --     coerente: esito_richiesto IS NULL (qualsiasi esito,
  --     retro-compatibile) oppure f.esito = esito_richiesto.
  -- =========================================================

  RETURN QUERY
  SELECT
    tfp.prerequisito_id,
    tf.codice,
    tf.descrizione,
    EXISTS (
      SELECT 1
        FROM pratiche.flussi f
        JOIN config.stati_flussi_pratiche sfp ON sfp.id = f.stato_id
       WHERE f.pratica_id        = p_pratica_id
         AND f.template_flusso_id = tfp.prerequisito_id
         AND sfp.codice_interno   = 'COMPLETATO'
         AND (
               tfp.esito_richiesto IS NULL
            OR f.esito = tfp.esito_richiesto
         )
    ) AS soddisfatto
  FROM pratiche.template_flussi_prerequisiti tfp
  JOIN pratiche.template_flussi tf ON tf.id = tfp.prerequisito_id
  WHERE tfp.template_flusso_id = p_template_flusso_id;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_check_prerequisiti_flusso(p_pratica_id bigint, p_template_flusso_id integer)
IS 'Pure check: ritorna prerequisiti con flag soddisfatto per pratica/template. Esito-aware (2026-06-08): rispetta template_flussi_prerequisiti.esito_richiesto (NULL = qualsiasi esito).';
```

</div>

---
{% include-markdown "signature-core.md" %}
