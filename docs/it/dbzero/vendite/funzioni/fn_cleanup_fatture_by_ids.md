{% include-markdown "it/dbzero/vendite/manual/fn_cleanup_fatture_by_ids.md" %}
# ⚙️ Funzione `fn_cleanup_fatture_by_ids`

```sql
CREATE FUNCTION fn_cleanup_fatture_by_ids(p_fatture_ids bigint[], p_lock_batch_id uuid)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cleanup_fatture_by_ids(p_fatture_ids bigint[], p_lock_batch_id uuid)
 RETURNS TABLE(deleted_fatture integer, deleted_righe integer, updated_attivita integer, riemesse_attivita integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_righe_ids         bigint[];
  v_ca_ids            bigint[];
  v_deleted_fatture   integer := 0;
  v_deleted_righe     integer := 0;
  v_updated_attivita  integer := 0;
  v_riemesse_attivita integer := 0;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Cleanup centralizzato di fatture/righe e ripristino
  --   COMPLETO di cio' che le fatture avevano consumato:
  --   attivita_fatturabili (sblocco) e commesse_attivita
  --   (ritorno in coda di emissione).
  --
  -- Regole:
  --   - usa GUC di manutenzione per bypass guard fatturato
  --   - su ripristino: stato_esecuzione torna a NULL
  --   - D-N pezzo 3 (C-23): PRIMA di cancellare, restituisce
  --     all'ambito di compensazione l'arrotondamento che le
  --     fatture cancellate gli avevano lasciato
  --   - RD-4: il ritorno a NON_EMESSA delle commesse_attivita
  --     vive QUI e non nei chiamanti, perche' i chiamanti sono
  --     tre e la correttezza di ognuno dipende dal fatto che
  --     facciano la stessa cosa
  -- =========================================================
  IF p_fatture_ids IS NULL OR array_length(p_fatture_ids, 1) IS NULL THEN
    RETURN QUERY SELECT 0, 0, 0, 0;
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

  -- ⚠️ RD-4: si raccoglie PRIMA della UPDATE qui sotto, che azzera
  -- `fattura_riga_id` e con esso il legame. Il predicato e'
  -- IDENTICO a quello della UPDATE, di proposito: se i due
  -- divergessero si sbloccherebbe un insieme di attivita' e se ne
  -- rimetterebbe in coda un altro, in silenzio.
  SELECT array_agg(DISTINCT af.commessa_attivita_id)
    INTO v_ca_ids
    FROM vendite.attivita_fatturabili af
   WHERE af.commessa_attivita_id IS NOT NULL
     AND (
           (p_lock_batch_id IS NOT NULL AND af.lock_batch_id = p_lock_batch_id)
        OR af.fattura_riga_id = ANY(v_righe_ids)
         );

  IF v_ca_ids IS NULL THEN
    v_ca_ids := ARRAY[]::bigint[];
  END IF;

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

  -- 🔴 RD-4 — il livello che mancava. Senza, le attivita' restano
  -- marcate come emesse: fn_emit_attivita_fatturabili_da_commessa
  -- filtra su stato_emissione = 'EMESSA' e non le riprende mai
  -- piu', e il cruscotto competenza continua a contarle lavorate.
  -- Solo le EMESSA: le ANNULLATA sono state annullate di proposito
  -- e non tornano in coda per una pulizia.
  UPDATE vendite.commesse_attivita ca
     SET stato_emissione = 'NON_EMESSA',
         data_update     = now(),
         user_update     = current_user
   WHERE ca.id = ANY(v_ca_ids)
     AND ca.stato_emissione = 'EMESSA';
  GET DIAGNOSTICS v_riemesse_attivita = ROW_COUNT;

  RETURN QUERY
  SELECT v_deleted_fatture, v_deleted_righe, v_updated_attivita, v_riemesse_attivita;
END;
$function$

COMMENT ON FUNCTION vendite.fn_cleanup_fatture_by_ids(p_fatture_ids bigint[], p_lock_batch_id uuid)
IS 'Pulizia centralizzata delle fatture e ripristino COMPLETO di cio'' che avevano consumato. Cancella note, riepiloghi IVA, righe, log, collegamento al lotto e testate; storna dall''ambito di compensazione l''arrotondamento delle fatture cancellate (D-N pezzo 3 / C-23) PRIMA di toccarle; azzera i fondi; sblocca le attivita_fatturabili; e — dal 2026-08-03, RD-4 — riporta le commesse_attivita collegate a stato_emissione = NON_EMESSA. ⚠️ Quest''ultimo passo vive QUI e non nei chiamanti: sono TRE (fn_annulla_lotto_da_draft, fn_elimina_fattura_da_lotto_draft, fn_riporta_lotto_a_draft) e la correttezza di ognuno dipende dal fatto che facciano la stessa cosa — senza, le attivita'' restano emesse senza fattura e nessun giro futuro le riprende. ⚠️ La popolazione delle commesse_attivita usa il predicato IDENTICO alla UPDATE su attivita_fatturabili e si raccoglie PRIMA di essa, che azzera fattura_riga_id. ⚠️ Il ramo su p_lock_batch_id prende TUTTE le attivita'' del batch: corretto nel reset globale, ed e'' il motivo per cui il reset per-fattura deve passare NULL (C-22).';
```

---
{% include-markdown "signature-core.md" %}
