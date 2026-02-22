{% include-markdown "it/dbzero/vendite/manual/fn_sync_attivita_stato_esecuzione.md" %}
# ⚙️ Funzione `fn_sync_attivita_stato_esecuzione`

```sql
CREATE FUNCTION fn_sync_attivita_stato_esecuzione(p_lotto_attivita_id bigint, p_target_stato_esecuzione character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_sync_attivita_stato_esecuzione(p_lotto_attivita_id bigint, p_target_stato_esecuzione character varying DEFAULT NULL::character varying)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_stato_lotto vendite.attivita_fatturabili_lotti.stato_lotto%TYPE;
  v_target vendite.attivita_fatturabili.stato_esecuzione%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Sincronizza stato_esecuzione sulle attivita del lotto.
  --
  -- Regole:
  --   - target esplicito opzionale
  --   - fallback da stato_lotto tramite helper condiviso
  --   - attivita fatturate sempre COMPLETED
  -- =========================================================

  IF p_lotto_attivita_id IS NULL OR p_lotto_attivita_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_sync_attivita_stato_esecuzione', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_attivita_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto_attivita_id obbligatorio')),
      NULL::uuid, 'lotto_attivita_id obbligatorio'
    );
  END IF;

  SELECT l.stato_lotto
    INTO v_stato_lotto
    FROM vendite.attivita_fatturabili_lotti l
   WHERE l.id = p_lotto_attivita_id
   FOR UPDATE;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_sync_attivita_stato_esecuzione', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_attivita_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto attivita non trovato')),
      NULL::uuid, 'lotto attivita non trovato'
    );
  END IF;

  v_target := upper(btrim(COALESCE(p_target_stato_esecuzione, '')));
  IF v_target IS NULL OR v_target = '' THEN
    v_target := vendite.fn_resolve_stato_esecuzione(
                  p_stato_source => v_stato_lotto,
                  p_current_stato_esecuzione => NULL::varchar,
                  p_has_critical => false,
                  p_esclusa => false,
                  p_fatturato => false,
                  p_default_stato_esecuzione => 'PENDING'
                );
  ELSE
    v_target := upper(btrim(v_target));
  END IF;

  IF v_target NOT IN ('PENDING','RUNNING','COMPLETED','ERRORE') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_sync_attivita_stato_esecuzione', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_attivita_id,'fattura_id',NULL,'context',jsonb_build_object('detail','stato_esecuzione target non valido','stato_esecuzione',v_target)),
      NULL::uuid, 'stato_esecuzione target non valido'
    );
  END IF;

  UPDATE vendite.attivita_fatturabili a
     SET stato_esecuzione = vendite.fn_resolve_stato_esecuzione(
           p_stato_source => v_target,
           p_current_stato_esecuzione => a.stato_esecuzione,
           p_has_critical => false,
           p_esclusa => false,
           p_fatturato => a.fatturato,
           p_default_stato_esecuzione => 'PENDING'
         ),
         data_update = now(),
         user_update = current_user
   WHERE a.lotto_attivita_id = p_lotto_attivita_id
     AND a.stato_esecuzione IS DISTINCT FROM vendite.fn_resolve_stato_esecuzione(
           p_stato_source => v_target,
           p_current_stato_esecuzione => a.stato_esecuzione,
           p_has_critical => false,
           p_esclusa => false,
           p_fatturato => a.fatturato,
           p_default_stato_esecuzione => 'PENDING'
         );
END
$function$

COMMENT ON FUNCTION vendite.fn_sync_attivita_stato_esecuzione(p_lotto_attivita_id bigint, p_target_stato_esecuzione character varying)
IS 'Sincronizza stato_esecuzione sulle attivita del lotto tramite helper condiviso.';
```

---
{% include-markdown "signature-core.md" %}
