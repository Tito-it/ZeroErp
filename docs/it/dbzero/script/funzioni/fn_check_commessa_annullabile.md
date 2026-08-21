{% include-markdown "it/dbzero/script/manual/fn_check_commessa_annullabile.md" %}
# ⚙️ Funzione `fn_check_commessa_annullabile`

```sql
CREATE FUNCTION fn_check_commessa_annullabile(p_commessa_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_commessa_annullabile(p_commessa_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono l'ANNULLAMENTO di una
--   commessa. Funzione PURA (fn_check_*): nessun raise di dominio,
--   nessuna scrittura. Consumatori: il guard di transizione (che
--   solleva il codice del primo motivo) e fn_available_actions_commessa
--   (che espone l'azione disabled + reasons).
--   Brief: brief-db-guard-uscita-commessa-e-capabilities §3.2.
-- Ritorna: [] se annullabile; altrimenti array ordinato di
--   {codice, reason, reason_key, dettaglio}.
DECLARE
  v_motivi jsonb   := '[]'::jsonb;
  v_emesse integer;
BEGIN
  -- Guard parametro (AGENTS.md): id assente o non valido e' un errore
  -- di programmazione, non una condizione di dominio -> errore parlante
  -- invece di normalizzazione silenziosa. Non intacca la purezza.
  IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_commessa_annullabile','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','commessa_id','valore',p_commessa_id),
      NULL::uuid, 'commessa_id obbligatorio (>0)');
  END IF;

  -- MOTIVO 1 — righe gia' EMESSE (D1, criterio D7).
  -- 'EMESSA' = uscita verso una fattura, NON "fatturata in via
  -- definitiva": il reset lotto cancella le fatture ma non riporta
  -- indietro questo stato. Blocchiamo comunque, di proposito.
  -- Indice: ix_commesse_attivita_commessa_stati
  -- (commessa_id, stato_approvazione, stato_emissione).
  SELECT count(*)
    INTO v_emesse
    FROM vendite.commesse_attivita ca
   WHERE ca.commessa_id = p_commessa_id
     AND ca.stato_emissione = 'EMESSA';

  IF v_emesse > 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_COMMESSA_ANNULLA_CON_RIGHE_EMESSE',
      'reason',     'RIGHE_EMESSE',
      'reason_key', 'vendite.commesse.azione_reason.righe_emesse',
      'dettaglio',  v_emesse);
  END IF;

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_commessa_annullabile(p_commessa_id bigint)
IS 'Funzione PURA (fn_check_*): motivi ostativi all''annullamento di una commessa. Ritorna [] se annullabile, altrimenti array di {codice, reason, reason_key, dettaglio}. Motivo unico: esistono righe con stato_emissione=EMESSA (codice 558). Criterio deliberatamente restrittivo (brief §2.1-bis, D7): EMESSA e non "fattura viva", perche'' il reset lotto azzera fattura_riga_id ma non stato_emissione, e ANNULLATA e'' terminale/irreversibile. Sorgente UNICA condivisa da vendite.trgfn_commesse_guard_transizione (solleva) e script.fn_available_actions_commessa (espone enabled/reasons). rev 2026-07-24.';
```

---
{% include-markdown "signature-core.md" %}
