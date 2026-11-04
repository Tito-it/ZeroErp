{% include-markdown "it/dbzero/script/manual/fn_canale_log_stringa.md" %}
# ⚙️ Funzione `fn_canale_log_stringa`

```sql
CREATE FUNCTION fn_canale_log_stringa()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_canale_log_stringa()
 RETURNS text
 LANGUAGE sql
 STABLE PARALLEL SAFE
 SET search_path TO 'pg_catalog'
AS $function$
    SELECT CASE
             -- l'interruttore: solo 'off' spegne, assente vale acceso
             WHEN lower(btrim(coalesce(current_setting('myapp.log_with_dblink', true), ''))) = 'off'
               THEN NULL
             -- la stringa: myapp.logconn vince su myapp.dblink_log_connection
             WHEN btrim(coalesce(current_setting('myapp.logconn', true), '')) <> ''
               THEN current_setting('myapp.logconn', true)
             WHEN btrim(coalesce(current_setting('myapp.dblink_log_connection', true), '')) <> ''
               THEN current_setting('myapp.dblink_log_connection', true)
           END;
$function$

COMMENT ON FUNCTION script.fn_canale_log_stringa()
IS 'La stringa di connessione del canale di log fuori transazione (dblink), se il canale e'' ACCESO; NULL se e'' spento o non configurato. La regola e'' una: acceso se c''e'' una stringa non vuota e myapp.log_with_dblink non vale ''off'' (maiuscole e spazi non contano); l''interruttore assente vale acceso. La stringa e'' myapp.logconn se valorizzata, altrimenti myapp.dblink_log_connection. Restituisce la stringa e non un booleano perche'' chi chiede se il canale e'' acceso la usa subito per connettersi: due letture separate tornerebbero a divergere. La leggono script.fn_ensure_logconn, dbops.fn_get_or_create_session_tx_id, script.fn_log_error_only e maintenance.fn_job_run_log_failure; dbops.fn_audit_log_once no, finche'' non si decide il suo ramo dblink. Non apre connessioni.';
```

</div>

---
{% include-markdown "signature-core.md" %}
