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
  v_numerate  integer;
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

  -- MOTIVO 3 — fatture gia' NUMERATE (aggiunto 2026-08-18).
  -- ⚠️ DELIBERATAMENTE RIDONDANTE rispetto al 2, e da NON
  --   semplificare via: e' la stessa scelta gia' fatta in
  --   fn_check_lotto_riportabile_a_draft e nel motivo 4 di
  --   fn_check_fattura_eliminabile_da_lotto. Il motivo 2 si
  --   affida allo stato, che pre-fiscale IMPLICA non numerata
  --   (C-19); qui si guarda il FATTO, perche' cancellare una
  --   fattura numerata apre un buco nella numerazione fiscale e
  --   il danno non si ripara.
  -- ⭐ Da oggi non e' piu' solo prudenza: il task
  --   popola_fatture_rettifiche scrive vendite.fatture_rettifiche
  --   sui documenti NUMERATI, e fk_fatture_ret_fattura non e'
  --   ON DELETE CASCADE. Senza questo motivo, l'unica cosa che
  --   tiene lontano il reset da quella proiezione sarebbe
  --   l'implicazione stato -> numero; e quando cede non da' un
  --   errore di dominio, da' una violazione di chiave esterna
  --   grezza dentro fn_cleanup_fatture_by_ids.
  SELECT count(*)
    INTO v_numerate
    FROM vendite.fatture f
    JOIN vendite.fatturazione_lotti_fatture lf
      ON lf.fattura_id = f.id
   WHERE lf.lotto_id = p_lotto_id
     AND f.numero IS NOT NULL;

  IF v_numerate > 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_LOTTO_FATTURE_NUMERATE',
      'reason',     'FATTURE_NUMERATE',
      'reason_key', 'vendite.lotti.azione_reason.fatture_numerate',
      'dettaglio',  v_numerate);
  END IF;

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_lotto_annullabile(p_lotto_id bigint)
IS 'Funzione PURA (fn_check_*): motivi ostativi all''annullamento di un lotto. Ritorna [] se annullabile, altrimenti array ordinato di {codice, reason, reason_key, dettaglio}. Motivo 1: lotto non in DRAFT (codice 798) — ANNULLATA e'' terminale e non si riapre, quindi si concede solo prima che il lotto abbia prodotto qualcosa; da EMESSA la via d''uscita non distruttiva e'' fn_riporta_lotto_a_draft. Motivo 2: fatture oltre il pre-fiscale (codice 799), delegato a script.fn_check_lotto_fatture_pre_fiscali. ⭐ Motivo 3 (2026-08-18): fatture gia'' NUMERATE (codice 801) — ⚠️ deliberatamente ridondante rispetto al 2 e da NON semplificare via, come nelle due sorelle: il motivo 2 si affida allo stato, che pre-fiscale IMPLICA non numerata, mentre questo guarda il FATTO. Era l''ULTIMA delle tre porte di reset che si affidava a quella implicazione, e da oggi il peso che ci si appoggia sopra e'' reale: il task popola_fatture_rettifiche scrive vendite.fatture_rettifiche sui documenti numerati e fk_fatture_ret_fattura NON e'' ON DELETE CASCADE — quando l''implicazione cede non da'' un errore di dominio, da'' una violazione di chiave esterna grezza dentro fn_cleanup_fatture_by_ids. Il tipo di lotto NON e'' un motivo: dal 2026-08-02 (D-L pt.2 + D-T) vale per MASSIVO e GIORNALIERO. Sorgente UNICA condivisa da vendite.fn_annulla_lotto_da_draft (solleva) e script.fn_available_actions_lotto (espone enabled/reasons).';
```

---
{% include-markdown "signature-core.md" %}
