{% include-markdown "it/dbzero/script/manual/fn_check_ordine_evadibile.md" %}
# ⚙️ Funzione `fn_check_ordine_evadibile`

```sql
CREATE FUNCTION fn_check_ordine_evadibile(p_ordine_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ordine_evadibile(p_ordine_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi per cui da un ordine non si genera una
--   bolla di evasione. Funzione PURA (fn_check_*): [] = lecito.
--   Consumatori: vendite.fn_genera_ddt_da_ordine (solleva il primo) e
--   script.fn_available_actions_ordine (can_genera_ddt).
--   Brief: brief-db-stati-documento-dal-vocabolario §6.17 (D-EVAD).
DECLARE
  -- L'elenco dei motivi: nessuna colonna di cui sia il riflesso.
  v_motivi    jsonb := '[]'::jsonb;
  v_numero    vendite.ordini.numero%TYPE;
  v_stato     config.stati_doc_ordini.codice_interno%TYPE;
  v_emissione config.stati_doc_ordini.emissione%TYPE;
BEGIN
  IF p_ordine_id IS NULL OR p_ordine_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script', 'fn_check_ordine_evadibile', 'E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro', 'ordine_id', 'valore', p_ordine_id),
      NULL::uuid, 'ordine_id obbligatorio (>0)');
  END IF;

  SELECT o.numero, s.codice_interno, s.emissione
    INTO v_numero, v_stato, v_emissione
    FROM vendite.ordini o
    JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
   WHERE o.id = p_ordine_id;

  IF NOT FOUND THEN
    RETURN v_motivi;   -- ordine inesistente: decide il chiamante
  END IF;

  -- L'ordine si evade dallo stato di emissione (la colonna del
  -- vocabolario) e da PARZIALMENTE_EVASO, la destinazione del processo
  -- che si nomina col codice, come la nomina la matrice.
  IF NOT (v_emissione OR v_stato = 'PARZIALMENTE_EVASO') THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_DDT_ORDINE_STATO_NON_EVADIBILE',
      'reason',     'ORDINE_NON_EVADIBILE',
      'reason_key', 'vendite.ordini.genera_ddt_reason.stato_non_evadibile',
      'dettaglio',  jsonb_build_object('stato', v_stato),
      'valori',     jsonb_build_array(COALESCE(v_numero, p_ordine_id::text), v_stato));
  END IF;

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_ordine_evadibile(p_ordine_id bigint)
IS 'Pure check: i motivi per cui da un ordine non si genera una bolla di evasione; [] = lecito, e [] anche per un ordine assente (decide il chiamante). L''ordine si evade dallo stato di emissione (la colonna emissione di config.stati_doc_ordini) e da PARZIALMENTE_EVASO, la destinazione del processo, che si nomina col codice; negli altri stati E_DDT_ORDINE_STATO_NON_EVADIBILE, reason ORDINE_NON_EVADIBILE, reason_key vendite.ordini.genera_ddt_reason.stato_non_evadibile, valori il numero dell''ordine e il codice dello stato, dettaglio {stato}. Sede unica della regola: la leggono vendite.fn_genera_ddt_da_ordine, che solleva il primo motivo, e script.fn_available_actions_ordine, che ne fa can_genera_ddt. Parametro non valido: E_PARAMETRO_INVALIDO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
