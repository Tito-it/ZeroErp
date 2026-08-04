{% include-markdown "it/dbzero/script/manual/fn_check_lotto_annullabile.md" %}
# ⚙️ Funzione `fn_check_lotto_annullabile`

```sql
CREATE FUNCTION fn_check_lotto_annullabile(p_lotto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_lotto_annullabile(p_lotto_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono l'ANNULLAMENTO di un
--   lotto. Funzione PURA (fn_check_*): nessun raise di dominio,
--   nessuna scrittura. Consumatori: vendite.fn_annulla_lotto_da_draft
--   (che solleva il codice del primo motivo) e
--   script.fn_available_actions_lotto (che espone enabled + reasons).
-- Ritorna: [] se annullabile; altrimenti array ordinato di
--   {codice, reason, reason_key, dettaglio}.
DECLARE
  v_motivi    jsonb := '[]'::jsonb;
  v_stato_cod config.stati_doc_fiscale.codice_interno%TYPE;
  v_trovato   boolean;
BEGIN
  -- Guard parametro (AGENTS.md).
  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_lotto_annullabile','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','lotto_id','valore',p_lotto_id),
      NULL::uuid, 'lotto_id obbligatorio (>0)');
  END IF;

  -- Stato corrente per CODICE: il codice_interno e' la chiave
  -- stabile, l'id no (lezione B-4). LEFT JOIN perche' un lotto
  -- senza stato deve arrivare al confronto e fallirlo, non
  -- sparire dalla riga.
  SELECT true, sdf.codice_interno
    INTO v_trovato, v_stato_cod
    FROM vendite.fatturazione_lotti fl
    LEFT JOIN config.stati_doc_fiscale sdf
      ON sdf.id = fl.stato_doc_fiscale_id
   WHERE fl.id = p_lotto_id;

  IF NOT COALESCE(v_trovato, false) THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_lotto_annullabile','E_LOTTO_NON_TROVATO',
      jsonb_build_object('lotto_id',p_lotto_id),
      NULL::uuid, p_lotto_id::text);
  END IF;

  -- MOTIVO 1 — il lotto non e' in bozza.
  -- L'annullamento e' terminale (ANNULLATA chiude il lotto e non
  -- si riapre): si concede solo prima che il lotto abbia
  -- prodotto qualcosa. Da EMESSA la strada e' «riporta in bozza».
  IF COALESCE(v_stato_cod, '') <> 'DRAFT' THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_LOTTO_NON_ANNULLABILE',
      'reason',     'STATO_NON_DRAFT',
      'reason_key', 'vendite.lotti.azione_reason.stato_non_draft',
      'dettaglio',  COALESCE(v_stato_cod, '-'));
  END IF;

  -- MOTIVO 2 — fatture oltre il pre-fiscale. Delegato: la
  -- definizione di «pre-fiscale» sta in un posto solo.
  v_motivi := v_motivi
            || script.fn_check_lotto_fatture_pre_fiscali(p_lotto_id);

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_lotto_annullabile(p_lotto_id bigint)
IS 'Funzione PURA (fn_check_*): motivi ostativi all''annullamento di un lotto. Ritorna [] se annullabile, altrimenti array ordinato di {codice, reason, reason_key, dettaglio}. Motivo 1: lotto non in DRAFT (codice 798) — ANNULLATA e'' terminale e non si riapre, quindi si concede solo prima che il lotto abbia prodotto qualcosa; da EMESSA la via d''uscita non distruttiva e'' fn_riporta_lotto_a_draft. Motivo 2: fatture oltre il pre-fiscale (codice 799), delegato a script.fn_check_lotto_fatture_pre_fiscali. Il tipo di lotto NON e'' un motivo: dal 2026-08-02 (D-L pt.2 + D-T) vale per MASSIVO e GIORNALIERO. Sorgente UNICA condivisa da vendite.fn_annulla_lotto_da_draft (solleva) e script.fn_available_actions_lotto (espone enabled/reasons): chiude il vicolo cieco del pulsante visibile da EMESSA, trovato in-app il 2026-07-31 e tappato allora con un v-if in Vue. rev 2026-08-04.';
```

---
{% include-markdown "signature-core.md" %}
