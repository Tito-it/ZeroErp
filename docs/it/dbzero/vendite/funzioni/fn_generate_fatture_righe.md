{% include-markdown "it/dbzero/vendite/manual/fn_generate_fatture_righe.md" %}
# ⚙️ Funzione `fn_generate_fatture_righe`

```sql
CREATE FUNCTION fn_generate_fatture_righe(p_lotto_id bigint, p_dry_run boolean)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_generate_fatture_righe(p_lotto_id bigint, p_dry_run boolean DEFAULT false)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_count integer := 0;
  v_row record;
  v_fattura_id vendite.fatture.id%TYPE;
  v_group jsonb;
  v_riga_nr integer;
  v_fattura_riga_id vendite.fatture_righe.id%TYPE;
  v_lock_batch_id vendite.fatturazione_lotti.lock_batch_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Genera le righe fattura da attivita lockate sul lotto e
  --   mantiene allineato stato_esecuzione sulle attivita.
  --
  -- Regole:
  --   - prima dell'esecuzione: PENDING -> RUNNING
  --   - a riga creata: stato_esecuzione -> COMPLETED
  --   - in dry_run: nessuna mutazione stato
  -- =========================================================

  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_generate_fatture_righe', 'E_GENERICO',
      jsonb_build_object(
        'scope','FATTURA',
        'severity','C',
        'code','E_GENERICO',
        'lotto_id', p_lotto_id,
        'fattura_id', NULL,
        'context', jsonb_build_object('detail','lotto_id obbligatorio', 'lotto_id', p_lotto_id)
      ),
      NULL::uuid, 'lotto_id obbligatorio'
    );
  END IF;

  SELECT fl.lock_batch_id
    INTO v_lock_batch_id
    FROM vendite.fatturazione_lotti fl
   WHERE fl.id = p_lotto_id;

  IF NOT p_dry_run AND v_lock_batch_id IS NOT NULL THEN
    UPDATE vendite.attivita_fatturabili a
       SET stato_esecuzione = 'RUNNING',
           data_update = now(),
           user_update = current_user
     WHERE a.lock_batch_id = v_lock_batch_id
       AND a.fatturato IS FALSE
       AND COALESCE(a.lock_in_fatturazione, false) IS TRUE
       AND (
         a.stato_esecuzione IS NULL
         OR a.stato_esecuzione IN ('PENDING','RUNNING')
       );
  END IF;

  FOR v_row IN
    SELECT a.id, a.articolo_id, a.quantita, a.prezzo_unitario,
           a.uom_id, a.sorgente_tipo_id, a.sorgente_uid, a.sorgente_riga
      FROM vendite.attivita_fatturabili a
     WHERE a.lock_batch_id = v_lock_batch_id
       AND a.fatturato IS FALSE
       AND COALESCE(a.lock_in_fatturazione, false) IS TRUE
     ORDER BY a.id
  LOOP
    v_fattura_id := vendite.fn_get_or_create_fattura_header(p_lotto_id, v_row.id);
    v_group := vendite.fn_group_attivita_fatturabili(v_row.id);

    IF p_dry_run THEN
      v_count := v_count + 1;
      CONTINUE;
    END IF;

    SELECT COALESCE(max(r.riga_nr), 0) + 1
      INTO v_riga_nr
      FROM vendite.fatture_righe r
     WHERE r.fattura_id = v_fattura_id;

    INSERT INTO vendite.fatture_righe (
      fattura_id,
      riga_nr,
      articolo_id,
      descrizione,
      uom_id,
      qta,
      prezzo_unitario,
      iva_id,
      dest_billing_account_id,
      sorgente_tipo_id,
      sorgente_uid,
      sorgente_riga,
      meta
    )
    VALUES (
      v_fattura_id,
      v_riga_nr,
      v_row.articolo_id,
      (SELECT descrizione FROM catalogo.articoli WHERE id = v_row.articolo_id),
      (v_group->>'uom_id')::bigint,
      v_row.quantita,
      v_row.prezzo_unitario,
      (v_group->>'iva_id')::integer,
      (v_group->>'dest_billing_account_id')::bigint,
      v_row.sorgente_tipo_id,
      v_row.sorgente_uid,
      v_row.sorgente_riga,
      jsonb_build_object('group_key', v_group)
    )
    RETURNING id
    INTO v_fattura_riga_id;

    UPDATE vendite.attivita_fatturabili
       SET fattura_riga_id = v_fattura_riga_id,
           fatturato = true,
           stato_esecuzione = 'COMPLETED',
           data_update = now(),
           user_update = current_user
     WHERE id = v_row.id;

    v_count := v_count + 1;
  END LOOP;

  RETURN v_count;
END
$function$

COMMENT ON FUNCTION vendite.fn_generate_fatture_righe(p_lotto_id bigint, p_dry_run boolean)
IS 'Genera righe fattura da attivita lockate e aggiorna stato_esecuzione (RUNNING/COMPLETED).';
```

---
{% include-markdown "signature-core.md" %}
