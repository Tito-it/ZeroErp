{% include-markdown "it/dbzero/vendite/manual/trgfn_v_resi_protect_num.md" %}
# ⚙️ Funzione `trgfn_v_resi_protect_num`

```sql
CREATE FUNCTION trgfn_v_resi_protect_num()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_v_resi_protect_num()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: rende resi.numero immutabile UNA VOLTA assegnato (a
--   CONFERMATO), ma consente la prima valorizzazione (NULL->valore).
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

COMMENT ON FUNCTION vendite.trgfn_v_resi_protect_num()
IS 'Protect condizionale resi.numero: immutabile dopo la prima assegnazione (a CONFERMATO), consente NULL->valore. Mirror trgfn_v_ddt_protect_num. rev 2026-07-13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
