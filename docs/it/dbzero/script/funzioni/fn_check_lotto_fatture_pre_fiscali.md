{% include-markdown "it/dbzero/script/manual/fn_check_lotto_fatture_pre_fiscali.md" %}
# ⚙️ Funzione `fn_check_lotto_fatture_pre_fiscali`

```sql
CREATE FUNCTION fn_check_lotto_fatture_pre_fiscali(p_lotto_id bigint)
```

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
-- Ritorna: [] se tutte le fatture del lotto sono pre-fiscali;
--   altrimenti array di {codice, reason, reason_key, dettaglio}.
DECLARE
  v_motivi    jsonb := '[]'::jsonb;
  v_draft_id  config.stati_doc_fiscale.id%TYPE;
  v_emessa_id config.stati_doc_fiscale.id%TYPE;
  v_bad       integer;
BEGIN
  -- Guard parametro (AGENTS.md): id assente o non valido e' un
  -- errore di programmazione, non una condizione di dominio.
  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_lotto_fatture_pre_fiscali','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','lotto_id','valore',p_lotto_id),
      NULL::uuid, 'lotto_id obbligatorio (>0)');
  END IF;

  SELECT s.id INTO v_draft_id
    FROM config.stati_doc_fiscale s
   WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE LIMIT 1;
  IF v_draft_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_lotto_fatture_pre_fiscali','E_CONFIG_MANCANTE',
      jsonb_build_object('codice_interno','DRAFT'),
      NULL::uuid, 'stato DRAFT non configurato');
  END IF;

  SELECT s.id INTO v_emessa_id
    FROM config.stati_doc_fiscale s
   WHERE s.codice_interno = 'EMESSA' AND s.attivo IS TRUE LIMIT 1;
  IF v_emessa_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_lotto_fatture_pre_fiscali','E_CONFIG_MANCANTE',
      jsonb_build_object('codice_interno','EMESSA'),
      NULL::uuid, 'stato EMESSA non configurato');
  END IF;

  -- MOTIVO UNICO — almeno una fattura oltre il pre-fiscale.
  -- IS DISTINCT FROM su entrambi gli id: lo stato NULL conta
  -- come NON pre-fiscale (fail-closed), un JOIN lo perderebbe.
  SELECT count(*)
    INTO v_bad
    FROM vendite.fatture f
    JOIN vendite.fatturazione_lotti_fatture lf
      ON lf.fattura_id = f.id
   WHERE lf.lotto_id = p_lotto_id
     AND f.stato_doc_fiscale_id IS DISTINCT FROM v_draft_id
     AND f.stato_doc_fiscale_id IS DISTINCT FROM v_emessa_id;

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
IS 'Funzione PURA (fn_check_*): motivi ostativi, sul versante FATTURE, alla demolizione del contenuto di un lotto. Ritorna [] se tutte le fatture sono pre-fiscali (DRAFT o EMESSA, cioe'' non ancora numerate — C-19), altrimenti {codice, reason, reason_key, dettaglio} con il conteggio (codice 799). Sede UNICA della definizione di «pre-fiscale» per le fatture di un lotto: la usano script.fn_check_lotto_annullabile e script.fn_check_lotto_riportabile_a_draft, e per loro tramite le due fn di mutazione e le capabilities. ⚠️ La condizione e'' IS DISTINCT FROM sui due id e non un NOT IN sui codici: una fattura con stato_doc_fiscale_id NULL deve contare come NON pre-fiscale (fail-closed). rev 2026-08-04.';
```

</div>

---
{% include-markdown "signature-core.md" %}
