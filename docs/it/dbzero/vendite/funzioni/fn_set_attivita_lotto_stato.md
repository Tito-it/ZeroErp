{% include-markdown "it/dbzero/vendite/manual/fn_set_attivita_lotto_stato.md" %}
# ⚙️ Funzione `fn_set_attivita_lotto_stato`

```sql
CREATE FUNCTION fn_set_attivita_lotto_stato(p_lotto_id bigint, p_stato_lotto text, p_note text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_set_attivita_lotto_stato(p_lotto_id bigint, p_stato_lotto text, p_note text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_stato_corrente vendite.attivita_fatturabili_lotti.stato_lotto%TYPE;
  v_stato_lotto_input vendite.attivita_fatturabili_lotti.stato_lotto%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Aggiorna stato tecnico e operativo del lotto attivita.
  --
  -- Regole:
  --   - IN_ESECUZIONE -> COMPLETATO | ERRORE
  --   - ERRORE -> IN_ESECUZIONE
  --   - COMPLETATO -> IN_ESECUZIONE
  -- =========================================================

  IF p_lotto_id IS NULL OR p_lotto_id <= 0 OR p_stato_lotto IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_attivita_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto_id e stato_lotto obbligatori')),
      NULL::uuid, 'lotto_id e stato_lotto obbligatori'
    );
  END IF;

  v_stato_lotto_input := upper(btrim(p_stato_lotto));

  IF v_stato_lotto_input NOT IN ('IN_ESECUZIONE','COMPLETATO','ERRORE') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_attivita_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','stato_lotto non valido','stato_lotto',p_stato_lotto)),
      NULL::uuid, 'stato_lotto non valido'
    );
  END IF;

  SELECT l.stato_lotto
    INTO v_stato_corrente
    FROM vendite.attivita_fatturabili_lotti l
   WHERE l.id = p_lotto_id
   FOR UPDATE;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_attivita_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto attivita non trovato')),
      NULL::uuid, 'lotto attivita non trovato'
    );
  END IF;

  IF v_stato_corrente = v_stato_lotto_input THEN
    RETURN;
  END IF;

  IF v_stato_corrente = 'IN_ESECUZIONE' AND v_stato_lotto_input NOT IN ('COMPLETATO','ERRORE') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_attivita_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','transizione non ammessa','da',v_stato_corrente,'a',v_stato_lotto_input)),
      NULL::uuid, 'transizione non ammessa'
    );
  END IF;

  IF v_stato_corrente = 'ERRORE' AND v_stato_lotto_input <> 'IN_ESECUZIONE' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_attivita_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','transizione non ammessa','da',v_stato_corrente,'a',v_stato_lotto_input)),
      NULL::uuid, 'transizione non ammessa'
    );
  END IF;

  IF v_stato_corrente = 'COMPLETATO' AND v_stato_lotto_input <> 'IN_ESECUZIONE' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_attivita_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','ATTIVITA_FATTURABILI','severity','C','code','E_GENERICO','lotto_id',p_lotto_id,'fattura_id',NULL,'context',jsonb_build_object('detail','transizione non ammessa','da',v_stato_corrente,'a',v_stato_lotto_input)),
      NULL::uuid, 'transizione non ammessa'
    );
  END IF;

  UPDATE vendite.attivita_fatturabili_lotti
     SET stato_lotto = v_stato_lotto_input,
         stato_operativo = CASE
                             WHEN v_stato_lotto_input = 'IN_ESECUZIONE' THEN 'APERTO'
                             WHEN v_stato_lotto_input = 'COMPLETATO' THEN 'CHIUSO'
                             WHEN v_stato_lotto_input = 'ERRORE' THEN 'ERRORE'
                             ELSE stato_operativo
                           END,
         meta = CASE
                  WHEN p_note IS NULL THEN meta
                  ELSE jsonb_set(meta, '{note_stato}', to_jsonb(p_note), true)
                END,
         data_update = now(),
         user_update = current_user
   WHERE id = p_lotto_id;

  PERFORM vendite.fn_sync_attivita_stato_esecuzione(p_lotto_id, NULL::varchar);
END
$function$

COMMENT ON FUNCTION vendite.fn_set_attivita_lotto_stato(p_lotto_id bigint, p_stato_lotto text, p_note text)
IS 'Aggiorna stato_lotto/stato_operativo del lotto attivita e sincronizza stato_esecuzione sulle righe.';
```

---
{% include-markdown "signature-core.md" %}
