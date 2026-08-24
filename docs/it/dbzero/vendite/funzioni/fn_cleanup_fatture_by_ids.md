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
  v_motivi_rettifiche jsonb;
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

  -- ══ GUARD FAIL-LOUD (2026-08-22) ═════════════════════════════
  -- ⛔ Una riga di fattura gia' RETTIFICATA non si cancella: su di
  --    essa e' gia' stato registrato un accredito, e
  --    `fattura_riga_rettificata_id` e' il SECONDO TETTO di quel
  --    accredito (20260818-27 punto 2) piu' il DatiFattureCollegate
  --    della TD04. Azzerare il legame per far passare la pulizia
  --    toglierebbe quel tetto proprio mentre le quantita' vengono
  --    ri-derivate: non si distrugge la prova per far riuscire
  --    l'operazione.
  --
  -- ⭐ PERCHE' QUI E NON SOLO NELLE fn_check_*. Le porte sono TRE, e
  --    le loro fn_check_* servono all'INTERFACCIA — spiegano prima
  --    del click. Questo e' l'unico punto che tutte e tre
  --    attraversano: e' il presidio della QUARTA porta, quella che
  --    nessuno ha ancora scritto. Il commento di questa funzione la
  --    chiedeva gia', a proposito di fatture_rettifiche.
  --
  -- ⚠️ Senza, il difetto non e' un errore di dominio ma una
  --    violazione di chiave esterna GREZZA (23503) dentro una
  --    funzione che i suoi chiamanti danno per infallibile —
  --    misurato il 2026-08-22 su test-riporta-lotto-a-draft-v1.
  --
  -- ⚠️ Il guard legge sotto ROW SECURITY (questa funzione e'
  --    SECURITY INVOKER). Un chiamante fuori perimetro potrebbe non
  --    vedere le righe che rettificano e passare di qui: in quel
  --    caso pero' NON si perde niente in silenzio, perche' e' la FK
  --    a fermare la cancellazione — si torna al 23503 di prima, che
  --    e' il comportamento attuale, non un peggioramento.
  v_motivi_rettifiche := script.fn_check_fatture_con_rettifiche(p_fatture_ids);

  IF jsonb_array_length(v_motivi_rettifiche) > 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_cleanup_fatture_by_ids',
      'E_FATTURE_RIGHE_RETTIFICATE',
      jsonb_build_object(
        'detail',      'Righe di fattura gia rettificate: pulizia rifiutata',
        'fatture_ids', to_jsonb(p_fatture_ids),
        'motivi',      v_motivi_rettifiche),
      NULL::uuid,
      (v_motivi_rettifiche -> 0 ->> 'dettaglio'));
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
IS 'Pulizia centralizzata delle fatture e ripristino COMPLETO di cio'' che avevano consumato. Cancella note, riepiloghi IVA, righe, log, collegamento al lotto e testate; storna dall''ambito di compensazione l''arrotondamento delle fatture cancellate (D-N pezzo 3 / C-23) PRIMA di toccarle; azzera i fondi; sblocca le attivita_fatturabili; e — dal 2026-08-03, RD-4 — riporta le commesse_attivita collegate a stato_emissione = NON_EMESSA. ⚠️ Quest''ultimo passo vive QUI e non nei chiamanti: sono TRE (fn_annulla_lotto_da_draft, fn_elimina_fattura_da_lotto, fn_riporta_lotto_a_draft) e la correttezza di ognuno dipende dal fatto che facciano la stessa cosa — senza, le attivita'' restano emesse senza fattura e nessun giro futuro le riprende. ⚠️ La popolazione delle commesse_attivita usa il predicato IDENTICO alla UPDATE su attivita_fatturabili e si raccoglie PRIMA di essa, che azzera fattura_riga_id. ⚠️ Il ramo su p_lock_batch_id prende TUTTE le attivita'' del batch: corretto nel reset globale, ed e'' il motivo per cui il reset per-fattura deve passare NULL (C-22). ⭐ NON cancella da vendite.fatture_rettifiche, e NON e'' una dimenticanza (domanda del backend, 2026-08-18, brief note-credito P-2). La proiezione del legame documentale delle note di credito la scrive il task popola_fatture_rettifiche, che gira DOPO numera_fatture: esiste quindi solo su documenti NUMERATI. E un documento numerato non e'' raggiungibile da nessuna delle tre porte di reset, perche'' tutte e tre lo rifiutano con un controllo ESPLICITO sul numero — fn_check_fattura_eliminabile_da_lotto motivo 4 (E_FATTURA_GIA_NUMERATA), fn_check_lotto_riportabile_a_draft motivo 3 e fn_check_lotto_annullabile motivo 3 (E_LOTTO_FATTURE_NUMERATE, aggiunto il 2026-08-18 proprio per chiudere l''ultima che si affidava al solo stato). ⚠️ La garanzia sta in quelle CONDIZIONI, non nei nomi delle funzioni: l''argomento «sono tutte *_da_draft» era vero e ha smesso di esserlo il 2026-08-04, quando fn_elimina_fattura_da_lotto_draft e'' stata rinominata e il suo perimetro allargato al pre-fiscale (RD-7). ⚠️ Se un giorno una porta di reset ammettesse un documento numerato, questa funzione dovrebbe cancellare anche la coppia in fatture_rettifiche: fk_fatture_ret_fattura NON e'' ON DELETE CASCADE, quindi il reset sbatterebbe su una violazione di chiave esterna grezza dentro una funzione che i suoi chiamanti danno per infallibile.';
```

---
{% include-markdown "signature-core.md" %}
