{% include-markdown "it/dbzero/dbops/manual/fn_get_pgagent_job_stato.md" %}
# ⚙️ Funzione `fn_get_pgagent_job_stato`

```sql
CREATE FUNCTION fn_get_pgagent_job_stato(p_jobname text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_get_pgagent_job_stato(p_jobname text)
 RETURNS TABLE(abilitato boolean, ultima_esecuzione timestamp with time zone, prossima_esecuzione timestamp with time zone)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire che cosa sa pgAgent di un job: se e' acceso, quando
    --   ha girato, quando girera'.
    --
    -- ⭐ SECURITY DEFINER, e la porta e' STRETTA: torna tre campi
    --   innocui di UN job nominato. L'alternativa era dare
    --   all'applicazione l'accesso all'intero schema pgagent —
    --   compreso pga_joblog, che contiene l'output dei comandi.
    --   Per far leggere tre date si sarebbe concesso un archivio.
    --
    -- ⛔ Zero righe significa «non so niente di questo job»:
    --   l'estensione manca, oppure il job non c'e'. Chi chiama e'
    --   un LEFT JOIN LATERAL e vede colonne vuote — che e' la
    --   risposta giusta, non un errore.
    -- =========================================================

    IF p_jobname IS NULL THEN
        RETURN;   -- il processo non dichiara nessun job
    END IF;

    -- ⚠️ La guardia non e' per scaramanzia: su un ambiente senza
    --   pgAgent quella tabella non esiste, e senza questo controllo
    --   la funzione fallirebbe alla PRIMA chiamata — cioe' la vista
    --   di panorama sarebbe inutilizzabile proprio dove serve di
    --   piu' capire che cosa manca.
    IF to_regclass('pgagent.pga_job') IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT j.jobenabled, j.joblastrun, j.jobnextrun
      FROM pgagent.pga_job j
     WHERE j.jobname = p_jobname;
END
$function$

COMMENT ON FUNCTION dbops.fn_get_pgagent_job_stato(p_jobname text)
IS 'Che cosa sa pgAgent di un job: se e'' abilitato, quando ha girato l''ultima volta, quando girera'' la prossima. Sono le due date che il giornale non ha, e servono a rispondere a «tutti i lavori hanno una programmazione, e stanno partendo?». ⛔ E'' una funzione plpgsql e non un JOIN dentro una vista perche'' lo schema pgagent puo'' mancare (in CI la fase 85_pgagent non gira): una vista si risolve alla CREATE e il migrate si fermerebbe dove l''estensione non c''e''. SECURITY DEFINER del proprietario degli oggetti, che su pgagent ha i permessi, nessun superuser: zeroerp_app non ha USAGE sullo schema pgagent, e concederglielo aprirebbe anche pga_joblog, l''output dei comandi eseguiti. E'' una porta stretta: tre campi di UN job nominato. Torna zero righe se l''estensione manca, se il jobname e'' NULL o se quel job non esiste.';
```

</div>

---
{% include-markdown "signature-core.md" %}
