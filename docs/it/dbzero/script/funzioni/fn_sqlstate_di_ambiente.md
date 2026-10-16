{% include-markdown "it/dbzero/script/manual/fn_sqlstate_di_ambiente.md" %}
# ⚙️ Funzione `fn_sqlstate_di_ambiente`

```sql
CREATE FUNCTION fn_sqlstate_di_ambiente(p_sqlstate text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_sqlstate_di_ambiente(p_sqlstate text)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- =========================================================
    -- Scopo:
    --   Dire se un SQLSTATE e' un guasto dell'AMBIENTE, cioe' una
    --   cosa che rimedia chi gestisce il server o il database, e
    --   non lo sviluppo. NULL -> false.
    -- =========================================================
    SELECT COALESCE(
               left(p_sqlstate, 2) IN ('08', '53', '57', '58')
               OR p_sqlstate IN ('42501', '55P03'),
               false);
$function$

COMMENT ON FUNCTION script.fn_sqlstate_di_ambiente(p_sqlstate text)
IS 'Se uno SQLSTATE e'' un guasto dell''AMBIENTE, cioe'' una cosa che rimedia chi gestisce il server o il database: classe 08 (connessione), 53 (risorse), 57 (intervento dell''operatore), 58 (sistema), piu'' 42501 (privilegio mancante: un diritto al ruolo e'' provisioning) e 55P03 (lock non ottenuto: contesa d''esercizio, D10). Il deadlock 40P01 e le altre 42xxx restano fuori: sono programma. NULL -> false. ⭐ Sede UNICA della lista (regola del 2): la usano la causa di maintenance.vw_job_run_da_guardare e i gestori WHEN others del framework automazioni, che rilanciano l''errore originale quando questa funzione dice si''. Brief: brief-db-presidio-job-run-a-chi-tocca (D8, D10).';
```

---
{% include-markdown "signature-core.md" %}
