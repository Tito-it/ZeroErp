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
    -- text nudo: il valore di una GUC, non il riflesso di una colonna
    v_allow_reset text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Proteggere fatture_log e fatturazione_lotti_log dalla
    --   cancellazione ACCIDENTALE, distinguendo pero' fra
    --   CANCELLARE LA STORIA e RITIRARE CIO' CHE E' SCADUTO.
    --
    -- Regole:
    --   DELETE del reset tecnico   -> ammesso (porta di verbo
    --     zeroerp.maintenance_reset_lotto_draft, aperta da
    --     vendite.fn_cleanup_fatture_by_ids)
    --   DELETE di riga scaduta     -> ammesso (retention)
    --   DELETE dalla porta di manutenzione -> ammesso
    --     (zeroerp.maintenance_allow_delete_logs, solo per la
    --      sessione del migratore, con la riga nel diario)
    --   DELETE di riga viva        -> vietato
    --
    -- ⭐ Il criterio della retention non e' CHI cancella ma COSA:
    --   cosi' dbops.fn_purge_cleanup_expired funziona com'e',
    --   senza propagare GUC ne' riconoscere ruoli — parita' con
    --   vendite.trgfn_event_log_append_only.
    --
    -- ⚠️ cleanup_at NULL = riga senza scadenza (nessuna regola
    --   CLEANUP_AT quando e' nata): non si cancella. In dubbio
    --   si conserva.
    -- =========================================================

    -- 1. Il reset tecnico di un lotto in bozza: porta di verbo, com'era.
    v_allow_reset := current_setting('zeroerp.maintenance_reset_lotto_draft', true);

    IF COALESCE(lower(v_allow_reset), 'off') IN ('on', 'true', '1') THEN
        RETURN OLD;
    END IF;

    -- 2. Retention: la riga ha passato la sua scadenza.
    IF OLD.cleanup_at IS NOT NULL AND OLD.cleanup_at <= now() THEN
        RETURN OLD;
    END IF;

    -- 3. Manutenzione straordinaria: la porta del migratore.
    IF script.fn_porta_manutenzione_aperta(
           'zeroerp.maintenance_allow_delete_logs', TG_RELID, TG_OP, OLD.id::text) THEN
        RETURN OLD;
    END IF;

    -- 4. Tutto il resto e' storia viva, e non si cancella.
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
IS 'BEFORE DELETE su vendite.fatture_log e vendite.fatturazione_lotti_log. Vieta la cancellazione di una riga VIVA (E_DELETE_NOT_ALLOWED). La ammette: dal reset tecnico del lotto in bozza (porta di verbo zeroerp.maintenance_reset_lotto_draft, aperta da vendite.fn_cleanup_fatture_by_ids); su una riga SCADUTA (cleanup_at <= now(), la retention, con lo stesso criterio di vendite.trgfn_event_log_append_only: non CHI cancella ma COSA, cosi'' dbops.fn_purge_cleanup_expired funziona com''e''); dalla porta di manutenzione zeroerp.maintenance_allow_delete_logs, che apre solo per la sessione del migratore (script.fn_porta_manutenzione_aperta) e lascia la riga in dbops.porte_manutenzione_passaggi. cleanup_at NULL = non scade mai. ⛔ Legge OLD.cleanup_at: si monta solo su tabelle che hanno la colonna.';
```

</div>

---
{% include-markdown "signature-core.md" %}
