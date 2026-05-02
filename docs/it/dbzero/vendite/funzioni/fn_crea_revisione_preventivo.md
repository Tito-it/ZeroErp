{% include-markdown "it/dbzero/vendite/manual/fn_crea_revisione_preventivo.md" %}
# ⚙️ Funzione `fn_crea_revisione_preventivo`

```sql
CREATE FUNCTION fn_crea_revisione_preventivo(p_preventivo_id bigint, p_user text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_crea_revisione_preventivo(p_preventivo_id bigint, p_user text)
 RETURNS TABLE(nuovo_preventivo_id bigint, numero character varying, nuova_rev integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_stato_corrente_cod  config.stati_doc_preventivi.codice%TYPE;
  v_numero              vendite.preventivi.numero%TYPE;
  v_max_rev             vendite.preventivi.rev%TYPE;
  v_stato_draft_id      config.stati_doc_preventivi.id%TYPE;
  v_new_id              vendite.preventivi.id%TYPE;
  v_new_rev             vendite.preventivi.rev%TYPE;
  v_has_draft           boolean;
BEGIN
  -- ==========================================================
  -- Scopo:
  --   Creare una nuova revisione in DRAFT a partire da un
  --   preventivo in stato EMESSO. Copia testata, righe
  --   attive e indirizzi. Disattiva la revisione corrente.
  --
  -- Regole (rev 03-05-2026):
  --   - stato corrente DEVE essere EMESSO (ACCETTATO non
  --     piu' ammesso: chiude la negoziazione e abilita
  --     push commessa, non e' rivisitabile)
  --   - non deve esistere gia' una revisione DRAFT per lo
  --     stesso numero
  --   - la revisione corrente viene disattivata
  --     (is_revision_attiva = false)
  --   - la nuova revisione ha rev = max(rev)+1, stato DRAFT,
  --     is_revision_attiva = true
  --   - righe copiate: solo attive con quantita > 0
  --   - indirizzi: tutti copiati
  --
  -- Parametri:
  --   p_preventivo_id : ID del preventivo da revisionare
  --   p_user          : utente che esegue l'operazione
  -- ==========================================================

  -- Guard: parametro obbligatorio
  IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_crea_revisione_preventivo',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object('param', 'p_preventivo_id', 'value', p_preventivo_id),
      NULL::uuid,
      'p_preventivo_id = ' || COALESCE(p_preventivo_id::text, 'NULL')
    );
  END IF;

  -- Recupera stato corrente e numero
  SELECT sdp.codice, p.numero
    INTO v_stato_corrente_cod, v_numero
    FROM vendite.preventivi p
    JOIN config.stati_doc_preventivi sdp ON sdp.id = p.stato_doc_preventivo_id
   WHERE p.id = p_preventivo_id;

  IF v_stato_corrente_cod IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_crea_revisione_preventivo',
      'PREV_STATO_CORRENTE_NON_TROVATO',
      jsonb_build_object('preventivo_id', p_preventivo_id),
      NULL::uuid,
      p_preventivo_id::text
    );
  END IF;

  -- Guard: revisione ammessa SOLO da EMESSO (rev 03-05-2026:
  -- ACCETTATO rimosso, vedi commento di scopo).
  IF v_stato_corrente_cod NOT IN ('EMESSO') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_crea_revisione_preventivo',
      'PREV_REVISIONE_STATO_NON_AMMESSO',
      jsonb_build_object(
        'preventivo_id', p_preventivo_id,
        'stato_corrente', v_stato_corrente_cod
      ),
      NULL::uuid,
      p_preventivo_id::text, v_stato_corrente_cod
    );
  END IF;

  -- Guard: non deve esistere gia' una revisione DRAFT
  SELECT EXISTS(
    SELECT 1
      FROM vendite.preventivi p2
      JOIN config.stati_doc_preventivi sdp2 ON sdp2.id = p2.stato_doc_preventivo_id
     WHERE p2.numero = v_numero
       AND sdp2.codice = 'DRAFT'
  ) INTO v_has_draft;

  IF v_has_draft THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_crea_revisione_preventivo',
      'PREV_REVISIONE_BOZZA_ESISTENTE',
      jsonb_build_object('numero', v_numero),
      NULL::uuid,
      v_numero
    );
  END IF;

  -- Recupera stato DRAFT id
  SELECT id INTO v_stato_draft_id
    FROM config.stati_doc_preventivi
   WHERE codice = 'DRAFT' AND attivo IS TRUE;

  IF v_stato_draft_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_crea_revisione_preventivo',
      'E_CONFIG_MANCANTE',
      jsonb_build_object('tabella', 'config.stati_doc_preventivi', 'codice', 'DRAFT'),
      NULL::uuid,
      'stato DRAFT non trovato o non attivo in config.stati_doc_preventivi'
    );
  END IF;

  -- Calcola nuova revisione
  SELECT COALESCE(MAX(p.rev), 0) + 1
    INTO v_new_rev
    FROM vendite.preventivi p
   WHERE p.numero = v_numero;

  -- Disattiva revisione corrente
  UPDATE vendite.preventivi
     SET is_revision_attiva = false,
         user_update = COALESCE(p_user, CURRENT_USER)
   WHERE id = p_preventivo_id;

  -- Crea nuova testata (copia campi dal preventivo originale).
  -- Totali a 0: il trigger STATEMENT su preventivi_righe li ricalcolera'
  -- dopo l'INSERT bulk delle righe copiate (una sola invocazione).
  INSERT INTO vendite.preventivi (
    numero, rev, is_revision_attiva,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al,
    totale_imponibile, totale_iva, totale_documento,
    valuta_id, competenza_mese, fatturazione_immediata,
    stato_doc_preventivo_id, data, termine_pagamento_id,
    storicizza, meta,
    user_insert, user_update
  )
  SELECT
    p.numero, v_new_rev, true,
    p.billing_account_id, p.istanza_utility_id, p.utility_id,
    p.validita_dal, p.validita_al,
    0, 0, 0,
    p.valuta_id, p.competenza_mese, p.fatturazione_immediata,
    v_stato_draft_id, CURRENT_DATE, p.termine_pagamento_id,
    p.storicizza, p.meta,
    COALESCE(p_user, CURRENT_USER), COALESCE(p_user, CURRENT_USER)
  FROM vendite.preventivi p
  WHERE p.id = p_preventivo_id
  RETURNING id INTO v_new_id;

  -- Copia righe attive
  INSERT INTO vendite.preventivi_righe (
    preventivo_id, articolo_id, descrizione,
    quantita, prezzo_unitario, sconto_percentuale,
    iva_id, ordine, attivo,
    qta_operativa, uom_operativa_id, factor_to_base,
    meta,
    user_insert, user_update
  )
  SELECT
    v_new_id, pr.articolo_id, pr.descrizione,
    pr.quantita, pr.prezzo_unitario, pr.sconto_percentuale,
    pr.iva_id, pr.ordine, pr.attivo,
    pr.qta_operativa, pr.uom_operativa_id, pr.factor_to_base,
    pr.meta,
    COALESCE(p_user, CURRENT_USER), COALESCE(p_user, CURRENT_USER)
  FROM vendite.preventivi_righe pr
  WHERE pr.preventivo_id = p_preventivo_id
    AND pr.attivo IS TRUE
    AND pr.quantita > 0;

  -- Copia indirizzi
  INSERT INTO vendite.preventivi_indirizzi (
    preventivo_id, tipo_indirizzo_id, snapshot,
    origine_indirizzo_id, origine_soggetto_ruolo_id,
    user_insert, user_update
  )
  SELECT
    v_new_id, pi.tipo_indirizzo_id, pi.snapshot,
    pi.origine_indirizzo_id, pi.origine_soggetto_ruolo_id,
    COALESCE(p_user, CURRENT_USER), COALESCE(p_user, CURRENT_USER)
  FROM vendite.preventivi_indirizzi pi
  WHERE pi.preventivo_id = p_preventivo_id;

  -- Ritorna risultato
  RETURN QUERY
  SELECT v_new_id, v_numero, v_new_rev;
END
$function$

COMMENT ON FUNCTION vendite.fn_crea_revisione_preventivo(p_preventivo_id bigint, p_user text)
IS 'Crea nuova revisione preventivo vendita: copia testata + righe attive + indirizzi. Disattiva revisione corrente. Guard: stato EMESSO (rev 03-05-2026: ACCETTATO non piu'' ammesso, chiude la negoziazione), no DRAFT esistente. Stessa firma %TYPE.';
```

---
{% include-markdown "signature-core.md" %}
