{% include-markdown "it/dbzero/vendite/manual/trgfn_event_log_append_only.md" %}
# ⚙️ Funzione `trgfn_event_log_append_only`

```sql
CREATE FUNCTION trgfn_event_log_append_only()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_event_log_append_only()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Tenere vendite.event_log append-only, distinguendo pero'
    --   fra ALTERARE LA STORIA e RITIRARE CIO' CHE E' SCADUTO.
    --
    -- Regole:
    --   UPDATE                         -> sempre vietato
    --   DELETE di riga scaduta         -> ammesso (retention)
    --   DELETE con porta di manutenzione -> ammesso (parita' con
    --                                     vendite.trgfn_logs_guard_delete)
    --   DELETE di riga viva            -> vietato
    --
    -- ⭐ Il criterio della retention non e' CHI cancella ma COSA:
    --   cosi' dbops.fn_purge_cleanup_expired funziona com'e',
    --   senza propagare GUC ne' riconoscere ruoli.
    --
    -- ⭐ Il veto sull'UPDATE e' cio' che rende `cleanup_at`
    --   immutabile: nessuno puo' anticipare la scadenza di una
    --   riga scomoda.
    -- =========================================================

    IF TG_OP = 'UPDATE' THEN
        PERFORM script.fn_log_and_raise_error(
            TG_TABLE_SCHEMA::text,
            'trgfn_event_log_append_only',
            'E_UPDATE_NOT_ALLOWED',
            jsonb_build_object(
                'detail', 'Registro append-only: la storia non si modifica',
                'table',  TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'id',     OLD.id
            ),
            NULL::uuid,
            TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
            OLD.id::text
        );
    END IF;

    -- Da qui in giu' e' un DELETE.

    -- 1. Retention: la riga ha passato la sua scadenza.
    --    ⚠️ `cleanup_at` NULL = riga senza scadenza (nessuna
    --    regola CLEANUP_AT corrispondeva quando e' nata): non si
    --    cancella. In dubbio si conserva.
    IF OLD.cleanup_at IS NOT NULL AND OLD.cleanup_at <= now() THEN
        RETURN OLD;
    END IF;

    -- 2. Manutenzione straordinaria: stessa porta dei log gemelli,
    --    aperta solo per la sessione del migratore, con la riga
    --    nel diario.
    IF script.fn_porta_manutenzione_aperta(
           'zeroerp.maintenance_allow_delete_logs', TG_RELID, TG_OP, OLD.id::text) THEN
        RETURN OLD;
    END IF;

    -- 3. Tutto il resto e' storia, e la storia non si cancella.
    PERFORM script.fn_log_and_raise_error(
        TG_TABLE_SCHEMA::text,
        'trgfn_event_log_append_only',
        'E_DELETE_NOT_ALLOWED',
        jsonb_build_object(
            'detail',     'Registro append-only: riga non scaduta',
            'table',      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
            'id',         OLD.id,
            'cleanup_at', OLD.cleanup_at
        ),
        NULL::uuid,
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        OLD.id::text
    );

    RETURN OLD;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_event_log_append_only()
IS 'Tiene vendite.event_log append-only distinguendo fra ALTERARE LA STORIA e RITIRARE CIO'' CHE E'' SCADUTO. UPDATE sempre vietato (E_UPDATE_NOT_ALLOWED); DELETE ammesso su una riga con cleanup_at <= now() (la retention) o dalla porta di manutenzione zeroerp.maintenance_allow_delete_logs, che apre solo per la sessione del migratore (script.fn_porta_manutenzione_aperta) e lascia la riga in dbops.porte_manutenzione_passaggi; ogni altro DELETE e'' E_DELETE_NOT_ALLOWED. ⭐ Il criterio della retention non e'' CHI cancella ma COSA: cosi'' dbops.fn_purge_cleanup_expired funziona com''e'', senza propagare GUC ne'' riconoscere ruoli. ⭐ Il veto sull''UPDATE rende immutabile cleanup_at: nessuno puo'' anticipare la scadenza di una riga scomoda. cleanup_at NULL = la riga non scade.';
```

</div>

---
{% include-markdown "signature-core.md" %}
