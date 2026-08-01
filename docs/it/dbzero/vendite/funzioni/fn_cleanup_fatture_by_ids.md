{% include-markdown "it/dbzero/vendite/manual/fn_cleanup_fatture_by_ids.md" %}
# ⚙️ Funzione `fn_cleanup_fatture_by_ids`

```sql
CREATE FUNCTION fn_cleanup_fatture_by_ids(p_fatture_ids bigint[], p_lock_batch_id uuid)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cleanup_fatture_by_ids(p_fatture_ids bigint[], p_lock_batch_id uuid)
 RETURNS TABLE(deleted_fatture integer, deleted_righe integer, updated_attivita integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_righe_ids bigint[];
  v_deleted_fatture integer := 0;
  v_deleted_righe integer := 0;
  v_updated_attivita integer := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Cleanup centralizzato di fatture/righe e ripristino
  --   attivita_fatturabili collegate.
  --
  -- Regole:
  --   - usa GUC di manutenzione per bypass guard fatturato
  --   - su ripristino: stato_esecuzione torna a NULL
  --   - D-N pezzo 3 (C-23): PRIMA di cancellare, restituisce
  --     all'ambito di compensazione l'arrotondamento che le
  --     fatture cancellate gli avevano lasciato
  -- =========================================================
  IF p_fatture_ids IS NULL OR array_length(p_fatture_ids, 1) IS NULL THEN
    RETURN QUERY SELECT 0, 0, 0;
    RETURN;
  END IF;

  PERFORM set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true);

  -- ── D-N pezzo 3 / C-23: storno prima di ogni cancellazione ────
  -- In testa alla funzione perche' legge le fatture INTATTE: cosi'
  -- resta corretto qualunque passo venga aggiunto qui sotto.
  -- UPDATE e non upsert: se la riga d'ambito non c'e', quella
  -- fattura non ha mai contribuito e non c'e' niente da togliere —
  -- crearla con saldo negativo inventerebbe un debito.
  -- IS NOT DISTINCT FROM sulle due colonne nullable: con `=` le
  -- fatture senza modalita' (la maggioranza) non troverebbero il
  -- proprio ambito e non stornerebbero nulla, in silenzio.
  WITH storno AS (
    SELECT f.billing_account_id,
           f.utility_id,
           f.tipo_doc_fiscale_id,
           f.emittente_soggetto_ruolo_id,
           f.valuta_id,
           f.termine_pagamento_id,
           f.modalita_pagamento_id,
           SUM(COALESCE(f.arrotondamento_attuale, 0)) AS quota
      FROM vendite.fatture f
     WHERE f.id = ANY(p_fatture_ids)
       AND COALESCE(f.arrotondamento_attuale, 0) <> 0
     GROUP BY f.billing_account_id, f.utility_id, f.tipo_doc_fiscale_id,
              f.emittente_soggetto_ruolo_id, f.valuta_id,
              f.termine_pagamento_id, f.modalita_pagamento_id
  )
  UPDATE vendite.fatture_arrotondamenti_scope s
     SET saldo_arrotondamento = s.saldo_arrotondamento - st.quota
    FROM storno st
   WHERE s.billing_account_id          = st.billing_account_id
     AND s.utility_id                  = st.utility_id
     AND s.tipo_doc_fiscale_id         = st.tipo_doc_fiscale_id
     AND s.emittente_soggetto_ruolo_id = st.emittente_soggetto_ruolo_id
     AND s.valuta_id                   = st.valuta_id
     AND s.termine_pagamento_id  IS NOT DISTINCT FROM st.termine_pagamento_id
     AND s.modalita_pagamento_id IS NOT DISTINCT FROM st.modalita_pagamento_id;

  PERFORM vendite.fn_reset_fondi_fattura(f_id)
    FROM unnest(p_fatture_ids) AS f_id;

  SELECT array_agg(r.id)
    INTO v_righe_ids
    FROM vendite.fatture_righe r
   WHERE r.fattura_id = ANY(p_fatture_ids);

  IF v_righe_ids IS NULL THEN
    v_righe_ids := ARRAY[]::bigint[];
  END IF;

  DELETE FROM vendite.note
   WHERE target_tipo = 'FATTURA'
     AND target_riga_id = ANY(v_righe_ids);

  DELETE FROM vendite.note
   WHERE target_tipo = 'FATTURA'
     AND target_id = ANY(p_fatture_ids);

  DELETE FROM vendite.fatture_riepiloghi_iva
   WHERE fattura_id = ANY(p_fatture_ids);

  DELETE FROM vendite.fatture_righe
   WHERE fattura_id = ANY(p_fatture_ids);
  GET DIAGNOSTICS v_deleted_righe = ROW_COUNT;

  DELETE FROM vendite.fatture_log
   WHERE fattura_id = ANY(p_fatture_ids);

  DELETE FROM vendite.fatturazione_lotti_fatture
   WHERE fattura_id = ANY(p_fatture_ids);

  DELETE FROM vendite.fatture
   WHERE id = ANY(p_fatture_ids);
  GET DIAGNOSTICS v_deleted_fatture = ROW_COUNT;

  -- ⚠️ Il primo ramo prende TUTTE le attivita' del batch: e'
  -- voluto nel reset globale (libera anche quelle agganciate al
  -- lotto che non sono mai diventate riga) ed e' il motivo per cui
  -- il reset PER-FATTURA deve passare p_lock_batch_id NULL (C-22).
  UPDATE vendite.attivita_fatturabili
     SET lock_in_fatturazione = false,
         lock_batch_id = NULL,
         fatturato = false,
         fattura_riga_id = NULL,
         stato_esecuzione = NULL,
         data_update = now(),
         user_update = current_user
   WHERE (p_lock_batch_id IS NOT NULL AND lock_batch_id = p_lock_batch_id)
      OR fattura_riga_id = ANY(v_righe_ids);
  GET DIAGNOSTICS v_updated_attivita = ROW_COUNT;

  RETURN QUERY
  SELECT v_deleted_fatture, v_deleted_righe, v_updated_attivita;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cleanup_fatture_by_ids(p_fatture_ids bigint[], p_lock_batch_id uuid)
IS 'Cleanup centralizzato fatture/righe con ripristino attivita e reset stato_esecuzione=NULL. Da D-N pezzo 3 (C-23) restituisce all''ambito di compensazione l''arrotondamento delle fatture che cancella, PRIMA di cancellarle: senza, il saldo d''ambito diventa la somma di cio'' che e'' stato emesso e di cio'' che e'' stato buttato, e la fattura successiva eredita il riporto di un documento che non esiste piu''. Lo storno e'' un UPDATE e non un upsert (nessuna riga d''ambito = nessun contributo mai dato) e confronta le due colonne nullable con IS NOT DISTINCT FROM. ⚠️ Il ramo lock_batch_id del ripristino attivita libera TUTTO il batch: chi resetta una sola fattura deve passare NULL (C-22).';
```

---
{% include-markdown "signature-core.md" %}
