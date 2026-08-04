# ⚙️ Funzione `fn_check_preventivo_annullabile`

```sql
CREATE FUNCTION fn_check_preventivo_annullabile(p_preventivo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_preventivo_annullabile(p_preventivo_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono l'ANNULLAMENTO di un
--   preventivo. Funzione PURA (fn_check_*): nessun raise di
--   dominio, nessuna scrittura. Consumatori: il guard di
--   transizione e script.fn_available_actions_preventivo.
--   Brief: brief-db-vie-uscita-operatore §3.1.
-- Ritorna: [] se annullabile; altrimenti array ordinato di
--   {codice, reason, reason_key, dettaglio}.
DECLARE
  v_motivi  jsonb := '[]'::jsonb;
  v_uid     vendite.preventivi.uid%TYPE;
  v_ordini  integer := 0;
  v_commesse integer := 0;
BEGIN
  IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_preventivo_annullabile','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','preventivo_id','valore',p_preventivo_id),
      NULL::uuid, 'preventivo_id obbligatorio (>0)');
  END IF;

  SELECT p.uid INTO v_uid
    FROM vendite.preventivi p
   WHERE p.id = p_preventivo_id;

  IF v_uid IS NULL THEN
    RETURN v_motivi;   -- preventivo inesistente: decide il chiamante
  END IF;

  -- MOTIVO 1 — un ordine e' gia' nato da questo preventivo.
  -- Catena diretta: ordini.sorgente_uid e' uuid e punta all'uid.
  SELECT count(*)
    INTO v_ordini
    FROM vendite.ordini o
   WHERE o.sorgente_uid = v_uid
     AND o.sorgente_tipo_id = (SELECT s.id FROM config.sorgenti s
                                WHERE s.codice_interno = 'PREVENTIVO');

  IF v_ordini > 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_PREV_ORDINE_GIA_GENERATO',
      'reason',     'ORDINE_GIA_GENERATO',
      'reason_key', 'vendite.preventivi.azione_reason.ordine_gia_generato',
      'dettaglio',  v_ordini);
  END IF;

  -- MOTIVO 2 — il preventivo e' gia' entrato in una commessa.
  -- Tabella polimorfa: la chiave e' testo, e per PREVENTIVO
  -- config.sorgenti.key_selector dice 'uid'.
  SELECT count(*)
    INTO v_commesse
    FROM vendite.commesse_sorgenti cs
   WHERE cs.sorgente_uid = v_uid::text
     AND cs.sorgente_tipo_id = (SELECT s.id FROM config.sorgenti s
                                 WHERE s.codice_interno = 'PREVENTIVO');

  IF v_commesse > 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_PREV_GIA_IN_COMMESSA',
      'reason',     'GIA_IN_COMMESSA',
      'reason_key', 'vendite.preventivi.azione_reason.gia_in_commessa',
      'dettaglio',  v_commesse);
  END IF;

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_preventivo_annullabile(p_preventivo_id bigint)
IS 'Pure check: motivi che impediscono l''annullamento di un preventivo. [] = lecito. Blocca quando esiste gia'' un figlio a valle: un ordine generato (vendite.ordini.sorgente_uid = preventivi.uid) o una riga in vendite.commesse_sorgenti (chiave uid::text, per key_selector di config.sorgenti). Sede unica condivisa dal guard di transizione e da script.fn_available_actions_preventivo. Brief: brief-db-vie-uscita-operatore.';
```

---
{% include-markdown "signature-core.md" %}
