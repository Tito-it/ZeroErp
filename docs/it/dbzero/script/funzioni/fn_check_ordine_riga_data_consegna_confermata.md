# ⚙️ Funzione `fn_check_ordine_riga_data_consegna_confermata`

```sql
CREATE FUNCTION fn_check_ordine_riga_data_consegna_confermata(p_ordine_riga_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ordine_riga_data_consegna_confermata(p_ordine_riga_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$

DECLARE
  v_ordine_id  vendite.ordini_righe.ordine_id%TYPE;
  v_riga_nr    vendite.ordini_righe.riga_nr%TYPE;
  -- I motivi di stato: un array jsonb composto da un'altra check,
  -- nessuna colonna di cui sia il riflesso.
  v_motivi     jsonb;
  -- La frase (script.fn_get_stato_testata_documento, RETURNS TABLE
  -- di text): composta, nessuna colonna di cui sia il riflesso.
  v_etichetta  text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   La data di consegna confermata di questa riga d'ordine si
  --   cambia ora? Funzione PURA (fn_check_*): [] se si', i motivi
  --   se no (il primo e' quello che il guard solleva), NULL se la
  --   riga o il suo ordine non si vedono (RLS di chi chiede).
  --   Consumatori: il guard
  --   vendite.trgfn_ordini_righe_guard_data_consegna_spedita
  --   (solleva il primo motivo), la colonna
  --   data_consegna_confermata_blocco di
  --   vendite.vw_ordini_righe_dettaglio, la selezione dell'utility
  --   del backend che aggiorna le date in blocco.
  -- =========================================================
  IF p_ordine_riga_id IS NULL OR p_ordine_riga_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script', 'script.fn_check_ordine_riga_data_consegna_confermata',
      'E_VENDITE_CHIAMATA_NON_VALIDA',
      jsonb_build_object('p_ordine_riga_id', p_ordine_riga_id),
      NULL::uuid, 'script.fn_check_ordine_riga_data_consegna_confermata',
      'p_ordine_riga_id (obbligatorio, maggiore di zero)');
  END IF;

  -- La riga, sotto la RLS di chi chiede.
  SELECT r.ordine_id, r.riga_nr
    INTO v_ordine_id, v_riga_nr
    FROM vendite.ordini_righe r
   WHERE r.id = p_ordine_riga_id;

  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  -- 1. Lo stato dell'ordine: i motivi della check di documento, cosi'
  --    come sono (leggono il montaggio del lock delle righe). NULL =
  --    l'ordine non si vede.
  v_motivi := script.fn_check_ordine_data_consegna_confermata(v_ordine_id);
  IF v_motivi IS NULL OR jsonb_array_length(v_motivi) > 0 THEN
    RETURN v_motivi;
  END IF;

  -- 2. La riga e' gia' partita con un DDT, anche in parte: la data di
  --    consegna si scrive prima di spedire (D-7, P-1). Il predicato e'
  --    vendite.fn_ordine_riga_spedita (DEFINER: vede i DDT fuori
  --    perimetro, e il guard non diventa fail-open).
  IF vendite.fn_ordine_riga_spedita(p_ordine_riga_id) THEN
    SELECT t.etichetta
      INTO v_etichetta
      FROM script.fn_get_stato_testata_documento('ORDINE_VENDITA', v_ordine_id) AS t;
    RETURN jsonb_build_array(jsonb_build_object(
      'codice',     'E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA',
      'reason',     'RIGA_SPEDITA',
      'reason_key', 'vendite.ordini.data_consegna_confermata_reason.riga_spedita',
      'dettaglio',  jsonb_build_object('ordine_riga_id', p_ordine_riga_id),
      'valori',     jsonb_build_array(COALESCE(v_etichetta, 'Ordine #' || v_ordine_id::text),
                                      v_riga_nr::text)));
  END IF;

  RETURN jsonb_build_array();
END;
$function$

COMMENT ON FUNCTION script.fn_check_ordine_riga_data_consegna_confermata(p_ordine_riga_id bigint)
IS 'Check di riga (2026-10-11, brief-db-date-consegna-righe-in-blocco D-7, P-1, linee-guida-sql §12.5): la data di consegna confermata di questa riga d''ordine si cambia ora? Funzione pura. NULL: riga, o il suo ordine, assente o non visibile (RLS). []: ammessa. Altrimenti i motivi, in quest''ordine (l''ordine e'' il contratto: il guard solleva il primo): 1) lo stato dell''ordine, cioe'' i motivi di script.fn_check_ordine_data_consegna_confermata cosi'' come sono (STATO_NON_AMMETTE, E_RIGA_DOC_NON_BOZZA: gli stati ammessi stanno nel montaggio del lock di vendite.ordini_righe; in DRAFT nessun motivo); 2) RIGA_SPEDITA (E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA, CONFLITTO_STATO): la riga e'' gia'' partita con un DDT uscito dalla bozza, anche per una parte (vendite.fn_ordine_riga_spedita) — la data di consegna si scrive prima di spedire. reason_key vendite.ordini.data_consegna_confermata_reason.riga_spedita; valori etichetta dell''ordine e numero di riga. Consumatori: il guard vendite.trgfn_ordini_righe_guard_data_consegna_spedita, la colonna data_consegna_confermata_blocco di vendite.vw_ordini_righe_dettaglio, la selezione dell''utility del backend che aggiorna le date di consegna in blocco (salta le righe con un motivo). ⭐ rev 2026-10-19 (20261019-58, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente.';
```

---
{% include-markdown "signature-core.md" %}
