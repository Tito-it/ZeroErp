{% include-markdown "it/dbzero/script/manual/fn_check_commessa_pronta_fatturazione.md" %}
# ⚙️ Funzione `fn_check_commessa_pronta_fatturazione`

```sql
CREATE FUNCTION fn_check_commessa_pronta_fatturazione(p_commessa_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_commessa_pronta_fatturazione(p_commessa_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi che impediscono a una commessa di
--   dichiararsi PRONTA_FATTURAZIONE. Funzione PURA (fn_check_*):
--   nessun raise di dominio, nessuna scrittura. Consumatori: il
--   guard di transizione (che solleva il codice del primo motivo)
--   e fn_available_actions_commessa (che espone l'azione
--   disabled + reasons).
--   Brief: brief-db-emittibilita-visibile-e-sbloccabile §3.3.
-- Ritorna: [] se la commessa puo' passare; altrimenti array
--   ordinato di {codice, reason, reason_key, dettaglio}.
DECLARE
  v_motivi    jsonb := '[]'::jsonb;
  v_pronte    integer := 0;   -- conteggio, non specchio di colonna
  v_emittente vendite.commesse.emittente_soggetto_ruolo_id%TYPE;
  v_trovata   boolean := false;
  v_codice    vendite.commesse.codice%TYPE;
BEGIN
  -- Guard parametro (AGENTS.md): id assente o non valido e' un
  -- errore di programmazione, non una condizione di dominio.
  IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'script','fn_check_commessa_pronta_fatturazione','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','commessa_id','valore',p_commessa_id),
      NULL::uuid, 'commessa_id obbligatorio (>0)');
  END IF;

  -- ⭐ `c.codice` viaggia sulla SELECT che c'era gia': serve a COMPORRE la
  --   frase («Commessa %s: ...»), non a decidere. Vedi la nota gemella in
  --   fn_check_commessa_annullabile per il caso del trigger BEFORE.
  SELECT c.emittente_soggetto_ruolo_id, true, c.codice
    INTO v_emittente, v_trovata, v_codice
    FROM vendite.commesse c
   WHERE c.id = p_commessa_id;

  -- MOTIVO 1 — nessuna riga che il motore raccoglierebbe.
  -- Le tre condizioni sono quelle di fn_list_emittibili_lane:
  -- dichiarare pronta una commessa che la lane non vedrebbe
  -- significa promettere un lavoro che non partira'.
  -- Indice: ix_commesse_attivita_commessa_stati.
  SELECT count(*)
    INTO v_pronte
    FROM vendite.commesse_attivita ca
   WHERE ca.commessa_id       = p_commessa_id
     AND ca.stato_approvazione = 'APPROVATA'
     AND ca.stato_emissione    = 'NON_EMESSA'
     AND ca.tipo_doc_fiscale_id IS NOT NULL;

  IF v_pronte = 0 THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_COMMESSA_NESSUNA_RIGA_APPROVATA',
      'reason',     'NESSUNA_RIGA_PRONTA',
      'reason_key', 'vendite.commesse.azione_reason.nessuna_riga_pronta',
      'dettaglio',  0,
      'valori',     jsonb_build_array(COALESCE(v_codice, p_commessa_id::text)));
  END IF;

  -- MOTIVO 2 — emittente fiscale assente sulla testata.
  -- E' parte della chiave di raggruppamento della lane: senza,
  -- il raggruppamento non diventa nessuna fattura.
  IF v_trovata AND v_emittente IS NULL THEN
    v_motivi := v_motivi || jsonb_build_object(
      'codice',     'E_COMMESSA_EMITTENTE_MANCANTE',
      'reason',     'EMITTENTE_MANCANTE',
      'reason_key', 'vendite.commesse.azione_reason.emittente_mancante',
      'dettaglio',  0,
      'valori',     jsonb_build_array(COALESCE(v_codice, p_commessa_id::text)));
  END IF;

  RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_commessa_pronta_fatturazione(p_commessa_id bigint)
IS 'Pure check: motivi che impediscono a una commessa di passare a PRONTA_FATTURAZIONE. [] = transizione lecita. Specchio dei filtri di vendite.fn_list_emittibili_lane (riga APPROVATA + NON_EMESSA + tipo_doc valorizzato; testata con emittente). Sede unica condivisa da vendite.trgfn_commesse_guard_transizione e script.fn_available_actions_commessa: il bottone non puo'' divergere dal guard. Terza sorella di fn_check_commessa_chiudibile / _annullabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
