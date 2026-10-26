{% include-markdown "it/dbzero/vendite/manual/fn_set_fatturazione_lotto_stato.md" %}
# ⚙️ Funzione `fn_set_fatturazione_lotto_stato`

```sql
CREATE FUNCTION fn_set_fatturazione_lotto_stato(p_lotto_id bigint, p_stato_lotto text, p_note text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_set_fatturazione_lotto_stato(p_lotto_id bigint, p_stato_lotto text, p_note text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_stato_corrente vendite.fatturazione_lotti.stato_lotto%TYPE;
  v_stato_lotto_input vendite.fatturazione_lotti.stato_lotto%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Aggiorna lo stato tecnico del lotto e mantiene
  --   allineato stato_esecuzione su fatturazione_lotti_fatture.
  --
  -- Regole:
  --   - mapping stato_esecuzione delegato a helper condiviso
  --   - critical=true  -> ERRORE
  --
  -- rev 2026-08-04 (D-M): via l'argomento p_esclusa all'helper.
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

  SELECT stato_lotto
    INTO v_stato_corrente
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
         meta = CASE
                  WHEN p_note IS NULL THEN meta
                  ELSE jsonb_set(meta, '{note_stato}', to_jsonb(p_note), true)
                END,
         data_update = now(),
         user_update = current_user
   WHERE id = p_lotto_id;

  UPDATE vendite.fatturazione_lotti_fatture lf
     SET stato_esecuzione = vendite.fn_resolve_stato_esecuzione(
           p_stato_source => v_stato_lotto_input,
           p_has_critical => COALESCE(f.critical, false),
           p_fatturato => false,
           p_default_stato_esecuzione => 'PENDING'
         ),
         data_update = now(),
         user_update = current_user
    FROM vendite.fatture f
   WHERE lf.lotto_id = p_lotto_id
     AND lf.fattura_id = f.id
     AND lf.stato_esecuzione IS DISTINCT FROM vendite.fn_resolve_stato_esecuzione(
           p_stato_source => v_stato_lotto_input,
           p_has_critical => COALESCE(f.critical, false),
           p_fatturato => false,
           p_default_stato_esecuzione => 'PENDING'
         );
END
$function$

COMMENT ON FUNCTION vendite.fn_set_fatturazione_lotto_stato(p_lotto_id bigint, p_stato_lotto text, p_note text)
IS 'Aggiorna stato_lotto tecnico e sincronizza stato_esecuzione fatture tramite helper condiviso. rev 2026-08-04 (D-M): via l''argomento p_esclusa all''helper, il flag e'' dormiente e quel ramo non e'' mai stato preso.';
```

</div>

---
{% include-markdown "signature-core.md" %}
