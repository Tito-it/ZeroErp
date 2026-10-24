{% include-markdown "it/dbzero/script/manual/fn_check_ordine_data_consegna_confermata.md" %}
# ⚙️ Funzione `fn_check_ordine_data_consegna_confermata`

```sql
CREATE FUNCTION fn_check_ordine_data_consegna_confermata(p_ordine_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ordine_data_consegna_confermata(p_ordine_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$

DECLARE
  v_stato      config.stati_doc_ordini.codice_interno%TYPE;
  -- La frase del lock (script.fn_get_stato_testata_documento):
  -- composta, nessuna colonna di cui sia il riflesso.
  v_etichetta  text;
BEGIN
  -- =========================================================
  -- Scopo:
  --   La promessa di consegna (data_consegna_confermata) delle
  --   righe di quest'ordine si cambia ora, da sola? Funzione
  --   PURA (fn_check_*): [] se si', un motivo se no, NULL se
  --   l'ordine non si vede. La regola non sta qui: sta nel
  --   montaggio del lock delle righe, letto da
  --   script.fn_doc_colonna_modificabile.
  --   Consumatore: script.fn_available_actions_ordine
  --   (can_edit_data_consegna_confermata).
  -- =========================================================
  IF p_ordine_id IS NULL OR p_ordine_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script', 'fn_check_ordine_data_consegna_confermata', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro', 'ordine_id', 'valore', p_ordine_id),
      NULL::uuid, 'l''ordine e'' obbligatorio');
  END IF;

  -- Lo stato, sotto la RLS di chi chiede: un ordine che non
  -- vede non ha risposta.
  SELECT sdo.codice_interno
    INTO v_stato
    FROM vendite.ordini o
    JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
   WHERE o.id = p_ordine_id;

  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  -- La sola data, in questo stato: lo dice il montaggio del lock.
  IF script.fn_doc_colonna_modificabile('vendite.ordini_righe'::regclass,
                                        'data_consegna_confermata',
                                        v_stato) THEN
    RETURN jsonb_build_array();
  END IF;

  -- La frase del rifiuto, la stessa del lock.
  SELECT t.etichetta
    INTO v_etichetta
    FROM script.fn_get_stato_testata_documento('ORDINE_VENDITA', p_ordine_id) AS t;

  RETURN jsonb_build_array(jsonb_build_object(
    'codice',     'E_RIGA_DOC_NON_BOZZA',
    'reason',     'STATO_NON_AMMETTE',
    'reason_key', 'vendite.ordini.data_consegna_confermata_reason.stato_non_ammette',
    'dettaglio',  jsonb_build_object('stato', v_stato),
    'valori',     jsonb_build_array(v_etichetta, v_stato, 'modificare')));
END;
$function$

COMMENT ON FUNCTION script.fn_check_ordine_data_consegna_confermata(p_ordine_id bigint)
IS 'Check (2026-10-10, brief-db-testata-dopo-emissione fase 1, R-1): la promessa di consegna (data_consegna_confermata) delle righe di quest''ordine si cambia ora, da sola? Funzione pura. NULL: ordine assente o non visibile (RLS). []: il lock delle righe la lascia cambiare (anche in DRAFT: che in bozza il verbo giusto sia la modifica della riga lo decide la capability). Un motivo quando lo stato non lo ammette: codice E_RIGA_DOC_NON_BOZZA (quello che il lock solleva), reason STATO_NON_AMMETTE, reason_key vendite.ordini.data_consegna_confermata_reason.stato_non_ammette, dettaglio {stato}, valori etichetta, stato, verbo. La regola non e'' scritta qui: gli stati ammessi stanno negli argomenti del lock di vendite.ordini_righe (oggi CONFERMATO e PARZIALMENTE_EVASO, 20261008-90) e si leggono con script.fn_doc_colonna_modificabile, che decide con la funzione del trigger. Consumatore: script.fn_available_actions_ordine (can_edit_data_consegna_confermata). ⭐ rev 2026-10-19 (20261019-57, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
