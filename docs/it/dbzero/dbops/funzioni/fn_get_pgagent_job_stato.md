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
IS 'Che cosa sa pgAgent di un job: se e'' abilitato, quando ha girato l''ultima volta, quando girera'' la prossima. Sono le due date che il nostro giornale non ha, e servono a rispondere a «tutti i lavori hanno una programmazione, e stanno partendo?». ⛔ E'' una FUNZIONE plpgsql e non un JOIN dentro una vista perche'' 85_pgagent in CI e'' MARK_RAN: una vista si risolve alla CREATE e il migrate si fermerebbe dove l''estensione non c''e'' — stessa regola presa per django.* col changeSet 20260905-30. ⭐ SECURITY DEFINER dal 20260906-08, ed e'' una CORREZIONE: era INVOKER, e zeroerp_app non ha USAGE sullo schema pgagent — la vista di panorama era illeggibile proprio da chi deve usarla («permesso negato per lo schema pgagent»). L''alternativa era un GRANT sullo schema all''applicazione, che avrebbe aperto anche pga_joblog (l''output dei comandi eseguiti): per far leggere tre date si sarebbe concesso un archivio. ⇒ Porta stretta: tre campi innocui di UN job nominato. ⚠️ Basta il proprietario degli oggetti, che su pgagent ha gia'' i permessi: nessun superuser. ⚠️ Torna ZERO RIGHE se l''estensione manca, se il jobname e'' NULL o se quel job non esiste. ⭐ Il difetto l''ha trovato test-riferimenti-morti-v1, compilando la funzione con plpgsql_check: nessuna prova manuale l''aveva visto, perche'' giravano tutte da titodb.';
```

</div>

---
{% include-markdown "signature-core.md" %}
