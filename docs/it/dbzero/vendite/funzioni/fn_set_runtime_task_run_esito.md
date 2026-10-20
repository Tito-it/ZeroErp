{% include-markdown "it/dbzero/vendite/manual/fn_set_runtime_task_run_esito.md" %}
# ⚙️ Funzione `fn_set_runtime_task_run_esito`

```sql
CREATE FUNCTION fn_set_runtime_task_run_esito(p_task_run_id bigint, p_task_stato text, p_error_code text, p_error_message text, p_meta jsonb)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_set_runtime_task_run_esito(p_task_run_id bigint, p_task_stato text, p_error_code text DEFAULT NULL::text, p_error_message text DEFAULT NULL::text, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_task_stato text;
  v_error_code text;
  v_meta jsonb;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Applicare in modo uniforme la chiusura di un task-run
  --   runtime del LOTTO.
  --
  -- Regole:
  --   - validazione input minimi
  --   - update stato/ended_at/meta
  --   - fail: valorizza error_code/error_message
  --   - complete/cancel: non forza errori, salvo reset dedicato
  --
  -- rev 2026-08-04: via il ramo ATTIVITA_FATTURABILI e con esso
  --   il parametro `p_scope`. Quel ramo aggiornava
  --   vendite.attivita_fatturabili_lotti_task_runs, droppata il
  --   2026-02-27 col resto della famiglia «attivita pipeline»:
  --   il CASCADE non porta via i corpi plpgsql, che PostgreSQL
  --   non traccia come dipendenze. Non e' mai esplosa perche'
  --   plpgsql pianifica per singolo statement, alla prima
  --   esecuzione di quello statement, e i tre wrapper passavano
  --   tutti 'LOTTO' cablato: il ramo morto non e' mai stato
  --   nemmeno pianificato.
  --
  -- 📌 rev 2026-08-24 (R-1): cambia UN token, `ended_at`. Il resto
  --   del corpo e' quello vivo, riprodotto senza toccarlo.
  --   ⚠️ I tre `E_GENERICO` qui sotto sono debito NOTO e non di
  --   questo cantiere: correggerli vuol dire coniare tre codici
  --   registrati con la loro classe. Scritto perche' chi rilegge
  --   sappia che sono stati guardati, non ignorati.
  -- =========================================================
  v_task_stato := upper(COALESCE(NULLIF(btrim(p_task_stato), ''), ''));
  v_error_code := NULLIF(btrim(p_error_code), '');
  v_meta := COALESCE(p_meta, '{}'::jsonb);

  IF p_task_run_id IS NULL OR p_task_run_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_set_runtime_task_run_esito',
      'E_GENERICO',
      jsonb_build_object(
        'scope', 'LOTTO',
        'severity', 'C',
        'code', 'E_GENERICO',
        'lotto_id', NULL,
        'fattura_id', NULL,
        'context', jsonb_build_object(
          'detail', 'task_run_id obbligatorio',
          'task_run_id', p_task_run_id
        )
      ),
      NULL::uuid,
      'task_run_id obbligatorio'
    );
  END IF;

  IF v_task_stato NOT IN ('COMPLETATO', 'ERRORE', 'ANNULLATO') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_set_runtime_task_run_esito',
      'E_GENERICO',
      jsonb_build_object(
        'scope', 'LOTTO',
        'severity', 'C',
        'code', 'E_GENERICO',
        'lotto_id', NULL,
        'fattura_id', NULL,
        'context', jsonb_build_object(
          'detail', 'task_stato non valido',
          'task_stato', p_task_stato
        )
      ),
      NULL::uuid,
      'task_stato non valido'
    );
  END IF;

  UPDATE vendite.fatturazione_lotti_task_runs
     SET task_stato = v_task_stato,
         -- ⭐ R-1: lo STESSO orologio di `started_at`. Con `now()`
         --    un tentativo aperto e chiuso nella stessa transazione
         --    otterrebbe una fine ANTERIORE all'inizio, e
         --    chk_fatt_lotti_task_runs_timestamps lo rifiuterebbe.
         --    ⚠️ Misurato il 24-08-2026: 165 corse su 319 hanno
         --    ended_at = started_at esatto, cioe' sono esattamente
         --    quel caso — non un'ipotesi.
         ended_at = clock_timestamp(),
         error_code = CASE
           WHEN v_task_stato = 'ERRORE' THEN COALESCE(v_error_code, 'E_GENERICO')
           ELSE error_code
         END,
         error_message = CASE
           WHEN v_task_stato = 'ERRORE' THEN COALESCE(NULLIF(btrim(p_error_message), ''), 'Errore task')
           ELSE error_message
         END,
         meta = COALESCE(meta, '{}'::jsonb) || v_meta,
         -- ⚠️ Audit: resta now(), come in tutta la casa.
         data_update = now(),
         user_update = current_user
   WHERE id = p_task_run_id;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_set_runtime_task_run_esito',
      'E_GENERICO',
      jsonb_build_object(
        'scope', 'LOTTO',
        'severity', 'C',
        'code', 'E_GENERICO',
        'lotto_id', NULL,
        'fattura_id', NULL,
        'context', jsonb_build_object(
          'detail', 'task_run non trovato',
          'task_run_id', p_task_run_id
        )
      ),
      NULL::uuid,
      concat('task_run non trovato id:', p_task_run_id::text)
    );
  END IF;
END
$function$

COMMENT ON FUNCTION vendite.fn_set_runtime_task_run_esito(p_task_run_id bigint, p_task_stato text, p_error_code text, p_error_message text, p_meta jsonb)
IS 'Helper condiviso per chiudere un task-run runtime del LOTTO. rev 2026-08-04: via il ramo ATTIVITA_FATTURABILI e con esso il parametro p_scope, che restava con un solo valore lecito. Quel ramo aggiornava vendite.attivita_fatturabili_lotti_task_runs, droppata il 2026-02-27 (20260227-16) col resto della famiglia «attivita pipeline»: il CASCADE non porta via i corpi plpgsql, che PostgreSQL non traccia come dipendenze. ⚠️ Non era mai esplosa perche'' plpgsql pianifica per singolo statement alla prima esecuzione di quello statement, e i tre wrapper passavano tutti ''LOTTO'' cablato — il ramo morto non e'' mai stato nemmeno pianificato. Il COMMENT precedente prometteva due domini: era l''unica cosa che mentiva davvero.';
```

</div>

---
{% include-markdown "signature-core.md" %}
