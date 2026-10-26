{% include-markdown "it/dbzero/vendite/manual/trgfn_v_ddt_protect_num.md" %}
# ⚙️ Funzione `trgfn_v_ddt_protect_num`

```sql
CREATE FUNCTION trgfn_v_ddt_protect_num()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_v_ddt_protect_num()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rende ddt.numero immutabile UNA VOLTA assegnato (a EMESSO),
--   ma consente la prima valorizzazione (NULL->valore). Eccezione al
--   lock framework (disabilitato per vendite.ddt.numero) necessaria
--   perche' il numero si assegna a EMESSO, non in DRAFT (C6).
BEGIN
    IF OLD.numero IS NOT NULL
       AND NEW.numero IS DISTINCT FROM OLD.numero THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_CODICE_NON_MODIFICABILE',
            jsonb_build_object(
                'column',    'numero',
                'old_value', OLD.numero,
                'new_value', NEW.numero
            ),
            NEW.tx_id,
            'numero'
        );
    END IF;
    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_v_ddt_protect_num()
IS 'Protect condizionale ddt.numero: immutabile dopo la prima assegnazione (a EMESSO), consente NULL->valore. Sostituisce il lock piatto framework (disabilitato in automation_lock_columns) perche'' il numero DDT si assegna a EMESSO, non in DRAFT (C6). rev 2026-07-09.';
```

</div>

---
{% include-markdown "signature-core.md" %}
