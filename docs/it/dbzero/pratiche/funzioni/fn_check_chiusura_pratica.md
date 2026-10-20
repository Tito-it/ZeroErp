{% include-markdown "it/dbzero/pratiche/manual/fn_check_chiusura_pratica.md" %}
# ⚙️ Funzione `fn_check_chiusura_pratica`

```sql
CREATE FUNCTION fn_check_chiusura_pratica(p_pratica_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_check_chiusura_pratica(p_pratica_id bigint)
 RETURNS TABLE(template_flusso_id integer, codice character varying, obbligatorio boolean, completato boolean, percorribile boolean, bloccante boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Fotografia dei template flusso della pratica ai fini
  --   della chiusura: eseguito? ancora percorribile?
  --   blocca la transizione a CHIUSA?
  --   Funzione fn_check_*: puro report, no raise.
  --   Fork-aware: scopa i template della DEFINIZIONE pinnata
  --   della pratica (definizione_id), non del tipo.
  -- =========================================================

  RETURN QUERY
  SELECT
    tf.id,
    tf.codice,
    tf.obbligatorio,
    -- Eseguito: almeno un'istanza COMPLETATO (qualsiasi esito).
    EXISTS (
      SELECT 1
        FROM pratiche.flussi f
        JOIN config.stati_flussi_pratiche sfp ON sfp.id = f.stato_id
       WHERE f.pratica_id         = p_pratica_id
         AND f.template_flusso_id = tf.id
         AND sfp.codice_interno   = 'COMPLETATO'
    ) AS fl_completato,
    -- Percorribile: nessun prerequisito insoddisfatto
    -- (esito-aware). Il ramo morto risulta false.
    NOT EXISTS (
      SELECT 1
        FROM pratiche.fn_check_prerequisiti_flusso(p_pratica_id, tf.id) pr
       WHERE NOT pr.soddisfatto
    ) AS fl_percorribile,
    -- Bloccante: obbligatorio, non eseguito, ancora percorribile.
    (
      tf.obbligatorio
      AND NOT EXISTS (
        SELECT 1
          FROM pratiche.flussi f
          JOIN config.stati_flussi_pratiche sfp ON sfp.id = f.stato_id
         WHERE f.pratica_id         = p_pratica_id
           AND f.template_flusso_id = tf.id
           AND sfp.codice_interno   = 'COMPLETATO'
      )
      AND NOT EXISTS (
        SELECT 1
          FROM pratiche.fn_check_prerequisiti_flusso(p_pratica_id, tf.id) pr
         WHERE NOT pr.soddisfatto
      )
    ) AS fl_bloccante
  FROM pratiche.template_flussi tf
  JOIN pratiche.pratiche p ON p.definizione_id = tf.definizione_id
  WHERE p.id = p_pratica_id
    AND tf.attivo = true;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_check_chiusura_pratica(p_pratica_id bigint)
IS 'Pure check: per ogni template attivo della DEFINIZIONE pinnata della pratica (fork-aware, definizione_id) ritorna completato (istanza COMPLETATO, qualsiasi esito), percorribile (prerequisiti esito-aware soddisfatti) e bloccante (obbligatorio non completato ancora percorribile). Il ramo morto di un bivio non blocca. Consumato dal guard di chiusura, da fn_check_pratica_chiudibile e dal percorso BE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
