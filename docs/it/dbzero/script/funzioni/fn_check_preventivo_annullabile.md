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
--   transizione, la porta vendite.fn_cambia_stato_preventivo e
--   script.fn_available_actions_preventivo.
--   Brief: brief-db-vie-uscita-operatore §3.1 e §7.3.
-- Ritorna: [] se annullabile; altrimenti array ordinato di
--   {codice, reason, reason_key, dettaglio}. L'ordine e' quello
--   di gravita': chi consuma solleva il PRIMO.
-- rev 2026-08-04 (§7.3): assorbito il criterio che viveva dentro
--   la porta (righe gia' EMESSA in commessa) -> MOTIVO 2. Da qui
--   la porta non ha piu' una regola propria: chiama questa.
DECLARE
  v_motivi  jsonb := '[]'::jsonb;
  v_uid     vendite.preventivi.uid%TYPE;
  v_ordini  integer := 0;
  v_emesse  integer := 0;
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

  -- MOTIVO 2 — righe gia' EMESSE in commessa: a valle esiste un
  -- documento fiscale. E' il criterio che stava dentro la porta
  -- (§7.3) e legge l'EFFETTO (le attivita' di commessa, scritte
  -- dalle funzioni di dominio), non la registrazione della
  -- sorgente letta dal MOTIVO 3, che la scrive il backend con una
  -- chiamata separata. Sono due fatti diversi: oggi coincidono,
  -- per costruzione non devono.
  -- starts_with() (PG 18, index-friendly) come nella porta.
  SELECT count(*)
    INTO v_emesse
    FROM vendite.commesse_attivita ca
   WHERE starts_with(ca.segment_key, 'PREV:' || v_uid::text || ':R:')
     AND ca.stato_emissione = 'EMESSA';

  IF v_emesse > 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_PREV_ANNULLA_COMMESSA_EMESSA',
      'reason',     'COMMESSA_GIA_EMESSA',
      'reason_key', 'vendite.preventivi.azione_reason.commessa_gia_emessa',
      'dettaglio',  v_emesse);
  END IF;

  -- MOTIVO 3 — il preventivo e' gia' entrato in una commessa,
  -- anche se nulla e' ancora uscito. Tabella polimorfa: la chiave
  -- e' testo, e per PREVENTIVO config.sorgenti.key_selector dice
  -- 'uid'.
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
IS 'Pure check: motivi che impediscono l''annullamento di un preventivo. [] = lecito. Sede UNICA della regola, condivisa da vendite.trgfn_preventivi_guard_annullamento, dalla porta vendite.fn_cambia_stato_preventivo e da script.fn_available_actions_preventivo. Motivi in ordine di gravita'' (chi consuma solleva il primo): 1) un ordine generato (vendite.ordini.sorgente_uid = preventivi.uid); 2) righe gia'' EMESSA in commessa (vendite.commesse_attivita, segment_key PREV:<uid>:R:) — a valle esiste una fattura; 3) una riga in vendite.commesse_sorgenti (chiave uid::text, per key_selector di config.sorgenti). Il 2 e il 3 NON sono ridondanti: il primo legge l''effetto scritto dalle funzioni di dominio, il secondo la registrazione scritta dal backend. rev 2026-08-04: assorbito il criterio della porta, che non ha piu'' regola propria (brief-db-vie-uscita-operatore §7.3).';
```

---
{% include-markdown "signature-core.md" %}
