{% include-markdown "it/dbzero/vendite/manual/fn_log_commessa_push_run.md" %}
# ⚙️ Funzione `fn_log_commessa_push_run`

```sql
CREATE FUNCTION fn_log_commessa_push_run(p_dry_run boolean, p_source_types text[], p_risultato jsonb, p_stato character varying, p_durata_ms integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_log_commessa_push_run(p_dry_run boolean DEFAULT false, p_source_types text[] DEFAULT NULL::text[], p_risultato jsonb DEFAULT '{}'::jsonb, p_stato character varying DEFAULT 'COMPLETATO'::character varying, p_durata_ms integer DEFAULT NULL::integer)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_id vendite.commesse_push_log.id%TYPE;
  v_stato vendite.commesse_push_log.stato%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Inserire una riga audit append-only per il run del push
  --   commesse, con validazioni fail-fast sui campi principali.
  --
  -- Regole:
  --   - stato ammesso: COMPLETATO | PARZIALE | ERRORE
  --   - durata_ms, se valorizzata, deve essere >= 0
  --   - user_insert gestito dal trigger audit JWT
  -- =========================================================
  v_stato := upper(COALESCE(NULLIF(btrim(p_stato), ''), ''));
  IF v_stato = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_log_commessa_push_run','E_GENERICO',
      jsonb_build_object(
        'scope','COMMESSE','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','stato run obbligatorio')
      ),
      NULL::uuid,
      'stato run obbligatorio'
    );
  END IF;

  IF v_stato NOT IN ('COMPLETATO', 'PARZIALE', 'ERRORE') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_log_commessa_push_run','E_GENERICO',
      jsonb_build_object(
        'scope','COMMESSE','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object(
          'detail','stato run non valido',
          'stato',v_stato
        )
      ),
      NULL::uuid,
      concat('stato run non valido: ', v_stato)
    );
  END IF;

  IF p_durata_ms IS NOT NULL AND p_durata_ms < 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_log_commessa_push_run','E_GENERICO',
      jsonb_build_object(
        'scope','COMMESSE','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object(
          'detail','durata_ms non valida',
          'durata_ms',p_durata_ms
        )
      ),
      NULL::uuid,
      'durata_ms non valida'
    );
  END IF;

  INSERT INTO vendite.commesse_push_log (
    dry_run,
    source_types,
    risultato,
    stato,
    durata_ms
  )
  VALUES (
    COALESCE(p_dry_run, false),
    p_source_types,
    COALESCE(p_risultato, '{}'::jsonb),
    v_stato,
    p_durata_ms
  )
  RETURNING id INTO v_id;

  RETURN v_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_log_commessa_push_run(p_dry_run boolean, p_source_types text[], p_risultato jsonb, p_stato character varying, p_durata_ms integer)
IS 'Registra il run dell''orchestratore push commesse in vendite.commesse_push_log con validazioni su stato e durata. User tracciato da audit JWT.';
```

---
{% include-markdown "signature-core.md" %}
