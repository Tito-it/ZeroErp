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
DECLARE
    v_allow_logs text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Tenere vendite.event_log append-only, distinguendo pero'
    --   fra ALTERARE LA STORIA e RITIRARE CIO' CHE E' SCADUTO.
    --
    -- Regole:
    --   UPDATE                      -> sempre vietato
    --   DELETE con GUC manutenzione -> ammesso (parita' con
    --                                  script.trgfn_logs_guard_delete)
    --   DELETE di riga scaduta      -> ammesso (retention)
    --   DELETE di riga viva         -> vietato
    --
    -- ⭐ Il criterio del terzo ramo non e' CHI cancella ma COSA:
    --   cosi' dbops.fn_purge_cleanup_expired funziona com'e',
    --   senza propagare GUC ne' riconoscere ruoli, e senza
    --   toccare una funzione condivisa di dbops.
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

    -- 1. Manutenzione straordinaria: stessa leva dei log gemelli.
    v_allow_logs := current_setting('zeroerp.maintenance_allow_delete_logs', true);

    IF COALESCE(lower(v_allow_logs), 'off') IN ('on', 'true', '1') THEN
        RETURN OLD;
    END IF;

    -- 2. Retention: la riga ha passato la sua scadenza.
    --    ⚠️ `cleanup_at` NULL = riga senza scadenza (nessuna
    --    regola CLEANUP_AT corrispondeva quando e' nata): non si
    --    cancella. In dubbio si conserva.
    IF OLD.cleanup_at IS NOT NULL AND OLD.cleanup_at <= now() THEN
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
IS 'Tiene vendite.event_log append-only distinguendo fra ALTERARE LA STORIA e RITIRARE CIO'' CHE E'' SCADUTO. UPDATE sempre vietato (E_UPDATE_NOT_ALLOWED); DELETE ammesso solo con la GUC zeroerp.maintenance_allow_delete_logs (parita'' con script.trgfn_logs_guard_delete dei log gemelli) o su riga con cleanup_at <= now(). ⭐ Il criterio del secondo ramo non e'' CHI cancella ma COSA: cosi'' dbops.fn_purge_cleanup_expired funziona com''e'', senza propagare GUC ne'' riconoscere ruoli. ⭐ Ed e'' il veto sull''UPDATE a rendere immutabile cleanup_at: nessuno puo'' anticipare la scadenza di una riga scomoda. ⚠️ Prima del 2026-08-22 era un RAISE EXCEPTION nudo, senza codice registrato, e vietava anche il DELETE della retention: con cleanup_at il job settimanale avrebbe iniziato a fallire.';
```

</div>

---
{% include-markdown "signature-core.md" %}
