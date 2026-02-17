{% include-markdown "it/dbzero/vendite/manual/fn_set_fatturazione_lotto_stato.md" %}
# ⚙️ Funzione `fn_set_fatturazione_lotto_stato`

```sql
CREATE FUNCTION fn_set_fatturazione_lotto_stato(p_lotto_id bigint, p_stato_lotto text, p_note text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_set_fatturazione_lotto_stato(p_lotto_id bigint, p_stato_lotto text, p_note text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_stato_corrente vendite.fatturazione_lotti.stato_lotto%TYPE;
  v_tipo_lotto vendite.fatturazione_lotti.tipo_lotto%TYPE;
  v_stato_lotto_input vendite.fatturazione_lotti.stato_lotto%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Aggiorna lo stato job del lotto e allinea lo stato operativo.
  --
  -- Regole:
  --   - IN_ESECUZIONE -> COMPLETATO | ERRORE
  --   - ERRORE -> IN_ESECUZIONE
  --   - COMPLETATO -> IN_ESECUZIONE
  -- =========================================================

  IF p_lotto_id IS NULL OR p_lotto_id <= 0 OR p_stato_lotto IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_fatturazione_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto_id e stato_lotto obbligatori')),
      NULL::uuid, 'Parametri obbligatori mancanti'
    );
  END IF;

  v_stato_lotto_input := upper(btrim(p_stato_lotto));

  IF v_stato_lotto_input NOT IN ('IN_ESECUZIONE','COMPLETATO','ERRORE') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_fatturazione_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','stato_lotto non valido', 'stato_lotto', p_stato_lotto)),
      NULL::uuid, 'stato_lotto non valido'
    );
  END IF;

  SELECT stato_lotto, tipo_lotto
    INTO v_stato_corrente, v_tipo_lotto
    FROM vendite.fatturazione_lotti
   WHERE id = p_lotto_id
   FOR UPDATE;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_fatturazione_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','lotto non trovato', 'lotto_id', p_lotto_id)),
      NULL::uuid, 
      concat('Lotto non trovato ', 'lotto_id: ', p_lotto_id::text)
    );
  END IF;

  IF v_stato_corrente = v_stato_lotto_input THEN
    RETURN;
  END IF;

  IF v_stato_corrente = 'IN_ESECUZIONE'
     AND v_stato_lotto_input NOT IN ('COMPLETATO','ERRORE') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_fatturazione_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','transizione non ammessa', 'da', v_stato_corrente, 'a', v_stato_lotto_input)),
      NULL::uuid, 
      concat('Transizione non ammessa: stato in esecuzione' , ' da ', v_stato_corrente, ' a ', v_stato_lotto_input) 
    );
  END IF;

  IF v_stato_corrente = 'ERRORE' AND v_stato_lotto_input <> 'IN_ESECUZIONE' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_fatturazione_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','transizione non ammessa', 'da', v_stato_corrente, 'a', v_stato_lotto_input)),
      NULL::uuid, 
      concat('Transizione non ammessa: stato errore' , ' da ', v_stato_corrente, ' a ', v_stato_lotto_input)
    );
  END IF;

  IF v_stato_corrente = 'COMPLETATO' AND v_stato_lotto_input <> 'IN_ESECUZIONE' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_fatturazione_lotto_stato', 'E_GENERICO',
      jsonb_build_object('scope','LOTTO','severity','C','code','E_GENERICO','lotto_id',NULL,'fattura_id',NULL,'context',jsonb_build_object('detail','transizione non ammessa', 'da', v_stato_corrente, 'a', v_stato_lotto_input)),
      NULL::uuid, 
      concat('Transizione non ammessa: stato completato' , ' da ', v_stato_corrente, ' a ', v_stato_lotto_input)
    );
  END IF;

  UPDATE vendite.fatturazione_lotti
     SET stato_lotto = v_stato_lotto_input,
         stato_operativo = CASE
                             WHEN v_stato_lotto_input = 'ERRORE' THEN 'ERRORE'
                             WHEN v_stato_lotto_input = 'IN_ESECUZIONE' THEN 'APERTO'
                             WHEN v_stato_lotto_input = 'COMPLETATO' AND v_tipo_lotto = 'MASSIVO' THEN 'CHIUSO'
                             ELSE stato_operativo
                           END,
         meta = CASE
                  WHEN p_note IS NULL THEN meta
                  ELSE jsonb_set(meta, '{note_stato}', to_jsonb(p_note), true)
                END,
         data_update = now(),
         user_update = current_user
   WHERE id = p_lotto_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_set_fatturazione_lotto_stato(p_lotto_id bigint, p_stato_lotto text, p_note text)
IS 'Aggiorna stato_lotto e allinea stato_operativo.';
```

---
{% include-markdown "signature-core.md" %}
