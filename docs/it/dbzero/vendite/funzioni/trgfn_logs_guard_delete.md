{% include-markdown "it/dbzero/vendite/manual/trgfn_logs_guard_delete.md" %}
# ⚙️ Funzione `trgfn_logs_guard_delete`

```sql
CREATE FUNCTION trgfn_logs_guard_delete()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_logs_guard_delete()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_allow_logs  text;
    v_allow_reset text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Proteggere fatture_log e fatturazione_lotti_log dalla
    --   cancellazione ACCIDENTALE, distinguendo pero' fra
    --   CANCELLARE LA STORIA e RITIRARE CIO' CHE E' SCADUTO.
    --
    -- Regole:
    --   DELETE con GUC manutenzione -> ammesso
    --     (zeroerp.maintenance_allow_delete_logs, oppure
    --      zeroerp.maintenance_reset_lotto_draft: il reset
    --      tecnico di un lotto in bozza)
    --   DELETE di riga scaduta      -> ammesso (retention)
    --   DELETE di riga viva         -> vietato
    --
    -- ⭐ Rev 2026-09-18 (Passo D): il ramo della retention.
    --   Il criterio non e' CHI cancella ma COSA: cosi'
    --   dbops.fn_purge_cleanup_expired funziona com'e', senza
    --   propagare GUC ne' riconoscere ruoli — parita' con
    --   vendite.trgfn_event_log_append_only.
    --
    -- ⚠️ cleanup_at NULL = riga senza scadenza (nessuna regola
    --   CLEANUP_AT quando e' nata): non si cancella. In dubbio
    --   si conserva.
    -- =========================================================

    -- 1. Manutenzione straordinaria e reset tecnico: com'era.
    v_allow_logs  := current_setting('zeroerp.maintenance_allow_delete_logs', true);
    v_allow_reset := current_setting('zeroerp.maintenance_reset_lotto_draft', true);

    IF COALESCE(lower(v_allow_logs), 'off') IN ('on', 'true', '1')
       OR COALESCE(lower(v_allow_reset), 'off') IN ('on', 'true', '1') THEN
        RETURN OLD;
    END IF;

    -- 2. Retention: la riga ha passato la sua scadenza.
    IF OLD.cleanup_at IS NOT NULL AND OLD.cleanup_at <= now() THEN
        RETURN OLD;
    END IF;

    -- 3. Tutto il resto e' storia viva, e non si cancella.
    PERFORM script.fn_log_and_raise_error(
        'vendite', TG_NAME, 'E_DELETE_NOT_ALLOWED',
        jsonb_build_object(
            'table',      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
            'id',         OLD.id,
            'cleanup_at', OLD.cleanup_at
        ),
        NULL::uuid, TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME, OLD.id::text
    );

    RETURN OLD;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_logs_guard_delete()
IS 'BEFORE DELETE su vendite.fatture_log e vendite.fatturazione_lotti_log. Vieta la cancellazione di una riga VIVA; ammette quella con GUC di manutenzione (zeroerp.maintenance_allow_delete_logs / zeroerp.maintenance_reset_lotto_draft) e — rev 2026-09-18, Passo D di analisi-osservabilita-log.md — quella di una riga SCADUTA (cleanup_at <= now()): e'' la retention che passa, con lo stesso criterio di trgfn_event_log_append_only (non CHI cancella ma COSA), cosi'' dbops.fn_purge_cleanup_expired funziona com''e''. ⚠️ cleanup_at NULL = non scade mai. ⛔ Legge OLD.cleanup_at: si monta solo su tabelle che hanno la colonna.';
```

</div>

---
{% include-markdown "signature-core.md" %}
