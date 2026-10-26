{% include-markdown "it/dbzero/vendite/manual/trgfn_commesse_attivita_guard_quantita_immutabile.md" %}
# ⚙️ Funzione `trgfn_commesse_attivita_guard_quantita_immutabile`

```sql
CREATE FUNCTION trgfn_commesse_attivita_guard_quantita_immutabile()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_commesse_attivita_guard_quantita_immutabile()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_bypass text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Immutabilita della quantita: una riga di commessa EMESSA e'
    --   un fatto e non si modifica con UPDATE (si corregge con righe
    --   nuove). Brief immutabilita-quantita §0/§4a.
    -- Regole:
    --   - blocca UPDATE della quantita se stato_emissione <> 'NON_EMESSA';
    --   - il re-push su NON_EMESSA (fn_upsert_commessa_attivita) passa
    --     (riga non emessa) -> nessun bypass necessario nella hot-path;
    --   - bypass tecnico via GUC zeroerp.maintenance_reset_lotto_draft
    --     (reset lotto), coerente con gli altri guard di dominio.
    -- =========================================================
    v_bypass := current_setting('zeroerp.maintenance_reset_lotto_draft', true);
    IF v_bypass IS NOT NULL AND lower(v_bypass) IN ('1','true','on','yes') THEN
        RETURN NEW;
    END IF;

    IF OLD.stato_emissione <> 'NON_EMESSA'
       AND NEW.quantita IS DISTINCT FROM OLD.quantita THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_COMMESSA_ATTIVITA_QUANTITA_IMMUTABILE',
            jsonb_build_object(
                'id', OLD.id,
                'segment_key', OLD.segment_key,
                'stato_emissione', OLD.stato_emissione,
                'quantita_old', OLD.quantita,
                'quantita_new', NEW.quantita),
            NULL::uuid, OLD.id::text, OLD.segment_key
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_commesse_attivita_guard_quantita_immutabile()
IS 'Guard immutabilita quantita commesse_attivita: blocca UPDATE della quantita su righe EMESSA (stato_emissione <> NON_EMESSA). Il re-push su NON_EMESSA passa; bypass tecnico via GUC zeroerp.maintenance_reset_lotto_draft. Errore E_COMMESSA_ATTIVITA_QUANTITA_IMMUTABILE. Brief immutabilita-quantita §4a.';
```

</div>

---
{% include-markdown "signature-core.md" %}
