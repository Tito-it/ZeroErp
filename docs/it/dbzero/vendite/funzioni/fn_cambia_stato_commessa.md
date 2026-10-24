{% include-markdown "it/dbzero/vendite/manual/fn_cambia_stato_commessa.md" %}
# ⚙️ Funzione `fn_cambia_stato_commessa`

```sql
CREATE FUNCTION fn_cambia_stato_commessa(p_commessa_id bigint, p_nuovo_stato character varying, p_user text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_cambia_stato_commessa(p_commessa_id bigint, p_nuovo_stato character varying, p_user text DEFAULT NULL::text)
 RETURNS TABLE(commessa_id bigint, stato_da character varying, stato_a character varying)
 LANGUAGE plpgsql
AS $function$
-- Scopo: entrypoint sanzionato per il cambio stato commessa.
--   Valida parametri, risolve lo stato target, esegue l'UPDATE.
--   Matrice e guard di dominio sono enforced dal trigger
--   vendite.trgfn_commesse_guard_transizione sull'UPDATE.
--   rev 2026-08-06: la destinazione non risolta solleva
--   E_STATO_WORKFLOW_NON_TROVATO. Il precedente
--   E_STATO_SCONOSCIUTO lo condivideva con
--   config.trgfn_toponomastica_normalize, dove pero' «stato»
--   era la NAZIONE di un indirizzo: due verita' diverse sotto
--   un nome solo, quindi nessuna policy HTTP poteva essere
--   giusta per entrambe (404 qui, 400 la'). Brief terzo lato
--   §11.2. Il vecchio codice e' RITIRATO (obsoleto_dal), non
--   cancellato: regge il diario dei log gia' scritti.
DECLARE
  v_stato_corrente_id   vendite.commesse.stato_commessa_id%TYPE;
  v_stato_corrente_cod  vendite.stati_commessa.codice_interno%TYPE;
  v_codice              vendite.commesse.codice%TYPE;
  v_nuovo_stato_id      vendite.stati_commessa.id%TYPE;
BEGIN
  -- Guard: parametri obbligatori
  IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_cambia_stato_commessa',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object('p_commessa_id', p_commessa_id),
      NULL::uuid,
      'p_commessa_id'
    );
  END IF;

  -- Stato corrente + esistenza commessa
  SELECT c.stato_commessa_id, sc.codice_interno, c.codice
    INTO v_stato_corrente_id, v_stato_corrente_cod, v_codice
    FROM vendite.commesse c
    JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
   WHERE c.id = p_commessa_id;

  IF v_stato_corrente_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_cambia_stato_commessa',
      'E_COMMESSA_NON_TROVATA',
      jsonb_build_object('p_commessa_id', p_commessa_id),
      NULL::uuid,
      p_commessa_id::text
    );
  END IF;

  -- Stato target esiste ed e' attivo
  SELECT id INTO v_nuovo_stato_id
    FROM vendite.stati_commessa
   WHERE codice_interno = p_nuovo_stato AND attivo IS TRUE;

  IF v_nuovo_stato_id IS NULL THEN
    -- «La destinazione indicata non esiste»: e' un 404, e ora
    -- puo' dirlo perche' il codice non e' piu' condiviso con
    -- l'errore di compilazione dell'indirizzo.
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_cambia_stato_commessa',
      'E_STATO_WORKFLOW_NON_TROVATO',
      jsonb_build_object('p_nuovo_stato', p_nuovo_stato),
      NULL::uuid,
      coalesce(p_nuovo_stato, 'NULL')
    );
  END IF;

  -- Esecuzione: aggiorna stato. Il trigger
  -- vendite.trgfn_commesse_guard_transizione valida matrice +
  -- guard di dominio; solleva se non ammessa.
  UPDATE vendite.commesse
     SET stato_commessa_id = v_nuovo_stato_id,
         user_update = COALESCE(p_user, CURRENT_USER)
   WHERE id = p_commessa_id;

  RETURN QUERY
  SELECT p_commessa_id, v_stato_corrente_cod, p_nuovo_stato;
END
$function$

COMMENT ON FUNCTION vendite.fn_cambia_stato_commessa(p_commessa_id bigint, p_nuovo_stato character varying, p_user text)
IS 'Entrypoint DB-first cambio stato commessa. Risolve codice->id e UPDATE; matrice + guard dominio (->PRONTA_FATTURAZIONE richiede righe approvate) enforced dal trigger trgfn_commesse_guard_transizione. rev 2026-06-07. rev 2026-08-06: la destinazione non risolta solleva E_STATO_WORKFLOW_NON_TROVATO (892) invece di E_STATO_SCONOSCIUTO (9), ritirato. Il vecchio codice era sollevato anche da config.trgfn_toponomastica_normalize, dove «stato» significava NAZIONE dell''indirizzo: due verita'' diverse sotto un nome solo, e nessun http_status poteva essere giusto per entrambe (404 la destinazione che non esiste, 400 il campo da correggere). Brief brief-db-be-terzo-lato-presidio-codici §11.2, decisione di Tid del 2026-08-06.';
```

</div>

---
{% include-markdown "signature-core.md" %}
