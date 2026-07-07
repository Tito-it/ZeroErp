{% include-markdown "it/dbzero/pratiche/manual/fn_reconcile_sorgente.md" %}
# ⚙️ Funzione `fn_reconcile_sorgente`

```sql
CREATE FUNCTION fn_reconcile_sorgente(p_sorgente_tipo_id bigint, p_sorgente_uid text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_reconcile_sorgente(p_sorgente_tipo_id bigint, p_sorgente_uid text)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: motore di avanzamento milestone su esito proiettato (GUIDA D4/G3a).
--   Consuma il descrittore normalizzato (fn_stato_sorgente) e completa i
--   milestone che attendono quel verdetto, per QUALSIASI percorso di
--   scrittura del documento (standalone incluso). Ritorna il numero di
--   milestone avanzati.
DECLARE
  v_esito         pratiche.flussi.esito%TYPE;
  v_stato_incorso config.stati_flussi_pratiche.id%TYPE;
  v_stato_compl   config.stati_flussi_pratiche.id%TYPE;
  v_avanzati      integer := 0;
  r_ps            record;
  r_f             record;
  v_cand_count    integer;
BEGIN
  -- Guard parametri ID: errore esplicito, no normalizzazione silenziosa.
  IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche','pratiche.fn_reconcile_sorgente','E_PARAMETRO_INVALIDO',
      jsonb_build_object('param','p_sorgente_tipo_id','valore',p_sorgente_tipo_id),
      NULL::uuid,'p_sorgente_tipo_id obbligatorio e > 0');
  END IF;
  IF p_sorgente_uid IS NULL OR btrim(p_sorgente_uid) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'pratiche','pratiche.fn_reconcile_sorgente','E_PARAMETRO_INVALIDO',
      jsonb_build_object('param','p_sorgente_uid'),
      NULL::uuid,'p_sorgente_uid obbligatorio');
  END IF;

  -- Descrittore normalizzato: esito e' SEMPRE un verdetto o NULL.
  SELECT d.esito INTO v_esito
    FROM pratiche.fn_stato_sorgente(p_sorgente_tipo_id, p_sorgente_uid) d;

  -- Nessun verdetto (es. EMESSO) -> nessun avanzamento automatico.
  IF v_esito IS NULL THEN
    RETURN 0;
  END IF;

  -- Stati destinazione, risolti una volta.
  SELECT id INTO v_stato_incorso
    FROM config.stati_flussi_pratiche WHERE codice_interno = 'IN_CORSO';
  SELECT id INTO v_stato_compl
    FROM config.stati_flussi_pratiche WHERE codice_interno = 'COMPLETATO';

  -- Ogni aggancio pratica<->documento su (tipo, uid).
  FOR r_ps IN
    SELECT ps.pratica_id, ps.flusso_id
      FROM pratiche.pratiche_sorgenti ps
     WHERE ps.sorgente_tipo_id = p_sorgente_tipo_id
       AND ps.sorgente_uid = p_sorgente_uid
  LOOP
    -- Milestone candidati nella pratica: template che attende questo tipo,
    -- con binding G2 attivo che matcha il verdetto, NON terminali; se il
    -- link porta un flusso_id esplicito ci si restringe a quello (D-B5).
    SELECT count(*) INTO v_cand_count
      FROM pratiche.flussi f
      JOIN pratiche.template_flussi tf ON tf.id = f.template_flusso_id
      JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
     WHERE f.pratica_id = r_ps.pratica_id
       AND tf.attende_sorgente_tipo_id = p_sorgente_tipo_id
       AND s.codice_interno NOT IN ('COMPLETATO','ANNULLATO')
       AND (r_ps.flusso_id IS NULL OR f.id = r_ps.flusso_id)
       AND EXISTS (
             SELECT 1 FROM pratiche.template_flussi_avanzamento_proiezione b
              WHERE b.template_flusso_id = tf.id
                AND b.attivo
                AND (b.esito_richiesto IS NULL OR b.esito_richiesto = v_esito));

    -- Ambiguo: piu' candidati senza link per-flusso -> non indovinare (D-B5).
    -- Il log e' a prova di fallimento: un errore nello scrivere il log NON
    -- deve propagare (best-effort) -> fallback RAISE WARNING (server log).
    IF r_ps.flusso_id IS NULL AND v_cand_count > 1 THEN
      BEGIN
        INSERT INTO pratiche.reconcile_errori
               (sorgente_tipo_id, sorgente_uid, pratica_id, errcode, messaggio, tx_id)
        VALUES (p_sorgente_tipo_id, p_sorgente_uid, r_ps.pratica_id,
                'E_RECONCILE_AMBIGUO',
                format('%s milestone candidati per tipo %s senza flusso_id esplicito: skip',
                       v_cand_count, p_sorgente_tipo_id),
                dbops.fn_get_or_create_session_tx_id());
      EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'reconcile_errori log (ambiguo) fallito per (tipo %, uid %): [%] %',
          p_sorgente_tipo_id, p_sorgente_uid, SQLSTATE, SQLERRM;
      END;
      CONTINUE;
    END IF;

    -- Avanzamento dei candidati (a due salti dove serve).
    FOR r_f IN
      SELECT f.id, s.codice_interno AS stato
        FROM pratiche.flussi f
        JOIN pratiche.template_flussi tf ON tf.id = f.template_flusso_id
        JOIN config.stati_flussi_pratiche s ON s.id = f.stato_id
       WHERE f.pratica_id = r_ps.pratica_id
         AND tf.attende_sorgente_tipo_id = p_sorgente_tipo_id
         AND s.codice_interno NOT IN ('COMPLETATO','ANNULLATO')
         AND (r_ps.flusso_id IS NULL OR f.id = r_ps.flusso_id)
         AND EXISTS (
               SELECT 1 FROM pratiche.template_flussi_avanzamento_proiezione b
                WHERE b.template_flusso_id = tf.id
                  AND b.attivo
                  AND (b.esito_richiesto IS NULL OR b.esito_richiesto = v_esito))
    LOOP
      -- D-B2: la matrice non ha DA_ESEGUIRE->COMPLETATO diretta.
      IF r_f.stato = 'DA_ESEGUIRE' THEN
        UPDATE pratiche.flussi SET stato_id = v_stato_incorso WHERE id = r_f.id;
      END IF;
      -- Completamento con il verdetto proiettato -> scatta la generazione a valle.
      UPDATE pratiche.flussi
         SET stato_id = v_stato_compl, esito = v_esito
       WHERE id = r_f.id;
      v_avanzati := v_avanzati + 1;
    END LOOP;
  END LOOP;

  RETURN v_avanzati;
END;
$function$

COMMENT ON FUNCTION pratiche.fn_reconcile_sorgente(p_sorgente_tipo_id bigint, p_sorgente_uid text)
IS 'GUIDA D4/G3a: motore di avanzamento milestone su esito proiettato. Se il documento (tipo, uid) proietta un verdetto (fn_stato_sorgente.esito), completa i milestone in attesa (template_flussi.attende_sorgente_tipo_id + binding template_flussi_avanzamento_proiezione), a due salti (D-B2), idempotente sui non-terminali (D-B11), con tie-break multi-istanza via pratiche_sorgenti.flusso_id (D-B5). INVOKER (D-B4). Ritorna il numero di milestone avanzati.';
```

---
{% include-markdown "signature-core.md" %}
