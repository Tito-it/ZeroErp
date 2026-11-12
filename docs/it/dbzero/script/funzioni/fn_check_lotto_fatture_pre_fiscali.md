{% include-markdown "it/dbzero/script/manual/fn_check_lotto_fatture_pre_fiscali.md" %}
# ⚙️ Funzione `fn_check_lotto_fatture_pre_fiscali`

```sql
CREATE FUNCTION fn_check_lotto_fatture_pre_fiscali(p_lotto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_lotto_fatture_pre_fiscali(p_lotto_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi, sul versante FATTURE, che impediscono
--   di demolire il contenuto di un lotto. Funzione PURA
--   (fn_check_*): nessun raise di dominio, nessuna scrittura.
--   Consumatori: script.fn_check_lotto_annullabile,
--   script.fn_check_lotto_riportabile_a_draft e — per loro
--   tramite — script.fn_available_actions_lotto.
-- Pre-fiscale = in uno stato non ancora congelato
--   (config.stati_doc_fiscale.congela_fiscale = false): lo
--   snapshot fiscale non e' preso, la fattura non e' numerata.
--   La soglia si legge dal vocabolario, non da un elenco di codici.
-- Ritorna: [] se tutte le fatture del lotto sono pre-fiscali;
--   altrimenti array di {codice, reason, reason_key, dettaglio}.
DECLARE
  v_motivi    jsonb := '[]'::jsonb;
  v_bad       integer;  -- un conteggio
BEGIN
  -- Guard parametro (AGENTS.md): id assente o non valido e' un
  -- errore di programmazione, non una condizione di dominio.
  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_lotto_fatture_pre_fiscali','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','lotto_id','valore',p_lotto_id),
      NULL::uuid, 'lotto_id obbligatorio (>0)');
  END IF;

  -- MOTIVO UNICO — almeno una fattura oltre il pre-fiscale.
  -- NOT EXISTS e non un JOIN: una fattura il cui stato non si
  -- trova conta come NON pre-fiscale (fail-closed).
  SELECT count(*)
    INTO v_bad
    FROM vendite.fatture f
    JOIN vendite.fatturazione_lotti_fatture lf
      ON lf.fattura_id = f.id
   WHERE lf.lotto_id = p_lotto_id
     AND NOT EXISTS (SELECT 1
                       FROM config.stati_doc_fiscale s
                      WHERE s.id = f.stato_doc_fiscale_id
                        AND s.congela_fiscale IS FALSE);

  IF v_bad > 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_LOTTO_FATTURE_NON_PRE_FISCALI',
      'reason',     'FATTURE_NON_PRE_FISCALI',
      'reason_key', 'vendite.lotti.azione_reason.fatture_non_pre_fiscali',
      'dettaglio',  v_bad);
  END IF;

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_lotto_fatture_pre_fiscali(p_lotto_id bigint)
IS 'Funzione pura (fn_check_*): i motivi, sul versante delle fatture, che impediscono di demolire il contenuto di un lotto. Ritorna [] se tutte le fatture del lotto sono pre-fiscali, cioe'' in uno stato non ancora congelato (config.stati_doc_fiscale.congela_fiscale = false: lo snapshot fiscale non e'' preso, la fattura non e'' numerata); altrimenti un motivo {codice, reason, reason_key, dettaglio} col conteggio (E_LOTTO_FATTURE_NON_PRE_FISCALI). La soglia si legge dal vocabolario, non da un elenco di codici. Una fattura il cui stato non si trova conta come non pre-fiscale (fail-closed). La usano script.fn_check_lotto_annullabile e script.fn_check_lotto_riportabile_a_draft, e per loro tramite i verbi e le capability del lotto. Errore: E_PARAMETRO_INVALIDO su un id assente o non positivo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
