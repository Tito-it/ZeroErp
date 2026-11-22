{% include-markdown "it/dbzero/maintenance/manual/fn_pota_giornale_corse.md" %}
# ⚙️ Funzione `fn_pota_giornale_corse`

```sql
CREATE FUNCTION fn_pota_giornale_corse(p_prima_di timestamp with time zone)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION maintenance.fn_pota_giornale_corse(p_prima_di timestamp with time zone)
 RETURNS jsonb
 LANGUAGE plpgsql
 STRICT
AS $function$
DECLARE
  -- bigint: il numero delle righe cancellate, un conteggio (non e' il riflesso di una colonna)
  v_cancellate bigint;
BEGIN
  -- Scopo: la ritenzione del giornale. Cancella le corse chiuse con
  --   started_at prima di p_prima_di, dei processi che non dichiarano
  --   dbops.processi.potatura_esclusione, tranne le righe tenute: per
  --   ogni corsia (processo, jobname) di maintenance.vw_job_run_corsie
  --   l'ultima di ciascun predicato dei lettori. Le corse aperte non si
  --   toccano mai.
  WITH tenute AS (
           SELECT t.id
             FROM maintenance.vw_job_run_corsie k
            CROSS JOIN LATERAL (
                  (SELECT l.id FROM maintenance.job_run_log l
                    WHERE l.processo_codice = k.processo_codice AND l.jobname = k.jobname
                    ORDER BY l.started_at DESC, l.id DESC LIMIT 1)
                  UNION ALL
                  (SELECT l.id FROM maintenance.job_run_log l
                    WHERE l.processo_codice = k.processo_codice AND l.jobname = k.jobname AND l.ended_at IS NOT NULL AND NOT l.saltata
                    ORDER BY l.started_at DESC, l.id DESC LIMIT 1)
                  UNION ALL
                  (SELECT l.id FROM maintenance.job_run_log l
                    WHERE l.processo_codice = k.processo_codice AND l.jobname = k.jobname AND l.ruolo_sessione IS NOT NULL
                    ORDER BY l.started_at DESC, l.id DESC LIMIT 1)
                  UNION ALL
                  (SELECT l.id FROM maintenance.job_run_log l
                    WHERE l.processo_codice = k.processo_codice AND l.jobname = k.jobname AND l.ok IS FALSE
                    ORDER BY l.started_at DESC, l.id DESC LIMIT 1)
                  UNION ALL
                  (SELECT l.id FROM maintenance.job_run_log l
                    WHERE l.processo_codice = k.processo_codice AND l.jobname = k.jobname AND l.origine = 'PGAGENT'
                    ORDER BY l.started_at DESC, l.id DESC LIMIT 1)
                 ) t
       )
  DELETE FROM maintenance.job_run_log l
   WHERE l.started_at < p_prima_di
     AND l.ended_at IS NOT NULL
     AND NOT EXISTS (SELECT 1
                       FROM dbops.processi pr
                      WHERE pr.codice = l.processo_codice
                        AND pr.potatura_esclusione IS NOT NULL)
     AND NOT EXISTS (SELECT 1 FROM tenute t WHERE t.id = l.id);

  GET DIAGNOSTICS v_cancellate = ROW_COUNT;

  RETURN jsonb_build_object('soglia', p_prima_di, 'cancellate', v_cancellate);
END;
$function$

COMMENT ON FUNCTION maintenance.fn_pota_giornale_corse(p_prima_di timestamp with time zone)
IS 'La ritenzione del giornale delle corse. Cancella da maintenance.job_run_log le corse chiuse (ended_at valorizzato) con started_at prima della soglia, dei processi che non dichiarano dbops.processi.potatura_esclusione. Tiene sempre, per ogni coppia (processo, jobname), l''ultima riga (started_at, id decrescenti) di ciascun predicato con cui i lettori cercano «l''ultima»: in assoluto, conclusa e non saltata, col ruolo registrato, fallita, di pgAgent; e ogni corsa aperta, a qualunque eta''. Restituisce l''esito {soglia, cancellate}. STRICT: con la soglia NULL non cancella niente. SECURITY INVOKER: la chiama maintenance.proc_pota_giornale_corse_job, che fissa la soglia a 12 mesi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
