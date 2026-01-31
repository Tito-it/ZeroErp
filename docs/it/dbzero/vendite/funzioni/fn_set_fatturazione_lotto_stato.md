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
  v_stato_operativo vendite.fatturazione_lotti.stato_operativo%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Aggiorna lo stato job del lotto e allinea lo stato operativo.
  --
  -- Regole:
  --   - IN_ESECUZIONE -> COMPLETATO | ERRORE
  --   - ERRORE -> IN_ESECUZIONE (reset)
  --   - COMPLETATO: stato finale (no ritorno)
  --   - MASSIVO: COMPLETATO -> stato_operativo CHIUSO
  --   - GIORNALIERO: stato_operativo gestito da stato_doc_fiscale
  -- =========================================================

  IF p_lotto_id IS NULL OR p_stato_lotto IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_fatturazione_lotto_stato', 'E_GENERICO',
      jsonb_build_object('detail','lotto_id e stato_lotto obbligatori'),
      NULL::uuid, 'Parametri obbligatori mancanti'
    );
  END IF;

  SELECT stato_lotto, tipo_lotto, stato_operativo
    INTO v_stato_corrente, v_tipo_lotto, v_stato_operativo
    FROM vendite.fatturazione_lotti
   WHERE id = p_lotto_id
   FOR UPDATE;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_fatturazione_lotto_stato', 'E_GENERICO',
      jsonb_build_object('detail','lotto non trovato', 'lotto_id', p_lotto_id),
      NULL::uuid, 
      concat('Lotto non trovato', 'lotto_id: ', p_lotto_id::text)
    );
  END IF;

  IF v_stato_corrente = p_stato_lotto THEN
    RETURN;
  END IF;

  IF v_stato_corrente = 'COMPLETATO' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_fatturazione_lotto_stato', 'E_GENERICO',
      jsonb_build_object('detail','transizione non ammessa', 'da', v_stato_corrente, 'a', p_stato_lotto),
      NULL::uuid, 
      concat('Transizione non ammessa: stato finale' , ' da ', v_stato_corrente, ' a ', p_stato_lotto)
    );
  END IF;

  IF v_stato_corrente = 'IN_ESECUZIONE'
     AND p_stato_lotto NOT IN ('COMPLETATO','ERRORE') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_fatturazione_lotto_stato', 'E_GENERICO',
      jsonb_build_object('detail','transizione non ammessa', 'da', v_stato_corrente, 'a', p_stato_lotto),
      NULL::uuid, 
      concat('Transizione non ammessa: stato in esecuzione' , ' da ', v_stato_corrente, ' a ', p_stato_lotto) 
    );
  END IF;

  IF v_stato_corrente = 'ERRORE'
     AND p_stato_lotto NOT IN ('IN_ESECUZIONE') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_set_fatturazione_lotto_stato', 'E_GENERICO',
      jsonb_build_object('detail','transizione non ammessa', 'da', v_stato_corrente, 'a', p_stato_lotto),
      NULL::uuid, 
      concat('Transizione non ammessa: stato errore' , ' da ', v_stato_corrente, ' a ', p_stato_lotto)
    );
  END IF;

  UPDATE vendite.fatturazione_lotti
     SET stato_lotto = p_stato_lotto,
         stato_operativo = CASE
                             WHEN p_stato_lotto = 'ERRORE' THEN 'ERRORE'
                             WHEN p_stato_lotto = 'COMPLETATO' AND v_tipo_lotto = 'MASSIVO' THEN 'CHIUSO'
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
```

---
{% include-markdown "signature-core.md" %}
